
__all__ = [
    'StringIO', 'urlsplit', 'urlunsplit', 'urlquote', 'urlunquote',
    'urlencode', 'utype', 'ltype', 'pyexec', 'strbase', 'funcode',
    'urlparse',
]

utype = str
ltype = int
strbase = str, bytes

from io import BytesIO as StringIO
from urllib.parse import urlsplit, urlunsplit, urlencode, urlparse
from urllib.parse import quote as urlquote
from urllib.parse import unquote as urlunquote

pyexec = exec

def funcode(fun):
    return fun.__code__
