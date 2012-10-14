#
# Views for managing album/song lists
#
#
import logging
from flask import request
from webapp import app, randomize2_list, randomize_list
from iposonic import SubsonicMissingParameterException, SubsonicProtocolException, IposonicException
from mediamanager import MediaManager, UnsupportedMediaError

log = logging.getLogger('list-view')


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

    ret = app.iposonic.get_starred(query, artistCount, albumCount, songCount)
    print("ret: %s" % ret)
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

    if not type_a in ['random', 'newest', 'highest', 'frequent', 'recent', 'starred']:
        raise SubsonicProtocolException("Invalid or missing parameter: type")

    if not size:
        size = 20
    if not offset:
        offset = 0

    if type_a == 'random':
        log.info("getting ", type_a)
        albums = app.iposonic.get_albums()
        albums = randomize2_list(albums, size)
    elif type_a == 'highest':
        log.info("getting ", type_a)
        albums = app.iposonic.get_albums(
            query={'userRating': 'notNull'}, order=('userRating', 1))
    elif type_a == 'newest':
        log.info("getting ", type_a)
        albums = app.iposonic.get_albums(
            query={'created': 'notNull'}, order=('created', 1))
    elif type_a == 'starred':
        log.info("getting ", type_a)
        albums = app.iposonic.get_albums(query={'starred': 'notNull'})
    else:
        # get all albums...hey, they may be a lot!
        albums = [a for a in app.iposonic.get_albums()]

    last = min(offset + size, len(albums) - 1)
    return request.formatter({'albumList': {'album': albums[offset:last]}})


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
        print("genre: %s" % genre)
        songs = app.iposonic.get_genre_songs(genre.strip().lower())
    else:
        all_songs = app.iposonic.get_songs()
        assert all_songs
        songs = randomize2_list(all_songs)

    # add cover art
    songs = [x.update({'coverArt': x.get('id')}) or x for x in songs]
    return request.formatter({'randomSongs': {'song': songs}})
