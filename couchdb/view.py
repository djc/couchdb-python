#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Implementation of a view server for functions written in Python."""

import simplejson as json
import sys
import traceback
from types import FunctionType

def run(input=sys.stdin, output=sys.stdout):
    r"""CouchDB view function handler implementation for Python.
    
    >>> from StringIO import StringIO
    
    >>> output = StringIO()
    >>> run(input=StringIO('["reset"]\n'), output=output)
    >>> print output.getvalue()
    true
    <BLANKLINE>
    
    >>> output = StringIO()
    >>> run(input=StringIO('["add_fun", "def fun(doc): yield None, doc"]\n'),
    ...     output=output)
    >>> print output.getvalue()
    true
    <BLANKLINE>
    
    >>> output = StringIO()
    >>> run(input=StringIO('["add_fun", "def fun(doc): yield None, doc"]\n'
    ...                    '["map_doc", {"foo": "bar"}]\n'),
    ...     output=output)
    >>> print output.getvalue()
    true
    [[[null, {"foo": "bar"}]]]
    <BLANKLINE>
    
    :param input: the readable file-like object to read input from
    :param output: the writable file-like object to write output to
    """
    functions = []

    def reset():
        del functions[:]
        return True

    def add_fun(string):
        string = '\xef\xbb\xbf' + string.encode('utf-8')
        globals_ = {}
        try:
            exec string in {}, globals_
        except Exception, e:
            return {'error': {'id': 'map_compilation_error', 'reason': e.args[0]}}
        err = {'error': {
            'id': 'map_compilation_error',
            'reason': 'string must eval to a function (ex: "def(doc): return 1")'
        }}
        if len(globals_) != 1:
            return err
        function = globals_.values()[0]
        if type(function) is not FunctionType:
            return err
        functions.append(function)
        return True

    def map_doc(doc):
        results = []
        for function in functions:
            try:
                results.append([[key, value] for key, value in function(doc)])
            except Exception, e:
                results.append([])
                output.write(json.dumps({'log': e.args[0]}))
        return results

    handlers = {'reset': reset, 'add_fun': add_fun, 'map_doc': map_doc}

    try:
        while True:
            line = input.readline()
            if not line:
                break
            try:
                cmd = json.loads(line)
            except ValueError, e:
                sys.stderr.write('error: %s\n' % e)
                exit(1)
            else:
                retval = handlers[cmd[0]](*cmd[1:])
                output.write(json.dumps(retval))
                output.write('\n')
                output.flush()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run()
