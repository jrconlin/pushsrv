import redis
from . import StorageBase


class SimplePushFlags(StorageBase):

    def __init__(self, config, **kw):
        self.redis = redis.StrictRedis(**kw)

    def get(self, key, default=None):
        return self.redis.get(key) or default

    def set(self, key, value):
        return self.redis.set(key, value)

    def delete(self, key):
        return self.redis.delete(key)
