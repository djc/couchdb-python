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
from httplib import BadStatusLine, HTTPConnection, HTTPSConnection
import re
import socket
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
           'ServerError', 'Unauthorized', 'RedirectLimit', 'Session',
           'Resource']
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
    return datetime.strptime(i[1][1]['Date'][5:-4], '%d %b %Y %H:%M:%S')


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
                crlf = self.resp.fp.read(2)
                self.resp.close()
                self.callback()
                break
            chunk = self.resp.fp.read(chunksz)
            for ln in chunk.splitlines():
                yield ln
            crlf = self.resp.fp.read(2)


class Session(object):

    def __init__(self, cache=None, timeout=None, max_redirects=5):
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

        if body is not None:
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

        path_query = urlunsplit(('', '') + urlsplit(url)[2:4] + ('',))
        conn = self._get_connection(url)
        if conn.sock is None:
            conn.connect()

        def _try_request(retries=1):
            try:
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
                if retries > 0 and e.line == '':
                    conn.close()
                    conn.connect()
                    return _try_request(retries - 1)
                else:
                    raise
            except socket.error, e:
                ecode = e.args[0]
                if retries > 0 and ecode == 54: # reset by peer
                    conn.close()
                    conn.connect()
                    return _try_request(retries - 1)
                elif ecode == 32: # broken pipe
                    pass
                else:
                    raise

        resp = _try_request()
        status = resp.status

        # Handle authentication challenge
        if status == 401:
            resp.read()
            auth_header = resp.getheader('www-authenticate', '')
            if auth_header:
                if self._authenticate(auth_header, headers, credentials):
                    resp = _try_request()
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
            if data is not None:
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
        if not streamed and method in ('GET', 'HEAD') and 'etag' in resp.msg:
            self.cache[url] = (status, resp.msg, data)
            if len(self.cache) > CACHE_SIZE[1]:
                self._clean_cache()

        if not streamed and data is not None:
            data = StringIO(data)

        return status, resp.msg, data

    def _clean_cache(self):
        ls = sorted(self.cache.iteritems(), key=cache_sort)
        self.cache = dict(ls[-CACHE_SIZE[0]:])

    def _authenticate(self, info, headers, credentials):
        # Naive Basic authentication support
        match = re.match(r'''(\w*)\s+realm=['"]([^'"]+)['"]''', info)
        if match:
            scheme, realm = match.groups()
            if scheme.lower() == 'basic':
                headers['Authorization'] = 'Basic %s' % b64encode(
                    '%s:%s' % credentials
                )
                return True

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
        if headers.get('content-type') == 'application/json':
            data = json.decode(data.read())
        return status, headers, data

    def get_json(self, *a, **k):
        status, headers, data = self.get(*a, **k)
        if headers.get('content-type') == 'application/json':
            data = json.decode(data.read())
        return status, headers, data

    def post_json(self, *a, **k):
        status, headers, data = self.post(*a, **k)
        if headers.get('content-type') == 'application/json':
            data = json.decode(data.read())
        return status, headers, data

    def put_json(self, *a, **k):
        status, headers, data = self.put(*a, **k)
        if headers.get('content-type') == 'application/json':
            data = json.decode(data.read())
        return status, headers, data

    def _request(self, method, path=None, body=None, headers=None, **params):
        all_headers = self.headers.copy()
        all_headers.update(headers or {})
        return self.session.request(method, urljoin(self.url, path, **params),
                                    body=body, headers=all_headers,
                                    credentials=self.credentials)


def extract_credentials(url):
    """Extract authentication (user name and password) credentials from the
    given URL.
    
    >>> extract_credentials('http://localhost:5984/_config/')
    ('http://localhost:5984/_config/', (None, None))
    >>> extract_credentials('http://joe:secret@localhost:5984/_config/')
    ('http://localhost:5984/_config/', ('joe', 'secret'))
    """
    parts = urlsplit(url)
    netloc = parts[1]
    if '@' in netloc:
        creds, netloc = netloc.split('@')
        username, password = creds.split(':')
        parts = list(parts)
        parts[1] = netloc
    else:
        username = None
        password = None
    return urlunsplit(parts), (username, password)


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
    """
    if base and base.endswith('/'):
        base = base[:-1]
    retval = [base]

    # build the path
    path = '/'.join([''] + [quote(s) for s in path if s is not None])
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

