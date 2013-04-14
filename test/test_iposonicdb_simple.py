from __future__ import unicode_literals
from nose import SkipTest
from harnesses import harn_setup_dbhandler_and_scan_directory, harn_scan_music_directory
import os
from os.path import join

from iposonic import IposonicDB
from iposonicdb import SqliteIposonicDB
from mediamanager import MediaManager

from logging import getLogger
log = getLogger(__name__)
#
# Test configuration
#
tmp_dir = "/tmp/iposonic/"


class TestIposonicDB:
    dbhandler = IposonicDB
    # Run the harnesses
    id_songs = []
    id_artists = []
    id_albums = []
    dbfile = ""
    def setup(self):
        harn_setup_dbhandler_and_scan_directory(self, "/test/data", add_songs=False, dbfile=self.dbfile)
        harn_scan_music_directory(self)
        #self.db.add_path("/tmp/")

    def _harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = self.test_dir
        self.id_l = []

        for f in os.listdir(root):
            path = join("/", root, f)
            eid = self.db.add_path(path)
            self.id_l.append(eid)

    def test_get_music_folders(self):
        assert self.db.get_music_folders()

    @SkipTest
    def test_get_albums(self):
        raise NotImplemented

    def test_get_songs(self):
        songs = self.db.get_songs()
        assert songs
        for s in songs:
            assert 'title' in s, "Missing title in song: %s" % s

    def test_update_entry_artist(self):
        ret = self.db.get_artists()
        assert ret and ret[0], "Missing artists"
        eid = ret[0].get('id')
        assert eid, "Missing eid in item %r" % ret
        log.info("eid record: %r" % eid)
        self.db.update_entry(eid, {'userRating': 5})
        ret = self.db.get_artists(eid=eid)
        assert int(ret.get('userRating')) == 5, "Value was: %s" % ret

    def test_get_artists(self):
        ret = self.db.get_artists()
        assert ret, "No artists in the DB"
        # name is a required field for an artist
        for artist in ret:
            log.info("artist: %r with id %r" % (artist, artist.get('id')))
            assert artist.get('name'), "Bad music_directories: %s" % artist

    def test_search_songs_by_artist(self):
        harn_scan_music_directory(self)
        ret = self.db.get_songs(query={'artist': 'mock_artist'})
        assert ret[0]['title'], ret

    def test_get_song_by_id(self):
        #self.harn_load_fs()
        harn_scan_music_directory(self)
        assert self.id_songs, "Empty id_songs: %s" % self.id_songs
        for eid in self.id_songs:
            info = self.db.get_songs(eid=eid)
            assert 'path' in info, "error processing eid: %s" % eid
            assert 'created' in info, "missing created in %s" % info

    def test_search_songs_by_title(self):
        harn_scan_music_directory(self)
        ret = self.db.get_songs(query={'title': 'mock_title'})
        info = ret[0]
        assert info['title'], ret
        assert info.get('bitRate'), ret
        print info

    def test_get_indexes(self):
        print self.db.get_indexes()         

    def test__search(self):
        artists = {'-1408122649': {'isDir': 'true', 'path': '/opt/music/mock_artist', 'name': 'mock_artist', 'id': '-1408122649'}}
        ret = IposonicDB._search(artists, {'name': 'mock_artist'})
        assert '-1408122649' in ret[0].get(
            'id'), "Expected %s got %s" % ('-1408122649', ret)

    def test_highest(self):
        ret = self.db.get_highest()
        assert ret, "Missing ret. %s" % ret
        print "ret: %s" % ret

    def test_latest(self):
        album = self.db.add_path(os.getcwd(
        ) + '/test/data/mock_artist/mock_album/', album=True)
        ret = self.db.get_albums()
        assert ret, "Missing ret. %s" % ret
        print "ret: %s" % ret
