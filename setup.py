#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

setup(
    name = 'CouchDB',
    version = '0.1',
    description = 'Python library for working with CouchDB',
    long_description = \
"""This is a Python library for CouchDB. It provides a convenient high level
interface for CouchDB databases.""",
    author = 'Christopher Lenz',
    author_email = 'cmlenz@gmx.de',
    license = 'BSD',
    url = 'http://code.google.com/p/couchprojects/wiki/CouchDbPython',
    zip_safe = True,

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database :: Front-Ends',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages = ['couchdb'],
    test_suite = 'couchdb.tests.suite',

    setup_requires = ['httplib2', 'simplejson'],

    entry_points = {
        'console_scripts': [
            'couchdb-view-python = couchdb.view:run'
        ],
    }
)
