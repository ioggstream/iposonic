#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3

from nose import *

# standard libs
import os
import sys
import re
from os.path import join, basename, dirname

from iposonic import MediaManager

import logging
log = logging.getLogger("test")


class TestMediaManager:
    def get_info_harn(self, file_name, expected):
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
            'parent': MediaManager.get_entry_id(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_mp3(self):
        file_name = "./test/data/lara.mp3"
        parent = dirname(file_name)

        expected = {
            'title': 'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)',
            'artist': 'Lara St John (PREVIEW: buy it at www.magnatune.com)',
            'parent': MediaManager.get_entry_id(join("/", os.getcwd(), parent))
        }
        self.get_info_harn(file_name, expected)

    def get_info_test_wma(self):
        file_name = "./test/data/sample.wma"
        expected = {}
        self.get_info_harn(file_name, expected)

    @SkipTest
    def browse_path_test(self):
        MediaManager.browse_path("/opt/music")
