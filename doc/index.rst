.. -*- mode: rst; encoding: utf-8 -*-
.. couchdb-python documentation master file, created by
   sphinx-quickstart on Thu Apr 29 18:32:43 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
============

``couchdb`` is Python package for working with CouchDB_ from Python code.
It consists of the following main modules:

* ``couchdb.client``: This is the client library for interfacing CouchDB
  servers. If you don't know where to start, this is likely to be what you're
  looking for.

* ``couchdb.mapping``: This module provides advanced mapping between CouchDB
  JSON documents and Python objects.

Additionally, the ``couchdb.view`` module implements a view server for
views written in Python.

There may also be more information on the `project website`_.

.. _couchdb: http://couchdb.org/
.. _project website: http://code.google.com/p/couchdb-python
.. _views written in Python: views

Documentation
=============

.. toctree::
   :maxdepth: 2
   :numbered:

   getting-started.rst
   views.rst
   client.rst
   mapping.rst
   changes.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
