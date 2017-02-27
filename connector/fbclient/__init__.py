from marshmallow import Schema, fields

from requests.auth import AuthBase

from connector.config import Config


config = Config()


class StorageSchema(Schema):  # pragma: no cover
    usage = fields.Int(load_only=True)
    limit = fields.Int()


class FallBallAuth(AuthBase):  # pragma: no cover
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Token {}'.format(self.token)
        return r
