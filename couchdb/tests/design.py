# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import unittest

from couchdb import design
from couchdb.tests import testutil


class DesignTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_options(self):
        options = {'collation': 'raw'}
        view = design.ViewDefinition(
            'foo', 'foo',
            'function(doc) {emit(doc._id, doc._rev)}',
            options=options)
        _, db = self.temp_db()
        view.sync(db)
        design_doc = db.get('_design/foo')
        self.assertTrue(design_doc['views']['foo']['options'] == options)

    def test_retrieve_view_defn(self):
        '''see issue 183'''
        view_def = design.ViewDefinition('foo', 'bar', 'baz')
        result = view_def.sync(self.db)
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result[0][0], True)
        self.assertEqual(result[0][1], '_design/foo')
        doc = self.db[result[0][1]]
        self.assertEqual(result[0][2], doc['_rev'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DesignTestCase))
    suite.addTest(doctest.DocTestSuite(design))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
