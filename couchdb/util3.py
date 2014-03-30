
__all__ = ['StringIO', 'urlsplit', 'urlunsplit', 'utype', 'ltype', 'pyexec']

utype = str
ltype = int

from io import BytesIO as StringIO
from urllib.parse import urlsplit, urlunsplit

pyexec = exec
