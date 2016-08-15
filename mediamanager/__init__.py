"""mediamanager module"""
from __future__ import unicode_literals

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
import mutagen.oggvorbis
import mutagen.asf
import re
import os
import sys
import logging
from binascii import crc32

from os.path import dirname, basename, join

#local import
from stringutils import isdir, stat, to_unicode


class UnsupportedMediaError(Exception):
    pass


def get_cover_art_from_file(path):
    """Don't check existence, just raise."""
    f = mutagen.File(path)
    img_file = MediaManager.uuid(dirname(path))
    if f and 'APIC:' in f:
        assert False, "Trovata!"
        artwork = f.tags['APIC:'].data
        with open(join('/tmp/iposonic/_cache/', 'test_%s' % img_file), 'wb') as img:
            img.write(artwork)


class MediaManager(object):
    """Class to manage media object."""
    ALLOWED_FILE_EXTENSIONS = ["mp3", "ogg", "wma", "flac", "m4a", "mp4"]

    log = logging.getLogger('MediaManager')
    re_track_1 = re.compile("([0-9]+)?[ -_]+(.*)")
    re_track_2 = re.compile("^(.*)([0-9]+)?$")
    re_split_s = "\s*-\s*"
    re_notes = re.compile('\((.+)\)')
    re_notes_2 = re.compile(b'\[.+\]')
    re_notascii = re.compile("[^A-Za-z0-9]")

    stopwords = set(['i', 'the'])

    @staticmethod
    def normalize_artist(x, stopwords=False):
        """Return the ascii part of a album name."""
        # normalize artist name
        try:
            artist = x.get('artist', x.get('name', x.get('Author'))).lower()
        except AttributeError:
            raise UnsupportedMediaError(
                "Missing artist field (artist, name or Author) in: %s" % x)
        artist = artist.replace('&', ' and ')
        if stopwords:
            artist = "".join([x for x in artist.split(
                " ") if x not in MediaManager.stopwords])
        ret = MediaManager.re_notascii.sub("", artist)
        MediaManager.log.debug("normalize_artist(%r): %r" % (x, ret))
        return ret

    @staticmethod
    def normalize_album(x):
        """Return the normalized album name.

            - lowercase
            - replace & with and
            - remove parentheses and their content
        """
        try:
            album = x.get('album', x.get('parent')).lower()
        except AttributeError:
            raise UnsupportedMediaError(
                "Missing album field (album, parent) in: %s" % x)
        album = album.replace('&', ' and ')
        album = MediaManager.re_notes.sub("", album)
        album = MediaManager.re_notes_2.sub("", album)
        MediaManager.log.debug("normalize_artist(%r): %r" % (x, album))
        return album.strip()

    @staticmethod
    def lyrics_uuid(info):
        """Create an UUID for song lyric. 

           @raise UnsupportedMediaError if artist is missing
        """
        return MediaManager.uuid(
                                 os.path.join(
                                 MediaManager.normalize_artist(
                                                               info, stopwords=True),
                                 info['title'].lower())
                                 )

    @staticmethod
    def cover_art_uuid(info):
            """Generate an un unique identifier for coverart.

               Raise UnsupportedMediaError if artist/album is missing
            """
            return MediaManager.uuid(os.path.join(
                                     MediaManager.normalize_artist(info),
                                     MediaManager.normalize_album(info))
                                     )

    @staticmethod
    def uuid(path):
        """ path should be byte[], so encode it
            if it's unicode
        """
        data = path
        if isinstance(path, unicode):
            data = path.encode('utf-8')
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
            # return lambda x: MP3(x, ID3=EasyID3)
            return MediaManager.mp3_tag_manager
        if path.endswith("ogg"):
            return mutagen.oggvorbis.Open
        if path.endswith("flac"):
            return mutagen.flac.FLAC
        if path.endswith(("mp4","m4a")):
            return mutagen.mp4.MP4
        if path.endswith("wma"):
            return mutagen.asf.Open
        raise UnsupportedMediaError(
            "Can't find tag manager for path: %s" % path)

    @staticmethod
    def mp3_tag_manager(path):
        try:
            return MP3(path, ID3=EasyID3)
        except HeaderNotFoundError:
            # Convert id3 tag manually
            #    TIT2 bal dans ma rue
            #    TRCK 16
            #    TPE1 Edith Piaf
            #    TALB L'etoile de la chanson
            #    COMM:ID3v1 Comment:'eng' Created by Grip
            #    TCON Alternative
            ret = mutagen.id3.Open(path)
            return {
                    'title' : ret.get('TIT2').text,
                    'track': getattr(ret.get('TRCK'), 'text', 0),
                    'artist': getattr(ret.get('TPE1'), 'text', 'WuMing'),
                    'album': getattr(ret.get('TALB'), 'text', 'WuMingAlbum'),
                    'genre': getattr(ret.get('TCON'), 'text', 'WuMingGenre')
                    }
                
        raise HeaderNotFoundError()
    
    @staticmethod
    def get_info_from_filename(path):
        """Get track number, path, file size from file name."""
        #assert os.path.isfile(path)

        try: # TODO os.path.splitext 
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
        """Get from an existing file: title, artist, album"""
        filename = basename(path_u)

        # strip extension
        filename, extension = os.path.splitext(filename)
        extension = extension[1:]
        
        ret = {}
        # strip notes enclosed by () - eg. (cdno), (year) from filename
        m_notes = MediaManager.re_notes.search(filename)
        if m_notes:
            try:
                notes = m_notes.group(1)

                filename = filename.replace(m_notes.group(), "").strip()
                ret['year'] = int(notes)
                MediaManager.log.debug("year: %r " % notes)

            except:
                MediaManager.log.debug("notes: %r" % notes)

        info_l = [x.strip(" -") for x in filename.split("-")]
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
            size = os.path.getsize(path_u)
        except:
            size = -1

        if not 'track' in ret and not isdir(path_u):
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
        #if not os.path.isdir(path_u):
        #    raise UnsupportedMediaError("Path is not an Album: %s" % path_u)
        return MediaManager.get_info_from_filename2(path_u).get('title')

        MediaManager.log.info("parsing album path: %r" % path_u)
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

           NB: get_info infers data from file path 
               using get_info_from_filename2 and overrides
               data with id3.

           "bitRate": 192,
           "contentType": "audio/mpeg",
           "duration": 264,
           "isDir": false,
           "isVideo": false,
           "size": 6342112,
            "created": 12345
           TODO all strings should still be unicode
        """
        if True:  # os.path.isfile(path):
            try:
                path_u = to_unicode(path)
                # get basic info
                ret = MediaManager.get_info_from_filename2(path_u)

                manager = MediaManager.get_tag_manager(path_u)
                audio = manager(path)
                #audio = manager(path.encode('utf-8'))
                MediaManager.log.debug("Original id3: %r" % audio)
                
                # Add only non-null fields
                for (k, v) in audio.iteritems():
                    if isinstance(v, list) and v and v[0]:
                        ret[k] = v[0]

                ret['id'] = MediaManager.uuid(path)
                ret['isDir'] = 'false'
                ret['isVideo'] = 'false'
                ret['parent'] = MediaManager.uuid(dirname(path))
                ret['created'] = int(os.stat(path).st_ctime)

                try:
                    ret['bitRate'] = audio.info.bitrate / 1000
                    ret['duration'] = int(audio.info.length)
                    ret['track'] = MediaManager.get_track_number(ret)

                except Exception as e:
                    MediaManager.log.warn(
                        "Error parsing track or bitrate: %s" % e)

                # This field is Iposonic specific and
                # is used to identify a song independently of
                # the interpreter and cache the lyrics
                try:
                    ret['scrobbleId'] = MediaManager.lyrics_uuid(ret)
                except UnsupportedMediaError:
                    ret['scrobbleId'] = None
                    # raise # TESTME what happens if I don't raise?

                # Set default values for missing params
                ret.setdefault('artist', 'WuMing')  

                MediaManager.log.debug("Parsed id3: %r" % ret)
                return ret
            except HeaderNotFoundError as e:
                raise UnsupportedMediaError(
                    "Header not found in file: %s" % path, e)
            except ID3NoHeaderError as e:
                MediaManager.log.warn("Media has no id3 header: %r" % path)
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
                try:
                    info = MediaManager.get_info(path)
                except UnsupportedMediaError as e:
                    MediaManager.log.warn(
                        "Media not supported by Iposonic: %s\n\n" % e)
                except HeaderNotFoundError as e:
                    raise e
                except ID3NoHeaderError as e:
                    MediaManager.log.warn("Media has no id3 header: %r" % path)

    @staticmethod
    def get_track_number(x):
        """Return track info searching it in various parameters."""
        def _trackize(x):
            if not x:
                return 0

            try:
                return int(x)
            except:
                pass
            
            if x.find("/"):
                x = x[:x.index("/")]
            try:
                return int(x)
            except ValueError:
                MediaManager.log.debug("Error parsing track")
                return 0

        for field in ['track', 'tracknumber']:
            ret = _trackize(x.get(field))
            if ret:
                return ret
        return 0
