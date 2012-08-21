#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3


# standard libs
import os, sys, re
from os.path import join
from binascii import crc32

# manage media files
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import HeaderNotFoundError
import mutagen.oggvorbis

import logging
log = logging.getLogger('iposonic')

#tests
from nose import SkipTest

def log(s):
  
  print >>sys.stderr, s

class ResponseHelper:
  @staticmethod
  def responsize(msg="", jsonmsg= None, status="ok", version="9.0.0"):
    if jsonmsg:
      assert not msg, "Can't define both msg and jsonmsg'"
      msg = ResponseHelper.json2xml(jsonmsg)
    ret = """<?xml version="1.0" encoding="UTF-8"?>
    <subsonic-response xmlns="http://subsonic.org/restapi" version="%s" status="%s">%s</subsonic-response>""" %(version,status,msg)

    #
    # Subsonic android client doesn't recognize plain &
    #
    ret = ret.replace("&","\\&amp;")
    return ret

  @staticmethod
  def json2xml(json):
      """Convert a json structure to xml. The game is trivial. Nesting uses the '__content' keyword.
          ex. {
                'ul': {'style':'color:black;', '__content':
                      [
                      {'li': {'__content': 'Write first'}},
                      {'li': {'__content': 'Write second'}},
                      ]
                }
              }"""
      ret = ""
      content = None
      try:
        if isinstance(json, str) or isinstance(json, unicode):
            return json

        if isinstance(json, list):
            if not json:
                return ""
            for item in json:
                ret += ResponseHelper.json2xml(item)
            return ret

        for name in json.keys():
            attrs = ""
            assert isinstance(json[name],dict) , "entry is not a dictionary: %s" % json
            for (attr,value) in json[name].iteritems():
                if attr == '__content':
                    content = value
                else:
                    try:
                        attrs += """ %s="%s"   """ % (attr, value)
                    except UnicodeDecodeError as e:
                        print "value: %s"
                        raise e
            if not content:
                ret += """<%s %s />""" % (name,attrs)
            else:
                ret += """<%s %s>%s</%s>""" % (name, attrs, ResponseHelper.json2xml(content), name)
        return ret
      except:
        print "error xml-izing object: %s" % json
        raise

    
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
    
    @staticmethod
    def get_entry_id(path):
        return str(crc32(path))

    @staticmethod
    def get_tag_manager(path):
        path = path.lower()
        if not Iposonic.is_allowed_extension(path):
            raise UnsupportedMediaError("Unallowed extension for path: %s" % path)
            
        if path.endswith("mp3"):
            return EasyID3
        if path.endswith("ogg"):
            return mutagen.oggvorbis.Open
        raise UnsupportedMediaError("Can't find tag manager for path: %s" % path)

    @staticmethod
    def get_parent(path):
        ret = path[0:path.rfind("/")]
        MediaManager.log.info("parent(%s) = %s" % (path, ret))
        return ret
    @staticmethod
    def get_info(path):
        """Get id3 or ogg info from a file"""
        if os.path.isfile(path):
            try:
                manager = MediaManager.get_tag_manager(path)
                audio = manager(path)
                MediaManager.log.info( "Original id3: %s" % audio)
                ret = dict()
                for (k,v) in audio.iteritems():
                    if isinstance(v,list) and v:
                        ret[k] = v[0]
                ret['path'] = path
                ret['id'] = MediaManager.get_entry_id(path)
                ret['isDir'] = 'false'
                ret['parent'] = MediaManager.get_entry_id(MediaManager.get_parent(path))
                MediaManager.log.info( "Parsed id3: %s" % ret)
                return ret
            except UnsupportedMediaError as e:
                print "Media not supported by Iposonic: %s\n\n" % e
            except HeaderNotFoundError as e:
                raise e
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
class Artist(dict):
    def __init__(self,path):
        dict.__init__(self)
        self['path'] = path
        self['name'] = os.path.basename(path)
        self['id'] = MediaManager.get_entry_id(path)

class Album(Artist):
    def __init__(self,path):
        Artist.__init__(self,path)
        self['title'] = self['name']
        parent = MediaManager.get_parent(path)
        self['parent'] = MediaManager.get_entry_id(parent)
        self['artist'] = os.path.basename(parent)
  
class AlbumTest:
    def test_1(self):
        a = Album("./test/data/mock_artist/mock_album")
        assert a['name'] == "mock_album"

class Child:
    """A dictionary containing:
      id, isDir, parent
    """
    required_fields = ['id','isDir','parent']
    def validate(self):
        for i in self.required_fields:
            assert i in self
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
        
    def get_directory_path_by_id(self, dir_id):
        if dir_id in self.get_music_directories():
            path = self.get_music_directories()[dir_id]['path']
            return (path, os.path.join("/",self.music_folders[0],path))
        elif dir_id in self.albums:
            return (self.albums[dir_id]['path'], self.albums[dir_id]['path'])
        raise IposonicException("Missing directory with id: %s in %s" % (dir_id, self.artists))

    def get_song_by_id(self, eid):
        return self.songs[eid]

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
        

    def _search_songs(self, re_query, songCount = 10):
        # create an empty result set
        tags = ['artist', 'album', 'title']
        ret=dict(zip(tags,[[],[],[]]))
        
        # add fields from id3 tags
        for (eid, info) in self.songs.iteritems():
            for tag in tags:
                if self._filter(info,tag,re_query):
                    ret['title'].append(info)
        return ret
        raise NotImplemented()
    def _search_artists(self, re_query, artistCount = 10):
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
        print "ret: %s" % ret
        # add fields from directories
        ret['artist'].extend (self._search_artists(re_query)['artist'])

        songs = self._search_songs(re_query)
        for t in tags:
          ret[t].extend(songs[t])

        print "search2: %s" % ret
                    
        # TODO merge them or use sets
        return ret
            
        
    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
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
                #artist_j = {'artist' : {'id':MediaManager.get_entry_id(path), 'name': a}}

                first = a[0:1].upper()
                self.indexes.setdefault(first,[])
                self.indexes[first].append(artist_j)
              except IposonicException as e:
                log(e)
            print "artists: %s" % self.artists
            
#             for (root, dirfile, files) in os.walk(music_folder):
#                 for d in dirfile:
#                     path = join("/", root, d)
#                     try: self.add_entry(path)
#                     except: pass
#                 for f in files:
#                     path = join("/", root, f)
#                     try: self.add_entry(path)
#                     except: pass
        return self.indexes
        
#   
class SubsonicProtocolException(Exception):
    pass
class IposonicException(Exception):
    pass
  
