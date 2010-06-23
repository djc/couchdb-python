Getting started with couchdb-python
===================================

Some snippets of code to get you started with writing code against CouchDB.

Starting off::

    >>> import couchdb
    >>> couch = couchdb.Server()

This gets you a Server object, representing a CouchDB server. By default, it
assumes CouchDB is running on localhost:5894. If your CouchDB server is
running elsewhere, set it up like this:

    >>> couch = couchdb.Server('http://example.com:5984/')

You can create a new database from Python, or use an existing database:

    >>> db = couch.create('test') # newly created
    >>> db = couch['mydb'] # existing

After selecting a database, create a document and insert it into the db:

    >>> doc = {'foo': 'bar'}
    >>> db.save(doc)
    ('e0658cab843b59e63c8779a9a5000b01', '1-4c6114c65e295552ab1019e2b046b10e')
    >>> doc
    {'_rev': '1-4c6114c65e295552ab1019e2b046b10e', 'foo': 'bar', '_id': 'e0658cab843b59e63c8779a9a5000b01'}

The ``save()`` method returns the ID and "rev" for the newly created document.
You can also set your own ID by including an ``_id`` item in the document.

Getting the document out again is easy:

    >>> db['e0658cab843b59e63c8779a9a5000b01']
    <Document 'e0658cab843b59e63c8779a9a5000b01'@'1-4c6114c65e295552ab1019e2b046b10e' {'foo': 'bar'}>

To find all your documents, simply iterate over the database:

    >>> for id in db:
    ...     print id
    ...
    'e0658cab843b59e63c8779a9a5000b01'

Now we can clean up the test document and database we created:

    >>> db.delete(doc)
    >>> couch.delete('test')
