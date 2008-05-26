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
import simplejson as json
import sys

from couchdb import __version__ as VERSION
from couchdb.client import Database

def load_db(fileobj, dburl, username=None, password=None):
    envelope = message_from_file(fileobj)
    db = Database(dburl)
    if username is not None and password is not None:
        db.resource.http.add_credentials(username, password)

    for part in envelope.get_payload():
        docid = part['Content-ID']
        if part.is_multipart(): # doc has attachments
            for subpart in part.walk():
                if subpart is part:
                    continue
                if 'Content-ID' not in subpart:
                    doc = json.loads(subpart.get_payload())
                    doc['_attachments'] = {}
                else:
                    data = subpart.get_payload()
                    doc['_attachments'][subpart['Content-ID']] = {
                        'data': b64encode(data),
                        'content-type': subpart['Content-Type'],
                        'length': len(data)
                    }
        else:
            doc = json.loads(part.get_payload())
        del doc['_rev']
        print>>sys.stderr, 'Loading document %r' % docid
        db[docid] = doc

def main():
    parser = OptionParser(usage='%prog [options] dburl', version=VERSION)
    parser.add_option('--input', action='store', dest='input', metavar='FILE',
                      help='the name of the file to read from')
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
            password=options.password)

if __name__ == '__main__':
    main()
