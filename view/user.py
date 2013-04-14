#
# Views for managing playlists
#
#
from flask import request, abort
from webapp import app
from mediamanager import MediaManager

import logging
log = logging.getLogger('view.user')
#
# TO BE DONE
#


@app.route("/rest/getUser.view", methods=['GET', 'POST'])
def get_user_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    user = {'username': u,
            'email': u,
            'scrobblingEnabled': True,
            'adminRole': False,
            'settingsRole': True,
            'downloadRole': True,
            'uploadRole': True,
            'playlistRole': True,
            'coverArtRole': True,
            'commentRole': True,
            'podcastRole': True,
            'streamRole': True,
            'jukeboxRole': True,
            'sharedRole': False
            }

    return request.formatter({'user': user})


@app.route("/rest/createUser.view", methods=['GET', 'POST'])
def create_user_view():
    """Create an user getting info from GET variables.

        TODO get with post too
    """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])

    (un, pw, email, scrobbleUser, scrobblePassword) = map(request.args.get, [
                                                          'x',
                                                          'password',
                                                          'email',
                                                          'scrobbleUser',
                                                          'scrobblePassword'
                                                          ])
    new_user = {
        'username': un,
        'password': pw,
        'email': email,
        'scrobbleUser': scrobbleUser,
        'scrobblePassword': scrobblePassword
    }
    log.warn("adding user: %s " % new_user)
    app.iposonic.add_user(new_user)
    return request.formatter({})

@app.route("/rest/updateUser.view", methods=['GET', 'POST'])
def update_user_view():
    """Update an user getting info from GET variables.

        IMPORTANT: this method does not exist in Subsonic API
        TODO get with post too
    """
    (u, p, v, c, f, callback, eid) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback','id'])
    
    new_user = { k: request.args.get(k) for k in [
                                                          'password',
                                                          'email',
                                                          'scrobbleUser',
                                                          'scrobblePassword',
                                                          'nowPlaying'
                                                          ] if request.args.get(k)
                }
    log.info("updating with the following fields: %r" % new_user)
    new_user = app.iposonic.db.update_user(eid=eid, new=new_user)
    log.warn("updated user: %s " % new_user)
    return request.formatter({})


@app.route("/rest/deleteUser.view", methods=['GET', 'POST'])
def delete_user_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    raise NotImplementedError()


@app.route("/rest/getUsers.view", methods=['GET', 'POST'])
def get_users_view():
    """List all users in database."""
    (u, p, v, c, f, callback, eid) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])
    ret = app.iposonic.db.get_users(eid=eid)
    return request.formatter({'users': {'user': ret}})


@app.route("/rest/changePassword.view", methods=['GET', 'POST'])
def change_password_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    raise NotImplementedError()


@app.route("/rest/getNowPlaying.view", methods=['GET', 'POST'])
def get_now_playing_view():
    """TODO: save timestamp and song duration of every stream.view request

        xml response:
            <nowPlaying>
                <entry username="sindre"
                    minutesAgo="12"
                    playerId="2"
                    ... # all media properties />

                <entry username="bente"
                    minutesAgo="1"
                    playerId="4"
                    playerName="Kitchen"
                    ... # all media properties
                />
            </nowPlaying>
        """
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    user = app.iposonic.get_users(eid=MediaManager.uuid(u))
    assert user.get('nowPlaying'), "Nothing playing now..."

    song = app.iposonic.get_songs(eid=user.get('nowPlaying'))
    song.update({'username': u})

    return request.formatter({'nowPlaying': {'entry': song}})


@app.route("/rest/setNowPlaying.view", methods=['GET', 'POST'])
def set_now_playing_view():
    """TODO: save timestamp and song duration of every stream.view request
        """
    (u, p, v, c, f, callback, eid) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback', 'id'])

    log.info("Update nowPlaying: %s for user: %s -> %s" % (eid,
             u, MediaManager.uuid(u)))
    app.iposonic.db.update_user(eid=MediaManager.uuid(u), new={
                                                                  'nowPlaying' : eid
                                                                  })
    return request.formatter({})
