import re
import sys
import json
import boto3
import base64


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


class Workspace:

    def __init__(self, deployment_name, region, user_id, detail: dict, log):
        self.deployment_name = deployment_name
        self.region = region
        self.user_id = user_id
        self.detail = detail
        self.log = log
        self.filename = None
        self.file_contents = None
        self.__aws_s3_client = None
        self.__aws_dynamodb_client = None

    @property
    def aws_s3_client(self):
        """Returns the boto3 S3 session (establishes one automatically if one does not already exist)"""
        if self.__aws_s3_client is None:
            self.__aws_s3_client = boto3.client('s3', region_name=self.region)
        return self.__aws_s3_client

    @property
    def aws_dynamodb_client(self):
        """Returns the boto3 DynamoDB session (establishes one automatically if one does not already exist)"""
        if self.__aws_dynamodb_client is None:
            self.__aws_dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        return self.__aws_dynamodb_client

    def upload_object(self):
        response = self.aws_s3_client.put_object(
            Body=self.file_contents,
            Bucket=f'{self.deployment_name}-workspace',
            Key='shared/' + self.filename
        )
        assert response, f"Failed to upload object to shared workspace"
        return True

    def list_objects(self):
        response = self.aws_s3_client.list_objects_v2(
            Bucket=f'{self.deployment_name}-workspace',
            Prefix='shared/'
        )
        assert response, f"list_objects in shared workspace failed"
        return response

    def get_object(self):
        response = self.aws_s3_client.get_object(
            Bucket=f'{self.deployment_name}-workspace',
            Key='shared/' + self.filename
        )
        assert response, f"get_object from shared workspace failed for filename {self.filename}"
        return response['Body'].read()

    def delete_object(self):
        response = self.aws_s3_client.delete_object(
            Bucket=f'{self.deployment_name}-workspace',
            Key='shared/' + self.filename
        )
        assert response, f"delete_object from shared workspace failed for filename {self.filename}"
        return True

    def list(self):

        list_results = self.list_objects()
        regex = 'shared/(.*)'
        file_list = []
        file_name_list = []
        if 'Contents' in list_results:
            for l in list_results['Contents']:
                search = re.search(regex, l['Key'])
                if search.group(1):
                    file_list.append(l['Key'])
            for file_entry in file_list:
                file_name = re.search(regex, file_entry).group(1)
                file_name_list.append(file_name)
        return format_response(200, 'success', 'list files succeeded', None, files=file_name_list)

    def get(self):
        if 'filename' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.filename = self.detail['filename']

        # List files in bucket to confirm that file is present
        list_results = self.list_objects()
        regex = 'shared/(.*)'
        file_list = []
        file_name_list = []
        if 'Contents' in list_results:
            for l in list_results['Contents']:
                search = re.search(regex, l['Key'])
                if search.group(1):
                    file_list.append(l['Key'])
            for file_entry in file_list:
                file_name = re.search(regex, file_entry).group(1)
                file_name_list.append(file_name)
        if self.filename in file_name_list:
            get_object_results = self.get_object()
            encoded_file = base64.b64encode(get_object_results).decode()
            return format_response(
                200, 'success', 'get file succeeded', None, filename=self.filename, file_contents=encoded_file
            )
        else:
            return format_response(404, 'failed', 'file not found', self.log)

    def create(self):
        filename_details = ['filename', 'file_contents']
        for i in filename_details:
            if i not in self.detail:
                return format_response(400, 'failed', 'invalid detail', self.log)
        self.filename = self.detail['filename']
        self.file_contents = self.detail['file_contents']

        try:
            decoded_file = base64.b64decode(self.file_contents)
            decoded_file.decode()
        except:
            return format_response(415, 'failed', 'file_contents must be bytes', self.log)

        if sys.getsizeof(decoded_file) > 26214400:
            return format_response(413, 'failed', 'max file size exceeded', self.log)

        self.file_contents = decoded_file
        self.upload_object()
        return format_response(200, 'success', 'create file succeeded', None)

    def delete(self):
        if 'filename' not in self.detail:
            return format_response(400, 'failed', 'invalid detail', self.log)
        self.filename = self.detail['filename']

        # List files in bucket to confirm that file is present
        list_results = self.list_objects()
        regex = 'shared/(.*)'
        file_list = []
        file_name_list = []
        if 'Contents' in list_results:
            for l in list_results['Contents']:
                search = re.search(regex, l['Key'])
                if search.group(1):
                    file_list.append(l['Key'])
            for file_entry in file_list:
                file_name = re.search(regex, file_entry).group(1)
                file_name_list.append(file_name)
        if self.filename in file_name_list:
            self.delete_object()
            return format_response(200, 'success', 'delete file succeeded', None)
        else:
            return format_response(404, 'failed', 'file not found', self.log)

    def kill(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)

    def update(self):
        return format_response(405, 'failed', 'command not accepted for this resource', self.log)
