# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3
from __future__ import unicode_literals
from test_iposonic import tmp_dir
from logging import getLogger
from harnesses import harn_setup_dbhandler_and_scan_directory
from harnesses import harn_scan_music_directory
from harnesses import harn_create_users
log = getLogger(__name__)


from exc import IposonicException
import simplejson

from iposonic import Iposonic
from urllib import urlencode
from webapp import app, Dbh
import view.db
import view.user
from authorizer import Authorizer

class TestView:
    request_stub = {'u':'u', 'p': 'p', 'id': None, 'f': 'json'}
    def setup(self):
        app.authorizer = Authorizer(mock=True, access_file=None)
        app.iposonic = Iposonic(['/opt/music'], dbhandler=Dbh,
                                recreate_db=True, tmp_dir=tmp_dir)
        try:
            harn_scan_music_directory(app.iposonic)
        except IposonicException:
            pass
        harn_create_users(app.iposonic)
        
        self.songs = app.iposonic.get_songs()
        self.artists = app.iposonic.get_artists()
        self.users = app.iposonic.get_users()   
        assert self.songs,"no songs %r" % self.songs
        assert self.users,"no users %r" % self.users
        assert self.artists,"no artists %r" % self.artists

        self.client = app.test_client()
        
    def teardown(self):
        app.iposonic.db.end_db()
        
    def harn_db_get(self, view, nid):        
        self.request_stub.update({
                                  'id': nid
                                  })
        res = self.client.get('/rest/'+view+'.view?'+ urlencode(self.request_stub))
        info = simplejson.loads(res.data)['subsonic-response']
        assert info
        log.debug("response: %r" % res.data)
        return info
        
    def test_db_song(self):
        nid = self.songs[0]['id']
        info = self.harn_db_get('db', nid)
        assert info['id'] == nid
        
    def test_view_get_user(self):
        nid = self.users[0]['id']
        log.info("searching for uid %r" % nid)
        info = self.harn_db_get('getUsers', nid)
        assert info['users'] ['user'] ['id'] == nid, "error with item: %r" % info
        
        
    def test_view_set_now_playing(self):
        nid, song_id  = map (lambda x: x[0]['id'], [self.users, self.songs])
        username = self.users[0]['username']
        assert nid and song_id
        log.info("searching for uid %r, songid: %r" % (nid, song_id))
        ret = self.client.get('/rest/setNowPlaying.view?' + urlencode({
                                                        'u': username, 
                                                        'id': song_id
        }))
        info =  self.harn_db_get('getUsers', nid)
        assert info['users'] ['user'] ['nowPlaying'] == str(song_id), "error with item: %r vs %r" %( info, song_id)
        
    def test_view_update_user(self):
        nid, song_id  = map (lambda x: x[0]['id'], [self.users, self.songs])
        assert nid and song_id
        log.info("searching for uid %r, songid: %r" % (nid, song_id))
        ret = self.client.get('/rest/updateUser.view?' + urlencode({
                                                        'id': nid, 
                                                        'nowPlaying': song_id
        }))
        info =  self.harn_db_get('getUsers', nid)
        assert info['users'] ['user'] ['nowPlaying'] == str(song_id), "error with item: %r vs %r" %( info, song_id)
 