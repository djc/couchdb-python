
__all__ = ['StringIO', 'urlsplit', 'urlunsplit', 'utype', 'ltype']

utype = unicode
ltype = long

from io import BytesIO as StringIO
from urlparse import urlsplit, urlunsplit
