from flask import g, make_response, request
from flask_restful import Resource, reqparse, abort

from connector.config import Config
from connector.fbclient.user import User as FbUser
from connector.fbclient.client import Client
from . import parameter_validator, urlify, Memoize, OA, OACommunicationException

config = Config()


@Memoize
def get_name_for_tenant(tenant_id):
    tenant_resource = OA.get_resource(tenant_id)
    if 'tenantId' not in tenant_resource:
        raise KeyError("tenantId property is missing in OA resource {}".format(tenant_id))
    return tenant_resource['tenantId']


class TenantList(Resource):
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
        return {'tenantId': client.name}, 201


class Tenant(Resource):
    def get(self, tenant_id):
        company_name = g.company_name = get_name_for_tenant(tenant_id)
        client = Client(g.reseller, name=company_name)
        client.refresh()
        return {
            config.users_resource: {
                'usage': client.users_amount
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


class TenantDisable(Resource):
    def put(self, tenant_id):
        # Not supported by the service yet
        return {}


class TenantEnable(Resource):
    def put(self, tenant_id):
        # Not supported by the service yet
        return {}


class TenantAdminLogin(Resource):
    def get(self, tenant_id):
        company_name = g.company_name = get_name_for_tenant(tenant_id)
        user_id = request.headers.get('aps-identity-id')
        if not user_id:
            abort(400)
        try:
            email = OA.get_resource(user_id)['email']
            client = Client(reseller=g.reseller, name=company_name)
            user = FbUser(client=client, email=email)
            login_link = user.login_link()
        except OACommunicationException:
            # Requesting login link for non-existing user to get link to login form from service
            fake_user = FbUser(client=Client(g.reseller, 'fake_client'),
                               email='does-not-exist@non-existing.local')
            login_link = fake_user.login_link()
        response = make_response(login_link)
        response.headers.add('Content-Type', 'text/plain')
        return response


class TenantUserCreated(Resource):
    def post(self, tenant_id):
        return {}


class TenantUserRemoved(Resource):
    def delete(self, tenant_id, user_id):
        return {}
