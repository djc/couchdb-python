# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Daniel Holth
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import unittest
import os.path

from couchdb import loader
from couchdb.tests import testutil

expected = {
 '_id': u'_design/loader',
 'filters': {'filter': u'function(doc, req) { return true; }'},
 'language': u'javascript',
 'views': {'a': {'map': u'function(doc) {\n  emit(doc.property_to_index);\n}'}}}

class LoaderTestCase(unittest.TestCase):

    def test_loader(self):
        directory = os.path.join(os.path.dirname(__file__), '_loader')
        doc = loader.load_design_doc(directory, strip_files=True)
        self.assertEqual(doc, expected)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LoaderTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
