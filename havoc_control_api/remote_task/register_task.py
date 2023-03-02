import json
import botocore
import boto3
from datetime import datetime


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


class Task:

    def __init__(self, region, deployment_name, user_id, detail: dict, log):
        """
        Register a remote task instance
        """
        self.region = region
        self.deployment_name = deployment_name
        self.detail = detail
        self.user_id = user_id
        self.log = log
        self.task_name = None
        self.task_context = None
        self.task_type = None
        self.task_version = None
        self.__aws_dynamodb_client = None
        self.__aws_s3_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    @property
    def aws_s3_client(self):
        """Returns the boto3 S3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_s3_client is None:
            self.__aws_s3_client = boto3.client('s3', region_name=self.region)
        return self.__aws_s3_client

    def get_task_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-task-types',
            Key={
                'task_type': {'S': self.task_type}
            }
        )

    def get_task_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-tasks',
            Key={
                'task_name': {'S': self.task_name}
            }
        )

    def upload_object(self, instruct_user_id, instruct_instance, instruct_command, instruct_args, timestamp, end_time):
        payload = {
            'instruct_user_id': instruct_user_id, 'instruct_instance': instruct_instance,
            'instruct_command': instruct_command, 'instruct_args': instruct_args, 'timestamp': timestamp,
            'end_time': end_time
        }
        payload_bytes = json.dumps(payload).encode('utf-8')
        try:
            self.aws_s3_client.put_object(
                Body=payload_bytes,
                Bucket=f'{self.deployment_name}-workspace',
                Key=self.task_name + '/init.txt'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'object_uploaded'

    def add_task_entry(self, instruct_user_id, instruct_instance, instruct_command, instruct_args, public_ip, local_ip,
                       portgroups, ecs_task_id, timestamp, end_time):
        task_status = 'starting'
        task_host_name = 'None'
        task_domain_name = 'None'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-tasks',
                Key={
                    'task_name': {'S': self.task_name}
                },
                UpdateExpression='set '
                                'task_context=:task_context, '
                                'task_status=:task_status, '
                                'task_host_name=:task_host_name, '
                                'task_domain_name=:task_domain_name, '
                                'public_ip=:public_ip, '
                                'local_ip=:local_ip, '
                                'portgroups=:portgroups, '
                                'task_type=:task_type, '
                                'task_version=:task_version, '
                                'instruct_instances=:instruct_instances, '
                                'last_instruct_user_id=:last_instruct_user_id, '
                                'last_instruct_instance=:last_instruct_instance, '
                                'last_instruct_command=:last_instruct_command, '
                                'last_instruct_args=:last_instruct_args, '
                                'last_instruct_time=:last_instruct_time, '
                                'create_time=:create_time, '
                                'scheduled_end_time=:scheduled_end_time, '
                                'user_id=:user_id, '
                                'ecs_task_id=:ecs_task_id',
                ExpressionAttributeValues={
                    ':task_context': {'S': self.task_context},
                    ':task_status': {'S': task_status},
                    ':task_host_name': {'S': task_host_name},
                    ':task_domain_name': {'S': task_domain_name},
                    ':public_ip': {'S': public_ip},
                    ':local_ip': {'SS': local_ip},
                    ':portgroups': {'SS': portgroups},
                    ':task_type': {'S': self.task_type},
                    ':task_version': {'S': self.task_version},
                    ':instruct_instances': {'SS': [instruct_instance]},
                    ':last_instruct_user_id': {'S': instruct_user_id},
                    ':last_instruct_instance': {'S': instruct_instance},
                    ':last_instruct_command': {'S': instruct_command},
                    ':last_instruct_args': {'M': instruct_args},
                    ':last_instruct_time': {'S': 'None'},
                    ':create_time': {'S': timestamp},
                    ':scheduled_end_time': {'S': end_time},
                    ':user_id': {'S': self.user_id},
                    ':ecs_task_id': {'S': ecs_task_id}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'task_entry_added'

    def registration(self):
        portgroups = ['None']
        ecs_task_id = 'remote_task'
        instruct_user_id = 'None'
        instruct_instance = 'None'
        instruct_command = 'Initialize'
        instruct_args = {'no_args': 'True'}
        if 'end_time' in self.detail:
            end_time = self.detail['end_time']
        else:
            end_time = 'None'

        instruct_details = ['task_name', 'task_context', 'task_type', 'task_version', 'public_ip']
        for i in instruct_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)

        self.task_name = self.detail['task_name']
        self.task_context = self.detail['task_context']
        self.task_type = self.detail['task_type']
        self.task_version = self.detail['task_version']
        public_ip = self.detail['public_ip']
        local_ip = self.detail['local_ip']
        if not isinstance(local_ip, list):
            return format_response(400, 'failed', 'local_ip must be of type list', self.log)

        task_type_entry = self.get_task_type_entry()
        if not task_type_entry:
            return format_response(404, 'failed', f'task_type {self.task_type} does not exist', self.log)

        # Verify that the task_name is unique
        conflict = self.get_task_entry()
        task_status = conflict['Item']['task_status']['S']
        if task_status != 'terminated':
            return format_response(409, 'failed', f'{self.task_name} already exists as a running task', self.log)

        recorded_info = {
            'task_registered': {
                'user_id': self.user_id,
                'task_name': self.task_name,
                'task_context': self.task_context,
                'task_type': self.task_type,
                'task_version': self.task_version,
                'interface_details': local_ip
            }
        }
        print(recorded_info)

        timestamp = datetime.now().strftime('%s')
        upload_object_response = self.upload_object(
            instruct_user_id, instruct_instance, instruct_command, instruct_args, timestamp, end_time)
        if upload_object_response != 'object_uploaded':
            return format_response(500, 'failed', f'register_task failed with error {upload_object_response}', self.log)

        instruct_args_fixup = {'no_args': {'S': 'True'}}
        # Add task entry to tasks table in DynamoDB
        add_task_entry_response = self.add_task_entry(
            instruct_user_id, instruct_instance, instruct_command, instruct_args_fixup, public_ip, local_ip, portgroups, 
            ecs_task_id, timestamp, end_time)
        if add_task_entry_response != 'task_entry_added':
            return format_response(500, 'failed', f'register_task failed with error {add_task_entry_response}', self.log)

        # Send response
        return format_response(200, 'success', 'register_task succeeded', None)
