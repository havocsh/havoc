import json
import botocore
import boto3
import time as t


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


class Domain:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Instantiate a Domain instance
        """
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.domain_name = None
        self.hosted_zone = None
        self.certificate_arn = None
        self.validation_record = None
        self.__aws_dynamodb_client = None
        self.__aws_route53_client = None
        self.__aws_acm_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    @property
    def aws_route53_client(self):
        """Returns the boto3 Route53 session (establishes one automatically if one does not already exist)"""
        if self.__aws_route53_client is None:
            self.__aws_route53_client = boto3.client('route53', region_name=self.region)
        return self.__aws_route53_client
    
    @property
    def aws_acm_client(self):
        """Returns the boto3 ACM session (establishes one automatically if one does not already exist)"""
        if self.__aws_acm_client is None:
            self.__aws_acm_client = boto3.client('acm', region_name=self.region)
        return self.__aws_acm_client

    def query_domains(self):
        domains = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-domains'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                domains['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return domains

    def get_domain_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-domains',
            Key={
                'domain_name': {'S': self.domain_name}
            }
        )

    def verify_hosted_zone(self):
        try:
            zone = self.aws_route53_client.get_hosted_zone(
                Id=self.hosted_zone
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        if zone:
            if zone['HostedZone']['Name'] == self.domain_name + '.':
                return 'valid_domain'
            else:
                return 'invalid_domain'
        return 'invalid_domain'
    
    def create_domain_cert(self):
        try:
            response = self.aws_acm_client.request_certificate(
                DomainName = f'*.{self.domain_name}',
                ValidationMethod='DNS',
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                },
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': f'{self.deployment_name}-{self.domain_name}-certificate'
                    },
                ]
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        self.certificate_arn = response['CertificateArn']
        return 'domain_cert_created'

    def get_domain_validation_records(self):
        try:
            certificate_metadata = self.aws_acm_client.describe_certificate(
                CertificateArn = self.certificate_arn
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        resource_record = certificate_metadata['Certificate']['DomainValidationOptions'][0]['ResourceRecord']
        name = resource_record['Name']
        value = resource_record['Value']
        self.validation_record = [name, value]
        return 'domain_validation_records_requested'
    
    def create_validate_cert(self):
        name = self.validation_record[0]
        value = self.validation_record[1]
        try:
            self.aws_route53_client.change_resource_record_sets(
                HostedZoneId = self.hosted_zone,
                ChangeBatch = {
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet':{
                                'Name': name,
                                'Type': 'CNAME',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': value
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'cert_validation_record_created'
    
    def delete_domain_cert(self):
        try:
            self.aws_acm_client.delete_certificate(
                CertificateArn = self.certificate_arn
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'domain_cert_deleted'
    
    def delete_validate_cert(self):
        name = self.validation_record[0]
        value = self.validation_record[1]
        try:
            self.aws_route53_client.change_resource_record_sets(
                HostedZoneId = self.hosted_zone,
                ChangeBatch = {
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': name,
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': value
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'cert_validation_record_deleted'

    def create_domain_entry(self):
        # Check for domain conflict
        existing_domain = self.get_domain_entry()
        if 'Item' in existing_domain:
            return 'domain_exists'
        
        # Verify the hosted zone exists
        valid_domain = self.verify_hosted_zone()
        if valid_domain != 'valid_domain':
            return valid_domain
        
        # Create a wildcard certificate for the domain
        create_domain_cert_response = self.create_domain_cert()
        if create_domain_cert_response != 'domain_cert_created':
            return create_domain_cert_response
        
        # Wait a few seconds and then get the domain validation resource records from the certificate
        t.sleep(15)
        get_domain_validation_records_response = self.get_domain_validation_records()
        if get_domain_validation_records_response != 'domain_validation_records_requested':
            return get_domain_validation_records_response
        
        # Create the DNS entry that validates the certificate
        create_validate_cert_response = self.create_validate_cert()
        if create_validate_cert_response != 'cert_validation_record_created':
            return create_validate_cert_response
        
        # Add the domain details to the DynamoDB domains table
        api_domain = 'no'
        tasks = 'None'
        listeners = 'None'
        host_names = 'None'
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-domains',
                Key={
                    'domain_name': {'S': self.domain_name}
                },
                UpdateExpression='set hosted_zone=:hosted_zone, api_domain=:api_domain, '
                                 'certificate_arn=:certificate_arn, validation_record=:validation_record, '
                                 'tasks=:tasks, listeners=:listeners, host_names=:host_names, user_id=:user_id',
                ExpressionAttributeValues={
                    ':hosted_zone': {'S': self.hosted_zone},
                    ':api_domain': {'S': api_domain},
                    ':certificate_arn': {'S': self.certificate_arn},
                    ':validation_record': {'SS': self.validation_record},
                    ':tasks': {'SS': [tasks]},
                    ':listeners': {'SS': [listeners]},
                    ':host_names': {'SS': [host_names]},
                    ':user_id': {'S': self.user_id}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'domain_created'

    def delete_domain_entry(self):
        # Verify the domain exists
        domain_entry = self.get_domain_entry()
        if not domain_entry:
            return 'domain_entry_not_found'
        
        # Verify that the domain can be deleted
        api_domain = domain_entry['Item']['api_domain']['S']
        tasks = domain_entry['Item']['tasks']['SS']
        if api_domain == 'yes':
            return 'is_api_domain'
        if 'None' not in tasks:
            return 'has_associated_tasks'
        
        # Delete the wildcard certificate for the domain
        self.certificate_arn = domain_entry['Item']['certificate_arn']['S']
        delete_domain_cert_response = self.delete_domain_cert()
        if delete_domain_cert_response != 'domain_cert_deleted':
            return delete_domain_cert_response

        # Delete the certificate validation resource record
        self.validation_record = domain_entry['Item']['validation_record']['SS']
        delete_validate_cert_response = self.delete_validate_cert()
        if delete_validate_cert_response != 'cert_validation_record_deleted':
            return delete_validate_cert_response

        # Delete the domain details from the DynamoDB domains table
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-domains',
                Key={
                    'domain_name': {'S': self.domain_name}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'domain_deleted'

    def create(self):
        domain_details = ['domain_name', 'hosted_zone']
        for i in domain_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)
        self.domain_name = self.detail['domain_name']
        self.hosted_zone = self.detail['hosted_zone']

        # Create domain entry
        create_domain_entry_response = self.create_domain_entry()
        if create_domain_entry_response == 'domain_exists':
            return format_response(409, 'failed', f'{self.domain_name} already exists', self.log)
        elif create_domain_entry_response == 'invalid_domain':
            return format_response(404, 'failed', f'hosted_zone {self.hosted_zone} does not exist', self.log)
        elif create_domain_entry_response == 'domain_created':
            return format_response(200, 'success', 'create domain succeeded', None)
        else:
            return format_response(500, 'failed', f'create domain failed with error {create_domain_entry_response}', self.log)

    def delete(self):
        if 'domain_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.domain_name = self.detail['domain_name']

        # Delete domain entry
        delete_domain_entry_response = self.delete_domain_entry()
        if delete_domain_entry_response == 'domain_entry_not_found':
            return format_response(404, 'failed', f'domain {self.domain_name} does not exist', self.log)
        elif delete_domain_entry_response == 'is_api_domain':
            return format_response(409, 'failed', 'cannot delete the primary API domain', self.log)
        elif delete_domain_entry_response == 'has_associated_tasks':
            return format_response(409, 'failed', 'cannot delete domain that is assigned to active tasks', self.log)
        elif delete_domain_entry_response == 'domain_deleted':
            return format_response(200, 'success', 'delete domain succeeded', None)
        else:
            return format_response(500, 'failed', f'delete domain failed with error {delete_domain_entry_response}', self.log)

    def get(self):
        if 'domain_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.domain_name = self.detail['domain_name']

        domain_entry = self.get_domain_entry()
        if 'Item' not in domain_entry:
            return format_response(404, 'failed', f'domain {self.domain_name} does not exist', self.log)

        hosted_zone = domain_entry['Item']['hosted_zone']['S']
        api_domain = domain_entry['Item']['api_domain']['S']
        associated_tasks = domain_entry['Item']['tasks']['SS']
        associated_listeners = domain_entry['Item']['listeners']['SS']
        associated_host_names = domain_entry['Item']['host_names']['SS']
        domain_creator_id = domain_entry['Item']['user_id']['S']
        return format_response(200, 'success', 'get domain succeeded', None, domain_name=self.domain_name,
                               hosted_zone=hosted_zone, api_domain=api_domain, associated_tasks=associated_tasks,
                               associated_listeners=associated_listeners, associated_host_names=associated_host_names,
                               domain_creator_id=domain_creator_id)

    def list(self):
        domains_list = []
        domains = self.query_domains()
        for item in domains['Items']:
            self.domain_name = item['domain_name']['S']
            domains_list.append(self.domain_name)
        return format_response(200, 'success', 'list domains succeeded', None, domains=domains_list)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
