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
import os, sys, re
from os.path import join, basename, dirname
from binascii import crc32

# manage media files
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import  MP3, HeaderNotFoundError
import mutagen.oggvorbis

# logging and json
import simplejson
import logging
log = logging.getLogger('iposonic')

#tests
from nose import SkipTest


class ResponseHelper:
  """Serialize a python dict to an xml object, and embeds it in a subsonic-response

    see test/test_responsehelper.py for the test and documentation
    TODO: we could @annotate this ;)
  """
  log = logging.getLogger('ResponseHelper')
  @staticmethod
  def responsize_jsonp(ret, callback, status = "ok", version = "9.0.0"):
      if not callback: raise SubsonicProtocolException()
      # add headers to response
      ret.update({'status' : 'ok', 'version': '19.9.9' ,  "xmlns": "http://subsonic.org/restapi"})
      return "%s(%s)" % (
          callback,
          simplejson.dumps({'subsonic-response' : ret},
            indent = True,
            encoding = 'latin_1')
        )
  @staticmethod     
  def responsize_xml(ret):
      """Return an xml response from json and replace unsupported characters."""
      ret.update({'status' : 'ok', 'version': '19.9.9' ,  "xmlns": "http://subsonic.org/restapi"})
      return ResponseHelper.jsonp2xml({'subsonic-response' : ret}).replace("&","\\&amp;")
            
  @staticmethod
  def jsonp2xml(json):
      """Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.
      
        ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
      
          ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
          
          ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
          
          ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] } 
          
          ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
    "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}

              """
      ret = ""
      content = None
      for c in [str, int, unicode]:
          if isinstance(json, c): return str(json)
      if not isinstance(json, dict): raise Exception("class type: %s" % json)
      
      # every tag is a dict.
      #    its value can be a string, a list or a dict
      for tag in json.keys():
          tag_list = json[tag]
          
          # if tag_list is a list, then it represent a list of elements
          #   ex. {index: [{ 'a':'1'} , {'a':'2'} ] }
          #       --> <index a="1" /> <index b="2" />
          if isinstance(tag_list, list):                  
              for t in tag_list:  
                  # for every element, get the attributes
                  #   and embed them in the tag named
                  attributes = ""
                  content = ""
                  for (attr, value) in t.iteritems():
                      # only serializable values are attributes
                      if value.__class__.__name__ in 'str':
                          attributes = """%s %s="%s" """ % (attributes, attr , StringUtils.to_unicode(value))
                      elif value.__class__.__name__ in ['int', 'unicode', 'bool']:
                          attributes = """%s %s="%s" """ % (attributes, attr , value)
                      # other values are content
                      elif isinstance(value, dict):
                          content += ResponseHelper.jsonp2xml(value)
                      elif isinstance(value, list):
                          content += ResponseHelper.jsonp2xml({attr:value})
                  if content:    
                    ret += "<%s%s>%s</%s>" % (tag, attributes, content, tag)
                  else:
                    ret += "<%s%s/>" % (tag, attributes)
          if isinstance(tag_list, dict):
              attributes = ""
              content = ""

              for (attr, value) in tag_list.iteritems():
                  # only string values are attributes
                  if not isinstance(value, dict) and not isinstance(value, list):
                      attributes = """%s %s="%s" """ % (attributes, attr, value)
                  else:
                      content += ResponseHelper.jsonp2xml({attr: value})
              if content:    
                ret += "<%s%s>%s</%s>" % (tag, attributes, content, tag)
              else:
                ret += "<%s%s/>" % (tag, attributes)
                
      ResponseHelper.log.info( "\n\njsonp2xml: %s\n--->\n%s \n\n" % (json,ret))

      return ret.replace("isDir=\"True\"", "isDir=\"true\"")



    
##
## The app ;)
##
class UnsupportedMediaError(Exception):
    pass

class MediaInfo:
    @staticmethod
    def _get_tag(object, tag):
        try:
          return object[tag].text[0]
        except:
          return None
    def __init__(mutagen_data):
        self.artist = MediaInfo._get_tag(audio, 'TPE1')
        self.track = MediaInfo._get_tag(audio, 'TIT2')
        self.year  = MediaInfo._get_tag(audio, 'TDRC')

  
class MediaManager:
    log = logging.getLogger('MediaManager')
    re_track_1 = re.compile("([0-9]+)?[ -_]+(.*)")
    re_track_2 = re.compile("^(.*)([0-9]+)?$")    
    @staticmethod
    def get_entry_id(path):
        return str(crc32(path))

    @staticmethod
    def get_tag_manager(path):
        path = path.lower()
        if not Iposonic.is_allowed_extension(path):
            raise UnsupportedMediaError("Unallowed extension for path: %s" % path)
            
        if path.endswith("mp3"):
            return lambda x: MP3(x, ID3=EasyID3)
        if path.endswith("ogg"):
            return mutagen.oggvorbis.Open
        raise UnsupportedMediaError("Can't find tag manager for path: %s" % path)

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
            (track, title) = re.split("[ _\-]+", filename, 1) 
            track = int(track)
        except:
            (track, title) = (0, filename)
        return { 
            'title' : title
            , 'track' : track
            , 'path' : path
            , 'size'  : os.path.getsize(path)
            , 'suffix' : path[-3:]
        }
            
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
                ret  = MediaManager.get_info_from_filename(path)
                
                manager = MediaManager.get_tag_manager(path)
                audio = manager(path)
                
                MediaManager.log.info( "Original id3: %s" % audio)
                for (k,v) in audio.iteritems():
                    if isinstance(v,list) and v:
                        ret[k] = v[0]

                ret['id'] = MediaManager.get_entry_id(path)
                ret['isDir'] = 'false'
                ret['isVideo'] = 'false'
                ret['parent'] = MediaManager.get_entry_id(dirname(path))
                try:
                    ret['bitRate'] = audio.info.bitrate / 1000
                    ret['duration'] = int(audio.info.length)
                    if ret.get('tracknumber',0):
                        MediaManager.log.info("Overriding track with tracknumber")
                        ret['track'] = int(ret['tracknumber'])
                        
                except:
                    pass
                MediaManager.log.info( "Parsed id3: %s" % ret)
                return ret
            except HeaderNotFoundError as e:
                raise UnsupportedMediaError("Header not found in file: %s" % path, e)
            except ID3NoHeaderError as e:
                print "Media has no id3 header: %s" % path
            return None
        if not os.path.exists(path):
            raise UnsupportedMediaError("File does not exist: %s" % path)
            
        raise UnsupportedMediaError("Unsupported file type or directory: %s" % path)
            
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
                    

#
# Subsonic API uses those three items
#  for storing songs, albums and artists
#  Those entities require and id
class Entry(dict):
    required_fields = ['name','id']
    def validate(self):
        for x in required_fields:
            assert self[x]

class Artist(Entry):
    required_fields = ['name','id', 'isDir', 'path']
    def __init__(self,path):
        Entry.__init__(self)
        self['path'] = path
        self['name'] = basename(path)
        self['id'] = MediaManager.get_entry_id(path)
        self['isDir'] = 'true'

class Album(Artist):
    required_fields = ['name','id', 'isDir', 'path', 'title', 'parent', 'album']
    def __init__(self,path):
        Artist.__init__(self,path)
        self['title'] = self['name']
        self['album'] = self['name']
        parent = dirname(path)
        self['parent'] = MediaManager.get_entry_id(parent)
        self['artist'] = basename(parent)
        self['isDir'] = True
        
class AlbumTest:
    def test_1(self):
        a = Album("./test/data/mock_artist/mock_album")
        assert a['name'] == "mock_album"

class Media(Entry):
    required_fields = ['name','id','title','path','isDir']
    def __init__(self,path):
        Entry.__init__(self)
        self.update(MediaManager.get_info(path))

class Child(Entry):
    """A dictionary containing:
      id, isDir, parent
    """
    required_fields = ['id','isDir','parent']
    pass

class Directory:
    pass
#
# IpoSonic
#
        
class Iposonic:

    ALLOWED_FILE_EXTENSIONS = ["mp3","ogg","wma"]
    log = logging.getLogger('Iposonic')
    
    def __init__(self, music_folders):
        self.music_folders = music_folders
        #
        # Private data TODO use a local store?
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
    @staticmethod
    def is_allowed_extension(file):
        for e in Iposonic.ALLOWED_FILE_EXTENSIONS:
            if file.lower().endswith(e): return True
        return False
        
    def get_folder_by_id(self, folder_id):
      """It's ok just because self.music_folders are few"""
      for folder in self.music_folders:
        if MediaManager.get_entry_id(folder) == folder_id: return folder
      raise IposonicException("Missing music folder with id: %s" % dir_id)

    def get_music_directories(self):
        if not self.artists:
            self.walk_music_directory()
        return self.artists

    def get_entry_by_id(self, eid):
        if eid in self.get_music_directories():
            return self.get_music_directories()[eid]
        elif eid in self.albums:
            return self.albums[eid]
        elif eid in self.songs:
            return self.songs[eid]
        raise IposonicException("Missing entry with id: %s " % eid)
        
    def get_directory_path_by_id(self, eid):
        info = self.get_entry_by_id(eid)
        return (info['path'], info['path'])

        raise IposonicException("Missing directory with id: %s in %s" % (dir_id, self.artists))

    def get_song_by_id(self, eid):
        return self.songs[eid]

    def get_indexes(self):
        """
        {'A': 
        [{'artist': 
            {'id': '517674445', 'name': 'Antonello Venditti'}
            }, 
            {'artist': {'id': '-87058509', 'name': 'Anthony and the Johnsons'}}, 
            
            
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
        assert self.indexes
        items = []
        for (name, artists) in self.indexes.iteritems():
            items.append ({'name' : name, 'artist' : [ v['artist'] for v in artists  ]})
        return {'index': items}

    def add_entry(self, path, album = False):
        if os.path.isdir(path):
            eid = MediaManager.get_entry_id(path)
            if album:
                self.albums[eid] = Album(path)
            else:
                self.artists[eid] = Artist(path)
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

    @staticmethod
    def _filter(info, tag, re):
        if tag in info:
            Iposonic.log.info("checking %s" % info[tag])
            if re.match(info[tag]):
                return True
        return False

    def get_genre_songs(self, query):
        songs = []
        re_query = re.compile(".*%s.*" % query)
        for (eid,info) in self.songs.iteritems():
            print "get_genre_songs: info %s " % info
            if self._filter(info, 'genre', re_query):
              songs.append(info)
        return songs
        

    def _search_songs(self, re_query, songCount = 10, allFields = False):
        """"Return all songs where any tag matches the re_query."""
        # create an empty result set
        tags = ['title']
        if allFields:
            tags.extend(['artist', 'album'])
        ret=dict(zip(tags,[[],[],[]]))
        
        # add fields from id3 tags
        for (eid, info) in self.songs.iteritems():
            for tag in tags:
                if self._filter(info,tag,re_query):
                    ret['title'].append(info)
        return ret
        raise NotImplemented()
    def _search_artists(self, re_query, artistCount = 10):
        """"Return all artists where name matches the re_query."""
        ret={'artist':[]}
        for (eid, info) in self.artists.iteritems():
            assert isinstance(info,dict), "Info should be a dict, not  %s" % info
            if re_query.match(info['name']):
              ret['artist'].append(info)
        return ret
        raise NotImplemented()
    def _search_albums(self, re_query, albumCount = 10):
        raise NotImplemented()
    def search2(self, query, artistCount=10, albumCount = 10, songCount=10):
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
        #if albumCount != 10 or songCount != 10 or artistCount != 10: raise NotImplemented()
        re_query = re.compile(".*%s.*"%query)

        # create an empty result set
        tags = ['artist', 'album', 'title']
        ret=dict(zip(tags,[[],[],[]]))

        # add fields from directories
        ret['artist'].extend (self._search_artists(re_query)['artist'])

        songs = self._search_songs(re_query)
        for t in songs.keys():
          ret[t].extend(songs[t])

        self.log.info( "search2 result: %s" % ret)
                    
        # TODO merge them or use sets
        return ret
            
        
    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
          TODO: put in a separate thread?
        """
        print "walking: ", self.music_folders

        # reset database
        self.artists = dict()
        self.indexes = dict()
        
        # find all artists
        for music_folder in self.music_folders:        
          artists_local = [x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ]

          #index all artists
          for a in artists_local:
            if a:
              path = join("/",music_folder,a)
              try:
                self.add_entry(path)
                self.artists[MediaManager.get_entry_id(path)] = Artist(path)
                artist_j = {'artist' : {'id':MediaManager.get_entry_id(path), 'name': a}}

                #
                # indexes = { 'A' : {'artist': {'id': .., 'name': ...}}}
                #
                first = a[0:1].upper()
                self.indexes.setdefault(first,[])
                self.indexes[first].append(artist_j)
              except IposonicException as e:
                log.error(e)
            print "artists: %s" % self.artists
            
        return self.indexes
        
#   
class SubsonicProtocolException(Exception):
    """Request doesn't respect Subsonic API http://www.subsonic.org/pages/api.jsp"""
    pass
class IposonicException(Exception):
    pass
  
class StringUtils:
    encodings = ['ascii', 'latin_1',  'utf8', 'iso8859_15', 'cp850', 'cp037', 'cp1252']
    @staticmethod
    def to_unicode(s):
        for e in StringUtils.encodings:
            try: return unicode(s, encoding=e)
            except: pass
        raise UnicodeDecodeError("Cannot decode string: %s" % s)
        
