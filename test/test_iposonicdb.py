from __future__ import unicode_literals

from nose import *

import sys
import os
import re
from os.path import join, dirname
from iposonic import Iposonic, MediaManager, IposonicDB
from iposonicdb import SqliteIposonicDB, MySQLIposonicDB

from test_iposonicdb_simple import TestIposonicDB


class TestSqliteIposonicDB(TestIposonicDB):
    dbhandler = SqliteIposonicDB

    def _setup(self):
        self.id_songs = []
        self.id_artists = []
        self.id_albums = []

        self.test_dir = os.getcwd() + "/test/data/"
        self.db = self.dbhandler([self.test_dir], dbfile="mock_iposonic")
        self.db.init_db()
        self.db.reset()
        self.db.add_path("/tmp/")

    def teardown(self):
        print "closing server"
        self.db.end_db()
        pass  # os.unlink("meta.db")

    def test_get_songs(self):
        path = join(self.test_dir, "mock_artist/mock_album/sample.ogg")
        self.db.add_path(path)

        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        print "ret_execute: %s" % ret

        ret = self.db.get_songs()
        assert ret, "ret_get_songs: %s" % ret

    def test_get_songs_by_parent(self):
        path = join(self.test_dir, "mock_artist/mock_album/sample.ogg")
        self.db.add_path(path)

        parent = MediaManager.uuid(dirname(path))
        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        print "ret_execute: %s" % ret
        assert parent in [x.parent for x in ret], ret

        ret = self.db.get_songs(query={'parent': parent})
        assert ret, "ret_get_songs: %s" % ret

    def test_get_songs_with_select(self):
        self.db.add_path(self.test_dir + "/mock_artist/mock_album/sample.ogg")
        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        assert ret, "ret: %s" % ret

    def test_merge(self):
        # create a mock entry
        session = self.db.Session()
        path = join(self.test_dir, "mock_artist")
        mock_id = self.db.add_path(path)
        assert  mock_id, "No artists: %s " % mock_id
        record = session.query(self.db.Artist).filter_by(id=mock_id)#"-1525717793"
        assert record, "Can't find mock Artist with predefined id. Fix test code!"
        eid = record.one().id
        
        # update it
        record.update({'userRating': 5})
        session.commit()
        
        # check if updated
        dup = session.query(self.db.Artist).filter_by(id=eid).one()
        assert dup.userRating == '5', "dup: %s" % dup

    def test_add(self):
        path = "./test/data/Aretha Franklin/20 Greatest hits/Angel.mp3"
        eid = self.db.add_path(path)
        info_old = MediaManager.get_info(path)
        info = self.db.get_songs(eid=eid)

        assert info['title'], "ori: %s, saved: %s" % (info_old, info)
        assert info.get('bitRate'), "ori: %s, saved: %s" % (info_old, info)
        exit
        print info


class TestMySQLIposonicDB(TestSqliteIposonicDB):
    dbhandler = MySQLIposonicDB
    pass
