"""Test harnesses"""

from os.path import join
from os import getcwd, walk
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def harn_setup_dbhandler_and_scan_directory(klass, test_dir, add_songs=True, dbfile="mock_db"):
    """Setup the Iposonic dbhandler eventually adding songs to the DB.
        
        TODO pass db credential
    """
    log.info("setup dbhandler")
    klass.test_dir = getcwd() + test_dir
    klass.db = klass.dbhandler(
        [klass.test_dir], dbfile=dbfile)
    #klass.db.recreate_db = True
    klass.db.init_db()
    #klass.db.reset() do not reset from here!
    if add_songs:
        harn_scan_music_directory(klass)
    log.info("setup dbhandler ok")


def harn_scan_music_directory(klass):
    log.info("adding song and scanning path")
    # mock some test variables
    if not 'test_dir' in klass.__dict__:
        klass.__dict__.setdefault('test_dir', klass.music_folders[0])
    klass.__dict__.setdefault('id_albums', [])
    klass.__dict__.setdefault('id_songs', [])
    for (root, dirfile, files) in walk(klass.test_dir):
        for d in dirfile:
            path = join("/", root, d)
            klass.id_albums.append(
                klass.db.add_path(path, album=(root is not klass.test_dir)))
        for f in files:
            path = join("/", root, f)
            klass.id_songs.append(klass.db.add_path(path))
            
def harn_create_users(iposonic_klass):
        for unames in ["mock_user%s" % s for s in ['', 1, 2, 3]]:
            item = {
                'username': unames,
                'password': 'mock_password',
                'scrobbleUser': 'ioggstream',
                'scrobblePassword': 'secret'
            }
            iposonic_klass.add_user(item)
