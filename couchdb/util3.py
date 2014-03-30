
__all__ = [
    'StringIO', 'urlsplit', 'urlunsplit', 'utype', 'ltype', 'pyexec',
    'strbase',
]

utype = str
ltype = int
strbase = str, bytes

from io import BytesIO as StringIO
from urllib.parse import urlsplit, urlunsplit

pyexec = exec
