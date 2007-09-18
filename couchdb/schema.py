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

To define a document schema, you declare a Python class inherited from
`Schema`, and add any number of `Field` attributes:

>>> Person = Schema.with_fields(
...     name = TextField(),
...     age = IntegerField(),
...     added = DateTimeField(default=datetime.now)
... )
>>> person = Person(name='John Doe', age=42)
>>> doc_id = person.store(db)
>>> person.age
42

You can then load the data from the CouchDB server through your `Schema`
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
>>> person.store(db)            #doctest: +ELLIPSIS
u'...'

If you retrieve the document from the server again, you should be getting the
updated data:

>>> person = Person.load(db, doc_id)
>>> person.name
u'John R. Doe'
>>> person.rev != old_rev
True

>>> del server['python-tests']
"""

# NOTE: this module is very much under construction and still subject to major
#       changes or even removal
# TODO: nested dicts and lists

from calendar import timegm
from datetime import datetime
from decimal import Decimal
from time import strptime

from couchdb.client import Row

__all__ = ['Schema', 'Field', 'TextField', 'FloatField', 'IntegerField',
           'LongField', 'BooleanField', 'DecimalField', 'DateField',
           'DateTimeField', 'TimeField']
__docformat__ = 'restructuredtext en'


class Field(object):
    """Basic unit for mapping a piece of data between Python and JSON.
    
    Instances of this class can be added to subclasses of `Schema` to describe
    the schema of a document.
    """

    def __init__(self, name=None, default=None):
        self.name = name
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = instance._data.get(self.name)
        if value is None and self.default is not None:
            default = self.default
            if callable(default):
                default = default()
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


class SchemaMeta(type):

    def __new__(cls, name, bases, d):
        fields = {}
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)
        for attrname, attrval in d.items():
            if isinstance(attrval, Field):
                if not attrval.name:
                    attrval.name = attrname
                fields[attrname] = attrval
        d['_fields'] = fields
        return type.__new__(cls, name, bases, d)


class Schema(Field):
    __metaclass__ = SchemaMeta

    def __init__(self, **values):
        self._data = {}
        for attrname, field in self._fields.items():
            if attrname in values:
                setattr(self, attrname, values.pop(attrname))
            else:
                setattr(self, attrname, getattr(self, attrname))

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
        return cls.wrap(db.get(id))
    load = classmethod(load)

    def store(self, db):
        if getattr(self._data, 'id', None) is None:
            docid = db.create(self._data)
            self._data = db.get(docid)
            return docid
        else:
            db[self._data.id] = self._data
            return self._data.id

    def unwrap(self):
        return self._data

    def with_fields(cls, **d):
        fields = {}
        for attrname, attrval in d.items():
            if not attrval.name:
                attrval.name = attrname
            fields[attrname] = attrval
        d['_fields'] = fields
        return type('AnonymousSchema', (cls,), d)
    with_fields = classmethod(with_fields)

    def wrap(cls, data):
        instance = cls()
        instance._data = data
        return instance
    wrap = classmethod(wrap)

    def _to_python(self, value):
        return self.wrap(value)

    def _to_json(self, value):
        return self.unwrap()


class TextField(Field):
    _to_python = unicode


class FloatField(Field):
    _to_python = float


class IntegerField(Field):
    _to_python = int


class LongField(Field):
    _to_python = long


class BooleanField(Field):
    _to_python = bool


class DecimalField(Field):

    def _to_python(self, value):
        return Decimal(value)

    def _to_json(self, value):
        return unicode(value)


class DateField(Field):

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                timestamp = timegm(strptime(value, '%Y-%m-%d'))
                value = date.fromtimestamp(timestamp)
            except ValueError, e:
                raise ValueError('Invalid ISO date %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(Field):

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                timestamp = timegm(strptime(value, '%Y-%m-%dT%H:%M:%S'))
                value = datetime.utcfromtimestamp(timestamp)
            except ValueError, e:
                raise ValueError('Invalid ISO date/time %r' % value)
        return value

    def _to_json(self, value):
        return value.isoformat()


class TimeField(Field):

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                timestamp = timegm(strptime(value, '%H:%M:%S'))
                value = datetime.utcfromtimestamp(timestamp).time()
            except ValueError, e:
                raise ValueError('Invalid ISO time %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.time()
        return value.isoformat()


class ListProxy(list):

    def __init__(self, list, field):
        self.list = list
        self.field = field

    def __repr__(self):
        return repr(self.list)

    def __str__(self):
        return str(self.list)

    def __unicode__(self):
        return unicode(self.list)

    def __delitem__(self, index):
        del self.list[index]

    def __getitem__(self, index):
        item = self.list[index]
        if isinstance(self.field, Field):
            return self.field._to_python(item)
        else:
            return self.field.wrap(item)

    def __setitem__(self, index, value):
        if isinstance(self.field, Field):
            item = self.field._to_json(item)
        else:
            assert isinstance(value, self.field)
            return value.unwrap()
        self.list[index] = item

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def __len__(self):
        return len(self.list)

    def __nonzero__(self):
        return bool(self.list)

    def append(self, *args, **kwargs):
        if isinstance(self.field, Field):
            assert args and len(args) == 1
            value = self.field._to_json(args[0])
        else:
            value = self.field(**kwargs).unwrap()
        self.list.append(value)

    def extend(self, list):
        for item in list:
            self.append(item)


class ListField(Field):
    """

    >>> from couchdb import Server
    >>> server = Server('http://localhost:8888/')
    >>> db = server.create('python-tests')

    >>> class Post(Schema):
    ...     title = TextField()
    ...     content = TextField()
    ...     pubdate = DateTimeField(default=datetime.now)
    ...     comments = ListField(Schema.with_fields(
    ...         author = TextField(),
    ...         content = TextField()
    ...     ))

    >>> post = Post(title='Foo bar')
    >>> post.comments.append(author='myself', content='Bla bla')
    >>> len(post.comments)
    1
    >>> doc_id = post.store(db)
    >>> post = Post.load(db, doc_id)
    >>> comment = post.comments[0]
    >>> comment.author
    u'myself'
    >>> comment.content
    u'Bla bla'

    >>> del server['python-tests']
    """

    def __init__(self, field, name=None, default=None):
        Field.__init__(self, name=name, default=default or [])
        if type(field) is type and issubclass(field, Field):
            field = field()
        self.field = field

    def _to_python(self, value):
        return ListProxy(value, self.field)

    def _to_json(self, value):
        return list(value)
