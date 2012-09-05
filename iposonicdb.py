#
# Subsonic API uses those three items
#  for storing songs, albums and artists
#  Those entities require and id
import os
import sys
import re
import time
from os.path import join, basename, dirname
from binascii import crc32

# logging
import logging

from iposonic import IposonicException, Iposonic, IposonicDB
from iposonic import MediaManager, StringUtils, UnsupportedMediaError

# add local path for loading _mysqlembedded
sys.path.insert(0, './lib')
try:
    import _mysqlembedded
    sys.modules['_mysql'] = _mysqlembedded
except:
    """Fall back to mysql server module"""
    pass

# SqlAlchemy for ORM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.exc import ProgrammingError, OperationalError

from threading import Lock


def synchronized(lock):
    """ Synchronization decorator. """

    def wrap(f):
        def newFunction(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return newFunction
    return wrap


class LazyDeveloperMeta(DeclarativeMeta):
    """This class allows a lazy initialization of DAOs.

       Just add __tablename__ and __fields__ attribute to a subclass
       to associate a table.

       Should subclass DeclarativeMeta because it should contain Base initialization methods.

       TODO: actually uses only string columns, but it's ok for small collections ;)
       """
    def __init__(klass, classname, bases, dict_):
        """ Create a new class type.

            DeclarativeMeta stores class attributes in dict_
         """
        # Additionally, set attributes on the new object.
        is_pk = True
        for name in dict_.get('__fields__', []):
            setattr(
                klass, name, Column(name, String(128), primary_key=is_pk))
            is_pk = False

        # Return the new object using super().
        return DeclarativeMeta.__init__(klass, classname, bases, dict_)

Base = declarative_base(metaclass=LazyDeveloperMeta)


class IposonicDBTables:
    """DAO classes and Serializing methods."""
    class SerializerMixin(object):
        """Methods for serializing DAO and expose a dict-like behavior."""
        __fields__ = []

        def json(self):
            """Return a dict/json representation of the public fields of the object."""
            ret = []
            for (k, v) in self.__dict__.iteritems():
                if k in self.__fields__:
                    if k.lower() == 'isdir':
                        v = (v.lower() == 'true')
                    elif k.lower() in ['userrating', 'averagerating']:
                        v = int(v) if v is not None else 0
                    ret.append((k, v))
            return dict(ret)

        def get(self, attr):
            """Expose __dict__.get"""
            return self.__dict__.get(attr)

        def update(self, dict_):
            """Expose __dict__.update"""
            return self.__dict__.update(dict_)

        def __repr__(self):
            return "<%s: %s>" % (self.__class__.__name__, self.json().__repr__())

    class Artist(Base, SerializerMixin):
        __fields__ = ['id', 'name', 'isDir', 'path', 'userRating',
                      'averageRating', 'coverArt']
        __tablename__ = "artist"

        def __init__(self, path):
            Base.__init__(self)
            self.__dict__.update({
                'id': MediaManager.get_entry_id(path),
                'name': StringUtils.to_unicode(basename(path)),
                'path': StringUtils.to_unicode(path),
                'isDir': 'true'
            })

    class Media(Base, SerializerMixin):
        __tablename__ = "song"
        __fields__ = ['id', 'name', 'path', 'parent',
                      'title', 'artist', 'isDir', 'album',
                      'genre', 'track', 'tracknumber', 'date', 'suffix',
                      'isvideo', 'duration', 'size', 'bitrate',
                      'userRating', 'averageRating', 'coverArt'
                      ]

        def __init__(self, path):
            Base.__init__(self)
            self.__dict__.update(dict([(k, StringUtils.to_unicode(v)) for (
                k, v) in MediaManager.get_info(path).iteritems()]))

        def get(id, default=None):
            self.__dict__.get(id, default)

    class Album(Base, SerializerMixin):
        __fields__ = ['id', 'name', 'isDir', 'path', 'title',
                      'parent', 'album', 'artist',
                      'userRating', 'averageRating', 'coverArt']
        __tablename__ = "album"

        def __init__(self, path):
            Base.__init__(self)
            eid = MediaManager.get_entry_id(path)
            path_u = StringUtils.to_unicode(path)
            parent = dirname(path)
            dirname_u = basename(path_u)
            if dirname_u.find("-") > 0:
                dirname_u = re.split("\s*-\s*", dirname_u, 1)[1]

            self.__dict__.update({
                'id': eid,
                'name': dirname_u,
                'isDir': 'true',
                'path': path_u,
                'title': dirname_u,
                'parent': MediaManager.get_entry_id(parent),
                'album': dirname_u,
                'artist': basename(parent),
                'coverArt': eid
            })


class SqliteIposonicDB(object, IposonicDBTables):
    """Store data on Sqlite
    """
    log = logging.getLogger('SqliteIposonicDB')
    engine_s = "sqlite"

    def transactional(fn):
        """add transactional semantics to a method.

        """
        def transact(self, *args, **kwds):
            session = self.Session()
            kwds['session'] = session
            try:
                ret = fn(self, *args, **kwds)
                session.commit()
                return ret
            except (ProgrammingError, OperationalError) as e:
                session.rollback()
                print "Corrupted database: removing and recreating"
                self.reset()
            except Exception as e:
                session.rollback()
                if len(args):
                    ret = args[0]
                else:
                    ret = ""
                print "error: string: %s, ex: %s" % (
                    StringUtils.to_unicode(ret), e)
                raise
        transact.__name__ = fn.__name__
        return transact

    def create_uri(self):
        if self.engine_s == 'sqlite':
            return "%s:///%s" % (self.engine_s, self.dbfile)
        elif self.engine_s.startswith('mysql'):
            return "%s://%s:%s@%s/%s?charset=utf8" % (self.engine_s, self.user, self.passwd, self.host, self.dbfile)

    def __init__(self, music_folders, dbfile="iposonic1", refresh_interval=60, user="iposonic", passwd="iposonic", host="localhost", recreate_db=False):
        self.music_folders = music_folders

        # database credentials
        self.dbfile = dbfile
        self.user = user
        self.passwd = passwd
        self.host = host

        # sql alchemy db connector
        self.engine = create_engine(
            self.create_uri(), echo=True, convert_unicode=True)

        #self.engine.raw_connection().connection.text_factory = str
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.initialized = 0
        self.refresh_interval = refresh_interval
        self.indexes = dict()
        self.log.setLevel(logging.INFO)
        self.initialized = False
        self.recreate_db = recreate_db
        assert self.log.isEnabledFor(logging.INFO)

    def init_db(self):
        """On sqlite does nothing."""
        if recreate_db:
            self.reset()

    def end_db(self):
        pass

    def reset(self):
        """Drop and recreate database. Reinstantiate session."""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def _query(self, table_o, field_o, query, eid=None, session=None):
        assert table_o, "Table must not be null"
        qmodel = session.query(table_o)
        if eid:
            rs = qmodel.filter_by(id=eid).one()
            return rs.json()
        elif query:
            assert field_o, "Field must not be null"
            for (k, v) in query.items():
                rs = qmodel.filter(field_o.like("%%%s%%" % v)).all()
        else:
            rs = qmodel.all()
        if not rs:
            return []
        return [r.json() for r in rs]

    def _query_id(self, eid, session=None):
        assert eid, "Missing eid"
        for table_o in [self.Media, self.Album, self.Artist]:
            qmodel = session.query(table_o)
            try:
                rs = qmodel.filter_by(id=eid)
                if rs.one():
                    return rs
            except:
                pass
        raise ValueError("Eid not in db: %s" % eid)

    def _query_top(self, table_o, field_o, limit=20, session=None):
        """Return a list of songs, in json"""
        assert table_o and field_o
        qmodel = session.query(table_o)
        rs = qmodel.order_by(field_o.desc()).limit(limit)
        if not rs:
            return []
        return [r.json() for r in rs.all()]

    @transactional
    def get_highest(self, session=None):
        return self._query_top(self.Media, self.Media.userRating, session=session)

    @transactional
    def get_songs(self, eid=None, query=None, session=None):
        assert session
        print("get_songs: eid: %s, query: %s" % (eid, query))
        return self._query(self.Media, self.Media.title, query, eid=eid, session=session)

    @transactional
    def get_albums(self, eid=None, query=None, session=None):
        self.log.info("get_albums: eid: %s, query: %s" % (eid, query))
        return self._query(self.Album, self.Album.title, query, eid=eid, session=session)

    @transactional
    def get_artists(self, eid=None, query=None, session=None):
        """This method should trigger a filesystem initialization.

            returns a dict-array [{'id': .., 'name': .., 'path': .. }]

        """
        if not self.initialized:
            self.walk_music_directory()
        return self._query(self.Artist, self.Artist.name, query, eid=eid, session=session)

    def get_indexes(self):
        #
        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
        #
        indexes = dict()
        for artist_j in self.get_artists():
            a = artist_j.get('name')
            if not a:
                continue
            first = a[0:1].upper()
            indexes.setdefault(first, [])
            indexes[first].append({'artist': artist_j})
        print "indexes: %s" % indexes
        return indexes

    def get_music_folders(self):
        return self.music_folders

    @transactional
    def update_entry(self, eid, new, session=None):
        assert session, "Missing Session"
        assert eid, "Missing eid"
        assert new, "Missing new object"
        old = self._query_id(eid, session=session).update(new)

    @transactional
    def add_entry(self, path, album=False, session=None):
        assert session
        eid = None
        record = None
        if os.path.isdir(path):
            eid = MediaManager.get_entry_id(path)
            if album:
                record = self.Album(path)
            else:
                record = self.Artist(path)
            self.log.info("adding directory: %s, %s " % (eid,
                          StringUtils.to_unicode(path)))
        elif Iposonic.is_allowed_extension(path):
            try:
                record = self.Media(path)
                eid = record.id
                self.log.info("adding file: %s, %s " % (
                    eid, StringUtils.to_unicode(path)))
            except UnsupportedMediaError, e:
                raise IposonicException(e)

        if record and id:
            session.merge(record)
            session.flush()
            return eid

        raise IposonicException("Path not found or bad extension: %s " % path)

    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: use ctime|mtime or inotify to avoid unuseful I/O.
        """
        #raise NotImplementedError("This method should not be used")
        print "walking: ", self.get_music_folders()

        if time.time() - self.initialized < self.refresh_interval:
            return

        # reset database
        #self.reset()
        def add_or_log(self, path):
            try:
                self.add_entry(path)
            except IposonicException as e:
                self.log.error(e)
        # find all artists
        for music_folder in self.get_music_folders():
            artists_local = [x for x in os.listdir(
                music_folder) if os.path.isdir(join("/", music_folder, x))]

            #index all artists
            for a in artists_local:
                print "scanning artist: %s" % a
                if a:
                    path = join("/", music_folder, a)
                    add_or_log(self, path)
                if self.refresh_interval:
                    continue
                #
                # Scan recurrently only if not refresh_always
                #
                for dirpath, dirnames, filenames in os.walk(path):
                    for f in filenames:
                        add_or_log(self, join("/", path, dirpath, f))
        #
        # We're ok now
        #
        self.initialized = time.time()


class MySQLIposonicDB(SqliteIposonicDB):
    # mysql embedded
    import _mysqlembedded as _mysql
    """MySQL standard and embedded version.

        Classic version requires uri, otherwise
        you need to play with embedded.
    """
    log = logging.getLogger('SqliteIposonicDB')
    engine_s = "mysql+mysqldb"
    driver = _mysql
    datadir = "/tmp/iposonic/"

    sql_lock = Lock()

    def end_db(self):
        """MySQL requires teardown of connections and memory structures."""
        if self.initialized and self.driver:
            self.driver.server_end()

    #@synchronized(sql_lock)
    def init_db(self):
        if self.initialized:
            return
        print "initializing database in %s" % self.datadir
        if not os.path.isdir(self.datadir):
            os.mkdir(self.datadir)
        self.driver.server_init(
            ['ipython', "-h", self.datadir, '--bootstrap'], ['ipython_CLIENT', 'ipython_SERVER', 'embedded'])

        conn = self.driver.connection(user=self.user, passwd=self.passwd)
        try:
            conn.autocommit(True)

            conn.query("create database if not exists %s ;" % self.dbfile)
            conn.store_result()

            conn.query("use %s;" % self.dbfile)
            conn.store_result()

            conn.query("create table if not exists iposonic(version text);")
            conn.store_result()
            conn.query("insert into iposonic(version) values('0.0.1');")
            conn.store_result()
            assert not conn.error()
        except:
            raise
        finally:
            conn.close()
        if self.recreate_db:
            self.reset()
        self.initialized = True
        #_mysql.server_end()
