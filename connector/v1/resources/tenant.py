from flask import g, make_response, request

from flask_restful import reqparse

from connector.config import Config
from connector.fbclient.user import User as FbUser
from connector.fbclient.client import Client
from connector.utils import escape_domain_name

from . import (ConnectorResource, Memoize, OA, OACommunicationException,
               parameter_validator, urlify)

config = Config()


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


class TenantList(ConnectorResource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('aps', dest='aps_id', type=parameter_validator('id'),
                            required=True,
                            help='Missing aps.id in request')
        parser.add_argument(config.diskspace_resource, dest='storage_limit',
                            type=parameter_validator('limit'), required=False)
        parser.add_argument(config.users_resource, dest='users_limit',
                            type=parameter_validator('limit'), required=False)
        parser.add_argument(config.gold_users_resource, dest='gold_users_limit',
                            type=parameter_validator('limit'), required=False)
        parser.add_argument('oaSubscription', dest='sub_id', type=parameter_validator('aps', 'id'),
                            required=True,
                            help='Missing link to subscription in request')
        parser.add_argument('oaAccount', dest='acc_id', type=parameter_validator('aps', 'id'),
                            required=True,
                            help='Missing link to account in request')
        args = parser.parse_args()

        user_integration_enabled = bool(args.users_limit) or bool(args.gold_users_limit)

        company_name = OA.get_resource(args.acc_id)['companyName']
        company_name = urlify(company_name)
        sub_id = OA.get_resource(args.sub_id)['subscriptionId']
        company_name = '{}-sub{}'.format(company_name if company_name else 'Unnamed', sub_id)
        g.company_name = company_name
        storage_limit = args.storage_limit if args.storage_limit else 0

        client = Client(g.reseller, name=company_name, is_integrated=user_integration_enabled,
                        storage={'limit': storage_limit})
        client.create()

        if not user_integration_enabled:
            user = make_default_fallball_admin(client)
            user.create()

        OA.subscribe_on(args.aps_id, 'http://aps-standard.org/core/events/linked',
                        relation='users',
                        source_type='http://aps.odin.com/app/tn-fallball/tenant/1.2',
                        handler='onUsersChange')
        OA.subscribe_on(args.aps_id, 'http://aps-standard.org/core/events/unlinked',
                        relation='users',
                        source_type='http://aps.odin.com/app/tn-fallball/tenant/1.2',
                        handler='onUsersChange')

        return {'tenantId': client.name}, 201


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
            print "TFACTOR - storage limit"
            client = Client(g.reseller, name=company_name,
                            storage={'limit': args.storage_limit})
            print "TFACTOR - storage limit 2"
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
        tenant = OA.get_resource(tenant_id)
        OA.send_notification('Fallball was assigned for or removed from some users',
                             accountId=tenant['account']['aps']['id'])

        sync_tenant_usage_with_client(tenant_id, client)
        return {}
