import re
import os
import json
import launcher
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
    log = {'event': event}

    user_id = event['requestContext']['authorizer']['user_id']
    data = json.loads(event['body'])

    if 'action' not in data:
        return format_response(400, 'failed', 'request must contain valid action', log)
    action = data['action']

    if 'detail' not in data:
        return format_response(400, 'failed', 'request must contain valid detail', log)
    detail = data['detail']

    if 'playbook_name' not in detail:
        return format_response(400, 'failed', 'request detail must contain playbook_name', log)
    playbook_name = detail['playbook_name']

    if action == 'launch':
        # Execute container task
        playbook_run = launcher.Playbook(deployment_name, playbook_name, subnet, region, detail, user_id, log)
        response = playbook_run.launch()
        return response

    if action == 'get_results':
        # Get results from task instructions
        playbook_results = results_queue.Queue(deployment_name, playbook_name, region, detail, user_id, log)
        response = playbook_results.get_results()
        return response
