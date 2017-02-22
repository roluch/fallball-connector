import json

from flask_testing import TestCase
from mock import patch

from connector.app import app
from connector.config import Config
from connector.fbclient.reseller import Reseller
from connector.v1.resources.user import make_fallball_user
from tests.utils import bypass_auth

config = Config()


class TestUser(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        self.client = app.test_client()
        self.new_tenant = {'aps': {'type': 'http://new.app', 'id': '123-123-123'}}
        self.oa_user = {'email': 'user@odin.com', 'isAccountAdmin': True}
        self.user_service = {'aps': {'type': 'http://new.app/user-service/1.0'},
                             'tenant': {'aps': {'id': '123'}},
                             'userId': 'user@example.com',
                             'user': {'aps': {'id': '123'}
                                      }
                             }
        self.headers = {'Content-type': 'application/json',
                        'aps-instance-id': '123-123-123',
                        'aps-controller-uri': 'https://localhost'}

        return app

    @bypass_auth
    def test_new_user(self):
        with patch('connector.v1.resources.user.OA') as fake_oa, \
                patch('connector.v1.resources.user.FbUser') as fake_user, \
                patch('connector.v1.resources.user.Client') as fake_client, \
                patch('connector.v1.resources.user.get_name_for_tenant') as fake_name:
            user_instance = fake_user.return_value
            client_instance = fake_client.return_value
            fake_name.return_value = 'fake_client'
            user_instance.email = 'user@odin.com'
            client_instance.storage = {'limit': 100}
            fake_oa.get_resources.return_value = [self.new_tenant]
            fake_oa.get_resource.return_value = self.oa_user
            res = self.client.post('/v1/user', headers=self.headers,
                                   data=json.dumps(self.user_service))
            user_instance.create.assert_called()
            assert res.status_code == 201

    @bypass_auth
    def test_delete_user(self):
        with patch('connector.v1.resources.user.OA') as fake_oa, \
                patch('connector.v1.resources.user.make_fallball_user') as fake_user:
            instance = fake_user.return_value
            instance.client.name = 'fake_client'
            fake_user = self.user_service
            fake_user['userId'] = 'user@localhost'
            fake_oa.get_resource.return_value = fake_user
            fake_oa.get_resources.return_value = [self.new_tenant]
            res = self.client.delete('/v1/user/123', headers=self.headers)
            instance.delete.assert_called()
            assert res.status_code == 204

    @bypass_auth
    def test_update_user(self):
        with patch('connector.v1.resources.user.make_fallball_user') as fake_user:
            instance = fake_user.return_value
            instance.client.name = 'fake_client'
            res = self.client.put('/v1/user/123', headers=self.headers, data='{}')
            assert res.status_code == 200

    @bypass_auth
    def test_user_login(self):
        with patch('connector.v1.resources.user.make_fallball_user') as fake_user:
            instance = fake_user.return_value
            instance.client.name = 'fake_client'
            instance.login_link.return_value = 'login_link'
            res = self.client.get('/v1/user/123/login', headers=self.headers)
            assert b'login_link' in res.data

    def test_make_fallball_user(self):
        with patch('connector.v1.resources.user.OA') as fake_oa, \
                patch('connector.v1.resources.user.g') as fake_g, \
                patch('connector.v1.resources.user.get_name_for_tenant') as fake_name:
            fake_oa.get_resource.return_value = self.user_service
            fake_g.reseller = Reseller('fake_reseller')
            fake_name.return_value = 'fake_client'
            user = make_fallball_user('123-123-123')
            assert user.client.name == 'fake_client'
            assert user.client.reseller.name == 'fake_reseller'
            assert user.email == 'user@example.com'
