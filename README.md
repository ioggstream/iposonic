iposonic
========

A tiny subsonic server api implementation with python + flask.
Supports:
	- coverArt search on the web
	- playlist add/delete
	- simple and customizable authentication
	- full-text search
	- optional database backends 
  
It works nicely for listing and playing your files with a subsonic client.
	- Android client
	- MiniSub and Perisonic

quickstart
==========
To run, just 
 * install flask and the other dependencies with
	# pip install flask
 * configure your mp3 directory in webapp.py
 * run with
	# python webapp.py


You can test methods adding some audio files in test/data/ and messing with nose


prerequisites
============
Required
 * pip install flask
 * pip install mutagen

Optional
 * pip install sqlalchemy 	# [optional if you want a permanent store]
 * pip install nose 		# [to test and develop]


big collections
===============

If you have big music collections, Iposonic supports local data indexing with
 * MySQL Embedded 	(library provided in this source, with full text search)
 * MySQL Server 	(configure it in MySQLIposonicDB class)
 * Sqlite		(thru sqlalchemy, but does not support full text search)
