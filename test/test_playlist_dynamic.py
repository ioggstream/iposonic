from __future__ import unicode_literals
from nose import *
from iposonic import Iposonic
from datamanager.mysql import MySQLIposonicDB
from mediamanager.scrobble import get_similar
import os
import time
from scanner import walk_music_folder, watch_music_folder
from mediamanager import MediaManager

iposonic_app = None
music_folders = [os.path.join("/", u"/opt/music/")]
 
def setup():
    global iposonic_app
    iposonic_app = Iposonic(music_folders,
                        dbhandler=MySQLIposonicDB,
                        recreate_db=True,
                        tmp_dir="/tmp/iposonic")
    
def test_scanner_mysql():
    iposonic_app.db.init_db()

    # as we're in a test, don't walk forever
    # just end and check
    walk_music_folder(iposonic_app, forever=False)

    print ("songs: %s" % iposonic_app.get_songs())
    print ("artists: %s" % iposonic_app.get_artists())
    print ("albums: %s" % iposonic_app.get_albums())

#    iposonic_app.db.end_db()


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
            info = iposonic_app.db.get_songs(query={'scrobbleId': x})
            assert info
            print "found song: %s" % x
        except:
            print "not found: %s" % x


@SkipTest
def test_inotify_mysql():
    music_folders = [os.path.join("/", u"/opt/music/")]
    iposonic_app = Iposonic(music_folders,
                        dbhandler=MySQLIposonicDB,
                        recreate_db=True,
                        tmp_dir="/tmp/iposonic")
    iposonic_app.db.init_db()

    watch_music_folder(iposonic_app)

    print ("songs: %s" % iposonic_app.get_songs())
    print ("artists: %s" % iposonic_app.get_artists())
    print ("albums: %s" % iposonic_app.get_albums())

    iposonic_app.db.end_db()
