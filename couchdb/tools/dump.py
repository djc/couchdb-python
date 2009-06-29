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
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
import sys

from couchdb import __version__ as VERSION
from couchdb.client import Database
from couchdb.multipart import write_multipart


def dump_db(dburl, username=None, password=None, boundary=None,
            output=sys.stdout):
    db = Database(dburl)
    if username is not None and password is not None:
        db.resource.http.add_credentials(username, password)

    envelope = write_multipart(output)
    #envelope = MIMEMultipart('mixed', boundary)

    for docid in db:
        doc = db.get(docid, attachments=True)
        print>>sys.stderr, 'Dumping document %r' % doc.id
        attachments = doc.pop('_attachments', {})
        jsondoc = json.dumps(doc, sort_keys=True, indent=2)

        if attachments:
            inner = envelope.start({
                'Content-ID': doc.id,
                'ETag': '"%s"' % doc.rev
            })
            part = inner.add('application/json', jsondoc)

            for name, info in attachments.items():
                content_type = info.get('content_type')
                if content_type is None: # CouchDB < 0.8
                    content_type = info.get('content-type')
                subpart = inner.add(content_type, b64decode(info['data']), {
                    'Content-ID': name
                })
            inner.end()

        else:
            part = envelope.add('application/json', jsondoc, {
                'Content-ID': doc.id,
                'ETag': '"%s"' % doc.rev
            }, )

    envelope.end()


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

    dump_db(args[0], username=options.username, password=options.password)


if __name__ == '__main__':
    main()
