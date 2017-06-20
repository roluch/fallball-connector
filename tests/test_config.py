from flask_testing import TestCase
from connector.app import app
from connector.config import check_configuration, Config
from tests.utils import InlineClass
from future.utils import viewitems


class TestConfig(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})

        return app

    def test_check_configuration(self):
        config = InlineClass({
            'fallball_service_url': 'FAKE_VALUE',
            'fallball_service_authorization_token': 'FAKE_VALUE',
            'oauth_key': 'FAKE_VALUE',
            'oauth_secret': 'FAKE_VALUE'
        })
        assert check_configuration(config) is True
        config.fallball_service_url = 'PUT_HERE_FAKE_VALUE'
        assert check_configuration(config) is False

    def test_config_load(self):
        Config.load()
        config = InlineClass({
            'debug': True,
            'fallball_service_url': 'PUT_HERE_FALLBALL_SERVICE_URI',
            'fallball_service_authorization_token': 'PUT_HERE_FALLBALL_SERVICE_AUTHORIZATION_TOKEN',
            'oauth_key': 'PUT_HERE_OAUTH_KEY',
            'oauth_secret': 'PUT_HERE_OAUTH_SECRET',
            'diskspace_resource': 'DISKSPACE',
            'devices_resource': 'DEVICES',
        })

        for (key, value) in viewitems(config.__dict__):
            self.assertTrue(hasattr(Config, key))

        Config.conf_file = 'tests/fake_config_invalid.json'
        with self.assertRaises(RuntimeError):
            Config.load()

        Config.conf_file = 'not_exists'
        with self.assertRaises(IOError):
            Config.load()
