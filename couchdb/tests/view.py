# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
from StringIO import StringIO
import unittest

from couchdb import view


class ViewServerTestCase(unittest.TestCase):

    def test_reset(self):
        input = StringIO('["reset"]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEquals(output.getvalue(), 'true\n')

    def test_add_fun(self):
        input = StringIO('["add_fun", "def fun(doc): yield None, doc"]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEquals(output.getvalue(), 'true\n')

    def test_map_doc(self):
        input = StringIO('["add_fun", "def fun(doc): yield None, doc"]\n'
                         '["map_doc", {"foo": "bar"}]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(),
                         'true\n'
                         '[[[null, {"foo": "bar"}]]]\n')

    def test_map_doc_with_logging(self):
        fun = 'def fun(doc): log(\'running\'); yield None, doc'
        input = StringIO('["add_fun", "%s"]\n'
                         '["map_doc", {"foo": "bar"}]\n' % fun)
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(),
                         'true\n'
                         '{"log": "running"}\n'
                         '[[[null, {"foo": "bar"}]]]\n')

    def test_map_doc_with_logging_json(self):
        fun = 'def fun(doc): log([1, 2, 3]); yield None, doc'
        input = StringIO('["add_fun", "%s"]\n'
                         '["map_doc", {"foo": "bar"}]\n' % fun)
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(),
                         'true\n'
                         '{"log": "[1, 2, 3]"}\n'
                         '[[[null, {"foo": "bar"}]]]\n')

    def test_reduce(self):
        input = StringIO('["reduce", '
                          '["def fun(keys, values): return sum(values)"], '
                          '[[null, 1], [null, 2], [null, 3]]]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(), '[true, [6]]\n')

    def test_reduce_with_logging(self):
        input = StringIO('["reduce", '
                          '["def fun(keys, values): log(\'Summing %r\' % (values,)); return sum(values)"], '
                          '[[null, 1], [null, 2], [null, 3]]]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(),
                         '{"log": "Summing (1, 2, 3)"}\n'
                         '[true, [6]]\n')

    def test_rereduce(self):
        input = StringIO('["rereduce", '
                          '["def fun(keys, values, rereduce): return sum(values)"], '
                          '[1, 2, 3]]\n')
        output = StringIO()
        view.run(input=input, output=output)
        self.assertEqual(output.getvalue(), '[true, [6]]\n')



def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(view))
    suite.addTest(unittest.makeSuite(ViewServerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
