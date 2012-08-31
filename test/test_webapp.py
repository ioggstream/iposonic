import nose
import httplib


requests = ["/rest/getRandomSongs.view", "/rest/ping.view"]

def test_request():
    for r in requests:
        conn = httplib.HTTPConnection("0:5000")
        conn.request("GET","%s?u=aaa&p=enc:aaa&genre=%s&f=jsonp&callback=XXX"% (r,'pop'))
        res = conn.getresponse()
        print res.status, res.reason

        
