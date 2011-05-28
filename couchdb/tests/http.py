# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import socket
import time
import unittest
from StringIO import StringIO

from couchdb import http
from couchdb.tests import testutil


class SessionTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_timeout(self):
        dbname, db = self.temp_db()
        timeout = 1
        session = http.Session(timeout=timeout)
        start = time.time()
        status, headers, body = session.request('GET', db.resource.url + '/_changes?feed=longpoll&since=1000&timeout=%s' % (timeout*2*1000,))
        self.assertRaises(socket.timeout, body.read)
        self.failUnless(time.time() - start < timeout * 1.3)


class ResponseBodyTestCase(unittest.TestCase):
    def test_close(self):
        class TestStream(StringIO):
            def isclosed(self):
                return len(self.buf) == self.tell()

        class Counter(object):
            def __init__(self):
                self.value = 0

            def __call__(self):
                self.value += 1

        counter = Counter()

        response = http.ResponseBody(TestStream('foobar'), counter)

        response.read(10) # read more than stream has. close() is called
        response.read() # steam ended. another close() call

        self.assertEqual(counter.value, 1)

    def test_double_iteration_over_same_response_body(self):
        class TestHttpResp(object):
            msg = {'transfer-encoding': 'chunked'}
            def __init__(self, fp):
                self.fp = fp

            def isclosed(self):
                return len(self.fp.buf) == self.fp.tell()

        data = 'foobarbaz'
        data = '\n'.join([hex(len(data))[2:], data])
        response = http.ResponseBody(TestHttpResp(StringIO(data)),
                                     lambda *a, **k: None)
        self.assertEqual(list(response), ['foobarbaz'])
        self.assertEqual(list(response), [])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(http))
    suite.addTest(unittest.makeSuite(SessionTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ResponseBodyTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
