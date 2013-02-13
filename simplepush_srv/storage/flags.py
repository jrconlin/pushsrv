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
            self.redis = redis.StrictRedis(**kw)
        except redis.ConnectionError:
            warnings.error("No REDIS server found!")
            self.redis = FakeRedis()

    def get(self, key, default=None):
        return self.redis.get(key) or default

    def set(self, key, value):
        return self.redis.set(key, value)

    def delete(self, key):
        return self.redis.delete(key)
