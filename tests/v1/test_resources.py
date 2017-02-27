import json

from flask_testing import TestCase

from mock import patch, ANY, MagicMock, call

from connector.app import app

from connector.v1.resources import parameter_validator, OA, OACommunicationException

from connector.config import Config

from tests.v1.utils import bypass_auth

config = Config()


class TestMethods(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        return app

    def test_parameter_validator(self):
        validate = parameter_validator('fake_param')
        with self.assertRaises(ValueError):
            validate({})
        assert validate({'fake_param': 1}) == 1


class TestOA(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})
        return app

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_get_notification_manager(self, send_request_mock):
        OA.get_notification_manager()
        send_request_mock.assert_called()
        url = send_request_mock.call_args[0][1]
        assert 'notification-manager/1' in url

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_send_notification(self, send_request_mock):
        OA.send_notification('fake_notification')
        OA.send_notification('fake_notification', details='fake_notification_details')
        OA.send_notification('fake_notification', details='fake_notification_details',
                             messageKeys={'details': 123},
                             accountId='account123', status='error', userId='user123')
        send_request_mock.assert_called()
        expected_message = {
            'status': 'error',
            'message': {
                'message': 'fake_notification',
                'keys': {'details': 123}
            },
            'details': {
                'message': 'fake_notification_details',
                'keys': {'details': 123}
            },
            'accountId': 'account123',
            'userId': 'user123'
        }
        message = send_request_mock.call_args[0][2]
        assert message == expected_message

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_subscribe_on(self, send_request_mock):
        OA.subscribe_on(resource_id='fake_resource_id',
                        event_type='fake_event', handler='fake_handler',
                        relation='fake_relation',
                        source_type='fake_type')
        send_request_mock.assert_called()
        expected_subscription = {
            'event': 'fake_event',
            'source': {
                'type': 'fake_type'
            },
            'relation': 'fake_relation',
            'handler': 'fake_handler'
        }
        subscription = send_request_mock.call_args[0][2]
        assert subscription == expected_subscription

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_get_resource(self, send_request_mock):
        OA.get_resource('fake_resource_id', transaction=False, retry_num=5)
        send_request_mock.assert_called_with('get', ANY, transaction=False, retry_num=5)
        url = send_request_mock.call_args[0][1]
        assert 'fake_resource_id' in url

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_put_resource(self, send_request_mock):
        expected_body = {
            'aps': {
                'resourceId': 'fake_resource_id'
            }
        }
        OA.put_resource(expected_body, transaction=False, retry_num=5)
        send_request_mock.assert_called_with('put', ANY, body=ANY, transaction=False, retry_num=5)
        args, kwArgs = send_request_mock.call_args
        body = kwArgs['body']
        assert body == expected_body

    @bypass_auth
    @patch('connector.v1.resources.OA.send_request')
    def test_get_resources(self, send_request_mock):
        OA.get_resources('fake_rql_request', transaction=False, retry_num=5)
        send_request_mock.assert_called_with('get',
                                             'fake_rql_request',
                                             transaction=False, retry_num=5)

    @bypass_auth
    @patch('connector.v1.resources.requests')
    @patch('connector.v1.resources.request')
    @patch('connector.v1.resources.g')
    def test_send_request(self, flask_g_mock, flask_request_mock, requests_mock):
        flask_g_mock.auth = 'fake_auth'
        fake_headers = {
            'aps-resource-id': 'fake_impersonation_resource_id',
            'aps-transaction-id': 'fake_transaction_id',
            'Content-Type': 'application/json'
        }
        flask_request_mock.headers = {
            'aps-controller-uri': 'fake_aps_controller_uri',
            'aps-transaction-id': fake_headers['aps-transaction-id']
        }
        expected_body = {
            'aps': {
                'id': 'fake_resource_id'
            }
        }

        with self.assertRaises(OACommunicationException):
            OA.send_request('post', 'fake_path', retry_num=-1)
        status_200_mock = MagicMock()
        status_400_mock = MagicMock()
        status_500_mock = MagicMock()
        status_200_mock.status_code = 200
        status_400_mock.status_code = 400
        status_500_mock.status_code = 500
        requests_mock.request.side_effect = [status_500_mock, status_400_mock, status_200_mock]
        with self.assertRaises(OACommunicationException):
            OA.send_request('post', 'fake_path', transaction=False)
        OA.send_request('post', 'fake_path', body=expected_body, transaction=True,
                        impersonate_as='fake_impersonation_resource_id', retry_num=2)

        fake_call = call(method='post',
                         url='fake_path',
                         data=json.dumps(expected_body), headers=fake_headers,
                         auth=ANY, timeout=ANY,
                         verify=False)
        # as we have retry_num == 2 request must be called 2 times
        requests_mock.request.assert_has_calls([fake_call, fake_call])
