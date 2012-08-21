#!/usr/bin/python
# -*- coding: utf-8 -*-
# iposonic - a micro implementation of the subsonic server API
#  for didactical purposes: I just wanted to play with flask
#
# Roberto Polli (c) 2012
# AGPL v3

from nose import *

# standard libs
import os, sys, re
from os.path import join

from iposonic import MediaManager


class TestMediaManager:
    def get_info_harn(self, file, expected):
        info = MediaManager.get_info(os.getcwd() +"/"+ file)
        for f in expected.keys():
            assert info[f] == expected[f], "Mismatching field %s. Expected %s get %s" % (f, expected[f], info[f])
    def get_info_test_ogg(self):
        file = "./test/data/mock_artist/mock_album/sample.ogg"
        expected = {
          'title':'mock_title',
          'artist': 'mock_artist' ,
          'year':'mock_year',
          'parent' : MediaManager.get_entry_id(os.getcwd() + "/./test/data/mock_artist/mock_album")
          }
        self.get_info_harn(file,expected)
    def get_info_test_mp3(self):
        file = "./test/data/lara.mp3"
        expected = {
          'title' : 'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)',
          'artist' : 'Lara St John (PREVIEW: buy it at www.magnatune.com)',
          'parent' : MediaManager.get_entry_id("./test/data"),
          'id' : MediaManager.get_entry_id(file)
        }
        self.get_info_harn(file, expected)
    def get_info_test_wma(self):
        file = "./test/data/sample.wma"
        expected = {}
        self.get_info_harn(file, expected)
    @SkipTest
    def browse_path_test(self):
        MediaManager.browse_path("/opt/music")


