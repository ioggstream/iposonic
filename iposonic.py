#!/usr/bin/python
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3

from flask import Flask
from flask import request, send_file


import os
from os.path import join
from binascii import crc32
app = Flask(__name__)

#
# Configuration
#
music_folders = ["/opt/music/"]

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
                    attrs += """ %s="%s"   """ % (attr, value)
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
    def __init__(self, music_folders):
        self.music_folders = music_folders
        #
        # Private data TODO use a local store?
        #
        self.artists = []
        self.indexes = dict()
        self.music_directories = dict()
        self.songs = dict()
        
    def get_folder_by_id(self, folder_id):
      """It's ok just because self.music_folders are few"""
      for folder in self.music_folders:
        if self.get_directory_id(folder) == folder_id: return folder
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
          
    def get_directory_id(self, dir_name):
        return str(crc32(dir_name))

    def add_entry(self, path):
        if os.path.isdir(path):
            dir_id = self.get_directory_id(path)
            self.music_directories[dir_id] = path
            return dir_id
        else:
            song_id = self.get_directory_id(path)
            self.songs[song_id] = path
            return song_id
        raise IposonicException("Path not found: %s " % path)
    def walk_music_directory(self):
        """Find all artists (top-level directories) and create indexes.

          TODO: create a cache for this.
        """
        print "walking: ", self.music_folders

        # find all artists
        for music_folder in self.music_folders:
          artists_local = [x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ]
          self.artists.extend(artists_local)

          #index all artists
          for a in artists_local:
            if a:
              path = join("/",music_folder,a)
              self.add_entry(path)
              artist_j = {'artist' : {'id':self.get_directory_id(path), 'name': a}}
              first = a[0:1].upper()
              self.indexes.setdefault(first,[])
              self.indexes[first].append(artist_j)

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
# The web 
#

iposonic = Iposonic(music_folders)

@app.route("/rest/ping.view", methods = ['GET', 'POST'])
def ping_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return ResponseHelper.responsize("")

@app.route("/rest/getLicense.view", methods = ['GET', 'POST'])
def get_license_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return ResponseHelper.responsize("""<license valid="true" email="foo@bar.com" key="ABC123DEF" date="2009-09-03T14:46:43"/>""")

@app.route("/rest/getMusicFolders.view", methods = ['GET', 'POST'])
def get_music_folders_view():
    ret = dict()
    for d in iposonic.music_folders:
      if os.path.isdir(d):
        ret[ 'musicFolder'] = {'id': crc32(d), 'name': d }
    return ResponseHelper.responsize(jsonmsg={'musicFolders' : {'__content' : ret}})

  
@app.route("/rest/getIndexes.view", methods = ['GET', 'POST'])
def get_indexes_view():
    """
    Return subsonic indexes.
    Request:
      u=Aaa&p=enc:616263&v=1.2.0&c=android&ifModifiedSince=0&musicFolderId=591521045
    Response: 
    <indexes lastModified="237462836472342">
      <shortcut id="11" name="Audio books"/>
      <shortcut id="10" name="Podcasts"/>
      <index name="A">
        <artist id="1" name="ABBA"/>
        <artist id="2" name="Alanis Morisette"/>
        <artist id="3" name="Alphaville"/>
      </index>
      <index name="B">
        <artist name="Bob Dylan" id="4"/>
      </index>

      <child id="111" parent="11" title="Dancing Queen" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
      size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
      path="ABBA/Arrival/Dancing Queen.mp3"/>

      <child id="112" parent="11" title="Money, Money, Money" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
      size="4910028" contentType="audio/flac" suffix="flac"
      transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
      path="ABBA/Arrival/Money, Money, Money.mp3"/>
    </indexes>

    TODO implement @param musicFolderId
    TODO implement @param ifModifiedSince
    """
    # refresh indexes
    iposonic.walk_music_directory()

    # serialize data
    indexes_j = [{'index': {'name': k, '__content': v}} for (k,v) in iposonic.indexes.iteritems()]
    indexes = {'indexes': {  '__content' : indexes_j }}
    
    return ResponseHelper.responsize(jsonmsg = indexes)


@app.route("/rest/getMusicDirectory.view", methods = ['GET', 'POST'])
def get_music_directory_view():
    """
      request:
        /rest/getMusicDirectory.view?u=Aaa&p=enc:616263&v=1.2.0&c=android&id=-493506601
      response1:
      <directory id="1" name="ABBA">
        <child id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22"/>
        <child id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23"/>
      </directory>

      response2:
      <directory id="11" parent="1" name="Arrival">
        <child id="111" parent="11" title="Dancing Queen" isDir="false"
        album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
        size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
        path="ABBA/Arrival/Dancing Queen.mp3"/>

        <child id="112" parent="11" title="Money, Money, Money" isDir="false"
        album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
        size="4910028" contentType="audio/flac" suffix="flac"
        transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
        path="ABBA/Arrival/Money, Money, Money.mp3"/>
      </directory>
      
        TODO getAlbumArt
        TODO getBitRate
    """
    if not 'id' in request.args:
        raise SubsonicProtocolException("Missing required parameter: 'id' in getMusicDirectory.view")
    dir_id = request.args['id']
    (path, dir_path) = iposonic.get_directory_path_by_id(dir_id)
    artist = path[path.rfind("/")+1:]
    children = []
    for child in os.listdir(dir_path):
        path = join("/", dir_path, child)
        iposonic.add_entry(path)
        children.append( {'child': {
          'id' : iposonic.get_directory_id(path),
          'parent' : dir_id,
          'title' : child,
          'artist' : artist,
          'isDir': str(os.path.isdir(path)).lower(),
          'coverArt' : 0
              }})
    return ResponseHelper.responsize(jsonmsg={'directory': {'id' : dir_id, 'name': artist, '__content': children}})
@app.route("/rest/getMusicDirectory.view", methods = ['GET', 'POST'])
def get_music_directory_view2():
    """response2:
      <directory id="11" parent="1" name="Arrival">
      <child id="111" parent="11" title="Dancing Queen" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
      size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
      path="ABBA/Arrival/Dancing Queen.mp3"/>

      <child id="112" parent="11" title="Money, Money, Money" isDir="false"
      album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
      size="4910028" contentType="audio/flac" suffix="flac"
      transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
      path="ABBA/Arrival/Money, Money, Money.mp3"/>
      </directory>

      """

    if not 'id' in request.args:
      raise SubsonicProtocolException("Missing required parameter: 'id' in getMusicDirectory.view")
      dir_id = request.args['id']
      (artist, dir_path) = iposonic.get_directory_path_by_id(dir_id)
      children = []
      for album in os.listdir(dir_path):
        children.append( {'child': {
        'id' : iposonic.get_directory_id(child),
        'parent' : dir_id,
        'title' : child,
        'artist' : artist,
        'isDir': os.path.isdir(join("/",dir_path, child)),
        'coverArt' : 0
        }})
        return ResponseHelper.responsize(jsonmsg={'directory': {'id' : dir_id, 'name': artist, '__content': children}})

      
@app.route("/rest/getRandomSongs.view", methods = ['GET', 'POST'])
def get_random_songs_view():
    """    <randomSongs>
    <song id="111" parent="11" title="Dancing Queen" isDir="false"
    album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="24"
    size="8421341" contentType="audio/mpeg" suffix="mp3" duration="146" bitRate="128"
    path="ABBA/Arrival/Dancing Queen.mp3"/>

    <song id="112" parent="11" title="Money, Money, Money" isDir="false"
    album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
    size="4910028" contentType="audio/flac" suffix="flac"
    transcodedContentType="audio/mpeg" transcodedSuffix="mp3"  duration="208" bitRate="128"
    path="ABBA/Arrival/Money, Money, Money.mp3"/>
    </randomSongs>
    """
    song = {'song':{"__content" : ""}}
    randomSongs = {'randomSongs' : {'__content' : song}}
    return ResponseHelper.responsize(jsonmsg = randomSongs)

@app.route("/rest/stream.view", methods = ['GET', 'POST'])
def stream_view():
  """@params ?u=Aaa&p=enc:616263&v=1.2.0&c=android&id=1409097050&maxBitRate=0

  """
  if not 'id' in request.args:
      raise SubsonicProtocolException("Missing required parameter: 'id' in stream.view")
  (album, path) = iposonic.get_song_path_by_id(request.args['id'])
  if os.path.isfile(path):
      print "sending static file: %s" % path
      return send_file(path)
  raise IposonicException("why here?")
#   
class SubsonicProtocolException(Exception):
    pass
class IposonicException(Exception):
    pass
  
  
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

