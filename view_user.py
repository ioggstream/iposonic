#
# Views for managing playlists
#
#
from flask import request, abort
from webapp import app
from mediamanager import MediaManager, stringutils, UnsupportedMediaError
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


@app.route("/rest/getNowPlaying.view")
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
    abort(404)
    raise NotImplementedError()
