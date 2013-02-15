import redis
import warnings
from . import StorageBase


class FakeRedis(dict):

    def delete(self, key):
        if key in self:
            del self[key]


class SimplePushFlags(StorageBase):

    def __init__(self, config, **kw):
        try:
            self.redis = redis.StrictRedis(
                    host=config.get('flags.redis.host', 'localhost'),
                    port=int(config.get('flags.redis.port', '6379')))
            self.prefix = config.get('flags.prefix', '')

        except redis.ConnectionError:
            warnings.error("No REDIS server found!")
            self.redis = FakeRedis()

    def get(self, key, default=None):
        return self.redis.get('%s%s' % (self.prefix, key)) or default

    def set(self, key, value):
        return self.redis.set('%s%s' % (self.prefix, key), value)

    def delete(self, key):
        return self.redis.delete('%s%s' % (self.prefix, key))
