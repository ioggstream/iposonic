#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
#

#from __future__ import unicode_literals

from flask import Flask
from flask import request

import random

from os.path import join

import simplejson
import logging

from authorizer import Authorizer

from iposonic import (Iposonic,
                      IposonicException,
                      SubsonicProtocolException,
                      SubsonicMissingParameterException,
                      )


from mediamanager import MediaManager, UnsupportedMediaError, StringUtils
from config import tmp_dir, cache_dir, music_folders, authorizer
import cgi

#
# Use one of the allowed DB
#
try:
    #assert False
    from iposonicdb import MySQLIposonicDB as Dbh
except:
    from iposonic import IposonicDB as Dbh

log = logging.getLogger('iposonic-webapp')
app = Flask(__name__)

###
# The web
###

fs_cache = dict()
iposonic = Iposonic(music_folders, dbhandler=Dbh, recreate_db=False)
#
# Test connection
#


@app.route("/rest/ping.view", methods=['GET', 'POST'])
def ping_view():
    """Return an empty response.

        Basic parameters (valid for all requests) are:
        - u
        - p
        - v
        - c
        - f
        - callback
    """
    (u, p, v, c) = map(request.args.get, ['u', 'p', 'v', 'c'])
    log.warn("songs: %s" % iposonic.db.get_songs())
    log.warn("albums: %s" % iposonic.db.get_albums())
    log.warn("artists: %s" % iposonic.db.get_artists())
    log.warn("indexes: %s" % iposonic.db.get_indexes())
    log.warn("indexes: %s" % iposonic.db.get_playlists())

    return request.formatter({}, version='1.8.0')


@app.route("/rest/getLicense.view", methods=['GET', 'POST'])
def get_license_view():
    """Return a valid license ;) """
    (u, p, v, c) = [request.args.get(x, None) for x in ['u', 'p', 'v', 'c']]
    return request.formatter({'license': {'valid': 'true', 'email': 'robipolli@gmail.com', 'key': 'ABC123DEF', 'date': '2009-09-03T14:46:43'}})

#
# Pre/Post processing
#


@app.before_request
def authorize():
    """Authenticate users"""
    (u, p, v, c) = map(
        request.args.get, ['u', 'p', 'v', 'c'])

    p_clear = hex_decode(p)
    if not authorizer.authorize(u, p_clear):
        return "401 Unauthorized", 401

    pass


@app.before_request
def set_formatter():
    """Return a function to create the response."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    if f == 'jsonp':
        if not callback:
            # MiniSub has a bug, trying to retrieve jsonp without
            #   callback in case of getCoverArt.view
            #   it's not a problem because the getCoverArt should
            #   return a byte stream
            if request.endpoint not in ['get_cover_art_view', 'stream_view', 'download_view']:
                log.info("request: %s" % request.data)
                raise SubsonicProtocolException(
                    "Missing callback with jsonp in: %s" % request.endpoint)
        request.formatter = lambda x: ResponseHelper.responsize_jsonp(
            x, callback)
    else:
        request.formatter = ResponseHelper.responsize_xml


@app.after_request
def set_content_type(response):
    """Set json response content-type."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    log.warn("response is streamed: %s" % response.is_streamed)

    if f == 'jsonp' and not response.is_streamed:
        response.headers['content-type'] = 'application/json'

    if not response.is_streamed and not request.endpoint in ['stream_view', 'download_view']:
        log.info("response: %s" % response.data)

    return response


#
# Helpers
#
def hex_decode(s):
    """Decode an eventually hex-encoded password."""
    if not s:
        return ""
    ret = ""
    if s.startswith("enc:"):
        s = s[4:]
        i = 0
        for i in range(0, len(s), 2):
            l = int(s[i:i + 2], 16)
            ret += chr(l)
    else:
        ret = s
    log.info("decoded password: %s" % ret)
    return ret


def randomize(dictionary, limit=20):
    a_all = dictionary.keys()
    a_max = len(a_all)
    ret = []
    r = 0

    if not a_max:
        return ret

    try:
        for x in range(0, limit):
            r = random.randint(0, a_max - 1)
            k_rnd = a_all[r]
            ret.append(dictionary[k_rnd])
        return ret
    except:
        log.info("a_all:%s" % a_all)
        raise


def randomize2(dictionary, limit=20):
    a_max = len(dictionary)
    ret = []

    for (k, v) in dictionary.iteritems():
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(v)
    return ret


def randomize2_list(lst, limit=20):
    a_max = len(lst)
    ret = []

    for k in lst:
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(k)
    return ret


class ResponseHelper:
    """Serialize a python dict to an xml object, and embeds it in a subsonic-response

      see test/test_responsehelper.py for the test and documentation
      TODO: we could @annotate this ;)
    """
    log = logging.getLogger('ResponseHelper')

    @staticmethod
    def responsize_jsonp(ret, callback, status="ok", version="9.0.0"):
        assert status and version  # TODO
        if not callback:
            raise SubsonicProtocolException()
        # add headers to response
        ret.update({
            'status': 'ok',
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        return "%s(%s)" % (
            callback,
            simplejson.dumps({'subsonic-response': ret},
                             indent=True,
                             encoding='latin_1')
        )

    @staticmethod
    def responsize_xml(ret, status="ok", version="9.0.0"):
        """Return an xml response from json and replace unsupported characters."""
        ret.update({
            'status': 'ok',
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        return ResponseHelper.jsonp2xml({'subsonic-response': ret}).replace("&", "\\&amp;")

    @staticmethod
    def jsonp2xml(json):
        """Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.

          ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }

            ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}

            ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }

            ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }

            ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
      "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}

                """
        ret = ""
        content = None
        for c in [str, int, unicode]:
            if isinstance(json, c):
                return str(json)
        if not isinstance(json, dict):
            raise Exception("class type: %s" % json)

        # every tag is a dict.
        #    its value can be a string, a list or a dict
        for tag in json.keys():
            tag_list = json[tag]

            # if tag_list is a list, then it represent a list of elements
            #   ex. {index: [{ 'a':'1'} , {'a':'2'} ] }
            #       --> <index a="1" /> <index b="2" />
            if isinstance(tag_list, list):
                for t in tag_list:
                    # for every element, get the attributes
                    #   and embed them in the tag named
                    attributes = ""
                    content = ""
                    for (attr, value) in t.iteritems():
                        # only serializable values are attributes
                        if value.__class__.__name__ in 'str':
                            attributes = """%s %s="%s" """ % (
                                attributes,
                                attr,
                                cgi.escape(
                                    StringUtils.to_unicode(value), quote=None)
                            )
                        elif value.__class__.__name__ in ['int', 'unicode', 'bool', 'long']:
                            attributes = """%s %s="%s" """ % (
                                attributes, attr, value)
                        # other values are content
                        elif isinstance(value, dict):
                            content += ResponseHelper.jsonp2xml(value)
                        elif isinstance(value, list):
                            content += ResponseHelper.jsonp2xml({attr: value})
                    if content:
                        ret += "<%s%s>%s</%s>" % (
                            tag, attributes, content, tag)
                    else:
                        ret += "<%s%s/>" % (tag, attributes)
            if isinstance(tag_list, dict):
                attributes = ""
                content = ""

                for (attr, value) in tag_list.iteritems():
                    # only string values are attributes
                    if not isinstance(value, dict) and not isinstance(value, list):
                        attributes = """%s %s="%s" """ % (
                            attributes, attr, value)
                    else:
                        content += ResponseHelper.jsonp2xml({attr: value})
                if content:
                    ret += "<%s%s>%s</%s>" % (tag, attributes, content, tag)
                else:
                    ret += "<%s%s/>" % (tag, attributes)

        ResponseHelper.log.info(
            "\n\njsonp2xml: %s\n--->\n%s \n\n" % (json, ret))

        return ret.replace("isDir=\"True\"", "isDir=\"true\"")
