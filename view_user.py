#
# Views for managing playlists
#
#
from flask import request
from webapp import iposonic, app
from mediamanager import MediaManager, StringUtils, UnsupportedMediaError
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
