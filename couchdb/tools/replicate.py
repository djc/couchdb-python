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

def compact(server, dbnames):
    for dbname in dbnames:
        sys.stdout.flush()
        db = server[dbname]
        db.resource.post('_compact')

def main():

    usage = '%prog [options]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--source-server',
        action='store',
        dest='source_url',
        help='the url of the server to replicate from')
    parser.add_option('--target-server',
        action='store',
        dest='target_url',
        default="http://127.0.0.1:5984",
        help='the url of the server to replicate to [%default]')
    parser.add_option('--database',
        action='append',
        dest='dbnames',
        help='Database to replicate. Can be given more than once. [all databases]')
    parser.add_option('--no-target-compaction',
        action='store_false',
        dest='compact_target',
        help='do not start compaction of target after replications')
    parser.add_option('--continuous',
        action='store_true',
        dest='continuous',
        help='trigger continuous replication in cochdb')

    options, args = parser.parse_args()
    if not options.target_url or (not options.source_url):
        parser.error("Need at least --source-server and --target-server")
        sys.exit(1)

    if not options.source_url.endswith('/'):
        options.source_url = options.source_url + '/'
    if not options.target_url.endswith('/'):
        options.target_url = options.target_url + '/'

    source_server = couchdb.client.Server(options.source_url)
    target_server = couchdb.client.Server(options.target_url)

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

        body.update({'source': '%s%s' % (options.source_url, dbname), 'target': dbname})
        target_server.resource.post('_replicate', body)
        print '%.1fs' % (time.time() - start)
    
    if options.compact_target:
        compact(target_server, dbnames)

if __name__ == '__main__':
    main()
