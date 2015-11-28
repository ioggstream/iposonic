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
#
from __future__ import unicode_literals
import config
import logging
logging.basicConfig(level=config.loglevel)

import sys
import os
os.path.supports_unicode_filenames = True
import argparse
from threading import Thread

from iposonic import Iposonic

from webapp import app, log
from authorizer import Authorizer

# Import all app views
#  TODO move to a view module
import view.browse
import view.playlist
import view.user
import view.media
import view.list
import view.db


def yappize():
    try:
        # profiling
        import yappi
        import signal

        def signal_handler(signal_n, frame):
            print('You pressed Ctrl+C!')
            yappi.stop()
            yappi.print_stats(open("yappi.out", "w"))
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

        yappi.start()
    except:
        pass


def run(argc, argv):

    parser = argparse.ArgumentParser(
        description='Iposonic is a SubSonic compatible streaming server.'
        + 'Run with #python ./__main__.py -c /opt/music')
    parser.add_argument('-c', dest='collection', metavar=None, type=str,
                        nargs="+", required=True,
                        help='Music collection path')
    parser.add_argument('-t', dest='tmp_dir', metavar=None, type=str,
                        nargs=None, default=os.path.expanduser('~/.iposonic'),
                        help='Temporary directory, defaults to ~/.iposonic')
    
    parser.add_argument(
        '--access-file', dest='access_file', action=None, type=str,
        default=os.path.expanduser('~/.iposonic_auth'),
        help='Access file for user authentication, defaults to ~/.iposonic_auth. Use --noauth to disable authentication.')
    parser.add_argument(
        '--noauth', dest='noauth', action=None, type=bool,
        nargs='?', const=True, default=False,
        help='Disable authentication.')

    parser.add_argument(
        '--free-coverart', dest='free_coverart', action=None, type=bool,
        const=True, default=False, nargs='?',
        help='Do not authenticate requests to getCoverArt. Default is False: iposonic requires authentication for every request.')
    parser.add_argument('--resetdb', dest='resetdb', action=None, type=bool,
                        const=True, default=False, nargs='?',
                        help='Drop database and cache directories and recreate them.')
    parser.add_argument(
        '--rename-non-utf8', dest='rename_non_utf8', action=None, type=bool,
        const=True, default=False, nargs='?',
        help='Rename non utf8 files to utf8 guessing encoding. When false, iposonic support only utf8 filenames.')

    # host, port and execution options
    parser.add_argument('-s', dest='server', metavar=None, type=str,
                        nargs=None, required=False, default='127.0.0.1',
                        help='server host (default 0.0.0.0)')
    parser.add_argument('-p', dest='port', metavar=None, type=int,
                        nargs=None, required=False, default=5000,
                        help='server port (default 5000)')
    
    parser.add_argument('--profile', metavar=None, type=bool,
                        nargs='?', const=True, default=False,
                        help='profile with yappi')
    parser.add_argument('--wsgi', metavar=None, type=bool,
                        nargs='?', const=True, default=False,
                        help='run with CherryPy containter')
    parser.add_argument('--db', dest='dbstring', metavar=None, type=str,
                    nargs=None, required=False, default='mysql',
                    help='server host (default 0.0.0.0)')
    args = parser.parse_args()
    print(args)

    if args.profile:
        yappize()

    app.config.update(args.__dict__)

    for x in args.collection:
        assert(os.path.isdir(x)), "Missing music folder: %s" % x

    try:
        if args.dbstring == 'mysql':
            from datamanager.mysql import MySQLIposonicDB as Dbh
        elif args.dbstring == 'sqlite':
            from datamanager.sqlite import SqliteIposonicDB as Dbh
        else:
            raise ImportError('Pick a supported db')
    except ImportError:
            from datamanager.inmemory import MemoryIposonicDB as Dbh

    app.iposonic = Iposonic(args.collection, 
                            dbhandler=Dbh,
                            recreate_db=args.resetdb, 
                            tmp_dir=args.tmp_dir)
    app.iposonic.db.init_db()

    # While developing don't enforce authentication
    #   otherwise you can use a credential file
    #   or specify your users inline
    skip_authentication = args.noauth
    app.authorizer = Authorizer(
        mock=skip_authentication, access_file=args.access_file)

    #
    # Run cover_art downloading thread
    #
    from mediamanager.cover_art import cover_art_worker, cover_art_mock
    for i in range(1):
        t = Thread(target=cover_art_worker, args=[app.iposonic.cache_dir])
        t.daemon = True
        t.start()

    #
    # Run scrobbling thread
    #
    try:
        from mediamanager.scrobble import scrobble_worker
        for i in range(1):
            t = Thread(target=scrobble_worker, args=[])
            t.daemon = True
            t.start()
    except:
        log.exception("Cannot enable scrobbling. Please install pylast library with # pip install pylast")
    #
    # Run walker thread
    #
    from scanner import walk_music_folder
    for i in range(1):
        t = Thread(target=walk_music_folder, args=[app.iposonic])
        t.daemon = True
        t.start()

    if args.wsgi:
        from cherrypy import wsgiserver
        d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
        server = wsgiserver.CherryPyWSGIServer((args.server, args.port), d)
    
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
    else:
        app.run(host=args.server, port=args.port, debug=True)

if __name__ == "__main__":
    argc, argv = len(sys.argv), sys.argv
    run(argc, argv)
