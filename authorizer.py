"""A simple authorizer class"""

import logging
from hashlib import md5

log = logging.getLogger('iposonic-authorizer')
class Authorizer:
    """A simple authorizer."""
    users = dict()

    def __init__(self, access_file=None, mock=False):
        self.mock = mock
        
        if self.mock:
            return
        if not access_file:
            return
        try:
            f = open(access_file)
            for line in f.readlines():
                try:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("#"):
                        continue;    
                    user, passwd = line.split("=")
                    if user and passwd:
                        log.info("Adding user: %s" % user )
                        self.add_user(user, passwd, cleartext=False)
                except:
                    log.info("Malformed line: [%s]" % line)
        except:
            raise

    def authorize(self, user, passwd):
        """Validate a password using the stored value."""
        if self.mock:
            log.info("Mock authentication: ok")
            return True

        passwd_hash = self.users.get(user)
        if md5(passwd).hexdigest() == passwd_hash:
            return True
        log.info("Error authenticating user: %s" % user)
        return False

    def add_user(self, user, passwd, cleartext=True):
        if cleartext:
            passwd = md5(passwd).hexdigest()
        self.users.setdefault(user, passwd)
