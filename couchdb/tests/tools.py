# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#


import unittest
from StringIO import StringIO

from couchdb.tools import load
from couchdb.tests import testutil

class ToolLoadTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_handle_credentials(self):
        # Issue 194: couchdb-load attribute error: 'Resource' object has no attribute 'http'
        # http://code.google.com/p/couchdb-python/issues/detail?id=194
        load.load_db(StringIO(''), self.db.resource.url, 'foo', 'bar')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ToolLoadTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

