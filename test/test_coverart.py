from nose import *
from mediamanager import *
import os

from iposonic import IposonicDB, UnsupportedMediaError
from art_downloader import q, cover_art_worker


def get_cover_art_file(info):
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


def test_download_simple():
    path = "/opt/music/Evanescence/"
    dirs = ["Anywhere But Home", "Evanescence EP", "Fallen",
            "Mystary (EP) - 2003", "Origin", "Sound Asleep", "The Open Door"]
    for f in dirs:
        f = os.path.join("/", path, f)

        info = IposonicDB.Album(f)
        cover = MediaManager.cover_art_uuid(info)
        print "cover_art_info", cover, info.get('id')

        for s in os.listdir(f):
            try:
                s_info = IposonicDB.Media(os.path.join("/", f, s))
                s_cover = MediaManager.cover_art_uuid(s_info)
                print "cover_art_info", s_cover
                # Hp1: usare coverArt=song_id ci permette di
                #   trovare subito cover_uuid per l'album
                #   e il parent, ma colpisce due volte il db
                #   Limita il  caching
                # Hp2: impostare coverArt in fase di add_entry()
                #   se l'album non viene trovato e' impossibile
                #   prendere i dati della canzone.
                #   Non posso usare pero' il valore a prescindere
                #   a meno di non rinominare i file in modo che path
                #   e metadati corrispondano (eg. vedi collezioni)
                #   Cache ++
                # Hp3: usa Hp1 e salva il risultato su db ;)
                covers = get_cover_art_file(s_info)
                assert cover in covers, covers
                #assert s_cover == cover, "%s" % [
                #    map(s_info.get, ['artist','album']),
                #    map(info.get, ['artist','album'])
                #]
            except UnsupportedMediaError:
                pass
