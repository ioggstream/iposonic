from flask import Flask
from flask import request

import os
from binascii import crc32
app = Flask(__name__)

root_path = "/home/rpolli/share/Musica/"
root_indexes = dict()
music_folders = [root_path]
artists = []
indexes = dict()

def responsize(msg="", jsonmsg= None, status="ok", version="9.0.0"):
    if jsonmsg:
        assert not msg, "Can't define both msg and jsonmsg'"
        msg = json2xml(jsonmsg)
    return """<?xml version="1.0" encoding="UTF-8"?>
  <subsonic-response xmlns="http://subsonic.org/restapi" version="%s" status="%s">%s</subsonic-response>""" %(version,status,msg)

def json2xml(json):
    ret = ""
    content = None
    try:
      if isinstance(json, list):
          if not json:
              return ""
          for item in json:
              ret += json2xml(item)
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
              ret += """<%s %s>%s</%s>""" % (name, attrs, json2xml(content), name)
      return ret
    except:
      print "error: %s" % json
      raise
    
def test_json2xml_1():
    val = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    print "ret: %s" % json2xml(val)

def test_json2xml_2():
    val = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    print json2xml([val, val])

def test_json2xml_3():
    val1 = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    val2 = { 'musicFolders': {'__content' : val1}}
    print json2xml(val2)
    
def test_json2xml_4():
      val1 = { 'musicFolder': {'id': 1234, 'name': "sss" }}
      val2 = { 'musicFolders': {'__content' : [val1, val1]}}
      print json2xml(val2)

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/rest/ping.view", methods = ['GET', 'POST'])
def ping_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return responsize("")

@app.route("/rest/getLicense.view", methods = ['GET', 'POST'])
def get_license_view():
    (u,p,v,c) = [request.args[x] for x in ['u','p','v','c']]
    return responsize("""<license valid="true" email="foo@bar.com" key="ABC123DEF" date="2009-09-03T14:46:43"/>""")

@app.route("/rest/getMusicFolders.view", methods = ['GET', 'POST'])
def get_music_folders_view():
    ret = dict()
    for d in music_folders:
      if os.path.isdir(d):
        ret[ 'musicFolder'] = {'id': crc32(d), 'name': d }
    return responsize(jsonmsg={'musicFolders' : {'__content' : ret}})

def walk_music_directory(music_folders):
    global root_indexes, artists, indexes
    from os.path import join, getsize
    print "walking: ", music_folders
    for music_folder in music_folders:
        print os.listdir(music_folder)
        artists.extend([x for x in os.listdir(music_folder)  if os.path.isdir(join("/",music_folder,x)) ])

    for a in artists:
        if a:
          artist_j = {'artist' : {'id':crc32(a), 'name': a}}
          first = a[0:1].upper()
          indexes.setdefault(first,[])
          indexes[first].append(artist_j)
    return indexes

def test_walk_music_directory():
    print walk_music_directory()


  
@app.route("/rest/getIndexes.view", methods = ['GET', 'POST'])
def get_indexes_view():
    global indexes
    """
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
    
    """
    walk_music_directory(music_folders)
    indexes_j = [{'index': {'name': k, '__content': v}} for (k,v) in indexes.iteritems()]
    indexes = {'indexes': {  '__content' : indexes_j }}
    
    
    return responsize(jsonmsg = indexes)
  
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
    return responsize(jsonmsg = randomSongs)


  
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

