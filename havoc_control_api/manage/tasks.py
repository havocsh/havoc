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


class Tasks:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.task_name = None
        self.__aws_dynamodb_client = None
        self.__aws_ecs_client = None
        self.__aws_route53_client = None

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

    @property
    def aws_route53_client(self):
        """Returns the boto3 Route53 session (establishes one automatically if one does not already exist)"""
        if self.__aws_route53_client is None:
            self.__aws_route53_client = boto3.client('route53', region_name=self.region)
        return self.__aws_route53_client

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
        return 'resource_record_deleted'

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

    def query_tasks(self):
        tasks = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-tasks'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                tasks['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return tasks

    def get_task_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-tasks',
            Key={
                'task_name': {'S': self.task_name}
            }
        )

    def update_task_entry(self, task_status):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-tasks',
                Key={
                    'task_name': {'S': self.task_name}
                },
                UpdateExpression='set task_status=:task_status',
                ExpressionAttributeValues={
                    ':task_status': {'S': task_status}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'task_entry_updated'
    
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

    def terminate_task(self):
        task_entry = self.get_task_entry()
        if 'Item' not in task_entry:
            return 'task_not_found'
        # Verify that the task is not associated with active listeners
        if 'None' not in task_entry['Item']['listeners']['SS']:
            return 'task_associated_with_listener'
        ecs_task_id = task_entry['Item']['ecs_task_id']['S']
        if ecs_task_id == 'remote_task':
            update_task_entry_response = self.update_task_entry('terminated')
            if update_task_entry_response == 'task_entry_updated':
                return 'task_terminated'
            else:
                return update_task_entry_response
        portgroups = task_entry['Item']['portgroups']['SS']
        for portgroup in portgroups:
            if portgroup != 'None':
                portgroup_entry = self.get_portgroup_entry(portgroup)
                tasks = portgroup_entry['Item']['tasks']['SS']
                tasks.remove(self.task_name)
                if not tasks:
                    tasks.append('None')
                portgroup_entry_update = self.update_portgroup_entry(portgroup, tasks)
                if portgroup_entry_update != 'portgroup_entry_updated':
                    return portgroup_entry_update
        try:
            self.aws_ecs_client.stop_task(
                cluster=f'{self.deployment_name}-task-cluster',
                task=ecs_task_id,
                reason=f'Task stopped by {self.user_id}'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        if task_entry['Item']['task_domain_name']['S'] != 'None':
            task_public_ip = task_entry['Item']['public_ip']['S']
            task_host_name = task_entry['Item']['task_host_name']['S']
            task_domain_name = task_entry['Item']['task_domain_name']['S']
            domain_entry = self.get_domain_entry(task_domain_name)
            hosted_zone = domain_entry['Item']['hosted_zone']['S']
            tasks = domain_entry['Item']['tasks']['SS']
            tasks.remove(self.task_name)
            if not tasks:
                tasks.append('None')
            domain_host_names = domain_entry['Item']['host_names']['SS']
            domain_host_names.remove(task_host_name)
            if not domain_host_names:
                domain_host_names.append('None')
            update_domain_entry_response = self.update_domain_entry(task_domain_name, tasks, domain_host_names)
            if update_domain_entry_response != 'domain_entry_updated':
                return update_domain_entry_response
            delete_resource_record_set_response = self.delete_resource_record_set(hosted_zone, task_host_name, task_domain_name, task_public_ip)
            if delete_resource_record_set_response != 'resource_record_deleted':
                return delete_resource_record_set_response
        update_task_entry_response = self.update_task_entry('terminated')
        if update_task_entry_response != 'task_entry_updated':
            return update_task_entry_response
        
        # Remove task from active_resources in deployment table
        deployment_details = self.get_deployment_entry()
        active_resources = deployment_details['Item']['active_resources']['M']
        active_tasks = active_resources['tasks']['SS']
        active_tasks.remove(self.task_name)
        if len(active_tasks) == 0:
            active_tasks = ['None']
        active_resources['tasks']['SS'] = active_tasks
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response
        return 'task_terminated'

    def get(self):
        if 'task_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.task_name = self.detail['task_name']

        task_entry = self.get_task_entry()
        if 'Item' not in task_entry:
            return format_response(404, 'failed', f'task {self.task_name} does not exist', self.log)

        task_item = task_entry['Item']
        task_name = task_item['task_name']['S']
        task_type = task_item['task_type']['S']
        task_version = task_item['task_version']['S']
        task_context = task_item['task_context']['S']
        task_status = task_item['task_status']['S']
        public_ip = task_item['public_ip']['S']
        local_ip = task_item['local_ip']['SS']
        associated_portgroups = task_item['portgroups']['SS']
        associated_listeners = task_item['listeners']['SS']
        instruct_ids = task_item['instruct_ids']['SS']
        instruct_instances = task_item['instruct_instances']['SS']
        last_instruct_user_id = task_item['last_instruct_user_id']['S']
        last_instruct_id = task_item['last_instruct_id']['S']
        last_instruct_instance = task_item['last_instruct_instance']['S']
        last_instruct_command = task_item['last_instruct_command']['S']
        last_instruct_args = task_item['last_instruct_args']['M']
        last_instruct_args_fixup = {}
        for key, value in last_instruct_args.items():
            if 'S' in value:
                last_instruct_args_fixup[key] = value['S']
            if 'N' in value:
                last_instruct_args_fixup[key] = value['N']
            if 'BOOL' in value:
                last_instruct_args_fixup[key] = value['BOOL']
            if 'B' in value:
                last_instruct_args_fixup[key] = value['B']
        last_instruct_time = task_item['last_instruct_time']['S']
        task_creator_user_id = task_item['user_id']['S']
        create_time = task_item['create_time']['S']
        scheduled_end_time = task_item['scheduled_end_time']['S']
        ecs_task_id = task_item['ecs_task_id']['S']
        task_host_name = task_item['task_host_name']['S']
        task_domain_name = task_item['task_domain_name']['S']
        return format_response(
            200, 'success', 'get task succeeded', None, task_name=task_name, task_type=task_type, task_version=task_version,
            task_context=task_context, task_status=task_status, public_ip=public_ip, local_ip=local_ip,
            associated_portgroups=associated_portgroups, associated_listeners=associated_listeners, instruct_ids=instruct_ids,
            instruct_instances=instruct_instances, last_instruct_user_id=last_instruct_user_id, last_instruct_id=last_instruct_id,
            last_instruct_instance=last_instruct_instance, last_instruct_command=last_instruct_command,
            last_instruct_args=last_instruct_args_fixup, last_instruct_time=last_instruct_time,
            task_creator_user_id=task_creator_user_id, create_time=create_time, scheduled_end_time=scheduled_end_time, 
            ecs_task_id=ecs_task_id, task_host_name=task_host_name, task_domain_name=task_domain_name
        )

    def kill(self):
        if 'task_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.task_name = self.detail['task_name']

        terminate_task_response = self.terminate_task()
        if terminate_task_response == 'task_not_found':
            return format_response(404, 'failed', f'task {self.task_name} does not exist', self.log)
        elif terminate_task_response == 'task_associated_with_listener':
            return format_response(409, 'failed', 'cannot kill a task that is associated with an active listener', self.log)
        elif terminate_task_response == 'task_terminated':
            return format_response(200, 'success', 'kill task succeeded', None)
        else:
            return format_response(500, 'failed', f'kill task failed with error {terminate_task_response}', self.log)

    def list(self):
        if 'task_name_contains' in self.detail:
            tnf = self.detail['task_name_contains']
            if tnf is None:
                tnf = ''
        else:
            tnf = ''
        if 'task_type' in self.detail:
            ttf = self.detail['task_type']
            if ttf is None:
                ttf = ''
        else:
            ttf = ''
        if 'task_status' in self.detail:
            tsf = self.detail['task_status'].lower()
            if tsf is None:
                tsf = 'running'
        else:
            tsf = 'running'
        tasks_list = []
        tasks_list_final = []
        tasks = self.query_tasks()
        if 'Items' in tasks:
            for item in tasks['Items']:
                task_name = item['task_name']['S']
                task_type = item['task_type']['S']
                task_status = item['task_status']['S']
                task_dict = {'task_name': task_name, 'task_type': task_type, 'task_status': task_status}
                tasks_list.append(task_dict)
            tn_filtered = [x for x in tasks_list if tnf in x['task_name']]
            tt_filtered = [x for x in tn_filtered if ttf in x['task_type']]
            tasks_list_final = [x for x in tt_filtered if tsf == x['task_status'] or tsf == 'all' or (tsf == 'running' and (x['task_status'] == 'starting' or x['task_status'] == 'idle' or x['task_status'] == 'busy'))]
        return format_response(200, 'success', 'list tasks succeeded', None, tasks=tasks_list_final)

    def create(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def delete(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
