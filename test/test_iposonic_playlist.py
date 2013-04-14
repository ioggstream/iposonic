from __future__ import unicode_literals
from nose import with_setup
from iposonicdb import SqliteIposonicDB, MySQLIposonicDB
from harnesses import harn_setup_dbhandler_and_scan_directory,    harn_scan_music_directory
from test_iposonic import tmp_dir
from mediamanager import MediaManager
from iposonic import EntryNotFoundException

import logging
logging.basicConfig(level=logging.DEBUG)

class TestPlaylistIposonicDB:
    dbhandler = MySQLIposonicDB
    # Harness
    id_songs = []
    id_artists = []
    id_albums = []

    def setup_playlist(self):
        item = self.db.Playlist("mock_playlist")
        songs = ",".join([str(x.get('id')) for x in self.db.get_songs()])
        item.update({'entry': songs})

        # use session directly to avoid testing our methods with other methods
        session = self.db.Session()
        session.merge(item)
        session.commit()
        session.close()

    def setup(self):
        harn_setup_dbhandler_and_scan_directory(self, "/test/data")
        harn_scan_music_directory(self)

        self.setup_playlist()
        
    def teardown(self):
        self.db.end_db()

    def test_get_playlists(self):
        items = self.db.get_playlists()
        item = items[0]
        assert item.get('name') == 'mock_playlist', "No playlists: %s" % item

    def test_get_playlist(self):
        eid = MediaManager.uuid('mock_playlist')
        ret = self.db.get_playlists(eid=eid)
        assert ret, "Can't find playlist %s" % eid
        assert ret.get('name') == 'mock_playlist', "No playlists: %s" % ret


class TestUserIposonicDB:
    dbhandler = MySQLIposonicDB
    # Harness
    id_songs = []
    id_artists = []
    id_albums = []

    def setup_user(self):
        session = self.db.Session()
        print ("setting up users...")
        for unames in ["mock_user%s" % s for s in ['', 1, 2, 3]]:
            item = self.db.User(unames)
            item.update({
                'password': 'mock_password',
                'scrobbleUser': 'ioggstream',
                'scrobblePassword': 'secret'
            })
            print ("setting up user...%s", item)

            session.merge(item)
        session.commit()
        session.close()

    def setup(self):
        harn_setup_dbhandler_and_scan_directory(self, tmp_dir, add_songs=False)
        self.setup_user()

    def teardown(self):
        self.db.end_db()
    #
    # Tests
    #
    def test_get_users(self):
        items = self.db.get_users()
        print  items
        item = items[0]
        assert item.get('username') == 'mock_user', "No users: %s" % item

    #@with_setup([setup, setup_user])
    def test_add_remove_user(self):
        u = {
            'username': 'mock_user',
            'password': 'mock_password',
            'scrobbleUser': 'ioggstream',
            'scrobblePassword': 'secret'
        }
        eid = self.db.add_user(u)
        assert eid, "Item not working"
        print ("retrieving item with id: %s" % eid)
        t = self.db.get_users(eid=eid)
        assert 'username' in t, "Created %s" % t

        self.db.delete_user(eid=eid)
        try:
            t = self.db.get_users(eid=eid)
            assert False, "can't find user"
        except EntryNotFoundException:
            pass

    def test_get_user(self):
        eid = MediaManager.uuid('mock_user')
        ret = self.db.get_users(eid)
        assert ret, "Can't find user %s" % eid
        assert ret.get('username') == 'mock_user', "No user: %s" % ret
