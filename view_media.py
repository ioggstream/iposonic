#
# Views for downloading songs
#
#
import os
import sys
import time
import subprocess
from os.path import join
from flask import request, send_file, Response, abort
from webapp import iposonic, app, cache_dir
from iposonic import IposonicException, SubsonicProtocolException, SubsonicMissingParameterException
from mediamanager import MediaManager, StringUtils, UnsupportedMediaError
from art_downloader import CoverSource
from urllib import urlopen

#
# download and stream
#


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
    info = iposonic.get_entry_by_id(eid)
    path = info.get('path', None)
    assert path, "missing path in song: %s" % info

    def is_transcode(maxBitRate, info):
        try:
            return int(maxBitRate) < info.get('bitRate')
        except:
            print "sending unchanged"
            return False

    print "actual - bitRate: ", info.get('bitRate')
    assert os.path.isfile(path), "Missing file: %s" % path
    if is_transcode(maxBitRate, info):
        return Response(_transcode_mp3(path, maxBitRate), direct_passthrough=True)
    print "sending static file: %s" % path
    return send_file(path)
    raise IposonicException("why here?")


def _transcode_mp3(srcfile, maxBitRate):
    """Transcode mp3 files reducing the bitrate."""
    cmd = ["/usr/bin/lame", "-B", maxBitRate, srcfile, "-"]
    print "generate(): %s" % cmd
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
    info = iposonic.get_entry_by_id(request.args['id'])
    assert 'path' in info, "missing path in song: %s" % info
    if os.path.isfile(info['path']):
        return send_file(info['path'])
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
    iposonic.update_entry(eid, {'userRating': rating})
    if rating == 5:
        iposonic.update_entry(
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
    iposonic.update_entry(eid, {'starred': time.strftime("%Y-%m-%dT%H:%M:%S")})
    return request.formatter({})


@app.route("/rest/unstar.view", methods=['GET', 'POST'])
def unstar_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, rating) = map(request.args.get, ['id', 'rating'])
    if not eid:
        raise SubsonicMissingParameterException(
            'id', sys._getframe().f_code.co_name)
    iposonic.update_entry(eid, {'starred': None})
    return request.formatter({})

cache_coverart = dict()


@app.route("/rest/getCoverArt.view", methods=['GET', 'POST'])
def get_cover_art_view():
    """Get coverart.

        For albums/directories it uses directory id, and have not
        access to the real artist name.

        For songs we can tweak a bit.
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, size) = map(request.args.get, ['id', 'size'])

    # Don't abuse album search
    if cache_coverart.get(eid, 0) + 60 > time.time():
        abort(404)

    # Return file if present
    cover_art_path = join("/", cache_dir, "%s" % eid)
    try:
        print "coverart: returning file"
        return send_file(cover_art_path)
    except IOError:
        pass

    # ...then if song, try with parent...
    info = iposonic.get_entry_by_id(eid)
    try:
        if info.get('isDir') in [False, 'false', 'False']:
            cover_art_path = join("/", cache_dir, "%s" % info.get('parent'))
            print "coverart %s: returning parent: %s" % (
                eid, info.get('parent'))
            return send_file(cover_art_path)
    except IOError:
        print "info: %s" % info
        pass

    # ...then with artist+album...
    try:
        cover_art_path = MediaManager.get_entry_id(
            "%s/%s" % (info.get('artist'), info.get('album')))
        return send_file(cover_art_path)
    except IOError:
        pass

    # ..finally download missing cover_art in cache_dir
    if not info.get('album'):
        print "info: ", info
        abort(404)

    print "coverart %s: searching album: %s " % (eid, info.get('album'))
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
                [x.get('artist', x.get('name')) for x in [info, cover]])

    cache_coverart.setdefault(eid, int(time.time()))
    raise IposonicException("Can't find CoverArt")


@app.route("/rest/getLyrics.view", methods=['GET', 'POST'])
def get_lyrics_view():
    raise NotImplementedError("WriteMe")
