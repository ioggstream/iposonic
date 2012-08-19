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


