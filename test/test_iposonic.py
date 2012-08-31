from nose import *

import sys, os, re
from os.path import join
from iposonic import Iposonic, MediaManager

class TestIposonic:
    def setup(self):
        self.test_dir = os.getcwd()+"/test/data/"
        self.iposonic =  Iposonic([self.test_dir])

    def teardown(self):
        self.iposonic = None

    def harn_load_fs2(self):
        for (root, dirfile, files) in os.walk(self.test_dir):
            for d in dirfile:
                path = join("/", root, d)
                self.iposonic.add_entry(path)
            for f in files:
                path = join("/", root, f)
                self.iposonic.add_entry(path)

    def harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = self.test_dir
        self.id_l = []

        for f in os.listdir(root):
            path = join("/",root,f)
            eid = self.iposonic.add_entry(path)
            self.id_l.append(eid)


    def test_get_artists(self):
        ret = self.iposonic.get_artists()
        assert ret
        for (eid,info) in ret.iteritems():
            assert 'name' in info, "Bad music_directories: %s" % ret

    def test_get_song_by_id(self):
        """Retrieve added songs info and path by id """
        self.harn_load_fs()

        for eid in self.id_l:
            try:
              info = self.iposonic.get_song_by_id(eid)
              assert 'path'  in info
            except:
              print "error processing eid: %s" % eid
        self.harn_load_fs()
        
    def test_search_songs_1(self):
        """Search added songs for title, return songs"""
        self.iposonic.db.walk_music_directory()
        self.harn_load_fs2()
        ret = self.iposonic._search_songs(re_query=re.compile(".*mock_title.*"))
        assert ret['title'], ret
        
    def test_search_songs_2(self):
        """Search added songs for artist, return song"""
        self.iposonic.db.walk_music_directory()
        self.harn_load_fs2()
        ret = self.iposonic._search_songs(re_query=re.compile(".*mock_artist.*"))
        assert ret['title'], ret
        
    def test_search_artists_1(self):
        """Search artist folders, return artists"""
        self.iposonic.db.walk_music_directory()
        self.harn_load_fs2()
        ret = self.iposonic._search_artists(re_query=re.compile(".*mock_artist.*"))
        assert ret['artist'], ret

    def test_search2_0(self):
        """Search everything, return artist and title (existing artist folder).

          TODO actually search songs and artists folders"""
        self.harn_load_fs2()
        ret = self.iposonic.search2(query="mock_artist")
        assert ret['artist'], "Missing artist in %s" % ret
        assert ret['title'], "Missing title in %s" % ret

    @SkipTest
    def test_search2_1(self):
        """Search everything, return artist (unexisting artist folder).

            SkipTest: a search in songs won't return an album
            you must search in folders
          """
        self.harn_load_fs2()
        ret = self.iposonic.search2(query="Lara")
        assert ret['artist'], "Missing artist in %s" % ret

    @SkipTest 
    def test_search2_2(self):
        """Search everything, return album.

          SkipTest: a search in songs won't return an album
            you must search in folders
        """
        self.harn_load_fs()
        ret = self.iposonic.search2(query="Bach")
        assert ret['album'], "Missing album in %s" % ret
        
    def test_search2_3(self):
        """Search everything, return artist in folders"""
        self.iposonic.db.walk_music_directory()
        ret = self.iposonic.search2(query="mock_artist")
        assert ret['artist'], "Missing artist in %s" % ret

    @SkipTest
    def test_search2_4(self):
        """Search everything, return everything.

        SkipTest: won't return anquery pattern used in this test will return just songs!
            not  albums, not artists
            you must search in folders
        """
        self.harn_load_fs()
        ret = self.iposonic.search2(query="magnatune")
        for x in ['album','title','artist']:
            assert ret[x], "Missing %s in %s" % (x, ret)

    def test_genre_songs(self):
        self.harn_load_fs2()
        ret = self.iposonic.get_genre_songs("mock_genre")
        assert ret
        for x in ret:
            assert x['genre'] == "mock_genre"

    def test_directory_get(self):
        self.iposonic.db.walk_music_directory()
        try:
            dirs = self.iposonic.db.get_artists()
            assert dirs.keys() , "empty artists %s" % dirs
            k=dirs.keys()[0]
            (id_1,dir_1) = (k, dirs[k])
            print self.iposonic.get_directory_path_by_id(id_1)
        except:
            raise Exception("Can't find entry %s in %s" % (id_1, self.iposonic.db.get_artists()))

    def test_walk_music_directory(self):
        print self.iposonic.db.walk_music_directory()

    def test_get_indexes(self):
        self.iposonic.db.walk_music_directory()
        print self.iposonic.db.get_indexes()
