import os, json, base64, zlib, datetime, argparse, pprint
from configparser import ConfigParser

import havoc

init_parser = argparse.ArgumentParser(description='havoc playbook - PowerShell Empire Builtin Host Recon')

init_parser.add_argument('--profile', help='Use a specific profile from your credential file')
init_args = init_parser.parse_args()

profile = init_args.profile

# Load the ./HAVOC configuration file
havoc_config = ConfigParser()
havoc_config_file = os.path.expanduser('~/.havoc/config')
havoc_config.read(havoc_config_file)

# Get api_key and secret_key
if profile:
    api_key = havoc_config.get(profile, 'API_KEY')
    secret = havoc_config.get(profile, 'SECRET')
    api_region = havoc_config.get(profile, 'API_REGION')
    api_domain_name = havoc_config.get(profile, 'API_DOMAIN_NAME')
else:
    api_key = havoc_config.get('default', 'API_KEY')
    secret = havoc_config.get('default', 'SECRET')
    api_region = havoc_config.get('default', 'API_REGION')
    api_domain_name = havoc_config.get('default', 'API_DOMAIN_NAME')

h = havoc.Connect(api_region, api_domain_name, api_key, secret)

# Configure pretty print for displaying output.
pp = pprint.PrettyPrinter(indent=4)

# Create a config parser and setup config parameters
config = ConfigParser(allow_no_value=True)
config.optionxform = str
config.read('havoc-playbooks/activity_report/activity_report.ini')

tasks = config.get('activity_report', 'tasks').split(',')
start_time = config.get('activity_report', 'start_time')
end_time = config.get('activity_report', 'end_time')

for task in tasks:
    task = task.strip()
    print(f'\nGetting results for task {task}\n')
    print('+------------------------------------------------------------------+')
    get_task_results = h.get_task_results(task, start_time=start_time, end_time=end_time)
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