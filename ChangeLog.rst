Version 1.2 (2018-02-09)
------------------------

* Fixed some issues relating to usage with Python 3
* Remove support for Python 2.6 and 3.x with x < 4
* Fix logging response in query server (fixes #321)
* Fix HTTP authentication password encoding (fixes #302)
* Add missing ``http.Forbidden`` error (fixes #305)
* Show ``doc`` property on ``Row`` string representation
* Add methods for mango queries and indexes
* Allow mango filters in ``_changes`` API


Version 1.1 (2016-08-05)
------------------------

* Add script to load design documents from disk
* Add methods on ``Server`` for user/session management
* Add microseconds support for DateTimeFields
* Handle changes feed as emitted by CouchBase (fixes #289)
* Support Python 3 in ``couchdb-dump`` script (fixes #296)
* Expand relative URLs from Location headers (fixes #287)
* Correctly handle ``_rev`` fields in mapped documents (fixes #278)


Version 1.0.1 (2016-03-12)
--------------------------

* Make sure connections are correctly closed on GAE (fixes #224)
* Correctly join path parts in replicate script (fixes #269)
* Fix id and rev for some special documents
* Make it possible to disable SSL verification


Version 1.0 (2014-11-16)
------------------------

* Many smaller Python 3 compatibility issues have been fixed
* Improve handling of binary attachments in the ``couchdb-dump`` tool
* Added testing via tox and support for Travis CI


Version 0.10 (2014-07-15)
-------------------------

* Now compatible with Python 2.7, 3.3 and 3.4
* Added batch processing for the ``couchdb-dump`` tool
* A very basic API to access the ``_security`` object
* A way to access the ``update_seq`` value on view results


Version 0.9 (2013-04-25)
------------------------

* Don't validate database names on the client side. This means some methods
  dealing with database names can return different exceptions than before.
* Use HTTP socket more efficiently to avoid the Nagle algorithm, greatly
  improving performace. Note: add the ``{nodelay, true}`` option to the CouchDB
  server's httpd/socket_options config.
* Add support for show and list functions.
* Add support for calling update handlers.
* Add support for purging documents.
* Add ``iterview()`` for more efficient iteration over large view results.
* Add view cleanup API.
* Enhance ``Server.stats()`` to optionally retrieve a single set of statistics.
* Implement ``Session`` timeouts.
* Add ``error`` property to ``Row`` objects.
* Add ``default=None`` arg to ``mapping.Document.get()`` to make it a little more
  dict-like.
* Enhance ``Database.info()`` so it can also be used to get info for a design
  doc.
* Add view definition options, e.g. collation.
* Fix support for authentication in dump/load tools.
* Support non-ASCII document IDs in serialization format.
* Protect ``ResponseBody`` from being iterated/closed multiple times.
* Rename iteration method for ResponseBody chunks to ``iterchunks()`` to
  prevent usage for non-chunked responses.
* JSON encoding exceptions are no longer masked, resulting in better error
  messages.
* ``cjson`` support is now deprecated.
* Fix ``Row.value`` and ``Row.__repr__`` to never raise exceptions.
* Fix Python view server's reduce to handle empty map results list.
* Use locale-independent timestamp identifiers for HTTP cache.
* Don't require setuptools/distribute to install the core package. (Still
  needed to install the console scripts.)


Version 0.8 (Aug 13, 2010)
--------------------------

* The couchdb-replicate script has changed from being a poor man's version of
  continuous replication (predating it) to being a simple script to help
  kick off replication jobs across databases and servers.
* Reinclude all http exception types in the 'couchdb' package's scope.
* Replaced epydoc API docs by more extensive Sphinx-based documentation.
* Request retries schedule and frequency are now customizable.
* Allow more kinds of request errors to trigger a retry.
* Improve wrapping of view results.
* Added a ``uuids()`` method to the ``client.Server`` class (issue 122).
* Tested with CouchDB 0.10 - 1.0 (and Python 2.4 - 2.7).


Version 0.7.0 (Apr 15, 2010)
----------------------------

* Breaking change: the dependency on ``httplib2`` has been replaced by
  an internal ``couchdb.http`` library. This changes the API in several places.
  Most importantly, ``resource.request()`` now returns a 3-member tuple. 
* Breaking change: ``couchdb.schema`` has been renamed to ``couchdb.mapping``.
  This better reflects what is actually provided. Classes inside
  ``couchdb.mapping`` have been similarly renamed (e.g. ``Schema`` -> ``Mapping``).
* Breaking change: ``couchdb.schema.View`` has been renamed to
  ``couchdb.mapping.ViewField``, in order to help distinguish it from
  ``couchdb.client.View``.
* Breaking change: the ``client.Server`` properties ``version`` and ``config``
  have become methods in order to improve API consistency.
* Prevent ``schema.ListField`` objects from sharing the same default (issue 107).
* Added a ``changes()`` method to the ``client.Database`` class (issue 103).
* Added an optional argument to the 'Database.compact`` method to enable
  view compaction (the rest of issue 37).


Version 0.6.1 (Dec 14, 2009)
----------------------------

* Compatible with CouchDB 0.9.x and 0.10.x.
* Removed debugging statement from ``json`` module (issue 82).
* Fixed a few bugs resulting from typos.
* Added a ``replicate()`` method to the ``client.Server`` class (issue 61).
* Honor the boundary argument in the dump script code (issue 100).
* Added a ``stats()`` method to the ``client.Server`` class.
* Added a ``tasks()`` method to the ``client.Server`` class.
* Allow slashes in path components passed to the uri function (issue 96).
* ``schema.DictField`` objects now have a separate backing dictionary for each
  instance of their ``schema.Document`` (issue 101).
* ``schema.ListField`` proxy objects now have a more consistent (though somewhat
  slower) ``count()`` method (issue 91).
* ``schema.ListField`` objects now have correct behavior for slicing operations
  and the ``pop()`` method (issue 92).
* Added a ``revisions()`` method to the Database class (issue 99).
* Make sure we always return UTF-8 from the view server (issue 81).


Version 0.6 (Jul 2, 2009)
-------------------------

* Compatible with CouchDB 0.9.x.
* ``schema.DictField`` instances no longer need to be bound to a ``Schema``
  (issue 51).
* Added a ``config`` property to the ``client.Server`` class (issue 67).
* Added a ``compact()`` method to the ``client.Database`` class (issue 37).
* Changed the ``update()`` method of the ``client.Database`` class to simplify
  the handling of errors. The method now returns a list of ``(success, docid,
  rev_or_exc)`` tuples. See the docstring of that method for the details.
* ``schema.ListField`` proxy objects now support the ``__contains__()`` and
  ``index()`` methods (issue 77).
* The results of the ``query()`` and ``view()`` methods in the ``schema.Document``
  class are now properly wrapped in objects of the class if the ``include_docs``
  option is set (issue 76).
* Removed the ``eager`` option on the ``query()`` and ``view()`` methods of
  ``schema.Document``. Use the ``include_docs`` option instead, which doesn't
  require an additional request per document.
* Added a ``copy()`` method to the ``client.Database`` class, which translates to
  a HTTP COPY request (issue 74).
* Accessing a non-existing database through ``Server.__getitem__`` now throws
  a ``ResourceNotFound`` exception as advertised (issue 41).
* Added a ``delete()`` method to the ``client.Server`` class for consistency
  (issue 64).
* The ``couchdb-dump`` tool now operates in a streaming fashion, writing one
  document at a time to the resulting MIME multipart file (issue 58).
* It is now possible to explicitly set the JSON module that should be used
  for decoding/encoding JSON data. The currently available choices are
  ``simplejson``, ``cjson``, and ``json`` (the standard library module). It is also
  possible to use custom decoding/encoding functions.
* Add logging to the Python view server. It can now be configured to log to a
  given file or the standard error stream, and the log level can be set debug
  to see all communication between CouchDB and the view server (issue 55).


Version 0.5 (Nov 29, 2008)
--------------------------

* ``schema.Document`` objects can now be used in the documents list passed to
  ``client.Database.update()``.
* ``Server.__contains__()`` and ``Database.__contains__()`` now use the HTTP HEAD
  method to avoid unnecessary transmission of data. ``Database.__del__()`` also
  uses HEAD to determine the latest revision of the document.
* The ``Database`` class now has a method ``delete()`` that takes a document
  dictionary as parameter. This method should be used in preference to
  ``__del__`` as it allow conflict detection and handling.
* Added ``cache`` and ``timeout`` arguments to the ``client.Server`` initializer.
* The ``Database`` class now provides methods for deleting, retrieving, and
  updating attachments.
* The Python view server now exposes a ``log()`` function to map and reduce
  functions (issue 21).
* Handling of the rereduce stage in the Python view server has been fixed.
* The ``Server`` and ``Database`` classes now implement the ``__nonzero__`` hook
  so that they produce sensible results in boolean conditions.
* The client module will now reattempt a request that failed with a
  "connection reset by peer" error.
* inf/nan values now raise a ``ValueError`` on the client side instead of
  triggering an internal server error (issue 31).
* Added a new ``couchdb.design`` module that provides functionality for
  managing views in design documents, so that they can be defined in the
  Python application code, and the design documents actually stored in the
  database can be kept in sync with the definitions in the code.
* The ``include_docs`` option for CouchDB views is now supported by the new
  ``doc`` property of row instances in view results. Thanks to Paul Davis for
  the patch (issue 33).
* The ``keys`` option for views is now supported (issue 35).


Version 0.4 (Jun 28, 2008)
--------------------------

* Updated for compatibility with CouchDB 0.8.0
* Added command-line scripts for importing/exporting databases.
* The ``Database.update()`` function will now actually perform the ``POST``
  request even when you do not iterate over the results (issue 5).
* The ``_view`` prefix can now be omitted when specifying view names.


Version 0.3 (Feb 6, 2008)
-------------------------

* The ``schema.Document`` class now has a ``view()`` method that can be used to
  execute a CouchDB view and map the result rows back to objects of that
  schema.
* The test suite now uses the new default port of CouchDB, 5984.
* Views now return proxy objects to which you can apply slice syntax for
  "key", "startkey", and "endkey" filtering.
* Add a ``query()`` classmethod to the ``Document`` class.


Version 0.2 (Nov 21, 2007)
--------------------------

* Added __len__ and __iter__ to the ``schema.Schema`` class to iterate
  over and get the number of items in a document or compound field.
* The "version" property of client.Server now returns a plain string
  instead of a tuple of ints.
* The client library now identifies itself with a meaningful
  User-Agent string.
* ``schema.Document.store()`` now returns the document object instance,
  instead of just the document ID.
* The string representation of ``schema.Document`` objects is now more
  comprehensive.
* Only the view parameters "key", "startkey", and "endkey" are JSON
  encoded, anything else is left alone.
* Slashes in document IDs are now URL-quoted until CouchDB supports
  them.
* Allow the content-type to be passed for temp views via
  ``client.Database.query()`` so that view languages other than
  Javascript can be used.
* Added ``client.Database.update()`` method to bulk insert/update
  documents in a database.
* The view-server script wrapper has been renamed to ``couchpy``.
* ``couchpy`` now supports ``--help`` and ``--version`` options.
* Updated for compatibility with CouchDB release 0.7.0.


Version 0.1 (Sep 23, 2007)
--------------------------

* First public release.
