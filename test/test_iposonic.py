from nose import *

import os
from os.path import join

from harnesses import harn_setup, harn_load_fs2

from iposonic import Iposonic

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
#
# Test configuration
#
tmp_dir = "/tmp/iposonic/"


class TestIposonic:
    """Test queries on in-memory data store."""
    # Run the harnesses
    id_songs = []
    id_artists = []
    id_albums = []

    def setup(self):
        log.info("Setup************")
        self.test_dir = os.getcwd() + "/test/data/"
        self.iposonic = Iposonic([self.test_dir])
        self.db = self.iposonic.db
        harn_load_fs2(self)
        assert self.iposonic.db.albums
        assert self.iposonic.db.songs

    def teardown(self):
        self.iposonic = None


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

    def test_starred(self):
        eid = self.iposonic.get_songs()[0].get('id')
        print "songs: %s" % self.iposonic.get_songs()[0]
        self.iposonic.update_entry(eid, {'starred': '12 12 23'})
        print self.iposonic.get_songs(eid=eid)
        ret = self.iposonic.get_starred()
        assert ret, "Missing ret. %s" % ret
        assert '12 12 23' in [x.get('starred') for x in ret['title']
                              ], "Missing starred. %s" % ret['title']
        print "ret: %s" % ret

#
# Test DB
#
