import uuid

import pkg_resources

from flask import g

from flask_restful import reqparse

from connector.fbclient.reseller import Reseller

from . import ConnectorResource, Memoize, parameter_validator

env = pkg_resources.Environment()
res = env._distmap.get('fallball-connector', [None])[0]
version = res.version if res else ''


@Memoize
def get_reseller_name(reseller_id):
    res = [r for r in Reseller.all() if r.rid == reseller_id]
    return None if not res else res[0].name


class HealthCheck(ConnectorResource):
    def get(self):
        return {'status': 'ok',
                'version': version}


class ApplicationList(ConnectorResource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('aps', dest='aps_type', type=parameter_validator('type'),
                            required=True, help='No APS type specified')
        parser.add_argument('aps', dest='aps_id', type=parameter_validator('id'),
                            required=True, help='No APS id specified')
        args = parser.parse_args()
        g.reseller.create()
        return {'aps': {'type': args.aps_type, 'id': args.aps_id}, 'appId': str(uuid.uuid4())}, 201


class Application(ConnectorResource):
    def delete(self, app_id):
        g.reseller.delete()
        return {}, 204


class ApplicationUpgrade(ConnectorResource):
    def post(self, app_id):
        return {}


class ApplicationTenantNew(ConnectorResource):
    def post(self, app_id, tenant_id=None):
        return {}


class ApplicationTenantDelete(ConnectorResource):
    def delete(self, app_id, tenant_id=None):
        return {}
