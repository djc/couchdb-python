#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from base64 import b64decode
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from optparse import OptionParser
import simplejson as json
import sys

from couchdb import __version__ as VERSION
from couchdb.client import Database

def dump_db(dburl, username=None, password=None, boundary=None):
    envelope = MIMEMultipart('mixed', boundary)
    db = Database(dburl)
    if username is not None and password is not None:
        db.resource.http.add_credentials(username, password)
    for docid in db:
        doc = db.get(docid, attachments=True)
        print>>sys.stderr, 'Dumping document %r' % doc.id
        attachments = doc.pop('_attachments', {})

        part = MIMEBase('application', 'json')
        part.set_payload(json.dumps(doc, sort_keys=True, indent=2))

        if attachments:
            inner = MIMEMultipart('mixed')
            inner.attach(part)
            for name, info in attachments.items():
                content_type = info.get('content_type')
                if content_type is None: # CouchDB < 0.8
                    content_type = info.get('content-type')
                maintype, subtype = content_type.split('/', 1)
                subpart = MIMEBase(maintype, subtype)
                subpart['Content-ID'] = name
                subpart.set_payload(b64decode(info['data']))
                inner.attach(subpart)
            part = inner

        part['Content-ID'] = doc.id
        part['ETag'] = doc.rev

        envelope.attach(part)
    return envelope.as_string()

def main():
    parser = OptionParser(usage='%prog [options] dburl', version=VERSION)
    parser.add_option('-u', '--username', action='store', dest='username',
                      help='the username to use for authentication')
    parser.add_option('-p', '--password', action='store', dest='password',
                      help='the password to use for authentication')
    parser.set_defaults()
    options, args = parser.parse_args()

    if len(args) != 1:
        return parser.error('incorrect number of arguments')

    print dump_db(args[0], username=options.username,
                  password=options.password)

if __name__ == '__main__':
    main()
