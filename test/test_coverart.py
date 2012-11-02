from __future__ import unicode_literals

from nose import *
from mediamanager import *
import os

from iposonic import IposonicDB, UnsupportedMediaError
from mediamanager.cover_art import q, cover_art_worker


def harn_get_cover_art_file(info):
    """Ritorna una lista di possibili valori per la cover."""
    covers = []
    # id3 info
    covers.append(MediaManager.cover_art_uuid(info))

    # path info
    p = info.get('path')
    covers.append(MediaManager.uuid(p[p.rfind("/", 2):]))

    return covers


def test_worker():
    path = "/opt/music/Evanescence/"
    dirs = ["Anywhere But Home", "Evanescence EP", "Fallen",
            "Mystary (EP) - 2003", "Origin", "Sound Asleep", "The Open Door"]
    cover_search = lambda x: {'cover_small': 'http://x'}
    for f in dirs:
        f = os.path.join("/", path, f)

        info = IposonicDB.Album(f)
        q.put(info)
    q.put(None)
    cover_art_worker("/tmp/", cover_search=cover_search)
