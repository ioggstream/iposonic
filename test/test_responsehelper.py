from webapp import ResponseHelper


def var_sample():
    album = {'album': {'album': u'Bach Violin Concertos (PREVIEW: buy it at www.magnatune.com)',
                       'isDir': 'false', 'date': u'2001', 'parent': '759327748',
                       'artist': u'Lara St John (PREVIEW: buy it at www.magnatune.com)', 'genre': u'Classical',
                       'path': '/home/rpolli/workspace-py/iposonic/test/data/lara.mp3',
                       'title': u'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)', 'id': '-780183664', 'tracknumber': u'1'}}


def test_jsonp2xml_1():
    val = {'musicFolder': [{'id': 1234, 'name': "sss"}]}
    print "ret: %s" % ResponseHelper.jsonp2xml(val)


def test_jsonp2xml_2():
    val = {'musicFolder': [{'id': 1234, 'name': "sss"}, {'id': 456,
                                                         'name': "aaa"}]}
    print "ret: %s" % ResponseHelper.jsonp2xml(val)


def test_jsonp2xml_3():
    val1 = {'musicFolder': {'id': 1234, 'name': "sss"}}
    val2 = {'musicFolders': {'musicFolder': [{'id': 1234, 'name':
                                              "sss"}, {'id': 456, 'name': "aaa"}]}}
    print ResponseHelper.jsonp2xml(val2)


def test_jsonp2xml_4():
    val = {"subsonic-response": {"musicFolders": {"musicFolder": [{"id": 0, "name": "Music"}]},
                                 "status": "ok", "version": "1.7.0", "xmlns": "http://subsonic.org/restapi"}}

    val2 = {
        "subsonic-response": {
            "musicFolders": {
                "musicFolder": [
                    {
                        "id": "-510260975",
                        "name": "/opt/music/"
                    }
                ]
            },
            "status": "ok",
            "version": "19.9.9",
            "xmlns": "http://subsonic.org/restapi"
        }}
    print ResponseHelper.jsonp2xml(val2)


def test_jsonp2xml_5():
    val = {
        'index': [{'name': 'A',
        'artist': [
                   {'id': '517674445', 'name': 'sss'},
                   {'id': '-87058509', 'name': 'Johnsons'},
                   {'id': '998700272', 'name': 'Franklin'},
                   {'id': '250502050', 'name': 'Antonella'},
                   {'id': '449525971', 'name': 'Artista'},
                   {'id': '-187601579', 'name': 'John'}
                   ]
                   }]
    }

    print ResponseHelper.jsonp2xml(val)
