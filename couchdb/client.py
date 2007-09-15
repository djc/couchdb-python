# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Python client API for CouchDB."""

import httplib2
from urllib import quote, urlencode
import simplejson as json

__all__ = ['ResourceNotFound', 'ResourceConflict', 'ServerError', 'Server']
__docformat__ = 'restructuredtext en'


class ResourceNotFound(Exception):
    """Exception raised when a 404 HTTP error is received in response to a
    request.
    """


class ResourceConflict(Exception):
    """Exception raised when a 409 HTTP error is received in response to a
    request.
    """


class ServerError(Exception):
    """Exception raised when a 500 HTTP error is received in response to a
    request.
    """


class Server(object):
    """Representation of a CouchDB server.

    >>> server = Server('http://localhost:8888/')
    >>> server.version
    (0, 6, 4)

    This class behaves like a dictionary of databases. For example, to get a
    list of database names on the server, you can simply iterate over the
    server object:

    >>> for name in server:
    ...     print repr(name)
    u'test'
    >>> 'test' in server
    True
    >>> len(server)
    1

    New databases can be created using the `create` method:

    >>> db = server.create('foo')
    >>> db
    <Database 'foo'>
    >>> db.name
    'foo'
    >>> del server['foo']
    """

    def __init__(self, uri):
        self.resource =  Resource(httplib2.Http(), uri)

    def __contains__(self, name):
        try:
            self.resource.get(name) # FIXME: should use HEAD
            return True
        except ResourceNotFound:
            return False

    def __iter__(self):
        """Iterate over the names of all databases."""
        return iter(self.resource.get('_all_dbs'))

    def __len__(self):
        """Return the number of databases."""
        return len(self.resource.get('_all_dbs'))

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.resource.uri)

    def __delitem__(self, name):
        """Remove the database with the specified name.
        
        :param name: the name of the database
        :raise ResourceNotFound: if no database with that name exists
        """
        self.resource.delete(name)

    def __getitem__(self, name):
        """Return a `Database` object representing the database with the
        specified name.
        
        :param name: the name of the database
        :raise ResourceNotFound: if no database with that name exists
        """
        return Database(self.resource, name)

    def _get_version(self):
        """Return the version number of the CouchDB server.
        
        Note that this results in a request being made, and can also be used
        to check for the availability of the server.
        """
        data = self.resource.get()
        version = data['version']
        return tuple([int(part) for part in version.split('.')])
    version = property(_get_version)

    def create(self, name):
        """Create a new database with the given name.
        
        :param name: the name of the database
        :return: a `Database` object representing the created database
        """
        self.resource.put(name)
        return Database(self.resource, name)


class Database(object):
    """Representation of a database on a CouchDB server."""

    def __init__(self, resource, name):
        self.resource = Resource(resource.http, URI(resource.uri, name))
        self.name = name

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.name)

    def __contains__(self, id):
        """Return whether the database contains a document with the specified
        ID.
        
        :param id: the document ID
        :return: `True` if a document with the ID exists, `False` otherwise
        """
        try:
            self.resource.get(id) # FIXME: should use HEAD
            return True
        except ResourceNotFound:
            return False

    def __iter__(self):
        """Return the IDs of all documents in the database."""
        return (item.id for item in self.view('_all_docs'))

    def __len__(self):
        """Return the number of documents in the database."""
        return self.resource.get()['doc_count']

    def __delitem__(self, id):
        """Remove the document with the specified ID from the database.
        
        :param id: the document ID
        """
        self.resource.delete(id)

    def __getitem__(self, id):
        """Return the document with the specified ID.
        
        :param id: the document ID
        :return: a `Row` object representing the requested document
        :rtype: `Row`
        """
        return Row(self.resource, self.resource.get(id))

    def __setitem__(self, id, content):
        """Create or update a document with the specified ID.
        
        :param id: the document ID
        :param content: the document content; either a plain dictionary for
                        new documents, or a `Row` object for existing
                        documents
        :return: a `Row` object representing the requested document
        :rtype: `Row`
        """
        if isinstance(content, Row):
            row = content
            content = row.copy()
            content['_rev'] = row.rev
        data = self.resource.put(id, content=content)
        content['_id'] = data['_id']
        content['_rev'] = data['_rev']

    def create(self, **content):
        """Create a new document in the database with a generated ID.
        
        Any keyword arguments are used to populate the fields of the new
        document.
        
        :return: the ID of the created document
        :rtype: `unicode`
        """
        data = self.resource.post(content=content)
        return data['_id']

    def query(self, *args, **kwargs):
        """Execute an ad-hoc query against the database.
        
        The query can either be specified as a string containing the view
        function definition, or by using keyword arguments, from which a
        simple Javascript view function is dynamically constructed.
        
        :return: an iterable over the resulting `Row` objects
        :rtype: ``generator``
        """
        if kwargs:
            assert not args
            code = 'function(doc){if(' + '&&'.join([
                'doc.%s==%s' % (k, json.dumps(v)) for k, v in kwargs.items()
            ]) + ')return doc;}'
        else:
            assert len(args) == 1
            code = args[0]

        data = self.resource.post('_temp_view', content=code)
        for row in data['rows']:
            yield Row(row)

    def view(self, name, **kwargs):
        """Execute a predefined view.
        
        :return: a `View` object
        :rtype: `View`
        """
        return View(self.resource, name)(**kwargs)


class View(object):
    """Representation of a permanent view on the server."""

    def __init__(self, resource, name):
        self.resource = Resource(resource.http, URI(resource.uri, name))
        self.name = name

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.name)

    def __call__(self, **kwargs):
        data = self.resource.get(**kwargs)
        for row in data['rows']:
            yield Row(row)

    def __iter__(self):
        return self()


class Row(dict):
    """Representation of a row as returned by database views.
    
    This is basically just a dictionary with the two additional properties
    `id` and `rev`, which contain the document ID and revision, respectively.
    """

    def __init__(self, content):
        dict.__init__(self, content)
        self._id = self.pop('_id')
        self._rev = self.pop('_rev')

    def __repr__(self):
        return '<%s %r@%r>' % (type(self).__name__, self.id, self.rev)

    id = property(lambda self: self._id)
    rev = property(lambda self: self._rev)


# Internals


class Resource(object):

    def __init__(self, http, uri):
        self.http = http
        self.uri = uri

    def delete(self, path=None, headers=None, **params):
        return self._request('DELETE', path, headers=headers, **params)

    def get(self, path=None, headers=None, **params):
        return self._request('GET', path, headers=headers, **params)

    def head(self, path=None, headers=None, **params):
        return self._request('HEAD', path, headers=headers, **params)

    def post(self, path=None, content=None, headers=None, **params):
        return self._request('POST', path, content=content, headers=headers,
                             **params)

    def put(self, path=None, content=None, headers=None, **params):
        return self._request('PUT', path, content=content, headers=headers,
                             **params)

    def _request(self, method, path=None, content=None, headers=None,
                 **params):
        headers = headers or {}
        body = None
        if content:
            if not isinstance(content, basestring):
                body = json.dumps(content)
                headers.setdefault('Content-Type', 'application/json')
            else:
                body = content
        resp, data = self.http.request(URI(self.uri, path), method, body=body,
                                       headers=headers)
        if data:# FIXME and resp.get('content-type') == 'application/json':
            data = json.loads(data)
        if resp.status >= 500:
            raise ServerError()
        elif resp.status == 404:
            raise ResourceNotFound()
        elif resp.status == 409:
            raise ResourceConflict()
        return data


def URI(base, *path, **query):
    """Assemble a URI based on a base, any number of path segments, and query
    string parameters.

    >>> URI('http://example.org/', '/_all_dbs')
    'http://example.org/_all_dbs'
    """
    if base and base.endswith('/'):
        base = base[:-1]
    retval = [base]

    # build the path
    path = '/'.join([''] +
                    [quote(s.strip('/')) for s in path if s is not None])
    if path:
        retval.append(path)

    # build the query string
    params = []
    for name, value in query.items():
        if type(value) in (list, tuple):
            params.extend([(name, i) for i in value if i is not None])
        elif value is not None:
            params.append((name, value))
    if params:
        retval.extend(['?', urlencode(params)])

    return ''.join(retval)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
