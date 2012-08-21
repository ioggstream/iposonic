# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
from flask import Flask
from flask import request, send_file

import os,sys
from os.path import join

from iposonic import Iposonic, IposonicException, SubsonicProtocolException, ResponseHelper, log

app = Flask(__name__)


#
# Configuration
#
music_folders = ["/opt/music/"]

iposonic = Iposonic(music_folders)

###
# The web
###

#
# Test connection
#
@app.route("/rest/ping.view", methods = ['GET', 'POST'])
def ping_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return ResponseHelper.responsize("")

@app.route("/rest/getLicense.view", methods = ['GET', 'POST'])
def get_license_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return ResponseHelper.responsize("""<license valid="true" email="foo@bar.com" key="ABC123DEF" date="2009-09-03T14:46:43"/>""")


#
# List music collections
#
@app.route("/rest/getMusicFolders.view", methods = ['GET', 'POST'])
def get_music_folders_view():
    ret = dict()
    for d in iposonic.music_folders:
      if os.path.isdir(d):
        ret[ 'musicFolder'] = {'id': iposonic.get_entry_id(d), 'name': d }
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
        try:
          eid = iposonic.add_entry(path)
          is_dir = os.path.isdir(path)
          child_j = {
            'id' : iposonic.get_entry_id(path),
            'parent' : dir_id,
            'title' : child,
            'artist' : artist,
            'isDir': str(is_dir).lower(),
            'coverArt' : 0
            }
          if not is_dir:
            (path, info) = tuple(iposonic.get_song_by_id(eid))
            child_j.update({
              'track' : 0,
              'year' : 0,
              'genre' : 'none',
              'size'  : os.path.getsize(path),
              'suffix' : path[-3:],
              'path'  : path
              })
            if info:
                child_j.update(info)
          children.append({'child': child_j})
        except IposonicException as e:
          log (e)
          
    return ResponseHelper.responsize(jsonmsg={'directory': {'id' : dir_id, 'name': artist, '__content': children}})



#
# Search
#
@app.route("/rest/search2.view", methods = ['GET', 'POST'])
def search2_view():
    """
    request:
      u=Aaa&p=enc:616263&v=1.2.0&c=android&query=Mannoia&artistCount=10&albumCount=20&songCount=25

    response:
        <searchResult2>
        <artist id="1" name="ABBA"/>
        <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22"/>
        <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23"/>
        <song id="112" parent="11" title="Money, Money, Money" isDir="false"
              album="Arrival" artist="ABBA" track="7" year="1978" genre="Pop" coverArt="25"
              size="4910028" contentType="audio/flac" suffix="flac"
              transcodedContentType="audio/mpeg" transcodedSuffix="mp3"
              path="ABBA/Arrival/Money, Money, Money.mp3"/>
    </searchResult2>

    """
    if not 'query' in request.args:
        raise SubsonicProtocolException("Missing required parameter: 'query' in search2_view.view")
        
    (query, artistCount, albumCount, songCount) = [request.args[x] for x in ("query", "artistCount", "albumCount", "songCount")]

    # ret is 
    ret = iposonic.search2(query, artistCount, albumCount, songCount)
    songs = []
    for (eid,path,info) in ret['title'].values():
      song_j = info
      song_j.update({'path' : path, 'id': eid, 'isDir' : 'false'})
      songs.append({'song': song_j })
      print "song: %s" % song
    return ResponseHelper.responsize(
      {'searchResult2':
        {'__content': songs }}
      )
    raise NotImplemented("WriteMe")





#
# Extras
#
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
    raise NotImplemented("WriteMe")
    song = {'song':{"__content" : ""}}
    randomSongs = {'randomSongs' : {'__content' : song}}
    return ResponseHelper.responsize(jsonmsg = randomSongs)




#
# download and stream
#

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

@app.route("/rest/download.view", methods = ['GET', 'POST'])
def download_view():
  """@params ?u=Aaa&p=enc:616263&v=1.2.0&c=android&id=1409097050&maxBitRate=0

  """
  if not 'id' in request.args:
      raise SubsonicProtocolException("Missing required parameter: 'id' in stream.view")
  (album, path) = iposonic.get_song_path_by_id(request.args['id'])
  if os.path.isfile(path):
      return send_file(path)
  raise IposonicException("why here?")



#
# TO BE DONE
#
@app.route("/rest/getCoverArt.view", methods = ['GET', 'POST']) 
def get_cover_art_view():
    raise NotImplemented("WriteMe")

@app.route("/rest/getLyrics.view", methods = ['GET', 'POST'])
def get_lyrics_view():
    raise NotImplemented("WriteMe")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

