from nose import *

import sys
import os
import re
from os.path import join, dirname
from iposonic import Iposonic, MediaManager, IposonicDB
from iposonicdb import SqliteIposonicDB

from test_iposonic import TestIposonicDB


class TestSqliteIposonicDB(TestIposonicDB):
    dbhandler = SqliteIposonicDB

    def _setup(self):
        self.id_songs = []
        self.id_artists = []
        self.id_albums = []

        self.test_dir = os.getcwd() + "/test/data/"
        self.db = self.dbhandler([self.test_dir], dbfile="mock_iposonic")
        self.db.reset()
        self.db.add_entry("/tmp/")

    def teardown(self):
        print "closing server"
        self.db.end_db()
        pass  # os.unlink("meta.db")

    def test_get_songs(self):
        path = join(self.test_dir, "mock_artist/mock_album/sample.ogg")
        self.db.add_entry(path)

        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        print "ret_execute: %s" % ret

        ret = self.db.get_songs()
        assert ret, "ret_get_songs: %s" % ret

    def test_get_songs_by_parent(self):
        path = join(self.test_dir, "mock_artist/mock_album/sample.ogg")
        self.db.add_entry(path)

        parent = MediaManager.get_entry_id(dirname(path))
        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        print "ret_execute: %s" % ret
        assert parent in [x.parent for x in ret], ret

        ret = self.db.get_songs(query={'parent': parent})
        assert ret, "ret_get_songs: %s" % ret

    def test_get_songs_with_select(self):
        self.db.add_entry(self.test_dir + "mock_artist/mock_album/sample.ogg")
        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        assert ret, "ret: %s" % ret

    def test_merge(self):
        session = self.db.Session()
        record = session.query(self.db.Artist).filter_by(id="-1525717793")
        eid = record.one().id
        record.update({'userRating': 5})
        session.commit()
        dup = session.query(self.db.Artist).filter_by(id=eid).one()
        assert dup.userRating == '5', "dup: %s" % dup

    def test_add(self):
        path = "./test/data/Aretha Franklin/20 Greatest hits/Angel.mp3"
        eid = self.db.add_entry(path)
        info_old = MediaManager.get_info(path)
        info = self.db.get_songs(eid=eid)

        assert info['title'], "ori: %s, saved: %s" % (info_old, info)
        assert info.get('bitRate'), "ori: %s, saved: %s" % (info_old, info)
        print info


class TestMySQLIposonicDB(TestSqliteIposonicDB):
    pass
