#!/usr/bin/env python
#
# Code imported from coverart
#    https://github.com/jmcantrell/coverart/blob/master/coverart/sources/lastfmcovers.py
#
import sys
import re
from urllib import urlopen, quote_plus
from xml.etree.ElementTree import parse


class CoverSource(object):
    """Download cover art from url_base."""
    def __init__(self):
        self.max_results = 10
        self.source_name = 'Last.FM'
        self.api_key = '2f63459bcb2578a277c5cf5ec4ca62f7'
        self.url_base = 'http://ws.audioscrobbler.com/2.0/?method=album.search&api_key=%s' % self.api_key

    def search(self, query):
        url = '%s&album=%s' % (self.url_base, quote_plus('%s' % query))
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


class CoverSource_old(object):  # {{{1

    def __init__(self):
        self.max_results = 10
        self.source_name = 'AllCDCovers'
        self.url_base = 'http://www.allcdcovers.com'

    def search(self, query):
        url = '%s/search/music/all/%s' % (self.url_base, quote_plus(query))
        results_page = urlopen(url).read()
        seen = set()
        count = 0
        for rm in re.finditer(r'<a href="(/show/.*?/.*?/front)">', results_page):
            if not rm or rm.group(1) in seen:
                continue
            cover_page = urlopen(self.url_base + rm.group(1)).read()
            clm = re.search(r'<a href="(/download/.*?)">', cover_page)
            csm = re.search(r'<div class="productImage"><img .*?src="(/image_system/.*?)" />', cover_page)
            am = re.search(r'<dt>Title:</dt><dd>(.*?)</dd>', cover_page)
            if am and csm and clm:
                count += 1
                yield {
                    'album': am.group(1),
                    'cover_large': self.url_base + clm.group(1),
                    'cover_small': self.url_base + clm.group(1),
                }
            if count == self.max_results:
                break
            seen.add(rm.group(1))

#}}}1


if __name__ == '__main__':
    c = CoverSource()
    for res in c.search(sys.argv[1]):
        print res
