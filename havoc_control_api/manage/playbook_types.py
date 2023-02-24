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


class Registration:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Register playbook types.
        """
        self.region = region
        self.deployment_name = deployment_name
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.playbook_type = None
        self.playbook_version = None
        self.playbook_template = None
        self.template_pointer = None
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
    
    def query_playbook_types(self):
        playbook_types = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-playbook-types'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                playbook_types['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return playbook_types
    
    def get_playbook_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbook-types',
            Key={
                'playbook_type': {'S': self.playbook_type}
            }
        )
    
    def add_playbook_type_entry(self):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbook-types',
                Key={
                    'playbook_type': {'S': self.playbook_type}
                },
                UpdateExpression='set '
                                'playbook_version=:playbook_version, '
                                'template_pointer=:template_pointer, '
                                'created_by=:created_by',
                ExpressionAttributeValues={
                    ':playbook_version': {'S': self.playbook_version},
                    ':template_pointer': {'S': self.template_pointer},
                    ':created_by': {'S': self.user_id}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_type_entry_created'
    
    def remove_playbook_type_entry(self):
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-playbook-types',
                Key={
                    'playbook_type': {'S': self.playbook_type}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_type_entry_removed'
    
    def get_object(self):
        try:
            get_object_response = self.aws_s3_client.get_object(
                Bucket=f'{self.deployment_name}-playbook-types',
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
                Body=self.playbook_template,
                Bucket=f'{self.deployment_name}-playbook-types',
                Key=self.template_pointer
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_uploaded'
    
    def delete_object(self):
        try:
            self.aws_s3_client.delete_object(
                Bucket=f'{self.deployment_name}-playbook-types',
                Key=self.template_pointer
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_deleted'
    
    def add_playbook_type(self):
        existing_playbook_type = self.get_playbook_type_entry()
        if existing_playbook_type:
            return 'playbook_type_exists'
        add_playbook_type_entry_response = self.add_playbook_type_entry()
        if add_playbook_type_entry_response != 'playbook_type_entry_created':
            return add_playbook_type_entry_response
        upload_object_response = self.upload_object()
        if upload_object_response != 'object_uploaded':
            return upload_object_response
        return 'playbook_type_created'
    
    def delete_playbook_type(self):
        existing_playbook_type = self.get_playbook_type_entry()
        if not existing_playbook_type:
            return 'playbook_type_not_found'
        remove_playbook_type_entry_response = self.remove_playbook_type_entry()
        if remove_playbook_type_entry_response != 'playbook_type_entry_removed':
            return remove_playbook_type_entry_response
        delete_object_response = self.delete_object()
        if delete_object_response != 'object_deleted':
            return delete_object_response
        return 'playbook_type_deleted'
    
    def create(self):
        task_details = ['playbook_type', 'playbook_version', 'playbook_template']
        for i in task_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_type = self.detail['playbook_type']
        self.playbook_version = self.detail['playbook_version']
        self.playbook_template = self.detail['playbook_template']
        self.template_pointer = f'{self.playbook_type}.template'

        # Attempt playbook configuration creation and return result
        add_playbook_type_response = self.add_playbook_type()
        if add_playbook_type_response == 'playbook_type_exists':
            return format_response(409, 'failed', f'playbook_type {self.playbook_type} already exists', self.log)
        elif add_playbook_type_response == 'playbook_type_created':
            return format_response(200, 'success', 'playbook_type creation succeeded', None)
        else:
            return format_response(500, 'failed', f'playbook_type creation failed with error {add_playbook_type_response}', self.log)
    
    def delete(self):
        if 'playbook_type' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_type = self.detail['playbook_type']
        
        # Attempt playbook configuration deletion and return result
        delete_playbook_type_response = self.delete_playbook_type()
        if delete_playbook_type_response == 'playbook_type_not_found':
            return format_response(404, 'failed', f'playbook {self.playbook_type} does not exist', self.log)
        elif delete_playbook_type_response == 'playbook_type_deleted':
            return format_response(200, 'success', 'playbook_type deletion succeeded', None)
        else:
            return format_response(500, 'failed', f'playbook_type deletion failed with error {delete_playbook_type_response}', self.log)
        
    def get(self):
        if 'playbook_type' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_type = self.detail['playbook_type']
        playbook_type_entry = self.get_playbook_type_entry()
        if not playbook_type_entry:
            return format_response(404, 'failed', f'playbook_type {self.playbook_type} does not exist', self.log)
        playbook_version = playbook_type_entry['Item']['playbook_schedule']['S']
        self.template_pointer = playbook_type_entry['Item']['config_pointer']['S']
        get_object_results = self.get_object()
        playbook_template = None
        if 'Body' in get_object_results:
                playbook_template = get_object_results['Body'].read()
        created_by = playbook_type_entry['Item']['created_by']['S']
        return format_response(
            200, 'success', 'get playbook_type succeeded', None, playbook_type=self.playbook_type,
            playbook_version=playbook_version, playbook_template=playbook_template, created_by=created_by
        )
    
    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
    
    def list(self):
        playbook_types_list = []
        playbook_types = self.query_playbook_types()
        for item in playbook_types['Items']:
            playbook_type = item['playbook_type']['S']
            playbook_types_list.append(playbook_type)
        return format_response(200, 'success', 'list playbook_types succeeded', None, playbook_types=playbook_types_list)
    
    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)