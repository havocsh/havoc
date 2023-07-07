import json
import botocore
import boto3


def format_response(status_code, result, message, log, **kwargs):
    response = {'outcome': result}
    if message:
        response['message'] = message
    if kwargs:
        for k, v in kwargs.items():
            if v:
                response[k] = v
    if log:
        log['response'] = response
        print(log)
    return {'statusCode': status_code, 'body': json.dumps(response)}


class Deployment:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Instantiate a Deployment instance
        """
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.__aws_dynamodb_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    def get_deployment_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )
    
    def create_deployment_entry(self):
        existing_deployment = self.get_deployment_entry()
        if 'Item' in existing_deployment:
            return 'deployment_exists'
        else:
            deployment_version = self.detail['deployment_version']
            deployment_admin_email = self.detail['deployment_admin_email']
            results_queue_expiration = self.detail['results_queue_expiration']
            api_domain_name = self.detail['api_domain_name']
            api_region = self.detail['api_region']
            enable_task_results_logging = self.detail['enable_task_results_logging']
            task_results_logging_cwlogs_group = self.detail['task_results_logging_cwlogs_group']
            enable_playbook_results_logging = self.detail['enable_playbook_results_logging']
            playbook_results_logging_cwlogs_group = self.detail['playbook_results_logging_cwlogs_group']
            tfstate_s3_bucket = self.detail['tfstate_s3_bucket']
            tfstate_s3_key = self.detail['tfstate_s3_key']
            tfstate_s3_region = self.detail['tfstate_s3_region']
            tfstate_dynamodb_table = self.detail['tfstate_dynamodb_table']
            try:
                self.aws_dynamodb_client.update_item(
                    TableName=f'{self.deployment_name}-deployment',
                    Key={
                        'deployment_name': {'S': self.deployment_name}
                    },
                    UpdateExpression='set deployment_version=:deployment_version, '
                                    'deployment_admin_email=:deployment_admin_email, '
                                    'results_queue_expiration=:results_queue_expiration, '
                                    'api_domain_name=:api_domain_name, '
                                    'api_region=:api_region, '
                                    'enable_task_results_logging=:enable_task_results_logging, '
                                    'task_results_logging_cwlogs_group=:task_results_logging_cwlogs_group, '
                                    'enable_playbook_results_logging=:enable_playbook_results_logging, '
                                    'playbook_results_logging_cwlogs_group=:playbook_results_logging_cwlogs_group, '
                                    'tfstate_s3_bucket=:tfstate_s3_bucket, '
                                    'tfstate_s3_key=:tfstate_s3_key, '
                                    'tfstate_s3_region=:tfstate_s3_region, '
                                    'tfstate_dynamodb_table=:tfstate_dynamodb_table',
                    ExpressionAttributeValues={
                        ':deployment_version': {'S': deployment_version},
                        ':deployment_admin_email': {'S': deployment_admin_email},
                        ':results_queue_expiration': {'S': results_queue_expiration},
                        ':api_domain_name': {'S': api_domain_name},
                        ':api_region': {'S': api_region},
                        ':enable_task_results_logging': {'S': enable_task_results_logging},
                        ':task_results_logging_cwlogs_group': {'S': task_results_logging_cwlogs_group},
                        ':enable_playbook_results_logging': {'S': enable_playbook_results_logging},
                        ':playbook_results_logging_cwlogs_group': {'S': playbook_results_logging_cwlogs_group},
                        ':tfstate_s3_bucket': {'S': tfstate_s3_bucket},
                        ':tfstate_s3_key': {'S': tfstate_s3_key},
                        ':tfstate_s3_region': {'S': tfstate_s3_region},
                        ':tfstate_dynamodb_table': {'S': tfstate_dynamodb_table}
                    }
                )
            except botocore.exceptions.ClientError as error:
                return error
            except botocore.exceptions.ParamValidationError as error:
                return error
            return 'deployment_created'

    def update_deployment_entry(self):
        existing_deployment = self.get_deployment_entry()
        if 'Item' in existing_deployment:
            if 'deployment_version' in self.detail:
                deployment_version = self.detail['deployment_version']
            else:
                deployment_version = existing_deployment['Item']['deployment_version']['S']
            if 'deployment_admin_email' in self.detail:
                deployment_admin_email = self.detail['deployment_admin_email']
            else:
                deployment_admin_email = existing_deployment['Item']['deployment_admin_email']['S']
            if 'results_queue_expiration' in self.detail:
                results_queue_expiration = self.detail['results_queue_expiration']
            else:
                results_queue_expiration = existing_deployment['Item']['results_queue_expiration']['S']
            if 'api_domain_name' in self.detail:
                api_domain_name = self.detail['api_domain_name']
            else:
                api_domain_name = existing_deployment['Item']['api_domain_name']['S']
            if 'api_region' in self.detail:
                api_region = self.detail['api_region']
            else:
                api_region = existing_deployment['Item']['api_region']['S']
            if 'enable_task_results_logging' in self.detail:
                enable_task_results_logging = self.detail['enable_task_results_logging']
            else:
                enable_task_results_logging = existing_deployment['Item']['enable_task_results_logging']['S']
            if 'enable_playbook_results_logging' in self.detail:
                enable_playbook_results_logging = self.detail['enable_playbook_results_logging']
            else:
                enable_playbook_results_logging = existing_deployment['Item']['enable_playbook_results_logging']['S']
            try:
                self.aws_dynamodb_client.update_item(
                    TableName=f'{self.deployment_name}-deployment',
                    Key={
                        'deployment_name': {'S': self.deployment_name}
                    },
                    UpdateExpression='set deployment_version=:deployment_version, '
                                    'deployment_admin_email=:deployment_admin_email, '
                                    'results_queue_expiration=:results_queue_expiration, '
                                    'api_domain_name=:api_domain_name, '
                                    'api_region=:api_region, '
                                    'enable_task_results_logging=:enable_task_results_logging, '
                                    'enable_playbook_results_logging=:enable_playbook_results_logging',
                    ExpressionAttributeValues={
                        ':deployment_version': {'S': deployment_version},
                        ':deployment_admin_email': {'S': deployment_admin_email},
                        ':results_queue_expiration': {'S': results_queue_expiration},
                        ':enable_task_results_logging': {'S': enable_task_results_logging},
                        ':enable_playbook_results_logging': {'S': enable_playbook_results_logging},
                        ':api_domain_name': {'S': api_domain_name},
                        ':api_region': {'S': api_region}
                    }
                )
            except botocore.exceptions.ClientError as error:
                return error
            except botocore.exceptions.ParamValidationError as error:
                return error
            return 'deployment_updated'
        else:
            return 'deployment_not_found'

    def create(self):
        if self.detail:
            create_deployment_entry_response = self.create_deployment_entry()
        else:
            return format_response(400, 'failed', 'invalid detail', self.log)
        if create_deployment_entry_response == 'deployment_exists':
            return format_response(400, 'failed', 'deployment already exists - use update method to modify deployment parameters', self.log)
        elif create_deployment_entry_response == 'deployment_created':
            return format_response(200, 'success', 'create_deployment succeeded', None)
        else:
            return format_response(500, 'failed', f'create_deployment failed with error: {create_deployment_entry_response}', self.log)

    def delete(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def get(self):
        deployment_entry = self.get_deployment_entry()
        if deployment_entry is None:
            return format_response(400, 'failed', 'deployment not found - use create method to create deployment parameters', self.log)
        deployment_version = deployment_entry['Item']['deployment_version']['S']
        deployment_admin_email = deployment_entry['Item']['deployment_admin_email']['S']
        results_queue_expiration = deployment_entry['Item']['results_queue_expiration']['S']
        api_domain_name = deployment_entry['Item']['api_domain_name']['S']
        api_region = deployment_entry['Item']['api_region']['S']
        enable_task_results_logging = deployment_entry['Item']['enable_task_results_logging']['S']
        task_results_logging_cwlogs_group = deployment_entry['Item']['task_results_logging_cwlogs_group']['S']
        enable_playbook_results_logging = deployment_entry['Item']['enable_playbook_results_logging']['S']
        playbook_results_logging_cwlogs_group = deployment_entry['Item']['playbook_results_logging_cwlogs_group']['S']
        tfstate_s3_bucket = deployment_entry['Item']['tfstate_s3_bucket']['S']
        tfstate_s3_key = deployment_entry['Item']['tfstate_s3_key']['S']
        tfstate_s3_region = deployment_entry['Item']['tfstate_s3_region']['S']
        tfstate_dynamodb_table = deployment_entry['Item']['tfstate_dynamodb_table']['S']
        return format_response(
            200,
            'success',
            'get deployment succeeded',
            None,
            deployment_name=self.deployment_name,
            deployment_version=deployment_version,
            deployment_admin_email=deployment_admin_email,
            results_queue_expiration=results_queue_expiration,
            api_domain_name=api_domain_name,
            api_region=api_region,
            enable_task_results_logging=enable_task_results_logging,
            task_results_logging_cwlogs_group=task_results_logging_cwlogs_group,
            enable_playbook_results_logging=enable_playbook_results_logging,
            playbook_results_logging_cwlogs_group=playbook_results_logging_cwlogs_group,
            tfstate_s3_bucket=tfstate_s3_bucket,
            tfstate_s3_key=tfstate_s3_key,
            tfstate_s3_region=tfstate_s3_region,
            tfstate_dynamodb_table=tfstate_dynamodb_table
        )

    def list(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        if self.detail:
            update_deployment_entry_response = self.update_deployment_entry()
        else:
            return format_response(400, 'failed', 'invalid detail', self.log)
        if update_deployment_entry_response == 'deployment_not_found':
            return format_response(400, 'failed', 'deployment not found - use create method to create deployment parameters', self.log)
        elif update_deployment_entry_response == 'deployment_updated':
            return format_response(200, 'success', 'update deployment succeeded', None)
        else:
            return format_response(500, 'failed', f'deployment update failed with error: {update_deployment_entry_response}', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
