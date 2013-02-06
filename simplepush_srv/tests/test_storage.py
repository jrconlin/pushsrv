from simplepush_srv.storage.storage import (Storage, SimplePushSQL,
                                            StorageException)
from . import TConfig, FakeLogger
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
            data = [{'channelID': 'aaa', 'uaid': '111', 'version': 1,
                     'last_accessed': 10},
                    {'channelID': 'bbb', 'uaid': '111', 'version': 1,
                     'last_accessed': 20},
                    {'channelID': 'exp', 'uaid': '111', 'version': 0,
                     'state': 0, 'last_accessed': 20},
                    {'channelID': 'ccc', 'uaid': '222', 'version': 2}]
        session = self.storage.Session()
        for datum in data:
            pk = "%s.%s" % (datum['uaid'], datum['channelID'])
            session.add(SimplePushSQL(pk=pk,
                                      chid=datum['channelID'],
                                      uaid=datum['uaid'],
                                      vers=datum['version'],
                                      last=datum.get('last_accessed'),
                                      state=datum.get('state', 1)))
        session.commit()

    def test_update_child(self):
        self.load()
        self.storage.update_channel('111.aaa', 2, FakeLogger())
        rec = self.storage._get_record('111.aaa')
        self.assertEqual(rec[0].get('vers'), '2')

    def test_register_chids(self):
        self.load()
        self.storage.register_chid('444', 'ddd', FakeLogger())
        rec = self.storage._get_record('444.ddd')
        self.assertEqual(rec[0].get('uaid'), '444')

    def test_delete_chid(self):
        self.load()
        self.storage.delete_chid('111', 'aaa', FakeLogger())
        rec = self.storage._get_record('111.aaa')
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0].get('state'), 0)

    def test_get_updates(self):
        self.load()
        data = self.storage.get_updates('111', last_accessed=None,
                                        logger=FakeLogger())
        self.assertEqual(data.get('expired')[0], 'exp')
        self.assertEqual(len(data.get('updates')), 2)
        data = self.storage.get_updates('111', last_accessed=20,
                                        logger=FakeLogger())
        self.assertEqual(len(data.get('updates')), 1)

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
