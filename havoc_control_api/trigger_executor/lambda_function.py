import re
import os
import json
import executor
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
    results_queue_expiration = int(os.environ['RESULTS_QUEUE_EXPIRATION'])
    log = {'event': event}

    if 'requestContext' in event:
        user_id = event['requestContext']['authorizer']['user_id']
        data = json.loads(event['body'])
    else:
        data = event
        user_id = event['user_id']

    scheduled_trigger = False
    if 'scheduled_trigger' in data:
        scheduled_trigger = True

    if 'action' not in data:
        return format_response(400, 'failed', 'request must contain valid action', log)
    action = data['action']

    if 'detail' not in data:
        return format_response(400, 'failed', 'request must contain valid detail', log)
    detail = data['detail']

    if 'trigger_name' not in detail:
        return format_response(400, 'failed', 'request detail must contain trigger_name', log)
    trigger_name = detail['trigger_name']

    if action == 'execute_trigger':
        # Execute trigger
        execute_trigger = executor.Trigger(deployment_name, results_queue_expiration, scheduled_trigger, trigger_name, region, detail, user_id, log)
        response = execute_trigger.execute()
        return response

    if action == 'get_results':
        # Get results from trigger execution
        trigger_results = results_queue.Queue(deployment_name, trigger_name, region, detail, user_id, log)
        response = trigger_results.get_results()
        return response
