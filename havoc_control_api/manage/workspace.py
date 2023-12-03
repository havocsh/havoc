import re
import sys
import json
import botocore
import boto3
import base64


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


class Workspace:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.path = None
        self.file_name = None
        self.file_contents = None
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

    def upload_object(self):
        try:
            self.aws_s3_client.put_object(
                Body=self.file_contents,
                Bucket=f'{self.deployment_name}-workspace',
                Key=self.path + self.file_name
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_uploaded'

    def list_objects(self):
        if self.file_name:
            prefix = f'{self.path}{self.file_name}'
        else:
            prefix = self.path
        return self.aws_s3_client.list_objects_v2(
            Bucket=f'{self.deployment_name}-workspace',
            Prefix=prefix
        )
    
    def head_object(self):
        try:
            head_object_response = self.aws_s3_client.head_object(
                Bucket=f'{self.deployment_name}-workspace',
                Key=self.path + self.file_name
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return head_object_response

    def get_object(self):
        try:
            get_object_response = self.aws_s3_client.get_object(
                Bucket=f'{self.deployment_name}-workspace',
                Key=self.path + self.file_name
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return get_object_response

    def delete_object(self):
        try:
            self.aws_s3_client.delete_object(
                Bucket=f'{self.deployment_name}-workspace',
                Key=self.path + self.file_name
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_deleted'
    
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

    def list(self):
        if 'path' in self.detail:
            if self.detail['path'] not in ['shared/', 'upload/']:
                return format_response(400, 'failed', f'invalid path', self.log)
            path_list = [self.detail['path']]
        else:
            path_list = ['shared/', 'upload/']
        
        file_dict = {}
        for self.path in path_list:
            list_results = self.list_objects()
            regex = f'{self.path}(.*)'
            file_list = []
            if 'Contents' in list_results:
                for l in list_results['Contents']:
                    search = re.search(regex, l['Key'])
                    if search.group(1):
                        file_list.append(search.group(1))
            file_dict[self.path] = file_list
        return format_response(200, 'success', 'list files succeeded', None, files=file_dict)

    def get(self):
        filename_details = ['path', 'file_name']
        for i in filename_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing {i}', self.log)
        self.path = self.detail['path']
        self.file_name = self.detail['file_name']

        # Verify that file exists and get it's size, if size is larger than 26214400, return an error
        list_results = self.list_objects()
        if len(list_results['Contents']) == 0:
            return format_response(404, 'failed', 'file not found', self.log)
        file_details = self.head_object()
        if file_details['ContentLength'] > 26214400:
            return format_response(400, 'failed', 'max file size exceeded; use create_workspace_access_get_url to download large files', None,)
        
        # Get and return the file contents
        get_object_results = self.get_object()
        if 'Body' in get_object_results:
            object = get_object_results['Body'].read()
            encoded_file = base64.b64encode(object).decode()
            return format_response(200, 'success', 'get file succeeded', None, file_name=self.file_name, file_contents=encoded_file)
        else:
            return format_response(500, 'failed', f'retrieving object failed with error {get_object_results}', self.log)

    def create(self):
        filename_details = ['path', 'file_name', 'file_contents']
        for i in filename_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing {i}', self.log)
        self.path = self.detail['path']
        if self.path not in ['shared/', 'upload/']:
            return format_response(400, 'failed', f'invalid path', self.log)
        self.file_name = self.detail['file_name']
        self.file_contents = self.detail['file_contents']

        try:
            decoded_file = base64.b64decode(self.file_contents)
            decoded_file.decode()
        except:
            return format_response(415, 'failed', 'file_contents must be bytes', self.log)

        if sys.getsizeof(decoded_file) > 26214400:
            return format_response(413, 'failed', 'max file size exceeded; use create_workspace_access_put_url to upload large files', self.log)

        self.file_contents = decoded_file
        upload_object_response = self.upload_object()
        if upload_object_response == 'object_uploaded':
            # Add file to active_resources in deployment table
            deployment_details = self.get_deployment_entry
            active_resources = deployment_details['active_resources']['M']
            active_files = active_resources['files']['SS']
            if active_files == ['None']:
                active_files = [self.file_name]
            else:
                active_files.append(self.file_name)
            active_resources['files']['SS'] = active_files
            update_deployment_entry_response = self.update_deployment_entry(active_resources)
            if update_deployment_entry_response != 'deployment_updated':
                return format_response(500, 'failed', f'create_file failed with error {update_deployment_entry_response}', self.log)
            return format_response(200, 'success', 'create_file succeeded', None)
        else:
            return format_response(500, 'failed', f'create_file failed with error {upload_object_response}', self.log)

    def delete(self):
        filename_details = ['path', 'file_name']
        for i in filename_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing {i}', self.log)
        self.path = self.detail['path']
        if self.path not in ['shared/', 'upload/']:
            return format_response(400, 'failed', f'invalid path', self.log)
        self.file_name = self.detail['file_name']

        # List files in bucket to confirm that file is present
        list_results = self.list_objects()
        if len(list_results['Contents']) == 0:
            return format_response(404, 'failed', 'file not found', self.log)
        
        # Delete the file and return a response
        delete_object_response = self.delete_object()
        if delete_object_response == 'object_deleted':
            # Remove file from active_resources in deployment table
            deployment_details = self.get_deployment_entry
            active_resources = deployment_details['active_resources']['M']
            active_files = active_resources['files']['SS']
            active_files.remove(self.file_name)
            if len(active_files) == 0:
                active_files = ['None']
            active_resources['files']['SS'] = active_files
            update_deployment_entry_response = self.update_deployment_entry(active_resources)
            if update_deployment_entry_response != 'deployment_updated':
                return format_response(500, 'failed', f'delete_file failed with error {update_deployment_entry_response}', self.log)
            return format_response(200, 'success', 'delete_file succeeded', None)
        else:
            return format_response(500, 'failed', f'delete_file failed with error {delete_object_response}', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
