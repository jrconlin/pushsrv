import unittest2
from simplepush_srv.storage.fakeflags import ConfigFlags


class TestFlags(unittest2.TestCase):

    test_conf = {
                 'flags.zk.path': '/test/simplepush/config',
                 'flags.alpha': 'Apple',
                 'flags.beta': 'Banana'}

    def setUp(self):
        self.flags = ConfigFlags(self.test_conf)
        self.flags._init(self.test_conf)

    def tearDown(self):
        #self.flags.zk.delete(self.flags.zk_path)
        pass


    def test_init(self):
        self.assertEqual('Apple', self.flags.get('alpha', 'qumquat'))
        self.assertEqual('Banana', self.flags.get('beta', 'qumquat'))

    def test_set(self):
        self.assertEqual('qumquat', self.flags.get('gamma', 'qumquat'))
        self.assertEqual('Cantalope', self.flags.set('gamma', 'Cantalope'))
        self.assertEqual('Cantalope', self.flags.get('gamma', 'qumquat'))

    def test_del(self):
        self.flags.delete('beta')
        self.assertEqual(self.flags.get('beta', 'qumquat'), 'qumquat')

