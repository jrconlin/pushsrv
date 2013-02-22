import json
import warnings
from . import StorageBase
from kazoo.client import (KazooClient, KazooState)
from kazoo.exceptions import (BadVersionError, NoNodeError,
                              ConnectionClosedError,
                              NodeExistsError, ZookeeperError)


class ConfigFlags(StorageBase):
    """ A configuration manager using ZooKeeper. For setting flags
    on all instances for a given product. This will default to
    using a locally stored cache if ZooKeeper fails to respond.

    Note: current live flags are limited to 1MB total.

    Set initial values in config.ini file as
        flags.foo = bar
    to set "foo" flag to value bar.

    """

    #TODO:
    # * Break flags into separate elements instead of single JSON?
    # * Add fake dict to hold settings if ZK not installed/avaliable.
    localFlags = {}
    version = None

    def __init__(self, config, **kw):
        try:
            if 'Configurator' in type(config).__name__:
                config = config.get_settings()
            conf = config.get('flags.zk.settings')
            if conf is not None:
                conf = dict(json.loads(conf))
                self.zk = KazooClient(conf)
            else:
                self.zk = KazooClient()
            # get a copy of the local flags.
            self.zk_path = config.get('flags.zk.path',
                                      '/general/config')
            self.zk.start()
            node = self.zk.exists(self.zk_path)
            if node is None:
                # Virgin install, set from the config values.
                self._init_zk(config)
            self.zk.add_listener(self._zk_listener)
            self._refreshCache(config=config)

        except Exception, e:
            warnings.warn("Could not connect to ZooKeeper %s" % repr(e))

    def _init_zk(self, config):
        """ Initialize ZooKeeper to values defined in config.ini """
        try:
            for key in filter(lambda x: x.startswith('flags'),
                              config.keys()):
                self.localFlags[key[6:]] = config[key]
            data = json.dumps(self.localFlags)
            if self.zk.exists(self.zk_path):
                node = self.zk.set(self.zk_path, data)
            else:
                self.zk.create(self.zk_path, data, makepath=True)
                node = self.zk.exists(self.zk_path)
            self.version = node.version
        except NodeExistsError:
            warnings.warn("Flags - Race Condition (I lost)")
            return False

    def get(self, key, default=None):
        while True:
            try:
                data, node = self.zk.get(self.zk_path)
                self.localFlags = json.loads(data)
                return self.localFlags.get(key, default)
            except ConnectionClosedError:
                self.zk.restart()
                continue
            except ZookeeperError:
                return self.localFlags.get(key, default)

    def set(self, key, value):
        self.localFlags[key] = value
        self._publish()
        return value

    def delete(self, key):
        del self.localFlags[key]
        self._publish()
        return True

    def _publish(self, config=None, version=None):
        """ Try to publish changes to ZooKeeper """
        if config is None:
            config = self.localFlags
        if version is None:
            version = self.version
        data = json.dumps(config)
        while True:
            try:
                # transactions hang.
                node = self.zk.exists(self.zk_path)
                if node is None:
                    node = self.zk.create(self.zk_path, value=data)
                else:
                    node = self.zk.set(self.zk_path, value=data,
                                       version=node.version)
                self.version = node.version
                return True
            except BadVersionError:
                warnings.warn("Flags - Race occurred (I lost)")
                return False
            except NoNodeError:
                warnings.warn("Flags - Failed to create node")
                return False
            except ZookeeperError, e:
                warnings.warn("Flags - Unknown error occurred %s" % repr(e))
                return False
            except ConnectionClosedError:
                self.zk.restart()

    def _refreshCache(self, config=None):
        """ Refresh the local cache from ZooKeeper """
        while True:
            try:
                data, node = self.zk.get(self.zk_path)
                break
            except NoNodeError:
                return self._init_zk(config)
            except ConnectionClosedError:
                self.zk.restart()
            except Exception, e:
                print repr(e);
        if len(data):
            self.localFlags = json.loads(data)
        else:
            self._publish(config=config, version=self.version)

    def _zk_listener(self, state):
        """ You've been reconnected! Time to refresh and pick up changes. """
        if state != KazooState.CONNECTED:
            self._refreshCache()
        return

