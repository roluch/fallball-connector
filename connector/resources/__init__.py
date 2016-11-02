try:
    from functools import reduce
except ImportError:
    pass

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

import re

import requests
from flask import g, request


def parameter_validator(*args):
    def extract_params(where, *args):
        def extract_one(where, what):
            if what not in where:
                raise ValueError("Missing {} in request".format(what))
            return where[what]

        return reduce(extract_one, args, where)

    def validate(where):
        return extract_params(where, *args)

    return validate


def urlify(data):
    return re.sub(r'\s+', '-',
                  re.sub(r'[^\w\s]', '', data))


class OACommunicationException(Exception):
    def __init__(self, resp):
        msg = "Request to OA failed. OA responded with code {}\n{}".format(resp.status_code,
                                                                           resp.text)
        super(OACommunicationException, self).__init__(msg)


class OA(object):
    @staticmethod
    def get_resource(resource_id):
        oa_uri = request.headers.get('aps-controller-uri')
        transaction_id = request.headers.get('aps-transaction-id')
        rql_request = 'aps/2/resources/{}'.format(resource_id)
        oa_request = urljoin(oa_uri, rql_request)
        resp = requests.get(oa_request,
                            headers={'aps-transaction-id': transaction_id},
                            auth=g.auth)
        if resp.status_code != 200:
            raise OACommunicationException(resp)
        return resp.json()

    @staticmethod
    def get_resources(rql_request):
        oa_uri = request.headers.get('aps-controller-uri')
        transaction_id = request.headers.get('aps-transaction-id')
        oa_request = urljoin(oa_uri, rql_request)
        resp = requests.get(oa_request,
                            headers={'aps-transaction-id': transaction_id},
                            auth=g.auth)
        if resp.status_code != 200:
            raise OACommunicationException(resp)
        return resp.json()


class Memoize(object):
    def __init__(self, function):
        self.function = function
        self.memoized = {}

    def __call__(self, *args):
        if args not in self.memoized:
            self.memoized[args] = self.function(*args)
        return self.memoized[args]
