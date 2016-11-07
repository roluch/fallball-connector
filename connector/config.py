import json
import os


class Config(object):
    default_path = os.path.join(os.path.dirname(__file__), 'config.json')
    conf_file = os.environ.get('CONFIG_PATH', default_path)
    diskspace_resource = None
    default_user_limit = None
    gold_user_limit = None
    devices_resource = None
    users_resource = None
    gold_users_resource = None
    base_uri = None
    application_token = None
    oauth = None

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
            Config.gold_users_resource = config.get('gold_users_resource')
            try:
                Config.diskspace_resource = config['diskspace_resource']
                Config.users_resource = config['users_resource']
                Config.devices_resource = config['devices_resource']
                Config.base_uri = config['base_uri']
                Config.application_token = config['application_token']
                Config.oauth = config['oauth']
            except KeyError as e:
                raise RuntimeError(
                    "{} parameter not specified in config.".format(e))
