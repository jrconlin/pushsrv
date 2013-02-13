from . import FakeLogger, FakeFlags
from simplepush_srv import main
from webtest import TestApp
import json
import unittest2
import time
import uuid


class TestViews(unittest2.TestCase):

    def load(self):
        data = [{'pk': '111.aaa', 'channelID': 'aaa', 'uaid': '111',
                 'version': 1},
                {'pk': '111.bbb', 'channelID': 'bbb', 'uaid': '111',
                 'version': 1},
                {'pk': '111.exp', 'channelID': 'exp', 'uaid': '111',
                 'version': 0, 'state': 0},
                {'pk': '222.ccc', 'channelID': 'ccc', 'uaid': '222',
                 'version': 2}]
        self.storage._load(data)

    def setUp(self):
        self.flags = FakeFlags()
        self.settings = {
            'db.backend': 'simplepush_srv.storage.memcache_sql.Storage',
            'db.memcache_servers': 'localhost:11211',
            'db.type': 'sqlite',
            #'db.db': ':memory:',
            'db.db': '/tmp/test.db',
            'logging.use_metlog': False,
            'flags': self.flags,
            'logger': FakeLogger()}
        self.app = TestApp(main({}, **self.settings))
        # pull these out of the fake app for convenience.
        self.storage = self.app.app.registry.get('storage')
        self.logger = self.app.app.registry.get('logger')

    def tearDown(self):
        self.storage.purge()

    def test_get_register(self):
        self.load()
        response = self.app.get('/v1/register/')
        assert('uaid' in response.json_body)
        assert('channelID' in response.json_body)
        assert('.' not in response.json_body['channelID'])
        assert('pushEndpoint' in response.json_body)
        assert(response.json_body['uaid'] != response.json_body['channelID'])
        myChid = uuid.uuid4().hex
        response2 = self.app.put('/v1/register/%s' % (myChid),
                                 headers={'X-UserAgent-ID':
                                          str(response.json_body['uaid'])})
        assert(response.json_body['uaid'] == response2.json_body['uaid'])
        assert(response2.json_body['channelID'] == myChid)

    def test_del_chid(self):
        self.load()
        self.flags['recovery'] = time.time()
        self.app.delete('/v1/112.aaa', headers={'X-UserAgent-ID': '112'},
                        status=410)
        self.flags.delete('recovery')
        self.app.delete('/v1/', headers={'X-UserAgent-ID': '112'}, status=404)
        self.app.delete('/v1/111.aaa', status=403)
        response = self.app.delete('/v1/111.aaa',
                                   headers={'X-UserAgent-ID': '111'})
        assert(response.json_body == {})

    def test_get_update(self):
        self.load()

        self.app.get('/v1/update/', status=403)
        response = self.app.get('/v1/update/',
                                headers={'X-UserAgent-ID': '111'}).json_body
        assert('exp' in response.get('expired'))
        assert('channelID' in response['updates'][0])
        assert('version' in response['updates'][0])
        response = self.app.get('/v1/update/',
                                headers={'X-UserAgent-ID': '666'},
                                status=410)

    def test_post_update(self):
        restore = [{'channelID': '111.aaa', 'version': '5'},
                   {'channelID': '111.bbb', 'version': '6'}]
        response = self.app.post('/v1/update/',
                                 params=json.dumps(restore),
                                 headers={'Content-Type': 'application/json'},
                                 status=403)
        response = self.app.post('/v1/update/',
                                 params=json.dumps(restore),
                                 headers={'X-UserAgent-ID': '111',
                                     'Content-Type': 'application/json'},
                                 status=200)

        assert(response.json_body.get('digest') == '111.aaa,111.bbb')
        response = self.app.post('/v1/update/',
                                params=json.dumps(restore),
                                headers={'X-UserAgent-ID': '111',
                                         'Content-Type': 'application/json'},
                                status=410)

    def test_channel_update(self):
        self.load()
        response = self.app.put('/v1/update/111.aaa',
                                params={'version': 9})
        assert(response.json_body == {})
        self.flags['recovery'] = time.time()
        response = self.app.put('/v1/update/111.zzz',
                                params={'version': 9}, status=503)
        self.flags.delete('recovery')
        response = self.app.put('/v1/update/111.zzz',
                                params={'version': 9}, status=404)

