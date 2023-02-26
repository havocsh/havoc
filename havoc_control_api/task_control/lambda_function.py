import re
import os
import json
import execute
import interact
import results_queue


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
    subnet = os.environ['SUBNET']
    default_security_group = os.environ['SECURITY_GROUP']
    log = {'event': event}

    user_id = event['requestContext']['authorizer']['user_id']
    data = json.loads(event['body'])

    if 'action' not in data:
        return format_response(400, 'failed', 'request must contain valid action', log)
    action = data['action']

    if 'detail' not in data:
        return format_response(400, 'failed', 'request must contain valid detail', log)
    detail = data['detail']

    if 'task_name' not in detail:
        return format_response(400, 'failed', 'request detail must contain task_name', log)
    task_name = detail['task_name']

    if action == 'execute':
        # Execute container task
        new_task = execute.Task(deployment_name, task_name, subnet, default_security_group, region, detail, user_id, log)
        response = new_task.run_task()
        return response

    if action == 'interact':
        # Send instructions to existing container task
        interact_task = interact.Task(deployment_name, task_name, region, detail, user_id, log)
        response = interact_task.instruct()
        return response

    if action == 'get_results':
        # Get results from task instructions
        task_results = results_queue.Queue(deployment_name, task_name, region, detail, user_id, log)
        response = task_results.get_results()
        return response
