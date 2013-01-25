import random
import unittest
import uuid
import json
from funkload.FunkLoadTestCase import FunkLoadTestCase
from pprint import pprint


class SimpleTest(FunkLoadTestCase):
    registry = {}

    def setUp(self):
        # conf_get('section', 'key')
        self.base_url = 'http://' + self.conf_get('main',
                                                  'host') + '/v1'
        self.iterations = self.conf_get('main', 'iterations')

    def register(self):
        chid = uuid.uuid4().hex
        # randomly register a new UAID
        if (random.randint(1, 10) > 8):
            self.setHeader('X-UserAgent-ID', None)
        result = json.loads(self.get('%s/register/%s' % (self.base_url, chid),
                                     description="Registering...").body)
        if result['channelID'] in self.registry:
            raise Exception('OH SHIT! ' + result['channelID'])
        self.registry[result['channelID']] = result['uaid']
        pprint(result)
        self.setter()

    def fetcher(self):
        chid = random.choice(self.registry.keys())
        uaid = self.registry.get(chid)
        self.setHeader('X-UserAgent-ID', uaid)
        self.get("%s/update/" % (self.base_url),
                 description='Fetching %s ' % uaid)

    def setter(self):
        if len(self.registry) == 0:
            print "No elements in registry"
            return self.fetcher(self)
        result = random.choice(self.registry.keys())
        self.put("%s/update/%s" % (self.base_url, result),
                 params={'version': random.randrange(10000)},
                 description='Setting channel %s' % result)

    def test_picker(self):
        self.register()
        for iteration in xrange(int(self.iterations)):
            pick = random.randint(1, 10)
            if pick == 9:
                self.register()
            elif pick == 10:
                self.setter()
            else:
                self.fetcher()
        pprint (self.registry)

if __name__ in ('main', '__main__'):
    unittest.main()
