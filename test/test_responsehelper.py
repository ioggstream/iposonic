from iposonic import ResponseHelper
assert ResponseHelper

def test_json2xml_1():
    val = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    print "ret: %s" % ResponseHelper.json2xml(val)

def test_json2xml_2():
    val = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    print "ret: %s" % ResponseHelper.json2xml([val, val])

def test_json2xml_3():
    val1 = { 'musicFolder': {'id': 1234, 'name': "sss" }}
    val2 = { 'musicFolders': {'__content' : val1}}
    print ResponseHelper.json2xml(val2)

def test_json2xml_4():
      val1 = { 'musicFolder': {'id': 1234, 'name': "sss" }}
      val2 = { 'musicFolders': {'__content' : [val1, val1]}}
      print ResponseHelper.json2xml(val2)

def test_json2xml_5():
    ul = {'ul': {'style':'color:black;', '__content':
      [
      {'li': {'__content': 'Write first'}},
      {'li': {'__content': 'Write second'}},
      ]
      }
      }
    print ResponseHelper.json2xml(ul)

def test_json2xml_6():
    album = {'album':{'album': u'Bach Violin Concertos (PREVIEW: buy it at www.magnatune.com)',
      'isDir': 'false', 'date': u'2001', 'parent': '759327748',
      'artist': u'Lara St John (PREVIEW: buy it at www.magnatune.com)', 'genre': u'Classical',
      'path': '/home/rpolli/workspace-py/iposonic/test/data/lara.mp3',
      'title': u'BWV 1041 : I. Allegro (PREVIEW: buy it at www.magnatune.com)', 'id': '-780183664', 'tracknumber': u'1'}}
    print ResponseHelper.json2xml(album)



