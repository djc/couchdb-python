# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Python client API for CouchDB.

>>> server = Server('http://localhost:5984/')
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

__all__ = ['PreconditionFailed', 'ResourceNotFound', 'ResourceConflict',
           'ServerError', 'Server', 'Database', 'Document', 'ViewResults',
           'Row']
__docformat__ = 'restructuredtext en'


class PreconditionFailed(Exception):
    """Exception raised when a 412 HTTP error is received in response to a
    request.
    """


class ResourceNotFound(Exception):
    """Exception raised when a 404 HTTP error is received in response to a
    request.
    """


class ResourceConflict(Exception):
    """Exception raised when a 409 HTTP error is received in response to a
    request.
    """


class ServerError(Exception):
    """Exception raised when an unexpected HTTP error is received in response
    to a request.
    """


class Server(object):
    """Representation of a CouchDB server.

    >>> server = Server('http://localhost:5984/')

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

    def __init__(self, uri, cache=None, timeout=None):
        """Initialize the server object.
        
        :param uri: the URI of the server (for example
                    ``http://localhost:5984/``)
        :param cache: either a cache directory path (as a string) or an object
                      compatible with the `httplib2.FileCache` interface. If
                      `None` (the default), no caching is performed.
        :param timeout: socket timeout in number of seconds, or `None` for no
                        timeout
        """
        http = httplib2.Http(cache=cache, timeout=timeout)
        http.force_exception_to_status_code = False
        self.resource = Resource(http, uri)

    def __contains__(self, name):
        """Return whether the server contains a database with the specified
        name.

        :param name: the database name
        :return: `True` if a database with the name exists, `False` otherwise
        """
        try:
            self.resource.head(validate_dbname(name))
            return True
        except ResourceNotFound:
            return False

    def __iter__(self):
        """Iterate over the names of all databases."""
        resp, data = self.resource.get('_all_dbs')
        return iter(data)

    def __len__(self):
        """Return the number of databases."""
        resp, data = self.resource.get('_all_dbs')
        return len(data)

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
        resp, data = self.resource.get()
        return data['version']
    version = property(_get_version, doc="""\
        The version number tuple for the CouchDB server.

        Note that this results in a request being made, and can also be used
        to check for the availability of the server.
        
        :type: `unicode`
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

    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')

    New documents can be added to the database using the `create()` method:

    >>> doc_id = db.create({'type': 'Person', 'name': 'John Doe'})

    This class provides a dictionary-like interface to databases: documents are
    retrieved by their ID using item access

    >>> doc = db[doc_id]
    >>> doc                 #doctest: +ELLIPSIS
    <Document u'...'@... {...}>

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
            self.resource.head(id)
            return True
        except ResourceNotFound:
            return False

    def __iter__(self):
        """Return the IDs of all documents in the database."""
        return iter([item.id for item in self.view('_all_docs')])

    def __len__(self):
        """Return the number of documents in the database."""
        resp, data = self.resource.get()
        return data['doc_count']

    def __delitem__(self, id):
        """Remove the document with the specified ID from the database.

        :param id: the document ID
        """
        resp, data = self.resource.head(id)
        self.resource.delete(id, rev=resp['etag'].strip('"'))

    def __getitem__(self, id):
        """Return the document with the specified ID.

        :param id: the document ID
        :return: a `Row` object representing the requested document
        :rtype: `Document`
        """
        resp, data = self.resource.get(id)
        return Document(data)

    def __setitem__(self, id, content):
        """Create or update a document with the specified ID.

        :param id: the document ID
        :param content: the document content; either a plain dictionary for
                        new documents, or a `Row` object for existing
                        documents
        """
        resp, data = self.resource.put(id, content=content)
        content.update({'_id': data['id'], '_rev': data['rev']})

    def _get_name(self):
        if self._name is None:
            self._name = self.info()['db_name']
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
        resp, data = self.resource.post(content=data)
        return data['id']

    def delete(self, doc):
        """Delete the given document from the database.

        Use this method in preference over ``__del__`` to ensure you're
        deleting the revision that you had previously retrieved. In the case
        the document has been updated since it was retrieved, this method will
        raise a `PreconditionFailed` exception.

        >>> server = Server('http://localhost:5984/')
        >>> db = server.create('python-tests')

        >>> doc = dict(type='Person', name='John Doe')
        >>> db['johndoe'] = doc
        >>> doc2 = db['johndoe']
        >>> doc2['age'] = 42
        >>> db['johndoe'] = doc2
        >>> db.delete(doc)
        Traceback (most recent call last):
          ...
        PreconditionFailed: (u'conflict', u'Update conflict')

        >>> del server['python-tests']
        
        :param doc: a dictionary or `Document` object holding the document data
        :raise PreconditionFailed: if the document was updated in the database
        :since: 0.4.1
        """
        self.resource.delete(doc['_id'], rev=doc['_rev'])

    def get(self, id, default=None, **options):
        """Return the document with the specified ID.

        :param id: the document ID
        :param default: the default value to return when the document is not
                        found
        :return: a `Row` object representing the requested document, or `None`
                 if no document with the ID was found
        :rtype: `Document`
        """
        try:
            resp, data = self.resource.get(id, **options)
        except ResourceNotFound:
            return default
        else:
            return Document(data)

    def info(self):
        """Return information about the database as a dictionary.
        
        The returned dictionary exactly corresponds to the JSON response to
        a ``GET`` request on the database URI.
        
        :return: a dictionary of database properties
        :rtype: ``dict``
        :since: 0.4
        """
        resp, data = self.resource.get()
        return data

    def delete_attachment(self, doc, filename):
        """Delete the specified attachment.
        
        :param doc: the dictionary or `Document` object representing the
                    document that the attachment belongs to
        :param filename: the name of the attachment file
        :since: 0.4.1
        """
        self.resource(doc['_id']).delete(filename, rev=doc['_rev'])

    def get_attachment(self, id_or_doc, filename, default=None):
        """Return an attachment from the specified doc id and filename.
        
        :param id_or_doc: either a document ID or a dictionary or `Document`
                          object representing the document that the attachment
                          belongs to
        :param filename: the name of the attachment file
        :param default: default value to return when the document or attachment
                        is not found
        :return: the content of the attachment as a string, or the value of the
                 `default` argument if the attachment is not found
        :since: 0.4.1
        """
        if isinstance(id_or_doc, basestring):
            id = id_or_doc
        else:
            id = id_or_doc['_id']
        try:
            resp, data = self.resource(id).get(filename)
            return data
        except ResourceNotFound:
            return default

    def put_attachment(self, doc, filename, content, content_type):
        """Create or replace an attachment.
        
        :param doc: the dictionary or `Document` object representing the
                    document that the attachment should be added to
        :param filename: the name of the attachment file
        :param content: the content to upload, either a file-like object or
                        a string
        :param content_type: content type of the attachment
        :since: 0.4.1
        """
        if hasattr(content, 'read'):
            content = content.read()
        self.resource(doc['_id']).put(filename, content=content, headers={
            'Content-Type': content_type
        }, rev=doc['_rev'])

    def query(self, map_fun, reduce_fun=None, language='javascript',
              wrapper=None, **options):
        """Execute an ad-hoc query (a "temp view") against the database.
        
        >>> server = Server('http://localhost:5984/')
        >>> db = server.create('python-tests')
        >>> db['johndoe'] = dict(type='Person', name='John Doe')
        >>> db['maryjane'] = dict(type='Person', name='Mary Jane')
        >>> db['gotham'] = dict(type='City', name='Gotham City')
        >>> map_fun = '''function(doc) {
        ...     if (doc.type == 'Person')
        ...         emit(doc.name, null);
        ... }'''
        >>> for row in db.query(map_fun):
        ...     print row.key
        John Doe
        Mary Jane
        
        >>> for row in db.query(map_fun, descending=True):
        ...     print row.key
        Mary Jane
        John Doe
        
        >>> for row in db.query(map_fun, key='John Doe'):
        ...     print row.key
        John Doe
        
        >>> del server['python-tests']
        
        :param map_fun: the code of the map function
        :param reduce_fun: the code of the reduce function (optional)
        :param language: the language of the functions, to determine which view
                         server to use
        :param wrapper: an optional callable that should be used to wrap the
                        result rows
        :param options: optional query string parameters
        :return: the view reults
        :rtype: `ViewResults`
        """
        return TemporaryView(uri(self.resource.uri, '_temp_view'), map_fun,
                             reduce_fun, language=language, wrapper=wrapper,
                             http=self.resource.http)(**options)

    def update(self, documents):
        """Perform a bulk update or insertion of the given documents using a
        single HTTP request.
        
        >>> server = Server('http://localhost:5984/')
        >>> db = server.create('python-tests')
        >>> for doc in db.update([
        ...     Document(type='Person', name='John Doe'),
        ...     Document(type='Person', name='Mary Jane'),
        ...     Document(type='City', name='Gotham City')
        ... ]):
        ...     print repr(doc) #doctest: +ELLIPSIS
        <Document u'...'@u'...' {'type': 'Person', 'name': 'John Doe'}>
        <Document u'...'@u'...' {'type': 'Person', 'name': 'Mary Jane'}>
        <Document u'...'@u'...' {'type': 'City', 'name': 'Gotham City'}>
        
        >>> del server['python-tests']
        
        If an object in the documents list is not a dictionary, this method
        looks for an ``items()`` method that can be used to convert the object
        to a dictionary. In this case, the returned generator will not update
        and yield the original object, but rather yield a dictionary with
        ``id`` and ``rev`` keys.
        
        :param documents: a sequence of dictionaries or `Document` objects, or
                          objects providing a ``items()`` method that can be
                          used to convert them to a dictionary
        :return: an iterable over the resulting documents
        :rtype: ``generator``
        
        :since: version 0.2
        """
        docs = []
        for doc in documents:
            if isinstance(doc, dict):
                docs.append(doc)
            elif hasattr(doc, 'items'):
                docs.append(dict(doc.items()))
            else:
                raise TypeError('expected dict, got %s' % type(doc))
        resp, data = self.resource.post('_bulk_docs', content={'docs': docs})
        assert data['ok'] # FIXME: Should probably raise a proper exception
        def _update():
            for idx, result in enumerate(data['new_revs']):
                doc = documents[idx]
                if isinstance(doc, dict):
                    doc.update({'_id': result['id'], '_rev': result['rev']})
                    yield doc
                else:
                    yield result
        return _update()

    def view(self, name, wrapper=None, **options):
        """Execute a predefined view.
        
        >>> server = Server('http://localhost:5984/')
        >>> db = server.create('python-tests')
        >>> db['gotham'] = dict(type='City', name='Gotham City')
        
        >>> for row in db.view('_all_docs'):
        ...     print row.id
        gotham
        
        >>> del server['python-tests']
        
        :param name: the name of the view, including the ``_view/design_docid``
                     prefix for custom views
        :param wrapper: an optional callable that should be used to wrap the
                        result rows
        :param options: optional query string parameters
        :return: the view results
        :rtype: `ViewResults`
        """
        if not name.startswith('_'):
            name = '_view/' + name
        return PermanentView(uri(self.resource.uri, *name.split('/')), name,
                             wrapper=wrapper,
                             http=self.resource.http)(**options)


class Document(dict):
    """Representation of a document in the database.

    This is basically just a dictionary with the two additional properties
    `id` and `rev`, which contain the document ID and revision, respectively.
    """

    def __repr__(self):
        return '<%s %r@%r %r>' % (type(self).__name__, self.id, self.rev,
                                  dict([(k,v) for k,v in self.items()
                                        if k not in ('_id', '_rev')]))

    id = property(lambda self: self['_id'])
    rev = property(lambda self: self['_rev'])


class View(object):
    """Abstract representation of a view or query."""

    def __init__(self, uri, wrapper=None, http=None):
        self.resource = Resource(http, uri)
        self.wrapper = wrapper

    def __call__(self, **options):
        return ViewResults(self, options)

    def __iter__(self):
        return self()

    def _encode_options(self, options):
        retval = {}
        for name, value in options.items():
            if name in ('key', 'startkey', 'endkey') \
                    or not isinstance(value, basestring):
                value = json.dumps(value, ensure_ascii=False)
            retval[name] = value
        return retval

    def _exec(self, options):
        raise NotImplementedError


class PermanentView(View):
    """Representation of a permanent view on the server."""

    def __init__(self, uri, name, wrapper=None, http=None):
        View.__init__(self, uri, wrapper=wrapper, http=http)
        self.resource = Resource(http, uri)
        self.name = name

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.name)

    def _exec(self, options):
        resp, data = self.resource.get(**self._encode_options(options))
        return data


class TemporaryView(View):
    """Representation of a temporary view."""

    def __init__(self, uri, map_fun=None, reduce_fun=None,
                 language='javascript', wrapper=None, http=None):
        View.__init__(self, uri, wrapper=wrapper, http=http)
        self.resource = Resource(http, uri)
        self.map_fun = map_fun
        self.reduce_fun = reduce_fun
        self.language = language

    def __repr__(self):
        return '<%s %r %r>' % (type(self).__name__, self.map_fun,
                               self.reduce_fun)

    def _exec(self, options):
        body = {'map': self.map_fun, 'language': self.language}
        if self.reduce_fun:
            body['reduce'] = self.reduce_fun
        content = json.dumps(body, ensure_ascii=False).encode('utf-8')
        resp, data = self.resource.post(content=content, headers={
            'Content-Type': 'application/json'
        }, **self._encode_options(options))
        return data


class ViewResults(object):
    """Representation of a parameterized view (either permanent or temporary)
    and the results it produces.
    
    This class allows the specification of ``key``, ``startkey``, and
    ``endkey`` options using Python slice notation.
    
    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')
    >>> db['johndoe'] = dict(type='Person', name='John Doe')
    >>> db['maryjane'] = dict(type='Person', name='Mary Jane')
    >>> db['gotham'] = dict(type='City', name='Gotham City')
    >>> map_fun = '''function(doc) {
    ...     emit([doc.type, doc.name], doc.name);
    ... }'''
    >>> results = db.query(map_fun)

    At this point, the view has not actually been accessed yet. It is accessed
    as soon as it is iterated over, its length is requested, or one of its
    `rows`, `total_rows`, or `offset` properties are accessed:
    
    >>> len(results)
    3

    You can use slices to apply ``startkey`` and/or ``endkey`` options to the
    view:

    >>> people = results[['Person']:['Person','ZZZZ']]
    >>> for person in people:
    ...     print person.value
    John Doe
    Mary Jane
    >>> people.total_rows, people.offset
    (3, 1)
    
    Use plain indexed notation (without a slice) to apply the ``key`` option.
    Note that as CouchDB makes no claim that keys are unique in a view, this
    can still return multiple rows:
    
    >>> list(results[['City', 'Gotham City']])
    [<Row id=u'gotham', key=[u'City', u'Gotham City'], value=u'Gotham City'>]
    """

    def __init__(self, view, options):
        self.view = view
        self.options = options
        self._rows = self._total_rows = self._offset = None

    def __repr__(self):
        return '<%s %r %r>' % (type(self).__name__, self.view, self.options)

    def __getitem__(self, key):
        options = self.options.copy()
        if type(key) is slice:
            if key.start is not None:
                options['startkey'] = key.start
            if key.stop is not None:
                options['endkey'] = key.stop
            return ViewResults(self.view, options)
        else:
            options['key'] = key
            return ViewResults(self.view, options)

    def __iter__(self):
        wrapper = self.view.wrapper
        for row in self.rows:
            if wrapper is not None:
                yield wrapper(row)
            else:
                yield row

    def __len__(self):
        return len(self.rows)

    def _fetch(self):
        data = self.view._exec(self.options)
        self._rows = [Row(r.get('id'), r['key'], r['value'])
                      for r in data['rows']]
        self._total_rows = data.get('total_rows')
        self._offset = data.get('offset', 0)

    def _get_rows(self):
        if self._rows is None:
            self._fetch()
        return self._rows
    rows = property(_get_rows, doc="""\
        The list of rows returned by the view.
        
        :type: `list`
        """)

    def _get_total_rows(self):
        if self._rows is None:
            self._fetch()
        return self._total_rows
    total_rows = property(_get_total_rows, doc="""\
        The total number of rows in this view.
        
        This value is `None` for reduce views.
        
        :type: `int` or ``NoneType`` for reduce views
        """)

    def _get_offset(self):
        if self._rows is None:
            self._fetch()
        return self._offset
    offset = property(_get_offset, doc="""\
        The offset of the results from the first row in the view.
        
        This value is 0 for reduce views.
        
        :type: `int`
        """)


class Row(object):
    """Representation of a row as returned by database views."""

    def __init__(self, id, key, value):
        self.id = id #: The document ID, or `None` for rows in a reduce view
        self.key = key #: The key of the row
        self.value = value #: The value of the row

    def __repr__(self):
        if self.id is None:
            return '<%s key=%r, value=%r>' % (type(self).__name__, self.key,
                                              self.value)
        return '<%s id=%r, key=%r, value=%r>' % (type(self).__name__, self.id,
                                                 self.key, self.value)


# Internals


class Resource(object):

    def __init__(self, http, uri):
        if http is None:
            http = httplib2.Http()
            http.force_exception_to_status_code = False
        self.http = http
        self.uri = uri

    def __call__(self, path):
        return type(self)(self.http, uri(self.uri, path))

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
        from couchdb import __version__
        headers = headers or {}
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('User-Agent', 'couchdb-python %s' % __version__)
        body = None
        if content is not None:
            if not isinstance(content, basestring):
                body = json.dumps(content, ensure_ascii=False).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')
            else:
                body = content

        resp, data = self.http.request(uri(self.uri, path, **params), method,
                                       body=body, headers=headers)
        status_code = int(resp.status)
        if data and resp.get('content-type') == 'application/json':
            try:
                data = json.loads(data)
            except ValueError:
                pass

        if status_code >= 400:
            if type(data) is dict:
                error = (data.get('error'), data.get('reason'))
            else:
                error = data
            if status_code == 404:
                raise ResourceNotFound(error)
            elif status_code == 409:
                raise ResourceConflict(error)
            elif status_code == 412:
                raise PreconditionFailed(error)
            else:
                raise ServerError((status_code, error))

        return resp, data


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
            if value is True:
                value = 'true'
            elif value is False:
                value = 'false'
            params.append((name, value))
    if params:
        retval.extend(['?', unicode_urlencode(params)])

    return ''.join(retval)

def unicode_quote(string, safe=''):
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return quote(string, safe)

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
