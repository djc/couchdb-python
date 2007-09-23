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
`Document`, and add any number of `Field` attributes:

>>> class Person(Document):
...     name = TextField()
...     age = IntegerField()
...     added = DateTimeField(default=datetime.now)
>>> person = Person(name='John Doe', age=42)
>>> doc_id = person.store(db)
>>> person.age
42

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

from calendar import timegm
from datetime import date, datetime, time
from decimal import Decimal
from time import strptime

__all__ = ['Schema', 'Document', 'Field', 'TextField', 'FloatField',
           'IntegerField', 'LongField', 'BooleanField', 'DecimalField',
           'DateField', 'DateTimeField', 'TimeField', 'DictField', 'ListField']
__docformat__ = 'restructuredtext en'


class Field(object):
    """Basic unit for mapping a piece of data between Python and JSON.
    
    Instances of this class can be added to subclasses of `Document` to describe
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


class Schema(object):
    __metaclass__ = SchemaMeta

    def __init__(self, **values):
        self._data = {}
        for attrname, field in self._fields.items():
            if attrname in values:
                setattr(self, attrname, values.pop(attrname))
            else:
                setattr(self, attrname, getattr(self, attrname))

    def __delitem__(self, name):
        del self._data[name]

    def __getitem__(self, name):
        return self._data[name]

    def __setitem__(self, name, value):
        self._data[name] = value

    def unwrap(self):
        return self._data

    def build(cls, **d):
        fields = {}
        for attrname, attrval in d.items():
            if not attrval.name:
                attrval.name = attrname
            fields[attrname] = attrval
        d['_fields'] = fields
        return type('AnonymousDocument', (cls,), d)
    build = classmethod(build)

    def wrap(cls, data):
        instance = cls()
        instance._data = data
        return instance
    wrap = classmethod(wrap)

    def _to_python(self, value):
        return self.wrap(value)

    def _to_json(self, value):
        return self.unwrap()


class Document(Schema):

    def __repr__(self):
        return repr(self._data)

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


class TextField(Field):
    """Schema field for string values."""
    _to_python = unicode


class FloatField(Field):
    """Schema field for float values."""
    _to_python = float


class IntegerField(Field):
    """Schema field for integer values."""
    _to_python = int


class LongField(Field):
    """Schema field for long integer values."""
    _to_python = long


class BooleanField(Field):
    """Schema field for boolean values."""
    _to_python = bool


class DecimalField(Field):

    def _to_python(self, value):
        return Decimal(value)

    def _to_json(self, value):
        return unicode(value)


class DateField(Field):
    """Schema field for storing dates.
    
    >>> field = DateField()
    >>> field._to_python('2007-04-01')
    datetime.date(2007, 4, 1)
    >>> field._to_json(date(2007, 4, 1))
    '2007-04-01'
    >>> field._to_json(datetime(2007, 4, 1, 15, 30))
    '2007-04-01'
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = date(*strptime(value, '%Y-%m-%d')[:3])
            except ValueError, e:
                raise ValueError('Invalid ISO date %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(Field):
    """Schema field for storing date/time values.
    
    >>> field = DateTimeField()
    >>> field._to_python('2007-04-01T15:30:00')
    datetime.datetime(2007, 4, 1, 15, 30)
    >>> field._to_json(datetime(2007, 4, 1, 15, 30))
    '2007-04-01T15:30:00'
    >>> field._to_json(date(2007, 4, 1))
    '2007-04-01T00:00:00'
    """

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
        if not isinstance(value, datetime):
            value = datetime.combine(value, time(0))
        return value.isoformat()


class TimeField(Field):
    """Schema field for storing times.
    
    >>> field = TimeField()
    >>> field._to_python('15:30:00')
    datetime.time(15, 30)
    >>> field._to_json(time(15, 30))
    '15:30:00'
    >>> field._to_json(datetime(2007, 4, 1, 15, 30))
    '15:30:00'
    """

    def _to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = time(*strptime(value, '%H:%M:%S')[3:6])
            except ValueError, e:
                raise ValueError('Invalid ISO time %r' % value)
        return value

    def _to_json(self, value):
        if isinstance(value, datetime):
            value = value.time()
        return value.isoformat()


class DictField(Field):
    """Field type for nested dictionaries.
    
    >>> from couchdb import Server
    >>> server = Server('http://localhost:8888/')
    >>> db = server.create('python-tests')

    >>> class Post(Document):
    ...     title = TextField()
    ...     content = TextField()
    ...     author = DictField(Schema.build(
    ...         name = TextField(),
    ...         email = TextField()
    ...     ))

    >>> post = Post(title='Foo bar', author=dict(name='John Doe',
    ...                                          email='john@doe.com'))
    >>> doc_id = post.store(db)
    >>> post = Post.load(db, doc_id)
    >>> post.author.name
    u'John Doe'
    >>> post.author.email
    u'john@doe.com'

    >>> del server['python-tests']
    """
    def __init__(self, schema, name=None, default=None):
        Field.__init__(self, name=name, default=default or {})
        self.schema = schema

    def _to_python(self, value):
        return self.schema.wrap(value)

    def _to_json(self, value):
        if isinstance(value, Schema):
            return value.unwrap()
        return dict(value)


class ListField(Field):
    """Field type for sequences of other fields.

    >>> from couchdb import Server
    >>> server = Server('http://localhost:8888/')
    >>> db = server.create('python-tests')

    >>> class Post(Document):
    ...     title = TextField()
    ...     content = TextField()
    ...     pubdate = DateTimeField(default=datetime.now)
    ...     comments = ListField(DictField(Schema.build(
    ...         author = TextField(),
    ...         content = TextField()
    ...     )))

    >>> post = Post(title='Foo bar')
    >>> post.comments.append(author='myself', content='Bla bla')
    >>> len(post.comments)
    1
    >>> doc_id = post.store(db)
    >>> post = Post.load(db, doc_id)
    >>> comment = post.comments[0]
    >>> comment['author']
    u'myself'
    >>> comment['content']
    u'Bla bla'

    >>> del server['python-tests']
    """

    def __init__(self, field, name=None, default=None):
        Field.__init__(self, name=name, default=default or [])
        if type(field) is type and issubclass(field, Field):
            field = field()
        self.field = field

    def _to_python(self, value):
        return self.Proxy(value, self.field)

    def _to_json(self, value):
        return list(value)


    class Proxy(list):

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
            return self.field._to_python(self.list[index])

        def __setitem__(self, index, value):
            self.list[index] = self.field._to_json(item)

        def __iter__(self):
            for index in range(len(self)):
                yield self[index]

        def __len__(self):
            return len(self.list)

        def __nonzero__(self):
            return bool(self.list)

        def append(self, *args, **kwargs):
            if args:
                assert len(args) == 1
                value = args[0]
            else:
                value = kwargs
            value = self.field._to_json(value)
            self.list.append(value)

        def extend(self, list):
            for item in list:
                self.append(item)
