#
# Views for downloading songs
#
#
import os
from os.path import join
import logging
from flask import request, send_file
from webapp import iposonic, app, fs_cache, cache_dir
from webapp import randomize2_list
from iposonic import IposonicException, SubsonicProtocolException
from mediamanager import MediaManager, StringUtils


log = logging.getLogger("iposonic-browse")

#
# List music collections
#


@app.route("/rest/getMusicFolders.view", methods=['GET', 'POST'])
def get_music_folders_view():
    """Return all music folders."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    return request.formatter(
        {'musicFolders': {'musicFolder':
                          [
                          {
                          'id': MediaManager.get_entry_id(d),
                          'name': d
                          } for d in iposonic.get_music_folders() if os.path.isdir(d)
                          ]
                          }}
    )


@app.route("/rest/getIndexes.view", methods=['GET', 'POST'])
def get_indexes_view():
    """Return subsonic indexes.

        params:
          - ifModifiedSince=0
          - musicFolderId=591521045

        xml response:
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

        jsonp response
            ...

        TODO implement @param musicFolderId
        TODO implement @param ifModifiedSince
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    # refresh indexes
    iposonic.refresh()

    #
    # XXX we should think to reimplement the
    #     DB in some consistent way before
    #     wasting time with unsearchable, dict-based
    #     data to format
    #
    return request.formatter({'indexes': iposonic.get_indexes()})


@app.route("/rest/getArtists.view")
def get_artists_view():
    """
    json response:
    {   artists:
        {  index: [
            {   name: A,
                    artist: [
                        {   id:,
                            name:,
                            coverArt:,
                            albumCount
                        },
                        {   id: ....}
                    ]
            },
            {   name: B, artist: [{},{}]}

        ]
        }
    }
    xml response:
    <artists>
        <index name="A">
            <artist id="5449" name="A-Ha" coverArt="ar-5449" albumCount="4"/>
            <artist id="5421" name="ABBA" coverArt="ar-5421" albumCount="6"/>
            <artist id="5432" name="AC/DC" coverArt="ar-5432" albumCount="15"/>
            <artist id="6633" name="Aaron Neville" coverArt="ar-6633" albumCount="1"/>
        </index>
        <index name="B">
            <artist id="5950" name="Bob Marley" coverArt="ar-5950" albumCount="8"/>
            <artist id="5957" name="Bruce Dickinson" coverArt="ar-5957" albumCount="2"/>
        </index>
    </artists>
    """
    raise NotImplementedError()


@app.route("/rest/getArtists.view")
def get_artist_view():
    """
    <artist id="5432" name="AC/DC" coverArt="ar-5432" albumCount="15">
        <album id="11047" name="Back In Black" coverArt="al-11047" songCount="10" created="2004-11-08T23:33:11" duration="2534" artist="AC/DC" artistId="5432"/>
    """
    raise NotImplementedError()


@app.route("/rest/getMusicDirectory.view", methods=['GET', 'POST'])
def get_music_directory_view():
    """Return the content of a directory.

      params:
        - id=-493506601
        -

      xml response 1:
          <directory id="1" name="ABBA">
            <child id="11"
                parent="1"
                title="Arrival"
                artist="ABBA"
                isDir="true"
                coverArt="22"/>
            <child id="12"
                parent="1"
                title="Super Trouper"
                artist="ABBA"
                isDir="true"
                coverArt="23"/>
          </directory>

      xml response 2:
          <directory id="11" parent="1" name="Arrival">
            <child id="111"
                parent="11"
                title="Dancing Queen"
                isDir="false"
                album="Arrival"
                artist="ABBA"
                track="7"
                year="1978"
                genre="Pop"
                coverArt="24"
                size="8421341"
                contentType="audio/mpeg"
                suffix="mp3"
                duration="146"
                bitRate="128"
                path="ABBA/Arrival/Dancing Queen.mp3"/>

            <child id="112"
                parent="11"
                ... # se above
                contentType="audio/flac"
                suffix="flac"
                transcodedContentType="audio/mpeg"
                transcodedSuffix="mp3"
                duration="208"
                bitRate="128"
                />
          </directory>

        jsonp response
    """
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])

    if not dir_id:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in getMusicDirectory.view")
    (path, dir_path) = iposonic.get_directory_path_by_id(dir_id)
    children = []
    artist = iposonic.db.Artist(path)
    #
    # if nothing changed before our last visit
    #    or is a virtual path (eg. uniexistent)
    #    don't rescan
    #
    try:
        last_modified = os.stat(dir_path).st_ctime
    except:
        last_modified = -1

    if last_modified == -1:
        print "Getting items from valbum."
        children = iposonic.get_songs(query={'albumId': dir_id})
    elif fs_cache.get(dir_id, 0) == last_modified:
        print "Getting items from cache."
        children = iposonic.get_songs(query={'parent': dir_id})
        children.extend(iposonic.get_albums(query={'parent': dir_id}))
    else:
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
        fs_cache.setdefault(dir_id, last_modified)

    def _track_or_die(x):
        try:
            return int(x['track'])
        except:
            return 0
    # Sort songs by track id, if possible
    children = sorted(children, key=_track_or_die)

    return request.formatter(
        {'directory': {
            'id': dir_id,
            'name': artist.get('name'),
            'child': children
        }
        })


#
# Search
#
@app.route("/rest/search2.view", methods=['GET', 'POST'])
def search2_view():
    """Search songs in archive.

        params:
          - query=Mannoia
          - artistCount=10  TODO
          - albumCount=20   TODO
          - songCount=25    TODO

        xml response:
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
    #songs = [{'song': s} for s in ret['title']]
    #songs.extend([{'album': a} for a in ret['album']])
    #songs.extend([{'artist': a} for a in ret['artist']])
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


@app.route("/rest/getStarred.view", methods=['GET', 'POST'])
def get_starred_view():
    """
        xml response
            <starred>
                <artist name="Kvelertak" id="143408"/>
                <artist name="Dimmu Borgir" id="143402"/>
                <artist name="Iron Maiden" id="143403"/>
                <album id="143862"
                        ... # album attributes
                       created="2011-02-26T10:45:30"
                       starred="2012-04-05T18:40:08"/>
                <album id="143888"
                        ... # album attributes
                        created="2011-03-23T09:29:13"
                        starred="2012-04-05T18:40:02"/>
                <song id="143588"
                        ... # song attributes
                        created="2010-09-27T20:52:23"
                        starred="2012-04-02T17:17:01"
                      albumId="163" artistId="133" type="music"/>
                <song id="143600" parent="143386" title="Satellite 15....The Final Frontier"
                      album="The Final Frontier (Mission Edition)" artist="Iron Maiden" isDir="false" coverArt="143386"
                      created="2010-08-16T21:08:01" starred="2012-04-02T14:12:54" duration="521" bitRate="320" track="1"
                      year="2010" genre="Heavy Metal" size="21855635" suffix="mp3" contentType="audio/mpeg" isVideo="false"
                      path="Iron Maiden/2010 The Final Frontier/01 Satellite 15....The Final Frontier.mp3" albumId="156"
                      artistId="126" type="music"/>
                <song id="143604" parent="143386" title="The Alchemist" album="The Final Frontier (Mission Edition)"
                      artist="Iron Maiden" isDir="false" coverArt="143386" created="2010-08-16T21:07:51"
                      starred="2012-04-02T14:12:52" duration="269" bitRate="320" track="5" year="2010" genre="Heavy Metal"
                      size="11774455" suffix="mp3" contentType="audio/mpeg" isVideo="false"
                      path="Iron Maiden/2010 The Final Frontier/05 The Alchemist.mp3" albumId="156" artistId="126"
                      type="music"/>
            </starred>
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (artistCount, albumCount, songCount) = map(
        request.args.get, ["artistCount", "albumCount", "songCount"])

    ret = iposonic.get_starred(query, artistCount, albumCount, songCount)
    print "ret: %s" % ret
    return request.formatter(
        {
            'starred': {
                'song': ret['title'],
                'album': ret['album'],
                'artist': ret['artist']
            }
        }
    )

    raise NotImplementedError()

#
# Extras
#


@app.route("/rest/getAlbumList.view", methods=['GET', 'POST'])
def get_album_list_view():
    """Get albums

        params:
           - type   in random,
                    newest,     TODO
                    highest,    TODO
                    frequent,   TODO
                    recent,     TODO
                    starred,    TODO
                    alphabeticalByName, TODO
                    alphabeticalByArtist TODO
           - size   items to return TODO
           - offset paging offset   TODO

        xml response:
            <albumList>
                <album id="11" parent="1" title="Arrival" artist="ABBA" isDir="true" coverArt="22" userRating="4" averageRating="4.5"/>
                <album id="12" parent="1" title="Super Trouper" artist="ABBA" isDir="true" coverArt="23" averageRating="4.4"/>
            </albumList>
    """
    (u, p, v, c, f, callback, dir_id) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])
    (size, type_a, offset) = map(request.args.get, ['size', 'type', 'offset'])

    if not type_a in ['random', 'newest', 'highest', 'frequent', 'recent']:
        raise SubsonicProtocolException("Invalid or missing parameter: type")

    if not size:
        size = 20

    if type_a == 'random':
        albums = randomize2_list(iposonic.get_albums(), size)
    elif type_a == 'highest':
        albums = iposonic.get_albums()[:size]
    else:
        albums = [a for a in iposonic.get_albums()]

    return request.formatter({'albumList': {'album': albums}})


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
        assert all_songs
        songs = randomize2_list(all_songs)
    assert songs
    # add cover art
    songs = [x.update({'coverArt': x.get('id')}) or x for x in songs]
    return request.formatter({'randomSongs': {'song': songs}})
