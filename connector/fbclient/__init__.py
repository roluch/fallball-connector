import slumber
from slumber import exceptions
from marshmallow import Schema, fields

from requests import Request
from requests.auth import AuthBase

from flask import g

from connector.config import Config
from connector.utils import log_outgoing_request, log_outgoing_response

config = Config()


class StorageSchema(Schema):
    usage = fields.Int(load_only=True)
    limit = fields.Int()


class FallBallAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Token {}'.format(self.token)
        return r


class LoggingResource(slumber.Resource):
    def _request(self, method, data=None, files=None, params=None):
        serializer = self._store["serializer"]
        url = self.url()

        headers = {"accept": serializer.get_content_type()}

        if not files:
            headers["content-type"] = serializer.get_content_type()
            if data is not None:
                data = serializer.dumps(data)

        req = Request(method=method, url=url, data=data, params=params, files=files,
                      headers=headers)
        s = self._store["session"]
        prepped = s.prepare_request(req)
        g.log['out'].append(dict(request=None, response=None))
        g.log['out'][-1]['request'] = log_outgoing_request(prepped)
        resp = s.send(prepped)
        g.log['out'][-1]['response'] = log_outgoing_response(resp)

        if 400 <= resp.status_code <= 499:
            exception_class = exceptions.HttpNotFoundError if resp.status_code == 404 \
                else exceptions.HttpClientError
            raise exception_class("Client Error %s: %s" % (resp.status_code, url), response=resp,
                                  content=resp.content)
        elif 500 <= resp.status_code <= 599:
            raise exceptions.HttpServerError("Server Error %s: %s" % (resp.status_code, url),
                                             response=resp, content=resp.content)

        self._ = resp
        return resp


class LoggingApi(slumber.API):
    resource_class = LoggingResource
