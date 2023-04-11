import re
import json
import hcl2
import havoc
from configparser import ConfigParser


def load_havoc_profiles():
    # Load the ./HAVOC profiles file
    havoc_profiles = ConfigParser()
    havoc_profiles.read('.havoc/profiles')
    return havoc_profiles


class ConfigPlaybook:

    def __init__(self, profile=None):
        self.profile = profile
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
    
    def configure(self):
        print('\nConfiguring a playbook creates a new playbook entity in your ./HAVOC deployment with a corresponding playbook configuration')
        print('that is based on a source template of a specific playbook type. The available playbook types will be displayed now. To proceed,')
        
        # Determine the playbook type to be used as the source for the playbook configuration
        list_playbook_types_response = self.havoc_client.list_playbook_types()
        playbook_types = list_playbook_types_response['playbook_types']
        playbook_types.sort()
        n = 1
        for playbook_type in playbook_types:
            print(f'{n}) {playbook_type}')
            n += 1
        playbook_number = input('\nEnter the number associated with the playbook type you would like to configure: ')
        playbook_selection = playbook_types[int(playbook_number) - 1]

        # Get the playbook type details and parse the playbook template
        print(f'\nGetting the template for playbook_type {playbook_selection}.')
        playbook_type_details = self.havoc_client.get_playbook_type(playbook_selection)
        playbook_template = hcl2.loads(playbook_type_details['playbook_template'])
        if 'variable' in playbook_template:
            print('The playbook template contains variables that require static values.')
            print('Please provide values for the variables below. They will be inserted into your playbook configuration:')
            playbook_vars = playbook_template['variable']
            for playbook_var in playbook_vars:
                for k in playbook_var.keys():
                    print(f'\nVariable: {k}')
                    if 'description' in playbook_var[k]:
                        description = playbook_var[k]['description']
                        print(f'Description: {description}')
                    default = None
                    if 'default' in playbook_var[k]:
                        default = playbook_var[k]['default']
                        print(f'Default: {default}')
                    if default:
                        provided_value = input(f'Enter a value to use for variable {k} or press enter to accept the default: ')
                    else:
                        provided_value = input(f'Enter a value to use for variable {k}: ')
                    value = provided_value or default
                    playbook_var[k]['value'] = value
            print('\nConverting playbook template to a playbook config.')
            for section in playbook_template:
                if section != 'variable':
                    json_section = json.dumps(playbook_template[section])
                    dep_matches = re.findall('\${(variable\.[^}]+)}', json_section)
                    if dep_matches:
                        dep_value = None
                        for dep_match in dep_matches:
                            dep_match_list = dep_match.split('.')
                            var_name = dep_match_list[1]
                            for variable in playbook_template['variable']:
                                for k in variable.keys():
                                    if k == var_name:
                                        dep_value = variable[k]['value']
                            re_sub = re.compile('\${' + dep_match + '}')
                            json_section = re.sub(re_sub, dep_value, json_section)
                            new_section = json.loads(json_section)
                            playbook_template[section] = new_section
            del playbook_template['variable']
            playbook_config = json.dumps(playbook_template)
            print('Done.')
        playbook_name = None
        while not playbook_name:
            playbook_name = input('\nPlease enter a name for this playbook: ')
            list_playbooks_response = self.havoc_client.list_playbooks()
            playbooks = list_playbooks_response['playbooks']
            for playbook in playbooks:
                if playbook_name == playbook['playbook_name']:
                    print(f'A playbook with name {playbook_name} already exists.')
                    playbook_name = None
        playbook_timeout = input('Please enter a timeout value in minutes that this playbook will be allowed to run before self-terminating: ')
        playbook_schedule = 'None'
        print('Creating a playbook with the configured properties. To run the configured playbook, use the following command in the ./HAVOC CLI:\n')
        print(f'  run_playbook --playbook_name={playbook_name}')
        create_playbook_response = self.havoc_client.create_playbook(playbook_name, playbook_selection, playbook_schedule, playbook_timeout, playbook_config)
        if create_playbook_response:
            return 'completed'
        else:
            return 'failed'

