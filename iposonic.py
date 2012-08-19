#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3



import os, sys
from os.path import join
from binascii import crc32
def log(s):
  print >>sys.stderr, s

class ResponseHelper:
  @staticmethod
  def responsize(msg="", jsonmsg= None, status="ok", version="9.0.0"):
    if jsonmsg:
      assert not msg, "Can't define both msg and jsonmsg'"
      msg = ResponseHelper.json2xml(jsonmsg)
    return """<?xml version="1.0" encoding="UTF-8"?>
    <subsonic-response xmlns="http://subsonic.org/restapi" version="%s" status="%s">%s</subsonic-response>""" %(version,status,msg)

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
        self.songs = dict()

    def is_allowed_extension(self, file):
        for e in self.ALLOWED_FILE_EXTENSIONS:
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
    def get_song_path_by_id(self, song_id):
      if song_id in self.songs:
        path = self.songs[song_id]
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
        elif self.is_allowed_extension(path):
            eid = self.get_entry_id(path)
            self.songs[eid] = path
            print "adding entry: %s, %s " % (eid, path)
            return eid
        raise IposonicException("Path not found or bad extension: %s " % path)
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
        self.iposonic =  Iposonic(music_folders)
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
  
