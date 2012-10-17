from __future__ import unicode_literals
from nose import *
from iposonic import Iposonic
from iposonicdb import MySQLIposonicDB

from scanner import walk_music_folder

def test_scanner_mysql():
    music_folders = [u"/opt/music"]
    iposonic = Iposonic(music_folders, 
                        dbhandler=MySQLIposonicDB, 
                        recreate_db=True,
                         tmp_dir="/tmp/iposonic")
    iposonic.db.init_db()
    
    walk_music_folder(iposonic)