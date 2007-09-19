# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Python client API for CouchDB.

>>> server = Server('http://localhost:8888/')
>>> db = server.create('python-tests')
>>> doc_id = db.create({'type': 'Person', 'name': 'John Doe'})
>>> doc = db[doc_id]
>>> doc['type']
u'Person'
>>> doc['name']
u'John Doe'
>>> del db[doc.id]
>>> doc.id in db
False

>>> del server['python-tests']
"""

import httplib2
from urllib import quote, urlencode
import re
import simplejson as json

__all__ = ['ResourceNotFound', 'ResourceConflict', 'ServerError', 'Server',
           'Database', 'View']
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
    server object.

    New databases can be created using the `create` method:

    >>> db = server.create('python-tests')
    >>> db
    <Database 'python-tests'>

    You can access existing databases using item access, specifying the database
    name as the key:

    >>> db = server['python-tests']
    >>> db.name
    'python-tests'

    Databases can be deleted using a ``del`` statement:

    >>> del server['python-tests']
    """

    def __init__(self, uri):
        """Initialize the server object.
        
        :param uri: the URI of the server (for example
                    ``http://localhost:8888/``)
        """
        self.resource = Resource(httplib2.Http(), uri)

    def __contains__(self, name):
        """Return whether the server contains a database with the specified
        name.

        :param name: the database name
        :return: `True` if a database with the name exists, `False` otherwise
        """
        try:
            self.resource.get(validate_dbname(name)) # FIXME: should use HEAD
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
        self.resource.delete(validate_dbname(name))

    def __getitem__(self, name):
        """Return a `Database` object representing the database with the
        specified name.

        :param name: the name of the database
        :return: a `Database` object representing the database
        :rtype: `Database`
        :raise ResourceNotFound: if no database with that name exists
        """
        return Database(uri(self.resource.uri, name), validate_dbname(name),
                        http=self.resource.http)

    def _get_version(self):
        data = self.resource.get()
        version = data['version']
        return tuple([int(part) for part in version.split('.')])
    version = property(_get_version, doc="""\
        The version number tuple for the CouchDB server.

        Note that this results in a request being made, and can also be used
        to check for the availability of the server.
        
        :type: `tuple`
        """)

    def create(self, name):
        """Create a new database with the given name.

        :param name: the name of the database
        :return: a `Database` object representing the created database
        :rtype: `Database`
        :raise ResourceConflict: if a database with that name already exists
        """
        self.resource.put(validate_dbname(name))
        return self[name]


class Database(object):
    """Representation of a database on a CouchDB server.

    >>> server = Server('http://localhost:8888/')
    >>> db = server.create('python-tests')

    New documents can be added to the database using the `create()` method:

    >>> doc_id = db.create({'type': 'Person', 'name': 'John Doe'})

    This class provides a dictionary-like interface to databases: documents are
    retrieved by their ID using item access

    >>> doc = db[doc_id]
    >>> doc                 #doctest: +ELLIPSIS
    <Row u'...'@...>

    Documents are represented as instances of the `Row` class, which is
    basically just a normal dictionary with the additional attributes ``id`` and
    ``rev``:

    >>> doc.id, doc.rev     #doctest: +ELLIPSIS
    (u'...', ...)
    >>> doc['type']
    u'Person'
    >>> doc['name']
    u'John Doe'

    To update an existing document, you use item access, too:

    >>> doc['name'] = 'Mary Jane'
    >>> db[doc.id] = doc

    The `create()` method creates a document with an auto-generated ID. If you
    want to explicitly specify the ID, you'd use item access just as with
    updating:

    >>> db['JohnDoe'] = {'type': 'person', 'name': 'John Doe'}

    >>> 'JohnDoe' in db
    True
    >>> len(db)
    2
    >>> list(db)            #doctest: +ELLIPSIS
    [u'...', u'JohnDoe']

    >>> del server['python-tests']
    """

    def __init__(self, uri, name=None, http=None):
        self.resource = Resource(http, uri)
        self._name = name

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
        doc = self[id] # FIXME: this should use HEAD once Etags are supported
        self.resource.delete(id, rev=doc.rev)

    def __getitem__(self, id):
        """Return the document with the specified ID.

        :param id: the document ID
        :return: a `Row` object representing the requested document
        :rtype: `Row`
        """
        return Row(self.resource.get(id))

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

    def _get_name(self):
        if self._name is None:
            self._name = self.resource.get()['db_name']
        return self._name
    name = property(_get_name)

    def create(self, data):
        """Create a new document in the database with a generated ID.

        Any keyword arguments are used to populate the fields of the new
        document.

        :param data: the data to store in the document
        :return: the ID of the created document
        :rtype: `unicode`
        """
        data = self.resource.post(content=data)
        return data['_id']

    def get(self, id, default=None):
        """Return the document with the specified ID.

        :param id: the document ID
        :param default: the default value to return when the document is not
                        found
        :return: a `Row` object representing the requested document, or `None`
                 if no document with the ID was found
        :rtype: `Row`
        """
        try:
            return self[id]
        except ResourceNotFound:
            return default

    def query(self, code, **options):
        """Execute an ad-hoc query against the database.
        
        >>> server = Server('http://localhost:8888/')
        >>> db = server.create('python-tests')
        >>> db['johndoe'] = dict(type='Person', name='John Doe')
        >>> db['maryjane'] = dict(type='Person', name='Mary Jane')
        >>> db['gotham'] = dict(type='City', name='Gotham City')
        >>> code = '''function(doc) {
        ...     if (doc.type=='Person')
        ...         return {'key': doc.name};
        ... }'''
        >>> for row in db.query(code):
        ...     print row['key']
        John Doe
        Mary Jane
        
        >>> for row in db.query(code, reverse=True):
        ...     print row['key']
        Mary Jane
        John Doe
        
        >>> for row in db.query(code, key='John Doe'):
        ...     print row['key']
        John Doe
        
        >>> del server['python-tests']
        
        :param code: the code of the view function
        :return: an iterable over the resulting `Row` objects
        :rtype: ``generator``
        """
        json_options = {}
        for name, value in options.items():
            json_options[name] = json.dumps(value)
        data = self.resource.post('_temp_view', content=code, **json_options)
        for row in data['rows']:
            yield Row(row)

    def view(self, name, **options):
        """Execute a predefined view.
        
        >>> server = Server('http://localhost:8888/')
        >>> db = server.create('python-tests')
        >>> db['gotham'] = dict(type='City', name='Gotham City')
        
        >>> for row in db.view('_all_docs'):
        ...     print row.id
        gotham
        
        >>> del server['python-tests']
        
        :return: a `View` object
        :rtype: `View`
        """
        view = View(uri(self.resource.uri, name), name,
                    http=self.resource.http)
        return view(**options)


class View(object):
    """Representation of a permanent view on the server."""

    def __init__(self, uri, name, http=None):
        self.resource = Resource(http, uri)
        self.name = name

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.name)

    def __call__(self, **options):
        json_options = {}
        for name, value in options.items():
            json_options[name] = json.dumps(value)
        data = self.resource.get(**json_options)
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
        return '<%s %r@%r %r>' % (type(self).__name__, self.id, self.rev,
                                  dict(self.items()))

    id = property(lambda self: self._id)
    rev = property(lambda self: self._rev)


# Internals


class Resource(object):

    def __init__(self, http, uri):
        if http is None:
            http = httplib2.Http()
            http.force_exception_to_status_code = False
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

        resp, data = self.http.request(uri(self.uri, path, **params), method,
                                       body=body, headers=headers)
        status_code = int(resp.status)
        if data:# FIXME and resp.get('content-type') == 'application/json':
            try:
                data = json.loads(data)
            except ValueError:
                pass

        if status_code >= 400:
            if type(data) is dict:
                error = data.get('error', {}).get('reason', data)
            else:
                error = data
            if status_code == 404:
                raise ResourceNotFound(error)
            elif status_code == 409:
                raise ResourceConflict(error)
            else:
                raise ServerError(error)

        return data


def uri(base, *path, **query):
    """Assemble a uri based on a base, any number of path segments, and query
    string parameters.

    >>> uri('http://example.org/', '/_all_dbs')
    'http://example.org/_all_dbs'
    """
    if base and base.endswith('/'):
        base = base[:-1]
    retval = [base]

    # build the path
    path = '/'.join([''] +
                    [unicode_quote(s.strip('/')) for s in path
                     if s is not None])
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
        retval.extend(['?', unicode_urlencode(params)])

    return ''.join(retval)

def unicode_quote(string):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return quote(string)

def unicode_urlencode(data):
    if isinstance(data, dict):
        data = data.items()
    params = []
    for name, value in data:
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        params.append((name, value))
    return urlencode(params)

VALID_DB_NAME = re.compile(r'^[a-z0-9_$()+-/]+$')
def validate_dbname(name):
    if not VALID_DB_NAME.match(name):
        raise ValueError('Invalid database name')
    return name
