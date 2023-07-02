import json
import boto3
from dateutil import parser
from datetime import datetime
from datetime import timedelta


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


class Queue:

    def __init__(self, deployment_name, trigger_name, region, detail: dict, user_id, log):
        self.deployment_name = deployment_name
        self.trigger_name = trigger_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.__aws_client = None

    @property
    def aws_client(self):
        """Returns the boto3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_client is None:
            self.__aws_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_client

    def query_queue(self, start_timestamp, end_timestamp):
        queue_results = {'Items': []}
        scan_kwargs = {
            'TableName': f'{self.deployment_name}-trigger-queue',
            'KeyConditionExpression': 'trigger_name = :trigger_name AND run_time BETWEEN :start_time AND :end_time',
            'ExpressionAttributeValues': {
                ':trigger_name': {'S': self.trigger_name},
                ':start_time': {'N': start_timestamp},
                ':end_time': {'N': end_timestamp}
            }
        }

        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_client.query(**scan_kwargs)
            for item in response['Items']:
                queue_results['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return queue_results

    def get_results(self):

        queue_list = []

        # Build query time range
        start_time = None
        if 'start_time' in self.detail:
            start_time = self.detail['start_time']
        end_time = None
        if 'end_time' in self.detail:
            end_time = self.detail['end_time']
        if start_time != '' and start_time is not None:
            start = parser.parse(start_time)
        else:
            start = datetime.now() - timedelta(minutes=1440)

        if end_time != '' and end_time is not None:
            end = parser.parse(end_time)
        else:
            end = datetime.now()

        # Assign query parameters
        start_timestamp = str(int(datetime.timestamp(start)))
        end_timestamp = str(int(datetime.timestamp(end)))
            
        # Run query
        queue_data = self.query_queue(start_timestamp, end_timestamp)
        if queue_data:
            for item in queue_data['Items']:
                run_time = item['run_time']['N']
                trigger_name = item['trigger_name']['S']
                scheduled_trigger = item['scheduled_trigger']['S']
                filter_command = item['filter_command']['S']
                filter_command_args = item['filter_command_args']['S']
                filter_command_timeout = item['filter_command_timeout']['S']
                filter_command_response = item['filter_command_response']['S']
                execute_command = item['execute_command']['S']
                execute_command_args = item['execute_command_args']['S']
                execute_command_timeout = item['execute_command_timeout']['S']
                execute_command_response = item['execute_command_response']['S']
                user_id = item['user_id']['S']

                # Add queue entry to results
                queue_list.append({
                    'trigger_name': trigger_name,
                    'scheduled_triger': scheduled_trigger,
                    'filter_command': filter_command,
                    'filter_command_args': filter_command_args,
                    'filter_command_timeout': filter_command_timeout,
                    'filter_command_response': filter_command_response,
                    'execute_command': execute_command,
                    'execute_command_args': execute_command_args,
                    'execute_command_timeout': execute_command_timeout,
                    'execute_command_response': execute_command_response,
                    'user_id': user_id,
                    'run_time': run_time
                    })

        return format_response(200, 'success', 'get_results succeeded', None, queue=queue_list)
