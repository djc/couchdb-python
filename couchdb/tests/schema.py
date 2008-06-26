# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import unittest

from couchdb import schema


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
    suite.addTest(unittest.makeSuite(ListFieldTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
