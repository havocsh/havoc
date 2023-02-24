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

    def __init__(self, deployment_name, playbook_name, region, detail: dict, user_id, log):
        self.deployment_name = deployment_name
        self.playbook_name = playbook_name
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
            'TableName': f'{self.deployment_name}-playbook-queue',
            'KeyConditionExpression': 'playbook_name = :playbook_name AND run_time BETWEEN :start_time AND :end_time',
            'ExpressionAttributeValues': {
                ':playbook_name': {'S': self.playbook_name},
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
            start_timestamp = None
            try:
                start_timestamp = str(int(start_time))
            except:
                pass
            if not start_timestamp:
                start = parser.parse(start_time)
                start_timestamp = str(int(datetime.timestamp(start)))
        else:
            start = datetime.now() - timedelta(minutes=1440)
            start_timestamp = str(int(datetime.timestamp(start)))

        if end_time != '' and end_time is not None:
            end_timestamp = None
            try:
                end_timestamp = str(int(end_time))
            except:
                pass
            if not end_timestamp:
                end = parser.parse(end_time)
                end_timestamp = str(int(datetime.timestamp(end)))
        else:
            end = datetime.now()
            end_timestamp = str(int(datetime.timestamp(end)))
            
        # Run query
        queue_data = self.query_queue(start_timestamp, end_timestamp)
        if queue_data:
            for item in queue_data['Items']:
                run_time = item['run_time']['N']
                playbook_name = item['playbook_name']['S']
                playbook_type = item['playbook_type']['S']
                playbook_operator_version = item['playbook_operator_version']['S']
                command_output = item['command_output']['S']
                user_id = item['user_id']['S']
                operator_command = item['operator_command']['S']
                command_args = item['command_args']['M']
                command_args_fixup = {}
                for key, value in command_args.items():
                    if 'S' in value:
                        command_args_fixup[key] = value['S']
                    if 'N' in value:
                        command_args_fixup[key] = value['N']
                    if 'BOOL' in value:
                        command_args_fixup[key] = value['BOOL']
                    if 'B' in value:
                        command_args_fixup[key] = value['B']

                # Add queue entry to results
                queue_list.append({
                    'playbook_name': playbook_name,
                    'playbook_type': playbook_type,
                    'playbook_operator_version': playbook_operator_version,
                    'user_id': user_id,
                    'operator_command': operator_command,
                    'command_args': command_args_fixup,
                    'command_output': command_output,
                    'run_time': run_time
                    })

        return format_response(200, 'success', 'get_results succeeded', None, queue=queue_list)
