from flask import g, make_response

from flask_restful import reqparse

from connector.config import Config
from connector.fbclient.user import User as FbUser
from connector.fbclient.client import Client
from connector.resources.tenant import get_name_for_tenant

from . import ConnectorResource, OA, parameter_validator

config = Config()


def get_limit(user_type):
    return config.gold_user_limit if user_type == config.gold_users_resource \
        else config.default_user_limit


user_types = {
    config.users_resource: 'default',
    config.gold_users_resource: 'gold'
}


class UserList(ConnectorResource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('aps', dest='aps_type', type=parameter_validator('type'),
                            required=True,
                            help='Missing aps.type in request')
        parser.add_argument('tenant', dest='tenant_id',
                            type=parameter_validator('aps', 'id'),
                            required=True,
                            help='Missing tenant in request')
        parser.add_argument('user', dest='user_id',
                            type=parameter_validator('aps', 'id'),
                            required=True,
                            help='Missing aps.id in request')
        parser.add_argument('resource', dest='user_type', type=str, required=False)
        args = parser.parse_args()

        company_name = g.company_name = get_name_for_tenant(args.tenant_id)

        client = Client(g.reseller, name=company_name)

        # There should not be failures if diskspace resource is removed but users are still enabled.
        # Set 0 limit for clients and all users in this scenario.
        client.refresh()
        limit = 0 if client.storage['limit'] == 0 else get_limit(args.user_type)

        oa_user = OA.get_resource(args.user_id)
        user = FbUser(client, email=oa_user['email'], admin=oa_user['isAccountAdmin'],
                      storage={'limit': limit},
                      profile_type=user_types.get(args.user_type, 'default'))
        user.create()

        return {'userId': user.email}, 201


class User(ConnectorResource):
    def delete(self, user_id):
        user = make_fallball_user(user_id)
        g.company_name = user.client.name
        user.delete()

        return {}, 204

    def put(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('resource', dest='user_type', type=str, required=False)
        args = parser.parse_args()
        user = make_fallball_user(user_id)
        user.refresh()
        client = user.client
        client.refresh()
        g.company_name = client.name
        user.storage['limit'] = 0 if client.storage['limit'] == 0 else get_limit(args.user_type)
        if args.user_type in user_types:
            user.profile_type = user_types.get(args.user_type)
        user.update()
        return {}, 200


class UserLogin(ConnectorResource):
    def get(self, user_id):
        user = make_fallball_user(user_id)
        g.company_name = user.client.name

        response = make_response(user.login_link())
        response.headers.add('Content-Type', 'text/plain')
        return response


def make_fallball_user(oa_user_service_id):
    oa_user_service = OA.get_resource(oa_user_service_id)
    oa_tenant_id = oa_user_service['tenant']['aps']['id']
    client = Client(reseller=g.reseller, name=get_name_for_tenant(oa_tenant_id))
    user = FbUser(client=client, email=oa_user_service['userId'])

    return user
