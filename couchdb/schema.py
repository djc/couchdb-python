# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Mapping from raw JSON data structures to Python objects and vice versa.

>>> from couchdb import Server
>>> server = Server('http://localhost:8888/')
>>> db = server.create('python-tests')
>>> doc_id = db.create(name='John Doe', age=42)

To define a document schema, you declare a Python class inherited from
`Document`, and add any number of `Field` attributes:

>>> class Person(Document):
...     name = TextField()
...     age = IntegerField()
...     added = DateTimeField(default=datetime.now)

You can then load the data from the CouchDB server through your `Document`
subclass, and conveniently access all attributes:

>>> person = Person.load(db, doc_id)
>>> person.id == doc_id
True
>>> old_rev = person.rev
>>> person.name
u'John Doe'
>>> person.age
42
>>> person.added                #doctest: +ELLIPSIS
datetime.datetime(...)

To update a document, simply set the attributes, and then call the ``store()``
method:

>>> person.name = 'John R. Doe'
>>> person.store(db)

If you retrieve the document from the server again, you should be getting the
updated data:

>>> person = Person.load(db, doc_id)
>>> person.name
u'John R. Doe'
>>> person.rev != old_rev
True

>>> del server['python-tests']
"""

# TODO: nested dicts and lists

from calendar import timegm
from datetime import datetime
from decimal import Decimal
from time import strptime

from couchdb.client import Row

__all__ = ['Document', 'Field', 'TextField', 'FloatField', 'IntegerField',
           'LongField', 'BoolField', 'DecimalField', 'DateField',
           'DateTimeField', 'TimeField']
__docformat__ = 'restructuredtext en'


class Field(object):
    """Basic unit for mapping a piece of data between Python and JSON.
    
    Instances of this class can be added to subclasses of `Document` to describe
    the schema of a document.
    """

    def __init__(self, default=None):
        self.name = None
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = instance._data.get(self.name)
        if value is None and self.default is not None:
            default = self.default
            if callable(default):
                return default()
            value = default
        if value is not None:
            value = self._to_python(value)
        return value

    def __set__(self, instance, value):
        if value is not None:
            value = self._to_json(value)
        instance._data[self.name] = value

    def _to_python(self, value):
        return unicode(value)

    def _to_json(self, value):
        return self._to_python(value)


class DocumentMeta(type):

    def __new__(cls, name, bases, d):
        for attrname, attrval in d.items():
            if isinstance(attrval, Field):
                attrval.name = attrname
        return type.__new__(cls, name, bases, d)


class Document(object):
    __metaclass__ = DocumentMeta

    def __init__(self, data):
        self._data = data

    def __repr__(self):
        return '<%s %r@%r>' % (type(self).__name__, self.id, self.rev)

    def __delitem__(self, name):
        del self._data[name]

    def __getitem__(self, name):
        return self._data[name]

    def __setitem__(self, name, value):
        self._data[name] = value

    def id(self):
        if hasattr(self._data, 'id'):
            return self._data.id
        return self._data.get('_id')
    id = property(id)

    def rev(self):
        if hasattr(self._data, 'rev'):
            return self._data.rev
        return self._data.get('_rev')
    rev = property(rev)

    def load(cls, db, id):
        return cls(db.get(id))
    load = classmethod(load)

    def store(self, db):
        if getattr(self._data, 'id', None) is None:
            docid = db.create(**self._data)
            self.clear()
            self.__init__(db[docid])
        else:
            db[self._data.id] = self._data


class TextField(Field):
    _to_python = unicode


class FloatField(Field):
    _to_python = float


class IntegerField(Field):
    _to_python = int


class LongField(Field):
    _to_python = long


class BoolField(Field):
    _to_python = bool


class DecimalField(Field):

    def _to_python(self, value):
        return Decimal(value)

    def _to_json(self, value):
        return unicode(value)


class DateField(Field):

    def _to_python(self, value):
        try:
            timestamp = timegm(strptime(value, '%Y-%m-%d'))
            return date.fromtimestamp(timestamp)
        except ValueError, e:
            raise ValueError('Invalid ISO date %r' % value)

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(Field):

    def _to_python(self, value):
        try:
            value = value.split('.', 1)[0] # strip out microseconds
            timestamp = timegm(strptime(value, '%Y-%m-%dT%H:%M:%S'))
            return datetime.utcfromtimestamp(timestamp)
        except ValueError, e:
            raise ValueError('Invalid ISO date/time %r' % value)

    def _to_json(self, value):
        return value.isoformat()


class TimeField(Field):

    def _to_python(self, value):
        try:
            value = value.split('.', 1)[0] # strip out microseconds
            timestamp = timegm(strptime(value, '%H:%M:%S'))
            return datetime.utcfromtimestamp(timestamp).time()
        except ValueError, e:
            raise ValueError('Invalid ISO time %r' % value)

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.time()
        return value.isoformat()
