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


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(http))
    suite.addTest(unittest.makeSuite(SessionTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
