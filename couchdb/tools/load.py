#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from base64 import b64encode
from email import message_from_file
from optparse import OptionParser
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
import sys

from couchdb import __version__ as VERSION
from couchdb.client import Database
from couchdb.multipart import read_multipart


def load_db(fileobj, dburl, username=None, password=None, ignore_errors=False):
    db = Database(dburl)
    if username is not None and password is not None:
        db.resource.http.add_credentials(username, password)

    for headers, is_multipart, payload in read_multipart(fileobj):
        docid = headers['content-id']

        if is_multipart: # doc has attachments
            for headers, _, payload in payload:
                if 'content-id' not in headers:
                    doc = json.loads(payload)
                    doc['_attachments'] = {}
                else:
                    doc['_attachments'][headers['content-id']] = {
                        'data': b64encode(payload),
                        'content_type': headers['content-type'],
                        'length': len(payload)
                    }

        else: # no attachments, just the JSON
            doc = json.loads(payload)

        del doc['_rev']
        print json.dumps(doc, indent=True)
        print>>sys.stderr, 'Loading document %r' % docid
        try:
            db[docid] = doc
        except Exception, e:
            if not ignore_errors:
                raise
            print>>sys.stderr, 'Error: %s' % e


def main():
    parser = OptionParser(usage='%prog [options] dburl', version=VERSION)
    parser.add_option('--input', action='store', dest='input', metavar='FILE',
                      help='the name of the file to read from')
    parser.add_option('--ignore-errors', action='store_true',
                      dest='ignore_errors',
                      help='whether to ignore errors in document creation '
                           'and continue with the remaining documents')
    parser.add_option('-u', '--username', action='store', dest='username',
                      help='the username to use for authentication')
    parser.add_option('-p', '--password', action='store', dest='password',
                      help='the password to use for authentication')
    parser.set_defaults(input='-')
    options, args = parser.parse_args()

    if len(args) != 1:
        return parser.error('incorrect number of arguments')

    if options.input != '-':
        fileobj = open(options.input)
    else:
        fileobj = sys.stdin

    load_db(fileobj, args[0], username=options.username,
            password=options.password, ignore_errors=options.ignore_errors)


if __name__ == '__main__':
    main()
