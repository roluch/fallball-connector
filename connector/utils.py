import logging
import sys
import json
import re

from flask import g


class ReverseProxied(object):
    """
    From http://flask.pocoo.org/snippets/35/ for compatibility when running behind reverse proxy

    Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


class ResellerNameFilter(logging.Filter):
    def filter(self, record):
        record.reseller_name = str(g.reseller_name)
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
        return json.dumps(resp)


logger = logging.getLogger(__file__)
logger.addFilter(ResellerNameFilter())
stream = logging.StreamHandler(sys.stdout)
formatter = ConnectorLogFormatter()
stream.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream)


def log_request(request):
    logger.info({"type": "request",
                 "app": "fallball_connector",
                 "method": request.method,
                 "url": request.url,
                 "headers": dict(request.headers),
                 "data": request.data.decode('utf-8')})


def log_response(response):
    logger.info({"type": "response",
                 "app": "fallball_connector",
                 "status_code": response.status_code,
                 "status": response.status,
                 "headers": dict(response.headers),
                 "data": response.data.decode('utf-8'),
                 "company": g.company_name})


def escape_domain_name(name):
    valid_name = re.sub(r'[^a-zA-Z0-9-.]', '-', name)
    valid_name = re.sub(r'(^-+)|(-+$)', '', valid_name)
    return valid_name
