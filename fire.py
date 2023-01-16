#!/usr/bin/env python3
from multiprocessing import Pool
from pathlib import Path
import shutil
import tldextract
import boto3
import botocore
import os
import sys
import random
import datetime
import tzlocal
import argparse
import json
import configparser
from typing import Tuple, List, Union, Any, Callable
from time import sleep

AWS_DEFAULT_REGIONS = [
    "ap-south-1",
    "eu-north-1",
    "eu-west-3",
    "eu-west-2",
    "eu-west-1",
    "ap-northeast-3",
    "ap-northeast-2",
    "ap-northeast-1",
    "ca-central-1",
    "sa-east-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "eu-central-1",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2"
]

class FireProx(object):
    def __init__(self, arguments: argparse.Namespace, help_text: str):
        self.profile_name = arguments.profile_name
        self.access_key = arguments.access_key
        self.secret_access_key = arguments.secret_access_key
        self.session_token = arguments.session_token
        self.region = arguments.region
        self.command = arguments.command
        self.api_id = arguments.api_id
        self.url = arguments.url
        self.api_list = []
        self.client = None
        self.help = help_text

        if self.access_key and self.secret_access_key:
            if not self.region:
                self.error('Please provide a region with AWS credentials')

        if not self.load_creds():
            self.error('Unable to load AWS credentials')

        if not self.command:
            self.error('Please provide a valid command')

    def __str__(self):
        return 'FireProx()'

    def _try_instance_profile(self) -> bool:
        """Try instance profile credentials

        :return:
        """
        try:
            if not self.region:
                self.client = boto3.client('apigateway')
            else:
                self.client = boto3.client(
                    'apigateway',
                    region_name=self.region
                )
            self.client.get_account()
            self.region = self.client._client_config.region_name
            return True
        except:
            return False

    def load_creds(self) -> bool:
        """Load credentials from AWS config and credentials files if present.

        :return:
        """
        # If no access_key, secret_key, or profile name provided, try instance credentials
        if not any([self.access_key, self.secret_access_key, self.profile_name]):
            return self._try_instance_profile()
        # Read in AWS config/credentials files if they exist
        credentials = configparser.ConfigParser()
        credentials.read(os.path.expanduser('~/.aws/credentials'))
        config = configparser.ConfigParser()
        config.read(os.path.expanduser('~/.aws/config'))
        # If profile in files, try it, but flow through if it does not work
        config_profile_section = f'profile {self.profile_name}'
        if self.profile_name in credentials:
            if config_profile_section not in config and self.region is None:
                print(f'Please create a section for {self.profile_name} in your ~/.aws/config file or provide region')
                return False
            # if region is not set, load it from config
            if self.region is None:
                self.region = config[config_profile_section].get('region', 'us-east-1')
            try:
                self.client = boto3.session.Session(profile_name=self.profile_name,
                        region_name=self.region).client('apigateway')
                self.client.get_account()
                return True
            except:
                pass
        # Maybe had profile, maybe didn't
        if self.access_key and self.secret_access_key:
            try:
                self.client = boto3.client(
                    'apigateway',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_access_key,
                    aws_session_token=self.session_token,
                    region_name=self.region
                )
                self.client.get_account()
                if self.region is None:
                    self.region = self.client._client_config.region_name
                # Save/overwrite config if profile specified
                if self.profile_name:
                    if config_profile_section not in config:
                        config.add_section(config_profile_section)
                    config[config_profile_section]['region'] = self.region
                    with open(os.path.expanduser('~/.aws/config'), 'w') as file:
                        config.write(file)
                    if self.profile_name not in credentials:
                        credentials.add_section(self.profile_name)
                    credentials[self.profile_name]['aws_access_key_id'] = self.access_key
                    credentials[self.profile_name]['aws_secret_access_key'] = self.secret_access_key
                    if self.session_token:
                        credentials[self.profile_name]['aws_session_token'] = self.session_token
                    else:
                        credentials.remove_option(self.profile_name, 'aws_session_token')
                    with open(os.path.expanduser('~/.aws/credentials'), 'w') as file:
                        credentials.write(file)
                return True
            except:
                return False
        else:
            return False

    def error(self, error):
        print(self.help)
        sys.exit(error)

    def get_template(self):
        url = self.url
        if url[-1] == '/':
            url = url[:-1]

        title = 'fireprox_{}'.format(
            tldextract.extract(url).domain
        )
        version_date = f'{datetime.datetime.now():%Y-%m-%dT%XZ}'
        template = '''
        {
          "swagger": "2.0",
          "info": {
            "version": "{{version_date}}",
            "title": "{{title}}"
          },
          "basePath": "/",
          "schemes": [
            "https"
          ],
          "paths": {
            "/": {
              "get": {
                "parameters": [
                  {
                    "name": "proxy",
                    "in": "path",
                    "required": true,
                    "type": "string"
                  },
                  {
                    "name": "X-My-X-Forwarded-For",
                    "in": "header",
                    "required": false,
                    "type": "string"
                  }
                ],
                "responses": {},
                "x-amazon-apigateway-integration": {
                  "uri": "{{url}}/",
                  "responses": {
                    "default": {
                      "statusCode": "200"
                    }
                  },
                  "requestParameters": {
                    "integration.request.path.proxy": "method.request.path.proxy",
                    "integration.request.header.X-Forwarded-For": "method.request.header.X-My-X-Forwarded-For"
                  },
                  "passthroughBehavior": "when_no_match",
                  "httpMethod": "ANY",
                  "cacheNamespace": "irx7tm",
                  "cacheKeyParameters": [
                    "method.request.path.proxy"
                  ],
                  "type": "http_proxy"
                }
              }
            },
            "/{proxy+}": {
              "x-amazon-apigateway-any-method": {
                "produces": [
                  "application/json"
                ],
                "parameters": [
                  {
                    "name": "proxy",
                    "in": "path",
                    "required": true,
                    "type": "string"
                  },
                  {
                    "name": "X-My-X-Forwarded-For",
                    "in": "header",
                    "required": false,
                    "type": "string"
                  }
                ],
                "responses": {},
                "x-amazon-apigateway-integration": {
                  "uri": "{{url}}/{proxy}",
                  "responses": {
                    "default": {
                      "statusCode": "200"
                    }
                  },
                  "requestParameters": {
                    "integration.request.path.proxy": "method.request.path.proxy",
                    "integration.request.header.X-Forwarded-For": "method.request.header.X-My-X-Forwarded-For"
                  },
                  "passthroughBehavior": "when_no_match",
                  "httpMethod": "ANY",
                  "cacheNamespace": "irx7tm",
                  "cacheKeyParameters": [
                    "method.request.path.proxy"
                  ],
                  "type": "http_proxy"
                }
              }
            }
          }
        }
        '''
        template = template.replace('{{url}}', url)
        template = template.replace('{{title}}', title)
        template = template.replace('{{version_date}}', version_date)

        return str.encode(template)

    def create_api(self, url):
        if not url:
            self.error('Please provide a valid URL end-point')

        print(f'Creating => {url}...')

        template = self.get_template()
        response = self.client.import_rest_api(
            parameters={
                'endpointConfigurationTypes': 'REGIONAL'
            },
            body=template
        )
        resource_id, proxy_url = self.create_deployment(response['id'])
        self.store_api(
            response['id'],
            response['name'],
            response['createdDate'],
            response['version'],
            url,
            resource_id,
            proxy_url
        )

    def update_api(self, api_id, url):
        if not any([api_id, url]):
            self.error('Please provide a valid API ID and URL end-point')

        if url[-1] == '/':
            url = url[:-1]

        resource_id = self.get_resource(api_id)
        if resource_id:
            print(f'Found resource {resource_id} for {api_id}!')
            response = self.client.update_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='ANY',
                patchOperations=[
                    {
                        'op': 'replace',
                        'path': '/uri',
                        'value': '{}/{}'.format(url, r'{proxy}'),
                    },
                ]
            )
            return response['uri'].replace('/{proxy}', '') == url
        else:
            self.error(f'Unable to update, no valid resource for {api_id}')

    def delete_api(self, api_id):
        if not api_id:
            self.error('Please provide a valid API ID')
        retry = 3
        success = False
        error_msg = 'Generic error'
        while retry > 0 and not success:
            try:
                response = self.client.delete_rest_api(
                    restApiId=api_id
                )
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Code'] == 'NotFoundException':
                    error_msg = 'API not found'
                    break
                elif err.response['Error']['Code'] == 'TooManyRequestsException':
                    error_msg = 'Too many requests'
                    sleep(1)
                else:
                    error_msg = err.response['Error']['Message']
            except BaseException as e:
                error_msg = 'Generic error'
            else:
                success = True
                error_msg = ''
            finally:
                retry -= 1
        return success, error_msg


    def list_api(self, deleted_api_id=None, deleting=False):
        response = self.client.get_rest_apis()
        if deleting:
            return response['items']
        for item in response['items']:
            try:
                created_dt = item['createdDate']
                api_id = item['id']
                name = item['name']
                proxy_url = self.get_integration(api_id).replace('{proxy}', '')
                url = f'https://{api_id}.execute-api.{self.region}.amazonaws.com/fireprox/'
                if not api_id == deleted_api_id:
                    print(f'[{created_dt}] ({api_id}) {name}: {url} => {proxy_url}')
            except:
                pass

        return response['items']

    def store_api(self, api_id, name, created_dt, version_dt, url,
                  resource_id, proxy_url):
        print(
            f'[{created_dt}] ({api_id}) {name} => {proxy_url} ({url})'
        )

    def create_deployment(self, api_id):
        if not api_id:
            self.error('Please provide a valid API ID')

        response = self.client.create_deployment(
            restApiId=api_id,
            stageName='fireprox',
            stageDescription='FireProx Prod',
            description='FireProx Production Deployment'
        )
        resource_id = response['id']
        return (resource_id,
                f'https://{api_id}.execute-api.{self.region}.amazonaws.com/fireprox/')

    def get_resource(self, api_id):
        if not api_id:
            self.error('Please provide a valid API ID')
        response = self.client.get_resources(restApiId=api_id)
        items = response['items']
        for item in items:
            item_id = item['id']
            item_path = item['path']
            if item_path == '/{proxy+}':
                return item_id
        return None

    def get_integration(self, api_id):
        if not api_id:
            self.error('Please provide a valid API ID')
        resource_id = self.get_resource(api_id)
        response = self.client.get_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='ANY'
        )
        return response['uri']


def parse_arguments() -> Tuple[argparse.Namespace, str]:
    """Parse command line arguments and return namespace

    :return: Namespace for arguments and help text as a tuple
    """
    parser = argparse.ArgumentParser(description='FireProx API Gateway Manager')
    parser.add_argument('--profile_name',
                        help='AWS Profile Name to store/retrieve credentials', type=str, default=None)
    parser.add_argument('--access_key',
                        help='AWS Access Key', type=str, default=None)
    parser.add_argument('--secret_access_key',
                        help='AWS Secret Access Key', type=str, default=None)
    parser.add_argument('--session_token',
                        help='AWS Session Token', type=str, default=None)
    parser.add_argument('--region',
                        help='AWS Region', type=str, default=None)
    parser.add_argument('--command',
                        help='Commands: list, list_all, create, delete, prune, update', type=str, default=None)
    parser.add_argument('--api_id',
                        help='API ID', type=str, required=False)
    parser.add_argument('--url',
                        help='URL end-point', type=str, required=False)
    return parser.parse_args(), parser.format_help()


def parse_region(region:  str | List, mode: str = "all")-> Union[str, List, None]:
    """Parse 'region' and return the final region or set of regions according
    to mode
    """
    if region is None:
        return None
    if mode not in ['all', 'random']:
        raise ValueError(f"mode should one of ['all', 'random']")

    elif isinstance(region, str):
        # if region is a file containing regions, read from it
        if os.path.isfile(region):
            with open(region) as f:
                regions = [reg.strip() for reg in f.readlines()]
                if mode == "random":
                    return random.choice(regions)
                elif mode == "all":
                    return regions
        elif ',' in region:
            regions = region.split(sep=',')
            if mode == "random":
                return random.choice(regions)
            else:
                return regions
        else:
            return region

    elif isinstance(region, list):
        if mode == "all":
            return region
        elif mode == "random":
            return random.choice(region)


def main():
    """Run the main program

    :return:
    """
    args, help_text = parse_arguments()
    #fp = FireProx(args, help_text)
    if args.command == 'list':
        region_parsed = parse_region(args.region)
        if isinstance(region_parsed, list):
            for region in region_parsed:
                args.region = region
                fp = FireProx(args, help_text)
                print(f'Listing API\'s from {fp.region}...')
                result = fp.list_api(deleting=False)
        else:
            args.region = region_parsed
            fp = FireProx(args, help_text)
            print(f'Listing API\'s from {fp.region}...')
            result = fp.list_api(deleting=False)


    elif args.command == "list_all":
        for region in AWS_DEFAULT_REGIONS:
            args.region = region
            fp = FireProx(args, help_text)
            print(f'Listing API\'s from {fp.region}...')
            result = fp.list_api(deleting=False)


    elif args.command == 'create':
        if args.region is not None:
            # if region is a file containing regions, choose one randomly
            if os.path.isfile(args.region):
                with open(args.region) as f:
                    regions = [reg.strip() for reg in f.readlines()]
                    self.region = random.choice(regions)
        result = fp.create_api(fp.url)


    elif args.command == 'delete':
        region_parsed = parse_region(args.region)
        if region_parsed is None or isinstance(region_parsed, str):
            args.region = region_parsed
            fp = FireProx(args, help_text)
            result, msg = fp.delete_api(fp.api_id)
            if result:
                print(f'Deleting {fp.api_id} => Success!')
            else:
                print(f'Deleting {fp.api_id} => Failed! ({msg})')
        else:
            print(f'[ERROR] More than one region provided for command \'delete\'\n')
            sys.exit(1)


    elif args.command == 'prune':
        region_parsed = parse_region(args.region)
        if region_parsed is None:
            region_parsed = AWS_DEFAULT_REGIONS
        if isinstance(region_parsed, str):
            region_parsed = [region_parsed]
        while True:
            choice = input(f"This will delete ALL APIs from region(s): {','.join(region_parsed)}. Proceed? [y/N] ") or 'N'
            if choice.upper() in ['Y', 'N']:
                break
        if choice.upper() == 'Y':
            for region in region_parsed:
                args.region = region
                fp = FireProx(args, help_text)
                print(f'Retrieving API\'s from {region}...')
                current_apis = fp.list_api(deleting=True)
                if len(current_apis) == 0:
                    print(f'No API found')
                else:
                    for api in current_apis:
                        result = fp.delete_api(api_id=api['id'])
                        success = 'Success!' if result else 'Failed!'
                        print(f'Deleting {api["id"]} => {success}')


    elif args.command == 'update':
        print(f'Updating {fp.api_id} => {fp.url}...')
        result = fp.update_api(fp.api_id, fp.url)
        success = 'Success!' if result else 'Failed!'
        print(f'API Update Complete: {success}')


    else:
        print(f'[ERROR] Unsupported command: {args.command}\n')
        print(help_text)
        sys.exit(1)


if __name__ == '__main__':
    main()
