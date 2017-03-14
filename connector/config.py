import json
import os


def check_configuration(config):
    for item in (
        'fallball_service_url',
        'fallball_service_authorization_token',
        'oauth_key',
        'oauth_signature',
    ):
        if getattr(config, item).startswith('PUT_HERE_'):
            return False

    return True


class Config(object):
    conf_file = os.environ.get('CONFIG_FILE', './config.json')
    debug = False
    diskspace_resource = None
    default_user_limit = None
    gold_user_limit = None
    devices_resource = None
    users_resource = None
    gold_users_resource = None
    fallball_service_url = None
    fallball_service_authorization_token = None
    oauth_key = None
    oauth_signature = None

    def __init__(self):
        if not Config.diskspace_resource:
            self.load()

    @staticmethod
    def load():
        if not os.path.isfile(Config.conf_file):
            raise IOError("Config file not found: {}".format(Config.conf_file))

        with open(Config.conf_file, 'r') as c:
            config = json.load(c)
            Config.default_user_limit = config.get('default_user_limit', 10)
            Config.gold_user_limit = config.get('gold_user_limit', 15)
            Config.gold_users_resource = config.get('gold_users_resource', 'GOLD_USERS')
            Config.debug = bool(config.get('debug', False))

            try:
                Config.diskspace_resource = config['diskspace_resource']
                Config.users_resource = config['users_resource']
                Config.devices_resource = config['devices_resource']
                Config.fallball_service_url = config['fallball_service_url']
                Config.fallball_service_authorization_token = \
                    config['fallball_service_authorization_token']
                Config.oauth_key = config['oauth_key']
                Config.oauth_signature = config['oauth_signature']
            except KeyError as e:
                raise RuntimeError(
                    "{} parameter not specified in config.".format(e))
