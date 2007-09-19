#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import os
import unittest
from couchdb import ResourceConflict, ResourceNotFound, Server


class CouchTests(unittest.TestCase):

    def setUp(self):
        uri = os.environ.get('COUCHDB_URI', 'http://localhost:8888/')
        self.server = Server(uri)
        if 'python-tests' in self.server:
            del self.server['python-tests']
        self.db = self.server.create('python-tests')

    def tearDown(self):
        if 'python-tests' in self.server:
            del self.server['python-tests']

    def _create_test_docs(self, num):
        for i in range(num):
            self.db[str(i)] = {'a': i + 1, 'b': (i + 1) ** 2}

    def test_db_info(self):
        self.assertEqual(0, len(self.db))

    def test_create_doc(self):
        data = {'a': 1, 'b': 1}
        self.db['0'] = data
        self.assertEqual('0', data['_id'])
        assert '_rev' in data
        doc = self.db['0']
        self.assertEqual('0', doc.id)
        self.assertEqual(data['_rev'], doc.rev)
        self.assertEqual(1, len(self.db))

    def test_iter_docs(self):
        self._create_test_docs(4)
        self.assertEqual(4, len(self.db))
        for doc_id in self.db:
            assert int(doc_id) in range(4)

    def test_all_docs(self):
        self._create_test_docs(4)
        self.assertEqual(4, len(self.db))
        for doc_id in self.db:
            assert int(doc_id) in range(4)

    def test_delete_doc(self):
        self._create_test_docs(1)
        del self.db['0']
        self.assertRaises(ResourceNotFound, self.db.__getitem__, '0')

    def test_simple_query(self):
        self._create_test_docs(4)
        query = """function(doc) {
            if (doc.a==4)
                return doc.b
        }"""
        result = list(self.db.query(query))
        self.assertEqual(1, len(result))
        self.assertEqual('3', result[0].id)
        self.assertEqual(16, result[0]['value'])

        # modify a document, and redo the query
        doc = self.db['0']
        doc['a'] = 4
        self.db['0'] = doc
        result = list(self.db.query(query))
        self.assertEqual(2, len(result))

        # add more documents, and redo the query again
        self.db.create({'a': 3, 'b': 9})
        self.db.create({'a': 4, 'b': 16})
        result = list(self.db.query(query))
        self.assertEqual(3, len(result))
        self.assertEqual(6, len(self.db))

        # delete a document, and redo the query once more
        del self.db['0']
        result = list(self.db.query(query))
        self.assertEqual(2, len(result))
        self.assertEqual(5, len(self.db))

    def test_conflict_detection(self):
        doc1 = {'a': 1, 'b': 1}
        self.db['foo'] = doc1
        doc2 = self.db['foo']
        self.assertEqual(doc1['_id'], doc2.id)
        self.assertEqual(doc1['_rev'], doc2.rev)

        # make conflicting modifications
        doc1['a'] = 2
        doc2['a'] = 3
        self.db['foo'] = doc1
        self.assertRaises(ResourceConflict, self.db.__setitem__, 'foo', doc2)

        # try submitting without the revision info
        data = {'_id': 'foo', 'a': 3, 'b': 1}
        self.assertRaises(ResourceConflict, self.db.__setitem__, 'foo', data)

        del self.db['foo']
        self.db['foo'] = data

    def test_lots_of_docs(self):
        num = 500 # Crank up manually to really test
        for i in range(num): 
            self.db[str(i)] = {'integer': i, 'string': str(i)}
        self.assertEqual(num, len(self.db))

        query = """function(doc) {
            return {key: doc.integer};
        }"""
        results = list(self.db.query(query))
        self.assertEqual(num, len(results))
        for idx, row in enumerate(results):
            self.assertEqual(idx, row['key'])

        results = list(self.db.query(query, reverse=True))
        self.assertEqual(num, len(results))
        for idx, row in enumerate(results):
            self.assertEqual(num - idx - 1, row['key'])

    def test_multiple_rows(self):
        self.db['NC'] = {'cities': ["Charlotte", "Raleigh"]}
        self.db['MA'] = {'cities': ["Boston", "Lowell", "Worcester",
                                    "Cambridge", "Springfield"]}
        self.db['FL'] = {'cities': ["Miami", "Tampa", "Orlando",
                                    "Springfield"]}

        query = """function(doc){
            var rows = []
            for (var i = 0; i < doc.cities.length; i++) {
                rows[i] = {key: doc.cities[i] + ", " + doc._id};
            }
            // if a function returns a object with a single "multi" member
            // then each element in the member will be output as its own row
            // in the results
            return {multi: rows}
        }"""
        results = list(self.db.query(query))
        self.assertEqual(11, len(results))
        self.assertEqual("Boston, MA", results[0]['key']);
        self.assertEqual("Cambridge, MA", results[1]['key']);
        self.assertEqual("Charlotte, NC", results[2]['key']);
        self.assertEqual("Lowell, MA", results[3]['key']);
        self.assertEqual("Miami, FL", results[4]['key']);
        self.assertEqual("Orlando, FL", results[5]['key']);
        self.assertEqual("Raleigh, NC", results[6]['key']);
        self.assertEqual("Springfield, FL", results[7]['key']);
        self.assertEqual("Springfield, MA", results[8]['key']);
        self.assertEqual("Tampa, FL", results[9]['key']);
        self.assertEqual("Worcester, MA", results[10]['key']);

        # Add a city and rerun the query
        doc = self.db['NC']
        doc['cities'].append("Wilmington")
        self.db['NC'] = doc
        results = list(self.db.query(query))
        self.assertEqual(12, len(results))
        self.assertEqual("Wilmington, NC", results[10]['key'])

        # Remove a document and redo the query again
        del self.db['MA']
        results = list(self.db.query(query))
        self.assertEqual(7, len(results))
        self.assertEqual("Charlotte, NC", results[0]['key']);
        self.assertEqual("Miami, FL", results[1]['key']);
        self.assertEqual("Orlando, FL", results[2]['key']);
        self.assertEqual("Raleigh, NC", results[3]['key']);
        self.assertEqual("Springfield, FL", results[4]['key']);
        self.assertEqual("Tampa, FL", results[5]['key']);
        self.assertEqual("Wilmington, NC", results[6]['key'])

    def test_large_docs(self):
        size = 100
        longtext = '0123456789\n' * size
        self.db.create({'longtext': longtext})
        self.db.create({'longtext': longtext})
        self.db.create({'longtext': longtext})
        self.db.create({'longtext': longtext})

        query = """function(doc) {
            return doc.longtext;
        }"""
        results = list(self.db.query(query))
        self.assertEqual(4, len(results))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CouchTests, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
