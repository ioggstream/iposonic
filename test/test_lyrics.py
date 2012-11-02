from __future__ import unicode_literals
from nose import *
from mediamanager.lyrics import ChartLyrics
import logging
log = logging.getLogger(__name__)


def test_get_lyrics():
    info = {'artist': 'Evanescence', 'title': 'Snow White Queen'}
    c = ChartLyrics()

    lyrics = c.search(info)
    assert lyrics
    log.info ("lyrics: %s" % lyrics)
