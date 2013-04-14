
class IposonicException(Exception):
    """Generic Iposonic Exception"""
    pass

class EntryNotFoundException(IposonicException, KeyError):
    """Entry not found."""
    pass


class SubsonicProtocolException(IposonicException):
    """Request doesn't respect Subsonic API .

        see: http://www.subsonic.org/pages/api.jsp
    """
    def __init__(self, message, request=None):
        if request:
            message += "request data: %r" % request
        Exception.__init__(self, message)
    


class SubsonicMissingParameterException(SubsonicProtocolException):
    """The request doesn't conform due to a missing parameter."""
    def __init__(self, param, method, request=None):
        SubsonicProtocolException.__init__(
            self, "Missing required parameter: %r in %r" % (param, method))

