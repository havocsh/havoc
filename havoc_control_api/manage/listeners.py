import os
import re
import ast
import json
import botocore
import boto3
import time as t
from datetime import datetime


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


class Listener:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        """
        Instantiate a Portgroup instance
        """
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.vpc_id = os.environ['VPC_ID']
        self.subnet_0 = os.environ['SUBNET_0']
        self.subnet_1 = os.environ['SUBNET_1']
        self.default_security_group = os.environ['SECURITY_GROUP']
        self.portgroups = []
        self.security_groups = []
        self.task_name = None
        self.host_name = None
        self.domain_name = None
        self.hosted_zone = None
        self.listener_name = None
        self.listener_config = {}
        self.load_balancer_arn = None
        self.load_balancer_dns_name = None
        self.target_ip = None
        self.certificate_arn = None
        self.__aws_dynamodb_client = None
        self.__aws_elbv2_client = None
        self.__aws_acm_client = None
        self.__aws_ecs_client = None
        self.__aws_route53_client = None

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client
    
    @property
    def aws_elbv2_client(self):
        """Returns the boto3 ELBv2 session (establishes one automatically if one does not already exist)"""
        if self.__aws_elbv2_client is None:
            self.__aws_elbv2_client = boto3.client('elbv2', region_name=self.region)
        return self.__aws_elbv2_client
    
    @property
    def aws_acm_client(self):
        """Returns the boto3 ACM session (establishes one automatically if one does not already exist)"""
        if self.__aws_acm_client is None:
            self.__aws_acm_client = boto3.client('acm', region_name=self.region)
        return self.__aws_acm_client
    
    @property
    def aws_ecs_client(self):
        """Returns the boto3 ECS session (establishes one automatically if one does not already exist)"""
        if self.__aws_ecs_client is None:
            self.__aws_ecs_client = boto3.client('ecs', region_name=self.region)
        return self.__aws_ecs_client
    
    @property
    def aws_route53_client(self):
        """Returns the boto3 Route53 session for this project (establishes one automatically if one does not already exist)"""
        if self.__aws_route53_client is None:
            self.__aws_route53_client = boto3.client('route53')
        return self.__aws_route53_client

    def query_listeners(self):
        listeners = {'Items': []}
        scan_kwargs = {'TableName': f'{self.deployment_name}-listeners'}
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.aws_dynamodb_client.scan(**scan_kwargs)
            for item in response['Items']:
                listeners['Items'].append(item)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return listeners

    def get_listener_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-listeners',
            Key={
                'listener_name': {'S': self.listener_name}
            }
        )

    def get_listener_details(self, lb_arn):
        return self.aws_elbv2_client.describe_listeners(
            LoadBalancerArn=lb_arn
        )
    
    def get_task_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-tasks',
            Key={
                'task_name': {'S': self.task_name}
            }
        )
    
    def get_ecstask_details(self, ecs_task_id):
        return self.aws_ecs_client.describe_tasks(
            cluster=f'{self.deployment_name}-task-cluster',
            tasks=[ecs_task_id]
        )
    
    def create_load_balancer(self):
        load_balancer_name = f'{self.deployment_name}-{self.listener_name}'
        load_balancer_name = re.sub('_', '', load_balancer_name)
        try:
            create_load_balancer_response = self.aws_elbv2_client.create_load_balancer(
                Name = load_balancer_name[0:31],
                Subnets = [self.subnet_0, self.subnet_1],
                SecurityGroups = [self.default_security_group] + self.security_groups,
                Type = 'application',
                IpAddressType = 'ipv4'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        self.load_balancer_arn = create_load_balancer_response['LoadBalancers'][0]['LoadBalancerArn']
        self.load_balancer_dns_name = create_load_balancer_response['LoadBalancers'][0]['DNSName']
        try:
            self.aws_elbv2_client.modify_load_balancer_attributes(
                LoadBalancerArn = self.load_balancer_arn,
                Attributes = [
                    {
                        'Key': 'idle_timeout.timeout_seconds',
                        'Value': '5'
                    },
                ]
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'load_balancer_created'

    def delete_load_balancer(self):
        try:
            self.aws_elbv2_client.delete_load_balancer(
                LoadBalancerArn = self.load_balancer_arn
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'load_balancer_deleted'
    
    def create_target_group(self, port):
        target_group_name = f'{self.listener_name}-{port}'
        target_group_name = re.sub('_', '', target_group_name)
        listener_type = self.listener_config[port]['listener_type']
        try:
            response = self.aws_elbv2_client.create_target_group(
                Name = target_group_name[0:31],
                Protocol = listener_type,
                Port = int(port),
                VpcId = self.vpc_id,
                HealthCheckProtocol = listener_type,
                TargetType = 'ip',
                IpAddressType = 'ipv4'
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        self.listener_config[port]['target_group_arn'] = response['TargetGroups'][0]['TargetGroupArn']
        return 'target_group_created'
    
    def delete_target_group(self, port):
        target_group_arn = self.listener_config[port]['target_group_arn']
        try:
            self.aws_elbv2_client.delete_target_group(
                TargetGroupArn = target_group_arn
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'target_group_deleted'
    
    def register_target(self, port):
        target_group_arn = self.listener_config[port]['target_group_arn']
        try:
            self.aws_elbv2_client.register_targets(
                TargetGroupArn = target_group_arn,
                Targets=[
                    {
                        'Id': self.target_ip,
                        'Port': int(port)
                    },
                ]
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'target_registered'
    
    def get_certificate(self):
        response = self.aws_acm_client.list_certificates(
            CertificateStatuses = ['ISSUED']
            )
        if 'CertificateSummaryList' in response:
            certificate_summary_list = response['CertificateSummaryList']
            for certificate in certificate_summary_list:
                if self.domain_name in certificate['DomainName']:
                    self.certificate_arn = certificate['CertificateArn']

    def create_lb_listener(self, port):
        listener_type = self.listener_config[port]['listener_type']
        target_group_arn = self.listener_config[port]['target_group_arn']
        lb_listener_args = {'LoadBalancerArn': self.load_balancer_arn, 'Protocol': listener_type, 'Port': int(port)}
        lb_listener_args['DefaultActions'] = [{'TargetGroupArn': target_group_arn, 'Type': 'forward'}]
        if listener_type == 'HTTPS':
            lb_listener_args['SslPolicy'] = 'ELBSecurityPolicy-2016-08'
            lb_listener_args['Certificates'] = [{'CertificateArn': self.certificate_arn}]
        try:
            response = self.aws_elbv2_client.create_listener(**lb_listener_args)
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        self.listener_config[port]['listener_arn'] = response['Listeners'][0]['ListenerArn']
        return 'lb_listner_created'
    
    def delete_lb_listener(self, port):
        listener_arn = self.listener_config[port]['listener_arn']
        try:
            self.aws_elbv2_client.delete_listener(
                ListenerArn = listener_arn
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'lb_listener_deleted'
    
    def create_listener_entry(self):
        timestamp = datetime.now().strftime('%s')
        listener_config = json.dumps(self.listener_config)
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-listeners',
                Key={
                    'listener_name': {'S': self.listener_name}
                },
                UpdateExpression='set '
                                 'listener_config=:listener_config, '
                                 'task_name=:task_name, '
                                 'target_ip=:target_ip, '
                                 'portgroups=:portgroups, '
                                 'host_name=:host_name, '
                                 'domain_name=:domain_name, '
                                 'load_balancer_arn=:load_balancer_arn, '
                                 'load_balancer_dns_name=:load_balancer_dns_name, '
                                 'certificate_arn=:certificate_arn, '
                                 'user_id=:user_id, '
                                 'create_time=:create_time',
                ExpressionAttributeValues={
                    ':listener_config': {'S': listener_config},
                    ':task_name': {'S': self.task_name},
                    ':target_ip': {'S': self.target_ip},
                    ':portgroups': {'SS': self.portgroups},
                    ':host_name': {'S': self.host_name},
                    ':domain_name': {'S': self.domain_name},
                    ':load_balancer_arn': {'S': self.load_balancer_arn},
                    ':load_balancer_dns_name': {'S': self.load_balancer_dns_name},
                    ':certificate_arn': {'S': self.certificate_arn},
                    ':user_id': {'S': self.user_id},
                    ':create_time': {'S': timestamp}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'listener_entry_created'
    
    def delete_listener_entry(self):
        try:
            self.aws_dynamodb_client.delete_item(
                TableName=f'{self.deployment_name}-listeners',
                Key={
                    'listener_name': {'S': self.listener_name}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'listener_entry_deleted'

    def get_portgroup_entry(self, portgroup_name):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-portgroups',
            Key={
                'portgroup_name': {'S': portgroup_name}
            }
        )

    def update_portgroup_entry(self, portgroup_name, listeners):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-portgroups',
                Key={
                    'portgroup_name': {'S': portgroup_name}
                },
                UpdateExpression='set listeners=:listeners',
                ExpressionAttributeValues={
                    ':listeners': {'SS': listeners}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'portgroup_updated'
    
    def update_task_entry(self, listeners):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-tasks',
                Key={
                    'task_name': {'S': self.task_name}
                },
                UpdateExpression='set listeners=:listeners',
                ExpressionAttributeValues={
                    ':listeners': {'SS': listeners}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'task_updated'
    
    def get_domain_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-domains',
            Key={
                'domain_name': {'S': self.domain_name}
            }
        )

    def create_resource_record_set(self):
        try:
            self.aws_route53_client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet':{
                                'Name': f'{self.host_name}.{self.domain_name}',
                                'Type': 'CNAME',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': self.load_balancer_dns_name
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
        return 'resource_record_set_created'
    
    def delete_resource_record_set(self):
        try:
            self.aws_route53_client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': f'{self.host_name}.{self.domain_name}',
                                'Type': 'CNAME',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': self.load_balancer_dns_name
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
        return 'resource_record_set_deleted'

    def update_domain_entry(self, domain_listeners, host_names):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-domains',
                Key={
                    'domain_name': {'S': self.domain_name}
                },
                UpdateExpression='set listeners=:listeners, host_names=:host_names',
                ExpressionAttributeValues={
                    ':listeners': {'SS': domain_listeners},
                    ':host_names': {'SS': host_names}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'domain_entry_updated'
    
    def get_deployment_entry(self):
        return self.aws_dynamodb_client.get_item(
            TableName=f'{self.deployment_name}-deployment',
            Key={
                'deployment_name': {'S': self.deployment_name}
            }
        )
    
    def update_deployment_entry(self, active_resources):
        try:
            self.aws_dynamodb_client.update_item(
                TableName=f'{self.deployment_name}-deployment',
                Key={
                    'deployment_name': {'S': self.deployment_name}
                },
                UpdateExpression='set active_resources=:active_resources',
                ExpressionAttributeValues={
                    ':active_resources': {'M': active_resources}
                }
            )
        except botocore.exceptions.ClientError as error:
            return error
        except botocore.exceptions.ParamValidationError as error:
            return error
        return 'deployment_updated'
    
    def create_listener(self, listener_config):
        # Validate inputs
        https_listener = None
        for listener_port in listener_config:
            listener_type = listener_config[listener_port]['listener_type']
            if listener_type not in ['HTTP', 'HTTPS']:
                return 'failed_listener_type_not_supported'
            if listener_type == 'HTTPS' and (self.domain_name is None or self.host_name is None):
                return 'failed_https_listener_type_requires_domain_name_and_host_name'
            if listener_type == 'HTTPS':
                https_listener = True
            self.listener_config[listener_port] = {'listener_type': listener_type}
        get_listener_entry_response = self.get_listener_entry()
        if 'Item' in get_listener_entry_response:
            return 'failed_listener_exists'
        if self.domain_name:
            get_domain_entry_response = self.get_domain_entry()
            if 'Item' not in get_domain_entry_response:
                return 'failed_domain_name_not_found'
            if self.host_name in get_domain_entry_response['Item']['host_names']['SS']:
                return 'failed_host_name_exists_for_domain'
            self.hosted_zone = get_domain_entry_response['Item']['hosted_zone']['S']
            if 'None' in get_domain_entry_response['Item']['listeners']['SS']:
                domain_listeners = []
            else:
                domain_listeners = get_domain_entry_response['Item']['listeners']['SS']
            domain_listeners.append(self.listener_name)
            if 'None' in get_domain_entry_response['Item']['host_names']['SS']:
                associated_host_names = []
            else:
                associated_host_names = get_domain_entry_response['Item']['host_names']['SS']
            associated_host_names.append(self.host_name)
        
        # Get details for the task that will be the target for the LB
        task_entry = self.get_task_entry()
        ecs_task_id = task_entry['Item']['ecs_task_id']['S']
        if ecs_task_id == 'remote_task':
            return 'failed_remote_task_cannot_be_lb_target'
        task_details = self.get_ecstask_details(ecs_task_id)
        self.target_ip = task_details['tasks'][0]['attachments'][0]['details'][3]['value']

        # If HTTPS listener type, get the certificate details
        if https_listener:
            self.get_certificate()
            if self.certificate_arn is None:
                return 'failed_no_certificate_found_for_domain'
        
        # Validate portgroups and update portgroup's associated listeners
        for portgroup in self.portgroups:
            portgroup_entry = self.get_portgroup_entry(portgroup)
            if 'Item' not in portgroup_entry:
                return 'failed_portgroup_not_found'
            self.security_groups.append(portgroup_entry['Item']['securitygroup_id']['S'])
            if 'None' in portgroup_entry['Item']['listeners']['SS']:
                portgroup_listeners = []
            else:
                portgroup_listeners = portgroup_entry['Item']['listeners']['SS']
            portgroup_listeners.append(self.listener_name)
            update_portgroup_entry_response = self.update_portgroup_entry(portgroup, portgroup_listeners)
            if update_portgroup_entry_response != 'portgroup_updated':
                return update_portgroup_entry_response
        
        # Update associated listeners for the task
        if 'None' in task_entry['Item']['listeners']['SS']:
            task_listeners = []
        else:
            task_listeners = task_entry['Item']['listeners']['SS']
        task_listeners.append(self.listener_name)
        update_task_entry_response = self.update_task_entry(task_listeners)
        if update_task_entry_response != 'task_updated':
            return update_task_entry_response
        
        # Create a new load balancer
        create_load_balancer_response = self.create_load_balancer()
        if create_load_balancer_response != 'load_balancer_created':
            return create_load_balancer_response

        # Create a target group, register the task as a target and create the lb listener
        for listener_port in self.listener_config:
            create_target_group_response = self.create_target_group(listener_port)
            if create_target_group_response != 'target_group_created':
                return create_target_group_response
                
            register_target_response = self.register_target(listener_port)
            if register_target_response != 'target_registered':
                return register_target_response
        
            create_listener_response = self.create_lb_listener(listener_port)
            if create_listener_response != 'lb_listner_created':
                return create_listener_response
        
        # Set up Route53 entry if a domain name is present
        if self.domain_name:
            create_resource_record_set_response = self.create_resource_record_set()
            if create_resource_record_set_response != 'resource_record_set_created':
                return create_resource_record_set_response
            update_domain_entry_response = self.update_domain_entry(domain_listeners, associated_host_names)
            if update_domain_entry_response != 'domain_entry_updated':
                return update_domain_entry_response

        # Create a listener entry in DynamoDB
        create_listener_entry_response = self.create_listener_entry()
        if create_listener_entry_response != 'listener_entry_created':
            return create_listener_entry_response
        
        # Add listener to active_resources in deployment table
        deployment_details = self.get_deployment_entry()
        active_resources = deployment_details['Item']['active_resources']['M']
        active_listeners = active_resources['listeners']['SS']
        if active_listeners == ['None']:
            active_listeners = [self.listener_name]
        else:
            active_listeners.append(self.listener_name)
        active_resources['listeners']['SS'] = active_listeners
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response
        return 'listener_created'
    
    def delete_listener(self):
        # Get listener details
        listener_entry = self.get_listener_entry()
        if 'Item' not in listener_entry:
            return 'listener_not_found'
        self.load_balancer_arn = listener_entry['Item']['load_balancer_arn']['S']
        self.load_balancer_dns_name = listener_entry['Item']['load_balancer_dns_name']['S']
        self.certificate_arn = listener_entry['Item']['certificate_arn']['S']
        self.task_name = listener_entry['Item']['task_name']['S']
        self.target_ip = listener_entry['Item']['target_ip']['S']
        self.host_name = listener_entry['Item']['host_name']['S']
        self.domain_name = listener_entry['Item']['domain_name']['S']
        self.load_balancer_dns_name = listener_entry['Item']['load_balancer_dns_name']['S']
        self.portgroups = listener_entry['Item']['portgroups']['SS']
        self.listener_config = json.loads(listener_entry['Item']['listener_config']['S'])

        # Delete Route53 entry if a domain name is present
        if self.domain_name:
            get_domain_entry_response = self.get_domain_entry()
            if 'Item' not in get_domain_entry_response:
                return 'domain_name_not_found'
            self.hosted_zone = get_domain_entry_response['Item']['hosted_zone']['S']
            domain_listeners = get_domain_entry_response['Item']['listeners']['SS']
            domain_listeners.remove(self.listener_name)
            if not domain_listeners:
                domain_listeners = ['None']
            associated_host_names = get_domain_entry_response['Item']['host_names']['SS']
            associated_host_names.remove(self.host_name)
            if not associated_host_names:
                associated_host_names = ['None']
            delete_resource_record_set_response = self.delete_resource_record_set()
            if delete_resource_record_set_response != 'resource_record_set_deleted':
                return delete_resource_record_set_response
            update_domain_entry_response = self.update_domain_entry(domain_listeners, associated_host_names)
            if update_domain_entry_response != 'domain_entry_updated':
                return update_domain_entry_response
        
        # Delete lb listener and target group
        for listener_port in self.listener_config:
            delete_lb_listener_response = self.delete_lb_listener(listener_port)
            if delete_lb_listener_response != 'lb_listener_deleted':
                return delete_lb_listener_response

            delete_target_group_response = self.delete_target_group(listener_port)
            if delete_target_group_response != 'target_group_deleted':
                return delete_target_group_response
            
        # Delete load balancer
        delete_load_balancer_response = self.delete_load_balancer()
        if delete_load_balancer_response != 'load_balancer_deleted':
            return delete_load_balancer_response
        
        # Update portgroup listener reference
        for portgroup in self.portgroups:
            portgroup_entry = self.get_portgroup_entry(portgroup)
            portgroup_listeners = portgroup_entry['Item']['listeners']['SS']
            portgroup_listeners.remove(self.listener_name)
            if not portgroup_listeners:
                portgroup_listeners = ['None']
            update_portgroup_entry_response = self.update_portgroup_entry(portgroup, portgroup_listeners)
            if update_portgroup_entry_response != 'portgroup_updated':
                return update_portgroup_entry_response
        
        # Update task listener reference
        task_entry = self.get_task_entry()
        task_listeners = task_entry['Item']['listeners']['SS']
        task_listeners.remove(self.listener_name)
        if not task_listeners:
            task_listeners = ['None']
        update_task_entry_response = self.update_task_entry(task_listeners)
        if update_task_entry_response != 'task_updated':
            return update_task_entry_response

        # Delete the listener entry in DynamoDB
        delete_listener_entry_response = self.delete_listener_entry()
        if delete_listener_entry_response != 'listener_entry_deleted':
            return delete_listener_entry_response
        
        # Remove listener from active_resources in deployment table
        deployment_details = self.get_deployment_entry()
        active_resources = deployment_details['Item']['active_resources']['M']
        active_listeners = active_resources['listeners']['SS']
        active_listeners.remove(self.listener_name)
        if len(active_listeners) == 0:
            active_listeners = ['None']
        active_resources['listeners']['SS'] = active_listeners
        update_deployment_entry_response = self.update_deployment_entry(active_resources)
        if update_deployment_entry_response != 'deployment_updated':
            return update_deployment_entry_response
        return 'listener_deleted'

    def create(self):
        listener_details = ['listener_name', 'listener_config', 'task_name', 'portgroups']
        for i in listener_details:
            if i not in self.detail:
                return format_response(400, 'failed', f'invalid detail: missing {i}', self.log)
            if not self.detail[i]:
                return format_response(400, 'failed', f'invalid detail: {i} cannot be null', self.log)
        self.listener_name = self.detail['listener_name']
        self.task_name = self.detail['task_name']
        self.portgroups = self.detail['portgroups']
        if isinstance(self.detail['listener_config'], dict):
            listener_config = self.detail['listener_config']
        else:
            listener_config = ast.literal_eval(self.detail['listener_config'])
        if 'domain_name' in self.detail:
            self.domain_name = self.detail['domain_name']
        if 'host_name' in self.detail:
            self.host_name = self.detail['host_name']
        if self.domain_name and not self.host_name:
            return format_response(400, 'failed', 'invalid detail: domain_name provided but no host_name', self.log)
        if self.host_name and not self.domain_name:
            return format_response(400, 'failed', 'invalid detail: host_name provided but no domain_name', self.log)
        
        create_listener_response = self.create_listener(listener_config)
        if create_listener_response == 'listener_created':
            return format_response(200, 'success', 'create listener succeeded', None, listener_name=self.listener_name,
                                   task_name=self.task_name, host_name=self.host_name, domain_name=self.domain_name,
                                   listener_config=listener_config, portgroups=self.portgroups)
        elif isinstance(create_listener_response, str) and 'failed_' in create_listener_response:
            return format_response(400, 'failed', f'create listener failed with error {create_listener_response}', self.log)
        else:
            return format_response(500, 'failed', f'create listener failed with error {create_listener_response}', self.log)

    def delete(self):
        if 'listener_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail: missing listener_name', self.log)
        self.listener_name = self.detail['listener_name']
        if not self.listener_name:
            return format_response(400, 'failed', 'invalid detail: listener_name cannot be null', self.log)

        delete_listener = self.delete_listener()
        if delete_listener == 'listener_deleted':
            return format_response(200, 'success', 'delete listener succeeded', None)
        elif isinstance(delete_listener, str) and delete_listener == 'listener_not_found':
            return format_response(404, 'failed', f'listener {self.listener_name} does not exist', self.log)
        elif isinstance(delete_listener, str) and delete_listener == 'domain_name_not_found':
            return format_response(404, 'failed', f'domain_name entry for listener {self.listener_name} does not exist', self.log)
        else:
            return format_response(500, 'failed', f'delete listener failed with error {delete_listener}', self.log)

    def get(self):
        if 'listener_name' not in self.detail:
            return format_response(400, 'failed', 'invalid detail: missing listener_name', self.log)
        self.listener_name = self.detail['listener_name']
        if not self.listener_name:
            return format_response(400, 'failed', 'invalid detail: listener_name cannot be null', self.log)

        listener_entry = self.get_listener_entry()
        if 'Item' not in listener_entry:
            return format_response(404, 'failed', f'listener {self.listener_name} does not exist', self.log)

        task_name = listener_entry['Item']['task_name']['S']
        host_name = listener_entry['Item']['host_name']['S']
        domain_name = listener_entry['Item']['domain_name']['S']
        portgroups = listener_entry['Item']['portgroups']['SS']
        listener_creator_id = listener_entry['Item']['user_id']['S']
        create_time = listener_entry['Item']['create_time']['S']
        listener_config = {}
        self.listener_config = json.loads(listener_entry['Item']['listener_config']['S'])
        for port in self.listener_config:
            listener_config[port] = {'listener_type': self.listener_config[port]['listener_type']}
        
        return format_response(200, 'success', 'get listener succeeded', None, listener_name=self.listener_name,
                               listener_config=listener_config, host_name=host_name, task_name=task_name,
                               domain_name=domain_name, listener_creator_id=listener_creator_id, create_time=create_time,
                               portgroups=portgroups)

    def list(self):
        listeners_list = []
        listeners = self.query_listeners()
        for item in listeners['Items']:
            self.listener_name = item['listener_name']['S']
            listeners_list.append(self.listener_name)
        return format_response(200, 'success', 'list listeners succeeded', None, listeners=listeners_list)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
