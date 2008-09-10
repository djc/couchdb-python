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
import StringIO

from couchdb import client


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        uri = os.environ.get('COUCHDB_URI', 'http://localhost:5984/')
        self.server = client.Server(uri)
        if 'python-tests' in self.server:
            del self.server['python-tests']
        self.db = self.server.create('python-tests')

    def tearDown(self):
        if 'python-tests' in self.server:
            del self.server['python-tests']

    def test_doc_id_quoting(self):
        self.db['foo/bar'] = {'foo': 'bar'}
        self.assertEqual('bar', self.db['foo/bar']['foo'])
        del self.db['foo/bar']
        self.assertEqual(None, self.db.get('foo/bar'))

    def test_unicode(self):
        self.db[u'føø'] = {u'bår': u'Iñtërnâtiônàlizætiøn', 'baz': 'ASCII'}
        self.assertEqual(u'Iñtërnâtiônàlizætiøn', self.db[u'føø'][u'bår'])
        self.assertEqual(u'ASCII', self.db[u'føø'][u'baz'])

    def test_doc_revs(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']
        doc['bar'] = 43
        self.db['foo'] = doc
        new_rev = doc['_rev']

        new_doc = self.db.get('foo')
        self.assertEqual(new_rev, new_doc['_rev'])
        new_doc = self.db.get('foo', rev=new_rev)
        self.assertEqual(new_rev, new_doc['_rev'])
        old_doc = self.db.get('foo', rev=old_rev)
        self.assertEqual(old_rev, old_doc['_rev'])

    def test_attachment_crud(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']
        
        self.db.put_attachment(doc, 'foo.txt', 'Foo bar', 'text/plain')
        self.assertNotEquals(old_rev, doc['_rev'])

        doc = self.db['foo']
        attachment = doc['_attachments']['foo.txt']
        self.assertEqual(len('Foo bar'), attachment['length'])
        self.assertEqual('text/plain', attachment['content_type'])

        self.assertEqual('Foo bar', self.db.get_attachment(doc, 'foo.txt'))
        self.assertEqual('Foo bar', self.db.get_attachment('foo', 'foo.txt'))

        old_rev = doc['_rev']
        self.db.delete_attachment(doc, 'foo.txt')
        self.assertNotEquals(old_rev, doc['_rev'])
        self.assertEqual(None, self.db['foo'].get('_attachments'))
        
    def test_attachment_crud_with_files(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']
        f = StringIO.StringIO('Foo bar baz')
        
        self.db.put_attachment(doc, 'foo.txt', f, 'text/plain')
        self.assertNotEquals(old_rev, doc['_rev'])

        doc = self.db['foo']
        attachment = doc['_attachments']['foo.txt']
        self.assertEqual(len('Foo bar baz'), attachment['length'])
        self.assertEqual('text/plain', attachment['content_type'])

        self.assertEqual('Foo bar baz', self.db.get_attachment(doc, 'foo.txt'))
        self.assertEqual('Foo bar baz', self.db.get_attachment('foo', 'foo.txt'))

        old_rev = doc['_rev']
        self.db.delete_attachment(doc, 'foo.txt')
        self.assertNotEquals(old_rev, doc['_rev'])
        self.assertEqual(None, self.db['foo'].get('_attachments'))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DatabaseTestCase, 'test'))
    suite.addTest(doctest.DocTestSuite(client))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
