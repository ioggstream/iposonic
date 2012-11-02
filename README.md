iposonic
========

A tiny subsonic server api implementation with python + flask.
Supports:
* coverArt search on the web
* playlist add / delete, 4 default dynamic meta - playlist(included starred and random)
* simple and customizable authentication
* mp3 down - sampling for streaming from GPRS / UMTS connections
* rating and starring
* full - text search songs and albums
* optional database backends

It works nicely for listing and playing your files with a subsonic client.
* Android client
* MiniSub and Perisonic

quickstart
==========
To run, just
* install flask and the other dependencies with
           # pip install flask
* configure your mp3 directory in webapp.py
* run with
           # python main.py -c /music/folder
* help yourself
           # python main.py --help


You can test methods adding some audio files in test / data / and messing with nose


prerequisites
============
Required
* pip install flask
* pip install mutagen
* pip install simplejson
* pip install argparse

Optional
* pip install sqlalchemy       # [optional if you want a permanent store]
* pip install MySQL - python     # [optional if you want MySQL support]
* pip install pylast             # [optional if you want to scrobble to last.fm]
* pip install nose             # [to test and develop]
* [apt - get | yum] install lame   # [optional if you want transcoding and down-sampling]

big collections
===============

If you have big music collections, Iposonic supports local data indexing with
* MySQL Embedded(library provided in this source, with full text search)
* MySQL Server(configure it in MySQLIposonicDB class)
* Sqlite(thru sqlalchemy, but does not support full text search)

scrobbling
==========

Scrobbling is enabled on development branches: lastfm and fs_thread

