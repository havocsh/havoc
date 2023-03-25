import os
import sys
import subprocess
import platform
import requests
import argparse
import havoc_profile
import havoc_config_playbook
from configparser import ConfigParser
from havoc_deployment import ManageDeployment

config = ConfigParser()
config.read('.havoc/havoc.cfg')

deployment_version = config.get('version', 'deployment_version')
tf_version = config.get('version', 'tf_version')

init_parser = argparse.ArgumentParser(description='./HAVOC deployment script')

init_parser.add_argument('--add_profile', help='Add a profile to your local .havoc/profiles file.')
init_parser.add_argument('--remove_profile', help='Remove a profile from your local .havoc/profiles file.')
init_parser.add_argument('--list_profiles', help='List the profiles in your local .havoc/profiles file.')
init_parser.add_argument('--profile', help='Specify a profile to use when launching the ./HAVOC CLI.')
init_parser.add_argument('--deployment', help='Manage your ./HAVOC deployment (create|modify|update|remove|get_deployment|connect_tf_backend|disconnect_tf_backend).')
init_parser.add_argument('--playbook', help='Configure a ./HAVOC playbook.')
init_parser.add_argument('--run_script', help='Run a local ./HAVOC script.')
init_args = init_parser.parse_args()


def tf_bin():
    tf = None
    cwd = os.getcwd()
    while not tf:
        if os.path.isfile(f'{cwd}/terraform'):
            tf = f'{cwd}/terraform'
        else:
            if platform.system().lower() in ['darwin', 'linux', 'freebsd', 'openbsd']:
                operating_system = platform.system().lower()
            if platform.machine().lower() in ['i686', 'x86_64']:
                architecture = 'amd64'
            if platform.machine().lower() == 'arm64':
                architecture = 'arm64'
            if platform.machine().lower() == 'i386':
                architecture = '386'
            
            print(f'Downloading appropriate Terraform binary for {operating_system}, {architecture} to {cwd}.')
            url=f'https://releases.hashicorp.com/terraform/{tf_version}/terraform_{tf_version}_{operating_system}_{architecture}.zip'
            r = requests.get(url, allow_redirects=True)
            with open(f'{cwd}/terraform_{tf_version}_{operating_system}_{architecture}.zip', 'wb') as tf_file:
                tf_file.write(r.content)
            if not os.path.isfile(f'{cwd}/terraform_{tf_version}_{operating_system}_{architecture}.zip'):
                print('Failed to download Terraform binary.')
                print(f'Please download the appropriate Terraform binary for your system here: https://releases.hashicorp.com/terraform/{tf_version}/')
                print('Unzip the binary in your local havoc-framework directory.')
                exit()
            tf_zip = f'{cwd}/terraform_{tf_version}_{operating_system}_{architecture}.zip'
            subprocess.run(['unzip', tf_zip])
            tf = f'{cwd}/terraform'
        if not tf:
            print('Could not find a local Terraform binary and one could not be automatically downloaded because your OS architecture could not be determined.')
            print(f'Please download the appropriate Terraform binary for your system here: https://releases.hashicorp.com/terraform/{tf_version}/')
            print('Make sure that the Terraform binary is added to your path.')
            exit()
    return tf


if __name__ == "__main__":

    if not len(sys.argv) > 1:
        import havoc_cli
        havoc_cmd = havoc_cli.HavocCMD()
        havoc_cmd.cmdloop()
    
    if init_args.profile and not init_args.deployment and not init_args.playbook_config:
        import havoc_cli
        havoc_cmd = havoc_cli.HavocCMD()
        havoc_cmd.profile = init_args.profile
        havoc_cmd.cmdloop()
    
    if init_args.add_profile:
        profile_task = havoc_profile.add_profile('add')
        if profile_task == 'completed':
            print('\nProfile task completed successfully.\n')
        else:
            print('\nProfile task failed.\n')
    
    if init_args.remove_profile:
        profile_task = havoc_profile.remove_profile('remove')
        if profile_task == 'completed':
            print('\nProfile task completed successfully.\n')
        else:
            print('\nProfile task failed.\n')
    
    if init_args.list_profiles:
        profile_task = havoc_profile.list_profiles()
        if profile_task == 'completed':
            print('\nProfile task completed successfully.\n')
        else:
            print('\nProfile task failed.\n')
    
    if init_args.deployment:
        if init_args.deployment not in ['create', 'modify', 'update', 'remove', 'get_deployment', 'connect_tf_backend', 'disconnect_tf_backend']:
            print('Missing --deployment action. Specify action using "--deployment <action>" notation.')
            print('<action> can be any of the following: create|modify|update|remove|get_deployment|connect_tf_backend|disconnect_tf_backend')
            exit()
        if init_args.profile:
            profile = init_args.profile
        else:
            profile = None
        m = ManageDeployment(tf_bin(), deployment_version, profile)
        if init_args.deployment == 'create':
            deploy_task = m.create()
        if init_args.deployment == 'modify':
            deploy_task = m.modify()
        if init_args.deployment == 'update':
            deploy_task = m.update()
        if init_args.deployment == 'remove':
            deploy_task = m.remove()
        if init_args.deployment == 'get_deployment':
            deploy_task = m.get_deployment()
        if init_args.deployment == 'connect_tf_backend':
            deploy_task = m.connect_tf_backend()
        if init_args.deployment == 'disconnect_tf_backend':
            deploy_task = m.disconnect_tf_backend()
        
        if deploy_task == 'completed':
            print('\nDeployment task completed successfully.\n')
        else:
            print('\nDeployment task failed.\n')
    
    if init_args.playbook:
        if init_args.playbook not in ['configure']:
            print('Missing --playbook action. Specify action using "--playbook <action>" notation.')
            print('<action> can be any of the following: configure')
            exit()
        profiles_test = havoc_config_playbook.load_havoc_profiles()
        if not profiles_test:
            print('\nPlaybook configuration task failed. No ./HAVOC profiles found.')
        else:
            if init_args.profile:
                profile = init_args.profile
            else:
                profile = None
            c = havoc_config_playbook.ConfigPlaybook(profile)
            configure_task = c.configure()
            if configure_task == 'completed':
                print('\nPlaybook configuration task completed successfully.\n')
            else:
                print('\nPlaybook configuration task failed.')
    
    if init_args.run_script:
        spath = 'havoc_scripts'
        havoc_scripts = [name for name in os.listdir(spath) if os.path.isdir(os.path.join(spath, name))]
        if init_args.run_script not in havoc_scripts:
            print(f'Script {init_args.run_script} not found. Specify a script to run using "--run_script <script_name>" notation.')
            print('<script_name> can be any of the following:')
            for script_name in havoc_scripts:
                print(f' {script_name}\n')
            exit()
        profiles_test = havoc_config_playbook.load_havoc_profiles()
        if not profiles_test:
            print('\nScript task failed. No ./HAVOC profiles found.')
        else:
            script = init_args.run_script
            if init_args.profile:
                profile = init_args.profile
                subprocess.run(['.venv/bin/python3', script, f'--profile= {profile}'])
            else:
                subprocess.run(['python', script])
            print('\nPlaybook configuration task failed.')
