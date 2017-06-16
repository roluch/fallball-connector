import json

from flask_testing import TestCase
from mock import MagicMock, patch, DEFAULT
from slumber.exceptions import HttpClientError, HttpServerError


from connector.app import app
from connector.config import Config
from connector.fbclient.reseller import Reseller
from connector.v1.resources import OACommunicationException
from connector.v1.resources.tenant import get_name_for_tenant
from tests.v1.utils import bypass_auth

from connector.v1.resources.tenant import config as config_from_tenant

config = Config()


class TestTenant(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        self.client = app.test_client()
        self.headers = {'Content-type': 'application/json',
                        'aps-instance-id': '123-123-123',
                        'aps-identity-id': '123-123-123',
                        'aps-controller-uri': 'https://localhost'}
        self.new_tenant = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:provisioning',
                                'subscription': '555'},
                        config.diskspace_resource: {'limit': 1000},
                        'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                        'account': {'aps': {'id': 555}}})
        self.new_tenant_no_email = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:provisioning',
                                'subscription': '555'},
                        config.diskspace_resource: {'limit': 1000},
                        'accountinfo': {'techContact': {}},
                        'account': {'aps': {'id': 555}}})
        self.fb_client_with_users = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:provisioning',
                                'subscription': '555'},
                        'USERS': {'limit': 10},
                        'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                        'account': {'aps': {'id': 555}}})
        self.diskless_tenant = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:provisioning',
                                'subscription': '555'},
                        'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                        'account': {'aps': {'id': 555}}})
        self.reprovisioning_tenant = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:provisioning',
                                'subscription': '555'},
                        'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                        'status': 'activationRequired',
                        'account': {'aps': {'id': 555}}})
        self.reprovisioned_tenant = \
            json.dumps({'aps': {'type': 'http://new.app', 'id': '123-123-123',
                                'status': 'aps:ready',
                                'subscription': '555'},
                        'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                        'status': 'reprovisioned',
                        'account': {'aps': {'id': 555}}})
        self.users_changed_notification = '{}'

        return app

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.make_default_fallball_admin')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant(self, FbClient_mock, make_admin_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.storage = {'usage': 1}
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        fb_admin_mock = make_admin_mock.return_value
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'}},
                                            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant)
        fb_client_mock.create.assert_called()
        make_admin_mock.assert_called()
        fb_admin_mock.update.assert_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_create_reprovisioned_tenant(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company'},
                                            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.reprovisioned_tenant)
        fb_client_mock.create.assert_not_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_create_client_reprovision_not_completed(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company'},
                                            {'subscriptionId': 555}]
        headers = self.headers.copy()
        headers.update({'Aps-Request-Phase': 'async'})
        res = self.client.post('/v1/tenant', headers=headers, data=self.reprovisioning_tenant)
        fb_client_mock.create.assert_not_called()
        assert res.status_code == 202

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant_no_email(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.storage = {'usage': 1}
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        OA_mock.get_resource.side_effect = [
            {'companyName': 'fake_company', 'techContact': {'email': 'tenant-tech@fallball.io'},
             'addressPostal': {'postalCode': '11111'}},
            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant_no_email)
        fb_client_mock.create.assert_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant_recoverable_error(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        response = MagicMock()

        response.json.return_value = {'postal_code': {
            'code': 'E1002',
            'message': "Postal code can't start with 999"}
        }

        fb_client_mock.create.side_effect = HttpClientError(response=response)
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'}},
                                            {'subscriptionId': 555}]

        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant)
        fb_client_mock.create.assert_called()

        assert res.json['status'] == 'activationRequired'
        assert res.status_code == 202

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant_recoverable_error_invalid_zip(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        response = MagicMock()

        response.json.return_value = {'postal_code': {
            'code': 'E1001',
            'message': "Postal code must be a 5-digit number"}
        }

        fb_client_mock.create.side_effect = HttpClientError(response=response)
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'}},
                                            {'subscriptionId': 555}]

        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant)
        fb_client_mock.create.assert_called()

        assert res.json['status'] == 'activationRequired'
        assert res.status_code == 202
        assert res.json['statusData']['perPropertyData'][0]['message']['text'] == \
            'The postal code must consist of five digits'

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant_unrecoverable_error(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        response = MagicMock()
        response.json.return_value = {'unknown_error': 'Something went wrong'}
        response.text = 'Something went wrong'
        response.status_code = 400
        fb_client_mock.create.side_effect = HttpClientError(response=response)
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'}},
                                            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant)
        fb_client_mock.create.assert_called()

        assert res.status_code == 500

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_tenant_unexpected_error(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        response = MagicMock()
        response.json.return_value = {'unknown_error': 'Something went wrong'}
        response.text = 'Something went wrong'
        response.status_code = 500
        fb_client_mock.create.side_effect = HttpServerError(response=response)
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'}},
                                            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.new_tenant)
        fb_client_mock.create.assert_called()

        assert res.status_code == 500

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_fb_client_users(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.storage = {'usage': 1}
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'},
                                             },
                                            {'subscriptionId': 555}]
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.fb_client_with_users)
        fb_client_mock.create.assert_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.Client')
    def test_new_fb_client_no_diskspace(self, FbClient_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.storage = {'usage': 1}
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        OA_mock.get_resource.side_effect = [{'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'}
                                             },
                                            {'subscriptionId': 555}]
        OA_mock.is_application_support_users.return_value = True
        res = self.client.post('/v1/tenant', headers=self.headers, data=self.diskless_tenant)
        fb_client_mock.create.assert_called()
        assert res.status_code == 201

    @bypass_auth
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_resource_usage(self, FbClient_mock, get_name_for_fb_client_mock, OA_mock):
        fb_client_mock = FbClient_mock.return_value
        get_name_for_fb_client_mock.return_value = 'fake_client'
        fb_client_mock.users_by_type = {
            'PLATINUM': 1,
            'BRONZE': 2
        }
        fb_client_mock.storage = {'usage': 1}
        OA_mock.get_user_resources.return_value = ['PLATINUM', 'BRONZE']

        res = self.client.get('/v1/tenant/123', headers=self.headers)
        data = res.json
        assert data[config.diskspace_resource]['usage'] == 1
        assert data['PLATINUM']['usage'] == 1
        assert data['BRONZE']['usage'] == 2
        assert res.status_code == 200

        fb_client_mock.users_by_type['BRONZE'] = 4
        res = self.client.get('/v1/tenant/123', headers=self.headers)
        data = res.json
        assert data['BRONZE']['usage'] == 4

    @bypass_auth
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_update_tenant(self, FbClient_mock, get_name_for_fb_client_mock):
        fb_client_mock = FbClient_mock.return_value
        get_name_for_fb_client_mock.return_value = 'fake_client'
        res = self.client.put('/v1/tenant/123', headers=self.headers,
                              data=self.new_tenant)
        fb_client_mock.update.assert_called()
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_update_fb_client_no_diskspace(self, FbClient_mock, get_name_for_fb_client_mock):
        fb_client_mock = FbClient_mock.return_value
        get_name_for_fb_client_mock.return_value = 'fake_client'
        res = self.client.put('/v1/tenant/123', headers=self.headers,
                              data=self.diskless_tenant)
        fb_client_mock.update.assert_not_called()
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_delete_tenant(self, FbClient_mock, get_name_for_fb_client_mock):
        fb_client_mock = FbClient_mock.return_value

        get_name_for_fb_client_mock.return_value = 'fake_client'
        res = self.client.delete('/v1/tenant/123', headers=self.headers)
        fb_client_mock.delete.assert_called()
        assert res.status_code == 204

    @bypass_auth
    def test_fb_client_disable(self):
        res = self.client.put('/v1/tenant/123/disable', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    def test_fb_client_enable(self):
        res = self.client.put('/v1/tenant/123/enable', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    def test_admin_login(self, get_name_for_fb_client_mock, flask_g_mock, OA_mock, FbUser_mock):
        get_name_for_fb_client_mock.return_value = 'fake_client'
        flask_g_mock.reseller = Reseller('fake_reseller')
        fb_user_mock = FbUser_mock.return_value
        fb_user_mock.login_link.return_value = 'login_link_with_token'
        res = self.client.get('/v1/tenant/123/adminlogin', headers=self.headers)
        assert res.status_code == 200
        assert b'token' in res.data

    @bypass_auth
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    def test_admin_login_no_user_in_oa(self, get_name_for_fb_client_mock,
                                       flask_g_mock, OA_mock, FbUser_mock):
        get_name_for_fb_client_mock.return_value = 'fake_client'
        flask_g_mock.reseller = Reseller('fake_reseller')
        fake_oa_response = MagicMock()
        fake_oa_response.status_code = 404
        fake_oa_response.text = 'Get user from OA failed'
        OA_mock.get_resource.side_effect = OACommunicationException(fake_oa_response)
        fb_user_mock = FbUser_mock.return_value
        fb_user_mock.login_link.return_value = 'login_link_for_manual_login'
        res = self.client.get('/v1/tenant/123/adminlogin', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    def test_admin_login_no_user_in_fallball(self, get_name_for_fb_client_mock,
                                             flask_g_mock, OA_mock, FbUser_mock):
        get_name_for_fb_client_mock.return_value = 'fake_client'
        flask_g_mock.reseller = Reseller('fake_reseller')
        fake_fallball_response = MagicMock()
        fake_fallball_response.status_code = 404
        fb_user_mock = FbUser_mock.return_value
        fb_user_mock.login_link.side_effect = [OACommunicationException(fake_fallball_response),
                                               DEFAULT]
        fb_user_mock.login_link.return_value = 'login_link_for_manual_login'
        res = self.client.get('/v1/tenant/123/adminlogin', headers=self.headers)
        assert res.status_code == 200

    def test_get_name_for_tenant(self):
        with patch('connector.v1.resources.tenant.OA') as fake_oa:
            fake_oa.get_resource.return_value = {'tenantId': 'fake_client'}
            assert get_name_for_tenant('123-123-123') == 'fake_client'

    @patch('connector.v1.resources.tenant.OA')
    def test_get_name_for_fb_client_fail(self, OA_mock):
        OA_mock.get_resource.return_value = {}
        self.assertRaises(KeyError, get_name_for_tenant, 'broken_tenant')

    @bypass_auth
    def test_fb_client_delete_user(self):
        res = self.client.delete('/v1/tenant/123/users/123', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    def test_fb_client_new_user(self):
        res = self.client.post('/v1/tenant/123/users', headers=self.headers)
        assert res.status_code == 200

    @bypass_auth
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_fb_client_on_users_change(self, FbClient_mock,
                                       get_name_for_fb_client_mock, flask_g_mock,
                                       OA_mock, FbUser_mock):
        fb_client_mock = FbClient_mock.return_value
        get_name_for_fb_client_mock.return_value = 'fake_client'
        flask_g_mock.reseller = Reseller('fake_reseller')
        fb_client_mock.users_by_type = {
            'BRILLIANT_USERS': 1
        }
        fb_client_mock.storage = {'usage': 1}
        tenant = {
            config.devices_resource: {
                'usage': 0
            },
            'BRILLIANT_USERS': {
                'usage': 1
            },
            config.diskspace_resource: {
                'usage': 1
            }
        }
        OA_mock.get_user_resources.return_value = ['BRILLIANT_USERS']
        self.client.post('/v1/tenant/123/onUsersChange',
                         headers=self.headers, data='{}')
        OA_mock.send_request.assert_called_with('put',
                                                'aps/2/application/tenant/123',
                                                tenant)

        fb_client_mock.users_by_type['SILVER_USERS'] = 2
        OA_mock.get_user_resources.return_value = ['BRILLIANT_USERS', 'SILVER_USERS']

        tenant['SILVER_USERS'] = {
          'usage': 2
        }

        self.client.post('/v1/tenant/123/onUsersChange',
                         headers=self.headers, data='{}')
        OA_mock.send_request.assert_called_with('put',
                                                'aps/2/application/tenant/123',
                                                tenant)

    @bypass_auth
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_tenant_reprovision(self, FbClient_mock,
                                get_name_for_fb_client_mock, flask_g_mock,
                                OA_mock, FbUser_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        fb_client_mock.storage = {'usage': 1}

        OA_mock.get_resource.side_effect = [json.loads(self.reprovisioning_tenant),
                                            {'companyName': 'fake_company',
                                             'techContact': {'email': 'new-tenant@fallball.io'},
                                             'addressPostal': {'postalCode': '11111'}},
                                            {'subscriptionId': 555}]

        resp = self.client.post('/v1/tenant/123/reprovision', headers=self.headers,
                                data=self.reprovisioning_tenant)

        tenant_body = {'status': 'reprovisioned', 'DISKSPACE': {'usage': 1},
                       'DEVICES': {'usage': 0},
                       'accountinfo': {'addressPostal': {'postalCode': '11111'}},
                       'statusData': {'messages': [], 'perPropertyData': []},
                       'tenantId': 'fake_company_name'}
        OA_mock.send_request.assert_called_with('PUT', '/aps/2/application/tenant/123', tenant_body)
        self.assertEqual(resp.status_code, 200)

    @bypass_auth
    @patch('connector.v1.resources.tenant.provision_fallball_client')
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_tenant_reprovision_unsuccessful(self, FbClient_mock,
                                             get_name_for_fb_client_mock, flask_g_mock,
                                             OA_mock, FbUser_mock, provision_fb_client_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        provision_result_mock = provision_fb_client_mock.return_value
        provision_result_mock.status_code = 202
        provision_result_mock.body = {'statusData': {}}
        OA_mock.get_resource.side_effect = [json.loads(self.reprovisioning_tenant),
                                            {'companyName': 'fake_company'},
                                            {'subscriptionId': 555}]

        resp = self.client.post('/v1/tenant/123/reprovision', headers=self.headers,
                                data=self.reprovisioning_tenant)

        OA_mock.send_request.assert_called_with('PUT',
                                                '/aps/2/application/tenant/123',
                                                {'statusData': {}})
        self.assertEqual(resp.status_code, 200)

    @bypass_auth
    @patch('connector.v1.resources.tenant.provision_fallball_client')
    @patch('connector.v1.resources.tenant.FbUser')
    @patch('connector.v1.resources.tenant.OA')
    @patch('connector.v1.resources.tenant.g')
    @patch('connector.v1.resources.tenant.get_name_for_tenant')
    @patch('connector.v1.resources.tenant.Client')
    def test_tenant_reprovision_reprovisioned(self, FbClient_mock,
                                              get_name_for_fb_client_mock, flask_g_mock,
                                              OA_mock, FbUser_mock, provision_fb_client_mock):
        fb_client_mock = FbClient_mock.return_value
        fb_client_mock.name = 'fake_company_name'
        fb_client_mock.reseller = Reseller('fake_reseller')
        provision_result_mock = provision_fb_client_mock.return_value
        provision_result_mock.status_code = 202
        provision_result_mock.body = {'statusData': {}}
        OA_mock.get_resource.side_effect = [json.loads(self.reprovisioned_tenant),
                                            {'companyName': 'fake_company'},
                                            {'subscriptionId': 555}]

        resp = self.client.post('/v1/tenant/123/reprovision', headers=self.headers,
                                data=self.reprovisioned_tenant)

        self.assertEqual(resp.status_code, 400)
