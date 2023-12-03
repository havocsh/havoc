import re
import ast
import json
import copy
import zlib
import base64
import botocore
import boto3
import time as t
from datetime import datetime, timedelta


class Deliver:

    def __init__(self, region, deployment_name, results_queue_expiration, enable_task_results_logging, results):
        self.region = region
        self.deployment_name = deployment_name
        self.results_queue_expiration = results_queue_expiration
        self.enable_task_results_logging = enable_task_results_logging
        self.user_id = None
        self.results = results
        self.task_name = None
        self.task_context = None
        self.task_type = None
        self.task_version = None
        self.__aws_dynamodb_client = None
        self.__aws_route53_client = None
        self.__aws_logs_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the Dynamodb boto3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    @property
    def aws_route53_client(self):
        """Returns the boto3 Route53 session (establishes one automatically if one does not already exist)"""
        if self.__aws_route53_client is None:
            self.__aws_route53_client = boto3.client('route53', region_name=self.region)
        return self.__aws_route53_client
    
    @property
    def aws_logs_client(self):
        """Returns the boto3 logs session (establishes one automatically if one does not already exist)"""
        if self.__aws_logs_client is None:
            self.__aws_logs_client = boto3.client('logs', region_name=self.region)
        return self.__aws_logs_client

    def get_domain_entry(self, domain_name):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-domains',
            Key={
                'domain_name': {'S': domain_name}
            }
        )

    def update_domain_entry(self, domain_name, domain_tasks, host_names):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-domains',
                Key={
                    'domain_name': {'S': domain_name}
                },
                UpdateExpression='set tasks=:tasks, host_names=:host_names',
                ExpressionAttributeValues={
                    ':tasks': {'SS': domain_tasks},
                    ':host_names': {'SS': host_names}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'domain_entry_updated'

    def delete_resource_record_set(self, hosted_zone, host_name, domain_name, ip_address):
        try:
            self.aws_route53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': f'{host_name}.{domain_name}',
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': ip_address
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'resource_record_set_deleted'

    def add_queue_attribute(self, stime, expire_time, task_instruct_id, task_instruct_instance, task_instruct_command,
                            task_instruct_args, task_host_name, task_domain_name, task_public_ip, task_local_ip, json_payload):
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
                                'task_domain_name=:task_domain_name, '
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

    def get_portgroup_entry(self, portgroup_name):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-portgroups',
            Key={
                'portgroup_name': {'S': portgroup_name}
            }
        )

    def update_portgroup_entry(self, portgroup_name, portgroup_tasks):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-portgroups',
                Key={
                    'portgroup_name': {'S': portgroup_name}
                },
                UpdateExpression='set tasks=:tasks',
                ExpressionAttributeValues={
                    ':tasks': {'SS': portgroup_tasks}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'portgroup_entry_updated'
    
    def put_log_event(self, payload, stime):
        log_stream_time = datetime.strftime(datetime.now(), '%Y/%m/%d')
        log_stream_name = f'{log_stream_time}/{self.task_name}'
        try:
            self.aws_logs_client.create_log_stream(
                logGroupName=f'{self.deployment_name}/task_results_logging',
                logStreamName=log_stream_name
            )
        except self.aws_logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        try:
            self.aws_logs_client.put_log_events(
                logGroupName=f'{self.deployment_name}/task_results_logging',
                logStreamName=log_stream_name,
                logEvents=[
                    {
                        'timestamp': int(stime) * 1000,
                        'message': payload
                    }
                ]
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'log_event_written'
    
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

    def deliver_result(self):
        # Set vars
        payload = None
        try:
            payload = json.loads(self.results['message'])
        except:
            pass
        if not payload:
            raw = re.search('\d+-\d+-\d+ \d+:\d+:\d+\+\d+ \[-\] ({.+})', self.results['message']).group(1)
            payload = ast.literal_eval(raw)

        if payload['instruct_user_id'] == 'None':
            self.user_id = payload['user_id']
        else:
            self.user_id = payload['instruct_user_id']
        self.task_name = payload['task_name']
        self.task_context = payload['task_context']
        self.task_type = payload['task_type']
        self.task_version = payload['task_version']
        task_instruct_id = payload['instruct_id']
        task_instruct_instance = payload['instruct_instance']
        task_instruct_command = payload['instruct_command']
        task_instruct_args = payload['instruct_args']
        task_public_ip = payload['public_ip']
        task_local_ip = payload['local_ip']
        task_forward_log = payload['forward_log']
        if 'end_time' in payload:
            task_end_time = payload['end_time']
        else:
            task_end_time = 'None'
        stime = payload['timestamp']
        from_timestamp = datetime.utcfromtimestamp(int(stime))
        expiration_time = from_timestamp + timedelta(days=self.results_queue_expiration)
        expiration_stime = expiration_time.strftime('%s')

        # Get task portgroups
        task_entry = self.get_task_entry()
        portgroups = task_entry['Item']['portgroups']['SS']
        task_host_name = task_entry['Item']['task_host_name']['S']
        task_domain_name = task_entry['Item']['task_domain_name']['S']

        # Clear out unwanted payload entries
        del payload['instruct_user_id']
        del payload['end_time']
        del payload['forward_log']

        # Log task result to CloudWatch Logs if enable_task_results_logging is set to true
        if self.enable_task_results_logging == 'true' and task_forward_log == 'True':
            cwlogs_payload = copy.deepcopy(payload)
            if task_instruct_command == 'terminate':
                del cwlogs_payload['instruct_args']
            if 'status' in cwlogs_payload['instruct_command_output']:
                if cwlogs_payload['instruct_command_output']['status'] == 'ready':
                    del cwlogs_payload['instruct_args']
            if 'get_shell_command_results' in cwlogs_payload['instruct_command_output']:
                get_shell_command_results = cwlogs_payload['instruct_command_output']['get_shell_command_results']
                tmp_results = json.loads(zlib.decompress(base64.b64decode(get_shell_command_results.encode())).decode())
                cwlogs_payload['instruct_command_output']['get_shell_command_results'] = tmp_results

            # Send result to CloudWatch Logs
            cwlogs_payload_json = json.dumps(cwlogs_payload)
            put_log_event_response = self.put_log_event(cwlogs_payload_json, stime)
            if put_log_event_response != 'log_event_written':
                print(f'Error writing task result log entry to CloudWatch Logs: {put_log_event_response}')

        # Add job to results queue
        db_payload = copy.deepcopy(payload)
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
        if task_instruct_command == 'terminate':
            for portgroup in portgroups:
                if portgroup != 'None':
                    portgroup_entry = self.get_portgroup_entry(portgroup)
                    portgroup_tasks = portgroup_entry['Item']['tasks']['SS']
                    if self.task_name in portgroup_tasks:
                        portgroup_tasks.remove(self.task_name)
                    if not portgroup_tasks:
                        portgroup_tasks.append('None')
                    update_portgroup_entry_response = self.update_portgroup_entry(portgroup, portgroup_tasks)
                    if update_portgroup_entry_response != 'portgroup_entry_updated':
                        print(f'Error updating portgroup entry: {update_portgroup_entry_response}')
            if task_host_name != 'None':
                domain_entry = self.get_domain_entry(task_domain_name)
                hosted_zone = domain_entry['Item']['hosted_zone']['S']
                domain_tasks = domain_entry['Item']['tasks']['SS']
                if self.task_name in domain_tasks:
                    domain_tasks.remove(self.task_name)
                if not domain_tasks:
                    domain_tasks.append('None')
                domain_host_names = domain_entry['Item']['host_names']['SS']
                if task_host_name in domain_host_names:
                    domain_host_names.remove(task_host_name)
                if not domain_host_names:
                    domain_host_names.append('None')
                update_domain_entry_response = self.update_domain_entry(task_domain_name, domain_tasks, domain_host_names)
                if update_domain_entry_response != 'domain_entry_updated':
                    print(f'Error updating domain entry: {update_domain_entry_response}')
                delete_resource_record_set_response = self.delete_resource_record_set(hosted_zone, task_host_name, task_domain_name, task_public_ip)
                if delete_resource_record_set_response != 'resource_record_set_deleted':
                    print(f'Error deleting resource record set: {delete_resource_record_set_response}')
            completed_instruction = self.update_task_entry(stime, 'terminated', task_end_time)
            if completed_instruction != 'task_entry_updated':
                print(f'Error updating task entry: {completed_instruction}')
            # Remove task from active_resources in deployment table
            deployment_details = self.get_deployment_entry
            active_resources = deployment_details['active_resources']['M']
            active_tasks = active_resources['tasks']['SS']
            active_tasks.remove(self.task_name)
            if len(active_tasks) == 0:
                active_tasks = ['None']
            active_resources['tasks']['SS'] = active_tasks
            update_deployment_entry_response = self.update_deployment_entry(active_resources)
            if update_deployment_entry_response != 'deployment_updated':
                print(f'Error updating deployment entry: {update_deployment_entry_response}')
            t.sleep(20)
        else:
            completed_instruction = self.update_task_entry(stime, 'idle', task_end_time)
            if completed_instruction != 'task_entry_updated':
                print(f'Error updating task entry: {completed_instruction}')

        if completed_instruction:
            add_queue_attribute_response = self.add_queue_attribute(stime, expiration_stime, task_instruct_id, task_instruct_instance,
                                                                    task_instruct_command, task_instruct_args_fixup, task_host_name,
                                                                    task_domain_name, task_public_ip, task_local_ip, json_payload)
            if add_queue_attribute_response != 'queue_attribute_added':
                print(f'Error adding queue attribute: {add_queue_attribute_response}')

        return True
