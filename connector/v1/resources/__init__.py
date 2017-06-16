from collections import namedtuple
import re
import json

import requests
from requests import Request, Session

try:
    from functools import reduce
except ImportError:
    pass

try:
    from urllib.parse import urljoin, quote as urlquote
except ImportError:
    from urlparse import urljoin
    from urllib import quote as urlquote

from flask import g, request

from flask_restful import Resource

from slumber.exceptions import HttpClientError, HttpServerError

from connector.utils import log_outgoing_request, log_outgoing_response

ErrorResponse = namedtuple("ErrorResponse", "status_code text")


class Memoize(object):
    def __init__(self, function):
        self.function = function
        self.memoized = {}

    def __call__(self, *args):
        if args not in self.memoized:
            self.memoized[args] = self.function(*args)
        return self.memoized[args]


def parameter_validator(*args):
    def extract_params(where, *args):
        def extract_one(where, what):
            if what not in where:
                raise ValueError("Missing {} in request".format(what))
            return where[what]

        return reduce(extract_one, args, where)

    def validate(where):
        return extract_params(where, *args)

    return validate


def urlify(data):
    return re.sub(r'\s+', '-',
                  re.sub(r'[^\w\s]', '', data))


def make_error(e):
    return {'message': e.response.text.strip('"')}, e.response.status_code


class ConnectorResource(Resource):
    def dispatch_request(self, *args, **kwargs):
        try:
            return super(ConnectorResource, self).dispatch_request(*args, **kwargs)
        except (HttpClientError, HttpServerError) as e:
            return make_error(e)


class OACommunicationException(Exception):
    def __init__(self, resp):
        msg = "Request to OA failed."
        if resp.status_code:
            msg += " OA responded with code {}".format(resp.status_code)
        msg += "\nError message: {}".format(resp.text)
        super(OACommunicationException, self).__init__(msg)


class OA(object):
    request_timeout = 50

    @staticmethod
    @Memoize
    def get_notification_manager():
        rql_request = 'aps/2/resources?implementing({})'.format(
            urlquote('http://www.parallels.com/pa/pa-core-services/notification-manager/1'))
        response = OA.send_request('get', rql_request, transaction=False)
        return response[0]['aps']['id']

    @staticmethod
    def send_notification(message, details=None, message_keys=None, account_id=None,
                          status='ready', user_id=None, link=None):
        notification = {
            'status': status,
            'message': {
                'message': message
            }
        }
        if account_id is not None:
            notification['accountId'] = account_id
        if user_id is not None:
            notification['userId'] = user_id
        if message_keys is not None:
            notification['message']['keys'] = message_keys
        if details is not None:
            notification['details'] = {
                'message': details
            }
            if message_keys is not None:
                notification['details']['keys'] = message_keys
        if link is not None:
            notification['link'] = link
        initiator_id = request.headers.get('aps-identity-id')
        if initiator_id is not None:
            notification['initiatorId'] = initiator_id

        rql_request = 'aps/2/resources/{}/notifications'.format(OA.get_notification_manager())
        return OA.send_request('post', rql_request, notification, transaction=False)

    @staticmethod
    def subscribe_on(resource_id='', event_type='', handler='', relation='',
                     source_type=''):
        subscription = {
            'event': event_type,
            'source': {
                'type': source_type
            },
            'relation': relation,
            'handler': handler
        }
        rql_request = 'aps/2/resources/{}/aps/subscriptions'.format(resource_id)
        return OA.send_request('post', rql_request, subscription)

    @staticmethod
    def get_resource(resource_id, transaction=True, retry_num=10):
        rql_request = 'aps/2/resources/{}'.format(resource_id)
        return OA.send_request('get', rql_request, transaction=transaction, retry_num=retry_num)

    @staticmethod
    def put_resource(representation, transaction=True, impersonate_as=None, retry_num=10):
        rql_request = 'aps/2/resources'
        return OA.send_request('put', rql_request, body=representation,
                               transaction=transaction,
                               impersonate_as=impersonate_as,
                               retry_num=retry_num)

    @staticmethod
    def get_resources(rql_request, transaction=True, retry_num=10):
        return OA.send_request('get', rql_request, transaction=transaction, retry_num=retry_num)

    @staticmethod
    def send_request(method, path, body=None, transaction=True, impersonate_as=None, retry_num=10):
        oa_uri = request.headers.get('aps-controller-uri')
        url = urljoin(oa_uri, path)

        headers = {'Content-Type': 'application/json'}
        if impersonate_as:
            headers['aps-resource-id'] = impersonate_as
        if transaction and request.headers.get('aps-transaction-id'):
            headers['aps-transaction-id'] = request.headers.get('aps-transaction-id')

        data = None if body is None else json.dumps(body)

        retry_num = retry_num if retry_num > 0 else 1

        with Session() as s:
            prepared = Request(
                method=method,
                url=url,
                data=data,
                headers=headers,
                auth=g.auth
            ).prepare()

            while retry_num > 0:
                retry_num -= 1
                try:
                    g.log['out'].append(dict(request=None, response=None))
                    g.log['out'][-1]['request'] = log_outgoing_request(prepared)
                    resp = s.send(prepared, timeout=OA.request_timeout, verify=False)
                    g.log['out'][-1]['response'] = log_outgoing_response(resp)
                except requests.exceptions.Timeout:
                    err = ErrorResponse(None, 'Request to OA timed out. '
                                              'Timeout: {}'.format(OA.request_timeout))
                    raise OACommunicationException(err)
                except Exception as e:
                    err = ErrorResponse(None, str(e))
                    raise OACommunicationException(err)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code != 400:
                    raise OACommunicationException(resp)

            raise OACommunicationException(resp)

    @staticmethod
    @Memoize
    def get_application_schema():
        return OA.send_request('get', 'aps/2/application', transaction=False)

    @staticmethod
    def is_application_support_users():
        return True if OA.get_application_schema().get('user') else False

    @staticmethod
    @Memoize
    def get_user_schema():
        user_schema = {}
        user_schema_uri = OA.get_application_schema().get('user', {}).get('schema')
        if user_schema_uri:
            user_schema = OA.send_request('get', user_schema_uri, transaction=False)
        return user_schema

    @staticmethod
    def get_user_resources():
        return OA.get_user_schema().get('properties', {}).get('resource', {}).get('enum', [])
