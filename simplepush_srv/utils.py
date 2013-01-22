from . import LOG
from email import utils as eut
import time
import calendar


def str_to_UTC(datestr):
    secs = 0
    try:
        timet = eut.parsedate_tz(datestr)
        secs = int(calendar.timegm(timet[:8])) + timet[9]
    except Exception, e:
        import pdb; pdb.set_trace();
        raise e
    return secs


def get_last_accessed(request):
    last_accessed = None
    try:
        last_accessed_str = request.headers.get('If-Modified-Since')
        if last_accessed_str:
            last_accessed = str_to_UTC(last_accessed_str)
        if request.registry.get('logger'):
            ims_str = time.strftime('%a, %d %b %Y %H:%M:%S UTC',
                                    time.gmtime(last_accessed))
            request.registry['logger'].debug('I-M-S: %s (%s)' % (ims_str,
                last_accessed_str))
    except Exception, e:
        settings = request.registry.settings
        if settings.get('dbg.traceback', False):
            import traceback
            traceback.print_exc()
        if settings.get('dbg.break_unknown_exception', False):
            import pdb
            pdb.set_trace()
        request.registry['logger'].log('Unknown exception: %s' % str(e))
    return last_accessed


