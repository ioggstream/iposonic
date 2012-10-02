# *-* coding: utf-8 *-*
#
# Views for downloading songs
#
#
from __future__ import unicode_literals

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("iposonic-browse")

import os
from os.path import join
os.path.supports_unicode_filenames = True

from flask import request, send_file
from webapp import app, fs_cache
from webapp import randomize2_list
from iposonic import IposonicException, SubsonicProtocolException
import mediamanager
from mediamanager import MediaManager
from mediamanager.stringutils import isdir, to_unicode


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
                          'id': MediaManager.uuid(d),
                          'name': d
                          } for d in app.iposonic.get_music_folders() if isdir(d)
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
    app.iposonic.refresh()

    #
    # XXX we should think to reimplement the
    #     DB in some consistent way before
    #     wasting time with unsearchable, dict-based
    #     data to format
    #
    return request.formatter({'indexes': app.iposonic.get_indexes()})


@app.route("/rest/getArtists.view", methods=['GET', 'POST'])
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


@app.route("/rest/getArtists.view", methods=['GET', 'POST'])
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
    (path, dir_path) = app.iposonic.get_directory_path_by_id(dir_id)
    children = []
    artist = app.iposonic.db.Artist(path)
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
        children = app.iposonic.get_songs(query={'albumId': dir_id})
    elif fs_cache.get(dir_id, 0) == last_modified:
        print "Getting items from cache."
        children = app.iposonic.get_songs(query={'parent': dir_id})
        children.extend(app.iposonic.get_albums(query={'parent': dir_id}))
    else:
        for child in os.listdir(unicode(dir_path)):
            # TODO find a way to support non-unicode directories and
            #    folders. The easiest way is to simply RENAME THEM!
            #    ................
            print "checking string type: ", type(child)
            #child = to_unicode(child)
            if child[0] in ['.', '_']:
                continue

            #
            # To manage non-utf8 filenames
            # the easiest thing is to rename
            # paths in utf.
            #
            # This may cause issues for collections
            # stored on windows or vfat filesystem.
            #
            # This is the KISS-siest approach
            # that avoids continuously encode
            # and decode of the filenames.
            #
            if not isinstance(child, unicode):
                if not app.config.get('rename_non_utf8'):
                    app.log.warn(
                        "skipping non unicode path: %s " % to_unicode(child))
                    continue
                child_new = to_unicode(child)
                os.rename(
                    b'%s/%s' % (dir_path.encode('utf-8'), child),
                    u'%s/%s' % (dir_path, child_new)
                )
                child = child_new

            path = join(dir_path, child)
            try:
                child_j = {}
                is_dir = isdir(path)
                # This is a Lazy Indexing. It should not be there
                #   unless a cache is set
                # XXX
                eid = MediaManager.uuid(path)
                try:
                    child_j = app.iposonic.get_entry_by_id(eid)
                except IposonicException:
                    app.iposonic.add_entry(path, album=is_dir)
                    child_j = app.iposonic.get_entry_by_id(eid)

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
    ret = app.iposonic.search2(query, artistCount, albumCount, songCount)
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
