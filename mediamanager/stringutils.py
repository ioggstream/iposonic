from __future__ import unicode_literals

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError
import mutagen.oggvorbis
import mutagen.asf
import re
import os
import sys
import logging
from binascii import crc32

from os.path import dirname, basename, join

trace = False
log = logging.getLogger(__name__)

encodings = ['utf-8', 'ascii', 'latin_1', 'iso8859_15', 'cp850',
             'cp037', 'cp1252']


def encode_safe(f):
    def t(path):
        for e in encodings:
            try:
                return f(path.decode('utf-8').encode(e))
            except UnicodeEncodeError, UnicodeDecodeError:
                pass
        return UnicodeEncodeError("Cannot find encoding for type: %s" % type(path))
    return t


#@encode_safe
def isdir(path):
    return os.path.isdir(path)


@encode_safe
def stat(path):
    return os.stat(path)


def detect_encode(s):
    for e in encodings:
        try:
            s.encode(e)
            return e
        except UnicodeDecodeError, UnicodeEncodeError:
            pass
    raise UnicodeEncodeError("Cannot decode object: %s" % s.__class__)


def to_unicode(s, getencoding=False):
    """Return the unicode representation of a string.

        Try every possible encoding of a string, returning
        the first one that doesn't except.

        If s is not a string, return the unchanged object.
    """
    if not isinstance(s, str):
        log.debug("returning unchanged object: %r" % s.__class__)
        return s
    for e in encodings:
        try:
            ret = s.decode(e)
            if getencoding:
                return (ret, e)
            return ret
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("Cannot decode object: %s" % s.__class__)
