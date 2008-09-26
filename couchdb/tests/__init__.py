# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import unittest

from couchdb.tests import client, couch_tests, multipart, schema, view

def suite():
    suite = unittest.TestSuite()
    suite.addTest(client.suite())
    suite.addTest(couch_tests.suite())
    suite.addTest(multipart.suite())
    suite.addTest(schema.suite())
    suite.addTest(view.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
