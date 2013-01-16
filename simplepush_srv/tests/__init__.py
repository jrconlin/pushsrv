from pyramid import testing
import json

class TConfig:

    def __init__(self, data):
        self.settings = data

    def get_settings(self):
        return self.settings


class FakeLogger:

    def error(self, s):
        self.log(s)

    def warn(self, s):
        self.log(s)

    def log(self, s):
        #print s
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


