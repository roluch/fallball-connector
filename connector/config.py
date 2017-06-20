import os

import yaml
from yaml import Loader, SafeLoader


def construct_yaml_str(self, node):
    # Override the default string handling function
    # to always return unicode objects
    return self.construct_scalar(node)


Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)


def check_configuration(config):
    for item in (
        'fallball_service_url',
        'fallball_service_authorization_token',
        'oauth_key',
        'oauth_secret',
    ):
        if getattr(config, item).startswith('PUT_HERE_'):
            return False

    return True


class Config(object):
    conf_file = os.environ.get('CONFIG_FILE', './config.yml')
    debug = False
    diskspace_resource = None
    devices_resource = None
    fallball_service_url = None
    fallball_service_authorization_token = None
    oauth_key = None
    oauth_secret = None
    environment = None
    country = None

    def __init__(self):
        if not Config.diskspace_resource:
            self.load()

    @staticmethod
    def load():
        if not os.path.isfile(Config.conf_file):
            raise IOError("Config file not found: {}".format(Config.conf_file))

        with open(Config.conf_file, 'r') as c:
            config = yaml.load(c)
            Config.debug = bool(config.get('debug', False))
            Config.environment = config.get('ENVIRONMENT', {})
            Config.country = config.get('COUNTRY', {})

            try:
                Config.diskspace_resource = config['diskspace_resource']
                Config.devices_resource = config['devices_resource']
                Config.fallball_service_url = config['fallball_service_url']
                Config.fallball_service_authorization_token = \
                    config['fallball_service_authorization_token']
                Config.oauth_key = config['oauth_key']
                Config.oauth_secret = config['oauth_secret']
            except KeyError as e:
                raise RuntimeError(
                    "{} parameter not specified in config.".format(e))
