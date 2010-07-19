#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Simple HTTP client implementation based on the ``httplib`` module in the
standard library.
"""

from base64 import b64encode
from datetime import datetime
import errno
from httplib import BadStatusLine, HTTPConnection, HTTPSConnection
import socket
import time
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import sys
try:
    from threading import Lock
except ImportError:
    from dummy_threading import Lock
import urllib
from urlparse import urlsplit, urlunsplit

from couchdb import json

__all__ = ['HTTPError', 'PreconditionFailed', 'ResourceNotFound',
           'ResourceConflict', 'ServerError', 'Unauthorized', 'RedirectLimit',
           'Session', 'Resource']
__docformat__ = 'restructuredtext en'


class HTTPError(Exception):
    """Base class for errors based on HTTP status codes >= 400."""


class PreconditionFailed(HTTPError):
    """Exception raised when a 412 HTTP error is received in response to a
    request.
    """


class ResourceNotFound(HTTPError):
    """Exception raised when a 404 HTTP error is received in response to a
    request.
    """


class ResourceConflict(HTTPError):
    """Exception raised when a 409 HTTP error is received in response to a
    request.
    """


class ServerError(HTTPError):
    """Exception raised when an unexpected HTTP error is received in response
    to a request.
    """


class Unauthorized(HTTPError):
    """Exception raised when the server requires authentication credentials
    but either none are provided, or they are incorrect.
    """


class RedirectLimit(Exception):
    """Exception raised when a request is redirected more often than allowed
    by the maximum number of redirections.
    """


CHUNK_SIZE = 1024 * 8
CACHE_SIZE = 10, 75 # some random values to limit memory use

def cache_sort(i):
    t = time.mktime(time.strptime(i[1][1]['Date'][5:-4], '%d %b %Y %H:%M:%S'))
    return datetime.fromtimestamp(t)

class ResponseBody(object):

    def __init__(self, resp, callback):
        self.resp = resp
        self.callback = callback

    def read(self, size=None):
        bytes = self.resp.read(size)
        if size is None or len(bytes) < size:
            self.close()
        return bytes

    def close(self):
        while not self.resp.isclosed():
            self.read(CHUNK_SIZE)
        self.callback()

    def __iter__(self):
        assert self.resp.msg.get('transfer-encoding') == 'chunked'
        while True:
            chunksz = int(self.resp.fp.readline().strip(), 16)
            if not chunksz:
                self.resp.fp.read(2) #crlf
                self.resp.close()
                self.callback()
                break
            chunk = self.resp.fp.read(chunksz)
            for ln in chunk.splitlines():
                yield ln
            self.resp.fp.read(2) #crlf


RETRYABLE_ERRORS = frozenset([
    errno.EPIPE, errno.ETIMEDOUT,
    errno.ECONNRESET, errno.ECONNREFUSED, errno.ECONNABORTED,
    errno.EHOSTDOWN, errno.EHOSTUNREACH,
    errno.ENETRESET, errno.ENETUNREACH, errno.ENETDOWN
])


class Session(object):

    def __init__(self, cache=None, timeout=None, max_redirects=5,
                 retry_delays=[0], retryable_errors=RETRYABLE_ERRORS):
        """Initialize an HTTP client session.

        :param cache: an instance with a dict-like interface or None to allow
                      Session to create a dict for caching.
        :param timeout: socket timeout in number of seconds, or `None` for no
                        timeout
        :param retry_delays: list of request retry delays.
        """
        from couchdb import __version__ as VERSION
        self.user_agent = 'CouchDB-Python/%s' % VERSION
        if cache is None:
            cache = {}
        self.cache = cache
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.perm_redirects = {}
        self.conns = {} # HTTP connections keyed by (scheme, host)
        self.lock = Lock()
        self.retry_delays = list(retry_delays) # We don't want this changing on us.
        self.retryable_errors = set(retryable_errors)

    def request(self, method, url, body=None, headers=None, credentials=None,
                num_redirects=0):
        if url in self.perm_redirects:
            url = self.perm_redirects[url]
        method = method.upper()

        if headers is None:
            headers = {}
        headers.setdefault('Accept', 'application/json')
        headers['User-Agent'] = self.user_agent

        cached_resp = None
        if method in ('GET', 'HEAD'):
            cached_resp = self.cache.get(url)
            if cached_resp is not None:
                etag = cached_resp[1].get('etag')
                if etag:
                    headers['If-None-Match'] = etag

        if body is None:
            headers.setdefault('Content-Length', '0')
        else:
            if not isinstance(body, basestring):
                try:
                    body = json.encode(body).encode('utf-8')
                except TypeError:
                    pass
                else:
                    headers.setdefault('Content-Type', 'application/json')
            if isinstance(body, basestring):
                headers.setdefault('Content-Length', str(len(body)))
            else:
                headers['Transfer-Encoding'] = 'chunked'

        authorization = basic_auth(credentials)
        if authorization:
            headers['Authorization'] = authorization

        path_query = urlunsplit(('', '') + urlsplit(url)[2:4] + ('',))
        conn = self._get_connection(url)

        def _try_request_with_retries(retries):
            while True:
                try:
                    return _try_request()
                except socket.error, e:
                    ecode = e.args[0]
                    if ecode not in self.retryable_errors:
                        raise
                    try:
                        delay = retries.next()
                    except StopIteration:
                        # No more retries, raise last socket error.
                        raise e
                    time.sleep(delay)
                    conn.close()

        def _try_request():
            try:
                if conn.sock is None:
                    conn.connect()
                conn.putrequest(method, path_query, skip_accept_encoding=True)
                for header in headers:
                    conn.putheader(header, headers[header])
                conn.endheaders()
                if body is not None:
                    if isinstance(body, str):
                        conn.sock.sendall(body)
                    else: # assume a file-like object and send in chunks
                        while 1:
                            chunk = body.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            conn.sock.sendall(('%x\r\n' % len(chunk)) +
                                              chunk + '\r\n')
                        conn.sock.sendall('0\r\n\r\n')
                return conn.getresponse()
            except BadStatusLine, e:
                # httplib raises a BadStatusLine when it cannot read the status
                # line saying, "Presumably, the server closed the connection
                # before sending a valid response."
                # Raise as ECONNRESET to simplify retry logic.
                if e.line == '' or e.line == "''":
                    raise socket.error(errno.ECONNRESET)
                else:
                    raise

        resp = _try_request_with_retries(iter(self.retry_delays))
        status = resp.status

        # Handle conditional response
        if status == 304 and method in ('GET', 'HEAD'):
            resp.read()
            self._return_connection(url, conn)
            status, msg, data = cached_resp
            if data is not None:
                data = StringIO(data)
            return status, msg, data
        elif cached_resp:
            del self.cache[url]

        # Handle redirects
        if status == 303 or \
                method in ('GET', 'HEAD') and status in (301, 302, 307):
            resp.read()
            self._return_connection(url, conn)
            if num_redirects > self.max_redirects:
                raise RedirectLimit('Redirection limit exceeded')
            location = resp.getheader('location')
            if status == 301:
                self.perm_redirects[url] = location
            elif status == 303:
                method = 'GET'
            return self.request(method, location, body, headers,
                                num_redirects=num_redirects + 1)

        data = None
        streamed = False

        # Read the full response for empty responses so that the connection is
        # in good state for the next request
        if method == 'HEAD' or resp.getheader('content-length') == '0' or \
                status < 200 or status in (204, 304):
            resp.read()
            self._return_connection(url, conn)

        # Buffer small non-JSON response bodies
        elif int(resp.getheader('content-length', sys.maxint)) < CHUNK_SIZE:
            data = resp.read()
            self._return_connection(url, conn)

        # For large or chunked response bodies, do not buffer the full body,
        # and instead return a minimal file-like object
        else:
            data = ResponseBody(resp,
                                lambda: self._return_connection(url, conn))
            streamed = True

        # Handle errors
        if status >= 400:
            ctype = resp.getheader('content-type')
            if data is not None and 'application/json' in ctype:
                data = json.decode(data)
                error = data.get('error'), data.get('reason')
            elif method != 'HEAD':
                error = resp.read()
                self._return_connection(url, conn)
            else:
                error = ''
            if status == 401:
                raise Unauthorized(error)
            elif status == 404:
                raise ResourceNotFound(error)
            elif status == 409:
                raise ResourceConflict(error)
            elif status == 412:
                raise PreconditionFailed(error)
            else:
                raise ServerError((status, error))

        # Store cachable responses
        if not streamed and method == 'GET' and 'etag' in resp.msg:
            self.cache[url] = (status, resp.msg, data)
            if len(self.cache) > CACHE_SIZE[1]:
                self._clean_cache()

        if not streamed and data is not None:
            data = StringIO(data)

        return status, resp.msg, data

    def _clean_cache(self):
        ls = sorted(self.cache.iteritems(), key=cache_sort)
        self.cache = dict(ls[-CACHE_SIZE[0]:])

    def _get_connection(self, url):
        scheme, host = urlsplit(url, 'http', False)[:2]
        self.lock.acquire()
        try:
            conns = self.conns.setdefault((scheme, host), [])
            if conns:
                conn = conns.pop(-1)
            else:
                if scheme == 'http':
                    cls = HTTPConnection
                elif scheme == 'https':
                    cls = HTTPSConnection
                else:
                    raise ValueError('%s is not a supported scheme' % scheme)
                conn = cls(host)
        finally:
            self.lock.release()
        return conn

    def _return_connection(self, url, conn):
        scheme, host = urlsplit(url, 'http', False)[:2]
        self.lock.acquire()
        try:
            self.conns.setdefault((scheme, host), []).append(conn)
        finally:
            self.lock.release()


class Resource(object):

    def __init__(self, url, session, headers=None):
        self.url, self.credentials = extract_credentials(url)
        if session is None:
            session = Session()
        self.session = session
        self.headers = headers or {}

    def __call__(self, *path):
        obj = type(self)(urljoin(self.url, *path), self.session)
        obj.credentials = self.credentials
        obj.headers = self.headers.copy()
        return obj

    def delete(self, path=None, headers=None, **params):
        return self._request('DELETE', path, headers=headers, **params)

    def get(self, path=None, headers=None, **params):
        return self._request('GET', path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        return self._request('HEAD', path, headers=headers, **params)

    def post(self, path=None, body=None, headers=None, **params):
        return self._request('POST', path, body=body, headers=headers,
                             **params)

    def put(self, path=None, body=None, headers=None, **params):
        return self._request('PUT', path, body=body, headers=headers, **params)

    def delete_json(self, *a, **k):
        status, headers, data = self.delete(*a, **k)
        if 'application/json' in headers.get('content-type'):
            data = json.decode(data.read())
        return status, headers, data

    def get_json(self, *a, **k):
        status, headers, data = self.get(*a, **k)
        if 'application/json' in headers.get('content-type'):
            data = json.decode(data.read())
        return status, headers, data

    def post_json(self, *a, **k):
        status, headers, data = self.post(*a, **k)
        if 'application/json' in headers.get('content-type'):
            data = json.decode(data.read())
        return status, headers, data

    def put_json(self, *a, **k):
        status, headers, data = self.put(*a, **k)
        if 'application/json' in headers.get('content-type'):
            data = json.decode(data.read())
        return status, headers, data

    def _request(self, method, path=None, body=None, headers=None, **params):
        all_headers = self.headers.copy()
        all_headers.update(headers or {})
        if path is not None:
            url = urljoin(self.url, path, **params)
        else:
            url = urljoin(self.url, **params)
        return self.session.request(method, url, body=body,
                                    headers=all_headers,
                                    credentials=self.credentials)


def extract_credentials(url):
    """Extract authentication (user name and password) credentials from the
    given URL.
    
    >>> extract_credentials('http://localhost:5984/_config/')
    ('http://localhost:5984/_config/', None)
    >>> extract_credentials('http://joe:secret@localhost:5984/_config/')
    ('http://localhost:5984/_config/', ('joe', 'secret'))
    >>> extract_credentials('http://joe%40example.com:secret@localhost:5984/_config/')
    ('http://localhost:5984/_config/', ('joe@example.com', 'secret'))
    """
    parts = urlsplit(url)
    netloc = parts[1]
    if '@' in netloc:
        creds, netloc = netloc.split('@')
        credentials = tuple(urllib.unquote(i) for i in creds.split(':'))
        parts = list(parts)
        parts[1] = netloc
    else:
        credentials = None
    return urlunsplit(parts), credentials


def basic_auth(credentials):
    if credentials:
        return 'Basic %s' % b64encode('%s:%s' % credentials)


def quote(string, safe=''):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return urllib.quote(string, safe)


def urlencode(data):
    if isinstance(data, dict):
        data = data.items()
    params = []
    for name, value in data:
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        params.append((name, value))
    return urllib.urlencode(params)


def urljoin(base, *path, **query):
    """Assemble a uri based on a base, any number of path segments, and query
    string parameters.

    >>> urljoin('http://example.org', '_all_dbs')
    'http://example.org/_all_dbs'

    A trailing slash on the uri base is handled gracefully:

    >>> urljoin('http://example.org/', '_all_dbs')
    'http://example.org/_all_dbs'

    And multiple positional arguments become path parts:

    >>> urljoin('http://example.org/', 'foo', 'bar')
    'http://example.org/foo/bar'

    All slashes within a path part are escaped:

    >>> urljoin('http://example.org/', 'foo/bar')
    'http://example.org/foo%2Fbar'
    >>> urljoin('http://example.org/', 'foo', '/bar/')
    'http://example.org/foo/%2Fbar%2F'

    >>> urljoin('http://example.org/', None) #doctest:+IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: argument 2 to map() must support iteration
    """
    if base and base.endswith('/'):
        base = base[:-1]
    retval = [base]

    # build the path
    path = '/'.join([''] + [quote(s) for s in path])
    if path:
        retval.append(path)

    # build the query string
    params = []
    for name, value in query.items():
        if type(value) in (list, tuple):
            params.extend([(name, i) for i in value if i is not None])
        elif value is not None:
            if value is True:
                value = 'true'
            elif value is False:
                value = 'false'
            params.append((name, value))
    if params:
        retval.extend(['?', urlencode(params)])

    return ''.join(retval)

