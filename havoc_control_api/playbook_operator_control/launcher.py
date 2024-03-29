import ast
import json
import botocore
import boto3
import datetime
import time as t


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


class Playbook:

    def __init__(self, deployment_name, playbook_name, subnet, region, detail, user_id, log):
        """
        Instantiate a playbook operator instance
        """
        self.deployment_name = deployment_name
        self.playbook_name = playbook_name
        self.subnet = subnet
        self.region = region
        self.detail = detail
        self.user_id = user_id
        self.log = log
        self.playbook_type = None
        self.playbook_config = None
        self.playbook_timeout = None
        self.created_by = None
        self.run_ecs_task_response = None
        self.__aws_dynamodb_client = None
        self.__aws_ecs_client = None
        self.__aws_s3_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    @property
    def aws_ecs_client(self):
        """Returns the boto3 ECS session (establishes one automatically if one does not already exist)"""
        if self.__aws_ecs_client is None:
            self.__aws_ecs_client = boto3.client('ecs', region_name=self.region)
        return self.__aws_ecs_client

    @property
    def aws_s3_client(self):
        """Returns the boto3 S3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_s3_client is None:
            self.__aws_s3_client = boto3.client('s3', region_name=self.region)
        return self.__aws_s3_client
    
    def get_playbook_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbooks',
            Key={
                'playbook_name': {'S': self.playbook_name}
            }
        )
    
    def get_playbook_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbook-types',
            Key={
                'playbook_type': {'S': self.playbook_type}
            }
        )
    
    def get_deployment_details(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )
    
    def get_credentials(self, created_by):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-authorizer',
            Key={
                'user_id': {'S': created_by}
            }
        )

    def upload_object(self, payload, file_name):
        payload_bytes = json.dumps(payload).encode('utf-8')
        try:
            self.aws_s3_client.put_object(
                Body=payload_bytes,
                Bucket=f'{self.deployment_name}-playbooks',
                Key=self.playbook_name + '/' + file_name
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_uploaded'

    def run_ecs_task(self, end_time):
        try:
            response = self.aws_ecs_client.run_task(
                cluster=f'{self.deployment_name}-playbook-operator-cluster',
                count=1,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': [self.subnet],
                        'assignPublicIp': 'ENABLED'
                    }
                },
                overrides={
                    'containerOverrides': [
                        {
                            'name': f'{self.deployment_name}-playbook_operator',
                            'environment': [
                                {'name': 'REGION', 'value': self.region},
                                {'name': 'DEPLOYMENT_NAME', 'value': self.deployment_name},
                                {'name': 'USER_ID', 'value': self.user_id},
                                {'name': 'PLAYBOOK_NAME', 'value': self.playbook_name},
                                {'name': 'PLAYBOOK_TYPE', 'value': self.playbook_type},
                                {'name': 'END_TIME', 'value': end_time}
                            ]
                        }
                    ]
                },
                tags=[
                    {
                        'key': 'playbook_name',
                        'value': self.playbook_name
                    }
                ],
                taskDefinition=f'{self.deployment_name}-playbook_operator'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        self.run_ecs_task_response = response
        return 'ecs_task_ran'

    def get_ecstask_details(self, ecs_task_id):
        return self.aws_ecs_client.describe_tasks(
            cluster=f'{self.deployment_name}-playbook-operator-cluster',
            tasks=[ecs_task_id]
        )

    def update_playbook_entry(self, ecs_task_id, timestamp, end_time):
        playbook_status = 'running'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                },
                UpdateExpression='set '
                                'playbook_type=:playbook_type, '
                                'playbook_config=:playbook_config, '
                                'playbook_timeout=:playbook_timeout, '
                                'playbook_status=:playbook_status, '
                                'last_executed_by=:last_executed_by, '
                                'last_execution_time=:last_execution_time, '
                                'termination_time=:termination_time, '
                                'ecs_task_id=:ecs_task_id, '
                                'created_by=:created_by',
                ExpressionAttributeValues={
                    ':playbook_type': {'S': self.playbook_type},
                    ':playbook_config': {'S': json.dumps(self.playbook_config)},
                    ':playbook_timeout': {'N': str(self.playbook_timeout)},
                    ':playbook_status': {'S': playbook_status},
                    ':last_executed_by': {'S': self.user_id},
                    ':last_execution_time': {'S': timestamp},
                    ':termination_time': {'S': end_time},
                    ':ecs_task_id': {'S': ecs_task_id},
                    ':created_by': {'S': self.created_by}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_updated'
    
    def get_deployment_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )
    
    def update_deployment_entry(self, active_resources):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-deployment',
                Key={
                    'deployment_name': {'S': self.deployment_name}
                },
                UpdateExpression='set active_resources=:active_resources',
                ExpressionAttributeValues={
                    ':active_resources': {'M': active_resources}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'deployment_updated'

    def launch(self):
        if 'playbook_type' in self.detail:
            self.playbook_type = self.detail['playbook_type']
        
        if 'playbook_config' in self.detail:
            try:
                self.playbook_config = ast.literal_eval(self.detail['playbook_config'])
            except:
                pass
            if not self.playbook_config:
                self.playbook_config = self.detail['playbook_config']
            if not isinstance(self.playbook_config, dict):
                return format_response(400, 'failed', f'invalid detail: playbook_config must be type dict', self.log)
        
        if 'playbook_timeout' in self.detail:
            self.playbook_timeout = self.detail['playbook_timeout']

        playbook_entry = None
        get_playbook_entry_response = self.get_playbook_entry()
        if 'Item' in get_playbook_entry_response:
            playbook_entry = get_playbook_entry_response
        if not playbook_entry:
            if not self.playbook_type or not self.playbook_config or not self.playbook_timeout:
                return format_response(
                    404, 
                    'failed', 
                    f'playbook {self.playbook_name} does not exist and ad-hoc playbook requirements not met', 
                    self.log
                )
            get_playbook_type_entry_response = self.get_playbook_type_entry()
            if 'Item' not in get_playbook_type_entry_response:
                return format_response(404, 'failed', f'playbook_type {self.playbook_type} does not exist', self.log)
            self.created_by = self.user_id
            try:
                self.playbook_timeout = int(self.playbook_timeout)
            except Exception as e:
                return format_response(400, 'failed', f'invalid detail: assigning playbook_timeout failed with error {e}', self.log)
        else:
            if playbook_entry['Item']['playbook_status']['S'] != 'not_running':
                return format_response(409, 'failed', f'playbook {self.playbook_name} is already running', self.log)
            self.playbook_config = json.loads(playbook_entry['Item']['playbook_config']['S'])
            self.playbook_type = playbook_entry['Item']['playbook_type']['S']
            self.playbook_timeout = int(playbook_entry['Item']['playbook_timeout']['N'])
            self.created_by = playbook_entry['Item']['created_by']['S']

        current_time = datetime.datetime.now()
        end_time_object = current_time + datetime.timedelta(self.playbook_timeout)
        end_time = end_time_object.strftime('%s')
        timestamp = current_time.strftime('%s')

        deployment_details = self.get_deployment_details()
        api_region = deployment_details['Item']['api_region']['S']
        api_domain_name = deployment_details['Item']['api_domain_name']['S']

        credentials = self.get_credentials(self.created_by)
        api_key = credentials['Item']['api_key']['S']
        secret_key = credentials['Item']['secret_key']['S']

        run_ecs_task_response = self.run_ecs_task(end_time)
        if run_ecs_task_response != 'ecs_task_ran':
            return format_response(500, 'failed', f'playbook launch failed with error {run_ecs_task_response}', self.log)
        # Log task execution details
        ecs_task_id = self.run_ecs_task_response['tasks'][0]['taskArn']
        t.sleep(10)
        ecs_task_details = self.get_ecstask_details(ecs_task_id)
        recorded_info = {
            'playbook_executed': {
                'user_id': self.user_id,
                'playbook_name': self.playbook_name,
                'playbook_type': self.playbook_type,
                'playbook_config': self.playbook_config
            },
            'playbook_operator_task_details': ecs_task_details,
        }
        print(recorded_info)

        # Send Initialize command to the playbook operator
        operator_command = 'Initialize'
        command_args = {'no_args': 'True'}
        payload = {'operator_command': operator_command, 'command_args': command_args, 'timestamp': timestamp, 'end_time': end_time}
        file_name = '00_init.json'
        upload_object_response = self.upload_object(payload, file_name)
        if upload_object_response != 'object_uploaded':
            return format_response(500, 'failed', f'initialize playbook operator failed with error {upload_object_response}', self.log)

        # Send execute_playbook command to the playbook operator
        operator_command = 'execute_playbook'
        command_args = {
            'api_region': api_region,
            'api_domain_name': api_domain_name,
            'api_key': api_key,
            'secret': secret_key,
            'playbook_config': self.playbook_config
        }
        payload = {'operator_command': operator_command, 'command_args': command_args, 'timestamp': timestamp, 'end_time': end_time}
        file_name = 'execute_playbook.json'
        upload_object_response = self.upload_object(payload, file_name)
        if upload_object_response != 'object_uploaded':
            return format_response(500, 'failed', f'execute_playbook failed with error {upload_object_response}', self.log)

        # Add playbook entry to playbooks table in DynamoDB
        update_playbook_entry_response = self.update_playbook_entry(ecs_task_id, timestamp, end_time)
        if update_playbook_entry_response != 'playbook_entry_updated':
            return format_response(500, 'failed', f'launch playbook failed with error {update_playbook_entry_response}', self.log)
        
        # Add playbook to active_resources in deployment table
        deployment_details = self.get_deployment_entry()
        active_resources = deployment_details['Item']['active_resources']['M']
        active_playbooks = active_resources['playbooks']['SS']
        if active_playbooks == ['None']:
            active_playbooks = [self.playbook_name]
        else:
            active_playbooks.append(self.playbook_name)
        active_resources['playbooks']['SS'] = active_playbooks
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response

        # Send response
        return format_response(200, 'success', 'launch playbook succeeded', None)
