"""A simple authorizer class"""


from hashlib import md5


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
                    user, passwd = line.split("=")
                    if user and passwd:
                        self.add_user(user, passwd)
                except:
                    print "Malformed line: %s" % line
        except:
            raise

    def authorize(self, user, passwd):
        """Validate a password using the stored value."""
        if self.mock:
            return True

        passwd_hash = self.users.get(user)
        if md5(passwd).hexdigest() == passwd_hash:
            return True
        return False

    def add_user(self, user, passwd, cleartext=True):
        if cleartext:
            passwd = md5(passwd).hexdigest()
        self.users.setdefault(user, passwd)
