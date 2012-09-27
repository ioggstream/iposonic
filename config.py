import os
from os.path import join
from authorizer import Authorizer
#
# Configuration
#
tmp_dir = "/tmp/iposonic"
cache_dir = join("/", tmp_dir, "_cache/")
music_folders = [
    #"/home/rpolli/workspace-py/iposonic/test/data/"
    "/home/rpolli/opt/music/"
]

# While developing don't enforce authentication
#   otherwise you can use a credential file
#   or specify your users inline
authorizer = Authorizer(mock=False, access_file=None)
authorizer.add_user("user", "md5hashofthepassword", cleartext=False)
