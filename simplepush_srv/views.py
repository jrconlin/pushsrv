from . import LOG, inRecovery
from .storage.storage import Storage
from mako.template import Template
from mozsvc.metrics import Service
from utils import get_last_accessed
from webob import Response
import json
import os
import pyramid.httpexceptions as http
import time
import uuid

api_version = 1

register = Service(name='register',
                   path='/v%s/register/{chid}' % api_version,
                   description='Register new',
                   accept=['X-UserAgent-ID'])
update = Service(name='update',
                 path='/v%s/update' % api_version,
                 description='Update info',
                 accept=['X-UserAgent-ID', 'If-Modified-Since'])
updatech = Service(name='updatech',
                   path='/v%s/update/{chid}' % api_version,
                   description='Update channel',
                   accept=['X-UserAgent-ID'])
item = Service(name='item',
               path='/v%s/{chid}' % api_version,
               description='item specific actions')


def gen_token(request):
    base = uuid.uuid4().hex
    return base


@register.get()
def get_register(request):
    """ Return a new channelID (and possibly a user agent) """
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    uaid = request.headers.get('X-UserAgent-ID', gen_token(request))
    chid = request.matchdict.get('chid', gen_token(request))
    if storage.register_chid(uaid, chid, logger):
        return {'channelID': chid, 'uaid': uaid}
    else:
        raise http.HTTPServerError('Could not register channel')


@item.delete()
def del_chid(request):
    """ Delete a channel """
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    uaid = request.headers.get('X-UserAgent-ID')
    chid = request.matchdict.get('chid')
    if uaid is None:
        raise http.HTTPForbidden()
    if chid is None:
        raise http.HTTPNotFound
    if not storage.delete_chid(uaid, chid, logger):
        raise http.HTTPServerError("Delete Failure")
    return {}


@update.get()
def get_update(request):
    """ Return list of known CHIDs & versions for a UAID """
    uaid = request.headers.get('X-UserAgent-ID')
    if not uaid:
        raise http.HTTPForbidden()
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    last_accessed = get_last_accessed(request)
    updates = storage.get_updates(uaid, last_accessed, logger)
    if updates is None:
        raise http.HTTPGone  # 410
    if updates is False:
        raise http.HTTPServerError('crapstix')
    else:
        return updates


@update.post()
def post_update(request):
    """ Restore data from the client """
    uaid = request.headers.get('X-UserAgent-ID')
    if not uaid:
        raise http.HTTPForbidden()
    #Storage checks for duplicate uaid info
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    try:
        data = request.json_body
        digest = storage.reload_data(uaid, data, logger)
        return {'digest': digest}
    except Exception, e:
        logger.error(str(e))
        raise http.HTTPGone


@updatech.put()
def channel_update(request):
    version = request.GET.get('version', request.POST.get('version'))
    if version is None:
        raise http.HTTPNoContent
    storage = request.registry.get('storage')
    logger = request.registry.get('logger')
    chid = request.matchdict.get('chid')
    try:
        if storage.update_chid(chid, version, logger):
            return {}
        else:
            if inRecovery(request.registry['safe']):
                # add retry period?
                raise http.HTTPServiceUnavailable()
            else:
                raise http.HTTPNotFound()
    except Exception, e:
        logger.error(str(e))
        raise e

