#
# Views for managing playlists
#
#
from flask import request, abort
from webapp import app
from mediamanager import MediaManager, UnsupportedMediaError
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
    """TODO return a mock username settings."""
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
    print("user: %s " % new_user)
    app.iposonic.add_user(new_user)
    raise NotImplementedError()


@app.route("/rest/deleteUser.view", methods=['GET', 'POST'])
def delete_user_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    raise NotImplementedError()


@app.route("/rest/getUsers.view", methods=['GET', 'POST'])
def get_users_view():
    """TODO return a mock username settings."""
    (u, p, v, c, f, callback) = map(
        request.args.get, ['u', 'p', 'v', 'c', 'f', 'callback'])
    ret = app.iposonic.db.get_users()
    return request.formatter({'users': { 'user': ret }})



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
    
    return request.formatter({'nowPlaying': {'entry': song} })
