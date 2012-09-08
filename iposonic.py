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


# standard libs
import os
import sys
import re
from os.path import join, basename, dirname
from binascii import crc32

#
# manage media files
#
# tags
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError
import mutagen.oggvorbis
import mutagen.asf
# albumArt
from art_downloader import CoverSource

# logging and json
import simplejson
import logging
log = logging.getLogger('iposonic')


class SubsonicProtocolException(Exception):
    """Request doesn't respect Subsonic API http://www.subsonic.org/pages/api.jsp"""
    pass


class IposonicException(Exception):
    pass


class StringUtils:
    encodings = ['ascii', 'latin_1', 'utf8', 'iso8859_15', 'cp850',
                 'cp037', 'cp1252']

    @staticmethod
    def to_unicode(s):
        if not isinstance(s, str):
            return s
        for e in StringUtils.encodings:
            try:
                return unicode(s, encoding=e)
            except:
                pass
        raise UnicodeDecodeError("Cannot decode string: %s" % s)


#tests
from nose import SkipTest


##
## The app ;)
##
class UnsupportedMediaError(Exception):
    pass


class MediaManager:
    log = logging.getLogger('MediaManager')
    re_track_1 = re.compile("([0-9]+)?[ -_]+(.*)")
    re_track_2 = re.compile("^(.*)([0-9]+)?$")
    re_split_s = "\s*-\s*"
    re_notes = re.compile('\((.+)\)')

    @staticmethod
    def get_entry_id(path):
        # path should be byte[], so convert it
        #   if it's unicode
        if isinstance(path, unicode):
            path = path.encode('utf8')
        return str(crc32(path))

    @staticmethod
    def get_tag_manager(path):
        path = path.lower()
        if not Iposonic.is_allowed_extension(path):
            raise UnsupportedMediaError(
                "Unallowed extension for path: %s" % path)

        if path.endswith("mp3"):
            return lambda x: MP3(x, ID3=EasyID3)
        if path.endswith("ogg"):
            return mutagen.oggvorbis.Open
        if path.endswith("wma"):
            return mutagen.asf.Open
        raise UnsupportedMediaError(
            "Can't find tag manager for path: %s" % path)

    @staticmethod
    def get_parent(path):
        ret = path[0:path.rfind("/")]
        MediaManager.log.info("parent(%s) = %s" % (path, ret))
        return ret

    @staticmethod
    def get_info_from_filename(path):
        """Get track number, path, file size from file name."""
        #assert os.path.isfile(path)
        filename = basename(path[:path.rfind(".")])
        try:
            (track, title) = re.split("\s+[_\-]\s+", filename, 1)
            track = int(track)
        except:
            (track, title) = (0, filename)
        try:
            size = os.path.getsize(path)
        except:
            size = 0
        return {
            'title': title,
            'track': track,
            'path': path,
            'size': size,
            'suffix': path[-3:]
        }

    @staticmethod
    def get_info_from_filename2(path_u):
        """Improve v1"""
        filename = basename(path_u)

        # strip extension
        try:
            filename = filename[:filename.rindex(".")]
        except:
            pass  # if no extension found

        ret = {}
        # strip notes (eg. cdno, year) from filename
        m_notes = MediaManager.re_notes.search(filename)
        if m_notes:
            try:
                notes = m_notes.group(1)

                filename = filename.replace(m_notes.group(), "").strip()
                ret['year'] = int(notes)
                print "year: %s " % notes

            except:
                print "notes: %s" % notes

        info_l = [x.strip(" -") for x in re.split("-", filename)]
        title, album, artist, track = (None, None, None, None)
        for x in info_l:
            try:
                track = int(x)
                if track > 1900:
                    ret['year'] = track
                    track = 0
                else:
                    ret['track'] = track
                continue
            except:
                pass
            if not title:
                title = x
            elif not album:
                title, album = x, title
            elif not artist:
                album, artist = x, album

        try:
            size = os.path.getsize(path)
        except:
            size = -1

        if not 'track' in ret:
            try:
                t, n = title.split(" ", 1)
                track = int(t)
                title = n
            except:
                pass

        ret.update({
            'title': title,
            'album': album,
            'artist': artist,
            'size': size,
            'track': track,
            'path': path_u,
            'suffix': path_u[path_u.rfind("."):],
        })
        return dict([(k, v) for (k, v) in ret.iteritems() if v is not None])

    @staticmethod
    def get_album_name(path_u):
        """Get album name from an unicode path.

            First splits by "-" to work out the possible artist name,
            then rules out the year by parentheses.

        """
        if not os.path.isdir(path_u):
            raise UnsupportedMediaError("Path is not an Album: %s" % path_u)
        return MediaManager.get_info_from_filename2(path_u).get('title')

        MediaManager.log.info("parsing album path: %s" % path_u)
        title = basename(path_u)
        for separator in ['-', '(']:
            if title.find(separator) > 0:
                a0, a1 = title.split(separator, 1)
                try:
                    t_ = int(a1.strip("() []"))
                    title = a0.strip().strip(separator)
                except:
                    title = a1.strip().strip(separator)

        return title

    @staticmethod
    def get_info(path):
        """Get id3 or ogg info from a file.
           "bitRate": 192,
           "contentType": "audio/mpeg",
           "duration": 264,
           "isDir": false,
           "isVideo": false,
           "size": 6342112,
        """
        if os.path.isfile(path):
            try:
                # get basic info
                ret = MediaManager.get_info_from_filename2(path)

                manager = MediaManager.get_tag_manager(path)
                audio = manager(path)

                MediaManager.log.info("Original id3: %s" % audio)
                for (k, v) in audio.iteritems():
                    if isinstance(v, list) and v and v[0]:
                        ret[k] = v[0]

                ret['id'] = MediaManager.get_entry_id(path)
                ret['isDir'] = 'false'
                ret['isVideo'] = 'false'
                ret['parent'] = MediaManager.get_entry_id(dirname(path))
                try:
                    ret['bitRate'] = audio.info.bitrate / 1000
                    ret['duration'] = int(audio.info.length)
                    if ret.get('tracknumber', 0):
                        MediaManager.log.info(
                            "Overriding track with tracknumber")
                        ret['track'] = int(ret['tracknumber'])

                except:
                    pass
                MediaManager.log.info("Parsed id3: %s" % ret)
                return ret
            except HeaderNotFoundError as e:
                raise UnsupportedMediaError(
                    "Header not found in file: %s" % path, e)
            except ID3NoHeaderError as e:
                print "Media has no id3 header: %s" % path
            return None
        if not os.path.exists(path):
            raise UnsupportedMediaError("File does not exist: %s" % path)

        raise UnsupportedMediaError(
            "Unsupported file type or directory: %s" % path)

    @staticmethod
    def browse_path(directory):
        for (root, filedir, files) in os.walk(directory):
            for f in files:
                path = join("/", root, f)
                # print "path: %s" % path
                try:
                    info = MediaManager.get_info(path)
                except UnsupportedMediaError as e:
                    print "Media not supported by Iposonic: %s\n\n" % e
                except HeaderNotFoundError as e:
                    raise e
                except ID3NoHeaderError as e:
                    print "Media has no id3 header: %s" % path


class IposonicDB(object):
    """An abstract in-memory data store based on dictionaries.

        Implement your own backend.
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

    class Entry(dict):
        required_fields = ['name', 'id']

        def validate(self):
            for x in required_fields:
                assert self[x]

    class Artist(Entry):
        required_fields = ['name', 'id', 'isDir', 'path']

        def __init__(self, path):
            IposonicDB.Entry.__init__(self)
            self['path'] = path
            self['name'] = basename(path)
            self['id'] = MediaManager.get_entry_id(path)
            self['isDir'] = 'true'

    class Album(Artist):
        required_fields = ['name', 'id', 'isDir', 'path', 'title',
                           'parent', 'album']

        def __init__(self, path):
            IposonicDB.Artist.__init__(self, path)
            if self['name'].find("-") > 0:
                self['name'] = re.split("\s*-\s*", self['name'], 1)[1]
            self['title'] = self['name']
            self['album'] = self['name']
            parent = dirname(path)
            self['parent'] = MediaManager.get_entry_id(parent)
            self['artist'] = basename(parent)
            self['isDir'] = True

    class Media(Entry):
        required_fields = ['name', 'id', 'title', 'path', 'isDir']

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

    @staticmethod
    def _search(hash_, query, limit=10, key_only=False):
        """return values in hash matching query.

            query is a dict, eg {'title': 'Viva l'Italia'}

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

            ret = filter(f_get_field, hash_)
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

    def get_indexes(self):
        return self.indexes

    def get_music_folders(self):
        return self.music_folders

    def get_highest(self):
        """Return a list of songs. [ { id:, title:, ..} ,..]"""
        f_sort = lambda x: self.songs.get(x).get('userRating')
        return sorted(self.songs, key=f_sort, reverse=True)[0:20]

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
        elif Iposonic.is_allowed_extension(path):
            try:
                info = MediaManager.get_info(path)
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

    ALLOWED_FILE_EXTENSIONS = ["mp3", "ogg", "wma"]
    log = logging.getLogger('Iposonic')

    def __init__(self, music_folders, dbhandler=IposonicDB):
        print("Creating Iposonic with dbhandler: %s" % dbhandler)
        self.db = dbhandler(music_folders)
        self.log.setLevel(logging.INFO)

    def __getattr__(self, method):
        """Proxies DB methods."""
        if method in [
            'get_artists',
            'get_music_folders',
            'get_albums',
            'get_songs',
            'get_highest',
            'get_playlists'
        ]:
            dbmethod = IposonicDB.__getattribute__(self.db, method)
            return dbmethod
        raise NotImplementedError("Method not found: %s" % method)

    @staticmethod
    def is_allowed_extension(file):
        for e in Iposonic.ALLOWED_FILE_EXTENSIONS:
            if file.lower().endswith(e):
                return True
        return False

    def get_folder_by_id(self, folder_id):
        """It's ok just because self.db.get_music_folders() are few"""
        for folder in self.db.get_music_folders():
            if MediaManager.get_entry_id(folder) == folder_id:
                return folder
        raise IposonicException("Missing music folder with id: %s" % dir_id)

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

    def add_entry(self, path, album=False):
        """TODO move do db"""
        return self.db.add_entry(path, album)

    def update_entry(self, eid, new):
        """TODO move do db"""
        return self.db.update_entry(eid, new)

    def get_genre_songs(self, query):
        songs = []
        return self.db.get_songs(query={'genre': query})

    def search2(self, query, artistCount=10, albumCount=10, songCount=10):
        """response: artist, album, song
        <artist id="1" name="ABBA"/>
        <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22"/>
        <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23"/>
        <song id="112" parent="11" title="Money, Money, Money" isDir="false"
              album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
              size="4910028" contentType="audio/flac" suffix="flac"
              transcodedContentType="audio/mpeg" transcodedSuffix="mp3"
              path="ABBA/Arrival/Money, Money, Money.mp3"/>

        """
        #if albumCount != 10 or songCount != 10 or artistCount != 10: raise NotImplementedError()

        # create an empty result set
        tags = ['artist', 'album', 'title']
        ret = dict(zip(tags, [[], [], []]))

        # add fields from directories
        ret['artist'].extend(self.db.get_artists(query={'name': query}))

        songs = self.db.get_songs(query={'title': query})
        ret['title'].extend(songs)

        self.log.info("search2 result: %s" % ret)

        # TODO merge them or use sets
        return ret

    def refresh(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        self.db.walk_music_directory()

#
