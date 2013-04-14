#
# Views for querying database
#
#
import os
import sys
import time
import subprocess
import logging
from os.path import join
from flask import request, send_file, Response, abort
from webapp import app
from iposonic import IposonicException, SubsonicProtocolException, SubsonicMissingParameterException
from mediamanager import MediaManager, UnsupportedMediaError
from mediamanager.cover_art import CoverSource
from urllib import urlopen
import urllib2
from mediamanager.lyrics import ChartLyrics
#
# download and stream
#
log = logging.getLogger('view_db')



@app.route("/rest/db.view", methods=['GET', 'POST'])
def db():
    """@params
        - id=1409097050
	return items for a given db id
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (eid, maxBitRate) = map(request.args.get, ['id', 'maxBitRate'])

    log.info("request.headers: %r" % request.headers)
    if not eid:
        raise SubsonicMissingParameterException('id', 'db.view', request=request)
    info = app.iposonic.get_entry_by_id(eid)
    return request.formatter(info)

@app.route("/rest/setnowplaying.view", methods=['GET', 'POST'])
def setnowplaying():
    """@params
        - id=1409097050
        - maxBitRate=0 TODO

    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])


    log.info("request.headers: %s" % request.headers)
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    info = app.iposonic.get_entry_by_id(eid)
    path = info.get('path', None)
    assert path, "missing path in song: %s" % info

    # update now playing
    try:
        log.info("Update nowPlaying: %s for user: %s -> %s" % (eid,
                 u, MediaManager.uuid(u)))
        user = app.iposonic.update_user(
            MediaManager.uuid(u), {'nowPlaying': eid})
    except:
        log.exception("Can't update nowPlaying for user: %s" % u)

    return request.formatter({})
