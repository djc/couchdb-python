#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Maximillian Dornseif <md@hudora.de>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""
This script replicates databases from one CouchDB server to an other.

This is mainly for backup purposes or "priming" a new server before
setting up trigger based replication. But you can also use the
'--continuous' option to set up automatic replication on newer
CouchDB versions.

Use 'python replicate.py --help' to get more detailed usage instructions.
"""

import couchdb.client
import optparse
import sys
import time

def main():

    usage = '%prog [options]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--database',
        action='append',
        dest='dbnames',
        help='Database to replicate. Can be given more than once. [all databases]')
    parser.add_option('--continuous',
        action='store_true',
        dest='continuous',
        help='trigger continuous replication in cochdb')
    parser.add_option('--compact',
        action='store_true',
        dest='compact',
        help='compact target database after replication')

    options, args = parser.parse_args()
    if len(args) != 2:
        raise parser.error('need source and target arguments')

    src, tgt = args
    if not src.endswith('/'):
        src += '/'
    if not tgt.endswith('/'):
        tgt += '/'

    source_server = couchdb.client.Server(src)
    target_server = couchdb.client.Server(tgt)

    if not options.dbnames:
        dbnames = sorted(i for i in source_server)
    else:
        dbnames = options.dbnames

    targetdbs = sorted(i for i in target_server)
    for dbname in sorted(dbnames, reverse=True):

        start = time.time()
        print dbname,
        sys.stdout.flush()
        if dbname not in targetdbs:
            target_server.create(dbname)
            print "created",
            sys.stdout.flush()

        body = {}
        if options.continuous:
            body['continuous'] = True

        body.update({'source': '%s%s' % (src, dbname), 'target': dbname})
        target_server.resource.post('_replicate', body)
        print '%.1fs' % (time.time() - start)

    if not options.compact:
        return

    sys.stdout.flush()
    for dbname in dbnames:
        target_server[dbname].compact()

if __name__ == '__main__':
    main()
