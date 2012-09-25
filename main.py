#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Flask part of iposonic
#
# author: Roberto Polli robipolli@gmail.com (c) 2012
#
# License AGPLv3
#
# TODO manage argv for:
#   * music_folders
#   * authentication backend
#   * reset db
#

import logging
#logging.basicConfig(level=logging.INFO)

import sys
import os
import thread
from flask import Flask, g
from iposonic import Iposonic

from webapp import iposonic
from webapp import tmp_dir, cache_dir, music_folders

from webapp import app, log

import view_browse
import view_playlist
import view_user
import view_media

try:
    # profiling
#    import yappi
    import signal
    import sys

    def signal_handler(signal, frame):
            print 'You pressed Ctrl+C!'
            yappi.stop()
            yappi.print_stats(open("yappi.out", "w"))
            sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    yappi.start()
except:
    pass


def run(argc, argv):
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


if __name__ == "__main__":
    argc, argv = len(sys.argv), sys.argv
    run(argc, argv)
