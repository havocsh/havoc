import re
import ast
import json
import copy
import botocore
import boto3
import time as t
from datetime import datetime, timedelta


class Deliver:

    def __init__(self, region, deployment_name, results_queue_expiration, results):
        self.region = region
        self.deployment_name = deployment_name
        self.results_queue_expiration = results_queue_expiration
        self.user_id = None
        self.results = results
        self.playbook_name = None
        self.playbook_type = None
        self.playbook_operator_version = None
        self.__aws_dynamodb_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the Dynamodb boto3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

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

        # Add stime to payload as timestamp
        payload['timestamp'] = stime

        # Get playbook portgroups
        playbook_entry = self.get_playbook_entry()
        self.playbook_type = playbook_entry['Item']['playbook_type']['S']
        
        # Clear out unwanted payload entries
        del payload['user_id']
        del payload['end_time']
        del payload['forward_log']

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

        add_queue_attribute_response = self.add_queue_attribute(stime, expiration_stime, operator_command, command_args_fixup, json_payload)
        if add_queue_attribute_response != 'queue_attribute_added':
            print(f'Error adding queue attribute: {add_queue_attribute_response}')

        return True
