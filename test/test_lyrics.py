from __future__ import unicode_literals
from nose import *
from mediamanager.lyrics import ChartLyrics


def test_get_lyrics():
    info = {'artist': 'Evanescence', 'title': 'Snow White Queen'}
    c = ChartLyrics()

    lyrics = c.search(info)
    assert lyrics
    print ("lyrics: " + lyrics)
