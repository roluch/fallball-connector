# -*- coding: utf-8 -*-

from collections import namedtuple

from flask import g, make_response
from flask_restful import reqparse, request
from slumber.exceptions import HttpClientError

from connector.config import Config
from connector.fbclient.user import User as FbUser
from connector.fbclient.client import Client
from connector.utils import escape_domain_name

from . import (ConnectorResource, Memoize, OA, OACommunicationException,
               parameter_validator, urlify)

config = Config()

AnalysisResult = namedtuple('AnalysisResult', 'recoverable data')
ProvisioningResult = namedtuple('ProvisioningResult', 'body status_code headers')


@Memoize
def get_name_for_tenant(tenant_id):
    tenant_resource = OA.get_resource(tenant_id)
    if 'tenantId' not in tenant_resource:
        raise KeyError("tenantId property is missing in OA resource {}".format(tenant_id))
    return tenant_resource['tenantId']


def sync_tenant_usage_with_client(tenant_id, client):
    client.refresh()
    tenant = {
        config.users_resource: {
            'usage': client.users_by_type['default']
        },
        config.diskspace_resource: {
            'usage': client.storage['usage']
        },
        config.devices_resource: {
            'usage': 0
        }
    }
    OA.send_request('put',
                    'aps/2/application/tenant/{}'.format(tenant_id),
                    tenant)


def make_default_fallball_admin(client):
    email = 'admin@{client_name}.{reseller_name}.fallball.io'.format(
        client_name=escape_domain_name(client.name),
        reseller_name=escape_domain_name(client.reseller.name))

    user = FbUser(client=client, email=email, admin=True, storage={'limit': 0})
    return user


def get_tenant_args():
    parser = reqparse.RequestParser()

    parser.add_argument('aps', dest='aps_id', type=parameter_validator('id'), required=True,
                        help='Missing aps.id in request')
    parser.add_argument('aps', dest='sub_id', type=parameter_validator('subscription'),
                        required=True, help='Missing aps.subscription in request')
    parser.add_argument('aps', dest='aps_type', type=parameter_validator('type'), required=True,
                        help='Missing aps.type in request')
    parser.add_argument('aps', dest='aps_status', type=parameter_validator('status'))

    parser.add_argument('account', dest='acc_id', type=parameter_validator('aps', 'id'),
                        required=True, help='Missing link to account in request')

    parser.add_argument('accountinfo', dest='account_info', type=dict)
    parser.add_argument('status', type=str)
    parser.add_argument('statusData', dest='status_data', type=dict)

    parser.add_argument(config.diskspace_resource, dest='storage_limit',
                        type=parameter_validator('limit'))
    parser.add_argument(config.users_resource, dest='users_limit',
                        type=parameter_validator('limit'))
    parser.add_argument(config.gold_users_resource, dest='gold_users_limit',
                        type=parameter_validator('limit'))

    return parser.parse_args()


def analyze_service_error(data):
    if len(data) == 1 and 'email' in data:
        info = {'status': 'activationRequired',
                'statusData': {
                    'code': 'ActivationData',
                    'messages': [
                        {
                            'type': 'error',
                            'text': "Please provide additional information to complete "
                                    "provisioning of the FallBall service",
                            'textLocalized': {
                                'ru': u'Пожалуйста, предоставьте дополнительные данные '
                                      u'для завершения создания сервиса FallBall'
                            }
                        }

                    ],
                    'perPropertyData': [
                        {
                            'propertyName': 'accountinfo.techContact.email',
                            'message': {
                                'text': "Dots are not allowed in local parts of email addresses",
                                'textLocalized': {
                                    'ru': u"Часть адреса электронной почты до знака @ "
                                          u"не должна содержать точек"
                                }
                            }
                        }
                    ]
                }}
        return AnalysisResult(True, info)
    return AnalysisResult(False, {})


def report_error(message):
    return {'status': 'error',
            'statusData': {
                'code': 'ActivationData',
                'messages': [
                    {
                        'type': 'error',
                        'text': '{}'.format(message),
                    }

                ],
                'perPropertyData': []
            }}


def provision_fallball_client(args):
    user_integration_enabled = bool(args.users_limit) or bool(args.gold_users_limit)

    company_info = OA.get_resource(args.acc_id)
    company_name = urlify(company_info['companyName'])

    if args.account_info['techContact'].get('email'):
        admin_email = args.account_info['techContact']['email']
    else:
        admin_email = company_info['techContact']['email']

    info = {
        'accountinfo': {
            'techContact': {
                'email': admin_email
            }
        }
    }

    sub_id = OA.get_resource(args.sub_id)['subscriptionId']
    company_name = '{}-sub{}'.format(company_name if company_name else 'Unnamed', sub_id)
    g.company_name = company_name
    storage_limit = args.storage_limit if args.storage_limit else 0

    client = Client(g.reseller, name=company_name, is_integrated=user_integration_enabled,
                    storage={'limit': storage_limit}, email=admin_email)

    try:
        client.create()
    except HttpClientError as e:
        resp = e.response.json()
        result = analyze_service_error(resp)
        if result.recoverable:
            info.update(result.data)
            return ProvisioningResult(info, 202,
                                      {'Aps-Info': "Additional information required to complete "
                                                   "provisioning"})
        else:
            info = report_error(resp)
            return ProvisioningResult(info, 500, {})
    except Exception as e:
        info = report_error(str(e))
        return ProvisioningResult(info, 500, {})

    if not user_integration_enabled:
        user = make_default_fallball_admin(client)
        user.create()

    OA.subscribe_on(args.aps_id, 'http://aps-standard.org/core/events/linked',
                    relation='users',
                    source_type=args.aps_type,
                    handler='onUsersChange')
    OA.subscribe_on(args.aps_id, 'http://aps-standard.org/core/events/unlinked',
                    relation='users',
                    source_type=args.aps_type,
                    handler='onUsersChange')

    status = 'reprovisioned' if args.status else ''

    return ProvisioningResult({'tenantId': client.name,
                               'status': status,
                               'statusData': {
                                   'messages': [],
                                   'perPropertyData': []
                               }}, 201, None)


class TenantList(ConnectorResource):
    def post(self):
        args = get_tenant_args()
        phase = request.headers.get('Aps-Request-Phase', 'sync')

        if args.status == 'reprovisioned':
            return {}, 201
        elif phase == 'async' and args.status != 'error':
            return {}, 202, {'Aps-Info': "Additional information required to complete provisioning"}

        return provision_fallball_client(args)


class Tenant(ConnectorResource):
    def get(self, tenant_id):
        company_name = g.company_name = get_name_for_tenant(tenant_id)
        client = Client(g.reseller, name=company_name)
        client.refresh()
        return {
            config.users_resource: {
                'usage': client.users_by_type['default']
            },
            config.diskspace_resource: {
                'usage': client.storage['usage']
            },
            config.devices_resource: {
                'usage': 0
            }
        }

    def put(self, tenant_id):
        parser = reqparse.RequestParser()
        parser.add_argument(config.diskspace_resource, dest='storage_limit',
                            type=parameter_validator('limit'), required=False,
                            help='Missing {} limit in request'.format(config.diskspace_resource))
        args = parser.parse_args()
        company_name = g.company_name = get_name_for_tenant(tenant_id)
        if args.storage_limit:
            client = Client(g.reseller, name=company_name,
                            storage={'limit': args.storage_limit})
            client.update()
        return {}

    def delete(self, tenant_id):
        company_name = g.company_name = get_name_for_tenant(tenant_id)
        client = Client(g.reseller, name=company_name)
        client.delete()
        return None, 204


class TenantDisable(ConnectorResource):
    def put(self, tenant_id):
        # Not supported by the service yet
        return {}


class TenantEnable(ConnectorResource):
    def put(self, tenant_id):
        # Not supported by the service yet
        return {}


class TenantAdminLogin(ConnectorResource):
    def get(self, tenant_id):
        try:
            company_name = g.company_name = get_name_for_tenant(tenant_id)
            client = Client(g.reseller, name=company_name)
            user = make_default_fallball_admin(client)
            login_link = user.login_link()
        except OACommunicationException:
            # Requesting login link for non-existing user to get link to login form from service
            fake_user = FbUser(client=Client(g.reseller, 'fake_client'),
                               email='does-not-exist@non-existing.local')
            login_link = fake_user.login_link()
        response = make_response(login_link)
        response.headers.add('Content-Type', 'text/plain')
        return response


class TenantUserCreated(ConnectorResource):
    def post(self, tenant_id):
        return {}


class TenantUserRemoved(ConnectorResource):
    def delete(self, tenant_id, user_id):
        return {}


class TenantOnUsersChange(ConnectorResource):
    def post(self, tenant_id):
        request.get_json()
        client = Client(g.reseller, get_name_for_tenant(tenant_id))
        sync_tenant_usage_with_client(tenant_id, client)
        return {}


class TenantReprovision(ConnectorResource):
    def post(self, tenant_id):
        args = get_tenant_args()

        tenant = OA.get_resource(tenant_id)
        if tenant['aps']['status'] != 'aps:provisioning' or tenant['status'] == 'reprovisioned':
            return {'error': "Cannot provision already provisioned client"}, 400

        result = provision_fallball_client(args)

        path = '/aps/2/application/tenant/{}'.format(tenant_id)

        if result.status_code == 201:
            body = {
                'accountinfo': args.account_info,
                'status': 'reprovisioned',
                'statusData': {},
            }
            body.update(result.body)
        else:
            body = result.body

        OA.send_request('PUT', path, body)

        return {}, 200
