#
# Views for downloading songs
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
log = logging.getLogger('view_media')


@app.route("/rest/stream.view", methods=['GET', 'POST'])
def stream_view():
    """@params
        - id=1409097050
        - maxBitRate=0 TODO

    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (eid, maxBitRate) = map(request.args.get, ['id', 'maxBitRate'])

    print("request.headers: %s" % request.headers)
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    info = app.iposonic.get_entry_by_id(eid)
    path = info.get('path', None)
    assert path, "missing path in song: %s" % info

    def is_transcode(maxBitRate, info):
        try:
            maxBitRate = int(maxBitRate)
            if maxBitRate:
                return maxBitRate < info.get('bitRate')
        except:
            print("sending unchanged")
            return False

    print("actual - bitRate: ", info.get('bitRate'))
    assert os.path.isfile(path), "Missing file: %s" % path
    if is_transcode(maxBitRate, info):
        return Response(_transcode(path, maxBitRate), direct_passthrough=True)
    print("sending static file: %s" % path)
    return send_file(path)
    raise IposonicException("why here?")


            

def _transcode(srcfile, maxBitRate, dstformat="ogg"):
    cmd = ["transcoder/transcode.sh", srcfile, dstformat, maxBitRate]
    srcfile = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        data = srcfile.stdout.read(4096)
        if not data:
            break
        yield data


def _transcode_mp3(srcfile, maxBitRate):
    """Transcode mp3 files reducing the bitrate."""
    cmd = ["/usr/bin/lame", "-S", "-v", "-b", "32", "-B", maxBitRate,
           srcfile, "-"]
    print("generate(): %s" % cmd)
    srcfile = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        data = srcfile.stdout.read(4096)
        if not data:
            break
        yield data


@app.route("/rest/download.view", methods=['GET', 'POST'])
def download_view():
    """@params
        id=1409097050
        maxBitRate=0

    """
    if not 'id' in request.args:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    info = app.iposonic.get_entry_by_id(request.args['id'])
    assert 'path' in info, "missing path in song: %s" % info
    try:
        return send_file(info['path'])
    except:
        abort(404)
    raise IposonicException("why here?")


@app.route("/rest/scrobble.view", methods=['GET', 'POST'])
def scrobble_view():
    """Add song to last.fm"""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    return request.formatter({})


@app.route("/rest/setRating.view", methods=['GET', 'POST'])
def set_rating_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, rating) = map(request.args.get, ['id', 'rating'])
    if not rating:
        raise SubsonicMissingParameterException(
            'rating', sys._getframe().f_code.co_name)
    if not eid:
        raise SubsonicMissingParameterException(
            'id', sys._getframe().f_code.co_name)
    rating = int(rating)
    app.iposonic.update_entry(eid, {'userRating': rating})
    if rating == 5:
        app.iposonic.update_entry(
            eid, {'starred': time.strftime("%Y-%m-%dT%H:%M:%S")})
    return request.formatter({})


@app.route("/rest/star.view", methods=['GET', 'POST'])
def star_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, rating) = map(request.args.get, ['id', 'rating'])
    if not eid:
        raise SubsonicMissingParameterException(
            'id', sys._getframe().f_code.co_name)
    app.iposonic.update_entry(
        eid, {'starred': time.strftime("%Y-%m-%dT%H:%M:%S")})

    # XXX example code to be added to Iposonic
    # for managing user-based media tagging
    # like starred.
    # Going this way may need to really choiche ONE db
    # because we'll multiply data (eg. #items x #users)
    #usermedia = app.iposonic.db.UserMedia('mock_user', eid)
    #usermedia.update( {
    #    'starred': time.strftime("%Y-%m-%dT%H:%M:%S"),
    #    'eid': "%s:%s" % ('mock',eid),
    #    'mid' : eid,
    #    'uid' : 'mock'
    #    } )
    app.iposonic.create_entry(usermedia)

    return request.formatter({})


@app.route("/rest/unstar.view", methods=['GET', 'POST'])
def unstar_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, rating) = map(request.args.get, ['id', 'rating'])
    if not eid:
        raise SubsonicMissingParameterException(
            'id', sys._getframe().f_code.co_name)
    app.iposonic.update_entry(eid, {'starred': None})
    return request.formatter({})


class CacheError:
    pass


cache2 = dict()


def memorize(f):

    """The memorize pattern is a simple cache implementation.

        It requires that te underlying function takes two
        parameters: f(eid, nocache=False).
    """
    def tmp(eid, nocache=False, **kwds):
        try:
            if not nocache:
                (item, ts) = cache2[eid]
                if item:
                    return item
                # retry after 60sec in case
                #    of empty items
                if ts + 60 < time.time():
                    return item

        except KeyError:
            pass

        try:
            cache2[eid] = (f(eid, nocache=nocache, **kwds), time.time())
        except IposonicException:
            cache2[eid] = (None, time.time())

        return cache2[eid][0]
    return tmp


@memorize
def get_cover_art_file(eid, nocache=False):
    from mediamanager.cover_art import q

    """Return coverArt file, eventually downloading it.

        Successful download requires both Artist and Album, so
        store the filename as uuid(Artist/Album)
        1- if parent directory...
        2- if song, download as Artist/Album
        3- if album, download as Artist/Album
        3- if albumId...

        We should manage some border cases:
        a- featured artists
            ex. album: Antonella Ruggiero
                song: Antonella Ruggiero & Subsonica
    """

    # if everything is fine, just get the file
    cover_art_path = os.path.join("/", app.iposonic.cache_dir, "%s" % eid)
    if os.path.exists(cover_art_path):
        return cover_art_path

    # otherwise we need to guess from item info,
    # and hit the database
    info = app.iposonic.get_entry_by_id(eid)
    log.info("entry from db: %s" % info)

    # search cover_art using id3 tag
    if not info.get('artist') or not info.get('album'):
        return None

    # if we're a CD collection, use parent
    if info.get('isDir') and info.get('album').lower().startswith("cd"):
        info = app.iposonic.get_entry_by_id(info.get('parent'))
        log.info("album is a cd, getting parent info: %s" % info)

    cover_art_path = os.path.join(
        "/", app.iposonic.cache_dir, MediaManager.cover_art_uuid(info))
    log.info("checking cover_art_uuid: %s" % cover_art_path)
    if os.path.exists(cover_art_path):
        return cover_art_path

    # if we're a file, let's use parent or albumId
    if info.get('isDir') in [False, 'false', 'False']:
        cover_art_path = join(
            "/", app.iposonic.cache_dir, "%s" % info.get('parent'))
        if os.path.exists(cover_art_path):
            return cover_art_path

    cover_art_path = join("/", app.iposonic.cache_dir,
                          MediaManager.cover_art_uuid(info))
    if os.path.exists(cover_art_path):
        return cover_art_path

    # if it's not present
    # use the background thread to download
    # and return 503
    q.put(info)
    abort(503)


@app.route("/rest/getCoverArt.view", methods=['GET', 'POST'])
def get_cover_art_view():
    """ Get coverart with cache."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, size) = map(request.args.get, ['id', 'size'])

    cover_art_path = get_cover_art_file(eid)

    if cover_art_path is None:
        abort(404)

    return send_file(cover_art_path)


@memorize
def get_lyrics(lid, nocache=False, info=None):
    lyrics_path = os.path.join("/", app.iposonic.cache_dir, "%s.lyr" % lid)
    try:
        with open(lyrics_path, "rb") as f:
            ret = f.read()
            if ret:
                return {'lyrics': ret}
    except IOError:
        pass
    # if the entry is not in cache, search the web
    log.warn("cannot find lyrics on cache")
    assert info, "Bad call of get_lyrics without info argument"
    c = ChartLyrics()
    ret = c.search(info)
    with open(lyrics_path, "wb") as f:
        f.write(ret.get('lyrics').encode('utf-8'))
    return ret


@app.route("/rest/getLyrics.view", methods=['GET', 'POST'])
def get_lyrics_view():
    """
         artist    No        The artist name.
        title
    json_response: {lyrics: { artist: ..., title: ...} }
    xml_response: <lyrics artist="Muse" title="Hysteria">...."""
    def lyrics_uuid(info):
        return MediaManager.uuid("%s/%s" % (
                                 MediaManager.normalize_artist(
                                 info, stopwords=True),
                                 info['title'].lower())
                                 )
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (artist, title) = map(request.args.get, ['artist', 'title'])
    assert artist and title
    assert  'null' not in [artist,
                           title], "A required field (artist,title) is empty."
    info = {'artist': artist, 'title': title}
    lyrics_id = lyrics_uuid(info)
    lyrics = get_lyrics(lyrics_id, info=info)
    assert 'lyrics' in lyrics, "Missing lyrics in %s" % lyrics
    ret = {'lyrics': {'artist': artist, 'title': title, '': [lyrics[
        'lyrics']]}}

    return request.formatter(ret)

    raise NotImplementedError("WriteMe")
