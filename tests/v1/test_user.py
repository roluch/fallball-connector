import json

from flask_testing import TestCase
from mock import patch

from connector.app import app
from connector.config import Config
from connector.fbclient.reseller import Reseller
from connector.v1.resources.user import make_fallball_user
from tests.v1.utils import bypass_auth

config = Config()


class TestUser(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        self.client = app.test_client()
        self.new_tenant = {'aps': {'type': 'http://new.app', 'id': '123-123-123'}}
        self.oa_user = {'email': 'user@odin.com', 'isAccountAdmin': True,
                        'displayName': 'User Name', 'aps': {'id': '123'}}
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
    @patch('connector.v1.resources.user.OA')
    @patch('connector.v1.resources.user.FbUser')
    @patch('connector.v1.resources.user.Client')
    @patch('connector.v1.resources.user.get_name_for_tenant')
    def test_new_user(self, get_name_for_tenant_mock, FbClient_mock, FbUser_mock, OA_mock):
        fb_user_mock = FbUser_mock.return_value
        client_instance = FbClient_mock.return_value
        get_name_for_tenant_mock.return_value = 'fake_client'
        fb_user_mock.email = 'user@odin.com'
        client_instance.storage = {'limit': 100}
        OA_mock.get_resources.return_value = [self.new_tenant]
        OA_mock.get_resource.return_value = self.oa_user
        res = self.client.post('/v1/user', headers=self.headers,
                               data=json.dumps(self.user_service))
        fb_user_mock.create.assert_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.user.OA')
    @patch('connector.v1.resources.user.make_fallball_user')
    def test_delete_user(self, make_fallball_user_mock, OA_mock):
        fb_user_mock = make_fallball_user_mock.return_value
        fb_user_mock.client.name = 'fake_client'
        make_fallball_user_mock = self.user_service
        make_fallball_user_mock['userId'] = 'user@localhost'
        OA_mock.get_resource.return_value = make_fallball_user_mock
        OA_mock.get_resources.side_effect = [[self.oa_user], [self.new_tenant]]
        res = self.client.delete('/v1/user/123', headers=self.headers)
        fb_user_mock.delete.assert_called()
        assert res.status_code == 204

    @bypass_auth
    @patch('connector.v1.resources.user.OA')
    @patch('connector.v1.resources.user.make_fallball_user')
    def test_update_user(self, make_fallball_user_mock, OA_mock):
        fb_user_mock = make_fallball_user_mock.return_value
        fb_user_mock.client.name = 'fake_client'
        OA_mock.get_resources.return_value = [self.oa_user]
        fb_user_mock.client.users_by_type = {
            'default': 1,
            'gold': 2
        }
        fb_user_mock.client.storage = {
            'usage': 1,
            'limit': 1
        }
        config.gold_users_resource = ''
        res = self.client.put('/v1/user/123', headers=self.headers, data='{}')
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.user.OA')
    @patch('connector.v1.resources.user.make_fallball_user')
    def test_update_user_with_profiles(self, make_fallball_user_mock, OA_mock, OA_tenant_mock):
        fb_user_mock = make_fallball_user_mock.return_value
        fb_user_mock.client.name = 'fake_client'
        config.gold_users_resource = 'GOLD_USERS'
        user_payload = json.dumps({
            'resource': config.gold_users_resource
        })
        fb_user_mock.client.users_by_type = {
            'default': 1,
            'gold': 2
        }
        fb_user_mock.client.storage = {
            'usage': 1,
            'limit': 1
        }
        OA_mock.get_resources.return_value = [self.oa_user]
        res = self.client.put('/v1/user/123', headers=self.headers, data=user_payload)
        OA_tenant_mock.send_request.assert_called()
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.user.make_fallball_user')
    def test_user_login(self, make_fallball_user_mock):
        fb_user_mock = make_fallball_user_mock.return_value
        fb_user_mock.client.name = 'fake_client'
        fb_user_mock.login_link.return_value = 'login_link'
        res = self.client.get('/v1/user/123/login', headers=self.headers)
        assert b'login_link' in res.data

    @patch('connector.v1.resources.user.OA')
    @patch('connector.v1.resources.user.g')
    @patch('connector.v1.resources.user.get_name_for_tenant')
    def test_make_fallball_user(self, get_name_for_tenant_mock, flask_g_mock, OA_mock):
        OA_mock.get_resource.return_value = self.user_service
        flask_g_mock.reseller = Reseller('fake_reseller')
        get_name_for_tenant_mock.return_value = 'fake_client'
        user = make_fallball_user('123-123-123')
        assert user.client.name == 'fake_client'
        assert user.client.reseller.name == 'fake_reseller'
        assert user.email == 'user@example.com'
