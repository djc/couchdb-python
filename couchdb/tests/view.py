# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import unittest

from couchdb import view

def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(view))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
