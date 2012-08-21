#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3



import os, sys, re
from os.path import join
from binascii import crc32

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import HeaderNotFoundError
import mutagen.oggvorbis

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
        if isinstance(json, str):
            return json

        if isinstance(json, list):
            if not json:
                return ""
            for item in json:
                ret += ResponseHelper.json2xml(item)
            return ret

        for name in json.keys():
            attrs = ""
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
    def get_info(path):
        """Get id3 or ogg info from a file"""
        if os.path.isfile(path):
            try:
                manager = MediaManager.get_tag_manager(path)
                audio = manager(path)
                print "Original id3: %s" % audio
                ret = dict()
                for (k,v) in audio.iteritems():
                    if isinstance(v,list) and v:
                        ret[k] = v[0]
                print "Parsed id3: %s" % ret
                return ret
            except UnsupportedMediaError as e:
                print "Media not supported by Iposonic: %s\n\n" % e
            except HeaderNotFoundError as e:
                raise e
            except ID3NoHeaderError as e:
                print "Media has no id3 header: %s" % path
            return None
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
                    

class MediaManagerTest:
    def get_info_harn(self, file, expected):
        info = MediaManager.get_info(file)
        for f in expected.keys():
            assert info[f] == expected[f], "Mismatching field. Expected %s get %s" % (expected[f], info[f])
    def get_info_test_ogg(self):
        file = "./test/data/sample.ogg"
        expected = {'title':'mock_title', 'artist': 'mock_artist' , 'year':'mock_year'}
        self.get_info_harn(file,expected)
    def get_info_test_mp3(self):
        file = "./test/data/lara.mp3"
        expected = {
          'title' : 'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)',
          'artist' : 'Lara St John (PREVIEW: buy it at www.magnatune.com)'
        }
        self.get_info_harn(file, expected)
    def get_info_test_wma(self):
        file = "./test/data/sample.wma"
        expected = {}
        self.get_info_harn(file, expected)
    def browse_path_test(self):
        MediaManager.browse_path("/opt/music")





#
# IpoSonic
#
        
class Iposonic:

    ALLOWED_FILE_EXTENSIONS = ["mp3","ogg","wma"]
    
    def __init__(self, music_folders):
        self.music_folders = music_folders
        #
        # Private data TODO use a local store?
        #
        self.artists = []
        self.indexes = dict()
        self.music_directories = dict()
        #
        # songs = { id: (path, info) ,   id: (path,info)}
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
        if self.get_entry_id(folder) == folder_id: return folder
      raise IposonicException("Missing music folder with id: %s" % dir_id)

    def get_music_directories(self):
        if not self.music_directories:
            self.walk_music_directory()
        return self.music_directories
        
    def get_directory_path_by_id(self, dir_id):
        if dir_id in self.get_music_directories():
            path = self.get_music_directories()[dir_id]
            return (path, os.path.join("/",self.music_folders[0],path))
        raise IposonicException("Missing directory with id: %s in %s" % (dir_id, self.music_directories))

    def get_song_by_id(self, eid):
        return self.songs[eid]

    def get_song_path_by_id(self, song_id):
      if song_id in self.songs:
        (path,info) = self.songs[song_id]
        return (path, os.path.join("/",self.music_folders[0],path))
      raise IposonicException("Missing song with id: %s in %s" % (song_id, self.songs))
          
    def get_entry_id(self, dir_name):
        return str(crc32(dir_name))
    

    def add_entry(self, path):
        if os.path.isdir(path):
            eid = self.get_entry_id(path)
            self.music_directories[eid] = path
            print "adding entry: %s, %s " % (eid, path)
            return eid
        elif Iposonic.is_allowed_extension(path):
            try:
              eid = self.get_entry_id(path)
              info = MediaManager.get_info(path)
              self.songs[eid] = (path, info)
              print "adding entry: %s, %s " % (eid, path)
              return eid
            except UnsupportedMediaError, e:
              raise IposonicException(e)
        raise IposonicException("Path not found or bad extension: %s " % path)

    @staticmethod
    def _filter(info, tag, re):
        if tag in info:
            print "checking %s" % info[tag]
            if re.match(info[tag]):
                return True
        return False

    def search2(self, query, artistCount=10, albumCount = 10, songCount=10):
        """response: artist, album, song"""
        if albumCount != 10 or songCount != 10 or artistCount != 10:
            raise NotImplemented()
        re_query = re.compile(".*%s.*"%query)

        # create an empty result set
        tags = ['artist', 'album', 'title']
        ret=dict(zip(tags,[[],[],[]]))
        print "ret: %s" % ret
        # add fields from directories
        ret['artist'].extend ( [a for a in self.artists if re_query.match(a)])
        ret['album'].extend( [d for d in self.music_directories.iteritems() if re_query.match(d[1]) ])

        # add fields from id3 tags
        for (eid,(path,info)) in self.songs.iteritems():
            for tag in tags:
                if self._filter(info,tag,re_query):
                    ret[tag].append((eid, path, info))
                    
                    
        # TODO merge them or use sets
        return ret
            
        
    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        print "walking: ", self.music_folders
        self.music_directories = dict()
        self.artists = []
        self.indexes = dict()
        # find all artists
        for music_folder in self.music_folders:
          artists_local = [x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ]
          self.artists.extend(artists_local)

          #index all artists
          for a in artists_local:
            if a:
              path = join("/",music_folder,a)
              try:
                self.add_entry(path)
                artist_j = {'artist' : {'id':self.get_entry_id(path), 'name': a}}
                first = a[0:1].upper()
                self.indexes.setdefault(first,[])
                self.indexes[first].append(artist_j)
              except IposonicException as e:
                log(e)

        return self.indexes
            
class IposonicTest:
    def setup(self):
        self.iposonic =  Iposonic([os.getcwd()])

    def harn_load_fs(self):
        """Adds the entries in root to the iposonic index"""
        root = os.getcwd() +"/test/data/"
        self.id_l = []

        for f in os.listdir(root):
            path = join("/",root,f)
            print "p: ",path
            self.id_l.append(self.iposonic.get_entry_id(path))
            self.iposonic.add_entry(path)    
    def test_get_song_by_id(self):
        """Retrieve added songs info and path by id """
        self.harn_load_fs()
        
        for eid in self.id_l:
            try:
              (path,info) = self.iposonic.get_song_by_id(eid)
              (path, full_path) = self.iposonic.get_song_path_by_id(eid)
            except:
              print "error processing eid: %s" % eid

    def test_search2_1(self):
        """Search added songs"""
        self.harn_load_fs()
        ret = self.iposonic.search2(query="Lara")
        print "ret: %s" % ret
        assert ret['artist']
    def test_search2_2(self):
        """Search added songs"""
        self.harn_load_fs()
        ret = self.iposonic.search2(query="Bach")
        print "ret: %s" % ret
        assert ret['album']
    def test_search2_3(self):
        """Search added songs"""
        self.harn_load_fs()
        ret = self.iposonic.search2(query="magnatune")
        print "ret: %s" % ret
        for x in ['album','title','artist']:
            assert ret[x] 
            
    def test_directory_get(self):
        self.iposonic.walk_music_directory()
        dirs = self.iposonic.music_directories
        k=dirs.keys()[0]
        (id_1,dir_1) = (k, dirs[k])
        print self.iposonic.get_directory_path_by_id(id_1)
    def test_walk_music_directory(self):
        print self.iposonic.walk_music_directory()
        
        
#   
class SubsonicProtocolException(Exception):
    pass
class IposonicException(Exception):
    pass
  
