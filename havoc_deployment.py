import os
import re
import boto3
import botocore
import subprocess
import havoc_profile
import havoc
from configparser import ConfigParser


def load_havoc_profiles():
    # Load the ./HAVOC profiles file
    havoc_profiles = ConfigParser()
    havoc_profiles.read('.havoc/profiles')
    return havoc_profiles

class ManageDeployment:

    def __init__(self, tf_bin, deployment_version, profile=None):
        self.tf_bin = tf_bin
        self.deployment_version = deployment_version
        self.profile = profile
        self.aws_profile = None
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


    def validate_deployment_name(self, name):
        if not re.search(r'^[a-zA-Z0-9\-]{3,63}$', name):
            print('\nDeployment name must be DNS compliant (limited to letters, numbers and hyphens), minimum 3 characters and maximum 32 characters.\n') 
            name = None
        else:
            if self.aws_profile:
                boto3.setup_default_session(profile_name=self.aws_profile)
            s3 = boto3.client('s3')
            try:
                response = s3.head_bucket(Bucket=name)
                if response == '200 OK':
                    print('\n./HAVOC deployment name not available. Please select a different deployment name.\n')
                    name = None
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 403:
                    print('\n./HAVOC deployment name not available. Please select a different deployment name.\n')
                    name = None
        return name
    
    def get_deployment(self):
        try:
            deployment_details = self.havoc_client.get_deployment()
            deployment_name = deployment_details['deployment_name']
            deployment_version = deployment_details['deployment_version']
            deployment_admin_email = deployment_details['deployment_admin_email']
            results_queue_expiration = deployment_details['results_queue_expiration']
            retrieved_api_domain_name = deployment_details['api_domain_name']
            retrieved_api_region = deployment_details['api_region']
            tfstate_s3_bucket = deployment_details['tfstate_s3_bucket']
            tfstate_s3_key = deployment_details['tfstate_s3_key']
            tfstate_s3_region = deployment_details['tfstate_s3_region']
            tfstate_dynamodb_table = deployment_details['tfstate_dynamodb_table']
        except Exception as e:
            print('Retrieving deployment details from ./HAVOC API failed with error:\n')
            print(e)
            print('\nMake sure to specify a valid ./HAVOC profile with the --profile parameter.')
            return 'failed'

        print('./HAVOC deployment details:\n')
        print(f'  DEPLOYMENT_NAME = {deployment_name}')
        print(f'  DEPLOYMENT_VERSION = {deployment_version}')
        print(f'  DEPLOYMENT_ADMIN_EMAIL = {deployment_admin_email}')
        print(f'  RESULTS_QUEUE_EXPIRATION = {results_queue_expiration}')
        print(f'  API_DOMAIN_NAME = {retrieved_api_domain_name}')
        print(f'  API_REGION = {retrieved_api_region}')
        print(f'  TERRAFORM_STATE_S3_BUCKET = {tfstate_s3_bucket}')
        print(f'  TERRAFORM_STATE_S3_KEY = {tfstate_s3_key}')
        print(f'  TERRAFORM_STATE_S3_REGION = {tfstate_s3_region}')
        print(f'  TERRAFORM_STATE_DYNAMODB_TABLE = {tfstate_dynamodb_table}')
        return 'completed'

    
    def connect_tf_backend(self, deployment=None):
        # Get the Terraform backend details
        print('Starting configuration for Terraform backend connection.')
        if not self.aws_profile:
            self.aws_profile = input('Specify the AWS credentials profile to use (or you can leave it blank for default): ')

        print('Getting backend connection settings from ./HAVOC deployment details.')
        try:
            deployment_details = self.havoc_client.get_deployment()
            tfstate_s3_bucket = deployment_details['tfstate_s3_bucket']
            tfstate_s3_key = deployment_details['tfstate_s3_key']
            tfstate_s3_region = deployment_details['tfstate_s3_region']
            tfstate_dynamodb_table = deployment_details['tfstate_dynamodb_table']
        except Exception as e:
            print('Retrieving deployment details from ./HAVOC API failed with error:\n')
            print(e)
            print('\nMake sure to specify a valid ./HAVOC profile with the --profile parameter.')
            return 'failed'

        print('Verifying the S3 bucket and key...\n')
        if self.aws_profile:
            boto3.setup_default_session(profile_name=self.aws_profile)
        s3 = boto3.client('s3')
        if deployment:
            try:
                s3.head_bucket(Bucket=tfstate_s3_bucket)
            except botocore.exceptions.ClientError as error:
                if error['Error']['Code'] == 403:
                    print(f'S3 bucket {tfstate_s3_bucket} found but access was denied.')
                if error['Error']['Code'] == 404:
                    print(f'No S3 bucket found for {tfstate_s3_bucket}')
                return 'failed'
            try:
                with open('havoc_deploy/aws/terraform/terraform.tfstate', 'r') as tfstate_f:
                    tfstate_data = tfstate_f.read().encode()
                s3.put_object(Bucket=tfstate_s3_bucket, Key=tfstate_s3_key, Body=tfstate_data) 
            except botocore.exceptions.ClientError as error:
                if error['Error']['Code'] == 403:
                    print(f'Writing tfstate file to {tfstate_s3_bucket} failed with access denied.')
                else:
                    print(f'Terraform state file creation failed with error {error["Error"]}')
                return 'failed'
        else:
            try:
                s3.head_object(Bucket=tfstate_s3_bucket, Key=tfstate_s3_key)
            except botocore.exceptions.ClientError as error:
                if error['Error']['Code'] == 403:
                    print(f'S3 bucket/key {tfstate_s3_bucket}/{tfstate_s3_key} found but access was denied.')
                if error['Error']['Code'] == 404:
                    print(f'No S3 bucket/key found for {tfstate_s3_bucket}/{tfstate_s3_key}.')
                return 'failed'
        print('Access verified. Writing Terraform backend configuration.\n')
        terraform_backend = 'terraform {\n' \
            '  backend "s3" {\n' \
            f'    profile        = "{self.aws_profile}"\n' \
            f'    bucket         = "{tfstate_s3_bucket}"\n' \
            f'    key            = "{tfstate_s3_key}"\n' \
            f'    region         = "{tfstate_s3_region}"\n' \
            f'    dynamodb_table = "{tfstate_dynamodb_table}"\n' \
            '    encrypt         = true\n' \
            '  }\n' \
            '}\n'
        with open('./havoc_deploy/aws/terraform/terraform_backend.tf', 'w+') as f:
            f.write(terraform_backend)
        print('Initializing Terraform...\n')
        tf_init_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'init', '-no-color']
        tf_init = subprocess.Popen(tf_init_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_init_output = tf_init.communicate()[1].decode('ascii')
        if tf_init_output:
            print('\nInitializing Terraform backend configuration encountered errors:\n')
            print(tf_init_output)
            print('\nRolling back changes...\n')
            if os.path.exists('havoc_deploy/aws/terraform/terraform_backend.tf'):
                os.remove('havoc_deploy/aws/terraform/terraform_backend.tf')
            return 'failed'
        print('Terraform initialization completed.\n')
        return 'completed'

    def disconnect_tf_backend(self):
        print('\nDeleting the Terraform backend configuration (this will not affect the Terraform state stored with your ./HAVOC deployment).\n')
        if os.path.exists('havoc_deploy/aws/terraform/terraform_backend.tf'):
            os.remove('havoc_deploy/aws/terraform/terraform_backend.tf')
            print('Backend configuration deleted. Initializing Terraform.\n')
            tf_init_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'init', '-migrate-state', '-force-copy', '-no-color']
            tf_init = subprocess.Popen(tf_init_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tf_init_output = tf_init.communicate()[1].decode('ascii')
            if tf_init_output:
                print('\nInitializing Terraform encountered errors:\n')
                print(tf_init_output)
        else:
            print('No Terraform backend configuration was found.\n')
        return 'completed'

    def create(self):
        # Check for existing deployment
        if os.path.isfile('havoc_deploy/aws/terraform/terraform.tfvars'):
            print('\nExisting deployment found.\n')
            print('If you intend to re-create this ./HAVOC deployment, remove the existing deployment first by running "./havoc --deployment remove".')
            print('If you would like to create another deployment without destroying this one,')
            print('clone the https://github.com/havocsh/havoc-framework.git repo to a different directory and deploy from there.')
            print('Exiting...')
            return 'failed'
        print(' - Deployment dependencies met. Proceeding with deployment.\n')

        # Build havoc-control-api packages for AWS Lambda
        subprocess.run('./havoc_build_packages.sh', shell=True)

        # Write out terraform.tfvars file
        print('\n - Setting up Terraform variables. Please provide the requested details.')
        aws_region = input('\nAWS region: ')
        self.aws_profile = input('AWS profile: ')
        deployment_name = None
        while not deployment_name:
            deployment_name_input = input('./HAVOC deployment name: ')
            test_bucket_1 = self.validate_deployment_name(f'{deployment_name_input}-workspace')
            test_bucket_2 = self.validate_deployment_name(f'{deployment_name_input}-terraform-state')
            if test_bucket_1 and test_bucket_2:
                deployment_name = deployment_name_input
        deployment_admin_email = input('./HAVOC deployment administrator email: ')
        results_queue_expiration = input('Task results queue expiration: ')
        enable_domain = input('Enable custom domain name? (Y/N): ')
        if enable_domain in ['y','Y','yes','Yes','YES']:
            enable_domain_name = 'true'
            custom_domain_name = input('Custom domain name: ')
            hosted_zone = input('Hosted zone ID: ')
        else:
            enable_domain_name = 'false'

        with open('./havoc_deploy/aws/terraform/terraform.tfvars', 'w+') as f:
            f.write(f'aws_region = "{aws_region}"\n')
            f.write(f'aws_profile = "{self.aws_profile}"\n')
            f.write(f'deployment_name = "{deployment_name}"\n')
            f.write(f'deployment_admin_email = "{deployment_admin_email}"\n')
            f.write(f'results_queue_expiration = "{results_queue_expiration}"\n')
            f.write(f'deployment_version = "{self.deployment_version}"\n')
            if enable_domain_name == 'true':
                f.write(f'enable_domain_name = {enable_domain_name}\n')
                f.write(f'domain_name = "{custom_domain_name}"\n')
                f.write(f'hosted_zone = "{hosted_zone}"\n')
            else:
                f.write(f'enable_domain_name = {enable_domain_name}\n')

        # Run Terraform and check for errors:
        print(' - Initializing Terraform...\n')
        tf_init_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'init', '-no-color']
        tf_init = subprocess.Popen(tf_init_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_init_output = tf_init.communicate()[1].decode('ascii')
        if tf_init_output:
            print('\nInitializing Terraform encountered errors:\n')
            print(tf_init_output)
            print('\nRolling back changes...\n')
            if os.path.exists('havoc_deploy/aws/terraform/terraform.tfvars'):
                os.remove('havoc_deploy/aws/terraform/terraform.tfvars')
            return 'failed'
        print(' - Starting Terraform tasks.\n')
        tf_apply_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'apply', '-no-color', '-auto-approve']
        tf_apply = subprocess.Popen(tf_apply_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_apply_output = tf_apply.communicate()[1].decode('ascii')
        if tf_apply_output:
            print('\nTerraform deployment encountered errors:\n')
            print(tf_apply_output)
            print('\nRolling back changes...\n')
            tf_destroy_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'destroy', '-no-color', '-auto-approve']
            tf_destroy = subprocess.Popen(tf_destroy_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tf_destroy_output = tf_destroy.communicate()[1].decode('ascii')
            if not tf_destroy_output:
                if os.path.exists('havoc_deploy/aws/terraform/terraform.tfvars'):
                    os.remove('havoc_deploy/aws/terraform/terraform.tfvars') 
                if os.path.exists('havoc_deploy/aws/terraform/terraform.tfstate'):
                    os.remove('havoc_deploy/aws/terraform/terraform.tfstate')
                print('\nRollback complete.')
            else:
                print('Terraform destroy encountered errors during rollback:')
                print(tf_destroy_output)
            print('Review errors above, correct the reported issues and try the deployment again.')
            return 'failed'
        print(' - Terraform deployment tasks completed.')

        # Create ./HAVOC profile
        profile_output = havoc_profile.add_profile('deploy_add')
        self.profile = profile_output['profile_name']
        api_domain_name = profile_output['api_domain_name']
        api_region = profile_output['api_region']
        tfstate_s3_region = api_region
        tfstate_s3_bucket = profile_output['tfstate_s3_bucket']
        tfstate_s3_key = 'havoc_terraform/terraform.tfstate'
        tfstate_dynamodb_table = profile_output['tfstate_dynamodb_table']
        self.havoc_client.create_deployment(
            self.deployment_version,
            deployment_admin_email,
            results_queue_expiration,
            api_domain_name,
            api_region,
            tfstate_s3_bucket, 
            tfstate_s3_key, 
            tfstate_s3_region, 
            tfstate_dynamodb_table
            )
        tf_connection = self.connect_tf_backend(deployment=True)
        if tf_connection == 'failed':
            print('\nThe ./HAVOC deployment succeeded but the Terraform backend could not be connected to S3 for backing up Terraform state.\n')
            print('Correct the errors above and run "./havoc --deployment connect_tf_backend" if you would like to have your Terraform state stored in S3.')
        return 'completed'

    def modify(self):
        # Setup method for modifying deployment parameters. Re-run terraform apply after changes.
        print('\nAvailable parameters:\n[1] AWS Profile\n[2] Deployment Admin Email\n[3] Results Queue Expiration Time\n')
        parameters = {}
        deployment_update = {}
        mod = True
        while mod:
            try:
                parameter_input = input('Enter the number of the parameter you would like to modify: ')
                if parameter_input == '1':
                    parameters['aws_profile'] = input('Enter the desired AWS profile to be used by Terraform: ')
                if parameter_input == '2':
                    deployment_admin_email = input('Enter the desired ./HAVOC deployment administrator email: ')
                    parameters['deployment_admin_email'] = deployment_admin_email
                    deployment_update['deployment_admin_email'] = deployment_admin_email
                if parameter_input == '3':
                    results_queue_expiration = input('Enter the desired task results queue expiration time in number of days: ')
                    parameters['results_queue_expiration'] = results_queue_expiration
                    deployment_update['results_queue_expiration'] = results_queue_expiration
                mod = input('\nWould you like to modify another paramenter? (y|n): ')
                if mod in ['n', 'N', 'no', 'No', 'NO'] or mod is None:
                    mod = False
            except KeyboardInterrupt:
                print('Ctrl+C detected. Skipping parameter.')
                mod = False
        if parameters is None:
            print('No parameters entered. Exiting.')
            return 'completed'

        # Read existing tfvars file and extract combine existing parameters with modified parameters.
        with open('./havoc_deploy/aws/terraform/terraform.tfvars', 'r') as f:
            for line in f:
                if '=' in line:
                    parameter_key = line.split(' = ')[0].rstrip()
                    parameter_value = line.split(' = ')[1].rstrip().replace('"', '')
                    if parameter_key not in parameters:
                        parameters[parameter_key] = parameter_value
        
        with open('./havoc_deploy/aws/terraform/terraform.tfvars', 'w') as f:
            for k,v in parameters.items():
                f.write(f'{k} = "{v}"\n')
            

        # Run Terraform and check for errors:
        print('Initializing Terraform...\n')
        tf_init_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'init', '-no-color']
        tf_init = subprocess.Popen(tf_init_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_init_output = tf_init.communicate()[1].decode('ascii')
        if tf_init_output:
            print('\nInitializing Terraform encountered errors:\n')
            print(tf_init_output)
            return 'failed'
        print('Starting Terraform tasks.\n')
        tf_apply_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'apply', '-no-color', '-auto-approve']
        tf_apply = subprocess.Popen(tf_apply_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_apply_output = tf_apply.communicate()[1].decode('ascii')
        if tf_apply_output:
            print('\nTerraform deployment encountered errors:\n')
            print(tf_apply_output)
            print('Review errors above, correct the reported issues and try again.')
            return 'failed'
        print('Terraform deployment tasks completed.')
        self.havoc_client.update_deployment(**deployment_update)
        return 'completed'

    def update(self):
        # Check for existing deployment
        no_local_tfstate = None
        no_remote_tfstate = None
        if not os.path.exists('havoc_deploy/aws/terraform/terraform.tfstate'):
            no_local_tfstate = True
        if not os.path.exists('havoc_deploy/aws/terraform/terraform_backend.tf'):
            no_remote_tfstate = True
        if no_local_tfstate and no_remote_tfstate:
            print('\nNo existing deployment found.\n')
            print('Perform the update from the system that created the ./HAVOC deployment.\n')
            print('Alternatively, you can connect this system to the Terraform deployment with the "./havoc --deployment connect_tf_backend" command.\n')
            return 'failed'
        
        # Rebuild havoc-control-api packages for AWS Lambda
        subprocess.run('./havoc_build_packages.sh', shell=True)

        # Run Terraform and check for errors:
        print('\n - Starting Terraform tasks.')
        tf_apply_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'apply', '-no-color', '-auto-approve']
        tf_apply = subprocess.Popen(tf_apply_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_apply_output = tf_apply.communicate()[1].decode('ascii')
        if tf_apply_output:
            print('\nTerraform update encountered errors:\n')
            print(tf_apply_output)
            print('Review errors above, correct the reported issues and try the update again.')
            return 'failed'
        print(' - Terraform tasks completed.\n')
        self.havoc_client.update_deployment(deployment_version=self.deployment_version)
        return 'completed'
    
    def remove(self):
        # Check for existing deployment
        no_local_tfstate = False
        no_remote_tfstate = False
        if not os.path.exists('havoc_deploy/aws/terraform/terraform.tfstate'):
            no_local_tfstate = True
        if not os.path.exists('havoc_deploy/aws/terraform/terraform_backend.tf'):
            no_remote_tfstate = True
        if no_local_tfstate and no_remote_tfstate:
            print('\nNo existing deployment found.\n')
            print('Perform the remove operation from the system that created the ./HAVOC deployment.\n')
            print('Alternatively, you can connect this system to the Terraform deployment with the "./havoc --deployment connect_tf_backend" command.\n')
            return 'failed'
        
        # Disconnect Terraform from S3 backend if present and delete terraform state from S3
        if no_remote_tfstate is False:
            with open('./havoc_deploy/aws/terraform/terraform_backend.tf', 'r') as tf_backend_f:
                tf_backend = tf_backend_f.read()
            self.aws_profile = re.search('profile\s+= "([^"]+)"', tf_backend).group(1)
            tfstate_s3_bucket = re.search('bucket\s+= "([^"]+)"', tf_backend).group(1)
            tfstate_s3_key = re.search('key\s+= "([^"]+)"', tf_backend).group(1)
            self.disconnect_tf_backend()
            boto3.setup_default_session(profile_name=self.aws_profile)
            s3 = boto3.client('s3')
            list_object_versions_response = s3.list_object_versions(Bucket=tfstate_s3_bucket, Prefix=tfstate_s3_key)
            tfstate_versions = list_object_versions_response['Versions']
            for tfstate_version in tfstate_versions:
                s3.delete_object(Bucket=tfstate_s3_bucket, Key=tfstate_s3_key, VersionId=tfstate_version['VersionId'])
        
        # Remove ./HAVOC profiles for deployment
        havoc_profile.remove_profile(mode='deploy_remove')

        # Run Terraform and check for errors
        print('\n - Starting Terraform tasks.')
        tf_destroy_cmd = [self.tf_bin, '-chdir=havoc_deploy/aws/terraform', 'destroy', '-no-color', '-auto-approve']
        tf_destroy = subprocess.Popen(tf_destroy_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tf_destroy_output = tf_destroy.communicate()[1].decode('ascii')
        if tf_destroy_output:
            print('\nTerraform destroy encountered errors:\n')
            print(tf_destroy_output)
            print('Review errors above, correct the reported issues and try the uninstall again.')
            return 'failed'
        print(' - Terraform tasks completed.\n')
        print('\n - Deleting local Terraform state.\n')
        if os.path.exists('havoc_deploy/aws/terraform/terraform.tfstate'):
            os.remove('havoc_deploy/aws/terraform/terraform.tfstate')
        if os.path.exists('havoc_deploy/aws/terraform/terraform_backend.tf'):
            os.remove('havoc_deploy/aws/terraform/terraform_backend.tf')
        if os.path.exists('havoc_deploy/aws/terraform/terraform.tfvars'):
            os.remove('havoc_deploy/aws/terraform/terraform.tfvars')
        return 'completed'
