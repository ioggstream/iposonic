#
# Views for managing playlists
#
#
from flask import request
from webapp import app, randomize2_list
from iposonic import SubsonicMissingParameterException, SubsonicProtocolException, IposonicException
from mediamanager import MediaManager, UnsupportedMediaError

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

    playlists = app.iposonic.get_playlists_static()

    playlists.extend(app.iposonic.get_playlists())
    return request.formatter({'status': 'ok', 'playlists': {'playlist': playlists}})


@app.route("/rest/getPlaylist.view", methods=['GET', 'POST'])
def get_playlist_view():
    """Return a playlist.

        response xml:
     <playlist id="15" name="kokos" comment="fan" owner="admin" public="true" songCount="6" duration="1391"
                     created="2012-04-17T19:53:44">
               <allowedUser>sindre</allowedUser>
               <allowedUser>john</allowedUser>
               <entry id="657" parent="655" title="Making Me Nervous" album="I Don&apos;t Know What I&apos;m Doing"
                      artist="Brad Sucks" isDir="false" coverArt="655" created="2008-04-10T07:10:32" duration="159"
                     bitRate="202" track="1" year="2003" size="4060113" suffix="mp3" contentType="audio/mpeg" isVideo="false"
                     path="Brad Sucks/I Don&apos;t Know What I&apos;m Doing/01 - Making Me Nervous.mp3" albumId="58"
                     artistId="45" type="music"/>
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

        TODO move database objects to app.iposonicdb. They  shouldn't be
                exposed outside.
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    eid = request.args.get('id')
    if not eid:
        raise SubsonicProtocolException(
            "Missing required parameter: 'id' in stream.view")

    entries = []
    # use default playlists
    if eid == MediaManager.uuid('starred'):
        j_playlist = app.iposonic.get_playlists_static(eid=eid)
        songs = app.iposonic.get_starred().get('title')
        entries = randomize2_list(songs, 5)
    elif eid in [x.get('id') for x in app.iposonic.get_playlists_static()]:
        j_playlist = app.iposonic.get_playlists_static(eid=eid)
        entries = randomize2_list(app.iposonic.get_songs())
    else:
        playlist = app.iposonic.get_playlists(eid=eid)
        assert playlist, "Playlists: %s" % app.iposonic.db.playlists
        print("found playlist: %s" % playlist)
        entry_ids = playlist.get('entry')
        if entry_ids:
            entries = [x for x in app.iposonic.get_song_list(
                entry_ids.split(","))]
        j_playlist = playlist
    # format output
    assert entries, "Missing entries: %s" % entries
    log.info("Entries retrieved: %r", entries)
    j_playlist.update({
        'entry': entries,
        'songCount': len(entries),
        'duration': sum([x.get('duration', 0) for x in entries])
    })
    return request.formatter({'status': 'ok', 'playlist': j_playlist})


@app.route("/rest/createPlaylist.view", methods=['GET', 'POST'])
def create_playlist_view():
    """TODO move to app.iposonic

        request body:
            name=2012-09-08&
            songId=-2072958145&
            songId=-2021195453&
            songId=-1785884780

    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (name, playlistId) = map(request.values.get, ['name', 'playlistId'])
    songId_l = request.values.getlist('songId')
    log.info("songId: %s", songId_l)
    if not (name or playlistId):
        log.info("request: %s", request.data)
        raise SubsonicMissingParameterException(
            'id or playlistId', 'create_playlist_view')

    # create a new playlist
    if not playlistId:
        eid = MediaManager.uuid(name)
        try:
            playlist = app.iposonic.get_playlists(eid=eid)
            raise IposonicException("Playlist esistente")
        except:
            pass
        # TODO DAO should not be exposed
        playlist = app.iposonic.db.Playlist(name)
        playlist.update({'entry': ",".join(songId_l)})
        app.iposonic.create_entry(playlist)

    # update
    else:
        playlist = app.iposonic.get_playlists(eid=playlistId)
        assert playlist
        songs = playlist.get('entry')
        songs += ",".join(songId_l)
        app.iposonic.update_entry(eid=playlistId, new={'entry': songs})
    return request.formatter({'status': 'ok'})


@app.route("/rest/deletePlaylist.view", methods=['GET', 'POST'])
def delete_playlist_view():
    """TODO move to app.iposonic

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

    app.iposonic.delete_entry(eid=eid)
    return request.formatter({'status': 'ok'})
