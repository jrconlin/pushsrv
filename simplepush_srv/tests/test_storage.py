from simplepush_srv.storage.storage import (Storage, SimplePushSQL,
                                            StorageException)
from . import TConfig, FakeLogger
import time
import unittest2


class TestStorage(unittest2.TestCase):

    def setUp(self):
        self.storage = Storage(config=TConfig({'db.type': 'sqlite',
                                               'db.db': ':memory:'}))

    def tearDown(self):
        self.storage.purge()
        del self.storage

    def load(self, data=[]):
        if not len(data):
            data = [{'channelID': 'aaa', 'uaid': '111', 'version': 1},
                    {'channelID': 'bbb', 'uaid': '111', 'version': 1},
                    {'channelID': 'exp', 'uaid': '111', 'version': 0,
                        'state': 0},
                    {'channelID': 'ccc', 'uaid': '222', 'version': 2}]
        session = self.storage.Session()
        for datum in data:
            session.add(SimplePushSQL(chid=datum['channelID'],
                                      uaid=datum['uaid'],
                                      vers=datum['version'],
                                      last=time.time(),
                                      state=datum.get('state', 1)))
        session.commit()

    def test_update_child(self):
        self.load()
        self.storage.update_chid('aaa', 2, FakeLogger())
        rec = self.storage._get_record('aaa')
        self.assertEqual(rec[0].get('vers'), '2')

    def test_register_chids(self):
        self.load()
        self.storage.register_chid('444', 'ddd', FakeLogger())
        rec = self.storage._get_record('ddd')
        self.assertEqual(rec[0].get('uaid'), '444')

    def test_delete_chid(self):
        self.load()
        self.storage.delete_chid('111', 'aaa', FakeLogger())
        rec = self.storage._get_record('aaa')
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0].get('state'), 0)

    def test_get_updates(self):
        self.load()
        data = self.storage.get_updates('111', FakeLogger())
        self.assertEqual(data.get('expired')[0], 'exp')
        self.assertEqual(data.get('digest'), 'aaa,bbb')
        self.assertEqual(len(data.get('updates')), 2)

    def test_reload_data(self):
        data = self.storage.reload_data('111',
                [{'channelID': 'aaa', 'version': '5'},
                 {'channelID': 'bbb', 'version': '6'}],
                FakeLogger())
        self.assertEqual(data, 'aaa,bbb')
        #TODO: check that subsequent updates are rejected.
        with self.assertRaises(StorageException):
            self.storage.reload_data('111',
                                     [{'channelID': 'ccc', 'version': '7'}],
                                     FakeLogger())
