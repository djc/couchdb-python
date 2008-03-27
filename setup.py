#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from distutils.cmd import Command
import doctest
from glob import glob
import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

class build_doc(Command):
    description = 'Builds the documentation'
    user_options = [
        ('force', None,
         "force regeneration even if no reStructuredText files have changed"),
        ('without-apidocs', None,
         "whether to skip the generation of API documentaton"),
    ]
    boolean_options = ['force', 'without-apidocs']

    def initialize_options(self):
        self.force = False
        self.without_apidocs = False

    def finalize_options(self):
        pass

    def run(self):
        from docutils.core import publish_cmdline
        from docutils.nodes import raw
        from docutils.parsers import rst

        docutils_conf = os.path.join('doc', 'conf', 'docutils.ini')
        epydoc_conf = os.path.join('doc', 'conf', 'epydoc.ini')

        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import HtmlFormatter

            def code_block(name, arguments, options, content, lineno,
                           content_offset, block_text, state, state_machine):
                lexer = get_lexer_by_name(arguments[0])
                html = highlight('\n'.join(content), lexer, HtmlFormatter())
                return [raw('', html, format='html')]
            code_block.arguments = (1, 0, 0)
            code_block.options = {'language' : rst.directives.unchanged}
            code_block.content = 1
            rst.directives.register_directive('code-block', code_block)
        except ImportError:
            print 'Pygments not installed, syntax highlighting disabled'

        for source in glob('doc/*.txt'):
            dest = os.path.splitext(source)[0] + '.html'
            if self.force or not os.path.exists(dest) or \
                    os.path.getmtime(dest) < os.path.getmtime(source):
                print 'building documentation file %s' % dest
                publish_cmdline(writer_name='html',
                                argv=['--config=%s' % docutils_conf, source,
                                      dest])

        if not self.without_apidocs:
            try:
                from epydoc import cli
                old_argv = sys.argv[1:]
                sys.argv[1:] = [
                    '--config=%s' % epydoc_conf,
                    '--no-private', # epydoc bug, not read from config
                    '--simple-term',
                    '--verbose'
                ]
                cli.cli()
                sys.argv[1:] = old_argv

            except ImportError:
                print 'epydoc not installed, skipping API documentation.'


class test_doc(Command):
    description = 'Tests the code examples in the documentation'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for filename in glob('doc/*.txt'):
            print 'testing documentation file %s' % filename
            doctest.testfile(filename, False, optionflags=doctest.ELLIPSIS)


setup(
    name = 'CouchDB',
    version = '0.3',
    description = 'Python library for working with CouchDB',
    long_description = \
"""This is a Python library for CouchDB. It provides a convenient high level
interface for the CouchDB server.""",
    author = 'Christopher Lenz',
    author_email = 'cmlenz@gmx.de',
    license = 'BSD',
    url = 'http://code.google.com/p/couchdb-python/',
    zip_safe = True,

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages = ['couchdb'],
    test_suite = 'couchdb.tests.suite',

    install_requires = ['httplib2', 'simplejson'],

    entry_points = {
        'console_scripts': [
            'couchpy = couchdb.view:main',
            'couchdb-dump = couchdb.tools.dump:main',
            'couchdb-load = couchdb.tools.load:main'
        ],
    },

    cmdclass = {'build_doc': build_doc, 'test_doc': test_doc}
)
