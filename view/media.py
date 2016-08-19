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
from mediamanager import MediaManager
from urllib import  urlencode
from urllib2 import urlopen
import simplejson
from mediamanager.lyrics import ChartLyrics
from mediamanager import scrobble
#
# download and stream
#
log = logging.getLogger('view_media')


def stream_view_new():
    """@params
        - id=1409097050
        - maxBitRate=0 TODO

        Function to be run in another app to increase asyncronicity
        
        Calls:
            - db.view               to get file info
            - setnowplaying.view    to set now playing
    """
    import socket
    socket.setdefaulttimeout(2)
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (eid, maxBitRate) = map(request.args.get, ['id', 'maxBitRate'])

    log.info("request.headers: %r" % request.headers)
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    
    try:        
        log.info("contact setNowPlaying.view")
        r_map = urlencode({'u':u, 'p': p, 'id': eid, 'f': 'json', 'id': eid})
      #  simplejson.load(urlopen('http://localhost:5000/rest/setNowPlaying.view?'+ r_map, timeout=2))
    except IOError:
        log.exception("error while setNowPlaying")
    
    log.info("contact db.view")
    r_map = urlencode({'u':u, 'p': p, 'id': eid, 'f': 'json'})
    info = simplejson.load(urlopen('http://localhost:5000/rest/db.view?'+ r_map, timeout=2))
    info = info['subsonic-response']
    return send_file(info['path'])
  
@app.route("/rest/stream.view", methods=['GET', 'POST'])    
def stream_view_old():
    """@params
        - id=1409097050
        - maxBitRate=0 TODO

    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (eid, maxBitRate) = map(request.args.get, ['id', 'maxBitRate'])

    log.info("request.headers: %r" % request.headers)
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
            log.info("sending unchanged")
            return False

    log.info("actual - bitRate: %r" % info.get('bitRate'))
    # XXX encode may be redundant here
    assert os.path.isfile(path.encode('utf-8')), "Missing file: %r" % path.encode('utf-8','xmlcharrefreplace')

    # update now playing
    try:
        log.info("Update nowPlaying: %r for user: %r -> %r" % (eid,
                 u, MediaManager.uuid(u)))
        user = app.iposonic.update_user(
            MediaManager.uuid(u), {'nowPlaying': eid})
    except:
        log.exception("Can't update nowPlaying for user: %r" % u)

    if is_transcode(maxBitRate, info):
        return Response(_transcode(path, maxBitRate), direct_passthrough=True)
    log.info("sending static file: %r" % path)
    return send_file(path)


def _transcode(srcfile, maxBitRate, dstformat="ogg"):
    cmd = ["transcoder/transcode.sh", srcfile, dstformat, maxBitRate]
    srcfile = subprocess.Popen(cmd, stdout=subprocess.PIPE, close_fds=True, preexec_fn=os.setsid)
    try:
        while True:
            data = srcfile.stdout.read(4096)
            if not data:
                break
            yield data
    except:
        log.exception("close connection while transcoding: killing process")
        os.killpg(srcfile.pid, 15)
        srcfile.kill()
        raise
    finally:
        pass
#        #srcfile.wait()


def _transcode_mp3(srcfile, maxBitRate):
    """Transcode mp3 files reducing the bitrate."""
    cmd = ["/usr/bin/lame", "-S", "-v", "-b", "32", "-B", maxBitRate,
           srcfile, "-"]
    print("generate(): %s" % cmd)
    srcfile = subprocess.Popen(cmd, stdout=subprocess.PIPE, close_fds=True)
    while True:
        data = srcfile.stdout.read(4096)
        if not data:
            break
        yield data

    

@app.route("/rest/download.view", methods=['GET', 'POST'])
def download_view():
    """Download the file with a given id. The id-path mapping is retieved via db.view.
    
        @params
        id=1409097050
        maxBitRate=0

    """
    if not 'id' in request.args:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
        
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, maxBitRate) = map(request.args.get, ['id', 'maxBitRate'])

    r_map = urlencode({'u':u, 'p': p, 'id': eid, 'f': 'json'})
    info = simplejson.load(urlopen('http://127.0.0.1:5000/rest/db.view?'+ r_map))
    info = info['subsonic-response']
    try:
        return send_file(info['path'])
    except KeyError:
        log.exception("missing path in song: %r" % info)
        abort(404)
    except:
        abort(404)
    raise IposonicException("why here?")


@app.route("/rest/scrobble.view", methods=['GET', 'POST'])
def scrobble_view():
    """Add song to last.fm

        id	Yes		A string which uniquely identifies the file to scrobble.
        time	No		(Since 1.8.0) The time (in milliseconds since 1 Jan 1970) at which the song was listened to.
        submission	No	True	Whether this is a "submission" or a "now playing" notification.


    """
    try:
        from mediamanager.scrobble import q
    except:
        abort(404)

    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, ts, submission) = map(
        request.args.get, ['id', 'time', 'submission'])
    assert eid, "Missing song id"

    if not u:
        log.info("Cannot scrobble due to bad user value: %r" % repr(u))
        assert u

    log.info("Retrieving scrobbling credentials")
    lastfm_user = app.iposonic.get_users(MediaManager.uuid(u))
    log.info("Scobbling credentials: %r" % lastfm_user)

    # get song info and append timestamp
    info = app.iposonic.get_entry_by_id(eid)
    info.update({'timestamp': int(time.time())})
    q.put(({
        'username': lastfm_user.get('scrobbleUser'),
        'password': lastfm_user.get('scrobblePassword')}, info))

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
    log.info("search cover_art requires media info from db: %r" % info)

    # search cover_art using id3 tag
    if not info.get('artist') or not info.get('album'):
        return None

    # if we're a CD collection, use parent
    #   TODO add other patterns to "cd" eg. "disk", "volume"
    if info.get('isDir') and info.get('album').lower().startswith("cd"):
        info = app.iposonic.get_entry_by_id(info.get('parent'))
        log.info("album is a cd, getting parent info: %r" % info)

    cover_art_path = os.path.join(
        "/", app.iposonic.cache_dir, MediaManager.cover_art_uuid(info))
    log.info("checking cover_art_uuid: %r" % cover_art_path)
    if os.path.exists(cover_art_path):
        return cover_art_path

    # if we're a file, let's use parent or albumId
    if info.get('isDir') in [False, 'false', 'False']:
        cover_art_path = join(
            "/", app.iposonic.cache_dir, "%s" % info.get('parent'))
        if os.path.exists(cover_art_path):
            log.info("successfully get cover_art from parent directory")
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

    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (artist, title) = map(request.args.get, ['artist', 'title'])
    assert artist and title
    assert  'null' not in [artist,
                           title], "A required field (artist,title) is empty."
    info = {'artist': artist, 'title': title}
    lyrics_id = MediaManager.lyrics_uuid(info)
    lyrics = get_lyrics(lyrics_id, info=info)
    assert 'lyrics' in lyrics, "Missing lyrics in %s" % lyrics
    ret = {'lyrics': {'artist': artist, 'title': title, '': [lyrics[
        'lyrics']]}}

    return request.formatter(ret)

    raise NotImplementedError("WriteMe")


@app.route("/rest/getArtistInfo.view", methods=['POST'])  
def get_artist_info():
    """ INFO:werkzeug:127.0.0.1 - - [16/Aug/2016 01:03:52] "POST /rest/getArtistInfo.view?u=ioggstream&p=enc:3371727431706333317035&v=1.2.0&c=DSub&id=-1778893842&includeNotPresent=true HTTP/1.0" 404 -

<artistInfo>
<biography>
Black Sabbath is an English <a target='_blank' href="http://www.last.fm/tag/heavy%20metal" class="bbcode_tag" rel="tag">heavy metal</a> band that formed in 1968 in Birmingham, West Midlands, England, United Kingdom, originally comprising <a target='_blank' href="http://www.last.fm/music/Ozzy+Osbourne" class="bbcode_artist">Ozzy Osbourne</a> (vocals), <a target='_blank' href="http://www.last.fm/music/Tony+Iommi" class="bbcode_artist">Tony Iommi</a> (guitar), <a target='_blank' href="http://www.last.fm/music/Geezer+Butler" class="bbcode_artist">Geezer Butler</a> (bass), and <a target='_blank' href="http://www.last.fm/music/Bill+Ward" class="bbcode_artist">Bill Ward</a> (drums). In the early <a target='_blank' href="http://www.last.fm/tag/70s" class="bbcode_tag" rel="tag">70s</a>, they were the first to pair heavily distorted, sonically dissonant <a target='_blank' href="http://www.last.fm/tag/blues%20rock" class="bbcode_tag" rel="tag">blues rock</a> at slow speeds with lyrics about drugs, mental pain and abominations of war, thus giving birth to generations of metal bands that followed in their wake. <a target='_blank' href="http://www.last.fm/music/Black+Sabbath">Read more about Black Sabbath on Last.fm</a>.
</biography>
<musicBrainzId>5182c1d9-c7d2-4dad-afa0-ccfeada921a8</musicBrainzId>
<lastFmUrl>http://www.last.fm/music/Black+Sabbath</lastFmUrl>
<smallImageUrl>http://userserve-ak.last.fm/serve/64/27904353.jpg</smallImageUrl>
<mediumImageUrl>http://userserve-ak.last.fm/serve/126/27904353.jpg</mediumImageUrl>
<largeImageUrl>
http://userserve-ak.last.fm/serve/_/27904353/Black+Sabbath+sabbath+1970.jpg
</largeImageUrl>
<similarArtist id="22" name="Accept"/>
<similarArtist id="101" name="Bruce Dickinson"/>
<similarArtist id="26" name="Aerosmith"/>
</artistInfo>
   """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (artist, ) = map(request.args.get, ['id'])
    assert artist
    artist = app.iposonic.get_artists(eid=artist)
    ret = scrobble.get_artist_info(artist['name'])
    log.warn("%r: %r", artist, ret)
    return request.formatter(ret)
