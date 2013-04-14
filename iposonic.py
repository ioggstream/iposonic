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

#
# manage media files
#
# tags
from mediamanager import MediaManager, UnsupportedMediaError
from mediamanager import stringutils
# logging and json
import logging
log = logging.getLogger('iposonic')

from datamanager.utils import jsonize
from exc import *




##
## The app ;)
##

class ArtistDAO:
    __tablename__ = "artist"
    __fields__ = ['id', 'name', 'isDir', 'path', 'userRating',
                  'averageRating', 'coverArt', 'starred', 'created']

    def get_info(self, path_u):
        return {
            'id': MediaManager.uuid(path_u),
            'name': basename(path_u),
            'path': path_u,
            'isDir': 'true'
        }


class MediaDAO:
    __tablename__ = "song"
    __fields__ = ['id', 'name', 'path', 'parent',
                  'title', 'artist', 'isDir', 'album',
                  'genre', 'track', 'tracknumber', 'date', 'suffix',
                  'isvideo', 'duration', 'size', 'bitRate',
                  'userRating', 'averageRating', 'coverArt',
                  'starred', 'created', 'albumId', 'scrobbleId'  # scrobbleId is an internal parameter used to match songs with last.fm
                  ]


class AlbumDAO:
    __tablename__ = "album"
    __fields__ = ['id', 'name', 'isDir', 'path', 'title',
                      'parent', 'album', 'artist',
                      'userRating', 'averageRating', 'coverArt',
                      'starred', 'created'
                      ]

    def get_info(self, path):
        """TODO use path_u directly."""
        eid = MediaManager.uuid(path)
        path_u = stringutils.to_unicode(path)
        parent = dirname(path)
        dirname_u = MediaManager.get_album_name(path_u)
        return {
            'id': eid,
            'name': dirname_u,
            'isDir': 'true',
            'path': path_u,
            'title': dirname_u,
            'parent': MediaManager.uuid(parent),
            'album': dirname_u,
            'artist': basename(parent),
            'coverArt': eid
        }


class PlaylistDAO:
    __tablename__ = "playlist"
    __fields__ = ['id', 'name', 'comment', 'owner', 'public',
                      'songCount', 'duration', 'created', 'entry'
                      ]

    def get_info(self, name):
        return {
            'id': MediaManager.uuid(name),
            'name': name
        }


class UserDAO:
    __tablename__ = "user"
    __fields__ = ['id', 'username', 'password', 'email',
                  'scrobbleUser', 'scrobblePassword', 'nowPlaying']


class UserMediaDAO:
    """TODO use this table for storing per-user metadata.

        Each user should have his own media rating.
        Queries should get a list of uids from here, then
        fetch playlist content by mid.
    """
    __tablename__ = "usermedia"
    __fields__ = ['eid', 'uid', 'mid', 'userRating', 'starred']


class IposonicDBTables(object):
    """Class defining base & tables.

        TODO For sqlalchemy usage I should only override
        the Base class...

        IMPORTANT: YOU HAVE TO OVERRIDE THOSE CLASSES
        IN THE IMPLEMENTATION FILE (eg. iposonicdb.py)
    """

    class BaseB(dict):
        def json(self):
            return self

    class Artist(BaseB, ArtistDAO):
        __fields__ = ArtistDAO.__fields__

        def __init__(self, path):
            IposonicDBTables.BaseB.__init__(self)
            self.update(self.get_info(path))

    class Album(BaseB, AlbumDAO):
        __fields__ = AlbumDAO.__fields__

        def __init__(self, path):
            IposonicDBTables.BaseB.__init__(self)
            self.update(self.get_info(path))

    class Media(BaseB, MediaDAO):
        __fields__ = MediaDAO.__fields__

        def __init__(self, path):
            IposonicDBTables.BaseB.__init__(self)
            self.update(MediaManager.get_info(path))

    class User(BaseB, UserDAO):
        __fields__ = UserDAO.__fields__

        def __init__(self, username):
            IposonicDBTables.BaseB.__init__(self)
            self.update({
                'id': MediaManager.uuid(username),
                'username': username}
            )

    class Playlist(BaseB, PlaylistDAO):
        __fields__ = PlaylistDAO.__fields__

        def __init__(self, name):
            IposonicDBTables.BaseB.__init__(self)
            self.update(self.get_info(name))


class IposonicDB(IposonicDBTables):
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
    def _get_hash(hash_, eid=None, query=None, order=None):
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
        raise ValueError(
            "Media Entry (song, artist, album) not found. eid: %s" % eid)

    def get_songs(self, eid=None, query=None):
        """Return a list of songs in the following form.

            [{'id': ..., 'title': ...}]
        """
        return IposonicDB._get_hash(self.songs, eid, query)

    def get_albums(self, eid=None, query=None, order=None):
        return IposonicDB._get_hash(self.albums, eid, query=query, order=order)

    def get_artists(self, eid=None, query=None):
        """This method should trigger a filesystem initialization.

            returns a list of dict
            [
                {'name': .., 'path': ..},
                {'name': .., 'path': ..},
            ]

        """
        if not self.artists:
            raise NotImplementedError("rewrite me in scanner thread")
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
                log.exception("error retrieving %s " % k )
        return ret

    def add_path(self, path, album=False):
        """Create an entry from path and add it to the DB."""
        if os.path.isdir(path):
            self.log.warn(
                "Adding %s: %s " % ("album" if album else "artist", stringutils.to_unicode(path)))
            eid = MediaManager.uuid(path)
            if album:
                self.albums[eid] = IposonicDB.Album(path)
            else:
                self.artists[eid] = IposonicDB.Artist(path)
            self.log.info(u"adding directory: %s, %s " % (eid, stringutils.to_unicode(path)))
            return eid
        elif MediaManager.is_allowed_extension(path):
            try:
                info = MediaManager.get_info(path)
                info.update({
                    'coverArt': MediaManager.cover_art_uuid(info)
                })
                self.songs[info['id']] = info
                self.log.info("adding file: %s, %s " % (info['id'], path))
                return info['id']
            except UnsupportedMediaError as e:
                raise IposonicException(e)
        raise IposonicException("Path not found or bad extension: %s " % path)

    def walk_music_directory_old(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        #raise NotImplementedError("This method should not be used")
        log.info("walking: ", self.get_music_folders())

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
                        self.add_path(path)
                        self.artists[MediaManager.uuid(
                            path)] = IposonicDB.Artist(path)
                        artist_j = {'artist': {
                            'id': MediaManager.uuid(path), 'name': a}}

                        #
                        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
                        #
                        first = a[0:1].upper()
                        self.indexes.setdefault(first, [])
                        self.indexes[first].append(artist_j)
                        log.info(
                            "Adding to index converted entry: %s" % artist_j)
                    except IposonicException as e:
                        log.error(e)
                log.info("artists: %s" % self.artists)

        return self.get_indexes()

    def get_users(self, eid=None, query=None):
        raise NotImplementedError(
            "In-memory datastore doesn't support multiple users")


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

    def __init__(self, music_folders, dbhandler=IposonicDB, recreate_db=False, tmp_dir="/tmp/iposonic"):
        self.log.info("Creating Iposonic with music folders: %s, dbhandler: %s" %
                      (music_folders, dbhandler))

        # set directory
        self.tmp_dir = tmp_dir
        self.cache_dir = join("/", tmp_dir, "_cache")

        # eventually create missing directories
        #   or die
        if not os.path.isdir(tmp_dir):
            os.mkdir(tmp_dir)
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

        self.db = dbhandler(
            music_folders, recreate_db=recreate_db, datadir=tmp_dir)
        self.log.setLevel(logging.WARN)



    def __getattr__(self, method):
        """Proxies DB methods."""
        if method in [
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
            dbmethod = IposonicDB.__getattribute__(self.db, method)
            return dbmethod

        return object.__getattr__(self, method)

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
                {'name': name, 'artist': [v['artist'] for v in artists]})
        return {'index': items}

    #
    #   Create Update Delete
    #

    def add_path(self, path, album=False):
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
        self.log.info("creating user: %s" % user)
        entry = self.db.User(user.get('username'))
        entry.update(user)
        return self.create_entry(entry)

    def update_user(self, eid, new):
        self.log.info("updating user: %s" % eid)
        entry = self.db.update_user(eid, new)
        return entry

    def delete_user(self, eid):
        self.log.info("delete user: %s" % eid)
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
