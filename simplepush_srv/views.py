from . import LOG
from mozsvc.metrics import Service
from utils import get_last_accessed
from .storage import StorageException
import pyramid.httpexceptions as http
import time
import traceback
import uuid

api_version = 1

register = Service(name='register',
                   path='/v%s/register/{chid}' % api_version,
                   description='Register new')
registern = Service(name='registern',
                    path='/v%s/register/' % api_version,
                    description='Register New no chid')
update = Service(name='update',
                 path='/v%s/update/' % api_version,
                 description='Update info')
updatech = Service(name='updatech',
                   path='/v%s/update/{chid}' % api_version,
                   description='Update channel')
item = Service(name='item',
               path='/v%s/{chid}' % api_version,
               description='item specific actions')


def gen_token(request):
    base = uuid.uuid4().hex
    return base


def has_uaid(request):
    if not 'X-UserAgent-ID' in request.headers:
        request.errors.add('header', 'X-UserAgent-ID',
                           'Missing X-UserAgent-ID header.')
        raise http.HTTPForbidden()


@register.get()
@register.put()
@registern.get()
@registern.put()
def get_register(request):
    """ Return a new channelID (and possibly a user agent) """
    storage = request.registry.get('storage')
    uaid = request.headers.get('X-UserAgent-ID', gen_token(request))
    flags = request.registry.get('flags')
    if flags.get('recovery') and not storage._uaid_is_known(uaid):
        raise http.HTTPGone()
    logger = request.registry.get('logger')
    chid = request.matchdict.get('chid', gen_token(request))
    uchid = '%s.%s' % (uaid, chid)
    if storage.register_chid(uaid, uchid, logger):
        return {'channelID': chid, 'uaid': uaid,
                'pushEndpoint': '%s://%s/v%s/update/%s' % (
                    request.environ.get('wsgi.url_scheme'),
                    request.environ.get('HTTP_HOST'),
                    api_version,
                    chid)}
    else:
        raise http.HTTPConflict()


@item.delete(validators=has_uaid)
def del_chid(request):
    """ Delete a channel """
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    uaid = request.headers.get('X-UserAgent-ID')
    chid = request.matchdict.get('chid')
    flags = request.registry.get('flags')
    if flags.get('recovery') and not storage._uaid_is_known(uaid):
        raise http.HTTPGone()  # 410
    if chid is None:
        raise http.HTTPForbidden()  # 403
    if not storage.delete_chid(uaid, chid, logger):
        raise http.HTTPServerError("Delete Failure")
    return {}


@update.get(validators=has_uaid)
def get_update(request):
    """ Return list of known CHIDs & versions for a UAID """
    uaid = request.headers.get('X-UserAgent-ID')
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    last_accessed = get_last_accessed(request)
    try:
        updates = storage.get_updates(uaid, last_accessed, logger)
    except StorageException, e:
        logger.log(msg=repr(e), type='error', severity=LOG.DEBUG)
        raise http.HTTPGone
    if updates is False:
        raise http.HTTPServerError()
    if updates.get('updates') is None or not len(updates.get('updates')):
        raise http.HTTPGone()  # 410
    else:
        return updates


@update.post(validators=has_uaid)
def post_update(request):
    """ Restore data from the client """
    uaid = request.headers.get('X-UserAgent-ID')
    #Storage checks for duplicate uaid info
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    try:
        data = request.json_body
        digest = storage.reload_data(uaid, data, logger)
        return {'digest': digest}
    except Exception:
        logger.log(msg=traceback.format_exc(), type='error', severity=LOG.WARN)
        raise http.HTTPGone


@updatech.put()
def channel_update(request):
    version = request.GET.get('version', request.POST.get('version'))
    if version is None:
        raise http.HTTPForbidden  # 403
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    chid = request.matchdict.get('chid')
    try:
        if storage.update_channel(chid, version, logger):
            return {}
        else:
            flags = request.registry.get('flags')
            recovery = flags.get('recovery')
            if recovery:
                if time.time() > recovery:
                    flags.delete('recovery')
                raise http.HTTPServiceUnavailable()  # 503
            else:

                raise http.HTTPNotFound()  # 404
    except http.HTTPServiceUnavailable, e:
        raise e
    except Exception, e:
        logger.log(msg=traceback.format_exc(), type='error',
                   severity=LOG.CRITICAL)
        raise e

