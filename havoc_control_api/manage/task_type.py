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
        Register or deregister a task_type
        """
        self.region = region
        self.deployment_name = deployment_name
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.task_type = None
        self.task_version = None
        self.source_image = None
        self.capabilities = None
        self.cpu = None
        self.memory = None
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

    def query_task_types(self):
        task_types = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-task-types'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                task_types['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return task_types

    def get_task_type_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-task-types',
            Key={
                'task_type': {'S': self.task_type}
            }
        )

    def add_task_type_entry(self, task_definition_arn):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-task-types',
                Key={
                    'task_type': {'S': self.task_type}
                },
                UpdateExpression='set '
                                'task_type=:task_type, '
                                'source_image=:source_image, '
                                'created_by=:created_by, '
                                'task_definition_arn=:task_definition_arn, '
                                'capabilities=:capabilities, '
                                'cpu=:cpu, '
                                'memory=:memory',
                ExpressionAttributeValues={
                    ':task_type': {'S': self.task_type},
                    ':task_version': {'S': self.task_version}, 
                    ':source_image': {'S': self.source_image},
                    ':created_by': {'S': self.user_id},
                    ':task_definition_arn': {'S': task_definition_arn},
                    ':capabilities': {'SS': self.capabilities},
                    ':cpu': {'N': self.cpu},
                    ':memory': {'N': self.memory}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error['Error']
        except botocore.exceptions.ParamValidationError as error:
            return error['Error']
        return 'task_type_entry_created'

    def remove_task_type_entry(self):
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-task-types',
                Key={
                    'task_type': {'S': self.task_type}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error['Error']
        except botocore.exceptions.ParamValidationError as error:
            return error['Error']
        return 'task_type_entry_removed'

    def add_ecs_task_definition(self):
        existing_task_type = self.get_task_type_entry()
        if existing_task_type:
            return 'task_type_exists'
        try:
            task_registration = self.aws_ecs_client.register_task_definition(
                family=f'{self.deployment_name}-{self.task_type}',
                taskRoleArn=f'{self.deployment_name}-task-role',
                executionRoleArn=f'{self.deployment_name}-execution-role',
                networkMode='awsvpc',
                containerDefinitions=[
                    {
                        'name': f'{self.deployment_name}-{self.task_type}',
                        'image': self.source_image,
                        'essential': True,
                        'entryPoint': [
                            '/bin/bash', '-c'
                        ],
                        'command': [
                            '/usr/bin/supervisord', '-c', '/etc/supervisor/conf.d/supervisord.conf'
                        ],
                        'logConfiguration': {
                            'logDriver': 'awslogs',
                            'options': {
                                'awslogs-group': self.deployment_name,
                                'awslogs-region': self.region,
                                'awslogs-stream-prefix': self.task_type
                            }
                        }
                    }
                ],
                requiresCompatibilities=['FARGATE'],
                cpu=self.cpu,
                memory=self.memory,
                tags=[
                    {
                        'key': 'deployment_name',
                        'value': self.deployment_name
                    },
                    {
                        'key': 'name',
                        'value': f'{self.deployment_name}-{self.task_type}'
                    },
                    {
                        'key': 'task_version',
                        'value': f'{self.task_version}'
                    }
                ]
            )
        except botocore.exceptions.ClientError as error:
            return error['Error']
        except botocore.exceptions.ParamValidationError as error:
            return error['Error']
        task_definition_arn = task_registration['taskDefinition']['taskDefinitionArn']
        add_task_type_entry_response = self.add_task_type_entry(task_definition_arn)
        if add_task_type_entry_response == 'task_type_entry_created':
            return 'task_type_created'
        else:
            return add_task_type_entry_response

    def remove_ecs_task_definition(self):
        task_type = self.get_task_type_entry()
        if not task_type:
            return 'task_type_not_found'
        task_definition_arn = task_type['Item']['task_definition_arn']['S']
        try:
            self.aws_ecs_client.deregister_task_definition(
                taskDefinition=task_definition_arn
            )
        except botocore.exceptions.ClientError as error:
            return error['Error']
        except botocore.exceptions.ParamValidationError as error:
            return error['Error']
        remove_task_type_entry_response = self.remove_task_type_entry()
        if remove_task_type_entry_response == 'task_type_entry_removed':
            return 'task_definition_removed'
        else:
            return remove_task_type_entry_response

    def create(self):
        task_details = ['task_type', 'task_version', 'source_image', 'capabilities', 'cpu', 'memory']
        for i in task_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)
        self.task_type = self.detail['task_type']
        self.task_version = self.detail['task_version']
        self.source_image = self.detail['source_image']
        self.capabilities = self.detail['capabilities']
        self.cpu = self.detail['cpu']
        self.memory = self.detail['memory']

        # Attempt ECS task definition registration and return result
        add_ecs_task_definition_response = self.add_ecs_task_definition()
        if add_ecs_task_definition_response == 'task_type_exists':
            return format_response(409, 'failed', f'task_type {self.task_type} already exists', self.log)
        elif add_ecs_task_definition_response == 'task_type_created':
            return format_response(200, 'success', 'task_type creation succeeded', None)
        else:
            return format_response(500, 'failed', f'task_type creation failed with error {add_ecs_task_definition_response}', self.log)

    def delete(self):
        if 'task_type' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.task_type = self.detail['task_type']
        
        # Attempt ECS task definition removal
        remove_ecs_task_definition_response = self.remove_ecs_task_definition()
        if remove_ecs_task_definition_response == 'task_type_not_found':
            return format_response(404, 'failed', f'task_type {self.task_type} does not exist', self.log)
        elif remove_ecs_task_definition_response == 'task_definition_removed':
            return format_response(200, 'success', 'delete task_type succeeded', None)
        else:
            return format_response(500, 'failed', f'task_type deletion failed with error {remove_ecs_task_definition_response}', self.log)
        
        

    def get(self):
        if 'task_type' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.task_type = self.detail['task_type']
        task_type_entry = self.get_task_type_entry()
        if 'Item' not in task_type_entry:
            return format_response(404, 'failed', f'task_type {self.task_type} does not exist', self.log)
        task_version = task_type_entry['Item']['task_version']['S']
        capabilities = task_type_entry['Item']['capabilities']['SS']
        source_image = task_type_entry['Item']['source_image']['S']
        created_by = task_type_entry['Item']['created_by']['S']
        cpu = task_type_entry['Item']['cpu']['N']
        memory = task_type_entry['Item']['memory']['N']
        return format_response(
            200, 'success', 'get task_type succeeded', None, task_type=self.task_type, task_version=task_version,
            capabilities=capabilities, source_image=source_image, created_by=created_by, cpu=cpu, memory=memory
        )

    def list(self):
        task_types_list = []
        task_types = self.query_task_types()
        for item in task_types['Items']:
            task_type = item['task_type']['S']
            task_types_list.append(task_type)
        return format_response(200, 'success', 'list task_type succeeded', None, task_types=task_types_list)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)


