#
# Subsonic API uses those three items
#  for storing songs, albums and artists
#  Those entities require and id
import os, sys, re
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

class PolliMeta(DeclarativeMeta):
    """Should subclass DeclarativeMeta because it should contain Base initialization methods."""
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

Base = declarative_base(metaclass=PolliMeta)     

class SerializerMixin(object):
    __fields__ = []
    def __repr__(self):
        return dict( [(k,v) for (k,v) in self.__dict__.iteritems() if k in self.__fields__])

class SqliteIposonicDB(object):
    """Store data on Sqlite
    """
    log = logging.getLogger('SqliteIposonicDB')   
 
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
        __fields__  = ['id', 'name', 'isDir', 'path', 'title', 'parent', 'album']
        __tablename__ = "album"
        def __init__(self,path):
            Base.__init__(self)
            parent = dirname(path)
            self.__dict__.update({
                'id' : MediaManager.get_entry_id(path),
                'title' : StringUtils.to_unicode(basename(path)),
                'album' : StringUtils.to_unicode(basename(path)),
                'path': StringUtils.to_unicode(path),
                'isDir' : 'true',
                'parent' : parent,
                'artist' : basename(parent)
                })
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

    def __init__(self, music_folders):
        self.music_folders = music_folders
        # Create the database
        self.engine = create_engine('sqlite:///meta.db', echo=True)
        self.engine.raw_connection().connection.text_factory = str
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.initialized = False
        self.indexes = dict()

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
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(title = v).all()
        else:
            rs = qmodel.all()
        assert rs, "Empty resultset %s" % rs
        return [r.__repr__() for r in rs]

    @transactional    
    def get_albums(self, eid = None, query = None, session = None ):
        self.log.info("get_songs: eid: %s, query: %s" % (eid, query))
        qmodel = session.query(self.Album)
        if eid:
            rs = qmodel.filter_by(id = eid).one()
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(title = v).all()
        else:
            rs = qmodel.all()
        assert rs, "Empty resultset %s" % rs
        return [r.__repr__() for r in rs]

    @transactional
    def get_artists(self, eid = None, query = None, session = None): 
        """This method should trigger a filesystem initialization.
            
            returns a dict-array {'artist':[]}

        """
        if not self.initialized:
            self.walk_music_directory()
            
        self.log.info("get_artists: query: %s" % query)
        qmodel = session.query(self.Artist)
        if eid:
            rs = qmodel.filter_by(id = eid).one()
        elif query:
            for (k,v) in query.items():
                rs = qmodel.filter_by(title = v).all()
        else:
            rs = qmodel.all()
        assert rs, "Empty resultset %s" % rs
        return dict( [(r.id,r.__repr__()) for r in rs] )

        raise NotImplemented()            
    def get_indexes(self):
        #
        # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
        #
        for (id,artist_j) in self.get_artists().iteritems():
            a = artist_j.get('name')
            if not a: continue
            first = a[0:1].upper()
            self.indexes.setdefault(first,[])
            self.indexes[first].append(artist_j)
        return self.indexes
        raise NotImplemented()
        
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
              self.log.info("adding file: %s, %s " % (eid, StringUtils.to_unicode(path))))
            except UnsupportedMediaError, e:
              raise IposonicException(e)
              
        if record and id:
            session.merge(record)
            session.flush()
            return eid

        raise IposonicException("Path not found or bad extension: %s " % path)
        
    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        #raise NotImplemented("This method should not be used")
        print "walking: ", self.get_music_folders()

        # reset database
        self.reset()
        
        # find all artists
        for music_folder in self.get_music_folders():        
          artists_local = [x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ]

          #index all artists
          for a in artists_local:
            if a:
              path = join("/",music_folder,a)
              try:
                self.add_entry(path)
              except IposonicException as e:
                log.error(e)
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    path = join("/", path, dirpath, f)
                    eid = self.add_entry(path)
        self.initialized = True
   
