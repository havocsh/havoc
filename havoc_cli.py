import re
import ast
import json
from configparser import ConfigParser
from cmd2 import Cmd
import havoc
import time as t


# Load the ./HAVOC profiles
def load_havoc_profiles():
    havoc_profiles = ConfigParser()
    havoc_profiles.read('.havoc/profiles')
    return havoc_profiles


def convert_input(args, inp):
    line = inp.split('--')
    for l in line:
        arg = re.search('([^=]+)=(.*)', l)
        if arg:
            if arg.group(1) in args and arg.group(1) != 'instruct_args' and arg.group(1) != 'module_args' and arg.group(1) != 'portgroups':
                args[arg.group(1)] = arg.group(2).strip()
            if arg.group(1) in args and (arg.group(1) == 'instruct_args' or arg.group(1) == 'module_args'):
                args[arg.group(1)] = ast.literal_eval(arg.group(2))
            if arg.group(1) in args and arg.group(1) in ['portgroups', 'capabilities']:
                args[arg.group(1)] = []
                for a in arg.group(2).split(','):
                    args[arg.group(1)].append(a.strip())
    return_args = {}
    for k,v in args.items():
        if v:
            return_args[k] = v
    return return_args


def format_output(command, data):
    data_out = {command: data}
    print(json.dumps(data_out, indent=4))


class HavocCMD(Cmd):

    print('         _ _         _    _  _____   ______ ')
    print('        / | |      \| |  | |/ ___ \ / _____)')
    print('       / /| |__  /  \ |  | | |   | | /      ')
    print('      / / |  __)/ /\ \ \/ /| |   | | |      ')
    print('     / /  | |  / |__| \  / | |___| | \_____ ')
    print('  ()/_/   |_| / ______|\/   \_____/ \______)')
    
    prompt = 'havoc> '
    intro = "havoc CLI - Type ? to list commands"

    def __init__(self):
        super().__init__()
        self.profile = None
        self.__havoc_client = None

    @property
    def havoc_client(self):
        if self.__havoc_client is None:
            havoc_profiles = load_havoc_profiles()
            if self.profile:
                api_key = havoc_profiles.get(self.profile, 'API_KEY')
                secret = havoc_profiles.get(self.profile, 'SECRET')
                api_region = havoc_profiles.get(self.profile, 'API_REGION')
                api_domain_name = havoc_profiles.get(self.profile, 'API_DOMAIN_NAME')
            else:
                api_key = havoc_profiles.get('default', 'API_KEY')
                secret = havoc_profiles.get('default', 'SECRET')
                api_region = havoc_profiles.get('default', 'API_REGION')
                api_domain_name = havoc_profiles.get('default', 'API_DOMAIN_NAME')
            self.__havoc_client = havoc.Connect(api_region, api_domain_name, api_key, secret, api_version=1)
        return self.__havoc_client

    def emptyline(self):
        pass

    def do_exit(self, inp):
        print('Bye')
        return True

    def help_exit(self):
        print('\nExit the application. Shorthand: Ctrl-D.\n')

    def do_get_deployment(self, inp):
        response = self.havoc_client.get_deployment()
        format_output('get_deployment', response)

    def help_get_deployment(self):
        print('\nGet details about the ./HAVOC deployment.')

    def do_list_tasks(self, inp):
        args = {'task_status': '', 'task_name_contains': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_tasks(**command_args)
        format_output('list_tasks', response)

    def help_list_tasks(self):
        print('\nList tasks.')
        print('\n--task_name_contains=<string> - (optional) only list tasks that contain the provided value in the task name')
        print('\n--task_status=(all|running|starting|idle|busy|terminated) - (optional) only list tasks whose status matches the provided value (defaults to "running," which includes tasks with a status of "starting," "idle," or "busy")')

    def do_get_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_task(**command_args)
        format_output('get_task', response)

    def help_get_task(self):
        print('\nGet details of a given task.')
        print('\n--task_name=<string> - (required) the name of the task to retrieve details for')

    def do_kill_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.kill_task(**command_args)
        format_output('kill_task', response)

    def help_kill_task(self):
        print('\nForce quit a running task.')
        print('\n--task_name=<string> - (required) the name of the task to kill')

    def do_verify_task(self, inp):
        args = {'task_name': '', 'task_type': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.verify_task(**command_args)
        if response:
            format_output('verify_task', response)
        else:
            format_output('verify_task', {command_args['task_name']: 'task not found'})

    def help_verify_task(self):
        print('\nCheck for the existence of a task with the given task_name and task_type')
        print('\n--task_name=<string> - (required) the name of the task to verify')
        print('\n--task_type=<string> - (required) the type of task that the verified task should be')

    def do_list_task_types(self, inp):
        response = self.havoc_client.list_task_types()
        format_output('list_task_types', response)

    def help_list_task_types(self):
        print('\nList all available task types.')

    def do_get_task_type(self, inp):
        args = {'task_type': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_task_type(**command_args)
        format_output('get_task_type', response)

    def help_get_task_type(self):
        print('\nGet details of a given task type.')
        print('\n--task_type=<string> - (required) the name of the task type to get')

    def do_create_task_type(self, inp):
        args = {'task_type': '', 'task_version': '', 'source_image': '', 'capabilities': '', 'cpu': '', 'memory': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_task_type(**command_args)
        format_output('create_task_type', response)

    def help_create_task_type(self):
        print('\nCreate a new task type with the given parameters.')
        print('\n--task_type=<string> - (required) a name to refer to the task type')
        print('\n--task_version=<string> - (required) the version number associated with this task type')
        print('\n--source_image=<string> - (required) URL of the source container image')
        print('\n--capabilities=<list> - (required) list of commands accepted by the task')
        print('\n--cpu=<integer> - (required) number of CPU cores to allocate to the task')
        print('\n--memory=<integer> - (required) amount of memory to allocate to the task')

    def do_delete_task_type(self, inp):
        args = {'task_type': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_task_type(**command_args)
        format_output('delete_task_type', response)

    def help_delete_task_type(self):
        print('\nDelete the given task type.')
        print('\n--task_type=<string> - (required) the name of the task type to delete')

    def do_list_triggers(self, inp):
        response = self.havoc_client.list_triggers()
        format_output('list_triggers', response)

    def help_list_triggers(self):
        print('\nList all triggers.')

    def do_get_trigger(self, inp):
        args = {'trigger_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_trigger(**command_args)
        format_output('get_trigger', response)

    def help_get_trigger(self):
        print('\nGet details of a given trigger.')
        print('\n--trigger_name=<string> - (required) the name of the trigger to get')

    def do_create_trigger(self, inp):
        args = {
            'trigger_name': '',
            'schedule_expression': '',
            'execute_command': '',
            'execute_command_args': '',
            'execute_command_timeout': '',
            'filter_command': '',
            'filter_command_args': '', 
            'filter_command_timeout': ''
        }
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_trigger(**command_args)
        format_output('create_trigger', response)

    def help_create_trigger(self):
        print('\nCreate a new trigger with the given parameters.')
        print('\n--trigger_name=<string> - (required) a name to assign to the trigger')
        print('\n--schedule_expression=<string> - (required) a rate or cron expression to specify execution interval of the trigger - examples: "rate(5 minutes)" or "cron(0 0 * * FRI)"')
        print('\n--execute_command=<string> - (required) The command to be executed by the trigger')
        print('\n--execute_command_args=<dict> - (optional) arguments applied to the execute_command; arguments should be specified as a dictionary of keys and values')
        print('\n--execute_command_timeout=<integer> - (optional) the number of seconds to wait for the execute command to return (defaults to 300 seconds)')
        print('\n--filter_command=<string> - (optional) provide a filter_command to run prior to the execute_command - if the filter_command does not return results, the trigger will exit')
        print('\n--filter_command_args=<dict> - (optional) arguments applied to the filter_command; arguments should be specified as a dictionary of keys and values')
        print('\n--filter_command_timeout=<integer> - (optional) the number of seconds to wait for the filter command to return (defaults to 300 seconds)')
        print('\n  *Note that the aggregate value of the execute_command_timeout and filter_command_timeout values should not exceed the schedule frequency')

    def do_delete_trigger(self, inp):
        args = {'trigger_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_trigger(**command_args)
        format_output('delete_trigger', response)

    def help_delete_trigger(self):
        print('\nDelete the given trigger.')
        print('\n--trigger_name=<string> - (required) the name of the trigger to delete')
    
    def do_execute_trigger(self, inp):
        args = {
            'trigger_name': '',
            'execute_command': '',
            'execute_command_args': '',
            'execute_command_timeout': '',
            'filter_command': '',
            'filter_command_args': '',
            'filter_command_timeout': ''
        }
        command_args = convert_input(args, inp)
        response = self.havoc_client.execute_trigger(**command_args)
        format_output('execute_trigger', response)

    def help_execute_trigger(self):
        print('\nExecute the given trigger.')
        print('\n--trigger_name=<string> - (required) the name of the trigger to execute')
        print('\n--execute_command=<string> - (required) The command to be executed by the trigger')
        print('\n--execute_command_args=<dict> - (optional) arguments applied to the execute_command; arguments should be specified as a dictionary of keys and values')
        print('\n--execute_command_timeout=<integer> - (optional) the number of seconds to wait for the execute command to return (defaults to 300 seconds)')
        print('\n--filter_command=<string> - (optional) provide a filter_command to run prior to the execute_command - if the filter_command does not return results, the trigger will exit')
        print('\n--filter_command_args=<dict> - (optional) arguments applied to the filter_command; arguments should be specified as a dictionary of keys and values')
        print('\n--filter_command_timeout=<integer> - (optional) the number of seconds to wait for the filter command to return (defaults to 300 seconds)')

    def do_get_trigger_results(self, inp):
        args = {'trigger_name': '', 'filter_command': '', 'execute_command': '', 'start_time': '', 'end_time': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_trigger_results(**command_args)
        format_output('get_trigger_results', response)

    def help_get_trigger_results(self):
        print('\nGet results for a given trigger, filtered by filter_command, execute_command, start_time and end_time.')
        print('\n--trigger_name=<string> - (required) retrieve results for the given trigger_name')
        print('\n--filter_command=<string> - (optional) filter the results by the specified filter_command')
        print('\n--execute_command=<string> - (optional) filter the results by the specified execute_command')
        print('\n--start_time=<string> - (optional) retrieve results that occurred after the specified time')
        print('\n--end_time=<string> - (optional) retrieve results that occurred before the specified time')

    def do_list_users(self, inp):
        response = self.havoc_client.list_users()
        format_output('list_users', response)

    def help_list_users(self):
        print('\nList all ./havoc users.')

    def do_get_user(self, inp):
        args = {'user_id': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_user(**command_args)
        format_output('get_user', response)

    def help_get_user(self):
        print('\nGet details of a given user.')
        print('\n--user_id=<string> - (required) the ID of the user to get')

    def do_create_user(self, inp):
        args = {'user_id': '', 'admin': '', 'remote_task': '', 'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_user(**command_args)
        format_output('create_user', response)

    def help_create_user(self):
        print('\nCreate a new user with the given parameters.')
        print('\n--user_id=<string> - (required) a unique identifier to associate with the user')
        print('\n--admin=[yes|no] - (optional) specify whether or not the user has admin privileges (defaults to no)')
        print('\n--remote_task=[yes|no] - (optional) specify whether or not the user is designated for a remote task (defaults to "*" which permits use for all tasks)')
        print('\n--task_name=<string> - (optional) associate the user with a specific task name')

    def do_update_user(self, inp):
        args = {'user_id': '', 'new_user_id': '', 'admin': '', 'remote_task': '', 'task_name': '', 'reset_keys': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.update_user(**command_args)
        format_output('update_user', response)

    def help_update_user(self):
        print('\nUpdate an existing user.')
        print('\n--user_id=<string> - (required) the user_id associated with the user to make updates to')
        print('\n--new_user_id=<string> - (optional) a new unique identifier to associate with the user')
        print('\n--admin=[yes|no] - (optional) - add or remove admin privileges for the user (defaults to no change)')
        print('\n--remote_task=[yes|no] - (optional) - add or remove remote task designation for the user (defaults to no change)')
        print('\n--task_name=<string> - (optional) - change the task name associated with the user (defaults to no change)')
        print('\n--reset_keys=yes - (optional) - forces a reset of the user\'s API key and secret (if not present, '
              'keys are not changed)')

    def do_delete_user(self, inp):
        args = {'user_id': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_user(**command_args)
        format_output('delete_user', response)

    def help_delete_user(self):
        print('\nDelete an existing user.')
        print('\n--user_id=<string> - (required) the user_id of the user to be deleted')

    def do_list_files(self, inp):
        args = {'path': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_files(**command_args)
        format_output('list_files', response)

    def help_list_files(self):
        print('\nList all files or files for a specific path in the workspace.')
        print('\n--path=<string> - (optional) the remote path in the workspace; can be shared/ or upload/')

    def do_get_file(self, inp):
        args = {'file_name': '', 'path': '', 'local_path': ''}
        command_args = convert_input(args, inp)
        local_path = command_args['local_path']
        file_name = command_args['file_name']
        f = open(f'{local_path}/{file_name}', 'wb')
        del command_args['local_path']
        response = self.havoc_client.get_file(**command_args)
        file_contents = response['file_contents']
        f.write(file_contents)
        f.close()
        del response['file_contents']
        response['local_path'] = local_path
        format_output('get_file', response)

    def help_get_file(self):
        print('\nDownload a file from the workspace.')
        print('\n--path=<string> - (required) the remote path in the workspace; can be shared/ or upload/')
        print('\n--file_name=<string> - (required) the name of the file to download.')
        print('\n--local_path=<string> - (required) the path to the local directory to download the file to')

    def do_create_file(self, inp):
        args = {'file_name': '', 'path': '', 'local_path': ''}
        command_args = convert_input(args, inp)
        path = command_args['path']
        file_name = command_args['file_name']
        local_path = command_args['local_path']
        with open(f'{local_path}/{file_name}', 'rb') as f:
            raw_file = f.read()
        command_args['raw_file'] = raw_file
        del command_args['local_path']
        response = self.havoc_client.create_file(**command_args)
        format_output('create_file', response)

    def help_create_file(self):
        print('\nUpload a file to the workspace.')
        print('\n--path=<string> - (required) the remote path in the workspace; can be shared/ or upload/')
        print('\n--file_name=<string> - (required) the name of the file to upload.')
        print('\n--local_path=<string> - (required) the path to the local directory where the file resides')

    def do_delete_file(self, inp):
        args = {'file_name': '', 'path': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_file(**command_args)
        format_output('delete_file', response)

    def help_delete_file(self):
        print('\nDelete a file in the workspace.')
        print('\n--path=<string> - (required) the remote path in the workspace; can be shared/ or upload/')
        print('\n--file_name=<string> - (required) the name of the file to be deleted.')

    def do_list_playbooks(self, inp):
        args = {'playbook_status': '', 'playbook_name_contains': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_playbooks(**command_args)
        format_output('list_playbooks', response)

    def help_list_playbooks(self):
        print('\nList all existing playbooks.')

    def do_get_playbook(self, inp):
        args = {'playbook_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_playbook(**command_args)
        format_output('get_playbook', response)

    def help_get_playbook(self):
        print('\nGet details of a given playbook.')
        print('\n--playbook_name=<string> - (required) the name of the playbook to retrieve details for')

    def do_create_playbook(self, inp):
        args = {'playbook_name': '', 'playbook_type': '', 'playbook_timeout': '', 'playbook_config': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_playbook(**command_args)
        format_output('create_playbook', response)

    def help_create_playbook(self):
        print('\nCreate a new playbook with the given parameters.')
        print('\n--playbook_name=<string> - (required) a unique identifier to associate with the playbook')
        print('\n--playbook_type=<string> - (required) the source playbook type')
        print('\n--playbook_timeout=<string> - (required) the amount of time to wait for the playbook to finish')
        print('\n--playbook_config=<string> - (required) the playbook configuration definition')

    def do_delete_playbook(self, inp):
        args = {'playbook_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_playbook(**command_args)
        format_output('delete_playbook', response)

    def help_delete_playbook(self):
        print('\nDelete an existing playbook.')
        print('\n--playbook_name=<string> - (required) the name of the playbook to be deleted')

    def do_kill_playbook(self, inp):
        args = {'playbook_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.kill_playbook(**command_args)
        format_output('kill_playbook', response)

    def help_kill_playbook(self):
        print('\nForce quit a running playbook.')
        print('\n--playbook_name=<string> - (required) the name of the running playbook to be killed')

    def do_run_playbook(self, inp):
        args = {'playbook_name': '', 'playbook_type': '', 'playbook_config': '', 'playbook_timeout': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.run_playbook(**command_args)
        format_output('run_playbook', response)

    def help_run_playbook(self):
        print('\nRun a pre-configured or ad-hoc playbook.')
        print('\n--playbook_name=<string> - (required) the name of the playbook to run')
        print('\n--playbook_type=<string> - (optional) if running an ad-hoc playbook, specify the type of playbook to run')
        print('\n--playbook_config=<dict> - (optional) if running an ad-hoc playbook, specify the config to be used by the playbook')
        print('\n--playbook_timeout=<int> - (optional) if running an ad-hoc playbook, specify the playbook timeout')
    
    def do_get_playbook_results(self, inp):
        args = {'playbook_name': '', 'operator_command': '', 'start_time': '', 'end_time': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_playbook_results(**command_args)
        format_output('get_playbook_results', response)

    def help_get_playbook_results(self):
        print('\nGet all results for a given playbook.')
        print('\n--playbook_name=<string> - (required) retrieve results for the given playbook_name')
        print('\n--operator_command=<string> - (optional) filter the results by the specified operator_command')
        print('\n--start_time=<string> - (optional) retrieve results that occurred after the specified time')
        print('\n--end_time=<string> - (optional) retrieve results that occurred before the specified time')
    
    def do_tail_playbook_results(self, inp):
        args = {'playbook_name': ''}
        command_args = convert_input(args, inp)
        get_playbook_response = self.havoc_client.get_playbook(**command_args)
        if get_playbook_response['last_execution_time'] != 'None':
            command_args['start_time'] = get_playbook_response['last_execution_time']
        playbook_results = []
        try:
            while True:
                get_playbook_results_response = self.havoc_client.get_playbook_results(**command_args)
                if 'queue' in get_playbook_results_response:
                    queue = sorted(get_playbook_results_response['queue'], key=lambda d: d['run_time'])
                    for result in queue:
                        operator_command = result['operator_command']
                        if operator_command not in playbook_results:
                            playbook_results.append(operator_command)
                            command_output = json.loads(result['command_output'])
                            if 'outcome' in command_output:
                                outcome = command_output['outcome']
                            elif 'status' in command_output:
                                outcome = command_output['status']
                            else:
                                outcome = 'None'
                            print(f' - operator_command: {operator_command}, outcome: {outcome}')
                t.sleep(5)
        except KeyboardInterrupt:
            print('tail_playbook_results stopped.')

    def help_tail_playbook_results(self):
        print('\nFollow results for a given playbook.')
        print('\n--playbook_name=<string> - (required) the name of the playbook to retrieve results from')
    
    def do_list_playbook_types(self, inp):
        response = self.havoc_client.list_playbook_types()
        format_output('list_playbook_types', response)

    def help_list_playbook_types(self):
        print('\nList all existing playbook types.')

    def do_get_playbook_type(self, inp):
        args = {'playbook_type': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_playbook_type(**command_args)
        format_output('get_playbook_type', response)

    def help_get_playbook_type(self):
        print('\nGet details of a given playbook type.')
        print('\n--playbook_type=<string> - (required) the playbook type to retrieve details for')

    def do_create_playbook_type(self, inp):
        args = {'playbook_type': '', 'playbook_version': '', 'playbook_template': ''}
        command_args = convert_input(args, inp)
        playbook_template_file = command_args['playbook_template']
        with open(f'{playbook_template_file}', 'r') as f:
            playbook_template = f.read()
        command_args['playbook_template'] = playbook_template
        response = self.havoc_client.create_playbook_type(**command_args)
        format_output('create_playbook_type', response)

    def help_create_playbook_type(self):
        print('\nCreate a new playbook type with the given parameters.')
        print('\n--playbook_type=<string> - (required) a unique identifier to associate with the playbook type')
        print('\n--playbook_version=<string> - (required) the version number for the playbook type')
        print('\n--playbook_template=<string> - (required) the path (including file name) to the local configuration template file to use as the source when configuring a playbook of this type')

    def do_delete_playbook_type(self, inp):
        args = {'playbook_type': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_playbook_type(**command_args)
        format_output('delete_playbook_type', response)

    def help_delete_playbook_type(self):
        print('\nDelete an existing playbook type.')
        print('\n--playbook_type=<string> - (required) the playbook type to be deleted')

    def do_list_portgroups(self, inp):
        response = self.havoc_client.list_portgroups()
        format_output('list_portgroups', response)

    def help_list_portgroups(self):
        print('\nList all existing portgroups.')

    def do_get_portgroup(self, inp):
        args = {'portgroup_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_portgroup(**command_args)
        format_output('get_portgroup', response)

    def help_get_portgroup(self):
        print('\nGet details of a given portgroup.')
        print('\n--portgroup_name=<string> - (required) the name of the portgroup to retrieve details for')

    def do_create_portgroup(self, inp):
        args = {'portgroup_name': '', 'portgroup_description': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_portgroup(**command_args)
        format_output('create_portgroup', response)

    def help_create_portgroup(self):
        print('\nCreate a new portgroup with the given parameters.')
        print('\n--portgroup_name=<string> - (required) a unique identifier to associate with the portgroup')
        print('\n--portgroup_description=<string> - (required) a description containing the purpose of the portgroup')

    def do_update_portgroup_rule(self, inp):
        args = {'portgroup_name': '', 'portgroup_action': '', 'ip_ranges': '', 'port': '', 'ip_protocol': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.update_portgroup_rule(**command_args)
        format_output('update_portgroup_rule', response)

    def help_update_portgroup_rule(self):
        print('\nAdd or remove a rule to or from a given portgroup.')
        print('\n--portgroup_name=<string> - (required) the name of the portgroup to modify')
        print('\n--portgroup_action=[add|remove] - (required) indicate whether to add or remove a rule')
        print('\n--ip_ranges=<string> - (required) the IP address range that is allowed access by the portgroup rule')
        print('\n--port=<integer> - (required) the port number that the IP ranges are allowed to access')
        print('\n--ip_protocol=[udp|tcp|icmp] - (required) the IP protcols that IP ranges are allowed to use')

    def do_delete_portgroup(self, inp):
        args = {'portgroup_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_portgroup(**command_args)
        format_output('delete_portgroup', response)

    def help_delete_portgroup(self):
        print('\nDelete an existing portgroup.')
        print('\n--portgroup_name=<string> - (required) the name of the portgroup to be deleted')

    def do_list_domains(self, inp):
        response = self.havoc_client.list_domains()
        format_output('list_domains', response)

    def help_list_domains(self):
        print('\nList all existing domains.')

    def do_get_domain(self, inp):
        args = {'domain_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_domain(**command_args)
        format_output('get_domain', response)

    def help_get_domain(self):
        print('\nGet details of a given domain.')
        print('\n--domain_name=<string> - (required) the name of the domain to retrieve details for')

    def do_create_domain(self, inp):
        args = {'domain_name': '', 'hosted_zone': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_domain(**command_args)
        format_output('create_domain', response)

    def help_create_domain(self):
        print('\nCreate a new domain with the given parameters.')
        print('\n--domain_name=<string> - (required) the domain name associated with the domain to be created')
        print('\n--hosted_zone=<string> - (required) the zone ID of the hosted zone associated with the domain')

    def do_delete_domain(self, inp):
        args = {'domain_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_domain(**command_args)
        format_output('delete_domain', response)

    def help_delete_domain(self):
        print('\nDelete an existing domain.')
        print('\n--domain_name=<string> - (required) the name of the domain to be deleted')
    
    def do_list_listeners(self, inp):
        response = self.havoc_client.list_listeners()
        format_output('list_listeners', response)

    def help_list_listeners(self):
        print('\nList all existing listeners.')

    def do_get_listener(self, inp):
        args = {'listener_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_listener(**command_args)
        format_output('get_listener', response)

    def help_get_listener(self):
        print('\nGet details of a given listener.')
        print('\n--listener_name=<string> - (required) the name of the listener to retrieve details for')

    def do_create_listener(self, inp):
        args = {'listener_name': '', 'listener_config': '', 'task_name': '', 'portgroups': '', 'host_name': '',
                'domain_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_listener(**command_args)
        format_output('create_listener', response)

    def help_create_listener(self):
        print('\nCreate a new listener with the given parameters.')
        print('\n--listener_name=<string> - (required) the listener name associated with the listener to be created')
        print('\n--listener_config=<dict> - (required) a nested dictionary containing port numbers as primary keys and listener_type key/value (value can be HTTP or HTTPS) nested under each primary key')
        print('\n  Example: --listener_config={80: {"listener_type": "HTTP"}, 443: {"listener_type": "HTTPS"}}')
        print('\n--task_name=<string> - (required) the task to forward listener traffic to')
        print('\n--portgroups=<string> - (required) the portgroups to assign to the listener')
        print('\n--host_name=<string> - (optional) if using an FQDN, specify the host name to be set in DNS')
        print('\n--domain_name=<string> - (optional) if using an FQDN, specify the domain name to be set in DNS')

    def do_list_workspace_get_urls(self, inp):
        args = {'path': '', 'file_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_workspace_get_urls(**command_args)
        format_output('list_workspace_get_urls', response)

    def help_list_workspace_get_urls(self):
        print('\nList all existing workspace_get_urls.')
        print('\n--path=<string> - (optional) provide a path to list workspace_get_urls for a specific path - can be "shared/" or "upload/"')        
        print('\n--file_name=<string> - (optional) provide a file name to list workspace_get_urls for a specific file')

    def do_get_workspace_get_url(self, inp):
        args = {'path': '', 'file_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_workspace_get_url(**command_args)
        format_output('get_workspace_get_url', response)

    def help_get_workspace_get_url(self):
        print('\nGet details of a given workspace_get_url.')
        print('\n--path=<string> - (required) the path to the file to retrieve the workspace_get_url for - can be "shared/" or "upload/"')
        print('\n--file_name=<string> - (required) the name of the file to retrieve the workspace_get_url for')

    def do_create_workspace_get_url(self, inp):
        args = {'path': '', 'file_name': '', 'expiration': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_workspace_get_url(**command_args)
        format_output('create_workspace_get_url', response)

    def help_create_workspace_get_url(self):
        print('\nCreate a new workspace_get_url with the given parameters.')
        print('\n--path=<string> - (required) the path to the file to create the workspace_get_url for - can be "shared/" or "upload/"')
        print('\n--file_name=<string> - (required) the name of the file to create the workspace_get_url for')
        print('\n--expiration=<integer> - (optional) amount of time in seconds for the workspace_get_url to remain valid - defaults to 3600')

    def do_list_workspace_put_urls(self, inp):
        args = {'path': '', 'file_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_workspace_put_urls(**command_args)
        format_output('list_workspace_put_urls', response)

    def help_list_workspace_put_urls(self):
        print('\nList all existing workspace_put_urls.')
        print('\n--path=<string> - (optional) provide a path to list workspace_put_urls for a specific path - can be "shared/" or "upload/"')        
        print('\n--file_name=<string> - (optional) provide a file name to list workspace_get_urls for a specific file')

    def do_get_workspace_put_url(self, inp):
        args = {'path': '', 'file_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_workspace_put_url(**command_args)
        format_output('get_workspace_put_url', response)

    def help_get_workspace_put_url(self):
        print('\nGet details of a given workspace_put_url.')
        print('\n--path=<string> - (required) the path to the file to retrieve the workspace_put_url for - can be "shared/" or "upload/"')
        print('\n--file_name=<string> - (required) the name of the file to retrieve the workspace_put_url for')

    def do_create_workspace_put_url(self, inp):
        args = {'path': '', 'file_name': '', 'expiration': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.create_workspace_put_url(**command_args)
        format_output('create_workspace_put_url', response)

    def help_create_workspace_put_url(self):
        print('\nCreate a new workspace_put_url with the given parameters.')
        print('\n--path=<string> - (required) the path to the file to create the workspace_put_url for - can be "shared/" or "upload/"')
        print('\n--file_name=<string> - (required) the name of the file to create the workspace_put_url for')
        print('\n--expiration=<integer> - (optional) amount of time in seconds for the workspace_put_url to remain valid - defaults to 3600')
    
    def do_delete_listener(self, inp):
        args = {'listener_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.delete_listener(**command_args)
        format_output('delete_listener', response)

    def help_delete_listener(self):
        print('\nDelete an existing listener.')
        print('\n--listener_name=<string> - (required) the name of the listener to be deleted')

    def do_run_task(self, inp):
        args = {'task_name': '', 'task_type': '', 'task_host_name': '', 'task_domain_name': '', 'portgroups': '',
                'end_time': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.run_task(**command_args)
        format_output('run_task', response)

    def help_run_task(self):
        print('\nRun a task.')
        print('\n--task_name=<string> - (required) a unique identifier to associate with the task')
        print('\n--task_type=<string> - (required) the type of Attack Container to be executed')
        print('\n--task_host_name=<string> - (optional) a host name to associate with the task')
        print('\n--task_domain_name=<string> - (optional) a domain name to associate with the task')
        print('\n--portgroups=<string> - (optional) a comma separated list of portgroups to associate with the task')
        print('\n--end_time=<string> - (optional) terminate the task at the given time')

    def do_task_startup(self, inp):
        args = {'task_name': '', 'task_type': '', 'task_host_name': '', 'task_domain_name': '', 'portgroups': '',
                'end_time': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.task_startup(**command_args)
        format_output('task_startup', response)

    def help_task_startup(self):
        print('\nRun a task and wait for it to be ready.')
        print('\n--task_name=<string> - (required) a unique identifier to associate with the task')
        print('\n--task_type=<string> - (required) the type of Attack Container to be executed')
        print('\n--task_host_name=<string> - (optional) a host name to associate with the task')
        print('\n--task_domain_name=<string> - (optional) a domain name to associate with the task')
        print('\n--portgroups=<string> - (optional) a comma separated list of portgroups to associate with the task')
        print('\n--end_time=<string> - (optional) terminate the task at the given time')

    def do_task_shutdown(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.task_shutdown(**command_args)
        format_output('task_shutdown', response)

    def help_task_shutdown(self):
        print('\nCleanly shutdown a task.')
        print('\n--task_name=<string> - (required) a unique identifier to associate with the task')

    def do_instruct_task(self, inp):
        args = {'task_name': '', 'instruct_instance': '', 'instruct_command': '', 'instruct_args': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.instruct_task(**command_args)
        format_output('instruct_task', response)

    def help_instruct_task(self):
        print('\nSend instructions to a running task.')
        print('\n--task_name=<string> - (required) the name of the task you want to instruct')
        print('\n--instruct_instance=<string> - (required) a unique string to associate with the instruction')
        print('\n--instruct_command=<string> - (required) the command to send to the task')
        print('\n--instruct_args=<dict> - (optional) a dictionary of arguments to pass with the command')

    def do_interact_with_task(self, inp):
        args = {'task_name': '', 'instruct_command': '', 'instruct_instance': '', 'instruct_args': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.interact_with_task(**command_args)
        format_output('interact_with_task', response)

    def help_interact_with_task(self):
        print('\nInteract with a running task and wait for instruction results.')
        print('\n--task_name=<string> - (required) the name of the task you want to instruct')
        print('\n--instruct_command=<string> - (required) the command to send to the task')
        print('\n--instruct_instance=<string> - (optional) a unique string to associate with the interaction')
        print('\n--instruct_args=<dict> - (optional) a dictionary of arguments to pass with the command')

    def do_get_task_results(self, inp):
        args = {'task_name': '', 'instruct_command': '', 'instruct_instance': '', 'start_time': '', 'end_time': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_task_results(**command_args)
        format_output('get_task_results', response)

    def help_get_task_results(self):
        print('\nGet results for a given task, filtered by instruct_command, instruct_instance, start_time and end_time.')
        print('\n--task_name=<string> - (required) the name of the task to retrieve results from')
        print('\n--instruct_instance=<string> - (optional) filter the results by the specified instruct_instance')
        print('\n--instruct_command=<string> - (optional) filter the results by the specified instruct_command')
        print('\n--start_time=<string> - (optional) retrieve results that occurred after the specified time')
        print('\n--end_time=<string> - (optional) retrieve results that occurred before the specified time')

    def do_wait_for_c2(self, inp):
        args = {'task_name': '', 'time_skew': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.wait_for_c2(**command_args)
            format_output('wait_for_c2', response)
        except KeyboardInterrupt:
            print('wait_for_c2 stopped.')

    def help_wait_for_c2(self):
        print('\nWait for a task to receive a C2 agent or session connection.')
        print('\n--task_name=<string> - (required) the name of the task that the C2 agent or session will to connect to')
        print('\n--time_skew=<string> - (optional) the number of minutes to skew the time window by - defaults to 2')
        print('Note - press Ctrl-C to cancel the wait_for_c2 operation.')

    def do_wait_for_idle_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.wait_for_idle_task(**command_args)
            format_output('wait_for_idle_task', response)
        except KeyboardInterrupt:
            print('wait_for_idle_task stopped.')

    def help_wait_for_idle_task(self):
        print('\nWait for a task to become idle.')
        print('\n--task_name=<string> - (required) the name of the task to wait on')
        print('Note - press Ctrl-C to cancel the wait_for_idle_task operation.')
    
    def do_list_empire_agents(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_empire_agents(**command_args)
        format_output('list_empire_agents', response)
    
    def help_list_empire_agents(self):
        print('\nGet a list of Empire agents that are connected to the given PowerShell Empire task.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task to query for connected Empire agents.')
    
    def do_kill_empire_agent(self, inp):
        args = {'task_name': '', 'agent_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.kill_empire_agent(**command_args)
        format_output('kill_empire_agent', response)
    
    def help_kill_empire_agent(self):
        print('\nKill an Empire agent that is connected to the given PowerShell Empire task.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task that the Empire agent is connected to.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent to kill.')
    
    def do_verify_empire_agent(self, inp):
        args = {'task_name': '', 'agent_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.verify_empire_agent(**command_args)
        if response:
            format_output('verify_empire_agent', response)
        else:
            format_output('verify_empire_agent', {command_args['agent_name']: 'agent not found'})

    def help_verify_empire_agent(self):
        print('\nVerify the existence of an Empire agent.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task to check for an Empire agent.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent to check for.')
    
    def do_execute_empire_agent_shell_command(self, inp):
        args = {'task_name': '', 'agent_name': '', 'command': '', 'wait_for_results': '', 'beginning_string': '', 'completion_string': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.execute_empire_agent_shell_command(**command_args)
            format_output('execute_empire_agent_shell_command', response)
        except KeyboardInterrupt:
            print('execute_empire_agent_shell_command stopped.')
    
    def help_execute_empire_agent_shell_command(self):
        print('\nExecute a shell command on an Empire agent.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task that the Empire agent is connected to.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent that should execute the command.')
        print('\n--command=<string> - (required) the command to execute.')
        print('\n--wait_for_results=<boolean> - (optional) indicate whether to wait for the command results. Defaults to True. If set to False, a task ID is returned instead of the shell command results.')
        print('\n--beginning_string=<string> - (optional) a string that should be present in the results to indicate the beginning of the command results. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')
        print('\n--completion_string=<string> - (optional) a string that should be present in the results to indicate the command is done. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')
        print('\n**Note that the --completion_string parameter can be passed by itself but if the --beginning_string parameter is present, it must also be accompanied by a --completion_string. When a using the --beginning_string and --completion_string parameters, only results between and including the strings will be returned.')

    def do_execute_empire_agent_module(self, inp):
        args = {'task_name': '', 'agent_name': '', 'module': '', 'module_args': '', 'wait_for_results': '', 'beginning_string': '', 'completion_string': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.execute_empire_agent_module(**command_args)
            format_output('execute_empire_agent_module', response)
        except KeyboardInterrupt:
            print('execute_empire_agent_module stopped.')
    
    def help_execute_empire_agent_module(self):
        print('\nExecute a module on an Empire agent.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task that the Empire agent is connected to.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent that should execute the module.')
        print('\n--module=<string> - (required) the Empire agent module to execute.')
        print('\n--module_args=<dict> - (optional) a dictionary of arguments to pass to the module.')
        print('\n--wait_for_results=<boolean> - (optional) indicate whether to wait for the module results. Defaults to True. If set to False, a task ID is returned instead of the module results.')
        print('\n--beginning_string=<string> - (optional) a string that should be present in the results to indicate the beginning of the module results. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')
        print('\n--completion_string=<string> - (optional) a string that should be present in the results to indicate the module is done. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')
        print('\n**Note that the --completion_string parameter can be passed by itself but if the --beginning_string parameter is present, it must also be accompanied by a --completion_string. When a using the --beginning_string and --completion_string parameters, only results between and including the strings will be returned.')

    def do_get_empire_agent_task_ids(self, inp):
        args = {'task_name': '', 'agent_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_empire_agent_task_ids(**command_args)
        format_output('get_empire_agent_task_ids', response)

    def help_get_empire_agent_task_ids(self):
        print('\nGet a list of task IDs associated with executed Empire agent shell commands and modules.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task that the Empire agent is connected to.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent to get task IDs from.')
    
    def do_get_empire_agent_results(self, inp):
        args = {'task_name': '', 'agent_name': '', 'task_id': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.get_empire_agent_results(**command_args)
        format_output('get_empire_agent_results', response)
    
    def help_get_empire_agent_results(self):
        print('\nGet the results of an executed Empire agent shell command or module.')
        print('\n--task_name=<string> - (required) the name of the PowerShell Empire task that the Empire agent is connected to.')
        print('\n--agent_name=<string> - (required) the name of the Empire agent to get shell command or module results from.')
        print('\n--task_id=<string> - (required) the task ID assigned to the shell command or module to get results from.')
    
    def do_list_metasploit_sessions(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.list_metasploit_sessions(**command_args)
        format_output('list_metasploit_sessions', response)
    
    def help_list_metasploit_sessions(self):
        print('\nGet a list of Metasploit sessions that are connected to the given Metasploit task.')
        print('\n--task_name=<string> - (required) the name of the Metasploit task to query for connected sessions.')
    
    def do_kill_metasploit_session(self, inp):
        args = {'task_name': '', 'session_id': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.kill_metasploit_session(**command_args)
        format_output('kill_metasploit_session', response)
    
    def help_kill_metasploit_session(self):
        print('\nKill a Metasploit session that is connected to the given Metasploit task.')
        print('\n--task_name=<string> - (required) the name of the Metasploit task that the session is connected to.')
        print('\n--session_id=<string> - (required) the ID of the Metasploit session to kill.')
    
    def do_verify_metasploit_session(self, inp):
        args = {'task_name': '', 'session_id': ''}
        command_args = convert_input(args, inp)
        response = self.havoc_client.verify_metasploit_session(**command_args)
        if response:
            format_output('verify_metasploit_session', response)
        else:
            format_output('verify_metasploit_session', {command_args['session_id']: 'Metasploit session not found'})

    def help_verify_metasploit_session(self):
        print('\nVerify the existence of a Metasploit session on a given task.')
        print('\n--task_name=<string> - (required) the name of the Metasploit task to check for a Metasploit session.')
        print('\n--session_id=<string> - (required) the ID of the Metasploit session to check for.')
    
    def do_run_metasploit_session_command(self, inp):
        args = {'task_name': '', 'session_id': '', 'session_command': '', 'wait_time': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.run_metasploit_session_command(**command_args)
            format_output('run_metasploit_session_command', response)
        except KeyboardInterrupt:
            print('run_metasploit_session_command stopped.')
    
    def help_run_metasploit_session_command(self):
        print('\nExecute a command on a Metasploit session.')
        print('\n--task_name=<string> - (required) the name of the Metasploit task that the Metasploit session is connected to.')
        print('\n--session_id=<string> - (required) the ID of the Metasploit session that should execute the command.')
        print('\n--session_command=<string> - (required) the session command to execute.')
        print('\n--wait_time=<integer> - (optional) amount of time to wait for the command to return results.')

    def do_run_metasploit_session_shell_command(self, inp):
        args = {'task_name': '', 'session_id': '', 'session_shell_command': '', 'wait_time': ''}
        command_args = convert_input(args, inp)
        try:
            response = self.havoc_client.run_metasploit_session_shell_command(**command_args)
            format_output('run_metasploit_session_shell_command', response)
        except KeyboardInterrupt:
            print('run_metasploit_session_shell_command stopped.')
    
    def help_run_metasploit_session_shell_command(self):
        print('\nExecute a shell command on a Metasploit session.')
        print('\n--task_name=<string> - (required) the name of the Metasploit task that the Metasploit session is connected to.')
        print('\n--session_id=<string> - (required) the ID of the Metasploit session that should execute the shell command.')
        print('\n--session_shell_command=<string> - (required) the session shell command to execute.')
        print('\n--wait_time=<integer> - (optional) amount of time to wait for the command to return results.')
    
    def default(self, inp):
        if inp == 'x' or inp == 'q':
            return self.do_exit(inp)

    do_EOF = do_exit
    help_EOF = help_exit


