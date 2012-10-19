from __future__ import unicode_literals
from nose import *
from iposonic import Iposonic
from iposonicdb import MySQLIposonicDB
import os
from scanner import walk_music_folder, watch_music_folder

def test_scanner_mysql():
    music_folders = [os.path.join("/",u"/opt/music/")]
    iposonic = Iposonic(music_folders, 
                        dbhandler=MySQLIposonicDB, 
                        recreate_db=True,
                         tmp_dir="/tmp/iposonic")
    iposonic.db.init_db()
    
    walk_music_folder(iposonic)
    
    print ("songs: %s" % iposonic.get_songs())
    print ("artists: %s" % iposonic.get_artists())
    print ("albums: %s" % iposonic.get_albums())

    iposonic.db.end_db()

def test_inotify_mysql():
    music_folders = [os.path.join("/",u"/opt/music/")]
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

