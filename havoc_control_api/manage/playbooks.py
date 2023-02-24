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


class Playbook:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Manage playbook operations.
        """
        self.region = region
        self.deployment_name = deployment_name
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.playbook_name = None
        self.playbook_type = None
        self.playbook_schedule = None
        self.playbook_timeout = None
        self.playbook_config = None
        self.config_pointer = None
        self.__aws_s3_client = None
        self.__aws_dynamodb_client = None

    @property
    def aws_s3_client(self):
        """Returns the boto3 S3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_s3_client is None:
            self.__aws_s3_client = boto3.client('s3', region_name=self.region)
        return self.__aws_s3_client
    
    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    def get_playbook_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbook_types',
            Key={
                'playbook_type': {'S': self.playbook_type}
            }
        )
    
    def query_playbooks(self):
        playbooks = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-playbooks'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                playbooks['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return playbooks
    
    def get_playbook_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbooks',
            Key={
                'playbook_name': {'S': self.playbook_name}
            }
        )
    
    def add_playbook_entry(self):
        playbook_type_entry = self.get_playbook_type_entry()
        if not playbook_type_entry:
            return 'playbook_type_not_found'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                },
                UpdateExpression='set '
                                'playbook_type=:playbook_type, '
                                'playbook_status=:playbook_status, '
                                'playbook_schedule=:playbook_schedule, '
                                'playbook_timeout=:playbook_timeout, '
                                'config_pointer=:config_pointer, '
                                'created_by=:created_by, '
                                'last_execution_time=:last_execution_time',
                ExpressionAttributeValues={
                    ':playbook_type': {'S': self.playbook_type},
                    ':playbook_status': {'S': 'not_running'}, 
                    ':playbook_schedule': {'S': self.playbook_schedule},
                    ':playbook_timeout': {'N': self.playbook_timeout},
                    ':config_pointer': {'S': self.config_pointer},
                    ':created_by': {'S': self.user_id},
                    ':last_execution_time': {'S': 'None'}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_created'
    
    def remove_playbook_entry(self):
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_removed'
    
    def get_object(self):
        try:
            get_object_response = self.aws_s3_client.get_object(
                Bucket=f'{self.deployment_name}-playbooks',
                Key=self.config_pointer
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return get_object_response
    
    def upload_object(self):
        try:
            self.aws_s3_client.put_object(
                Body=self.playbook_config,
                Bucket=f'{self.deployment_name}-playbooks',
                Key=self.config_pointer
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_uploaded'
    
    def delete_object(self):
        try:
            self.aws_s3_client.delete_object(
                Bucket=f'{self.deployment_name}-playbooks',
                Key=self.config_pointer
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_deleted'
    
    def add_playbook_configuration(self):
        existing_playbook = self.get_playbook_entry()
        if existing_playbook:
            return 'playbook_exists'
        add_playbook_entry_response = self.add_playbook_entry()
        if add_playbook_entry_response != 'playbook_entry_created':
            return add_playbook_entry_response
        upload_object_response = self.upload_object()
        if upload_object_response != 'object_uploaded':
            return upload_object_response
        return 'playbook_configuration_created'
    
    def delete_playbook_configuration(self):
        existing_playbook = self.get_playbook_entry()
        if not existing_playbook:
            return 'playbook_not_found'
        remove_playbook_entry_response = self.remove_playbook_entry()
        if remove_playbook_entry_response != 'playbook_entry_removed':
            return remove_playbook_entry_response
        delete_object_response = self.delete_object()
        if delete_object_response != 'object_deleted':
            return delete_object_response
        return 'playbook_configuration_deleted'
    
    def update_playbook_entry(self, playbook_status):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                },
                UpdateExpression='set playbook_status=:playbook_status',
                ExpressionAttributeValues={
                    ':playbook_status': {'S': playbook_status}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_updated'
    
    def terminate_playbook_operator(self):
        playbook_entry = self.get_playbook_entry()
        if not playbook_entry:
            return 'playbook_not_found'
        ecs_task_id = playbook_entry['Item']['ecs_task_id']['S']
        try:
            self.aws_ecs_client.stop_task(
                cluster=f'{self.deployment_name}-playbook-operator-cluster',
                task=ecs_task_id,
                reason=f'Playbook operator stopped by {self.user_id}'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        update_playbook_entry_response = self.update_task_entry('terminated')
        if update_playbook_entry_response != 'playbook_entry_updated':
            return update_playbook_entry_response
        return 'playbook_operator_terminated'
    
    def create(self):
        playbook_details = ['playbook_name', 'playbook_type', 'playbook_schedule', 'playbook_timeout', 'playbook_config']
        for i in playbook_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']
        self.playbook_type = self.detail['playbook_type']
        self.playbook_schedule = self.detail['playbook_schedule']
        self.playbook_timeout = self.detail['playbook_timeout']
        self.playbook_config = self.detail['playbook_config']
        self.config_pointer = f'{self.playbook_name}.config'

        # Attempt playbook configuration creation and return result
        add_playbook_configuration_response = self.add_playbook_configuration()
        if add_playbook_configuration_response == 'playbook_exists':
            return format_response(409, 'failed', f'playbook {self.playbook_name} already exists', self.log)
        elif add_playbook_configuration_response == 'playbook_type_not_found':
            return format_response(404, 'failed', f'playbook_type {self.playbook_type} does not exist', self.log)
        elif add_playbook_configuration_response == 'playbook_configuration_created':
            return format_response(200, 'success', 'playbook creation succeeded', None)
        else:
            return format_response(500, 'failed', f'playbook creation failed with error {add_playbook_configuration_response}', self.log)
    
    def delete(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']
        
        # Attempt playbook configuration deletion and return result
        delete_playbook_configuration_response = self.delete_playbook_configuration()
        if delete_playbook_configuration_response == 'playbook_not_found':
            return format_response(404, 'failed', f'playbook {self.playbook_name} does not exist', self.log)
        elif delete_playbook_configuration_response == 'playbook_configuration_deleted':
            return format_response(200, 'success', 'playbook deletion succeeded', None)
        else:
            return format_response(500, 'failed', f'playbook deletion failed with error {delete_playbook_configuration_response}', self.log)
        
    def get(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']
        playbook_entry = self.get_playbook_entry()
        if 'Item' not in playbook_entry:
            return format_response(404, 'failed', f'playbook_name {self.playbook_name} does not exist', self.log)
        playbook_type = playbook_entry['Item']['playbook_type']['S']
        playbook_status = playbook_entry['Item']['playbook_status']['S']
        playbook_schedule = playbook_entry['Item']['playbook_schedule']['S']
        playbook_timeout = playbook_entry['Item']['playbook_timeout']['N']
        self.config_pointer = playbook_entry['Item']['config_pointer']['S']
        get_object_results = self.get_object()
        playbook_config = None
        if 'Body' in get_object_results:
                playbook_config = get_object_results['Body'].read()
        created_by = playbook_entry['Item']['created_by']['S']
        last_executed_by = playbook_entry['Item']['last_executed_by']['S']
        last_execution_time = playbook_entry['Item']['last_execution_time']['S']
        return format_response(
            200, 'success', 'get playbook succeeded', None, playbook_name=self.playbook_name, playbook_type=playbook_type,
            playbook_status=playbook_status, playbook_schedule=playbook_schedule, playbook_timeout=playbook_timeout,
            playbook_config=playbook_config, created_by=created_by, last_executed_by=last_executed_by, last_execution_time=last_execution_time
        )
    
    def kill(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']

        terminate_playbook_operator_response = self.terminate_playbook_operator()
        if terminate_playbook_operator_response == 'playbook_not_found':
            return format_response(404, 'failed', f'playbook {self.playbook_name} does not exist', self.log)
        elif terminate_playbook_operator_response == 'playbook_operator_terminated':
            return format_response(200, 'success', 'kill playbook operator succeeded', None)
        else:
            return format_response(500, 'failed', f'kill playbook operator failed with error {terminate_playbook_operator_response}', self.log)
    
    def list(self):
        playbooks_list = []
        playbooks = self.query_playbooks()
        for item in playbooks['Items']:
            playbook_name = item['playbook_name']['S']
            playbooks_list.append(playbook_name)
        return format_response(200, 'success', 'list playbooks succeeded', None, playbooks=playbooks_list)
    
    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)