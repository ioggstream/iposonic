from __future__ import unicode_literals
from nose import *
from iposonic import Iposonic
from iposonicdb import MySQLIposonicDB
from mediamanager.scrobble import get_similar
import os
import time
from scanner import walk_music_folder, watch_music_folder
from mediamanager import MediaManager


def test_scanner_mysql():
    music_folders = [os.path.join("/", u"/opt/music/")]
    iposonic = Iposonic(music_folders,
                        dbhandler=MySQLIposonicDB,
                        recreate_db=True,
                        tmp_dir="/tmp/iposonic")
    iposonic.db.init_db()

    walk_music_folder(iposonic)

    print ("songs: %s" % iposonic.get_songs())
    print ("artists: %s" % iposonic.get_artists())
    print ("albums: %s" % iposonic.get_albums())

#    iposonic.db.end_db()


def test_get_similar_playlist():
    info = {
        'title': 'buonanotte fiorellino',
        'artist': 'francesco de gregori',
        'timestamp': int(time.time())
    }
    lastfm_user = {'username': 'ioggstream', 'password': 'secret'}
    ret_l = get_similar(info, lastfm_user)
    uid_l = [MediaManager.lyrics_uuid(
        {'artist': a, 'title': t}) for (a, t) in ret_l]
    playlist = []
    for x in uid_l:
        try:
            info = iposonic.db.get_songs(query={'scrobbleId': x})
            assert info
            print "found song: %s" % x
        except:
            print "not found: %s" % x


@SkipTest
def test_inotify_mysql():
    music_folders = [os.path.join("/", u"/opt/music/")]
    iposonic = Iposonic(music_folders,
                        dbhandler=MySQLIposonicDB,
                        recreate_db=True,
                        tmp_dir="/tmp/iposonic")
    iposonic.db.init_db()

    watch_music_folder(iposonic)

    print ("songs: %s" % iposonic.get_songs())
    print ("artists: %s" % iposonic.get_artists())
    print ("albums: %s" % iposonic.get_albums())

    iposonic.db.end_db()
