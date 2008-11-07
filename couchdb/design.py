# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Utility code for managing design documents."""

from copy import deepcopy
from itertools import groupby
from operator import attrgetter


class ViewDefinition(object):
    """Definition of a view stored in a specific design document.
    
    An instance of this class can be used to access the results of the view,
    as well as to keep the view definition in the design document up to date
    with the definition in the application code.
    
    >>> from couchdb import Server
    >>> server = Server('http://localhost:5984/')
    >>> db = server.create('python-tests')
    
    >>> view = ViewDefinition('tests', 'all', '''function(doc) {
    ...     emit(doc._id, null);
    ... }''')
    >>> view.get_doc(db)

    The view is not yet stored in the database, in fact, design doc doesn't
    even exist yet. That can be fixed using the `sync` method:

    >>> view.sync(db)

    >>> design_doc = view.get_doc(db)
    >>> design_doc                                          #doctest: +ELLIPSIS
    <Document u'_design/tests'@u'...' {...}>
    >>> print design_doc['views']['all']['map']
    function(doc) {
        emit(doc._id, null);
    }

    Use the static `sync_many()` method to create or update a collection of
    views in the database in an atomic and efficient manner, even across
    different design documents.

    >>> del server['python-tests']
    """

    def __init__(self, design, name, map_fun, reduce_fun=None,
                 language='javascript', wrapper=None):
        """Initialize the view definition.
        
        :param design: the name of the design document
        :param name: the name of the view
        :param map_fun: the map function code
        :param reduce_fun: the reduce function code (optional)
        :param language: the name of the language used
        :param wrapper: an optional callable that should be used to wrap the
                        result rows
        """
        if design.startswith('_design/'):
            design = design[8:]
        self.design = design
        self.name = name
        self.map_fun = map_fun
        self.reduce_fun = reduce_fun
        self.language = language
        self.wrapper = wrapper

    def __call__(self, db, **options):
        """Execute the view in the given database.
        
        :param db: the `Database` instance
        :param options: optional query string parameters
        :return: the view results
        :rtype: `ViewResults`
        """
        return db.view('/'.join([self.design, self.name]),
                       wrapper=self.wrapper, **options)

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__,
                            '/'.join(['_view', self.design, self.name]))

    def get_doc(self, db):
        """Retrieve and return the design document corresponding to this view
        definition from the given database.
        
        :param db: the `Database` instance
        :return: a `client.Document` instance, or `None` if the design document
                 does not exist in the database
        :rtype: `Document`
        """
        return db.get('_design/%s' % self.design)

    def sync(self, db):
        """Ensure that the view stored in the database matches the view defined
        by this instance.
        
        :param db: the `Database` instance
        """
        type(self).sync_many(db, [self])

    @staticmethod
    def sync_many(db, views, remove_missing=False, callback=None):
        """Ensure that the views stored in the database that correspond to a
        given list of `ViewDefinition` instances match the code defined in
        those instances.
        
        This function might update more than one design document. This is done
        using the CouchDB bulk update feature to ensure atomicity of the
        operation.
        
        :param db: the `Database` instance
        :param views: a sequence of `ViewDefinition` instances
        :param remove_missing: whether views found in a design document that
                               are not found in the list of `ViewDefinition`
                               instances should be removed
        :param callback: a callback function that is invoked when a design
                         document gets updated; the callback gets passed the
                         design document as only parameter
        """
        docs = []

        for design, views in groupby(views, key=attrgetter('design')):
            doc_id = '_design/%s' % design
            doc = db.get(doc_id, {'_id': doc_id})
            orig_doc = deepcopy(doc)
            languages = set()

            missing = list(doc.get('views', {}).keys())
            for view in views:
                funcs = {'map': view.map_fun}
                if view.reduce_fun:
                    funcs['reduce'] = view.reduce_fun
                doc.setdefault('views', {})[view.name] = funcs
                languages.add(view.language)
                if view.name in missing:
                    missing.remove(view.name)

            if remove_missing and missing:
                for name in missing:
                    del doc['views'][name]
            elif missing and 'language' in doc:
                languages.add(doc['language'])

            if len(languages) > 1:
                raise ValueError('Found different language views in one '
                                 'design document (%r)', list(languages))
            doc['language'] = list(languages)[0]

            if doc != orig_doc:
                if callback is not None:
                    callback(doc)
                docs.append(doc)

        db.update(docs)
