#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3
from __future__ import unicode_literals
from nose import *

# standard libs
import os
import sys
import re
from os.path import join, basename, dirname

from mediamanager import MediaManager, stringutils

import logging
log = logging.getLogger("test")
logging.basicConfig(level=logging.INFO)


class TestMediaManager:
    def get_info_harn(self, file_name, expected):
        """Harness  for testing MediaManager.get_info
            - simulating iposonic getting file_name info and
            - checking for the expected keys
        """
        info = MediaManager.get_info(os.getcwd() + "/" + file_name)
        print("info: %s" % info)
        for f in expected.keys():
            assert info[f] == expected[f], "Mismatching field %s. Expected %s get %s" % (f, expected[f], info[f])

    def get_info_test_ogg(self):
        file_name = "./test/data/mock_artist/mock_album/sample.ogg"
        parent = dirname(file_name)

        expected = {
            'title': 'mock_title',
            'artist': 'mock_artist',
            'year': 'mock_year',
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3(self):
        file_name = "./test/data/lara.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)',
            'artist': 'Lara St John (PREVIEW: buy it at www.magnatune.com)',
            'bitRate': 128,
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3_2(self):
        file_name = "./test/data/Aretha Franklin/20 Greatest hits/Angel.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'Angel',
            'artist': 'Aretha Franklin',
            'bitRate': 128,
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3_3(self):
        file_name = "./test/data/edith_piaf/letoile_de_la_chanson/16_bal_dans_ma_rue.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'bal dans ma rue',
            'artist': 'Edith Piaf',
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3_noartist_nodir(self):
        file_name = "./test/data/noartist.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'noartist',
            'artist': 'WuMing',
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3_noartist_withdir(self):
        file_name = "./test/data/unexistent_artist/noartist.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'bal dans ma rue',
            'artist': 'Edith Piaf',
            'parent': MediaManager.uuid(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_wma(self):
        file_name = "./test/data/sample.wma"
        expected = {}
        self.get_info_harn(file_name, expected)

    @SkipTest
    def browse_path_test(self):
        MediaManager.browse_path("/opt/music")

    def test_get_album_name(self):
        for name in ['mock_album - 2004', 'mock_album (2004)', 'mock_album (Disk1)']:
            path_u = join("/", os.getcwd(), "test/data/mock_artist/", name)
            try:
                os.mkdir(path_u)
            except:
                pass
            ret = MediaManager.get_info_from_filename2(path_u)
            assert ret['title'] == 'mock_album', "ret: %s" % ret
            os.rmdir(path_u)

    def test_get_album_name2(self):
        for name in ['20 mock_album - 2004', '20 mock_album (2004)', '20 mock_album (Disk1)']:
            path_u = join("/", os.getcwd(), "test/data/mock_artist/", name)
            try:
                os.mkdir(path_u)
            except:
                pass
            ret = MediaManager.get_info_from_filename2(path_u)
            assert ret['title'] == '20 mock_album', "ret: %s" % ret
            os.rmdir(path_u)

    def test_get_info_from_name2(self):
        for name in [
                'While my guitar gently weeps.mp3', 'The Beatles - While my guitar gently weeps.mp3', 'While my guitar gently weeps (1969).mp3', 'The Beatles - While my guitar gently weeps (1969).mp3', 'Greatest Hits - 01 - While my guitar gently weeps.mp3', 'While my guitar gently weeps (Disk1)', 'While my guitar gently weeps (EP) - 2003'
        ]:
            info = MediaManager.get_info_from_filename2(name)
            print "info: %s" % info
            assert info.get(
                'title') == 'While my guitar gently weeps', "ret: %s" % info

    def test_get_info_from_name2_full_path(self):
        for path in ['/opt/music/CSI/CSI - Kodemondo/Celluloide 03.ogg',
            './test/data/unexistent_artist/noartist.mp3']:
            info = MediaManager.get_info_from_filename2(path)
            print "info: %s" % info

    def test_normalize(self):
        info_l = [
            {'album': 'pippo', 'artist': u'Fiorella Mannoia'},
            {'album': 'pippo', 'artist': u'Fiorella_Mannoia'}
        ]
        for info in info_l:
            ret = MediaManager.normalize_artist(info)
            assert ret == 'fiorellamannoia'

    def test_normalize_stopwords(self):
        info_l = [
            {'album': 'pippo', 'artist': u'The Beatles'},
            {'album': 'pippo', 'artist': u'Beatles'}
        ]
        for info in info_l:
            ret = MediaManager.normalize_artist(info, stopwords=True)
            assert ret == 'beatles'

    def test_normalize_album(self):
        info_l = [
            {'artist': 'pippo', 'album': u'Evanescence'},
            {'artist': 'pippo', 'album': u'evanescence (EP)'},
            {'artist': 'pippo', 'album': u'Evanescence [EP]'},

        ]
        expected = 'evanescence'
        for info in info_l:
            ret = MediaManager.normalize_album(info)
            assert ret == expected, "Expecting: [%s], got [%s]" % (
                expected, ret)

    def test_coverart_uuid(self):
        info_l = [
            {'artist': 'Antony & the Johnsons', 'album': 'The crying light'},
            {'artist': 'Antony and the Johnsons', 'album': 'The crying light'},
        ]
        for info in info_l:
            ret = MediaManager.cover_art_uuid(info)
            print "coverid:", ret

    def test_unicode(self):
        for f in os.listdir("/opt/music/"):
            # f is a byte sequence returned by the
            #    filesystem and should be converted
            #    to a unicode object
            f_u = stringutils.to_unicode(f)
            print f.__class__, "%s" % f_u

    def test_utf16_bom(self):
        f = "./test/data/id3_with_bom_utf16_le.mp3"

        info = MediaManager.get_info(f)
        album = info.get('album').strip(u'\x01\xff\xfe')
        print ("info:%s\nalbum:%s" % (info, album))
