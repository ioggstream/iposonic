"""Test harnesses"""

from os.path import join
from os import getcwd, walk
import logging
logging.basicConfig()


def harn_setup(klass, test_dir, add_songs=True, dbfile=""):
    """Setup the Iposonic dbhandler eventually adding songs to the DB."""
    klass.test_dir = getcwd() + test_dir
    klass.db = klass.dbhandler(
        [klass.test_dir], dbfile=dbfile)
    klass.db.init_db()
    klass.db.reset()
    if add_songs:
        harn_load_fs2(klass)


def harn_load_fs2(klass):
    for (root, dirfile, files) in walk(klass.test_dir):
        for d in dirfile:
            path = join("/", root, d)
            klass.id_albums.append(
                klass.db.add_path(path, album=(root is not klass.test_dir)))
        for f in files:
            path = join("/", root, f)
            klass.id_songs.append(klass.db.add_path(path))