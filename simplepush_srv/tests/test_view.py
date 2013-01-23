from . import TConfig, FakeLogger, Request
from pyramid import testing
from simplepush_srv import views
from simplepush_srv.storage.storage import Storage, SimplePushSQL
import json
import pyramid.httpexceptions as http
import unittest2
import time


class TestViews(unittest2.TestCase):

    def load(self):
        data = [{'channelID': 'aaa', 'uaid': '111', 'version': 1},
                {'channelID': 'bbb', 'uaid': '111', 'version': 1},
                {'channelID': 'exp', 'uaid': '111', 'version': 0, 'state': 0},
                {'channelID': 'ccc', 'uaid': '222', 'version': 2}]
        session = self.storage.Session()
        for datum in data:
            pk = '%s.%s' % (datum['uaid'], datum['channelID'])
            session.add(SimplePushSQL(pk=pk,
                                      chid=datum['channelID'],
                                      uaid=datum['uaid'],
                                      vers=datum['version'],
                                      last=time.time(),
                                      state=datum.get('state', 1)))
        session.commit()

    def req(self, matchdict={}, user_id=None, headers=None, **kw):

        class Reg(dict):

            settings = {}

            def __init__(self, settings=None, **kw):
                super(Reg, self).__init__(**kw)
                if settings:
                    self.settings = settings

        request = Request(headers=headers, **kw)
        request.GET = kw.get('params',{})
        if 'post' in kw:
            request.POST = kw.get('post', {})
        request.registry = Reg(settings=self.config.get_settings())
        request.registry['storage'] = self.storage
        request.registry['logger'] = self.logger
        request.registry['safe'] = kw.get('safe') or {'start': time.time(),
                                                      'length': 60,
                                                      'mode': False}
        if matchdict:
            request.matchdict.update(matchdict)
        return request

    def setUp(self):
        self.config = testing.setUp()
        tsettings = TConfig({'db.type': 'sqlite',
                             'db.db': ':memory:',
                             'logging.use_metlog': False})
        self.storage = Storage(config=tsettings)
        self.logger = FakeLogger()

    def tearDown(self):
        self.storage.purge()

    def test_get_register(self):
        self.load()
        response = views.get_register(self.req())
        assert('uaid' in response)
        assert('channelID' in response)
        assert('pushEndpoint' in response)
        assert(response['uaid'] != response['channelID'])
        response2 = views.get_register(self.req(headers={'X-UserAgent-ID':
            response['uaid']}))
        assert(response['uaid'] == response2['uaid'])
        assert(response['channelID'] != response2['channelID'])

    def test_del_chid(self):
        self.load()
        self.assertRaises(http.HTTPForbidden, views.del_chid, self.req())
        self.assertRaises(http.HTTPNotFound, views.del_chid,
                          self.req(headers={'X-UserAgent-ID': 'aaa'}))
        response = views.del_chid(self.req(headers={'X-UserAgent-ID': '111'},
                                           matchdict={'chid': 'aaa'}))
        assert(response == {})

    def test_get_update(self):
        self.load()
        self.assertRaises(http.HTTPForbidden, views.get_update, self.req())
        response = views.get_update(self.req(headers={'X-UserAgent-ID':
                                                      '111'}))
        assert('exp' in response.get('expired'))
        assert(response['digest'] == 'aaa,bbb')
        assert('channelID' in response['updates'][0])
        assert('version' in response['updates'][0])
        self.assertRaises(http.HTTPGone, views.get_update,
                          self.req(headers={'X-UserAgent-ID': '666'}))

    def test_post_update(self):
        restore = [{'channelID': 'aaa', 'version': '5'},
                   {'channelID': 'bbb', 'version': '6'}]
        self.assertRaises(http.HTTPForbidden, views.post_update, self.req())
        response = views.post_update(self.req(headers={'X-UserAgent-ID':
                                                       '111',
                                                       'Content-Type':
                                                       'application/json'},
                                              body=json.dumps(restore)))
        assert(response.get('digest') == 'aaa,bbb')
        self.assertRaises(http.HTTPGone, views.post_update,
                          self.req(headers={'X-UserAgent-ID': '111'},
                                   body=json.dumps(restore)))

    def test_channel_update(self):
        self.load()
        response = views.channel_update(self.req(matchdict={'chid': 'aaa'},
                                                 post={'version': '9'}))
        assert(response == {})
        self.assertRaises(http.HTTPServiceUnavailable, views.channel_update,
                          self.req(matchdict={'chid': 'zzz'},
                                   post={'version': '9'},
                                   safe={'mode': True,
                                         'start': time.time(),
                                         'length': 60}))
        self.assertRaises(http.HTTPNotFound, views.channel_update,
                          self.req(matchdict={'chid': 'zzz'},
                                   post={'version': '9'},
                                   safe={'mode': False,
                                         'start': time.time(),
                                         'length': 60}))

