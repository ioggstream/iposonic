
from mediamanager import MediaManager, stringutils
from os.path import basename, dirname


class ArtistDAO:
    __tablename__ = "artist"
    __fields__ = ['id', 'name', 'isDir', 'path', 'userRating',
                  'averageRating', 'coverArt', 'starred', 'created']

    def get_info(self, path_u):
        return {
            'id': MediaManager.uuid(path_u),
            'name': basename(path_u),
            'path': path_u,
            'isDir': 'true'
        }


class MediaDAO:
    __tablename__ = "song"
    __fields__ = ['id', 'name', 'path', 'parent',
                  'title', 'artist', 'isDir', 'album',
                  'genre', 'track', 'tracknumber', 'date', 'suffix',
                  'isvideo', 'duration', 'size', 'bitRate',
                  'userRating', 'averageRating', 'coverArt',
                  'starred', 'created', 'albumId', 'scrobbleId'  # scrobbleId is an internal parameter used to match songs with last.fm
                  ]


class AlbumDAO:
    __tablename__ = "album"
    __fields__ = ['id', 'name', 'isDir', 'path', 'title',
                      'parent', 'album', 'artist',
                      'userRating', 'averageRating', 'coverArt',
                      'starred', 'created'
                      ]

    def get_info(self, path):
        """TODO use path_u directly."""
        eid = MediaManager.uuid(path)
        path_u = stringutils.to_unicode(path)
        parent = dirname(path)
        dirname_u = MediaManager.get_album_name(path_u)
        return {
            'id': eid,
            'name': dirname_u,
            'isDir': 'true',
            'path': path_u,
            'title': dirname_u,
            'parent': MediaManager.uuid(parent),
            'album': dirname_u,
            'artist': basename(parent),
            'coverArt': eid
        }


class PlaylistDAO:
    __tablename__ = "playlist"
    __fields__ = ['id', 'name', 'comment', 'owner', 'public',
                      'songCount', 'duration', 'created', 'entry'
                      ]

    def get_info(self, name):
        return {
            'id': MediaManager.uuid(name),
            'name': name
        }


class UserDAO:
    __tablename__ = "user"
    __fields__ = ['id', 'username', 'password', 'email',
                  'scrobbleUser', 'scrobblePassword', 'nowPlaying']


class UserMediaDAO:
    """TODO use this table for storing per-user metadata.

        Each user should have his own media rating.
        Queries should get a list of uids from here, then
        fetch playlist content by mid.
    """
    __tablename__ = "usermedia"
    __fields__ = ['eid', 'uid', 'mid', 'userRating', 'starred']


