#!/usr/bin/env python
#
# Code imported from coverart
#    https://github.com/jmcantrell/coverart/blob/master/coverart/sources/lastfmcovers.py
#
import sys
import re
import os
import time
import logging
from urllib import urlopen, quote_plus
from xml.etree.ElementTree import parse
from iposonic import IposonicException
from mediamanager import MediaManager
from threading import Thread
from Queue import Queue

q = Queue()

log = logging.getLogger(__name__)


class CoverSource(object):
    """Download cover art from url_base."""
    def __init__(self):
        self.max_results = 10
        self.source_name = 'Last.FM'
        self.api_key = '2f63459bcb2578a277c5cf5ec4ca62f7'
        self.url_base = 'http://ws.audioscrobbler.com/2.0/?method=album.search&api_key=%s' % self.api_key

    def search(self, query):
        url = '%s&album=%s' % (
            self.url_base, quote_plus('%s' % query.encode('utf-8')))
        tree = parse(urlopen(url))
        count = 0
        for a in tree.findall('results/albummatches/album'):
            result = {}
            result['album'] = a.findtext('name')
            result['artist'] = a.findtext('artist')
            for i in a.findall('image'):
                size = i.get('size')
                if size == 'extralarge':
                    result['cover_large'] = i.text
                elif size == 'large':
                    result['cover_small'] = i.text
            if 'cover_large' not in result:
                continue
            if 'cover_small' not in result:
                result['cover_small'] = result['cover_large']
            count += 1
            yield result
            if count == self.max_results:
                break


def memorize(f):
    cache2 = dict()

    """The memorize pattern is a simple cache implementation.

        It requires that te underlying function takes two
        parameters: f(eid, nocache=False).
    """
    def tmp(eid, nocache=False):
        try:
            if not nocache:
                (item, ts) = cache2[eid]
                if item:
                    return item
                # retry after 60sec in case
                #    of empty items
                if ts + 60 < time.time():
                    return item

        except KeyError:
            pass

        try:
            cache2[eid] = (f(eid, nocache=nocache), time.time())
        except IposonicException:
            cache2[eid] = (None, time.time())

        return cache2[eid][0]
    return tmp


@memorize
def cover_search(album, nocache=False):
    """Download album info from the web.

        This class implements the @memorize pattern
        to reduce web access.
    """
    ret = None
    if album:
        log.info("Searching the web for album: %s" % album)

        c = CoverSource()
        # search lowercase to increase
        # cache hits
        ret = c.search(album.lower())

        # don't return empty arrays
        if ret:
            return ret
    return ret


def cover_art_mock(cache_dir, cover_searc=cover_search):
    while True:
        log.info("cover_art_mock: %s" % q.get())


def cover_art_worker(cache_dir, cover_search=cover_search):
    log.info("starting downloader thread with tmp_dir: %s" % cache_dir)
    info = True
    while info:
        info = q.get()
        try:
            cover_art_path = os.path.join("/",
                                          cache_dir,
                                          MediaManager.cover_art_uuid(info)
                                          )
            log.info("coverart %s: searching album: %s " % (
                info.get('id'), info.get('album')))
            covers = cover_search(info.get('album'))
            for cover in covers:
                # TODO consider multiple authors in info
                #  ex. Actually "U2 & Frank Sinatra" != "U2"
                #      leads to a false negative
                # TODO con
                print "confronting info: %s with: %s" % (info, cover)
                normalize_info, normalize_cover = map(
                    MediaManager.normalize_artist, [info, cover])
                full_match = len(set([normalize_info, normalize_cover])) == 1
                stopwords_match = len(set([MediaManager.normalize_artist(
                    x, stopwords=True) for x in [info, cover]])) == 1

                partial_match = len(
                    [x for x in normalize_info if x not in normalize_cover]) == 0
                if full_match or stopwords_match or partial_match:
                    log.warn("Saving image %s -> %s" % (
                        cover.get('cover_small'), cover_art_path)
                    )
                    fd = open(cover_art_path, "w")
                    fd.write(urlopen(cover.get('cover_small')).read())
                    fd.close()

                else:
                    log.info("Artist mismatch: %s, %s" % tuple(
                        [x.get('artist', x.get('name')) for x in [info, cover]])
                    )
        except Exception as e:
            log.error("Error while downloading albumart.", e)

        q.task_done()
    log.warn("finish download thread")
