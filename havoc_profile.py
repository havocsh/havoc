import json
from configparser import ConfigParser

# Load the ./HAVOC configuration file
havoc_profiles = ConfigParser()
havoc_profiles.read('.havoc/profiles')


def list_profiles():
    print('\nProfiles:')
    for section in havoc_profiles.sections():
        deployment_name = havoc_profiles[section]['DEPLOYMENT_NAME']
        api_key = havoc_profiles[section['API_KEY']]
        print(f'  {section}\n')
        print(f'  - Deployment name: {deployment_name}\n')
        print(f'  - API key: {api_key}\n')
    return 'completed'


def add_profile(mode):
    # Create ./HAVOC profile (used by ./havoc -a, -d and -s options)
    print('Adding a ./HAVOC profile to .havoc/profiles. Please provide the requested details below.')

    if mode == 'deploy_add':
        deploy_profile = 'default'
        havoc_profiles[deploy_profile] = {}
        # Get the deployment output details and add them to the profile
        with open('./havoc_deploy/aws/terraform/terraform.tfstate', 'r') as tfstate_f:
            tf_state_data = json.load(tfstate_f)
        havoc_profiles[deploy_profile]['DEPLOYMENT_NAME'] = tf_state_data['outputs']['DEPLOYMENT_NAME']['value']
        havoc_profiles[deploy_profile]['DEPLOYMENT_ADMIN_EMAIL'] = tf_state_data['outputs']['DEPLOYMENT_ADMIN_EMAIL']['value']
        havoc_profiles[deploy_profile]['API_DOMAIN_NAME'] = tf_state_data['outputs']['API_DOMAIN_NAME']['value']
        havoc_profiles[deploy_profile]['API_REGION'] = tf_state_data['outputs']['API_REGION']['value']
        havoc_profiles[deploy_profile]['API_KEY'] = tf_state_data['outputs']['API_KEY']['value']
        havoc_profiles[deploy_profile]['SECRET'] = tf_state_data['outputs']['SECRET']['value']
        results_queue_expiration = tf_state_data['outputs']['RESULTS_QUEUE_EXPIRATION']['value']
        tfstate_s3_bucket = tf_state_data['outputs']['TERRAFORM_STATE_S3_BUCKET']['value']
        tfstate_dynamodb_table = tf_state_data['outputs']['TERRAFORM_STATE_DYNAMODB_TABLE']['value']
    else:
        # Get the profile name and make sure it is unique
        deploy_profile = None
        while not deploy_profile:
            deploy_profile = input('\n./HAVOC credential profile name [default]: ')
            if not deploy_profile:
                deploy_profile = 'default'
            if deploy_profile in havoc_profiles.sections():
                print(f'Profile {deploy_profile} already exists.')
                deploy_profile = None
        havoc_profiles[deploy_profile] = {}
        # Get the profile details from user inputs and add them to the profile
        havoc_profiles[deploy_profile]['DEPLOYMENT_NAME'] = input('Deployment name: ')
        havoc_profiles[deploy_profile]['DEPLOYMENT_ADMIN_EMAIL'] = input('Deployment admin email: ')
        havoc_profiles[deploy_profile]['API_DOMAIN_NAME'] = input('API domain name: ')
        havoc_profiles[deploy_profile]['API_REGION'] = input('API region: ')
        havoc_profiles[deploy_profile]['API_KEY'] = input('API key: ')
        havoc_profiles[deploy_profile]['SECRET'] = input('Secret: ')

    # Write the profile details to the .havoc/profiles file
    with open('./.havoc/profiles', 'a') as profiles_f:
        havoc_profiles.write(profiles_f)

    print('\nThe following deployment parameters have been written to your .havoc/profiles file:')
    print(f'[{deploy_profile}]')
    for k, v in havoc_profiles[deploy_profile].items():
        print(f'{k} = {v}')
    if mode == 'deploy_add':
        output = {
            'profile_name': deploy_profile, 
            'deployment_name': havoc_profiles[deploy_profile]['DEPLOYMENT_NAME'],
            'deployment_admin_email': havoc_profiles[deploy_profile]['DEPLOYMENT_ADMIN_EMAIL'],
            'api_domain_name': havoc_profiles[deploy_profile]['API_DOMAIN_NAME'],
            'api_region': havoc_profiles[deploy_profile]['API_REGION'],
            'results_queue_expiration': results_queue_expiration,
            'tfstate_s3_bucket': tfstate_s3_bucket,
            'tfstate_dynamodb_table': tfstate_dynamodb_table
            }
        return output
    else:
        return 'completed'


def remove_profile(mode):
    # Remove ./HAVOC profile (used by ./havoc -r option)
    profile_names = []
    
    # If deploy_remove mode, get ./HAVOC profile names based on deployment name
    if mode == 'deploy_remove':
        with open('./havoc_deploy/aws/terraform/terraform.tfstate', 'r') as tfstate_f:
            tf_state_data = json.load(tfstate_f)
        if 'outputs' in tf_state_data:
            deployment_name = tf_state_data['outputs']['DEPLOYMENT_NAME']['value']
            print(f'\nRemoving ./HAVOC profile names for deployment name {deployment_name} from .havoc/profiles.')

            # Find profiles associated with the deployment
            for section in havoc_profiles.sections():
                if havoc_profiles[section]['DEPLOYMENT_NAME'] == deployment_name:
                    profile_names.append(section)

    # if remove mode, get the profile name from user input and make sure it exists in .havoc/profiles
    if mode == 'remove':
        done = None
        while not profile_name_input and not done:
            profile_name_input = input('\nEnter the profile name to remove: ')
            if profile_name_input not in havoc_profiles.sections():
                print(f'Profile {profile_name_input} not found.')
                profile_name_input = None
            profile_names.append(profile_name_input)
            done = input('Would you like to remove another profile? (Y|N): ')
            if done in ['y', 'Y', 'yes', 'Yes', 'YES']:
                done = None
        
    if not profile_names:
        print('No profiles found.')
    else:
        # Remove the profiles and write out a new profiles file
        for profile_name in profile_names:
            havoc_profiles.remove_section(profile_name)
            print(f'\n./HAVOC profile {profile_name} removed from .havoc/profiles.')
        with open('./.havoc/profiles', 'w') as profiles_f:
            havoc_profiles.write(profiles_f)
    return 'completed'
