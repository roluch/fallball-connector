import pkg_resources

from flask import g
from flask_restful import Resource, abort, reqparse

from connector.fbclient.reseller import Reseller
from . import parameter_validator, Memoize

env = pkg_resources.Environment()
res = env._distmap.get('fallball-connector', [None])[0]
version = res.version if res else ''


@Memoize
def get_reseller_name(reseller_id):
    res = [r for r in Reseller.all() if r.rid == reseller_id]
    return None if not res else res[0].name


class HealthCheck(Resource):
    def get(self):
        return {'status': 'ok',
                'version': version}


class ApplicationList(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('aps', dest='aps_type', type=parameter_validator('type'),
                            required=True, help='No APS type specified')
        parser.add_argument('aps', dest='aps_id', type=parameter_validator('id'),
                            required=True, help='No APS id specified')
        args = parser.parse_args()
        g.reseller.create()
        return {'aps': {'type': args.aps_type, 'id': args.aps_id}}, 201


class Application(Resource):
    def delete(self, app_id):
        if g.reseller.reseller_name != app_id:
            abort(403)
        g.reseller.delete()


class ApplicationUpgrade(Resource):
    def post(self, app_id):
        return {}


class ApplicationTenantNew(Resource):
    def post(self, app_id, tenant_id=None):
        return {}


class ApplicationTenantDelete(Resource):
    def delete(self, app_id, tenant_id=None):
        return {}
