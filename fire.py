#!/usr/bin/env python3
from multiprocessing import Pool
from pathlib import Path
import shutil
import tldextract
import boto3
import os
import sys
import datetime
import tzlocal
import argparse
import json
import configparser
from typing import Tuple, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FireProx")



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
        self.urls = arguments.urls
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
            if config_profile_section not in config:
                logger.info(f' Please create a section for {self.profile_name} in your ~/.aws/config file')
                return False
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
        logger.infoA(self.help)
        sys.exit(error)

    def get_template(self, url):
        """Get the swagger template for a given url"""
        logger.info(f'Getting template for {url}')
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
        template = template.replace('{{url}}', f'https://{url}')

        template = template.replace('{{title}}', title)
        template = template.replace('{{version_date}}', version_date)

        return str.encode(template)

    def create_api(self, urls):
        """Create API Gateway for a given url"""
        logger.info(f'Creating API Gateway for {urls}')
        if not urls or not isinstance(urls, list):
            self.error('Please provide a list of valid URL end-points')

        api_gateways = {}

        if os.path.exists('endpoints.json'):
            with open('endpoints.json', 'r') as infile:
                api_gateways = json.load(infile)

        for url in urls:
            if url not in api_gateways:
                print(f'Creating => {url}...')

                template = self.get_template(url)
                response = self.client.import_rest_api(
                    parameters={
                        'endpointConfigurationTypes': 'REGIONAL'
                    },
                    body=template
                )
                resource_id, proxy_url = self.create_deployment(response['id'])
                api_gateway_info = {
                    'api_id': response['id'],
                    'name': response['name'],
                    'created_dt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'version': response['version'],
                    'url': url,
                    'resource_id': resource_id,
                    'proxy_url': proxy_url
                }
                self.store_api(api_gateways, **api_gateway_info)
                api_gateways[url] = api_gateway_info

        with open('endpoints.json', 'w') as outfile:
            json.dump(api_gateways, outfile)


    def update_api(self, api_id=None, url=None):
        if not url:
            # If URL is not provided, prompt user for URL
            url = input("Enter the URL to update: ")

    # Ensure the URL includes the 'https://' or 'http://' scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        if url[-1] == '/':
            url = url[:-1]

        if not api_id:
            # If API ID is not provided, check if URL exists in endpoints.json
            api_gateways = {}
            if os.path.exists('endpoints.json'):
                with open('endpoints.json', 'r') as infile:
                    api_gateways = json.load(infile)
            
            if url in api_gateways:
                api_id = api_gateways[url]['api_id']
            else:
                # URL not found in endpoints.json, list fireprox_ APIs and ask for API ID
                logger.info('URL not found in endpoints.json')
                logger.info('Retrieving API Gateway IDs from the current AWS account:')
                response = self.client.get_rest_apis()
                for item in response['items']:
                    if item['name'].startswith('fireprox_'):
                        logger.info(f"API ID: {item['id']}, API Name: {item['name']}")
                api_id = input("Enter the API ID to update: ")

        if not api_id:
            self.error('No valid API ID provided')

        resource_id = self.get_resource(api_id)
        if resource_id:
            logger.info(f'Found resource {resource_id} for {api_id}!')
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

    def delete_api(self, urls):
        if not urls or not isinstance(urls, list):
            self.error('Please provide a list of valid URLs')

        # Load the existing API Gateways from the 'endpoints.json' file
        api_gateways = {}
        try:
            with open('endpoints.json', 'r') as infile:
                api_gateways = json.load(infile)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # List to store API IDs to be deleted
        api_ids_to_delete = []

        for url in urls:
            # Add 'https://' to the URL if it doesn't have it
            if not url.startswith('https://'):
                url = 'https://' + url

            # Check if the URL exists in the 'endpoints.json' file
            if url in api_gateways:
                api_id = api_gateways[url]['api_id']
                api_ids_to_delete.append(api_id)
            else:
                # URL not found in 'endpoints.json', need to retrieve from AWS account
                logger.info(f' URL not found in endpoints.json: {url}')
                logger.info(' Available API Endpoints:')
                response = self.client.get_rest_apis()
                for item in response['items']:
                    if item['name'].startswith('fireprox_'):
                        logger.info(f" API ID: {item['id']}, API Name: {item['name']}")
                user_api_id = input('Enter the API ID you want to delete (or type "skip" to skip): ')
                if user_api_id.lower() != 'skip':
                    api_ids_to_delete.append(user_api_id)

        # Delete the API Gateways using the collected API IDs
        success_count = 0
        total_count = len(api_ids_to_delete)
        for api_id in api_ids_to_delete:
            try:
                response = self.client.delete_rest_api(restApiId=api_id)
                success_count += 1
                # Remove the deleted API from 'endpoints.json' file
                url_to_remove = next((url for url, info in api_gateways.items() if info['api_id'] == api_id), None)
                if url_to_remove:
                    del api_gateways[url_to_remove]
            except Exception as e:
                logger.info(f" Failed to delete API ID: {api_id}. Error: {e}")

        # Update the 'endpoints.json' file
        with open('endpoints.json', 'w') as outfile:
            json.dump(api_gateways, outfile)

        if success_count == total_count:
            return True
        else:
            return False

    def list_api(self, deleted_api_id=None):
        response = self.client.get_rest_apis()
        for item in response['items']:
            try:
                created_dt = item['createdDate'].strftime('%Y-%m-%d %H:%M:%S')
                api_id = item['id']
                name = item['name']
                # Only display APIs with names starting with 'fireprox_'
                if name.startswith('fireprox_'):
                    proxy_url = self.get_integration(api_id).replace('{proxy}', '')
                    url = f'https://{api_id}.execute-api.{self.region}.amazonaws.com/fireprox/'
                    if api_id != deleted_api_id:
                        logger.info(f'[{created_dt}] ({api_id}) {name}: {url} => {proxy_url}')
            except Exception as e:
                logger.error(f'Error processing API: {e}')

        return response['items']

    def store_api(self, api_gateways, *, api_id, name, created_dt, version, url, resource_id, proxy_url):
        logger.info(
            f'[{created_dt}] ({api_id}) {name} => {proxy_url} ({url})'
        )
        api_gateways[url] = {
            'api_id': api_id,
            'name': name,
            'created_dt': created_dt,
            'version': version,
            'url': url,
            'resource_id': resource_id,
            'proxy_url': proxy_url
        }
        with open('endpoints.json', 'w') as outfile:
            json.dump(api_gateways, outfile)

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
                        help='Commands: list, create, delete, update', type=str, default=None)
    parser.add_argument('--api_id',
                        help='API ID', type=str, required=False)
    parser.add_argument('--url',
                        help='URL to update API Gateway for', type=str, required=False)
    parser.add_argument('--urls', 
                        nargs='+', type=str, help='List of URL end-points to create API Gateways for', default=[], required=False)

    return parser.parse_args(), parser.format_help()


def main():
    """Run the main program

    :return:
    """
    args, help_text = parse_arguments()
    fp = FireProx(args, help_text)
    if args.command == 'list':
        logger.info(f' Listing API\'s...')
        result = fp.list_api()

    elif args.command == 'create':
        urls = fp.urls
        result = fp.create_api(urls)

    elif args.command == 'delete':
        result = fp.delete_api(fp.urls)
        success = 'Success!' if result else 'Failed!'
        logger.info(f' Deleting {fp.api_id} => {success}')

    elif args.command == 'update':
        logger.info(f' Updating {fp.api_id} => {fp.url}...')
        result = fp.update_api(fp.api_id, fp.url)
        success = 'Success!' if result else 'Failed!'
        logger.info(f' API Update Complete: {success}')

    else:
        logger.info(f' [ERROR] Unsupported command: {args.command}\n')
        logger.info(help_text)
        sys.exit(1)


if __name__ == '__main__':
    main()
