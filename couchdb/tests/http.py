# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import unittest

from couchdb import http


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(http))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
