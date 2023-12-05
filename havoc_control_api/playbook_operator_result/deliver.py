import re
import ast
import json
import copy
import botocore
import boto3
import time as t
from datetime import datetime, timedelta


class Deliver:

    def __init__(self, region, deployment_name, results_queue_expiration, enable_playbook_results_logging, results):
        self.region = region
        self.deployment_name = deployment_name
        self.results_queue_expiration = results_queue_expiration
        self.enable_playbook_results_logging = enable_playbook_results_logging
        self.user_id = None
        self.results = results
        self.playbook_name = None
        self.playbook_type = None
        self.playbook_operator_version = None
        self.__aws_dynamodb_client = None
        self.__aws_logs_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the Dynamodb boto3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    @property
    def aws_logs_client(self):
        """Returns the boto3 logs session (establishes one automatically if one does not already exist)"""
        if self.__aws_logs_client is None:
            self.__aws_logs_client = boto3.client('logs', region_name=self.region)
        return self.__aws_logs_client

    def add_queue_attribute(self, stime, expire_time, operator_command, command_args, json_payload):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbook-queue',
                Key={
                    'playbook_name': {'S': self.playbook_name},
                    'run_time': {'N': stime}
                },
                UpdateExpression='set '
                                'expire_time=:expire_time, '
                                'user_id=:user_id, '
                                'playbook_type=:playbook_type, '
                                'playbook_operator_version=:playbook_operator_version, '
                                'operator_command=:operator_command, '
                                'command_args=:command_args, '
                                'command_output=:payload',
                ExpressionAttributeValues={
                    ':expire_time': {'N': expire_time},
                    ':user_id': {'S': self.user_id},
                    ':playbook_type': {'S': self.playbook_type},
                    ':playbook_operator_version': {'S': self.playbook_operator_version},
                    ':operator_command': {'S': operator_command},
                    ':command_args': {'M': command_args},
                    ':payload': {'S': json_payload}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'queue_attribute_added'

    def get_playbook_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbooks',
            Key={
                'playbook_name': {'S': self.playbook_name}
            }
        )

    def update_playbook_entry(self):
        try:
            update_expression = 'set playbook_status=:playbook_status, ecs_task_id=:ecs_task_id'
            expression_attribute_values = {
                    ':playbook_status': {'S': 'not_running'},
                    ':ecs_task_id': {'S': 'None'}
                }
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_updated'
    
    def put_log_event(self, payload, stime):
        log_stream_time = datetime.strftime(datetime.now(), '%Y/%m/%d')
        log_stream_name = f'{log_stream_time}/{self.playbook_name}'
        try:
            self.aws_logs_client.create_log_stream(
                logGroupName=f'{self.deployment_name}/playbook_results_logging',
                logStreamName=log_stream_name
            )
        except self.aws_logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        try:
            self.aws_logs_client.put_log_events(
                logGroupName=f'{self.deployment_name}/playbook_results_logging',
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

        self.user_id = payload['user_id']
        self.playbook_name = payload['playbook_name']
        self.playbook_operator_version = payload['playbook_operator_version']
        operator_command = payload['operator_command']
        command_args = payload['command_args']
        stime = payload['timestamp']
        from_timestamp = datetime.utcfromtimestamp(int(stime))
        expiration_time = from_timestamp + timedelta(days=self.results_queue_expiration)
        expiration_stime = expiration_time.strftime('%s')

        # Get playbook portgroups
        playbook_entry = self.get_playbook_entry()
        self.playbook_type = playbook_entry['Item']['playbook_type']['S']
        
        # Clear out unwanted payload entries
        del payload['user_id']
        del payload['end_time']
        del payload['forward_log']

        # Log task result to CloudWatch Logs if enable_task_results_logging is set to true
        if self.enable_playbook_results_logging:

            # Send result to CloudWatch Logs
            payload_json = json.dumps(payload)
            put_log_event_response = self.put_log_event(payload_json, stime)
            if put_log_event_response != 'log_event_written':
                print(f'Error writing task result log entry to CloudWatch Logs: {put_log_event_response}')

        # Add job to results queue
        db_payload = copy.deepcopy(payload)
        del db_payload['playbook_name']
        del db_payload['playbook_operator_version']
        del db_payload['operator_command']
        del db_payload['command_args']
        del db_payload['timestamp']
        json_payload = json.dumps(db_payload['command_output'])
        command_args_fixup = {}
        for k, v in command_args.items():
            if isinstance(v, str):
                command_args_fixup[k] = {'S': v}
            if isinstance(v, int) and not isinstance(v, bool):
                command_args_fixup[k] = {'N': str(v)}
            if isinstance(v, bool):
                command_args_fixup[k] = {'BOOL': v}
            if isinstance(v, bytes):
                command_args_fixup[k] = {'B': v}
        if operator_command == 'terminate':
            completed_instruction = self.update_playbook_entry()
            if completed_instruction != 'playbook_entry_updated':
                print(f'Error updating playbook entry: {completed_instruction}')
            # Remove playbook from active_resources in deployment table
            deployment_details = self.get_deployment_entry()
            active_resources = deployment_details['Item']['active_resources']['M']
            active_playbooks = active_resources['playbooks']['SS']
            active_playbooks.remove(self.playbook_name)
            if len(active_playbooks) == 0:
                active_playbooks = ['None']
            active_resources['playbooks']['SS'] = active_playbooks
            update_deployment_entry_response = self.update_deployment_entry(active_resources)
            if update_deployment_entry_response != 'deployment_updated':
                print(f'Error updating deployment entry: {update_deployment_entry_response}')

        add_queue_attribute_response = self.add_queue_attribute(stime, expiration_stime, operator_command, command_args_fixup, json_payload)
        if add_queue_attribute_response != 'queue_attribute_added':
            print(f'Error adding queue attribute: {add_queue_attribute_response}')

        return True
