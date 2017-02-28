from flask_testing import TestCase
from connector.app import app
from connector.config import check_configuration, Config
from utils import InlineClass


class TestConfig(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})

        return app

    def test_check_configuration(self):
        config = InlineClass({
            'fallball_service_url': 'FAKE_VALUE',
            'fallball_service_authorization_token': 'FAKE_VALUE',
            'oauth_key': 'FAKE_VALUE',
            'oauth_signature': 'FAKE_VALUE'
        })
        assert check_configuration(config) is True
        config.fallball_service_url = 'PUT_HERE_FAKE_VALUE'
        assert check_configuration(config) is False

    def test_config_load(self):
        Config.load()
        config = InlineClass({
            'loglevel': 'DEBUG',
            'fallball_service_url': 'PUT_HERE_FALLBALL_SERVICE_URI',
            'fallball_service_authorization_token': 'PUT_HERE_FALLBALL_SERVICE_AUTHORIZATION_TOKEN',
            'oauth_key': 'PUT_HERE_OAUTH_KEY',
            'oauth_signature': 'PUT_HERE_OAUTH_SIGNATURE',
            'diskspace_resource': 'DISKSPACE',
            'users_resource': 'USERS',
            'gold_users_resource': 'GOLD_USERS',
            'devices_resource': 'DEVICES',
            'default_user_limit': 10,
            'gold_user_limit': 15
        })
        for attr, value in config.__dict__.iteritems():
            assert value == getattr(Config, attr)

        Config.conf_file = 'tests/fake_config_invalid.json'
        with self.assertRaises(RuntimeError):
            Config.load()

        Config.conf_file = 'not_exists'
        with self.assertRaises(IOError):
            Config.load()
