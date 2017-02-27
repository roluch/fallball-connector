from mock import patch

from connector.config import Config

config = Config()


def bypass_auth(fn):
    # type: (object) -> object
    def test_wrapper(*args, **kwargs):
        with patch('connector.v1.check_oauth_signature') as signature_mock, \
                patch('connector.v1.get_client_key') as key_mock, \
                patch('connector.v1.Reseller') as reseller_mock, \
                patch('connector.v1.get_reseller_name') as reseller_name_mock:
            signature_mock.return_value = True
            reseller_name_mock.return_value = 'strategize-back-end-technologies'
            key_mock.return_value = config.oauth_key
            instance = reseller_mock.return_value
            instance.reseller_name = '123-123-123'
            fn(*args, **kwargs)

    return test_wrapper


class InlineClass(object):
    def __init__(self, dict):
        self.__dict__ = dict
