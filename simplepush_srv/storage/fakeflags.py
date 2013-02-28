from . import StorageBase


class ConfigFlags(StorageBase):
    """ A fake configuration manager.

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
        self._init(config)

    def _init(self, config):
        """ Initialize to values defined in config.ini """
        if "Configurator" in str(type(config)):
            config = config.get_settings()
        for key in filter(lambda x: x.startswith('flags'),
                          config.keys()):
            self.localFlags[key[6:]] = config[key]

    def get(self, key, default=None):
        return self.localFlags.get(key, default)

    def set(self, key, value):
        self.localFlags[key] = value
        return value

    def delete(self, key):
        del self.localFlags[key]
        return True
