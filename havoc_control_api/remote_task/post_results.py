import json
import copy
import botocore
import boto3
from datetime import datetime, timedelta


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


class Deliver:

    def __init__(self, region, deployment_name, results_queue_expiration, enable_task_results_logging, user_id, results: dict, log):
        self.region = region
        self.deployment_name = deployment_name
        self.results_queue_expiration = results_queue_expiration
        self.enable_task_results_logging = enable_task_results_logging
        self.user_id = user_id
        self.results = results
        self.log = log
        self.task_name = None
        self.task_context = None
        self.task_type = None
        self.task_version = None
        self.__aws_dynamodb_client = None
        self.__aws_s3_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the Dynamodb boto3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    @property
    def aws_s3_client(self):
        """Returns the boto3 S3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_s3_client is None:
            self.__aws_s3_client = boto3.client('s3', region_name=self.region)
        return self.__aws_s3_client

    def add_queue_attribute(self, stime, expire_time, task_instruct_id, task_instruct_instance, task_instruct_command,
                            task_instruct_args, task_public_ip, task_local_ip, json_payload):
        task_host_name = 'None'
        task_domain_name = 'None'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-task-queue',
                Key={
                    'task_name': {'S': self.task_name},
                    'run_time': {'N': stime}
                },
                UpdateExpression='set '
                                'expire_time=:expire_time, '
                                'user_id=:user_id, '
                                'task_context=:task_context, '
                                'task_type=:task_type, '
                                'task_version=:task_version, '
                                'instruct_id=:instruct_id, '
                                'instruct_instance=:instruct_instance, '
                                'instruct_command=:instruct_command, '
                                'instruct_args=:instruct_args, '
                                'task_host_name=:task_host_name, '
                                'task_domain_name=:task_domain_name,'
                                'public_ip=:public_ip, '
                                'local_ip=:local_ip, '
                                'instruct_command_output=:payload',
                ExpressionAttributeValues={
                    ':expire_time': {'N': expire_time},
                    ':user_id': {'S': self.user_id},
                    ':task_context': {'S': self.task_context},
                    ':task_type': {'S': self.task_type},
                    ':task_version': {'S': self.task_version},
                    ':instruct_id': {'S': task_instruct_id},
                    ':instruct_instance': {'S': task_instruct_instance},
                    ':instruct_command': {'S': task_instruct_command},
                    ':instruct_args': {'M': task_instruct_args},
                    ':task_host_name': {'S': task_host_name},
                    ':task_domain_name': {'S': task_domain_name},
                    ':public_ip': {'S': task_public_ip},
                    ':local_ip': {'SS': task_local_ip},
                    ':payload': {'S': json_payload}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'queue_attribute_added'

    def get_user_details(self):
        """Returns details of a user"""
        response = self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-authorizer',
            Key={
                'user_id': {'S': self.user_id}
            }
        )
        return response
    
    def get_task_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-tasks',
            Key={
                'task_name': {'S': self.task_name}
            }
        )

    def update_task_entry(self, stime, task_status, task_end_time):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-tasks',
                Key={
                    'task_name': {'S': self.task_name}
                },
                UpdateExpression='set task_status=:task_status, last_instruct_time=:last_instruct_time, '
                                'scheduled_end_time=:scheduled_end_time',
                ExpressionAttributeValues={
                    ':task_status': {'S': task_status},
                    ':last_instruct_time': {'S': stime},
                    ':scheduled_end_time': {'S': task_end_time}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'task_entry_updated'
    
    def upload_object(self, payload_bytes, stime):
        try:
            self.aws_s3_client.put_object(
                Body=payload_bytes,
                Bucket=f'{self.deployment_name}-logging',
                Key=stime + '.txt'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 's3_object_uploaded'

    def deliver_result(self):
        # Set vars
        results_reqs = [
            'instruct_command_output', 'user_id', 'task_name', 'task_context', 'task_type', 'task_version',
            'instruct_user_id', 'instruct_id', 'instruct_instance', 'instruct_command', 'instruct_args', 'public_ip',
            'local_ip', 'end_time', 'forward_log', 'timestamp'
        ]
        for i in results_reqs:
            if i not in self.results:
                return format_response(400, 'failed', 'invalid results', self.log)

        self.task_name = self.results['task_name']
        self.task_context = self.results['task_context']
        self.task_type = self.results['task_type']
        self.task_version = self.results['task_version']
        task_instruct_id = self.results['instruct_id']
        task_instruct_instance = self.results['instruct_instance']
        task_instruct_command = self.results['instruct_command']
        task_instruct_args = self.results['instruct_args']
        task_public_ip = self.results['public_ip']
        task_local_ip = self.results['local_ip']
        task_forward_log = self.results['forward_log']
        stime = self.results['timestamp']
        from_timestamp = datetime.utcfromtimestamp(int(stime))
        expiration_time = from_timestamp + timedelta(days=self.results_queue_expiration)
        expiration_stime = expiration_time.strftime('%s')

        user_details = self.get_user_details()
        user_associated_task_name = user_details['Item']['task_name']['S']
        if self.task_name != user_associated_task_name and user_associated_task_name != '*':
            return format_response(403, 'failed', f'not allowed', self.log)

        if self.results['instruct_user_id'] != 'None':
            self.user_id = self.results['instruct_user_id']
        if 'end_time' in self.results:
            task_end_time = self.results['end_time']
        else:
            task_end_time = 'None'

        # Verify task
        task_entry = self.get_task_entry()
        if 'Item' not in task_entry:
            return format_response(404, 'failed', f'task_name {self.task_name} not found', self.log)

        # Clear out unwanted results entries
        del self.results['instruct_user_id']
        del self.results['end_time']
        del self.results['forward_log']

        # Log task result to S3 if enable_task_results_logging is set to true
        if self.enable_task_results_logging == 'true' and task_forward_log == 'True':
            s3_payload = copy.deepcopy(self.results)
            if task_instruct_command == 'terminate':
                del s3_payload['instruct_args']
            if 'status' in s3_payload['instruct_command_output']:
                if s3_payload['instruct_command_output']['status'] == 'ready':
                    del s3_payload['instruct_args']

            # Send result to S3
            payload_bytes = json.dumps(s3_payload).encode('utf-8')
            upload_object_response = self.upload_object(payload_bytes, stime)
            if upload_object_response != 's3_object_uploaded':
                print(f'Error uploading task results log entry to S3 bucket: {upload_object_response}')

        # Add job to results queue
        db_payload = copy.deepcopy(self.results)
        del db_payload['task_name']
        del db_payload['task_type']
        del db_payload['task_version']
        del db_payload['task_context']
        del db_payload['instruct_id']
        del db_payload['instruct_instance']
        del db_payload['instruct_command']
        del db_payload['instruct_args']
        del db_payload['public_ip']
        del db_payload['local_ip']
        del db_payload['timestamp']
        del db_payload['user_id']
        json_payload = json.dumps(db_payload['instruct_command_output'])
        task_instruct_args_fixup = {}
        for k, v in task_instruct_args.items():
            if isinstance(v, str):
                task_instruct_args_fixup[k] = {'S': v}
            if isinstance(v, int) and not isinstance(v, bool):
                task_instruct_args_fixup[k] = {'N': str(v)}
            if isinstance(v, bool):
                task_instruct_args_fixup[k] = {'BOOL': v}
            if isinstance(v, bytes):
                task_instruct_args_fixup[k] = {'B': v}
        add_queue_attribute_response = self.add_queue_attribute(stime, expiration_stime, task_instruct_id,
                                                                task_instruct_instance, task_instruct_command,
                                                                task_instruct_args_fixup, task_public_ip, 
                                                                task_local_ip, json_payload)
        if add_queue_attribute_response != 'queue_attribute_added':
            return format_response(500, 'failed', f'post_results failed with error {add_queue_attribute_response}', self.log)
        if task_instruct_command == 'terminate':
            update_task_entry_response = self.update_task_entry(stime, 'terminated', task_end_time)
            if update_task_entry_response != 'task_entry_updated':
                return format_response(500, 'failed', f'post_results failed with error {update_task_entry_response}', self.log)
        else:
            update_task_entry_response = self.update_task_entry(stime, 'idle', task_end_time)
            if update_task_entry_response != 'task_entry_updated':
                return format_response(500, 'failed', f'post_results failed with error {update_task_entry_response}', self.log)

        return format_response(200, 'success', 'post_results succeeded', None)
