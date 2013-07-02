#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
#

from __future__ import unicode_literals

from flask import Flask
from flask import request, abort
import random
import os
import simplejson
import logging
from exc import *
from mediamanager import stringutils
import cgi

#
# Use one of the allowed DB
#
try:
    #assert False
    from datamanager.mysql import MySQLIposonicDB as Dbh
    #from iposonicdb import SqliteIposonicDB as Dbh
except:
    from datamanager.inmemory import MemoryIposonicDB as Dbh

log = logging.getLogger('iposonic-webapp')


class IposonicApp(Flask):
    """Iposonic app, a flask of iposonic and authorizer."""
    iposonic = None


app = IposonicApp(__name__)

###
# The web
###
dump_response = False
fs_cache = dict()
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
    (u, p, v, c) = map(request.values.get, ['u', 'p', 'v', 'c'])
    iposonic = app.iposonic
    log.warn("config: %s" % app.config)
    log.warn("songs: %s" % len(iposonic.db.get_songs()))
    log.warn("albums: %s" % len(iposonic.db.get_albums()))
    log.warn("artists: %s" % len(iposonic.db.get_artists()))
    #log.warn("indexes: %s" % iposonic.db.get_indexes())
    #log.warn("playlists: %s" % iposonic.db.get_playlists())

    return request.formatter({})


@app.route("/rest/getLicense.view", methods=['GET', 'POST'])
def get_license_view():
    """Return a valid license ;) """
    (u, p, v, c) = [request.args.get(x, None) for x in ['u', 'p', 'v', 'c']]
    return request.formatter({'license': {'valid': 'true', 'email': 'robipolli@gmail.com', 'key': 'ABC123DEF', 'date': '2009-09-03T14:46:43'}})

#
# Pre/Post processing
#


def endpoint_requires_authentication(request, app):
    """The following endpoints don't strinctly require authentication."""
    if request.endpoint in ['get_cover_art_view']:
        # cover_art requires only the right params
        if app.config.get('free_coverart'):
            (v, c) = map(request.args.get, ['v', 'c'])
            if v and c:
                return False
            log.warn("Missing required params: v, c")
    return True


@app.before_request
def set_formatter():
    """Return a function to create the response."""
    (u, p, v, c, f, callback) = map(
        request.values.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    if f == 'json':
        request.formatter = ResponseHelper.responsize_json
    elif f == 'jsonp':
        if not callback:
            # MiniSub has a bug, trying to retrieve jsonp without
            #   callback in case of getCoverArt.view
            #   it's not a problem because the getCoverArt should
            #   return a byte stream
            if request.endpoint not in ['get_cover_art_view', 'stream_view', 'download_view']:
                log.info("request: %s" % request.data)
                raise SubsonicProtocolException(
                    "Missing callback with jsonp in: %s" % request.endpoint)
        request.formatter = lambda x, status='ok': ResponseHelper.responsize_jsonp(
            x, callback, status=status)
    else:
        request.formatter = ResponseHelper.responsize_xml


@app.before_request
def authorize():
    """Authenticate users"""

    # skip authentication on given endpoints
    if not endpoint_requires_authentication(request, app):
        return

    (u, p, v, c) = map(
        request.args.get, ['u', 'p', 'v', 'c'])

    # basic-auth has precedence over URI
    auth = request.authorization
    if auth:
        log.info(
            "Client sends basic-auth: %s:%s" % (auth.username, auth.password))
        p_clear = auth.password
        u = auth.username
    else:
        p_clear = hex_decode(p)

    if not app.authorizer.authorize(u, p_clear):
        abort(401)

    pass


@app.after_request
def set_content_type(response):
    """Set json response content-type."""
    (u, p, v, c, f, callback) = map(
        request.values.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    log.info("response is streamed: %s" % response.is_streamed)

    if f in ['jsonp', 'json'] and not response.is_streamed:
        response.headers[b'content-type'] = 'application/json'

    # Flask sets it by default
    if request.endpoint in ['get_cover_art_view']:
        response.headers[b'content-type'] = 'image/jpeg'
        #response.headers['content-type'] = 'application/octet-stream'

    if not response.is_streamed and not request.endpoint in ['stream_view', 'download_view']:
        # response.data is byte, so before printing we need to
        #   decode it as a unicode string
        log.info("response: %s" % response.data.decode('utf-8'))

    return response


#
# Error handling
#
@app.errorhandler(401)
def not_authenticated(e):
    ret = {'error':
           [{
            'code': 40,
            'message': 'Wrong username or password'
            }]
           }
    return request.formatter(ret, status='failed'), 401


@app.errorhandler(IposonicException)
def iposonic_error(e):
    ret = {'error':
           [{
            'code': 0,
            'message': "%s" % e
            }]
           }
    return request.formatter(ret, status='failed'), 500


@app.errorhandler(AssertionError)
def iposonic_error_in_flow(e):
    log.exception("Error: %s" % e)
    ret = {'error':
           [{
            'code': 0,
            'message': "%s" % e
            }]
           }
    return request.formatter(ret, status='failed'), 500


@app.errorhandler(Exception)
def iposonic_generic_error(e):
    ret = {'error':
           [{
            'code': 70,
            'message': "%s" % e
            }]
           }
    log.exception(e) #TODO does it work?
    return request.formatter(ret, status='failed'), 404
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
    random.seed(os.urandom(10))
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
    random.seed(os.urandom(10))
    a_max = len(dictionary)
    ret = []

    for (k, v) in dictionary.iteritems():
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(v)
    return ret


def randomize2_list(lst, limit=20):
    random.seed(os.urandom(10))
    a_max = len(lst)
    ret = []

    for k in lst:
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(k)
    return ret


def randomize_list(lst, limit=20):
    random.seed(os.urandom(10))
    a_max = len(lst)
    ret = []

    for k in range(limit):
        k_rnd = random.randint(0, a_max - 1)
        ret.append(lst[k_rnd])
    return ret


class ResponseHelper:
    """Serialize a python dict to an xml object, and embeds it in a subsonic-response

      see test/test_responsehelper.py for the test and documentation
      TODO: we could @annotate this ;)
    """
    log = logging.getLogger('ResponseHelper')

    @staticmethod
    def responsize_json(ret, status="ok", version="9.0.0"):
        ret.update({
            'status': status,
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        return simplejson.dumps({'subsonic-response': ret},
                                indent=False,
                                encoding='latin_1')

    @staticmethod
    def responsize_jsonp(ret, callback, status="ok", version="9.0.0"):
        assert status and version  # TODO
        #if not callback:
        #    raise SubsonicProtocolException()
        # add headers to response
        ret.update({
            'status': status,
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        return "%s(%s)" % (
            callback,
            simplejson.dumps({'subsonic-response': ret},
                             indent=False,
                             encoding='utf-8')
        )

    @staticmethod
    def responsize_xml(ret, status="ok", version="9.0.0"):
        import codecs
        """Return an xml response from json and replace unsupported characters."""
        ret.update({
            'status': status,
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        # To clear responses we need to mangle some BOM UTF chars
        return ResponseHelper.jsonp2xml({'subsonic-response': ret}).replace(u'\x01\xff\xfe', '').replace('&', '').encode('utf-8', 'xmlcharrefreplace')

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
                    if not isinstance(t, dict):
                        ret += "%s" % t
                    else:
                        for (attr, value) in t.iteritems():
                            # only serializable values are attributes
                            if value.__class__.__name__ in 'str':
                                attributes = """%s %s="%s" """ % (
                                    attributes,
                                    attr,
                                    cgi.escape(
                                        stringutils.to_unicode(value), quote=None)
                                )
                            elif value.__class__.__name__ in ['int', 'unicode', 'bool', 'long']:
                                attributes = """%s %s="%s" """ % (
                                    attributes, attr, value)
                            # other values are content
                            elif isinstance(value, dict):
                                content += ResponseHelper.jsonp2xml(value)
                            elif isinstance(value, list):
                                content += ResponseHelper.jsonp2xml(
                                    {attr: value})
                        if content:
                            ret += "<%s%s>%s</%s>" % (
                                tag, attributes, content, tag)
                        else:
                            ret += "<%s%s/>" % (tag, attributes)
            elif isinstance(tag_list, dict):
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

        # Log the source and destination of the response
        ResponseHelper.log.debug("ret object is  %s" % ret.__class__)
        if dump_response:
            ResponseHelper.log.debug(
                "\n\njsonp2xml: %s\n--->\n%s \n\n" % (json, ret))

        return ret.replace("isDir=\"True\"", "isDir=\"true\"")
