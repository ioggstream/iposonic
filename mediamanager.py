"""mediamanager module"""
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError  # ID3,
from mutagen.mp3 import MP3, HeaderNotFoundError
import mutagen.oggvorbis
import mutagen.asf
import re
import os
import sys
import logging
from binascii import crc32

from os.path import dirname, basename, join


class UnsupportedMediaError(Exception):
    pass


class MediaManager:
    """Class to manage media object."""
    ALLOWED_FILE_EXTENSIONS = ["mp3", "ogg", "wma"]

    log = logging.getLogger('MediaManager')
    re_track_1 = re.compile("([0-9]+)?[ -_]+(.*)")
    re_track_2 = re.compile("^(.*)([0-9]+)?$")
    re_split_s = "\s*-\s*"
    re_notes = re.compile('\((.+)\)')

    @staticmethod
    def normalize_album(x):
        """Return the ascii part of a album name."""
        # normalize artist name
        re_notascii = re.compile("[^A-Za-z0-9]")
        artist = x.get('artist').lower()
        ret = re_notascii.sub("", artist)
        print "normalize_album(%s): %s" % (x, ret)
        return ret

    @staticmethod
    def get_entry_id(path):
        # path should be byte[], so convert it
        #   if it's unicode
        data = path
        if isinstance(path, unicode):
            data = path.encode('utf8')
        return str(crc32(data))

    @staticmethod
    def is_allowed_extension(file_name):
        for e in MediaManager.ALLOWED_FILE_EXTENSIONS:
            if file_name.lower().endswith(e):
                return True
        return False

    @staticmethod
    def get_tag_manager(path):
        """Return the most suitable mutagen tag manager for file."""
        path = path.lower()
        if not MediaManager.is_allowed_extension(path):
            raise UnsupportedMediaError(
                "Unallowed extension for path: %s" % path)

        if path.endswith("mp3"):
            return lambda x: MP3(x, ID3=EasyID3)
        if path.endswith("ogg"):
            return mutagen.oggvorbis.Open
        if path.endswith("wma"):
            return mutagen.asf.Open
        raise UnsupportedMediaError(
            "Can't find tag manager for path: %s" % path)

    @staticmethod
    def get_info_from_filename(path):
        """Get track number, path, file size from file name."""
        #assert os.path.isfile(path)

        try:
            filename, extension = basename(path).rsplit(".", 1)
        except:
            filename, extension = basename(path), ""

        try:
            (track, title) = re.split("\s+[_\-]\s+", filename, 1)
            track = int(track)
        except:
            (track, title) = (0, filename)
        try:
            size = os.path.getsize(path)
        except:
            size = 0
        return {
            'title': title,
            'track': track,
            'path': path,
            'size': size,
            'suffix': MediaManager.get_extension(path)
        }

    @staticmethod
    def get_info_from_filename2(path_u):
        """Improve v1"""
        filename = basename(path_u)

        # strip extension
        try:
            filename, extension = filename.rsplit(".", 1)
        except:
            extension = ""  # if no extension found

        ret = {}
        # strip notes (eg. cdno, year) from filename
        m_notes = MediaManager.re_notes.search(filename)
        if m_notes:
            try:
                notes = m_notes.group(1)

                filename = filename.replace(m_notes.group(), "").strip()
                ret['year'] = int(notes)
                print "year: %s " % notes

            except:
                print "notes: %s" % notes

        info_l = [x.strip(" -") for x in re.split("-", filename)]
        title, album, artist, track = (None, None, None, None)
        for x in info_l:
            try:
                track = int(x)
                if track > 1900:
                    ret['year'] = track
                    track = 0
                else:
                    ret['track'] = track
                continue
            except:
                pass
            if not title:
                title = x
            elif not album:
                title, album = x, title
            elif not artist:
                album, artist = x, album

        try:
            size = os.path.getsize(path)
        except:
            size = -1

        if not 'track' in ret:
            try:
                t, n = title.split(" ", 1)
                track = int(t)
                title = n
            except:
                pass

        ret.update({
            'title': title,
            'album': album,
            'artist': artist,
            'size': size,
            'track': track,
            'path': path_u,
            'suffix': extension
        })
        return dict([(k, v) for (k, v) in ret.iteritems() if v is not None])

    @staticmethod
    def get_album_name(path_u):
        """Get album name from an unicode path.

            First splits by "-" to work out the possible artist name,
            then rules out the year by parentheses.

        """
        if not os.path.isdir(path_u):
            raise UnsupportedMediaError("Path is not an Album: %s" % path_u)
        return MediaManager.get_info_from_filename2(path_u).get('title')

        MediaManager.log.info("parsing album path: %s" % path_u)
        title = basename(path_u)
        for separator in ['-', '(']:
            if title.find(separator) > 0:
                a0, a1 = title.split(separator, 1)
                try:
                    t_ = int(a1.strip("() []"))
                    title = a0.strip().strip(separator)
                except:
                    title = a1.strip().strip(separator)

        return title

    @staticmethod
    def get_info(path):
        """Get id3 or ogg info from a file.
           "bitRate": 192,
           "contentType": "audio/mpeg",
           "duration": 264,
           "isDir": false,
           "isVideo": false,
           "size": 6342112,

           TODO all strings should be unicode
        """
        if os.path.isfile(path):
            try:
                path = StringUtils.to_unicode(path)
                # get basic info
                ret = MediaManager.get_info_from_filename2(path)

                manager = MediaManager.get_tag_manager(path)
                audio = manager(path)

                MediaManager.log.info("Original id3: %s" % audio)
                for (k, v) in audio.iteritems():
                    if isinstance(v, list) and v and v[0]:
                        ret[k] = v[0]

                ret['id'] = MediaManager.get_entry_id(path)
                ret['isDir'] = 'false'
                ret['isVideo'] = 'false'
                ret['parent'] = MediaManager.get_entry_id(dirname(path))
                try:
                    ret['bitRate'] = audio.info.bitrate / 1000
                    ret['duration'] = int(audio.info.length)
                    if ret.get('tracknumber', 0):
                        MediaManager.log.info(
                            "Overriding track with tracknumber")
                        ret['track'] = int(ret['tracknumber'])

                except Exception as e:
                    print "Error parsing track or bitrate: %s" % e

                MediaManager.log.info("Parsed id3: %s" % ret)
                return ret
            except HeaderNotFoundError as e:
                raise UnsupportedMediaError(
                    "Header not found in file: %s" % path, e)
            except ID3NoHeaderError as e:
                print "Media has no id3 header: %s" % path
            return None
        if not os.path.exists(path):
            raise UnsupportedMediaError("File does not exist: %s" % path)

        raise UnsupportedMediaError(
            "Unsupported file type or directory: %s" % path)

    @staticmethod
    def browse_path(directory):
        for (root, filedir, files) in os.walk(directory):
            for f in files:
                path = join("/", root, f)
                # print "path: %s" % path
                try:
                    info = MediaManager.get_info(path)
                except UnsupportedMediaError as e:
                    print "Media not supported by Iposonic: %s\n\n" % e
                except HeaderNotFoundError as e:
                    raise e
                except ID3NoHeaderError as e:
                    print "Media has no id3 header: %s" % path

    @staticmethod
    def get_track_number(x):
        """Search track info in various parameters."""
        def _trackize(x):
            if not x:
                return 0

            if x.find("/"):
                x = x[:x.index("/")]
            try:
                return int(x)
            except ValueError:
                return 0

        for field in ['track', 'tracknumber']:
            ret = _trackize(x.get(field))
            if ret:
                return ret
        return 0


class StringUtils:
    encodings = ['utf-8', 'ascii', 'latin_1', 'iso8859_15', 'cp850',
                 'cp037', 'cp1252']

    @staticmethod
    def to_unicode(s):
        """Return the unicode representation of a string.

            Try every possible encoding of a string, returning
            the first one that doesn't except.

            If s is not a string, return the unchanged object.
        """
        if not isinstance(s, str):
            print "returning unchanged object: %s" % s.__class__
            return s
        for e in StringUtils.encodings:
            try:
                return s.decode(e)
            except UnicodeDecodeError:
                pass
        raise UnicodeDecodeError("Cannot decode object: %s" % s.__class__)
