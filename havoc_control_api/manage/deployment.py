import json
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


class Deployment:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Instantiate a Deployment instance
        """
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.__aws_dynamodb_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    def get_deployment_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )

    def create_deployment_entry(self):
        existing_deployment = self.get_deployment_entry()
        if 'Item' in existing_deployment:
            return 'deployment_exists'
        else:
            deployment_version = self.detail['deployment_version']
            deployment_admin_email = self.detail['deployment_admin_email']
            results_queue_expiration = self.detail['results_queue_expiration']
            api_domain_name = self.detail['api_domain_name']
            api_region = self.detail['api_region']
            tfstate_s3_bucket = self.detail['tfstate_s3_bucket']
            tfstate_s3_key = self.detail['tfstate_s3_key']
            tfstate_s3_region = self.detail['tfstate_s3_region']
            tfstate_dynamodb_table = self.detail['tfstate_dynamodb_table']
            dynamodb_response = self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-deployment',
                Key={
                    'deployment_name': {'S': self.deployment_name}
                },
                UpdateExpression='set deployment_version=:deployment_version, deployment_admin_email=:deployment_admin_email, '
                                'results_queue_expiration=:results_queue_expiration, api_domain_name=:api_domain_name, api_region=:api_region, '
                                'tfstate_s3_bucket=:tfstate_s3_bucket, tfstate_s3_key=:tfstate_s3_key, tfstate_s3_region=:tfstate_s3_region, '
                                'tfstate_dynamodb_table=:tfstate_dynamodb_table',
                ExpressionAttributeValues={
                    ':deployment_version': {'S': deployment_version},
                    ':deployment_admin_email': {'S': deployment_admin_email},
                    ':results_queue_expiration': {'S': results_queue_expiration},
                    ':api_domain_name': {'S': api_domain_name},
                    ':api_region': {'S': api_region},
                    ':tfstate_s3_bucket': {'S': tfstate_s3_bucket},
                    ':tfstate_s3_key': {'S': tfstate_s3_key},
                    ':tfstate_s3_region': {'S': tfstate_s3_region},
                    ':tfstate_dynamodb_table': {'S': tfstate_dynamodb_table}
                }
            )
            return dynamodb_response

    def create(self):
        if self.detail:
            deployment = self.create_deployment_entry()
        else:
            return format_response(400, 'failed', 'invalid detail', self.log)
        if deployment == 'deployment_exists':
            return format_response(400, 'failed', 'deployment already exists', self.log)
        else:
            return format_response(200, 'success', 'create deployment succeeded', None)

    def delete(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def get(self):
        deployment_entry = self.get_deployment_entry()
        deployment_version = deployment_entry['Item']['deployment_version']['S']
        deployment_admin_email = deployment_entry['Item']['deployment_admin_email']['S']
        results_queue_expiration = deployment_entry['Item']['results_queue_expiration']['S']
        api_domain_name = deployment_entry['Item']['api_domain_name']['S']
        api_region = deployment_entry['Item']['api_region']['S']
        tfstate_s3_bucket = deployment_entry['Item']['tfstate_s3_bucket']['S']
        tfstate_s3_key = deployment_entry['Item']['tfstate_s3_key']['S']
        tfstate_s3_region = deployment_entry['Item']['tfstate_s3_region']['S']
        tfstate_dynamodb_table = deployment_entry['Item']['tfstate_dynamodb_table']['S']
        return format_response(
            200,
            'success',
            'get deployment succeeded',
            None,
            deployment_name=self.deployment_name,
            deployment_version=deployment_version,
            deployment_admin_email=deployment_admin_email,
            results_queue_expiration=results_queue_expiration,
            api_domain_name=api_domain_name,
            api_region=api_region,
            tfstate_s3_bucket=tfstate_s3_bucket,
            tfstate_s3_key=tfstate_s3_key,
            tfstate_s3_region=tfstate_s3_region,
            tfstate_dynamodb_table=tfstate_dynamodb_table
            )

    def list(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
