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
#from __future__ import unicode_literals


# standard libs
import os
import re
from os.path import join, basename, dirname

#
# manage media files
#
# tags
from mediamanager import MediaManager, UnsupportedMediaError

# logging and json
import logging
log = logging.getLogger('iposonic')


class IposonicException(Exception):
    pass


class SubsonicProtocolException(IposonicException):
    """Request doesn't respect Subsonic API http://www.subsonic.org/pages/api.jsp"""
    def __init__(self, request=None):
        if request:
            print "request: %s" % request.data
    pass


class SubsonicMissingParameterException(SubsonicProtocolException):
    def __init__(self, param, method, request=None):
        SubsonicProtocolException.__init__(
            self, "Missing required parameter: %s in %s", param, method)


##
## The app ;)
##
class IposonicDB(object):
    """An abstract in-memory data store based on dictionaries.

        Implement your own backend.
        
        FIXME update this class with all the features
            supported by SqliteIposonicDB
    """
    log = logging.getLogger('IposonicDB')

    def __init__(self, music_folders, **kwargs):
        """Initialize using music_folders, and ignore other kwargs."""
        self.music_folders = music_folders
        #
        # Private data
        #
        self.indexes = dict()
        #
        # artists = { id: {path:, name: }}
        #
        self.artists = dict()
        #
        # albums = { id: {path:, name:, parent: }}
        #
        self.albums = dict()
        #
        # songs = { id: {path: ..., {info}} ,   id: {path: , {info}}}
        #
        self.songs = dict()
        #
        # playlists = { id: {name: .., entry: [], ...}
        self.playlists = dict()

    class Entry(dict):
        required_fields = ['name', 'id']

        def json(self):
            return self

        def validate(self):
            for x in required_fields:
                assert self[x]

    class Artist(Entry):
        __fields__ = ['id', 'name', 'isDir', 'path', 'userRating',
                      'averageRating', 'coverArt']

        def __init__(self, path):
            IposonicDB.Entry.__init__(self)
            self.update({
                'path': path,
                'name': basename(path),
                'id': MediaManager.get_entry_id(path),
                'isDir': 'true'

            })

    class Album(Artist):
        __fields__ = ['id', 'name', 'isDir', 'path', 'title',
                      'parent', 'album', 'artist',
                      'userRating', 'averageRating', 'coverArt'
                      ]

        def __init__(self, path):
            IposonicDB.Artist.__init__(self, path)
            parent = dirname(path)

            if self['name'].find("-") > 0:
                self['name'] = re.split("\s*-\s*", self['name'], 1)[1]
            self.update({
                'title': self['name'],
                'album': self['name'],
                'parent': MediaManager.get_entry_id(parent),
                'artist': basename(parent),
                'isDir': True,
                'coverArt': self['id']
            })

    class Media(Entry):
        __fields__ = ['id', 'name', 'path', 'parent',
                      'title', 'artist', 'isDir', 'album',
                      'genre', 'track', 'tracknumber', 'date', 'suffix',
                      'isvideo', 'duration', 'size', 'bitRate',
                      'userRating', 'averageRating', 'coverArt'
                      ]

        def __init__(self, path):
            IposonicDB.Entry.__init__(self)
            self.update(MediaManager.get_info(path))

    class Playlist(Entry):
        required_fields = ['id', 'name', 'comment', 'owner', 'public',
                           'songCount', 'duration', 'created', 'entry'
                           ]

        def __init__(self, name):
            IposonicDB.Entry.__init__(self)
            self.update({
                'id': MediaManager.get_entry_id(name),
                'name': name
            })

    def init_db(self):
        pass

    def end_db(self):
        pass

    def reset(self):
        self.indexes = dict()
        self.artists = dict()
        self.albums = dict()
        self.songs = dict()
        self.playlists = dict()

    def create_entry(self, entry):
        """Add an entry to the persistent store.

            XXX See update_entry too and refactor.
        """
        if isinstance(entry, self.Playlist):
            hash_ = self.playlists
        else:
            raise NotImplementedError("Only for playlists")

        eid = entry.get('id')
        if eid in hash_:
            hash_[eid].update(entry)
        else:
            hash_[eid] = entry

    update_entry = create_entry

    @staticmethod
    def _search(hash_, query, limit=10, key_only=False):
        """return values in hash matching query.

            query is a dict, eg {'title': 'Viva l'Italia'}
                it has two protected words: 'Null' and 'notNull', ex.
                {'starred' : 'notNull' }
            return a list of values or keys:
            [
                {'id':.., 'name':.., 'path': ..},
                {'id':.., 'name':.., 'path': ..},
                {'id':.., 'name':.., 'path': ..},
            ]
        """
        assert query, "Query is required"
        assert hash_, "Hash is required"
        ret = []
        for (field, value) in query.items():
            re_query = re.compile(".*%s.*" % value, re.IGNORECASE)

            def f_get_field(x):
                try:
                    value = hash_.get(x).get(field)
                    return re_query.match(value) is not None
                except:
                    pass
                return False

            def f_is_null(x):
                try:
                    return  hash_.get(x).get(field) is None
                except:
                    return False

            def f_is_not_null(x):
                return not f_is_null(x)

            if value == 'isNull':
                f_filter = f_is_null
            elif value == 'notNull':
                f_filter = f_is_not_null
            else:
                f_filter = f_get_field

            ret = filter(f_filter, hash_)
            if not key_only:
                ret = [hash_[x] for x in ret]
            return ret
        raise IposonicException("No entries returned")

    @staticmethod
    def _get_hash(hash_, eid=None, query=None):
        if eid:
            return hash_.get(eid)
        if query:
            return IposonicDB._search(hash_, query)
        return hash_.values()

    def add(self, entry):
        return self.db.add(entry)

    def update_entry(self, eid, new):
        for h in [self.songs, self.artists, self.albums]:
            record = self._get_hash(h, eid)
            if record:
                h[eid].update(new)
                return
        raise ValueError("Entry not found with eid: %s" % eid)

    def get_songs(self, eid=None, query=None):
        """Return a list of songs in the following form.

            [{'id': ..., 'title': ...}]
        """
        return IposonicDB._get_hash(self.songs, eid, query)

    def get_albums(self, eid=None, query=None):
        return IposonicDB._get_hash(self.albums, eid, query)

    def get_artists(self, eid=None, query=None):
        """This method should trigger a filesystem initialization.

            returns a list of dict
            [
                {'name': .., 'path': ..},
                {'name': .., 'path': ..},
            ]

        """
        if not self.artists:
            self.walk_music_directory()
        return IposonicDB._get_hash(self.artists, eid, query)

    def get_playlists(self, eid=None, query=None):
        return IposonicDB._get_hash(self.playlists, eid, query)

    def get_indexes(self):
        return self.indexes

    def get_music_folders(self):
        return self.music_folders

    def get_highest(self):
        """Return a list of songs. [ { id:, title:, ..} ,..]"""
        f_sort = lambda x: self.songs.get(x).get('userRating')
        return sorted(self.songs, key=f_sort, reverse=True)[0:20]

    def get_song_list(self, eids=[]):
        """return iterable"""
        ret = []
        for k in eids:
            if k is None:
                continue
            try:
                ret.append(self.get_songs(eid=k))
            except Exception as e:
                print "error retrieving %s due %s" % (k, e)
        return ret

    def add_entry(self, path, album=False):
        if os.path.isdir(path):
            print "Adding entry %s" % path
            eid = MediaManager.get_entry_id(path)
            if album:
                self.albums[eid] = IposonicDB.Album(path)
            else:
                self.artists[eid] = IposonicDB.Artist(path)
            self.log.info("adding directory: %s, %s " % (eid, path))
            return eid
        elif MediaManager.is_allowed_extension(path):
            try:
                info = MediaManager.get_info(path)
                info.update({
                    'coverArt': info.get('parent')
                })
                self.songs[info['id']] = info
                self.log.info("adding file: %s, %s " % (info['id'], path))
                return info['id']
            except UnsupportedMediaError, e:
                raise IposonicException(e)
        raise IposonicException("Path not found or bad extension: %s " % path)

    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        #raise NotImplementedError("This method should not be used")
        print "walking: ", self.get_music_folders()

        # reset database
        self.reset()

        # find all artists
        for music_folder in self.get_music_folders():
            artists_local = [x for x in os.listdir(
                music_folder) if os.path.isdir(join("/", music_folder, x))]

            #index all artists
            for a in artists_local:
                if a:
                    path = join("/", music_folder, a)
                    try:
                        self.add_entry(path)
                        self.artists[MediaManager.get_entry_id(
                            path)] = IposonicDB.Artist(path)
                        artist_j = {'artist': {
                            'id': MediaManager.get_entry_id(path), 'name': a}}

                        #
                        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
                        #
                        first = a[0:1].upper()
                        self.indexes.setdefault(first, [])
                        self.indexes[first].append(artist_j)
                    except IposonicException as e:
                        log.error(e)
                print "artists: %s" % self.artists

        return self.get_indexes()


#
# IpoSonic
#

class Iposonic:
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

        TODO replace print with log
        """
    log = logging.getLogger('Iposonic')

    def __init__(self, music_folders, dbhandler=IposonicDB, recreate_db=False):
        print("Creating Iposonic with music folders: %s, dbhandler: %s" %
              (music_folders, dbhandler))
        self.db = dbhandler(music_folders, recreate_db=recreate_db)
        self.log.setLevel(logging.INFO)

    def __getattr__(self, method):
        """Proxies DB methods."""
        if method in [
            'get_artists',
            'get_music_folders',
            'get_albums',
            'get_highest',
            'get_playlists',
            'get_song_list',
            'delete_entry'
        ]:
            dbmethod = IposonicDB.__getattribute__(self.db, method)
            return dbmethod
        raise NotImplementedError("Method not found: %s" % method)

    def get_folder_by_id(self, folder_id):
        """It's ok just because self.db.get_music_folders() are few"""
        for folder in self.db.get_music_folders():
            if MediaManager.get_entry_id(folder) == folder_id:
                return folder
        raise IposonicException("Missing music folder with id: %s" % folder_id)

    def get_entry_by_id(self, eid):
        ret = None
        for f in [self.get_artists, self.get_albums, self.get_songs]:
            try:
                ret = f(eid)
            except:
                pass
            if ret:
                return ret
        raise IposonicException("Missing entry with id: %s " % eid)

    def get_directory_path_by_id(self, eid):
        """TODO return a single path"""
        info = self.get_entry_by_id(eid)
        return (info['path'], info['path'])

    def get_indexes(self):
        """
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
                  "id": "2f686f6d652f72706f6c6c692f6f70742f646174612f3939384441444243384645304546393232364335373739364632343743434642",
                  "name": "Abba"
                 },
                 {
                  "id": "2f686f6d652f72706f6c6c692f6f70742f646174612f3441444135414135324537384544464545423530363844433535334342303738",
                  "name": "Adele"
                 },

        """
        assert self.db.get_indexes()
        items = []
        for (name, artists) in self.db.get_indexes().iteritems():
            items.append(
                {'name': name, 'artist': [v['artist'] for v in artists]})
        return {'index': items}

    #
    #   Create Update Delete
    #

    def add_entry(self, path, album=False):
        """TODO move do db"""
        return self.db.add_entry(path, album)

    def update_entry(self, eid, new):
        """TODO move do db"""
        return self.db.update_entry(eid, new)

    def create_entry(self, entry):
        return self.db.create_entry(entry)

    #
    # Retrieve
    #
    def get_songs(self, eid=None, query=None):
        """return one or more songs.

            if eid, return a single dict,
            if query, return a list of dict

            Parsing (eg. to add coverArt) should check the returned type.
        """
        songs = self.db.get_songs(eid=eid, query=query)
        #print "songs: %s (%s) " % (songs, songs.__class__)

        # add album coverArt to each song
        if songs.__class__.__name__ == 'dict':
            songs.update({'coverArt': songs.get('parent')})
            #print "songs2: %s " % songs
            return songs

        return [x.update({'coverArt': x.get('parent')}) or x for x in songs]

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
            'artist': self.db.get_artists(query={'name': query}),
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
        self.db.walk_music_directory()

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
#
