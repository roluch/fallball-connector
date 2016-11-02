import json

from flask_testing import TestCase

from connector.app import app
from connector.config import Config
from tests.utils import bypass_auth

config = Config()


class TestApp(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        self.client = app.test_client()
        self.new_app = json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123'}})
        self.headers = {'Content-type': 'application/json',
                        'aps-instance-id': '123-123-123',
                        'aps-controller-uri': 'https://aps.com'}

        return app

    def test_healthcheck(self):
        res = self.client.get('/')
        assert 'status' in res.json.keys()
        self.assert200(res)

    def test_no_authorization(self):
        res = self.client.get('/app/12345')
        assert res.status_code == 401

    @bypass_auth
    def test_new_app(self):
        res = self.client.post('/app', headers=self.headers, data=self.new_app)
        assert res.status_code == 201

    @bypass_auth
    def test_delete_app(self):
        res = self.client.delete('/app/123-123-123', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    def test_delete_not_your_app(self):
        res = self.client.delete('/app/someone_elses_app', headers=self.headers)
        assert res.status_code == 403

    @bypass_auth
    def test_app_new_tenant(self):
        res = self.client.post('/app/123/tenants', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    def test_app_delete_tenant(self):
        res = self.client.delete('/app/123/tenants/123', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    def test_app_upgrade(self):
        res = self.client.post('/app/123/upgrade?version=100-500', headers=self.headers)
        assert res.status_code == 200
