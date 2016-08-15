import logging, re, os
from os.path import join
from mediamanager import stringutils, MediaManager, UnsupportedMediaError
from exc import IposonicException
from tables import *

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



class MemoryIposonicDB(IposonicDBTables):
    """An abstract in-memory data store based on dictionaries.

        Implement your own backend.

        FIXME update this class with all the features
            supported by SqliteMemoryIposonicDB
    """
    log = logging.getLogger('MemoryIposonicDB')

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
            return MemoryIposonicDB._search(hash_, query)
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
        return MemoryIposonicDB._get_hash(self.songs, eid, query)

    def get_albums(self, eid=None, query=None, order=None):
        return MemoryIposonicDB._get_hash(self.albums, eid, query=query, order=order)

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
        return MemoryIposonicDB._get_hash(self.artists, eid, query)

    def get_playlists(self, eid=None, query=None):
        return MemoryIposonicDB._get_hash(self.playlists, eid, query)

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
                self.log.exception("error retrieving %r " % k )
        return ret

    def add_path(self, path, album=False):
        """Create an entry from path and add it to the DB."""
        if os.path.isdir(path):
            self.log.warn(
                "Adding %s: %s " % ("album" if album else "artist", stringutils.to_unicode(path)))
            eid = MediaManager.uuid(path)
            if album:
                self.albums[eid] = MemoryIposonicDB.Album(path)
            else:
                self.artists[eid] = MemoryIposonicDB.Artist(path)
            self.log.info(u"adding directory: %r, %r " % (eid, stringutils.to_unicode(path)))
            return eid
        elif MediaManager.is_allowed_extension(path):
            try:
                info = MediaManager.get_info(path)
                info.update({
                    'coverArt': MediaManager.cover_art_uuid(info)
                })
                self.songs[info['id']] = info
                self.log.info("adding file: %r, %r " % (info['id'], path))
                return info['id']
            except UnsupportedMediaError as e:
                raise IposonicException(e)
        raise IposonicException("Path not found or bad extension: %s " % path)

    def walk_music_directory_old(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        #raise NotImplementedError("This method should not be used")
        self.log.info("walking: ", self.get_music_folders())

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
                            path)] = MemoryIposonicDB.Artist(path)
                        artist_j = {'artist': {
                            'id': MediaManager.uuid(path), 'name': a}}

                        #
                        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
                        #
                        first = a[0:1].upper()
                        self.indexes.setdefault(first, [])
                        self.indexes[first].append(artist_j)
                        self.log.info(
                            "Adding to index converted entry: %s" % artist_j)
                    except IposonicException as e:
                        self.log.error(e)
                self.log.info("artists: %r" % self.artists)

        return self.get_indexes()

    def get_users(self, eid=None, query=None):
        raise NotImplementedError(
            "In-memory datastore doesn't support multiple users")
