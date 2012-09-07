from nose import *

import sys
import os
import re
from os.path import join
from iposonic import Iposonic, MediaManager, IposonicDB
from iposonicdb import SqliteIposonicDB


class TestIposonic:
    def setup(self):
        self.test_dir = os.getcwd() + "/test/data/"
        self.iposonic = Iposonic([self.test_dir])
        self.iposonic.db.walk_music_directory()
        harn_load_fs2(self)

    def teardown(self):
        self.iposonic = None

    def harn_load_fs2(self):
        for (root, dirfile, files) in os.walk(self.test_dir):
            ret = dirfile
            ret.extend(files)
            for p in ret:
                path = join("/", root, p)
                self.iposonic.db.add_entry(path)

    def harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = self.test_dir
        self.id_l = []

        for f in os.listdir(root):
            path = join("/", root, f)
            eid = self.iposonic.add_entry(path)
            self.id_l.append(eid)

    def test_search_artists_by_name(self):
        ret = self.iposonic.db.get_artists(query={'name': 'mock_artist'})
        assert ret[0].get('name'), "ret: %s" % ret

    def test_search2_and_get_artist_and_title(self):
        ret = self.iposonic.search2("mock_artist")
        assert 'artist' in ret, "Missing artist in %s" % ret
        assert 'title' in ret, "Missing title in %s" % ret

    @SkipTest
    def test_search2_and_get_artist(self):
        """Search everything, return artist (unexisting artist folder).

            SkipTest: a search in songs won't return an album
            you must search in folders
          """
        ret = self.iposonic.search2(query="Lara")
        assert ret['artist'], "Missing artist in %s" % ret

    @SkipTest
    def test_search2_2(self):
        """Search everything, return album.

          SkipTest: a search in songs won't return an album
            you must search in folders
        """
        ret = self.iposonic.search2(query="Bach")
        assert ret['album'], "Missing album in %s" % ret

    def test_search2_and_get_artist_mock(self):
        ret = self.iposonic.search2(query="mock_artist")
        assert 'artist' in ret, "Missing artist in %s" % ret

    @SkipTest
    def test_search2_4(self):
        """Search everything, return everything.

        SkipTest: won't return anquery pattern used in this test will return just songs!
            not  albums, not artists
            you must search in folders
        """
        ret = self.iposonic.search2(query="magnatune")
        for x in ['album', 'title', 'artist']:
            assert ret[x], "Missing %s in %s" % (x, ret)

    def test_genre_songs(self):
        ret = self.iposonic.get_genre_songs("mock_genre")
        assert ret
        for x in ret:
            assert x['genre'] == "mock_genre"

    def test_directory_get(self):
        dirs = self.iposonic.db.get_artists()
        assert dirs, "empty artists %s" % dirs
        artist = dirs[0]
        eid = artist['id']
        assert artist
        assert artist['path'] == self.iposonic.get_directory_path_by_id(eid)[0], "Can't find entry %s in %s" % (
                eid, dirs)

def harn_setup(klass, test_dir):
        klass.test_dir = os.getcwd() + test_dir
        klass.db = klass.dbhandler([klass.test_dir], dbfile = "mock_iposonic")
        klass.db.reset()

        klass.db.walk_music_directory()

        # Run the harnesses
        klass.id_songs = []
        klass.id_artists = []
        klass.id_albums = []
def harn_load_fs2(klass):
    for (root, dirfile, files) in os.walk(klass.test_dir):
        for d in dirfile:
            path = join("/", root, d)
            klass.id_albums.append(klass.db.add_entry(path))
        for f in files:
            path = join("/", root, f)
            klass.id_songs.append(klass.db.add_entry(path))



class TestIposonicDB:
    dbhandler = IposonicDB

    def setup(self):
        harn_setup(self, "/test/data")
        klass.harn_load_fs2()
        klass.db.add_entry("/tmp/")

    def harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = self.test_dir
        self.id_l = []

        for f in os.listdir(root):
            path = join("/", root, f)
            eid = self.db.add_entry(path)
            self.id_l.append(eid)

    def test_get_music_folders(self):
        assert self.db.get_music_folders()

    @SkipTest
    def test_get_indexes(self):
        raise NotImplemented

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
        assert ret and ret[0]
        eid = ret[0].get('id')
        print "test_update_entry: record: %s" % eid
        self.db.update_entry(eid, {'rating': 5})
        ret = self.db.get_artists(eid=eid)
        assert ret.get('rating') == '5', "Value was: %s" % ret

    def test_merge(self):
        session = self.db.Session()
        record = session.query(self.db.Artist).filter_by(id="-1525717793")
        eid = record.one().id
        record.update({'rating': 5})
        """
        print "retrieved: %s" % record
        record.update({'rating':5})
        print "merging: %s " % record
        session.merge(record)
        session.flush()
        """
        session.commit()
        dup = session.query(self.db.Artist).filter_by(id=eid).one()
        assert dup.rating == '5', "dup: %s" % dup

    def test_get_artists(self):
        ret = self.db.get_artists()
        assert ret
        for artist in ret:
            assert 'name' in artist, "Bad music_directories: %s" % ret

    def test_search_songs_by_artist(self):
        harn_load_fs2(self)
        ret = self.db.get_songs(query={'artist': 'mock_artist'})
        assert ret[0]['title'], ret

    def test_get_song_by_id(self):
        self.harn_load_fs()
        assert self.id_l, "Empty id_l: %s" % id_l
        for eid in self.id_songs:
            info = self.db.get_songs(eid=eid)
            assert 'path' in info, "error processing eid: %s" % eid

    def test_search_songs_by_title(self):
        harn_load_fs2(self)
        ret = self.db.get_songs(query={'title': 'mock_title'})
        assert ret[0]['title'], ret

    def test_walk_music_directory(self):
        print self.db.walk_music_directory()

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

    
class TestPlaylistIposonicDB:
    dbhandler = SqliteIposonicDB

    def setup_playlist(self):
        item = self.db.Playlist("mock_playlist")
        songs = str.join(",",[str(x.get('id')) for x in self.db.get_songs()])
        item.update({'entry': songs})
        
        session = self.db.Session()
        session.add(item)
        session.commit()
        session.close()
        
    def setup(self):
        harn_setup(self, "/test/data")
        harn_load_fs2(self)
        
        self.setup_playlist()
        
        
    def test_get_playlists(self):
        items = self.db.get_playlists()
        item = items[0]
        assert item.get('name') == 'mock_playlist' , "No playlists: %s" % item
        
    def test_get_playlist(self):
        eid = MediaManager.get_entry_id('mock_playlist')
        ret = self.db.get_playlists(eid=eid)
        assert ret, "Can't find playlist %s" % eid
        assert ret.get('name') == 'mock_playlist' , "No playlists: %s" % ret
