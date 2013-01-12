# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#import memcache
from dateutil import parser
from inspect import stack
import string


class StorageException(Exception):
    pass


class StorageBase(object):

    def __init__(self, config, **kw):
        self.config = config
        self.settings = config.get_settings()
        self.alphabet = string.digits + string.letters
        self.memory = {}

    def parse_date(self, datestr):
        if not datestr:
            return None
        try:
            return float(datestr)
        except ValueError:
            pass
        try:
            return float(parser.parse(datestr).strftime('%s'))
        except ValueError:
            pass
        return None

    # customize for each memory model

    def health_check(self):
        """ Check that the current model is working correctly """
        # Is the current memory model working?
        return False

    def purge(self):
        """ Purge all listings (ONLY FOR TESTING) """
        raise StorageException('Undefined required method: ' %
                               stack()[0][3])
