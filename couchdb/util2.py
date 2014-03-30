
__all__ = ['StringIO', 'urlsplit', 'urlunsplit', 'utype', 'ltype', 'pyexec']

utype = unicode
ltype = long

from io import BytesIO as StringIO
from urlparse import urlsplit, urlunsplit

def pyexec(code, gns, lns):
    exec code in gns, lns
