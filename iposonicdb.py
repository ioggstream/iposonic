#
# Subsonic API uses those three items
#  for storing songs, albums and artists
#  Those entities require and id
import os, sys, re, time
from os.path import join, basename, dirname
from binascii import crc32

# logging and json
import simplejson
import logging

from iposonic import IposonicException, Iposonic, IposonicDB
from iposonic import MediaManager, StringUtils, UnsupportedMediaError

# SqlAlchemy for ORM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

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
        for name in dict_.get('__fields__',[]):
            setattr(klass, name, Column(name, String, primary_key = is_pk))
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
            for (k,v) in self.__dict__.iteritems():
                if k in self.__fields__:
                    if k.lower() == 'isdir':
                        v = (v.lower() == 'true')
                    ret.append((k,v))
            return dict(ret)
        def get(self, attr):
            """Expose __dict__.get"""
            return self.__dict__.get(attr)
        def __repr__(self):
            return self.json().__repr__()
 
    class Artist(Base, SerializerMixin):
        __fields__  = ['id','name', 'isDir', 'path']
        __tablename__ = "artist"
        def __init__(self,path):
            Base.__init__(self)
            self.__dict__.update({
                'id' : MediaManager.get_entry_id(path),
                'name' : StringUtils.to_unicode(basename(path)),
                'path': StringUtils.to_unicode(path),
                'isDir' : 'true'
                })
                
    class Media(Base, SerializerMixin):
        __tablename__ = "song"
        __fields__ = ['id','name','path', 'parent', 
            'title', 'artist', 'isDir', 'album',
            'genre', 'track', 'tracknumber', 'date', 'suffix',
            'isvideo', 'duration', 'size', 'bitrate' 
        ]
        def __init__(self,path):
            Base.__init__(self)
            self.__dict__.update( dict( [ (k,  StringUtils.to_unicode(v))  for (k,v) in  MediaManager.get_info(path).iteritems() ]))
        def get(id, default = None):
            self.__dict__.get(id, default)

    class Album(Base, SerializerMixin):
        __fields__  = ['id', 'name', 'isDir', 'path', 'title', 'parent', 'album', 'artist']
        __tablename__ = "album"
        def __init__(self,path):
            Base.__init__(self)
            parent = dirname(path)
            self.__dict__.update({
                'id' : MediaManager.get_entry_id(path),
                'name' : StringUtils.to_unicode(basename(path)),
                'isDir' : 'true',
                'path': StringUtils.to_unicode(path),
                'title' : StringUtils.to_unicode(basename(path)),
                'parent' : MediaManager.get_entry_id(parent),
                'album' : StringUtils.to_unicode(basename(path)),
                'artist' : basename(parent)
                })
            
            

class SqliteIposonicDB(object, IposonicDBTables):
    """Store data on Sqlite
    """
    log = logging.getLogger('SqliteIposonicDB')   
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
            except:
                session.rollback()
                raise
        transact.__name__ = fn.__name__
        return transact

    def __init__(self, music_folders, dbfile = "", refresh_always = True):
        self.music_folders = music_folders
        # Create the database
        self.engine = create_engine('sqlite://'+dbfile, echo=True, convert_unicode=True)
        self.engine.raw_connection().connection.text_factory = str
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.initialized = 0
        self.refresh_always = refresh_always
        self.indexes = dict()
        self.log.setLevel(logging.INFO)
        assert self.log.isEnabledFor(logging.INFO)

    def reset(self):
        """Drop and recreate database. Reinstantiate session."""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def _query(self, table, query):
        assert table, "Table must not be null"
        assert query, "Query must not be null"
        for (field, value) in query.items():
            pass
            
    @transactional
    def get_songs(self, eid = None, query = None, session = None):
        assert session
        self.log.info("get_songs: eid: %s, query: %s" % (eid, query))
        qmodel = session.query(self.Media)
        if eid:
            rs = qmodel.filter_by(id = eid).one()
            return rs.json()
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(title = v).all()
        else:
            rs = qmodel.all()
        if not rs: return []
        return [r.json() for r in rs]

    @transactional    
    def get_albums(self, eid = None, query = None, session = None ):
        self.log.info("get_albums: eid: %s, query: %s" % (eid, query))
        qmodel = session.query(self.Album)
        if eid:
            rs = qmodel.filter_by(id = eid).one()
            return rs.json()
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(title = v).all()
        else:
            rs = qmodel.all()
        self.log.info("resultset %s" % rs)
        return [r.json() for r in rs]

    @transactional
    def get_artists(self, eid = None, query = None, session = None): 
        """This method should trigger a filesystem initialization.
            
            returns a dict-array [{'id': .., 'name': .., 'path': .. }]

        """
        if not self.initialized:
            self.walk_music_directory()
            
        self.log.info("query: %s" % query)
        qmodel = session.query(self.Artist)
        if eid:
            rs = qmodel.filter_by(id = eid).one()
            return rs.json()
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(name = v).all()
        else:
            rs = qmodel.all()
        print("resultset: %s" % rs)
        return [r.json() for r in rs] 

    def get_indexes(self):
        #
        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
        #
        indexes = dict()
        for artist_j in self.get_artists():
            a = artist_j.get('name')
            if not a: continue
            first = a[0:1].upper()
            indexes.setdefault(first,[])
            indexes[first].append({'artist': artist_j})
        print "indexes: %s" % indexes
        return indexes
        
    def get_music_folders(self):
        return self.music_folders
        
    @transactional
    def add_entry(self, path, album = False, session = None):
        assert session
        eid = None
        record = None
        if os.path.isdir(path):
            eid = MediaManager.get_entry_id(path)
            if album:
                record = self.Album(path)
            else:
                record = self.Artist(path)
            self.log.info("adding directory: %s, %s " % (eid, StringUtils.to_unicode(path)))
        elif Iposonic.is_allowed_extension(path):
            try:
              record = self.Media(path)
              eid = record.id
              self.log.info("adding file: %s, %s " % (eid, StringUtils.to_unicode(path)))
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
        #raise NotImplemented("This method should not be used")
        print "walking: ", self.get_music_folders()
        
        if time.time() - self.initialized < 60:
            return
            
        # reset database
        self.reset()
        def add_or_log(self,path):
            try: 
                self.add_entry(path)
            except IposonicException as e:
                self.log.error(e)
        # find all artists
        for music_folder in self.get_music_folders():        
          artists_local = [x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ]

          #index all artists
          for a in artists_local:
            print "scanning artist: %s" % a
            if a:
              path = join("/",music_folder,a)
              add_or_log(self,path)
            if self.refresh_always:
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
   
