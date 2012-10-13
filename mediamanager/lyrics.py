from urllib2 import urlopen, quote
from xml.etree.ElementTree import parse
from iposonic import IposonicException
from logging import getLogger
log = getLogger(__name__)


class ChartLyrics():
    """Download song lyrics from ChartLyrics."""
    tags = ['Lyric', 'LyricId', 'LyricChecksum']
    tag_lyric, tag_lyric_id, tag_lyric_checksum = [
        '{http://api.chartlyrics.com/}%s' % x for x in tags]

    api_endpoint_search = "http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist=%s&song=%s"
    api_endpoint_get = "http://api.chartlyrics.com/apiv1.asmx/GetLyric?lyricId=%s&lyricCheckSum=%s"

    def get(self, info):
        """Get lyrics by id and checksum."""
        lyric_id, lyric_check_sum = [quote(info.get(x)) for x in [
                                     'artist', 'title']]
        uri = self.api_endpoint_search % (lyric_id, lyric_check_sum)
        log.info("downloading lyrics from: %s" % uri)
        xml_response = parse(urlopen(uri))

        for lyrics in xml_response.findall(self.tag_lyric):
            if lyrics is not None:
                # xml response is a byte sequence
                # so encode it as an utf-8 string
                return lyrics.text.encode('utf-8')

    def search(self, info):
        """Return the song lyrics (in utf-8) related to the song information.
            info = {'artist': .., 'title': ...}
        """
        ret = dict()
        artist, song = [quote(info.get(x).lower()) for x in [
                        'artist', 'title']]
        uri = self.api_endpoint_search % (artist, song)
        log.info("downloading lyrics from: %s" % uri)
        xml_response = urlopen(uri)
        xml_response = parse(xml_response)
        for item in xml_response.getiterator(self.tag_lyric):
            ret['lyrics'] = item.text  # .encode('utf-8')
        for item in xml_response.getiterator(self.tag_lyric_id):
            ret['lyricId'] = item.text  # .encode('utf-8')
        for item in xml_response.getiterator(self.tag_lyric_checksum):
            ret['lyricCheckSum'] = item.text  # .encode('utf-8')

        if len(ret):
            return ret
        raise IposonicException("Can't find lyrics")
