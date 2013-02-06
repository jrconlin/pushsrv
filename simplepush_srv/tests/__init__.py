from pprint import pprint
from pyramid import testing
import json


class FakeFlags(dict):

    def delete(self, key):
        if key in self:
            del self[key]


class TConfig:

    def __init__(self, data):
        self.settings = data

    def get_settings(self):
        return self.settings


class FakeLogger:

    def error(self, msg=None, **kw):
        kw.update({'msg': msg})
        self.log(kw)

    def warn(self, msg=None, **kw):
        kw.update({'msg': msg})
        self.log(kw)

    def debug(self, msg=None, **kw):
        kw.update({'msg': msg})
        self.log(kw)

    def log(self, msg=None, **kw):
        kw.update({'msg': msg})
        #pprint(kw)
        pass


def Request(params=None, post=None, matchdict=None, headers=None,
            registry=None, **kw):

    testing.DummyRequest.json_body = property(lambda s: json.loads(s.body))
    request = testing.DummyRequest(params=params, post=post, headers=headers,
                                   **kw)
    request.route_url = lambda s, **kw: s.format(**kw)
    if matchdict:
        request.matchdict = matchdict
    if registry:
        request.registry.update(registry)
    return request


