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

    log.info("request.headers: %s" % request.headers)
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in db.view")
    info = app.iposonic.get_entry_by_id(eid)
    return request.formatter(info)

