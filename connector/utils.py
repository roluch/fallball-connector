import logging
import sys
import json
import os
import re
import uuid
from functools import partial

from flask import g

logger = logging.getLogger(__file__)


class ResellerNameFilter(logging.Filter):
    def filter(self, record):
        record.reseller_name = str(getattr(g, 'reseller_name', None))
        return True


class ConnectorLogFormatter(logging.Formatter):
    def format(self, record):
        resp = {}
        if isinstance(record.msg, dict):
            resp['message'] = record.msg
        else:
            resp['message'] = record.getMessage()
        resp['time'] = self.formatTime(record, self.datefmt)
        resp['level'] = record.levelname
        resp['reseller_id'] = record.reseller_name

        if isinstance(record.msg, dict):
            rec_type = record.msg.pop('type', None)
            if 'data' in record.msg:
                try:
                    record.msg['data'] = json.loads(record.msg['data'])
                except:
                    pass
        else:
            rec_type = None

        if rec_type:
            return '{}: {}'.format(rec_type.upper(), json.dumps(resp, indent=4))

        return json.dumps(resp, indent=4)


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        resp = {}
        if isinstance(record.msg, dict):
            resp['message'] = record.msg
        else:
            resp['message'] = record.getMessage()
        resp['time'] = self.formatTime(record, self.datefmt)
        resp['level'] = record.levelname
        resp['reseller_id'] = record.reseller_name
        return json.dumps(resp)


stream = logging.StreamHandler(sys.stdout)
logger.addFilter(ResellerNameFilter())
formatter = JsonLogFormatter() if os.getenv('JSON_LOG') else ConnectorLogFormatter()
stream.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream)


def log_request(request):
    logger.debug({"request_id": getattr(g, 'request_id', None),
                  "type": "request",
                  "app": "fallball_connector",
                  "method": request.method,
                  "url": request.url,
                  "headers": dict(request.headers),
                  "data": request.data.decode('utf-8')})


def log_response(response):
    logger.debug({"request_id": getattr(g, 'request_id', None),
                  "type": "response",
                  "app": "fallball_connector",
                  "status_code": response.status_code,
                  "status": response.status,
                  "headers": dict(response.headers),
                  "data": response.data.decode('utf-8'),
                  "company": getattr(g, 'company_name', None)})


def log_outgoing_request(request, where='unknown'):
    logger.debug({"request_id": getattr(g, 'request_id', None),
                  "type": "{}_request".format(where),
                  "app": "fallball_connector",
                  "method": request.method,
                  "url": request.url,
                  "headers": dict(request.headers),
                  "data": request.body})


def log_outgoing_response(response, where='unknown'):
    logger.debug({"request_id": getattr(g, 'request_id', None),
                  "type": "{}_response".format(where),
                  "app": "fallball_connector",
                  "status": response.status_code,
                  "headers": dict(response.headers),
                  "data": response.content.decode()})


log_oa_request = partial(log_outgoing_request, where='oa')
log_oa_response = partial(log_outgoing_response, where='oa')
log_fallball_request = partial(log_outgoing_request, where='fallball')
log_fallball_response = partial(log_outgoing_response, where='fallball')


def escape_domain_name(name):
    valid_name = re.sub(r'[^a-zA-Z0-9-.]', '-', name)
    valid_name = re.sub(r'(^-+)|(-+$)', '', valid_name)
    return valid_name


def guid():
    return uuid.uuid4().hex
