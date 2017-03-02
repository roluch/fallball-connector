from flask_testing import TestCase
from connector.app import app, home
from mock import patch


class TestApp(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})

        return app

    @patch('connector.app.jsonify')
    def test_home(self, jsonify_mock):
        expected_result = {'service': 'fallball_connector', 'host': 'localhost'}
        jsonify_mock.return_value = expected_result
        assert home() == expected_result
