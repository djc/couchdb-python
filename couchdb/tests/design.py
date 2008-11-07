# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
import os
import unittest

from couchdb import design


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(design))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
