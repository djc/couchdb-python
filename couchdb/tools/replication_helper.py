#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Jan Lehnardt <jan@apache.org>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""
CouchDB DbUpdateNotification Script that triggers replication

Daemon script that acts as CouchDB DbUpdateNotificationProcess and triggers
replication on each incoming database update between the specified servers

Setup
Add this to your couch.ini:
DbUpdateNotificationProcess=/path/to/this/script/replication-helper.py \
--source-server=http://127.0.0.1 --target-server=http://127.0.0.1:5985

Format of messages it reads
{"db":"replication_notification_test","type":"updated"}

Todo: Generic'-out the listener part and implement the resplication trigger as
a delegate or subclass.
"""

import fcntl
import httplib
import httplib2
import optparse
import os
import sys
import time
import simplejson as json
from couchdb import __version__ as VERSION


class ReplicationHelper(object):
    """Listener daemon for CouchDB database notifications"""

    def __init__(self, args):
        super(ReplicationHelper, self).__init__()
        self.args = args
        self.http = httplib2.Http()
        self.databases = []

    def concat_uri(self, server, path):
        """Concat a server name and a path, is smart about slashes"""
        if not server.endswith("/"):
            return server + "/" + path
        else:
            return server + path

    def trigger_replication(self, database):
        """Triggers replication between --source- and --target-servers"""

        body = {'source': self.concat_uri(self.args.source_server, database)}

        # send replication request to target server
        for target_server in self.args.target_servers: 
            body['target'] = self.concat_uri(target_server, database)
            self.http.request(
                self.concat_uri(self.args.source_server, '_replicate'), 
                'POST', 
                body=json.dumps(body, ensure_ascii=False))

    def sync_databases(self):
        """Sync self.databases to all target servers"""

        if len(self.databases) > 0:
            for database in self.databases:
                try:
                    # not elegant, but we just don't care for problems
                    # CouchDB will relaunch us
                    self.trigger_replication(database)
                except httplib.HTTPException:
                    sys.exit(0)

            self.databases = []

    def __call__(self):
        """Reads notifications from stdin and triggers replication"""

        args = self.args
        wait_counter = time.time()

        while True:
            # non-blocking readline(), raises IOErrors
            fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)

            try:
                line = sys.stdin.readline()
                
                # poor man's validation. If we get garbage, we sys.exit
                if not line.endswith('}\n'):
                    sys.exit(0)
                note = json.loads(line)

                # we don't care for deletes
                if note['type'] == 'delete' and not args.ignore_deletes:
                    continue

                self.databases.append(note['db']) 
                
                # if there are more docs that we want to batch, flush
                if len(self.databases) >= int(args.batch_threshold):
                    self.sync_databases()
                    continue

            except IOError:
                # if we waited longer that we want to wait, flush
                if (time.time() - wait_counter) > int(args.wait_threshold):
                    self.sync_databases()
                    wait_counter = time.time()

                time.sleep(1)
                # implicit continue


def main():
    usage = '%prog [options] --source-server=http://server:port/ \
--target-servers=http://server2:port2/[,http://server3:port3/, ...]'

    parser = optparse.OptionParser(usage=usage, version=VERSION)

    parser.add_option('--source-server',
        action='store',
        dest='source_server',
        help='the name of the database to replicate from')
    parser.add_option('--target-servers',
        action='store',
        dest='target_servers',
        help='comma separated list of databases to replicate to')
    parser.add_option('--batch-threshold',
        action='store',
        dest='batch_threshold',
        default=0,
        help='number of changes that are to be replicated')
    parser.add_option('--wait-threshold',
        action='store',
        dest='wait_threshold',
        default=0,
        help='number of seconds to wait before triggering replication')
    parser.add_option('--ignore-deletes',
        action='store',
        dest='ignore_deletes',
        help='whether to ignore "delete" notifications',
        default=True)

    options, arg = parser.parse_args()

    if not options.target_servers or not options.source_server:
        parser.error("Need at least --source-server and --target-servers")
        sys.exit(1)

    options.target_servers = options.target_servers.split(',')
            
    ReplicationHelper(options)()

if __name__ == '__main__':
    main()
