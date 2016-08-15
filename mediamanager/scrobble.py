"""
    Scrobble music to last.fm

    TODO implement libre.fm
    """

from __future__ import unicode_literals
import time
import pylast
import logging
from Queue import Queue

q = Queue()

log = logging.getLogger(__name__)

API_KEY = "b725246f2c3e1738153c656928483570"
API_SECRET = "e08b9a80defa4ccd9fda4d4e89d5eb19"

ScrobbleNetwork = pylast.LastFMNetwork


def scrobble_many(info_l, lastfm_user):
    import socket
    socket.setdefaulttimeout(timeout=3)

    """Scrobble a song to a given user.

        `info_l` songs: a  list  of info dict as represented in Media
        `lastfm_user` dict: {'username': xxx, 'password': xxx}

        Other methods take care of getting:
        - info from songid
        - lastfm_user from request.username
        """
    for info in info_l:
        for x in ['artist', 'title']:
            assert info.get(x), "Missing required field: %s" % x

    network = ScrobbleNetwork(api_key=API_KEY, 
                              api_secret=API_SECRET, 
                              username=lastfm_user.get('username'), 
                              password_hash=pylast.md5(lastfm_user.get('password'))
                            )

    ret = network.scrobble_many(info_l)
    return ret


def get_similar(info, lastfm_user):
    """Get a playlist of song similar to the given one.

        TODO cache the list
        TODO match given items with the ones in the collection.
            A smart way could be generating uuid
    """
    network = ScrobbleNetwork(api_key=API_KEY, api_secret=
                              API_SECRET, username=lastfm_user.get('username'), password_hash=pylast.md5(lastfm_user.get('password')))

    t = pylast.Track(info.get('artist'), info.get('title'), network)

    return [(x.item.artist.name, x.item.title) for x in t.get_similar()]


def scrobble_worker():
    """Send scrobbling request to last.fm.

        Queue items are made of:
        qitem=( user, info)
    """
    log.info("starting scrobble worker")
    info = True
    while info:
        lastfm_user, info = q.get()
        try:
            scrobble_many([info], lastfm_user)
        except:
            log.exception("error while scrobbling entry: %r" % info)
        q.task_done()
    log.info("exiting scrobble worker")
