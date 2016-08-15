#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# author:   Roberto Polli (c) 2012
# license:  AGPL v3
#
# Subsonic is an opensource streaming server www.subsonic.org
#  as I love python and I don't want to install an application
#  server for listening music, I wrote IpoSonic
#
# IpoSonic does not have a web interface, like of the original subsonic server
#   and does not support transcoding (but it could in the future)
#
from __future__ import unicode_literals


# standard libs
import os
import re
from os.path import join, basename, dirname
from operator import itemgetter
#
# manage media files
#
# tags
from mediamanager import MediaManager
# logging and json
import logging
log = logging.getLogger('iposonic')

from datamanager.utils import jsonize
from exc import *

# The default data store
from datamanager.inmemory import MemoryIposonicDB


##
## The app ;)
##


#
# IpoSonic
#
class Iposonic(object):
    """Iposonic is a simple media server allowing to
        browse and stream music, managing playlists and
        cover arts.

        This is the core class.

        The initialization parameters are:
         - music_folders: a list of music directories
         - dbhandler: a database handler like the in-memory IposonicDB
                        or the included SQL backends (MySQL and Sqlite)
        - recreate_db: a handler for sql storages that delete the previous
                        copy of the db

        """
    log = logging.getLogger('Iposonic')

    def __init__(self, music_folders, dbhandler=MemoryIposonicDB, recreate_db=False, tmp_dir="/tmp/iposonic"):
        self.log.info("Creating Iposonic with music folders: %r, dbhandler: %r" %
                      (music_folders, dbhandler))

        # set directory
        self.tmp_dir = tmp_dir
        self.cache_dir = join("/", tmp_dir, "_cache")

        # eventually create missing directories
        #   or die
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.db = dbhandler(
            music_folders, recreate_db=recreate_db, datadir=tmp_dir)
        self.log.setLevel(logging.WARN)



    def __getattr__(self, method):
        """Proxies DB methods."""
        if method in [
            'music_folders',
            'add_path',
            #'get_artists',
            'get_albums',
            'get_song_list',
            'get_music_folders',
            'get_highest',
            'get_playlists',
            'delete_entry',
            # User management
            'get_users'

        ]:
            dbmethod = self.db.__class__.__getattribute__(self.db, method)
            return dbmethod

        return object.__getattribute__(self, method)

        #    raise NotImplementedError("Method not found: %s" % method, e)

     #@jsonize
    def get_artists(self, *args, **kwds):
        """Render artists in a webapp-able way."""
        return  self.db.get_artists(*args, **kwds)

    def get_folder_by_id(self, folder_id):
        """It's ok just because self.db.get_music_folders() are few"""
        for folder in self.db.get_music_folders():
            if MediaManager.uuid(folder) == folder_id:
                return folder
        raise IposonicException("Missing music folder with id: %s" % folder_id)

    def get_entry_by_id(self, eid):
        ret = None
        for f in [self.get_artists, self.get_albums, self.get_songs]:
            self.log.info("try to retrieve entry with %r" % f)
            try:
                ret = f(eid)
            except EntryNotFoundException:
                pass
            if ret:
                return ret
        raise IposonicException("Missing entry with id: %s " % eid)

    def get_directory_path_by_id(self, eid):
        """TODO return a single path"""
        info = self.get_entry_by_id(eid)
        return (info['path'], info['path'])

    def get_indexes(self):
        """Return subsonic-formatted indexes.

        {'A':
        [{'artist':
            {'id': '517674445', 'name': 'Antonello Venditti'}
            },
            {'artist': {'id': '-87058509', 'name':
                'Anthony and the Johnsons'}},


             "indexes": {
              "index": [
               {    "name": "A",

                "artist": [
                 {
                  "id": "12345",
                  "name": "Abba"
                 },
                 {
                  "id": "67890",
                  "name": "Adele"
                 },

        """
        assert self.db.get_indexes()
        items = []
        for (name, artists) in self.db.get_indexes().iteritems():
            items.append(
                {'name': name, 'artist': [v['artist'] for v in sorted(artists, key=itemgetter('artist'))]})
        return {'index': items}

    #
    #   Create Update Delete
    #

    def add_path_(self, path, album=False):
        """Add imageart related stuff here."""
        return self.db.add_path(path, album)

    def delete_entry(self, path):
        raise NotImplementedError("deleting entry: %s" % path)

    def update_entry(self, eid, new):
        """TODO move do db"""
        return self.db.update_entry(eid, new)

    def create_entry(self, entry):
        return self.db.create_entry(entry)

    #
    # User stuff
    #
    def add_user(self, user):
        self.log.info("creating user: %r" % user)
        entry = self.db.User(user.get('username'))
        entry.update(user)
        return self.create_entry(entry)

    def update_user(self, eid, new):
        self.log.info("updating user: %r" % eid)
        entry = self.db.update_user(eid, new)
        return entry

    def delete_user(self, eid):
        self.log.info("delete user: %r" % eid)
        entry = self.db.delete_user(eid)
        return entry
    #
    # Retrieve
    #

    def get_songs(self, eid=None, query=None):
        """return one or more songs.

            if eid, return a single dict,
            if query, return a list of dict

            Parsing (eg. to add coverArt) should check the returned type.

            TODO: to fasten getCoverArt.view we should avoid in getting
                always different path for all the files in the same album
        """
        songs = self.db.get_songs(eid=eid, query=query)

        # add album coverArt to each song
        # XXX find a smart way to get coverArt
        if isinstance(songs, dict):
            songs.update({'coverArt': songs.get('id')})
            return songs

        return [x.update({'coverArt': x.get('id')}) or x for x in songs]

    def get_genre_songs(self, query):
        songs = []
        return self.db.get_songs(query={'genre': query})

    def search2(self, query, artistCount=10, albumCount=10, songCount=10):
        """Return items matching the query in their principal name.

            ex. (song.title | album.title | artist.name) ~ query

            return:
            {
                artist: [{}, .. ,{}]
                album: [{}, .. ,{}]
                song: [{}, .. ,{}]
            }
            TODO return song instead of title
        """
        # TODO merge them or use sets
        return {
            'artist': self.get_artists(query={'name': query}),
            'album': self.db.get_albums(query={'title': query}),
            'title': self.db.get_songs(query={'title': query})
        }

    def get_starred(self, artistCount=10, albumCount=10, songCount=10):
        """Return items matching the query in their principal name.

            ex. (song.title | album.title | artist.name) ~ query

            return:
            {
                artist: [{}, .. ,{}]
                album: [{}, .. ,{}]
                song: [{}, .. ,{}]
            }
        """
        query = {'starred': 'notNull'}
        return {
            'artist': self.db.get_artists(query=query),
            'album': self.db.get_albums(query=query),
            'title': self.db.get_songs(query=query)
        }

    def refresh(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        raise NotImplementedError("Reimplement this in the scanner thread")

    def get_playlists_static(self, eid=None):
        """Return a set of static playlists like random songs or by genre.

            Useful for clients that doesn't support advanced queries.
        """
        playlist_static = [self.db.Playlist(
            name).json() for name in ['sample', 'random', 'genre', 'starred']]
        if not eid:
            return playlist_static

        for x in playlist_static:
            if eid == x.get('id'):
                return x

        raise ValueError("Playlist not static")
