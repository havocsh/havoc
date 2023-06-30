import re
import json
import dpath
import signal
import havoc
import botocore
import boto3
from datetime import datetime
from datetime import timedelta


def timeout_handler(signum, frame):
    raise Exception('timeout exceeded')


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

    def __init__(self, deployment_name, results_queue_expiration, scheduled_trigger, trigger_name, region, detail, user_id, log):
        """
        Instantiate a trigger executor instance
        """
        self.deployment_name = deployment_name
        self.results_queue_expiration = results_queue_expiration
        self.scheduled_trigger = scheduled_trigger
        self.trigger_name = trigger_name
        self.region = region
        self.detail = detail
        self.user_id = user_id
        self.log = log
        self.api_key = None
        self.secret = None
        self.api_region = None
        self.api_domain_name = None
        self.__aws_dynamodb_client = None
        self.__havoc_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    @property
    def havoc_client(self):
        if self.__havoc_client is None:
            self.__havoc_client = havoc.Connect(self.api_region, self.api_domain_name, self.api_key, self.secret, api_version=1)
        return self.__havoc_client
    
    def get_deployment_details(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )
    
    def get_credentials(self, created_by):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-authorizer',
            Key={
                'user_id': {'S': created_by}
            }
        )
    
    def add_queue_attribute(self, stime, expire_time, filter_command, filter_command_args, filter_command_timeout, filter_command_json,
                            execute_command, execute_command_args, execute_command_timeout, execute_command_json):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-trigger-queue',
                Key={
                    'trigger_name': {'S': self.trigger_name},
                    'run_time': {'N': stime}
                },
                UpdateExpression='set '
                                'expire_time=:expire_time, '
                                'user_id=:user_id, '
                                'filter_command=:filter_command, '
                                'filter_command_args=:filter_command_args, '
                                'filter_command_timeout=:filter_command_timeout, '
                                'filter_command_response=:filter_command_response, '
                                'execute_command=:execute_command, '
                                'execute_command_args=:execute_command_args, '
                                'execute_command_timeout=:execute_command_timeout, '
                                'execute_command_response=:execute_command_response',
                ExpressionAttributeValues={
                    ':expire_time': {'N': expire_time},
                    ':user_id': {'S': self.user_id},
                    ':filter_command': {'S': filter_command},
                    ':filter_command_args': {'S': filter_command_args},
                    ':filter_command_timeout': {'N': filter_command_timeout},
                    ':filter_command_response': {'S': filter_command_json},
                    ':execute_command': {'S': execute_command},
                    ':execute_command_args': {'S': execute_command_args},
                    ':execute_command_timeout': {'N': execute_command_timeout},
                    ':execute_command_response': {'S': execute_command_json}
                }
            )
        except botocore.exceptions.ClientError as error:
            return f'ClientError: {error}'
        except botocore.exceptions.ParamValidationError as error:
            return f'ParamValidationError: {error}'
        except Exception as error:
            return error
        return 'queue_attribute_added'

    def execute(self):
        stime = datetime.utcnow().strftime('%s')
        from_timestamp = datetime.utcfromtimestamp(int(stime))
        expiration_time = from_timestamp + timedelta(days=self.results_queue_expiration)
        expiration_stime = expiration_time.strftime('%s')
        filter_command = None
        filter_command_args = None
        filter_command_response = None
        if 'filter_command' in self.detail:
            filter_command = self.detail['filter_command']
            filter_commands = ['get_agent_results', 'get_filtered_task_results', 'get_playbook_results', 'get_task_results', 'wait_for_c2', 'wait_for_idle_task']
            if filter_command not in filter_commands:
                response = format_response(
                        400, 
                        'failed', 
                        'invalid detail: unsupported filter_command', 
                        self.log, 
                        trigger_name=self.trigger_name,
                        scheduled_trigger=self.scheduled_trigger
                    )
                return response
            
            if 'filter_command_args' in self.detail:
                filter_command_args = self.detail['filter_command_args']
                if filter_command_args is not None and not isinstance(filter_command_args, dict):
                    response = format_response(
                        400, 
                        'failed', 
                        'invalid detail: filter_command_args must be type dict', 
                        self.log, 
                        trigger_name=self.trigger_name,
                        scheduled_trigger=self.scheduled_trigger
                    )

                    return response
            
            if 'filter_command_timeout' in self.detail:
                try:
                    filter_command_timeout = int(self.detail['filter_command_timeout'])
                except Exception as e:
                    response = format_response(
                        400, 
                        'failed', 
                        f'invalid detail: assigning filter_command_timeout failed with error: {e}', 
                        self.log, 
                        trigger_name=self.trigger_name,
                        scheduled_trigger=self.scheduled_trigger
                    )
                    return response
            else:
                filter_command_timeout = 300

        if 'execute_command' not in self.detail:
            response = format_response(
                400, 
                'failed', 
                'invalid detail: missing execute_command', 
                self.log, 
                trigger_name=self.trigger_name,
                scheduled_trigger=self.scheduled_trigger
            )
            return response
        execute_command = self.detail['execute_command']

        execute_command_args = None
        if 'execute_command_args' in self.detail:
            execute_command_args = self.detail['execute_command_args']
            if execute_command_args and not isinstance(execute_command_args, dict):
                response = format_response(
                    400, 
                    'failed', 
                    'invalid detail: execute_command_args must be type dict', 
                    self.log, 
                    trigger_name=self.trigger_name,
                    scheduled_trigger=self.scheduled_trigger
                )
                return response
        
        if 'execute_command_timeout' in self.detail:
            try:
                execute_command_timeout = int(self.detail['execute_command_timeout'])
            except Exception as e:
                response = format_response(
                    400, 
                    'failed', 
                    f'invalid detail: assigning execute_command_timeout failed with error: {e}', 
                    self.log, 
                    trigger_name=self.trigger_name,
                    scheduled_trigger=self.scheduled_trigger
                )
                return response
        else:
            execute_command_timeout = 300

        deployment_details = self.get_deployment_details()
        self.api_region = deployment_details['Item']['api_region']['S']
        self.api_domain_name = deployment_details['Item']['api_domain_name']['S']

        credentials = self.get_credentials(self.user_id)
        self.api_key = credentials['Item']['api_key']['S']
        self.secret_key = credentials['Item']['secret_key']['S']

        if filter_command:
            signal.alarm(filter_command_timeout)
            try:
                filter_command_method = getattr(self.havoc_client, filter_command)
                if filter_command_args:
                    filter_command_response = filter_command_method(**filter_command_args)
                else:
                    filter_command_response = filter_command_method()
            except Exception as e:
                if e == 'timeout exceeded':
                    status_code = 200
                    outcome = 'success'
                    message = f'filter_command {filter_command} with args {filter_command_args} executed but did not return results ' \
                    f'before the {filter_command_timeout} second timeout expired'
                else:
                    status_code = 400
                    outcome = 'failed'
                    message = f'filter_command {filter_command} with args {filter_command_args} failed with error: {e}'
                response = format_response(
                        status_code, 
                        outcome, 
                        message,
                        self.log,
                        trigger_name=self.trigger_name,
                        scheduled_trigger=self.scheduled_trigger
                    )
                filter_command_json = json.dumps(message)
                execute_command_json = json.dumps(None)
                if not filter_command_args:
                    filter_command_args = 'None'
                if not execute_command_args:
                    execute_command_args = 'None'
                add_queue_attr_resp = self.add_queue_attribute(stime, expiration_stime, filter_command, filter_command_args, str(filter_command_timeout),
                                                               filter_command_json, execute_command, execute_command_args, str(execute_command_timeout),
                                                               execute_command_json)
                if add_queue_attr_resp != 'queue_attribute_added':
                    if 'ClientError:' in add_queue_attr_resp or 'ParamValidationError:' in add_queue_attr_resp or 'invalid_format' in add_queue_attr_resp:
                        return format_response(400, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                    else:
                        return format_response(500, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                return response
            empty_result_set = None
            if filter_command == 'get_task_results' or filter_command == 'get_filtered_task_results' or filter_command == 'get_playbook_results':
                if not filter_command_response['queue']:
                    empty_result_set = True
            if filter_command == 'get_agent_results':
                    if not filter_command_response:
                        empty_result_set = True
            if empty_result_set:
                add_queue_attr_resp = self.add_queue_attribute(stime, expiration_stime, filter_command, filter_command_args, str(filter_command_timeout),
                                                            filter_command_json, execute_command, execute_command_args, str(execute_command_timeout),
                                                            execute_command_json)
                if add_queue_attr_resp != 'queue_attribute_added':
                    if 'ClientError:' in add_queue_attr_resp or 'ParamValidationError:' in add_queue_attr_resp or 'invalid_format' in add_queue_attr_resp:
                        return format_response(400, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                    else:
                        return format_response(500, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                response = format_response(
                    200, 
                    'success', 
                    f'filter_command {filter_command} with args {filter_command_args} executed but did not return results',
                    self.log,
                    trigger_name=self.trigger_name,
                    scheduled_trigger=self.scheduled_trigger
                )
                return response

        if execute_command_args:
            json_args = json.dumps(execute_command_args)
            matches = re.findall('\${[^}]+}', json_args)
            if matches and not filter_command_response:
                message = f'no filter_command results available to populate variable references in execute_command_args'
                filter_command_json = json.dumps(filter_command_response)
                execute_command_json = json.dumps(message)
                if not filter_command_args:
                    filter_command_args = 'None'
                if not execute_command_args:
                    execute_command_args = 'None'
                add_queue_attr_resp = self.add_queue_attribute(stime, expiration_stime, filter_command, filter_command_args, str(filter_command_timeout),
                                                               filter_command_json, execute_command, execute_command_args, str(execute_command_timeout),
                                                               execute_command_json)
                if add_queue_attr_resp != 'queue_attribute_added':
                    if 'ClientError:' in add_queue_attr_resp or 'ParamValidationError:' in add_queue_attr_resp or 'invalid_format' in add_queue_attr_resp:
                        return format_response(400, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                    else:
                        return format_response(500, 'failed', f'filter_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                response = format_response(
                    400, 
                    'failed', 
                    message, 
                    self.log,
                    trigger_name=self.trigger_name,
                    scheduled_trigger=self.scheduled_trigger
                )
                return response
            for match in matches:
                search_path = re.search('\${([^}]+)}', match)
                if search_path:
                    orig_path = search_path.group(1)
                    dep_path = re.sub('\.', '/', orig_path)
                    dep_value = dpath.get(filter_command_response, dep_path)
                    re_sub = re.compile('\${' + re.escape(orig_path) + '}')
                    json_args = re.sub(re_sub, str(dep_value), json_args)
            execute_command_args = json.loads(json_args, strict=False)

        signal.alarm(execute_command_timeout)
        try:
            execute_command_method = getattr(self.havoc_client, execute_command)
            if execute_command_args:
                execute_command_response = execute_command_method(**execute_command_args)
            else:
                execute_command_response = execute_command_method()
        except Exception as e:
            if e == 'timeout exceeded':
                status_code = 200
                outcome = 'success'
                message = f'execute_command {execute_command} with args {execute_command_args} executed but did not return results ' \
                f'before the {execute_command_timeout} second timeout expired'
            else:
                status_code = 400
                outcome = 'failed'
                message = f'execute_command {execute_command} with args {execute_command_args} failed with error: {e}'
            filter_command_json = json.dumps(filter_command_response)
            execute_command_json = json.dumps(message)
            if not filter_command_args:
                filter_command_args = 'None'
            if not execute_command_args:
                execute_command_args = 'None'
            add_queue_attr_resp = self.add_queue_attribute(stime, expiration_stime, filter_command, filter_command_args, str(filter_command_timeout),
                                                           filter_command_json, execute_command, execute_command_args, str(execute_command_timeout), 
                                                           execute_command_json)
            if add_queue_attr_resp != 'queue_attribute_added':
                if 'ClientError:' in add_queue_attr_resp or 'ParamValidationError:' in add_queue_attr_resp or 'invalid_format' in add_queue_attr_resp:
                    return format_response(400, 'failed', f'execute_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
                else:
                    return format_response(500, 'failed', f'execute_command succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
            response = format_response(
                    status_code,
                    outcome,
                    message,
                    self.log,
                    trigger_name=self.trigger_name,
                    scheduled_trigger=self.scheduled_trigger
                )
            return response

        # Add entry to trigger_queue
        add_queue_attr_resp = self.add_queue_attribute(stime, expiration_stime, filter_command, filter_command_args, str(filter_command_timeout), 
                                                       filter_command_json, execute_command, execute_command_args, str(execute_command_timeout), 
                                                       execute_command_json)
        if add_queue_attr_resp != 'queue_attribute_added':
            if 'ClientError:' in add_queue_attr_resp or 'ParamValidationError:' in add_queue_attr_resp or 'invalid_format' in add_queue_attr_resp:
                return format_response(400, 'failed', f'execute trigger succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
            else:
                return format_response(500, 'failed', f'execute trigger succeeded but writing results to queue failed with error {add_queue_attr_resp}', self.log)
        # Send response
        response_args = {}
        if filter_command_response:
            response_args['filter_command'] = filter_command_response
        if execute_command_response:
            response_args['execute_command'] = execute_command_response
        response = format_response(200, 'success', 'execute_trigger succeeded', None, **response_args)
        return response