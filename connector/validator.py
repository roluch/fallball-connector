from oauthlib import oauth1 as oauth

from connector.config import Config


class RequestValidator(oauth.RequestValidator):
    enforce_ssl = False
    secret = 'secret'
    key = 'key'
    dummy_client = 'dummy'
    dummy_request_token = 'dummy'
    dummy_access_token = 'dummy'

    def __init__(self):
        self.endpoint = oauth.SignatureOnlyEndpoint(self)
        self._config = Config()
        super(RequestValidator, self).__init__()

    @property
    def nonce_length(self):
        return 16, 50

    def check_client_key(self, client_key):
        return True if client_key else False

    def validate_client_key(self, client_key, request):
        return client_key in self._config.oauth

    def get_client_secret(self, client_key, request):
        if client_key == 'dummy':
            return u'blah-blah-blah'
        return self._config.oauth[client_key]

    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce, request,
                                     request_token=None, access_token=None):
        return True  # we don't validate nonce and timestamp

    def validate_signature(self, url, command, body_string, headers):
        result, request = self.endpoint.validate_request(url, command, body_string, headers)
        return result

    def get_request(self, url, command, body_string, headers):
        result, request = self.endpoint.validate_request(url, command, body_string, headers)
        return request


def check_oauth_signature(request):
    return RequestValidator().validate_signature(request.url, request.method, request.data,
                                                 request.headers)


def get_client_key(request):
    oauth_request = RequestValidator().get_request(request.url, request.method, request.data,
                                                   request.headers)
    return oauth_request.client_key if oauth_request else None
