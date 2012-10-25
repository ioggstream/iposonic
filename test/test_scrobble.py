#
# scrobble playground (for now)
#
from __future__ import unicode_literals
from nose import *
import time
import pylast
from test_iposonic import harn_setup

API_KEY = "b725246f2c3e1738153c656928483570"
API_SECRET = "e08b9a80defa4ccd9fda4d4e89d5eb19"

username = "ioggstream"
password = "secret"
password_hash = pylast.md5(password)

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=
                               API_SECRET, username=username, password_hash=password_hash)


def test_get_user():
    u = network.get_user('ioggstream')
    u.get_library()
    u.get_country()
    u.get_neighbours()
    u.get_loved_tracks()
    u.get_top_artists()
    u.get_url()
    u.get_top_tags()
    u.get_top_albums()
    u.get_friends()
    u.get_name()
    u.get_playlists()
    u.get_playcount()


def scrobble(info, lastfm_user):
    """Scrobble a song to a given user.

        `info` song info dict as represented in Media
        `lastfm_user` dict: {'username': xxx, 'password': xxx}

        Other methods take care of getting:
        - info from songid
        - lastfm_user from request.username
        """
    for x in ['artist', 'title']:
        assert info.get(x), "Missing required field: %s" % x

    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=
                                   API_SECRET, username=lastfm_user.get('username'), password_hash=pylast.md5(lastfm_user.get('password')))
    ret = network.scrobble(
        info.get('artist'),
        info.get('title'),
        int(time.time()),
        album=info.get('album')
    )
    print (ret)


def scrobble_many(info_l, lastfm_user):
    """Scrobble a song to a given user.

        `info_l` songs: a  list  of info dict as represented in Media
        `lastfm_user` dict: {'username': xxx, 'password': xxx}

        Other methods take care of getting:
        - info from songid
        - lastfm_user from request.username
        """
    for x in ['artist', 'title']:
        assert info.get(x), "Missing required field: %s" % x

    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=
                                   API_SECRET, username=lastfm_user.get('username'), password_hash=pylast.md5(lastfm_user.get('password')))

    ret = network.scrobble_many(info_l)
    print (ret)


def test_scrobble():
    info = {
        'title': 'buonanotte fiorellino',
        'artist': 'francesco de gregori'
    }
    lastfm_user = {'username': 'ioggstream', 'password': 'secret'}
    scrobble(info, lastfm_user)


def test_scrobble_many():
    info = {
        'title': 'buonanotte fiorellino',
        'artist': 'francesco de gregori',
        'timestamp': int(time.time())
    }
    lastfm_user = {'username': 'ioggstream', 'password': 'secret'}

    scrobble_mant([info, info], lastfm_user)


def test_get_album_1():
    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=
                                   API_SECRET, username=lastfm_user.get('username'), password_hash=pylast.md5(lastfm_user.get('password')))

    top_albums = [(x.item.title, x.item.artist.name)
                  for x in u.get_top_albums()]
    top_albums = [(x.item.title, x.item.artist.name)
                  for x in u.get_top_albums()]


def test_shout():
    artist = network.get_artist("System of a Down")
    artist.shout("<3")


@SkipTest
def test_get_similar_playlist():
    info = {
        'title': 'buonanotte fiorellino',
        'artist': 'francesco de gregori',
        'timestamp': int(time.time())
    }
    lastfm_user = {'username': 'ioggstream', 'password': 'secret'}
    from mediamanager.scrobble import get_similar
    from mediamanager import MediaManager
    ret_l = get_similar(info, lastfm_user)
    uid_l = [MediaManager.lyrics_uuid(
        {'artist': a, 'title': t}) for (a, t) in ret_l]
    playlist = []
    for x in uid_l:
        assert iposonic.get


#def setup():
#    # add user with scrobbling credentials
