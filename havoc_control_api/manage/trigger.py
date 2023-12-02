import os
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


class Trigger:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Instantiate a Trigger instance
        """
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.trigger_name = None
        self.trigger_args = None
        self.rule_arn = None
        self.__aws_dynamodb_client = None
        self.__aws_cloudwatch_events_client = None
        self.role_arn = os.environ['ROLE_ARN']
        self.trigger_executor_arn = os.environ['TRIGGER_EXECUTOR_ARN']

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    @property
    def aws_cloudwatch_events_client(self):
        """Returns the boto3 CloudWatch Events session (establishes one automatically if one does not already exist)"""
        if self.__aws_cloudwatch_events_client is None:
            self.__aws_cloudwatch_events_client = boto3.client('events', region_name=self.region)
        return self.__aws_cloudwatch_events_client

    def query_triggers(self):
        triggers = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-triggers'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                triggers['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return triggers
    
    def get_trigger_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-triggers',
            Key={
                'trigger_name': {'S': self.trigger_name}
            }
        )
    
    def put_rule(self):
        schedule_expression = self.trigger_args['schedule_expression']
        try:
            response = self.aws_cloudwatch_events_client.put_rule(
                Name=self.trigger_name,
                RoleArn=self.role_arn,
                ScheduleExpression=schedule_expression,
                State='ENABLED'
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        self.rule_arn = response['RuleArn']
        return 'rule_created'
    
    def put_target(self):
        event_input = {'user_id': self.user_id, 'action': 'execute_trigger', 'scheduled_trigger': True, 'detail': {}}
        event_input['detail']['trigger_name'] = self.trigger_name
        event_input['detail']['execute_command'] = self.trigger_args['execute_command']
        if self.trigger_args['execute_command_args']:
            execute_command_args = ast.literal_eval(self.trigger_args['execute_command_args'])
            if not isinstance(execute_command_args, dict):
                return 'execute_command_args_invalid_format'
            event_input['detail']['execute_command_args'] = execute_command_args
        if self.trigger_args['execute_command_timeout']:
            try:
                int(self.trigger_args['execute_command_timeout'])
            except:
                return 'execute_command_timeout_invalid_format'
            event_input['detail']['execute_command_timeout'] = self.trigger_args['execute_command_timeout']
        if self.trigger_args['filter_command']:
            event_input['detail']['filter_command'] = self.trigger_args['filter_command']
        if self.trigger_args['filter_command_args']:
            filter_command_args = ast.literal_eval(self.trigger_args['filter_command_args'])
            if not isinstance(filter_command_args, dict):
                return 'filter_command_args_invalid_format'
            event_input['detail']['filter_command_args'] = filter_command_args
        if self.trigger_args['filter_command_timeout']:
            try:
                int(self.trigger_args['filter_command_timeout'])
            except:
                return 'filter_command_timeout_invalid_format'
            event_input['detail']['filter_command_timeout'] = self.trigger_args['filter_command_timeout']
        try:
            self.aws_cloudwatch_events_client.put_targets(
                Rule=self.trigger_name,
                Targets=[
                    {
                        'Arn': self.trigger_executor_arn,
                        'Id': self.trigger_name,
                        'Input': json.dumps(event_input)
                    }
                ]
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        return 'target_created'
    
    def delete_rule(self):
        try:
            self.aws_cloudwatch_events_client.delete_rule(
                Name=self.trigger_name,
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        return 'rule_deleted'
    
    def remove_targets(self):
        try:
            self.aws_cloudwatch_events_client.remove_targets(
                Rule=self.trigger_name,
                Ids=[self.trigger_name]
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        return 'targets_removed'
    
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

    def create_trigger_entry(self):

        # Check for trigger conflict
        existing_trigger = self.get_trigger_entry()
        if 'Item' in existing_trigger:
            return 'trigger_exists'
        
        # Create trigger rule
        trigger_rule = self.put_rule()
        if trigger_rule != 'rule_created':
            return trigger_rule
        
        # Create trigger target
        trigger_target = self.put_target()
        if trigger_target != 'target_created':
            self.delete_rule()
            return trigger_target
        
        # Add the trigger details to the DynamoDB triggers table
        schedule_expression = self.trigger_args['schedule_expression']
        execute_command = self.trigger_args['execute_command']
        execute_command_args = self.trigger_args['execute_command_args']
        if not execute_command_args:
            execute_command_args = {'no_args': 'true'}
        execute_command_timeout = self.trigger_args['execute_command_timeout']
        if execute_command_timeout is not None:
            try:
                int(execute_command_timeout)
            except:
                return 'execute_command_timeout_invalid_format'
        if not execute_command_timeout:
            execute_command_timeout = 'None'
        filter_command = self.trigger_args['filter_command']
        if not filter_command:
            filter_command = 'None'
        filter_command_args = self.trigger_args['filter_command_args']
        if not filter_command_args:
            filter_command_args = {'no_args': 'true'}
        filter_command_timeout = self.trigger_args['filter_command_timeout']
        if filter_command_timeout is not None:
            try:
                int(filter_command_timeout)
            except:
                return 'filter_command_timeout_invalid_format'
        if not filter_command_timeout:
            filter_command_timeout = 'None'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-triggers',
                Key={
                    'trigger_name': {'S': self.trigger_name}
                },
                UpdateExpression='set schedule_expression=:schedule_expression, execute_command=:execute_command, '
                                 'execute_command_args=:execute_command_args, execute_command_timeout=:execute_command_timeout, '
                                 'filter_command=:filter_command, filter_command_args=:filter_command_args, '
                                 'filter_command_timeout=:filter_command_timeout, rule_arn=:rule_arn, created_by=:created_by',
                ExpressionAttributeValues={
                    ':schedule_expression': {'S': schedule_expression},
                    ':execute_command': {'S': execute_command},
                    ':execute_command_args': {'S': execute_command_args},
                    ':execute_command_timeout': {'S': execute_command_timeout},
                    ':filter_command': {'S': filter_command},
                    ':filter_command_args': {'S': filter_command_args},
                    ':filter_command_timeout': {'S': filter_command_timeout},
                    ':rule_arn': {'S': self.rule_arn},
                    ':created_by': {'S': self.user_id}
                }
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        
        # Add trigger to active_resources in deployment table
        deployment_details = self.get_deployment_entry
        active_resources = deployment_details['active_resources']['M']
        active_triggers = active_resources['triggers']['L']
        if active_triggers == ['None']:
            active_triggers = [self.trigger_name]
        else:
            active_triggers.append(self.trigger_name)
        active_resources['triggers']['L'] = active_triggers
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response
        return 'trigger_created'

    def delete_trigger_entry(self):
        # Verify the trigger exists
        trigger_entry = self.get_trigger_entry()
        if 'Item' not in trigger_entry:
            return 'trigger_entry_not_found'

        # Remove the rule targets
        remove_targets_response = self.remove_targets()
        if remove_targets_response != 'targets_removed':
            return remove_targets_response

        # Delete the rule
        delete_rule_response = self.delete_rule()
        if delete_rule_response != 'rule_deleted':
            return delete_rule_response

        # Delete the trigger details from the DynamoDB triggers table
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-triggers',
                Key={
                    'trigger_name': {'S': self.trigger_name}
                }
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        
        # Remove trigger from active_resources in deployment table
        deployment_details = self.get_deployment_entry
        active_resources = deployment_details['active_resources']['M']
        active_triggers = active_resources['triggers']['L']
        active_triggers.remove(self.trigger_name)
        if len(active_triggers) == 0:
            active_triggers = ['None']
        active_resources['triggers']['L'] = active_triggers
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response
        return 'trigger_deleted'

    def create(self):
        trigger_details = ['trigger_name', 'execute_command', 'schedule_expression']
        for i in trigger_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing required parameter {i}', self.log)
            
        self.trigger_name = self.detail['trigger_name']
        self.trigger_args = {
            'schedule_expression': None,
            'execute_command': None,
            'execute_command_args': None,
            'execute_command_timeout': None,
            'filter_command': None,
            'filter_command_args': None,
            'filter_command_timeout': None
        }
        filter_commands = ['get_agent_results', 'get_filtered_task_results', 'get_playbook_results', 'get_task_results', 'wait_for_c2', 'wait_for_idle_task']
        for k, v in self.detail.items():
            if k != 'trigger_name':
                if k in self.trigger_args:
                    if k == 'filter_command' and v not in filter_commands:
                        return format_response(400, 'failed', f'invalid detail: {v} is not a supported filter_command', self.log)
                    self.trigger_args[k] = v
                else:
                    return format_response(400, 'failed', f'invalid detail: unknown parameter {k}', self.log)

        # Create trigger entry
        create_trigger_response = self.create_trigger_entry()
        if create_trigger_response == 'trigger_exists':
            return format_response(409, 'failed', f'{self.trigger_name} already exists', self.log)
        elif create_trigger_response == 'trigger_created':
            return format_response(200, 'success', 'create trigger succeeded', None)
        elif 'ClientError:' in create_trigger_response or 'ParamValidationError:' in create_trigger_response or 'invalid_format' in create_trigger_response:
            return format_response(400, 'failed', f'create trigger failed with error {create_trigger_response}', self.log)
        else:
            return format_response(500, 'failed', f'create trigger failed with error {create_trigger_response}', self.log)

    def delete(self):
        if 'trigger_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail: missing required parameter trigger_name', self.log)
        self.trigger_name = self.detail['trigger_name']

        # Delete trigger entry
        delete_trigger_entry_response = self.delete_trigger_entry()
        if delete_trigger_entry_response == 'trigger_entry_not_found':
            return format_response(404, 'failed', f'trigger {self.trigger_name} does not exist', self.log)
        elif delete_trigger_entry_response == 'trigger_deleted':
            return format_response(200, 'success', 'delete trigger succeeded', None)
        elif 'ClientError:' in delete_trigger_entry_response or 'ParamValidationError:' in delete_trigger_entry_response:
            return format_response(400, 'failed', f'delete trigger failed with error {delete_trigger_entry_response}', self.log)
        else:
            return format_response(500, 'failed', f'delete trigger failed with error {delete_trigger_entry_response}', self.log)

    def get(self):
        if 'trigger_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail: missing required parameter trigger_name', self.log)
        self.trigger_name = self.detail['trigger_name']

        trigger_entry = self.get_trigger_entry()
        if 'Item' not in trigger_entry:
            return format_response(404, 'failed', f'trigger {self.trigger_name} does not exist', self.log)

        schedule_expression = trigger_entry['Item']['schedule_expression']['S']
        execute_command = trigger_entry['Item']['execute_command']['S']
        execute_command_args = trigger_entry['Item']['execute_command_args']['S']
        filter_command = trigger_entry['Item']['filter_command']['S']
        filter_command_args = trigger_entry['Item']['filter_command_args']['S']
        filter_command_timeout = trigger_entry['Item']['filter_command_timeout']['S']
        created_by = trigger_entry['Item']['created_by']['S']
        return format_response(200, 'success', 'get trigger succeeded', None, trigger_name=self.trigger_name,
                               schedule_expression=schedule_expression, execute_command=execute_command,
                               execute_command_args=execute_command_args, filter_command=filter_command,
                               filter_command_args=filter_command_args, filter_command_timeout=filter_command_timeout,
                               created_by=created_by)

    def list(self):
        triggers_list = []
        triggers = self.query_triggers()
        for item in triggers['Items']:
            self.trigger_name = item['trigger_name']['S']
            triggers_list.append(self.trigger_name)
        return format_response(200, 'success', 'list triggers succeeded', None, triggers=triggers_list)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
