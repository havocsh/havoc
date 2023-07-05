import ast
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
        self.playbook_timeout = None
        self.playbook_config = None
        self.__aws_dynamodb_client = None
        self.__aws_ecs_client = None
    
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
    
    def get_playbook_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-playbook-types',
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
                                'playbook_timeout=:playbook_timeout, '
                                'playbook_config=:playbook_config, '
                                'created_by=:created_by, '
                                'last_executed_by=:last_executed_by, '
                                'last_execution_time=:last_execution_time',
                ExpressionAttributeValues={
                    ':playbook_type': {'S': self.playbook_type},
                    ':playbook_status': {'S': 'not_running'}, 
                    ':playbook_timeout': {'N': self.playbook_timeout},
                    ':playbook_config': {'S': self.playbook_config},
                    ':created_by': {'S': self.user_id},
                    ':last_executed_by': {'S': 'None'},
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
    
    def add_playbook_configuration(self):
        existing_playbook = self.get_playbook_entry()
        if 'Item' in existing_playbook:
            return 'playbook_exists'
        add_playbook_entry_response = self.add_playbook_entry()
        if add_playbook_entry_response != 'playbook_entry_created':
            return add_playbook_entry_response
        return 'playbook_configuration_created'
    
    def delete_playbook_configuration(self):
        existing_playbook = self.get_playbook_entry()
        if 'Item' not in existing_playbook:
            return 'playbook_not_found'
        playbook_status = existing_playbook['Item']['playbook_status']['S']
        if playbook_status == 'running':
            return 'playbook_running'
        remove_playbook_entry_response = self.remove_playbook_entry()
        if remove_playbook_entry_response != 'playbook_entry_removed':
            return remove_playbook_entry_response
        return 'playbook_configuration_deleted'
    
    def update_playbook_entry(self):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-playbooks',
                Key={
                    'playbook_name': {'S': self.playbook_name}
                },
                UpdateExpression='set playbook_status=:playbook_status, '
                                 'ecs_task_id=:ecs_task_id',
                ExpressionAttributeValues={
                    ':playbook_status': {'S': 'not_running'},
                    ':ecs_task_id': {'S': 'None'}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'playbook_entry_updated'
    
    def terminate_playbook_operator(self):
        playbook_entry = self.get_playbook_entry()
        if 'Item' not in playbook_entry:
            return 'playbook_not_found'
        playbook_status = playbook_entry['Item']['playbook_status']['S']
        if playbook_status != 'running' and playbook_status != 'starting':
            return 'playbook_not_running'
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
        update_playbook_entry_response = self.update_playbook_entry()
        if update_playbook_entry_response != 'playbook_entry_updated':
            return update_playbook_entry_response
        return 'playbook_operator_terminated'
    
    def create(self):
        playbook_details = ['playbook_name', 'playbook_type', 'playbook_timeout', 'playbook_config']
        for i in playbook_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing required parameter {i}', self.log)
        self.playbook_name = self.detail['playbook_name']
        self.playbook_type = self.detail['playbook_type']
        self.playbook_timeout = str(self.detail['playbook_timeout'])
        try:
            int(self.playbook_timeout)
        except Exception as error:
            return format_response(400, 'failed', f'invalid detail: playbook_timeout assignment failed with error {error}', self.log)
        self.playbook_config = ast.literal_eval(self.detail['playbook_config'])
        if not isinstance(self.playbook_config, dict):
                return format_response(400, 'failed', f'invalid detail: playbook_config must be type dict', self.log)
        self.playbook_config = json.dumps(self.playbook_config)

        # Attempt playbook configuration creation and return result
        add_playbook_configuration_response = self.add_playbook_configuration()
        if add_playbook_configuration_response == 'playbook_exists':
            return format_response(409, 'failed', f'playbook {self.playbook_name} already exists', self.log)
        elif add_playbook_configuration_response == 'playbook_type_not_found':
            return format_response(404, 'failed', f'playbook_type {self.playbook_type} does not exist', self.log)
        elif add_playbook_configuration_response == 'playbook_configuration_created':
            return format_response(200, 'success', 'create_playbook succeeded', None)
        else:
            return format_response(500, 'failed', f'create_playbook failed with error {add_playbook_configuration_response}', self.log)
    
    def delete(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']
        
        # Attempt playbook configuration deletion and return result
        delete_playbook_configuration_response = self.delete_playbook_configuration()
        if delete_playbook_configuration_response == 'playbook_not_found':
            return format_response(404, 'failed', f'playbook {self.playbook_name} does not exist', self.log)
        elif delete_playbook_configuration_response == 'playbook_running':
            return format_response(409, 'failed', f'playbook {self.playbook_name} is currently running', self.log)
        elif delete_playbook_configuration_response == 'playbook_configuration_deleted':
            return format_response(200, 'success', 'delete_playbook succeeded', None)
        else:
            return format_response(500, 'failed', f'delete_playbook failed with error {delete_playbook_configuration_response}', self.log)
        
    def get(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']
        playbook_entry = self.get_playbook_entry()
        if 'Item' not in playbook_entry:
            return format_response(404, 'failed', f'playbook_name {self.playbook_name} does not exist', self.log)
        playbook_type = playbook_entry['Item']['playbook_type']['S']
        playbook_status = playbook_entry['Item']['playbook_status']['S']
        playbook_timeout = playbook_entry['Item']['playbook_timeout']['N']
        playbook_config = json.loads(playbook_entry['Item']['playbook_config']['S'])
        created_by = playbook_entry['Item']['created_by']['S']
        last_executed_by = playbook_entry['Item']['last_executed_by']['S']
        last_execution_time = playbook_entry['Item']['last_execution_time']['S']
        return format_response(
            200, 'success', 'get playbook succeeded', None, playbook_name=self.playbook_name, playbook_type=playbook_type,
            playbook_status=playbook_status, playbook_timeout=playbook_timeout, playbook_config=playbook_config, created_by=created_by,
            last_executed_by=last_executed_by, last_execution_time=last_execution_time
        )
    
    def kill(self):
        if 'playbook_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.playbook_name = self.detail['playbook_name']

        terminate_playbook_operator_response = self.terminate_playbook_operator()
        if terminate_playbook_operator_response == 'playbook_not_found':
            return format_response(404, 'failed', f'playbook {self.playbook_name} does not exist', self.log)
        elif terminate_playbook_operator_response == 'playbook_not_running':
            return format_response(409, 'failed', f'playbook {self.playbook_name} is not running or starting', self.log)
        elif terminate_playbook_operator_response == 'playbook_operator_terminated':
            return format_response(200, 'success', 'kill playbook operator succeeded', None)
        else:
            return format_response(500, 'failed', f'kill playbook operator failed with error {terminate_playbook_operator_response}', self.log)
    
    def list(self):
        if 'playbook_name_contains' in self.detail:
            pnf = self.detail['playbook_name_contains']
        else:
            pnf = ''
        if 'playbook_status' in self.detail:
            psf = self.detail['playbook_status'].lower()
        else:
            psf = 'running'
        playbooks_list = []
        playbooks_list_final = []
        playbooks = self.query_playbooks()
        if 'Items' in playbooks:
            for item in playbooks['Items']:
                playbook_name = item['playbook_name']['S']
                playbook_status = item['playbook_status']['S']
                playbook_dict = {'playbook_name': playbook_name, 'playbook_status': playbook_status}
                playbooks_list.append(playbook_dict)
            pn_filtered = [x for x in playbooks_list if pnf in x['playbook_name']]
            playbooks_list_final = [x for x in pn_filtered if psf == x['playbook_status'] or psf == 'all']
        return format_response(200, 'success', 'list playbooks succeeded', None, playbooks=playbooks_list_final)
    
    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)