import os
import re
from authorizer import Login


def lambda_handler(event, context):
    region = re.search('arn:aws:lambda:([^:]+):.*', context.invoked_function_arn).group(1)
    deployment_name = os.environ['DEPLOYMENT_NAME']
    account_id = event['requestContext']['accountId']
    api_id = event["requestContext"]["apiId"]
    if 'API_DOMAIN_NAME' not in os.environ:
        api_domain_name = f'{api_id}.execute-api.{region}.amazonaws.com'
    else:
        api_domain_name = os.environ['API_DOMAIN_NAME']

    auth = Login(region, deployment_name, api_domain_name, account_id, api_id, event)
    auth.authorize_keys()
    response = auth.gen_response()

    return response
