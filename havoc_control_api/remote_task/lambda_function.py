import os
import re
import json
from get_commands import Retrieve
from post_results import Deliver
from register_task import Task


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


def lambda_handler(event, context):
    region = re.search('arn:aws:lambda:([^:]+):.*', context.invoked_function_arn).group(1)
    deployment_name = os.environ['DEPLOYMENT_NAME']
    results_queue_expiration = int(os.environ['RESULTS_QUEUE_EXPIRATION'])
    log = {'event': event}
    results = None
    detail = None

    user_id = event['requestContext']['authorizer']['user_id']
    data = json.loads(event['body'])
    try:
        command = data['command']
    except:
        return format_response(400, 'failed', 'invalid request', log)

    if command not in ['register_task', 'get_commands', 'post_results']:
        return format_response(400, 'failed', f'{command} is not a valid command', log)

    if 'detail' in data:
        detail = data['detail']

    if 'results' in data:
        results = data['results']

    if command == 'register_task':
        if not detail:
            return format_response(400, 'failed', 'missing detail', log)
        else:
            t = Task(region, deployment_name, user_id, detail, log)
            response = t.registration()
            return response

    if command == 'get_commands':
        if not detail:
            return format_response(400, 'failed', 'missing detail', log)
        else:
            r = Retrieve(region, deployment_name, detail, log)
            response = r.retrieve_commands()
            return response

    if command == 'post_results':
        if not results:
            return format_response(400, 'failed', 'missing results', log)
        else:
            d = Deliver(region, deployment_name, results_queue_expiration, user_id, results, log)
            response = d.deliver_result()
            return response
