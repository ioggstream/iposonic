#!/usr/bin/python
import sys
import os
import thread
from flask import Flask, g
from iposonic import Iposonic

from webapp import iposonic
from webapp import tmp_dir, cache_dir, music_folders

from webapp import app

import view_playlist
import view_user
import view_media

if __name__ == "__main__":
    argc, argv = len(sys.argv), sys.argv

    try:
        if argv[1] == '--reset':
            recreate_db = True
    except:
        recreate_db = False

    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    iposonic.db.init_db()
    print thread.get_ident(), "iposonic main @%s" % id(iposonic)
    app.run(host='0.0.0.0', port=5000, debug=True)
