# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import os
import unittest

from couchdb import client, schema


class DocumentTestCase(unittest.TestCase):

    def setUp(self):
        uri = os.environ.get('COUCHDB_URI', 'http://localhost:5984/')
        self.server = client.Server(uri)
        if 'python-tests' in self.server:
            del self.server['python-tests']
        self.db = self.server.create('python-tests')

    def tearDown(self):
        if 'python-tests' in self.server:
            del self.server['python-tests']

    def test_automatic_id(self):
        class Post(schema.Document):
            title = schema.TextField()
        post = Post(title='Foo bar')
        assert post.id is None
        post.store(self.db)
        assert post.id is not None
        self.assertEqual('Foo bar', self.db[post.id]['title'])

    def test_explicit_id_via_init(self):
        class Post(schema.Document):
            title = schema.TextField()
        post = Post(id='foo_bar', title='Foo bar')
        self.assertEqual('foo_bar', post.id)
        post.store(self.db)
        self.assertEqual('Foo bar', self.db['foo_bar']['title'])

    def test_explicit_id_via_setter(self):
        class Post(schema.Document):
            title = schema.TextField()
        post = Post(title='Foo bar')
        post.id = 'foo_bar'
        self.assertEqual('foo_bar', post.id)
        post.store(self.db)
        self.assertEqual('Foo bar', self.db['foo_bar']['title'])

    def test_change_id_failure(self):
        class Post(schema.Document):
            title = schema.TextField()
        post = Post(title='Foo bar')
        post.store(self.db)
        post = Post.load(self.db, post.id)
        try:
            post.id = 'foo_bar'
            self.fail('Excepted AttributeError')
        except AttributeError, e:
            self.assertEqual('id can only be set on new documents', e.args[0])


class ListFieldTestCase(unittest.TestCase):

    def test_to_json(self):
        # See <http://code.google.com/p/couchdb-python/issues/detail?id=14>
        class Post(schema.Document):
            title = schema.TextField()
            comments = schema.ListField(schema.DictField(schema.Schema.build(
                author = schema.TextField(),
                content = schema.TextField(),
            )))
        post = Post(title='Foo bar')
        post.comments.append(author='myself', content='Bla bla')
        post.comments = post.comments
        self.assertEqual([{'content': 'Bla bla', 'author': 'myself'}],
                         post.comments)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(schema))
    suite.addTest(unittest.makeSuite(DocumentTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ListFieldTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
