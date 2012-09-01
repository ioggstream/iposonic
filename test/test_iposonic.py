from nose import *

import sys, os, re
from os.path import join
from iposonic import Iposonic, MediaManager, IposonicDB
from iposonicdb import SqliteIposonicDB

class TestIposonic:
    def setup(self):
        self.test_dir = os.getcwd()+"/test/data/"
        self.iposonic =  Iposonic([self.test_dir])
        self.iposonic.db.walk_music_directory()
        self.harn_load_fs2()
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
            path = join("/",root,f)
            eid = self.iposonic.add_entry(path)
            self.id_l.append(eid)


        
    def test_search_artists_by_name(self):
        ret = self.iposonic.db.get_artists(query={'name':'mock_artist'})
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
        for x in ['album','title','artist']:
            assert ret[x], "Missing %s in %s" % (x, ret)

    def test_genre_songs(self):
        ret = self.iposonic.get_genre_songs("mock_genre")
        assert ret
        for x in ret:
            assert x['genre'] == "mock_genre"

    def test_directory_get(self):
        try:
            dirs = self.iposonic.db.get_artists()
            assert dirs.keys() , "empty artists %s" % dirs
            k=dirs.keys()[0]
            (id_1,dir_1) = (k, dirs[k])
            print self.db.get_directory_path_by_id(id_1)
        except:
            raise Exception("Can't find entry %s in %s" % (id_1, self.iposonic.db.get_artists()))



   
class TestIposonicDB:
    dbhandler = IposonicDB
    def setup(self):
        self.id_songs = []
        self.id_artists = []
        self.id_albums = []

        self.test_dir = os.getcwd()+"/test/data/"
        self.db = self.dbhandler([self.test_dir])
        self.db.walk_music_directory()

    def test_get_music_folders(self):
        assert self.db.get_music_folders()
    @SkipTest
    def test_get_indexes(self):
        raise NotImplemented
    @SkipTest
    def test_get_artists(self):
        raise NotImplemented
    @SkipTest
    def test_get_albums(self):
        raise NotImplemented
    def test_get_songs(self):
        songs = self.db.get_songs()
        assert songs
        for s in songs:
            assert s.title , "Missing title in song: %s" % s
        
    def harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = self.test_dir
        self.id_l = []

        for f in os.listdir(root):
            path = join("/",root,f)
            eid = self.db.add_entry(path)
            self.id_l.append(eid)

    def harn_load_fs2(self):
        for (root, dirfile, files) in os.walk(self.test_dir):
            for d in dirfile:
                path = join("/", root, d)
                seld.id_albums.append(self.db.add_entry(path))
            for f in files:
                path = join("/", root, f)
                self.id_songs.append(self.db.add_entry(path))


    def test_get_artists(self):
        ret = self.db.get_artists()
        assert ret
        for (eid,info) in ret.iteritems():
            assert 'name' in info, "Bad music_directories: %s" % ret
      
    def test_search_songs_by_artist(self):
        self.harn_load_fs2()
        ret = self.db.get_songs(query={'artist':'mock_artist'})
        assert ret[0]['title'], ret

    def test_get_song_by_id(self):
        self.harn_load_fs()
        assert self.id_l, "Empty id_l: %s" % id_l
        for eid in self.id_songs:
              info = self.db.get_songs(eid=eid)
              assert 'path'  in info,  "error processing eid: %s" % eid

        
    def test_search_songs_by_title(self):
        self.harn_load_fs2()
        ret = self.db.get_songs(query={'title':'mock_title'})
        assert ret[0]['title'], ret
          
    def test_walk_music_directory(self):
        print self.db.walk_music_directory()

    def test_get_indexes(self):
        print self.db.get_indexes()

    def test__search(self):
        artists = {'-1408122649': {'isDir': 'true', 'path': '/opt/music/mock_artist', 'name': 'mock_artist', 'id': '-1408122649'} }
        ret = IposonicDB._search(artists, {'name': 'mock_artist'})
        assert '-1408122649' in ret[0].get('id'), "Expected %s got %s" % ('-1408122649', ret)

class TestIposonicSqliteDB(TestIposonicDB):
    dbhandler = SqliteIposonicDB
    def setup(self):
        self.id_songs = []
        self.id_artists = []
        self.id_albums = []

        self.test_dir = os.getcwd()+"/test/data/"
        self.db = self.dbhandler([self.test_dir])
        self.db.reset()
    def teardown(self):
        pass #os.unlink("meta.db")
    def test_get_songs(self):
        self.db.add_entry(self.test_dir + "mock_artist/mock_album/sample.ogg")

        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        print "ret_execute: %s" % ret

        ret = self.db.get_songs()
        assert ret, "ret_get_songs: %s" % ret
    def test_get_songs_with_select(self):
        self.db.add_entry(self.test_dir + "mock_artist/mock_album/sample.ogg")
        l_session = self.db.Session()
        ret = l_session.execute("select * from song;").fetchall()
        assert ret, "ret: %s" % ret
