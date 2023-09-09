import re
import json
import botocore
import boto3
from datetime import datetime
from datetime import timedelta


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


class WorkspaceAccess:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.access_type = 'GET'
        self.path = 'shared/'
        self.filename = None
        self.presigned_url = None
        self.fields = json.dumps(None)
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
    
    def query_workspace_get_urls(self):
        object_access_urls = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-workspace-access'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                object_access_urls['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return object_access_urls
    
    def get_workspace_get_url(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-workspace-access',
            Key={
                'object_access': {'S': f'{self.access_type} {self.path}{self.filename}'}
            }
        )
    
    def create_workspace_get_url(self, expiration):
        try:
            self.presigned_url = self.aws_s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': f'{self.deployment_name}-workspace',
                    'Key': self.path + self.filename
                },
                ExpiresIn=expiration
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'workspace_get_url_created'
    
    def add_workspace_get_url_entry(self, stime, expire_time):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-workspace-access',
                Key={
                    'object_access': {'S': f'{self.access_type} {self.path}{self.filename}'},
                    'create_time': {'N': stime}
                },
                UpdateExpression='set '
                                'expire_time=:expire_time, '
                                'presigned_url=:presigned_url, '
                                'fields=:fields, '
                                'created_by=:created_by',
                ExpressionAttributeValues={
                    ':expire_time': {'N': expire_time},
                    ':presigned_url': {'S': self.presigned_url},
                    ':fields': {'S': self.fields},
                    ':created_by': {'S': self.user_id}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'workspace_get_url_entry_added'

    def create(self):
        # Validate request details and assign parameters
        if 'filename' not in self.details:
            return format_response(400, 'failed', f'invalid detail: missing filename', self.log)
        self.filename = self.detail['filename']
        if 'expiration' in self.detail:
            expiration = self.detail['expiration']
        else:
            expiration = 3600
        
        # Setup expiration time parameters
        stime = datetime.utcnow().strftime('%s')
        from_timestamp = datetime.utcfromtimestamp(int(stime))
        expiration_time = from_timestamp + timedelta(seconds=expiration)
        expiration_stime = expiration_time.strftime('%s')
        
        # Generate the presigned URL and write the details to workspace-object-access-urls table
        create_workspace_get_url_response = self.create_workspace_get_url(expiration)
        if create_workspace_get_url_response != 'workspace_get_url_created':
            return format_response(400, 'failed', f'create_workspace_get_url failed with error {create_workspace_get_url_response}', self.log)
        
        add_workspace_get_url_entry_response = self.add_workspace_get_url_entry(stime, expiration_stime)
        if add_workspace_get_url_entry_response != 'workspace_get_url_entry_added':
            return format_response(400, 'failed', f'create_workspace_get_url failed with error {add_workspace_get_url_entry_response}', self.log)
        return format_response(200, 'success', 'create_workspace_get_url succeeded', None, workspace_get_url=self.presigned_url)

    def delete(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
    
    def get(self):
        # Validate request details and assign parameters
        if 'filename' not in self.details:
            return format_response(400, 'failed', f'invalid detail: missing filename', self.log)
        self.filename = self.detail['filename']

        # Get the object access url details
        get_workspace_get_url_response = self.get_workspace_get_url()
        if 'Item' not in get_workspace_get_url_response:
            return format_response(404, 'failed', 'workspace_get_url not found', self.log)
        
        # Setup response parameters
        object_access = get_workspace_get_url_response['Item']['object_access']['S']
        create_time = get_workspace_get_url_response['Item']['create_time']['N']
        expire_time = get_workspace_get_url_response['Item']['expire_time']['N']
        presigned_url = get_workspace_get_url_response['Item']['presigned_url']['S']
        created_by = get_workspace_get_url_response['Item']['created_by']['S']
        
        return format_response(
            200, 'success', 'get_workspace_get_url succeeded', None,
            object_access=object_access,
            presigned_url=presigned_url,
            create_time=create_time,
            expire_time=expire_time,
            created_by=created_by
        )

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
    
    def list(self):
        if 'filename' in self.detail:
            self.filename = self.detail['filename']
        else:
            self.filename = '.*'
        requested_object = re.compile(f'{self.access_type} {self.path}{self.filename}')
        objects_list = []
        workspace_get_urls_response = self.query_workspace_get_urls()
        if 'Items' in workspace_get_urls_response:
            for item in workspace_get_urls_response['Items']:
                object_access = item['object_access']['S']
                search = re.search(requested_object, object_access)
                if search:
                    url = item['presigned_url']
                    object_dict = {'object_access': object_access, 'presigned_url': url}
                    objects_list.append(object_dict)
        return format_response(200, 'success', 'list workspace object access urls succeeded', None, workspace_get_urls=objects_list)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
