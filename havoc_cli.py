#!/usr/bin/env python3

import re
import ast
import json
from configparser import ConfigParser
from cmd2 import Cmd
import havoc

# Load the ./HAVOC configuration file
havoc_profiles = ConfigParser()
havoc_profiles.read('.havoc/profiles')

profile = None

# Get api_key and secret_key
if profile:
    api_key = havoc_profiles.get(profile, 'API_KEY')
    secret = havoc_profiles.get(profile, 'SECRET')
    api_region = havoc_profiles.get(profile, 'API_REGION')
    api_domain_name = havoc_profiles.get(profile, 'API_DOMAIN_NAME')
else:
    api_key = havoc_profiles.get('default', 'API_KEY')
    secret = havoc_profiles.get('default', 'SECRET')
    api_region = havoc_profiles.get('default', 'API_REGION')
    api_domain_name = havoc_profiles.get('default', 'API_DOMAIN_NAME')

h = havoc.Connect(api_region, api_domain_name, api_key, secret)


def convert_input(args, inp):
    line = inp.split('--')
    for l in line:
        arg = re.search('([^=]+)=(.*)', l)
        if arg:
            if arg.group(1) in args and arg.group(1) != 'instruct_args' and arg.group(1) != 'portgroups':
                args[arg.group(1)] = arg.group(2).strip()
            if arg.group(1) in args and arg.group(1) == 'instruct_args':
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

    prompt = 'havoc> '
    intro = "havoc CLI - Type ? to list commands"

    def emptyline(self):
        pass

    def do_exit(self, inp):
        print('Bye')
        return True

    def help_exit(self):
        print('\nExit the application. Shorthand: Ctrl-D.\n')

    def do_get_deployment(self, inp):
        get_deployment_response = h.get_deployment()
        format_output('get_deployment', get_deployment_response)

    def help_get_deployment(self):
        print('\nGet details about the ./HAVOC deployment.')

    def do_list_tasks(self, inp):
        args = {'task_status': '', 'task_name_contains': ''}
        command_args = convert_input(args, inp)
        list_tasks_response = h.list_tasks(**command_args)
        format_output('list_tasks', list_tasks_response)

    def help_list_tasks(self):
        print('\nList tasks.')
        print('\n--task_name_contains=<string> - (optional) only list tasks that contain the provided value in the task name')
        print('\n--task_status=(all|running|starting|idle|busy|terminated) - (optional) only list tasks whose status matches the provided value (defaults to "running," which includes tasks with a status of "starting," "idle," or "busy")')

    def do_get_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        get_task_response = h.get_task(**command_args)
        format_output('get_task', get_task_response)

    def help_get_task(self):
        print('\nGet details of a given task.')
        print('\n--task_name=<string> - (required) the name of the task to retrieve details for')

    def do_kill_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        kill_task_response = h.kill_task(**command_args)
        format_output('kill_task', kill_task_response)

    def help_kill_task(self):
        print('\nForce quit a running task.')
        print('\n--task_name=<string> - (required) the name of the task to kill')

    def do_verify_task(self, inp):
        args = {'task_name': '', 'task_type': ''}
        command_args = convert_input(args, inp)
        verify_task_response = h.verify_task(**command_args)
        if verify_task_response:
            format_output('verify_task', verify_task_response)
        else:
            format_output('verify_task', {command_args['task_name']: 'task not found'})

    def help_verify_task(self):
        print('\nCheck for the existence of a task with the given task_name and task_type')
        print('\n--task_name=<string> - (required) the name of the task to verify')
        print('\n--task_type=<string> - (required) the type of task that the verified task should be')

    def do_list_task_types(self, inp):
        list_task_types_response = h.list_task_types()
        format_output('list_task_types', list_task_types_response)

    def help_list_task_types(self):
        print('\nList all available task types.')

    def do_get_task_type(self, inp):
        args = {'task_type': ''}
        command_args = convert_input(args, inp)
        get_task_type_response = h.get_task_type(**command_args)
        format_output('get_task_type', get_task_type_response)

    def help_get_task_type(self):
        print('\nGet details of a given task type.')
        print('\n--task_type=<string> - (required) the name of the task type to get')

    def do_create_task_type(self, inp):
        args = {'task_type': '', 'task_version': '', 'source_image': '', 'capabilities': '', 'cpu': '', 'memory': ''}
        command_args = convert_input(args, inp)
        create_task_type_response = h.create_task_type(**command_args)
        format_output('create_task_type', create_task_type_response)

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
        delete_task_type_response = h.delete_task_type(**command_args)
        format_output('delete_task_type', delete_task_type_response)

    def help_delete_task_type(self):
        print('\nDelete the given task type.')
        print('\n--task_type=<string> - (required) the name of the task type to delete')

    def do_list_users(self, inp):
        list_users_response = h.list_users()
        format_output('list_users', list_users_response)

    def help_list_users(self):
        print('\nList all ./havoc users.')

    def do_get_user(self, inp):
        args = {'user_id': ''}
        command_args = convert_input(args, inp)
        get_user_response = h.get_user(**command_args)
        format_output('get_user', get_user_response)

    def help_get_user(self):
        print('\nGet details of a given user.')
        print('\n--user_id=<string> - (required) the ID of the user to get')

    def do_create_user(self, inp):
        args = {'user_id': '', 'admin': ''}
        command_args = convert_input(args, inp)
        create_user_response = h.create_user(**command_args)
        format_output('create_user', create_user_response)

    def help_create_user(self):
        print('\nCreate a new user with the given parameters.')
        print('\n--user_id=<string> - (required) a unique identifier to associate with the user')
        print('\n--admin=[yes|no] - (optional) specify whether or not the user has admin privileges (defaults to no)')

    def do_update_user(self, inp):
        args = {'user_id': '', 'new_user_id': '', 'admin': '', 'reset_keys': ''}
        command_args = convert_input(args, inp)
        update_user_response = h.update_user(**command_args)
        format_output('update_user', update_user_response)

    def help_update_user(self):
        print('\nUpdate an existing user.')
        print('\n--user_id=<string> - (required) the user_id associated with the user to make updates to')
        print('\n--new_user_id=<string> - (optional) a new unique identifier to associate with the user')
        print('\n--admin=[yes|no] - (optional) - add or remove admin privileges for the user (defaults to no change)')
        print('\n--reset_keys=yes - (optional) - forces a reset of the user\'s API key and secret (if not present, '
              'keys are not changed)')

    def do_delete_user(self, inp):
        args = {'user_id': ''}
        command_args = convert_input(args, inp)
        delete_user_response = h.delete_user(**command_args)
        format_output('delete_user', delete_user_response)

    def help_delete_user(self):
        print('\nDelete an existing user.')
        print('\n--user_id=<string> - (required) the user_id of the user to be deleted')

    def do_list_files(self, inp):
        list_files_response = h.list_files()
        format_output('list_files', list_files_response)

    def help_list_files(self):
        print('\nList all files in the shared workspace.')

    def do_get_file(self, inp):
        args = {'file_name': '', 'file_path': ''}
        command_args = convert_input(args, inp)
        file_path = command_args['file_path']
        file_name = command_args['file_name']
        f = open(f'{file_path}/{file_name}', 'wb')
        del command_args['file_path']
        get_file_response = h.get_file(**command_args)
        file_contents = get_file_response['file_contents']
        f.write(file_contents)
        f.close()
        del get_file_response['file_contents']
        get_file_response['file_path'] = file_path
        format_output('get_file', get_file_response)

    def help_get_file(self):
        print('\nDownload a file from the shared workspace.')
        print('\n--file_name=<string> - (required) the name of the file to download.')
        print('\n--file_path=<string> - (required) the path to the local directory to download the file to')

    def do_create_file(self, inp):
        args = {'file_name': '', 'file_path': ''}
        command_args = convert_input(args, inp)
        file_path = command_args['file_path']
        file_name = command_args['file_name']
        f = open(f'{file_path}/{file_name}', 'rb')
        raw_file = f.read()
        command_args['raw_file'] = raw_file
        del command_args['file_path']
        create_file_response = h.create_file(**command_args)
        format_output('create_file', create_file_response)

    def help_create_file(self):
        print('\nUpload a file to the shared workspace.')
        print('\n--file_name=<string> - (required) the name of the file to upload.')
        print('\n--file_path=<string> - (required) the path to the local directory where the file resides')

    def do_delete_file(self, inp):
        args = {'file_name': ''}
        command_args = convert_input(args, inp)
        delete_file_response = h.delete_file(**command_args)
        format_output('delete_file', delete_file_response)

    def help_delete_file(self):
        print('\nDelete a file in the shared workspace.')
        print('\n--file_name=<string> - (required) the name of the file to be deleted.')

    def do_list_portgroups(self, inp):
        list_portgroups_response = h.list_portgroups()
        format_output('list_portgroups', list_portgroups_response)

    def help_list_portgroups(self):
        print('\nList all existing portgroups.')

    def do_get_portgroup(self, inp):
        args = {'portgroup_name': ''}
        command_args = convert_input(args, inp)
        get_portgroup_response = h.get_portgroup(**command_args)
        format_output('get_portgroup', get_portgroup_response)

    def help_get_portgroup(self):
        print('\nGet details of a given portgroup.')
        print('\n--portgroup_name=<string> - (required) the name of the portgroup to retrieve details for')

    def do_create_portgroup(self, inp):
        args = {'portgroup_name': '', 'portgroup_description': ''}
        command_args = convert_input(args, inp)
        create_portgroup_response = h.create_portgroup(**command_args)
        format_output('create_portgroup', create_portgroup_response)

    def help_create_portgroup(self):
        print('\nCreate a new portgroup with the given parameters.')
        print('\n--portgroup_name=<string> - (required) a unique identifier to associate with the portgroup')
        print('\n--porgroup_description=<string> - (required) a description containing the purpose of the portgroup')

    def do_update_portgroup_rule(self, inp):
        args = {'portgroup_name': '', 'portgroup_action': '', 'ip_ranges': '', 'port': '', 'ip_protocol': ''}
        command_args = convert_input(args, inp)
        update_portgroup_rule_response = h.update_portgroup_rule(**command_args)
        format_output('update_portgroup_rule', update_portgroup_rule_response)

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
        delete_portgroup_response = h.delete_portgroup(**command_args)
        format_output('delete_portgroup', delete_portgroup_response)

    def help_delete_portgroup(self):
        print('\nDelete an existing portgroup.')
        print('\n--portgroup_name=<string> - (required) the name of the portgroup to be deleted')

    def do_list_domains(self, inp):
        list_domains_response = h.list_domains()
        format_output('list_domains', list_domains_response)

    def help_list_domains(self):
        print('\nList all existing domains.')

    def do_get_domain(self, inp):
        args = {'domain_name': ''}
        command_args = convert_input(args, inp)
        get_domain_response = h.get_domain(**command_args)
        format_output('get_domain', get_domain_response)

    def help_get_domain(self):
        print('\nGet details of a given domain.')
        print('\n--domain_name=<string> - (required) the name of the domain to retrieve details for')

    def do_create_domain(self, inp):
        args = {'domain_name': '', 'hosted_zone': ''}
        command_args = convert_input(args, inp)
        create_domain_response = h.create_domain(**command_args)
        format_output('create_domain', create_domain_response)

    def help_create_domain(self):
        print('\nCreate a new domain with the given parameters.')
        print('\n--domain_name=<string> - (required) the domain name associated with the domain to be created')
        print('\n--hosted_zone=<string> - (required) the zone ID of the hosted zone associated with the domain')

    def do_delete_domain(self, inp):
        args = {'domain_name': ''}
        command_args = convert_input(args, inp)
        delete_domain_response = h.delete_domain(**command_args)
        format_output('delete_domain', delete_domain_response)

    def help_delete_domain(self):
        print('\nDelete an existing domain.')
        print('\n--domain_name=<string> - (required) the name of the domain to be deleted')

    def do_run_task(self, inp):
        args = {'task_name': '', 'task_type': '', 'task_host_name': '', 'task_domain_name': '', 'portgroups': '',
                'end_time': ''}
        command_args = convert_input(args, inp)
        run_task_response = h.run_task(**command_args)
        format_output('run_task', run_task_response)

    def help_run_task(self):
        print('\nRun a ./havoc Attack Container as an ECS task.')
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
        task_startup_response = h.task_startup(**command_args)
        format_output('task_startup', task_startup_response)

    def help_task_startup(self):
        print('\nRun a ./havoc Attack Container as an ECS task and wait for task to be ready.')
        print('\n--task_name=<string> - (required) a unique identifier to associate with the task')
        print('\n--task_type=<string> - (required) the type of Attack Container to be executed')
        print('\n--task_host_name=<string> - (optional) a host name to associate with the task')
        print('\n--task_domain_name=<string> - (optional) a domain name to associate with the task')
        print('\n--portgroups=<string> - (optional) a comma separated list of portgroups to associate with the task')
        print('\n--end_time=<string> - (optional) terminate the task at the given time')

    def do_task_shutdown(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        task_shutdown_response = h.task_shutdown(**command_args)
        format_output('task_shutdown', task_shutdown_response)

    def help_task_shutdown(self):
        print('\nCleanly shutdown a ./havoc Container.')
        print('\n--task_name=<string> - (required) a unique identifier to associate with the task')

    def do_instruct_task(self, inp):
        args = {'task_name': '', 'instruct_instance': '', 'instruct_command': '', 'instruct_args': ''}
        command_args = convert_input(args, inp)
        instruct_task_response = h.instruct_task(**command_args)
        format_output('instruct_task', instruct_task_response)

    def help_instruct_task(self):
        print('\nSend instructions to a running task.')
        print('\n--task_name=<string> - (required) the name of the task you want to instruct')
        print('\n--instruct_instance=<string> - (required) a unique string to associate with the instruction')
        print('\n--instruct_command=<string> - (required) the command to send to the task')
        print('\n--instruct_args=<dict> - (optional) a dictionary of arguments to pass with the command')

    def do_interact_with_task(self, inp):
        args = {'task_name': '', 'instruct_command': '', 'instruct_instance': '', 'instruct_args': ''}
        command_args = convert_input(args, inp)
        interact_with_task_response = h.interact_with_task(**command_args)
        format_output('interact_with_task', interact_with_task_response)

    def help_interact_with_task(self):
        print('\nInteract with a running task and wait for instruction results.')
        print('\n--task_name=<string> - (required) the name of the task you want to instruct')
        print('\n--instruct_command=<string> - (required) the command to send to the task')
        print('\n--instruct_instance=<string> - (optional) a unique string to associate with the interaction')
        print('\n--instruct_args=<dict> - (optional) a dictionary of arguments to pass with the command')

    def do_get_task_results(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        get_task_results_response = h.get_task_results(**command_args)
        format_output('get_task_results', get_task_results_response)

    def help_get_task_results(self):
        print('\nGet all instruct_command results for a given task.')
        print('\n--task_name=<string> - (required) the name of the task to retrieve results from')

    def do_get_filtered_task_results(self, inp):
        args = {'task_name': '', 'instruct_command': '', 'instruct_instance': ''}
        command_args = convert_input(args, inp)
        get_filtered_task_results_response = h.get_filtered_task_results(**command_args)
        format_output('get_filtered_task_results', get_filtered_task_results_response)

    def help_get_filtered_task_results(self):
        print('\nGet results for a given task filtered by instruct_command and/or instruct_instance.')
        print('\n--task_name=<string> - (required) the name of the task to retrieve results from')
        print('\n--instruct_instance=<string> - (optional) the instruct_instance to retrieve results for')
        print('\n--instruct_command=<string> - (optional) the command to retrieve results for')

    def do_wait_for_c2(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        try:
            wait_for_c2_response = h.wait_for_c2(**command_args)
            format_output('wait_for_c2', wait_for_c2_response)
        except KeyboardInterrupt:
            print('wait_for_c2 stopped.')

    def help_wait_for_c2(self):
        print('\nWait for a task to receive a C2 agent or session connection.')
        print('\n--task_name=<string> - (required) the name of the task that the C2 agent or session will to connect to')
        print('Note - press Ctrl-C to cancel the wait_for_c2 operation.')

    def do_wait_for_idle_task(self, inp):
        args = {'task_name': ''}
        command_args = convert_input(args, inp)
        try:
            wait_for_idle_task_response = h.wait_for_idle_task(**command_args)
            format_output('wait_for_idle_task', wait_for_idle_task_response)
        except KeyboardInterrupt:
            print('wait_for_idle_task stopped.')

    def help_wait_for_idle_task(self):
        print('\nWait for a task to become idle.')
        print('\n--task_name=<string> - (required) the name of the task to wait on')
        print('Note - press Ctrl-C to cancel the wait_for_idle_task operation.')
    
    def do_verify_agent(self, inp):
        args = {'task_name': '', 'agent_name': ''}
        command_args = convert_input(args, inp)
        verify_agent_response = h.verify_agent(**command_args)
        if verify_agent_response:
            format_output('verify_agent', verify_agent_response)
        else:
            format_output('verify_agent', {command_args['agent_name']: 'agent not found'})
    
    def help_verify_agent(self):
        print('\nVerify the existence of a C2 agent.')
        print('\n--task_name=<string> - (required) the name of the task to check for an agent.')
        print('\n--agent_name=<string> - (required) the name of the agent to check for.')
    
    def do_execute_agent_shell_command(self, inp):
        args = {'task_name': '', 'agent_name': '', 'command': '', 'wait_for_results': '', 'completion_string': ''}
        command_args = convert_input(args, inp)
        try:
            execute_agent_shell_command_response = h.execute_agent_shell_command(**command_args)
            format_output('execute_agent_shell_command', execute_agent_shell_command_response)
        except KeyboardInterrupt:
            print('execute_agent_shell_command stopped.')
    
    def help_execute_agent_shell_command(self):
        print('\nExecute a shell command on a C2 agent.')
        print('\n--task_name=<string> - (required) the name of the task hosting the agent to execute a command on.')
        print('\n--agent_name=<string> - (required) the name of the agent that should execute the command.')
        print('\n--command=<string> - (required) the command to execute.')
        print('\n--wait_for_results=<boolean> - (optional) indicate whether to wait for the command results. Defaults to True. If set to False, a task ID is returned instead of the shell command results.')
        print('\n--completion_string=<string> - (optional) a string that should be present in the results to indicate the command is done. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')

    def do_execute_agent_module(self, inp):
        args = {'task_name': '', 'agent_name': '', 'module': '', 'module_args': '', 'wait_for_results': '', 'completion_string': ''}
        command_args = convert_input(args, inp)
        try:
            execute_agent_module_response = h.execute_agent_module(**command_args)
            format_output('execute_agent_module', execute_agent_module_response)
        except KeyboardInterrupt:
            print('execute_agent_module stopped.')
    
    def help_execute_agent_module(self):
        print('\nExecute a module on a C2 agent.')
        print('\n--task_name=<string> - (required) the name of the task hosting the agent to execute a module on.')
        print('\n--agent_name=<string> - (required) the name of the agent that should execute the module.')
        print('\n--module=<string> - (required) the agent module to execute.')
        print('\n--module_args=<dict> - (optional) a dictionary of arguments to pass to the module.')
        print('\n--wait_for_results=<boolean> - (optional) indicate whether to wait for the module results. Defaults to True. If set to False, a task ID is returned instead of the module results.')
        print('\n--completion_string=<string> - (optional) a string that should be present in the results to indicate the module is done. If not specified results are returned as soon as any results data becomes available, which may lead to incomplete results being returned.')

    def do_get_agent_results(self, inp):
        args = {'task_name': '', 'agent_name': '', 'task_id': ''}
        command_args = convert_input(args, inp)
        get_agent_results_response = h.get_agent_results(**command_args)
        format_output('get_agent_results', get_agent_results_response)
    
    def help_get_agent_results(self):
        print('\nGet the results of an executed agent shell command or module.')
        print('\n--task_name=<string> - (required) the name of the task hosting the agent to get results from.')
        print('\n--agent_name=<string> - (required) the name of the agent to get shell command or module results from.')
        print('\n--task_id=<string> - (required) the task ID assigned to the shell command or module to get results from.')
    
    def default(self, inp):
        if inp == 'x' or inp == 'q':
            return self.do_exit(inp)

    do_EOF = do_exit
    help_EOF = help_exit

if __name__ == '__main__':

    print('         _ _         _    _  _____   ______ ')
    print('        / | |      \| |  | |/ ___ \ / _____)')
    print('       / /| |__  /  \ |  | | |   | | /      ')
    print('      / / |  __)/ /\ \ \/ /| |   | | |      ')
    print('     / /  | |  / |__| \  / | |___| | \_____ ')
    print('  ()/_/   |_| / ______|\/   \_____/ \______)')

    havoc_cmd = HavocCMD()
    havoc_cmd.cmdloop()


