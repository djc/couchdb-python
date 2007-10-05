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

from couchdb import client


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        uri = os.environ.get('COUCHDB_URI', 'http://localhost:8888/')
        self.server = client.Server(uri)
        if 'python-tests' in self.server:
            del self.server['python-tests']
        self.db = self.server.create('python-tests')

    def tearDown(self):
        if 'python-tests' in self.server:
            del self.server['python-tests']

    def testDocIdQuoting(self):
        self.db['foo/bar'] = {'foo': 'bar'}
        self.assertEqual('bar', self.db['foo/bar']['foo'])
        del self.db['foo/bar']
        self.assertEqual(None, self.db.get('foo/bar'))



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DatabaseTestCase, 'test'))
    #suite.addTest(doctest.DocTestSuite(client))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
