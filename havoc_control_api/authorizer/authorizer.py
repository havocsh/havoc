import boto3
import datetime
import hashlib
import hmac


class Login:

    def __init__(self, region, deployment_name, api_domain_name, account_id, api_id, event):
        self.region = region
        self.deployment_name = deployment_name
        self.api_domain_name = api_domain_name
        self.api_arn = f'arn:aws:execute-api:{region}:{account_id}:{api_id}/havoc/*/*'
        self.remote_task_api_arn = f'arn:aws:execute-api:{region}:{account_id}:{api_id}/havoc/POST/remote-task'
        self.api_key = event['headers']['x-api-key']
        self.sig_date = event['headers']['x-sig-date']
        self.signature = event['headers']['x-signature']
        self.authorized = None
        self.user_id = None
        self.remote_task = None

    def sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def getSignatureKey(self, key, date_stamp):
        k_date = self.sign(('havoc' + key).encode('utf-8'), date_stamp)
        k_region = self.sign(k_date, self.region)
        kSigning = self.sign(k_region, self.api_domain_name)
        return kSigning

    def authorize_keys(self):
        client = boto3.client('dynamodb', region_name=self.region)
        response = client.query(
            TableName=f'{self.deployment_name}-authorizer',
            IndexName=f'{self.deployment_name}-ApiKeyIndex',
            KeyConditionExpression='api_key = :key',
            ExpressionAttributeValues={
                ':key': {
                    'S': self.api_key
                }
            }
        )
        resp_api_key = None
        resp_secret_key = None
        resp_user_id = None
        if response['Items']:
            resp_api_key = response['Items'][0]['api_key']['S']
            resp_secret_key = response['Items'][0]['secret_key']['S']
            resp_user_id = response['Items'][0]['user_id']['S']
            resp_remote_task = response['Items'][0]['remote_task']['S']

        if not self.api_key:
            self.authorized = False
            print('Authorization failed due to missing api_key')
            return self.authorized
        if not resp_user_id:
            self.authorized = False
            print('Authorization failed due to invalid api_key')
            return self.authorized

        # Create signing key elements
        sig_date = datetime.datetime.strptime(self.sig_date, '%Y%m%dT%H%M%SZ')
        t = datetime.datetime.utcnow()
        local_date_stamp = t.strftime('%Y%m%d')

        # Ensure sig_date is within the last 5 seconds
        duration = t - sig_date
        duration_in_s = duration.total_seconds()
        if duration_in_s > 600 or duration_in_s < 0:
            self.authorized = False
            print(f'Authorization failed for {self.api_key} due to time delay in signature date.')
            print(f'Current date/time: {t}, Signature date/time: {sig_date}')
            return self.authorized

        # Get signing_key
        signing_key = self.getSignatureKey(resp_secret_key, local_date_stamp)

        # Setup string to sign
        algorithm = 'HMAC-SHA256'
        credential_scope = local_date_stamp + '/' + self.region + '/' + self.api_domain_name
        string_to_sign = algorithm + '\n' + self.sig_date + '\n' + credential_scope + hashlib.sha256(
            resp_api_key.encode('utf-8')).hexdigest()

        # Generate signature
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        if self.api_key == resp_api_key and self.signature == signature:
            self.authorized = True
            self.user_id = resp_user_id
            self.remote_task = resp_remote_task
        else:
            self.authorized = False
            print('Authorization failed due to api_key, signature match failure')
        return self.authorized

    def gen_response(self):

        def gen_policy(authorized, remote_task):
            effect = "Allow" if authorized else "Deny"
            if remote_task == 'yes':
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Action": "execute-api:Invoke",
                        "Effect": effect,
                        "Resource": self.remote_task_api_arn
                    }],
                }
            else:
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Action": "execute-api:Invoke",
                        "Effect": effect,
                        "Resource": self.api_arn
                    }],
                }
            return policy

        if self.authorized:
            policy = gen_policy(self.authorized, self.remote_task)
            context = {'user_id': self.user_id, 'api_key': self.api_key}
            response = {
                'principalId': self.api_key,
                'policyDocument': policy,
                'context': context,
                'usageIdentifierKey': self.api_key
            }
            return response

        if not self.authorized:
            policy = gen_policy(self.authorized, self.remote_task)
            context = {}
            response = {
                'context': context,
                'policyDocument': policy
            }
            return response
