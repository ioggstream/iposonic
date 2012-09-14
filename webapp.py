#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
#
# TODO manage argv for:
#   * music_folders
#   * authentication backend
#   * reset db
#
#from __future__ import unicode_literals

from flask import Flask
from flask import request, send_file

import os
import sys
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

from art_downloader import CoverSource
from urllib import urlopen
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


#
# Configuration
#
tmp_dir = "/tmp/iposonic"
cache_dir = join(tmp_dir, "_cache/")
music_folders = [
    #"/home/rpolli/workspace-py/iposonic/test/data/"
    "/opt/music/"
]
fs_cache = dict()
iposonic = Iposonic(music_folders, dbhandler=Dbh, recreate_db=False)

# While developing don't enforce authentication
#   otherwise you can use a credential file
#   or specify your users inline
authorizer = Authorizer(mock=True, access_file=None)
authorizer.add_user("user", "password")
###
# The web
###

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
    print "songs: %s" % iposonic.db.get_songs()
    print "albums: %s" % iposonic.db.get_albums()
    print "artists: %s" % iposonic.db.get_artists()
    print "indexes: %s" % iposonic.db.get_indexes()
    print "indexes: %s" % iposonic.db.get_playlists()

    return request.formatter({})


@app.route("/rest/getLicense.view", methods=['GET', 'POST'])
def get_license_view():
    """Return a valid license ;) """
    (u, p, v, c) = [request.args.get(x, None) for x in ['u', 'p', 'v', 'c']]
    return request.formatter({'license': {'valid': 'true', 'email': 'robipolli@gmail.com', 'key': 'ABC123DEF', 'date': '2009-09-03T14:46:43'}})

#
# List music collections
#


@app.route("/rest/getMusicFolders.view", methods=['GET', 'POST'])
def get_music_folders_view():
    """Return all music folders."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    return request.formatter(
        {
            'musicFolders': {
                'musicFolder': [{
                    'id': MediaManager.get_entry_id(d), 
                    'name': d
                    } for d in iposonic.get_music_folders() if os.path.isdir(d)
                ]
            }
        }
    )


@app.route("/rest/getIndexes.view", methods=['GET', 'POST'])
def get_indexes_view():
    """Return subsonic indexes.

        params:
          - ifModifiedSince=0
          - musicFolderId=591521045

        xml response:
            <indexes lastModified="237462836472342">
              <shortcut id="11" name="Audio books"/>
              <shortcut id="10" name="Podcasts"/>
              <index name="A">
                <artist id="1" name="ABBA"/>
                <artist id="2" name="Alanis Morisette"/>
                <artist id="3" name="Alphaville"/>
              </index>
              <index name="B">
                <artist name="Bob Dylan" id="4"/>
              </index>

              <child id="111" parent="11" title="Dancing Queen" isDir="false"
              album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
              size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
              path="ABBA/Arrival/Dancing Queen.mp3"/>

              <child id="112" parent="11" title="Money, Money, Money" isDir="false"
              album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
              size="4910028" contentType="audio/flac" suffix="flac"
              transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
              path="ABBA/Arrival/Money, Money, Money.mp3"/>
            </indexes>

        jsonp response
            ...

        TODO implement @param musicFolderId
        TODO implement @param ifModifiedSince
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    # refresh indexes
    iposonic.refresh()

    #
    # XXX we should think to reimplement the
    #     DB in some consistent way before
    #     wasting time with unsearchable, dict-based
    #     data to format
    #
    return request.formatter({'indexes': iposonic.get_indexes()})


@app.route("/rest/getMusicDirectory.view", methods=['GET', 'POST'])
def get_music_directory_view():
    """Return the content of a directory.

      params:
        - id=-493506601
        -

      xml response 1:
          <directory id="1" name="ABBA">
            <child id="11" 
                parent="1" 
                title="Arrival" 
                artist="ABBA" 
                isDir="true" 
                coverArt="22"/>
            <child id="12" 
                parent="1" 
                title="Super Trouper" 
                artist="ABBA" 
                isDir="true" 
                coverArt="23"/>
          </directory>

      xml response 2:
          <directory id="11" parent="1" name="Arrival">
            <child id="111" 
                parent="11" 
                title="Dancing Queen" 
                isDir="false"
                album="Arrival" 
                artist="ABBA" 
                track="7" 
                year="1978" 
                genre="Pop" 
                coverArt="24"
                size="8421341" 
                contentType="audio/mpeg" 
                suffix="mp3" 
                duration="146" 
                bitRate="128"
                path="ABBA/Arrival/Dancing Queen.mp3"/>

            <child id="112" 
                parent="11" 
                ... # se above
                contentType="audio/flac" 
                suffix="flac"
                transcodedContentType="audio/mpeg" 
                transcodedSuffix="mp3"  
                duration="208" 
                bitRate="128"
                />
          </directory>

        jsonp response
    """
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])

    if not dir_id:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in getMusicDirectory.view")
    (path, dir_path) = iposonic.get_directory_path_by_id(dir_id)
    #
    # if nothing changed before our last visit
    #    don't rescan
    #
    last_modified = os.stat(dir_path).st_ctime
    artist = iposonic.db.Artist(path)
    children = []

    if fs_cache.get(dir_id, 0) == last_modified:
        print "Getting items from cache."
        children = iposonic.get_songs(query={'parent': dir_id})
        children.extend(iposonic.get_albums(query={'parent': dir_id}))
    else:
        for child in os.listdir(dir_path):
            child = StringUtils.to_unicode(child)
            if child[0] in ['.', '_']:
                continue
            path = join("/", dir_path, child)
            try:
                child_j = {}
                is_dir = os.path.isdir(path)
                # This is a Lazy Indexing. It should not be there
                #   unless a cache is set
                # XXX
                eid = MediaManager.get_entry_id(path)
                try:
                    child_j = iposonic.get_entry_by_id(eid)
                except IposonicException:
                    iposonic.add_entry(path, album=is_dir)
                    child_j = iposonic.get_entry_by_id(eid)

                children.append(child_j)
            except IposonicException as e:
                log.info(e)
        fs_cache.setdefault(dir_id, last_modified)

    def _track_or_die(x):
        try:
            return int(x['track'])
        except:
            return 0
    # Sort songs by track id, if possible
    children = sorted(children, key=_track_or_die)

    return request.formatter({'directory': {'id': dir_id, 'name': artist.get('name'), 'child': children}})


#
# Search
#
@app.route("/rest/search2.view", methods=['GET', 'POST'])
def search2_view():
    """Search songs in archive.

        params:
          - query=Mannoia
          - artistCount=10  TODO
          - albumCount=20   TODO
          - songCount=25    TODO

        xml response:
            <searchResult2>
                <artist id="1" name="ABBA"/>
                <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22"/>
                <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23"/>
                <song id="112" parent="11" title="Money, Money, Money" isDir="false"
                      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
                      size="4910028" contentType="audio/flac" suffix="flac"
                      transcodedContentType="audio/mpeg" transcodedSuffix="mp3"
                      path="ABBA/Arrival/Money, Money, Money.mp3"/>
            </searchResult2>

    """
    (u, p, v, c, f, callback, query) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'query'])
    print "query:%s\n\n" % query
    if not query:
        raise SubsonicProtocolException(
            "Missing required parameter: 'query' in search2.view")

    (artistCount, albumCount, songCount) = map(
        request.args.get, ["artistCount", "albumCount", "songCount"])

    # ret is
    print "searching"
    ret = iposonic.search2(query, artistCount, albumCount, songCount)
    #songs = [{'song': s} for s in ret['title']]
    #songs.extend([{'album': a} for a in ret['album']])
    #songs.extend([{'artist': a} for a in ret['artist']])
    print "ret: %s" % ret
    return request.formatter(
        {
            'searchResult2': {
                'song': ret['title'],
                'album': ret['album'],
                'artist': ret['artist']
            }
        }
    )
    raise NotImplementedError("WriteMe")



@app.route("/rest/getStarred.view", methods=['GET', 'POST'])
def get_starred_view():
    """
        xml response
            <starred>
                <artist name="Kvelertak" id="143408"/>
                <artist name="Dimmu Borgir" id="143402"/>
                <artist name="Iron Maiden" id="143403"/>
                <album id="143862" 
                        ... # album attributes
                       created="2011-02-26T10:45:30"
                       starred="2012-04-05T18:40:08"/>
                <album id="143888" 
                        ... # album attributes
                        created="2011-03-23T09:29:13" 
                        starred="2012-04-05T18:40:02"/>
                <song id="143588" 
                        ... # song attributes
                        created="2010-09-27T20:52:23" 
                        starred="2012-04-02T17:17:01" 
                      albumId="163" artistId="133" type="music"/>
                <song id="143600" parent="143386" title="Satellite 15....The Final Frontier"
                      album="The Final Frontier (Mission Edition)" artist="Iron Maiden" isDir="false" coverArt="143386"
                      created="2010-08-16T21:08:01" starred="2012-04-02T14:12:54" duration="521" bitRate="320" track="1"
                      year="2010" genre="Heavy Metal" size="21855635" suffix="mp3" contentType="audio/mpeg" isVideo="false"
                      path="Iron Maiden/2010 The Final Frontier/01 Satellite 15....The Final Frontier.mp3" albumId="156"
                      artistId="126" type="music"/>
                <song id="143604" parent="143386" title="The Alchemist" album="The Final Frontier (Mission Edition)"
                      artist="Iron Maiden" isDir="false" coverArt="143386" created="2010-08-16T21:07:51"
                      starred="2012-04-02T14:12:52" duration="269" bitRate="320" track="5" year="2010" genre="Heavy Metal"
                      size="11774455" suffix="mp3" contentType="audio/mpeg" isVideo="false"
                      path="Iron Maiden/2010 The Final Frontier/05 The Alchemist.mp3" albumId="156" artistId="126"
                      type="music"/>
            </starred>
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    ret = iposonic.search2(query, artistCount, albumCount, songCount)
    #songs = [{'song': s} for s in ret['title']]
    #songs.extend([{'album': a} for a in ret['album']])
    #songs.extend([{'artist': a} for a in ret['artist']])
    print "ret: %s" % ret
    return request.formatter(
        {
            'starred': {
                'song': ret['title'],
                'album': ret['album'],
                'artist': ret['artist']
            }
        }
    )

    raise NotImplementedError()

#
# Extras
#
@app.route("/rest/getAlbumList.view", methods=['GET', 'POST'])
def get_album_list_view():
    """Get albums

        params:
           - type   in random,
                    newest,     TODO
                    highest,    TODO
                    frequent,   TODO
                    recent,     TODO
                    starred,    TODO
                    alphabeticalByName, TODO
                    alphabeticalByArtist TODO
           - size   items to return TODO
           - offset paging offset   TODO

        xml response:
            <albumList>
                <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22" userRating="4" averageRating="4.5"/>
                <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23" averageRating="4.4"/>
            </albumList>
    """
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])
    (size, type_a, offset) = map(request.args.get, ['size', 'type', 'offset'])

    if not type_a in ['random', 'newest', 'highest', 'frequent', 'recent']:
        raise SubsonicProtocolException("Invalid or missing parameter: type")

    if not size:
        size = 20

    if type_a == 'random':
        albums = randomize2_list(iposonic.get_albums(), size)
    elif type_a == 'highest':
        albums = iposonic.get_albums()[:size]
    else:
        albums = [a for a in iposonic.get_albums()]

    return request.formatter({'albumList': {'album': albums}})


@app.route("/rest/getRandomSongs.view", methods=['GET', 'POST'])
def get_random_songs_view():
    """

    request:
      size    No  10  The maximum number of songs to return. Max 500.
      genre   No      Only returns songs belonging to this genre.
      fromYear    No      Only return songs published after or in this year.
      toYear  No      Only return songs published before or in this year.
      musicFolderId   No      Only return songs in the music folder with the given ID. See getMusicFolders.

    response xml:
      <randomSongs>
      <song id="111" parent="11" title="Dancing Queen" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
      size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
      path="ABBA/Arrival/Dancing Queen.mp3"/>

      <song id="112" parent="11" title="Money, Money, Money" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
      size="4910028" contentType="audio/flac" suffix="flac"
      transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
      path="ABBA/Arrival/Money, Money, Money.mp3"/>
      </randomSongs>

    response json:
        {'randomSongs':
            { 'song' : [
                {   'id' : ..,
                    'coverArt': ..,
                    'contentType': ..,
                    'transcodedContentType': ..,
                    'transcodedSuffix': ..
                }, ..
            }
        }
    """
    (size, genre, fromYear, toYear, musicFolderId) = map(request.args.get,
                                                         ['size', 'genre', 'fromYear', 'toYear', 'musicFolderId'])
    songs = []
    if genre:
        print "genre: %s" % genre
        songs = iposonic.get_genre_songs(genre)
    else:
        all_songs = iposonic.get_songs()
        assert all_songs
        songs = randomize2_list(all_songs)
    assert songs
    # add cover art
    songs = [x.update({'coverArt': x.get('parent')}) or x for x in songs]
    randomSongs = {'randomSongs': {'song': songs}}
    return request.formatter(randomSongs)


@app.route("/rest/getCoverArt.view", methods=['GET', 'POST'])
def get_cover_art_view():

    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, size) = map(request.args.get, ['id', 'size'])

    # Return file if present
    cover_art_path = join("/", cache_dir, "%s" % eid)
    try:
        return send_file(cover_art_path)
    except IOError:
        pass

    # ...then if song, try with parent...
    info = iposonic.get_entry_by_id(eid)
    try:
        if info.get('isDir') in [False, 'false', 'False']:
            cover_art_path = join("/", cache_dir, "%s" % info.get('parent'))
            return send_file(cover_art_path)
    except IOError:
        pass

    # ..finally download missing cover_art in cache_dir
    c = CoverSource()
    for cover in c.search(info.get('album')):
        print "confronting info: %s with: %s" % (info, cover)
        if len(set([MediaManager.normalize_album(x) for x in [info, cover]])) == 1:
            print "Saving image %s -> %s" % (cover.get('cover_small'), eid)
            fd = open(cover_art_path, "w")
            fd.write(urlopen(cover.get('cover_small')).read())
            fd.close()

            return send_file(cover_art_path)
        else:
            print "Artist mismatch: %s, %s" % tuple(
                [x.get('artist') for x in [info, cover]])
    raise IposonicException("Can't find CoverArt")


#
# Helpers
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
                print "request: %s" % request.data
                raise SubsonicProtocolException(
                    "Missing callback with jsonp in: %s" % request.endpoint)
        request.formatter = lambda x: ResponseHelper.responsize_jsonp(
            x, callback)
    else:
        request.formatter = ResponseHelper.responsize_xml


@app.after_request
def set_content_type(response):
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    print "response is streamed: %s" % response.is_streamed

    if f == 'jsonp' and not response.is_streamed:
        response.headers['content-type'] = 'application/json'

    if not response.is_streamed and not request.endpoint in ['stream_view', 'download_view']:
        print("response: %s" % response.data)

    return response


def hex_decode(s):
    """Decode an eventually hex-encoded password."""
    if not s:
        return ""
    ret = ""
    if s.startswith("enc:"):
        print "s: ", s
        s = s[4:]
        i = 0
        while i < len(s):
            l = int(s[i:i + 2], 16)
            print "l:", l
            l = chr(l)
            ret += l
            i += 2
    else:
        ret = s

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
        print "a_all:%s" % a_all
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
        ret.update({'status': 'ok', 'version': '19.9.9',
                   "xmlns": "http://subsonic.org/restapi"})
        return "%s(%s)" % (
            callback,
            simplejson.dumps({'subsonic-response': ret},
                             indent=True,
                             encoding='latin_1')
        )

    @staticmethod
    def responsize_xml(ret):
        """Return an xml response from json and replace unsupported characters."""
        ret.update({'status': 'ok', 'version': '19.9.9',
                   "xmlns": "http://subsonic.org/restapi"})
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
