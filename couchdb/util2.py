
__all__ = [
    'StringIO', 'urlsplit', 'urlunsplit', 'urlquote', 'urlunquote',
    'urlencode', 'utype', 'ltype', 'pyexec', 'strbase',
]

utype = unicode
ltype = long
strbase = str, bytes, unicode

from io import BytesIO as StringIO
from urlparse import urlsplit, urlunsplit
from urllib import quote as urlquote
from urllib import unquote as urlunquote
from urllib import urlencode

def pyexec(code, gns, lns):
    exec code in gns, lns
