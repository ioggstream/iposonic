#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
#
# TODO manage argv for:
#   * music_folders
#   * authentication backend
#   * reset db
#
from flask import Flask
from flask import request, send_file, redirect
from flask import Response

import os
import sys
import random
import re
from os.path import join, dirname, abspath

import simplejson
import logging

from iposonic import (Iposonic,
                      IposonicException,
                      SubsonicProtocolException,
                      MediaManager)
from iposonic import StringUtils

from art_downloader import CoverSource
from urllib import urlopen
try:
    from iposonicdb import MySQLIposonicDB as Dbh
except:
    from iposonic import IposonicDB as Dbh

app = Flask(__name__)

log = logging.getLogger('iposonic-webapp')

#
# Configuration
#
cache_dir = "/tmp/iposonic/_cache/"
music_folders = [
    #"/home/rpolli/workspace-py/iposonic/test/data/"
    "/opt/music/"
]

iposonic = None 

###
# The web
###

#
# Test connection
#


@app.route("/rest/ping.view", methods=['GET', 'POST'])
def ping_view():
    (u, p, v, c) = map(request.args.get, ['u', 'p', 'v', 'c'])
    print "songs: %s" % iposonic.db.get_songs()
    print "albums: %s" % iposonic.db.get_albums()
    print "artists: %s" % iposonic.db.get_artists()
    print "indexes: %s" % iposonic.db.get_indexes()
    return request.formatter({})


@app.route("/rest/getLicense.view", methods=['GET', 'POST'])
def get_license_view():
    (u, p, v, c) = [request.args.get(x, None) for x in ['u', 'p', 'v', 'c']]
    return request.formatter({'license': {'valid': 'true', 'email': 'robipolli@gmail.com', 'key': 'ABC123DEF', 'date': '2009-09-03T14:46:43'}})

#
# List music collections
#


@app.route("/rest/getMusicFolders.view", methods=['GET', 'POST'])
def get_music_folders_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    return request.formatter(
        {
            'musicFolders': {
                'musicFolder': [
                    {'id': MediaManager.get_entry_id(d), 'name': d} for d in iposonic.get_music_folders() if os.path.isdir(d)
                ]
            }
        }
    )


@app.route("/rest/getIndexes.view", methods=['GET', 'POST'])
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
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    # refresh indexes
    iposonic.refresh()

    #
    # XXX sample code to support jsonp clients
    #     this should be managed with some
    #     @jsonp_formatter
    #
    # XXX we should think to reimplement the
    #     DB in some consistent way before
    #     wasting time with unsearchable, dict-based
    #     data to format
    #
    return request.formatter({'indexes': iposonic.get_indexes()})


@app.route("/rest/getMusicDirectory.view", methods=['GET', 'POST'])
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
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])

    if not dir_id:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in getMusicDirectory.view")
    (path, dir_path) = iposonic.get_directory_path_by_id(dir_id)
    artist = iposonic.db.Artist(path)
    children = []
    for child in os.listdir(dir_path):
        child = StringUtils.to_unicode(child)
        if child[0] in ['.', '_']:
            continue
        path = join("/", dir_path, child)
        try:
            child_j = {}
            is_dir = os.path.isdir(path)
            # This is a Lazy Indexing. It should not be there
            #   unless a cache is set
            # XXX
            eid = MediaManager.get_entry_id(path)
            try:
                child_j = iposonic.get_entry_by_id(eid)
            except IposonicException:
                iposonic.add_entry(path, album=is_dir)
                child_j = iposonic.get_entry_by_id(eid)

            children.append(child_j)
        except IposonicException as e:
            log.info(e)

    def _track_or_die(x):
        try:
            return int(x['track'])
        except:
            return 0
    # Sort songs by track id, if possible
    children = sorted(children, key=_track_or_die)

    return request.formatter({'directory': {'id': dir_id, 'name': artist.get('name'), 'child': children}})


#
# Search
#
@app.route("/rest/search2.view", methods=['GET', 'POST'])
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
    (u, p, v, c, f, callback, query) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'query'])
    print "query:%s\n\n" % query
    if not query:
        raise SubsonicProtocolException(
            "Missing required parameter: 'query' in search2.view")

    (artistCount, albumCount, songCount) = map(
        request.args.get, ["artistCount", "albumCount", "songCount"])

    # ret is
    print "searching"
    ret = iposonic.search2(query, artistCount, albumCount, songCount)
    songs = [{'song': s} for s in ret['title']]
    songs.extend([{'album': a} for a in ret['album']])
    songs.extend([{'artist': a} for a in ret['artist']])
    print "ret: %s" % ret
    return request.formatter(
        {
            'searchResult2': {
                'song': ret['title'],
                'album': ret['album'],
                'artist': ret['artist']
            }
        }
    )
    raise NotImplementedError("WriteMe")


#
# Extras
#
@app.route("/rest/getAlbumList.view", methods=['GET', 'POST'])
def get_album_list_view():

    """
    http://your-server/rest/getAlbumList.view
    type    Yes     The list type. Must be one of the following: random, newest, highest, frequent, recent. Since 1.8.0 you can also use alphabeticalByName or alphabeticalByArtist to page through all albums alphabetically, and starred to retrieve starred albums.
    size    No  10  The number of albums to return. Max 500.
    offset  No  0   The list offset. Useful if you for example want to page through the list of newest albums.


    <albumList>
            <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22" userRating="4" averageRating="4.5"/>
            <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23" averageRating="4.4"/>
        </albumList>
    """
    mock_albums = [
        {'album': {'id': 11, 'parent': 1, 'title': 'Arrival',
                   'artist': 'ABBA', 'isDir': 'true'}}
    ]
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])
    (size, type_a, offset) = map(request.args.get, ['size', 'type', 'offset'])

    if not type_a in ['random', 'newest', 'highest', 'frequent', 'recent']:
        raise SubsonicProtocolException("Invalid or missing parameter: type")

    #albums = randomize(iposonic.albums, 20)
    albums = [a for a in iposonic.get_albums()]

    return request.formatter({'albumList': {'album': albums, 'song': iposonic.get_highest()}})


@app.route("/rest/getRandomSongs.view", methods=['GET', 'POST'])
def get_random_songs_view():
    """

    request:
      size    No  10  The maximum number of songs to return. Max 500.
      genre   No      Only returns songs belonging to this genre.
      fromYear    No      Only return songs published after or in this year.
      toYear  No      Only return songs published before or in this year.
      musicFolderId   No      Only return songs in the music folder with the given ID. See getMusicFolders.

    response xml:
      <randomSongs>
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

    response json:
        {'randomSongs':
            { 'song' : [
                {   'id' : ..,
                    'coverArt': ..,
                    'contentType': ..,
                    'transcodedContentType': ..,
                    'transcodedSuffix': ..
                }, ..
            }
        }
    """
    (size, genre, fromYear, toYear, musicFolderId) = map(request.args.get,
                                                         ['size', 'genre', 'fromYear', 'toYear', 'musicFolderId'])
    songs = []
    if genre:
        print "genre: %s" % genre
        songs = iposonic.get_genre_songs(genre)
    else:
        all_songs = iposonic.get_songs()
        assert len(all_songs)
        songs = randomize2_list(all_songs)
    assert songs
    songs = [x.update({'coverArt' : x.get('parent')}) or x for x in songs] 
    randomSongs = {'randomSongs': {'song': songs}}
    return request.formatter(randomSongs)


#
#
#
@app.route("/rest/getPlaylists.view", methods=['GET', 'POST'])
def get_playlists_view():
    """ response xml:
        <playlists>
                <playlist id="15" name="Some random songs" comment="Just something I tossed together" owner="admin" public="false" songCount="6" duration="1391" created="2012-04-17T19:53:44">
                    <allowedUser>sindre</allowedUser>
                    <allowedUser>john</allowedUser>
                </playlist>
                <playlist id="16" name="More random songs" comment="No comment" owner="admin" public="true" songCount="5" duration="1018" created="2012-04-17T19:55:49"/>
            </playlists>

        response jsonp:
            {playlists: { playlist : [
                {   id : ,
                    name: ,
                    comment: ,
                    owner: ,
                    public: ,
                    songCount:,
                    duration: ,
                    created:,
                },
                {   id, name, comment, owner, public, allowedUser: [
                    'jon',
                    'mary'
                    ] }
                ]
            }}
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    playlists = [iposonic.db.Playlist(
        name).json() for name in ['sample', 'random', 'genre']]

    playlists.extend(iposonic.get_playlists())
    return request.formatter({'playlists': {'playlist': playlists}})
    raise NotImplementedError()


@app.route("/rest/getPlaylist.view", methods=['GET', 'POST'])
def get_playlist_view():
    """Return a playlist.

        response xml:
     <playlist id="15" name="kokos" comment="fan" owner="admin" public="true" songCount="6" duration="1391"
5                     created="2012-04-17T19:53:44">
6               <allowedUser>sindre</allowedUser>
7               <allowedUser>john</allowedUser>
8               <entry id="657" parent="655" title="Making Me Nervous" album="I Don&apos;t Know What I&apos;m Doing"
9                      artist="Brad Sucks" isDir="false" coverArt="655" created="2008-04-10T07:10:32" duration="159"
10                     bitRate="202" track="1" year="2003" size="4060113" suffix="mp3" contentType="audio/mpeg" isVideo="false"
11                     path="Brad Sucks/I Don&apos;t Know What I&apos;m Doing/01 - Making Me Nervous.mp3" albumId="58"
12                     artistId="45" type="music"/>
        response jsonp:
            {'playlist': {
                'id':,
                'name':,
                'songCount',
                'allowedUser': [ 'user1', 'user2' ],
                'entry': [ {
                    id:,
                    title:,
                    ...
                    },
                ]
                }}

        TODO move database objects to iposonicdb. They  shouldn't be
                exposed outside.
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    eid = request.args.get('id')
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    playlists_static = map(MediaManager.get_entry_id, ['sample', 'random', 'genre'])
    print "Allowable: %s , id: %s, match: %s" %(
        playlists_static,
        eid,
        eid in map(unicode,playlists_static)
        )
    entries = []    
    # use default playlists
    if eid in playlists_static:
        j_playlist = iposonic.db.Playlist('sample').json()
        entries = randomize2_list(iposonic.get_songs(), 5)
    else:    
        playlist = iposonic.get_playlists(eid=eid)
        print "found playlist: %s" % playlist
        entry_ids = playlist.get('entry')
        if entry_ids:
            entries = [x for x in iposonic.get_song_list(entry_ids.split(","))]
        j_playlist = playlist
    j_playlist.update({
        'entry': entries, 
        'songCount': len(entries), 
        'duration' : sum([x.get('duration',0) for x in entries ]) 
    })
    return request.formatter({'playlist': j_playlist})

    
@app.route("/rest/createPlaylist.view",methods=['GET', 'POST'])
def create_playlist_view():
    """TODO move to iposonic
    
        request body:
            name=2012-09-08&
            songId=-2072958145&
            songId=-2021195453&
            songId=-1785884780
            
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (name, playlistId) = map(request.values.get, ['name', 'playlistId'])
    songId_l =  request.values.getlist('songId')
    print "songId: %s" % songId_l 
    if not name or playlistId:
        print "request: %s" % request.environ['body_copy']
        raise SubsonicMissingParameterException('id or playlistId', 'create_playlist_view')
        
    # create a new playlist
    if not playlistId:    
        eid = MediaManager.get_entry_id(name)
        try:
            playlist = iposonic.get_playlists(eid=eid)
            raise IposonicException("Playlist esistente")        
        except:
            pass
            
        playlist = iposonic.db.Playlist(name)
        playlist.update({'entry': ",".join(songId_l)})
        iposonic.create_entry(playlist)
        
    # update
    else:
        playlist = iposonic.get_playlists(eid=playlistId)
        songs = ",".join(playlist.get('entry'), songId_l)
        iposonic.update_entry(eid=playlistId, new={'entry': songs })
    return request.formatter({})
    
@app.route("/rest/deletePlaylist.view",methods=['GET', 'POST'])
def delete_playlist_view():
    """TODO move to iposonic
    
        request body:
            name=2012-09-08&
            songId=-2072958145&
            songId=-2021195453&
            songId=-1785884780
            
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    eid = request.values.get('id')
    
    if not eid:
        raise SubsonicMissingParameterException('id', 'delete_playlist_view')
        
    iposonic.delete_entry(eid=eid)
    return request.formatter({})

#
# download and stream
#
@app.route("/rest/stream.view", methods=['GET', 'POST'])
def stream_view():
    """@params ?u=Aaa&p=enc:616263&v=1.2.0&c=android&id=1409097050&maxBitRate=0

    """
    (u, p, v, c, f, callback, eid) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])

    print("request.headers: %s" % request.headers)
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    info = iposonic.get_entry_by_id(eid)
    path = info.get('path', None)
    assert path, "missing path in song: %s" % info
    if os.path.isfile(path):
        fp = open(path, "r")
        print "sending static file: %s" % path
        return send_file(path)
    raise IposonicException("why here?")


@app.route("/rest/download.view", methods=['GET', 'POST'])
def download_view():
    """@params ?u=Aaa&p=enc:616263&v=1.2.0&c=android&id=1409097050&maxBitRate=0

    """
    if not 'id' in request.args:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")
    info = iposonic.get_entry_by_id(request.args['id'])
    assert 'path' in info, "missing path in song: %s" % info
    if os.path.isfile(info['path']):
        return send_file(info['path'])
    raise IposonicException("why here?")


@app.route("/rest/scrobble.view", methods=['GET', 'POST'])
def scrobble_view():
    """Add song to last.fm"""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    return request.formatter({})


#@app.route("/rest/getCoverArt.view", methods=['GET', 'POST'])
def _get_cover_art_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, size) = map(request.args.get, ['id', 'size'])
    info = iposonic.get_entry_by_id(eid)
    if info.get('coverArtUrl'):
        return redirect(info.get('coverArtUrl'), 302)

    print "searching info for: %s" % info
    query = info.get('album')
    print "search path: %s" % query
    re_notascii = re.compile("[^A-z0-9]")
    c = CoverSource()
    for cover in c.search(info.get('album')):
        print "confronting info with: %s" % cover
        if len(set([re_notascii.sub(x.get('artist').lower(), "") for x in [info, cover]])) == 1:
            print "Artist match"
            iposonic.update_entry(
                eid, {'coverArtUrl': cover.get('cover_small')})
            open(join("/", cache_dir, "%s" % eid), "w").write()
            return redirect(cover.get('cover_small'), 302)
        else:
            print "Artist mismatch: %s, %s" % tuple(
                [x.get('artist') for x in [info, cover]])
    return ""


@app.route("/rest/getCoverArt.view", methods=['GET', 'POST'])
def get_cover_art_view():


    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, size) = map(request.args.get, ['id', 'size'])
        
    # Return file if present    
    cover_art_path = join("/", cache_dir, "%s" % eid)
    try:
        return send_file(cover_art_path)
    except IOError:
        pass
    
    # ...then if song, try with parent...
    info = iposonic.get_entry_by_id(eid)
    try:
        if info.get('isDir') in [ False, 'false', 'False' ]:
            cover_art_path = join("/", cache_dir, "%s" % info.get('parent'))
            return send_file(cover_art_path)
    except IOError:
        pass
        
    # ..finally download missing cover_art in cache_dir
    c = CoverSource()
    for cover in c.search(info.get('album')):
        print "confronting info: %s with: %s" % (info, cover)
        if len(set([MediaManager.normalize_album(x) for x in [info, cover]])) == 1:
            print "Saving image %s -> %s" % (cover.get('cover_small'), eid)
            fd = open(cover_art_path, "w")
            fd.write(urlopen(cover.get('cover_small')).read())
            fd.close()

            return send_file(cover_art_path)
        else:
            print "Artist mismatch: %s, %s" % tuple(
                [x.get('artist') for x in [info, cover]])
    raise IposonicException("Can't find CoverArt")


@app.route("/rest/setRating.view", methods=['GET', 'POST'])
def set_rating_view():
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    (eid, rating) = map(request.args.get, ['id', 'rating'])
    if not rating:
        raise SubsonicMissingParameterException(
            'rating', sys._getframe().f_code.co_name)
    if not eid:
        raise SubsonicMissingParameterException(
            'id', sys._getframe().f_code.co_name)
    iposonic.update_entry(eid, {'userRating': 5})
    return request.formatter({})


#
# TO BE DONE
#

@app.route("/rest/getUser.view", methods=['GET', 'POST'])
def set_rating_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    
    user = {'username' : u,
        'email': u,
        'scrobblingEnabled' : True,
        'adminRole' : False,
        'settingsRole' : True,
        'downloadRole'  : True,
        'uploadRole' : True,
        'playlistRole' : True,
        'coverArtRole' : True,
        'commentRole' : True,
        'podcastRole' : True,
        'streamRole' : True,
        'jukeboxRole' : True,
        'sharedRole' : False
    } 
    
    return request.formatter({'user': user})


@app.route("/rest/getLyrics.view", methods=['GET', 'POST'])
def get_lyrics_view():
    raise NotImplementedError("WriteMe")


#
# Helpers
#
class SubsonicMissingParameterException(SubsonicProtocolException):
    def __init__(self, param, method, request=None):
        SubsonicProtocolException.__init__(
            self, "Missing required parameter: %s in %s", param, method)


@app.before_request
def set_formatter():
    """Return a function to create the response."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    if f == 'jsonp':
        if not callback:
            # MiniSub has a bug, trying to retrieve jsonp without
            #   callback in case of getCoverArt.view
            #   it's not a problem because the getCoverArt should
            #   return a byte stream
            if request.endpoint not in ['get_cover_art_view', 'stream_view', 'download_view']:
                print "request: %s" % request.data
                raise SubsonicProtocolException(
                    "Missing callback with jsonp in: %s" % request.endpoint)
        request.formatter = lambda x: ResponseHelper.responsize_jsonp(
            x, callback)
    else:
        request.formatter = ResponseHelper.responsize_xml


@app.after_request
def set_content_type(response):
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    print "response is streamed: %s" % response.is_streamed

    if f == 'jsonp' and not response.is_streamed:
        response.headers['content-type'] = 'application/json'

    if not response.is_streamed and not request.endpoint in ['stream_view', 'download_view']:
        print("response: %s" % response.data)

    return response


def randomize(dictionary, limit=20):
    a_all = dictionary.keys()
    a_max = len(a_all)
    ret = []
    r = 0

    if not a_max:
        return ret

    try:
        for x in range(0, limit):
            r = random.randint(0, a_max - 1)
            k_rnd = a_all[r]
            ret.append(dictionary[k_rnd])
        return ret
    except:
        print "a_all:%s" % a_all
        raise


def randomize2(dictionary, limit=20):
    a_max = len(dictionary)
    ret = []

    for (k, v) in dictionary.iteritems():
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(v)
    return ret


def randomize2_list(lst, limit=20):
    a_max = len(lst)
    ret = []

    for k in lst:
        k_rnd = random.randint(0, a_max)
        if k_rnd > limit:
            continue
        ret.append(k)
    return ret

import cgi
class ResponseHelper:
    """Serialize a python dict to an xml object, and embeds it in a subsonic-response

      see test/test_responsehelper.py for the test and documentation
      TODO: we could @annotate this ;)
    """
    log = logging.getLogger('ResponseHelper')

    @staticmethod
    def responsize_jsonp(ret, callback, status="ok", version="9.0.0"):
        assert status and version  # TODO
        if not callback:
            raise SubsonicProtocolException()
        # add headers to response
        ret.update({'status': 'ok', 'version': '19.9.9',
                   "xmlns": "http://subsonic.org/restapi"})
        return "%s(%s)" % (
            callback,
            simplejson.dumps({'subsonic-response': ret},
                             indent=True,
                             encoding='latin_1')
        )

    @staticmethod
    def responsize_xml(ret):
        """Return an xml response from json and replace unsupported characters."""
        ret.update({'status': 'ok', 'version': '19.9.9',
                   "xmlns": "http://subsonic.org/restapi"})
        return ResponseHelper.jsonp2xml({'subsonic-response': ret}).replace("&", "\\&amp;")

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
            if isinstance(json, c):
                return str(json)
        if not isinstance(json, dict):
            raise Exception("class type: %s" % json)

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
                            attributes = """%s %s="%s" """ % (
                                attributes, 
                                attr , 
                                cgi.escape(StringUtils.to_unicode(value), quote=None)
                            )
                        elif value.__class__.__name__ in ['int', 'unicode', 'bool', 'long']:
                            attributes = """%s %s="%s" """ % (
                                attributes, attr, value)
                        # other values are content
                        elif isinstance(value, dict):
                            content += ResponseHelper.jsonp2xml(value)
                        elif isinstance(value, list):
                            content += ResponseHelper.jsonp2xml({attr: value})
                    if content:
                        ret += "<%s%s>%s</%s>" % (
                            tag, attributes, content, tag)
                    else:
                        ret += "<%s%s/>" % (tag, attributes)
            if isinstance(tag_list, dict):
                attributes = ""
                content = ""

                for (attr, value) in tag_list.iteritems():
                    # only string values are attributes
                    if not isinstance(value, dict) and not isinstance(value, list):
                        attributes = """%s %s="%s" """ % (
                            attributes, attr, value)
                    else:
                        content += ResponseHelper.jsonp2xml({attr: value})
                if content:
                    ret += "<%s%s>%s</%s>" % (tag, attributes, content, tag)
                else:
                    ret += "<%s%s/>" % (tag, attributes)

        ResponseHelper.log.info(
            "\n\njsonp2xml: %s\n--->\n%s \n\n" % (json, ret))

        return ret.replace("isDir=\"True\"", "isDir=\"true\"")


if __name__ == "__main__":
    argc, argv = len(sys.argv), sys.argv
    
    try:
        if argv[1] == '--reset':
            recreate_db = True
    except:
        recreate_db = False
        
    if not os.path.isdir("/tmp/iposonic/"):
        os.mkdir("/tmp/iposonic/")
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
        
    iposonic = Iposonic(music_folders, dbhandler=Dbh, recreate_db=recreate_db)
    iposonic.db.init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
