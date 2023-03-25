import json, base64, zlib, datetime, argparse, pprint
from configparser import ConfigParser

import havoc

init_parser = argparse.ArgumentParser(description='havoc playbook - PowerShell Empire Builtin Host Recon')

init_parser.add_argument('--profile', help='Use a specific profile from your credential file')
init_args = init_parser.parse_args()

profile = init_args.profile

def load_havoc_profiles():
    # Load the ./HAVOC profiles file
    havoc_profiles = ConfigParser()
    havoc_profiles.read('.havoc/profiles')
    return havoc_profiles

# Get api_key and secret_key
havoc_profiles = load_havoc_profiles()
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

h = havoc.Connect(api_region, api_domain_name, api_key, secret, api_version=1)

# Configure pretty print for displaying output.
pp = pprint.PrettyPrinter(indent=4)

# Create a config parser and setup config parameters
config = ConfigParser(allow_no_value=True)
config.optionxform = str
config.read('havoc_scripts/activity_report/activity_report.ini')

playbooks = config.get('playbook_report', 'playbook_names', fallback=None)
playbook_start_time = config.get('playbook_report', 'start_time')
playbook_end_time = config.get('playbook_report', 'end_time')
if playbooks:
    playbooks = playbooks.split(',')

tasks = config.get('task_report', 'task_names', fallback=None)
task_start_time = config.get('task_report', 'start_time')
task_end_time = config.get('task_report', 'end_time')
if tasks:
    tasks = tasks.split(',')

if tasks:
    for task in tasks:
        task = task.strip()
        print(f'\nGetting results for task {task}\n')
        print('+------------------------------------------------------------------+')
        get_task_results = h.get_task_results(task, start_time=task_start_time, end_time=task_end_time)
        task_id_records = []
        for entry in get_task_results['queue']:
            run_time = datetime.datetime.fromtimestamp(int(entry['run_time']))
            instruct_command = entry['instruct_command']
            instruct_command_args = entry['instruct_args']
            instruct_command_results = json.loads(entry['instruct_command_output'])
            if instruct_command != 'get_shell_command_results':
                if 'message' in instruct_command_results and 'taskID' in instruct_command_results['message']:
                    task_id = instruct_command_results['message']['taskID']
                    task_id_records.append(task_id)
                print(f'\n\nTask instruction: {instruct_command}')
                print(f'Task instruction run time: {run_time}')
                print('Task instruction arguments:')
                for k,v in instruct_command_args.items():
                    print(f'\t{k}: {v}')
            if instruct_command_results:
                if instruct_command != 'get_shell_command_results':
                    print('\nTask instruction results:')
                for k,v in instruct_command_results.items():
                    if instruct_command == 'get_shell_command_results' and k == 'results':
                        results_data = json.loads(zlib.decompress(base64.b64decode(v.encode())).decode())
                        for r in results_data:
                            if r['taskID'] in task_id_records:
                                command_output = r['results']
                                if command_output is not None and 'Job started:' not in command_output:
                                    print('\nAgent shell command results:')
                                    print(f'{command_output}')
                                    task_id_records.remove(r['taskID'])
                    if instruct_command != 'get_shell_command_results':
                        print(f'{k}: {v}')

if playbooks:
    for playbook in playbooks:
        playbook = playbook.strip()
        print(f'\nGetting results for playbook {playbook}\n')
        print('+------------------------------------------------------------------+')
        playbook_results = h.get_playbook_results(playbook, start_time=playbook_start_time, end_time=playbook_end_time)
        if 'queue' in playbook_results:
            for entry in playbook_results['queue']:
                run_time = datetime.datetime.fromtimestamp(int(entry['run_time']))
                operator_command = entry['operator_command']
                command_args = entry['command_args']
                command_output = json.loads(entry['command_output'])
                print(f'\nOperator command run time: {run_time}')
                print(f'Operator command: {operator_command}')
                pp.print(f'Operator command args: {command_args}')
                if command_output:
                    if 'outcome' in command_output:
                        operator_command_outcome = command_output['outcome']
                        print(f'Operator command outcome: {operator_command_outcome}')
                    if 'details' in command_output and command_output['details'] is not None:
                        try:
                            details = json.loads(command_output['details'])
                            print('Operator command output details:')
                            pp.pprint(details)
                        except:
                            print('Operator command output details:')
                            pp.pprint(command_output['details'])
