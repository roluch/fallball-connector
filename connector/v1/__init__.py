import sys
import logging
from collections import namedtuple

from flask import Blueprint, g, request
from flask_restful import Api, abort
from requests_oauthlib import OAuth1
from faker import Faker

from connector.config import Config
from connector.utils import log_request, log_response, guid
from connector.validator import check_oauth_signature, get_client_key
from connector.fbclient.reseller import Reseller

from connector.v1.resources import urlify
from connector.v1.resources.application import (Application, ApplicationList,
                                                ApplicationTenantDelete, ApplicationTenantNew,
                                                ApplicationUpgrade, HealthCheck,
                                                get_reseller_name)
from connector.v1.resources.tenant import (Tenant, TenantAdminLogin, TenantDisable, TenantEnable,
                                           TenantList, TenantUserCreated, TenantReprovision,
                                           TenantUserRemoved, TenantOnUsersChange)
from connector.v1.resources.user import User, UserList, UserLogin

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream = logging.StreamHandler(sys.stdout)
logger.addHandler(stream)

fake = Faker()
api_bp = Blueprint('v1', __name__)

ResellerInfo = namedtuple('ResellerInfo', ['id', 'name', 'is_new', 'auth'])


def allow_public_endpoints_only():
    public_endpoints = (HealthCheck.__name__.lower(),)
    if g.endpoint not in public_endpoints:
        abort(401)


def set_name_for_reseller(reseller_id):
    if not reseller_id:
        return None
    if g.endpoint == ApplicationList.__name__.lower():
        return urlify(fake.bs())
    return get_reseller_name(reseller_id)


def get_oauth():
    client_key = get_client_key(request)
    client_secret = Config().oauth_secret
    if not client_key or not client_secret:
        return None
    return OAuth1(client_key=client_key,
                  client_secret=client_secret)


def get_reseller_info():
    reseller_id = request.headers.get('Aps-Instance-Id')
    is_new = g.endpoint == ApplicationList.__name__.lower()
    reseller_name = set_name_for_reseller(reseller_id)
    oauth = get_oauth()
    return ResellerInfo(id=reseller_id, name=reseller_name, is_new=is_new, auth=oauth)


@api_bp.before_request
def before_request():
    g.request_id = guid()

    g.endpoint = request.endpoint
    if request.blueprint:
        g.endpoint = g.endpoint[len(request.blueprint):].lstrip('.')

    reseller_info = get_reseller_info()
    g.reseller_name = reseller_info.name
    g.company_name = 'N/A'

    log_request(request)

    if not reseller_info.name:
        allow_public_endpoints_only()
        return

    if not check_oauth_signature(request):
        abort(401)

    g.auth = reseller_info.auth

    g.reseller = Reseller(reseller_info.name, reseller_info.id, None)
    g.reseller.refresh()

    if not g.reseller.token and not reseller_info.is_new:
        abort(403)


@api_bp.after_request
def after_request(response):
    log_response(response)
    return response


resource_routes = {
    '/': HealthCheck,
    '/app': ApplicationList,
    '/app/<app_id>': Application,
    '/app/<app_id>/tenants': ApplicationTenantNew,
    '/app/<app_id>/tenants/<tenant_id>': ApplicationTenantDelete,
    '/app/<app_id>/upgrade': ApplicationUpgrade,

    '/tenant': TenantList,
    '/tenant/<tenant_id>': Tenant,
    '/tenant/<tenant_id>/disable': TenantDisable,
    '/tenant/<tenant_id>/enable': TenantEnable,
    '/tenant/<tenant_id>/adminlogin': TenantAdminLogin,
    '/tenant/<tenant_id>/users': TenantUserCreated,
    '/tenant/<tenant_id>/users/<user_id>': TenantUserRemoved,
    '/tenant/<tenant_id>/onUsersChange': TenantOnUsersChange,
    '/tenant/<tenant_id>/reprovision': TenantReprovision,

    '/user': UserList,
    '/user/<user_id>': User,
    '/user/<user_id>/userlogin': UserLogin,
}


class FallballApi(Api):
    def handle_error(self, e):
        code = getattr(e, 'code', 500)
        return self.make_response({'message': str(e),
                                   'error': type(e).__name__},
                                  code)


api = FallballApi(api_bp, catch_all_404s=True)

for route, resource in resource_routes.items():
    api.add_resource(resource, route, strict_slashes=False)
