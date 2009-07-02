#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Jan Lehnardt <jan@apache.org>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""
CouchDB ``update_notification`` script that triggers replication.

Daemon script that can be used as a CouchDB ``update_notification`` process
and triggers replication on each incoming database update between the
specified servers.

Setup:
Add this to your local.ini, in the section ``[update_notification]``::

    replication = /path/to/couchdb-replicate \\
      --source-server=http://127.0.0.1/ \\
      --target-server=http://127.0.0.1:5985/

Format of the messages it reads::

    {"db":"replication_notification_test","type":"updated"}

TODO: 
 - Generic'-out the listener part and implement the resplication trigger as
   a delegate or subclass.
 - Check if sub-second sleep delays are possible
"""

import fcntl
import httplib
import httplib2
import logging
import optparse
import os
import re
import sys
import time

from couchdb import __version__ as VERSION
from couchdb import json

log = logging.getLogger('couchdb.tools.replication_helper')


class ReplicationHelper(object):
    """Listener daemon for CouchDB database notifications"""

    def __init__(self, source, targets, options):
        super(ReplicationHelper, self).__init__()
        self.source = source
        self.targets = targets
        self.options = options
        self.http = httplib2.Http()
        self.databases = []

    def concat_uri(self, server, path):
        """Concat a server name and a path, is smart about slashes"""
        if not server.endswith("/"):
            return server + "/" + path
        else:
            return server + path

    def trigger_creation(self, database):
        """Creates database in all target servers."""
        log.debug('Create database %r', database)

        # send creation request to target server
        for target in self.targets:
            if target['username'] is not None:
                self.http.add_credentials(target['username'],
                                          target['password'])
            log.debug('Requesting creation of %r from %s', database,
                      target['scheme'] + target['host'])
            resp, data = self.http.request(
                self.concat_uri(target['scheme'] + target['host'], database),
                'PUT')
            if resp.status != 201:
                log.error('Unexpected HTTP response: %s %s (%s)', resp.status,
                          resp.reason, data)
            self.http.clear_credentials()

    def trigger_deletion(self, database):
        """Deletes database in all target servers."""
        log.debug('Delete database %r', database)

        # send deletion request to target server
        for target in self.targets:
            if target['username'] is not None:
                self.http.add_credentials(target['username'],
                                          target['password'])
            log.debug('Requesting deletion of %r from %s', database,
                      target['scheme'] + target['host'])
            resp, data = self.http.request(
                self.concat_uri(target['scheme'] + target['host'], database),
                'DELETE')
            if resp.status != 200:
                log.error('Unexpected HTTP response: %s %s (%s)', resp.status,
                          resp.reason, data)
            self.http.clear_credentials()

    def trigger_replication(self, database):
        """Triggers replication between source and target servers."""
        log.debug('Replicate database %r', database)

        body = {'source': self.concat_uri(self.source, database)}

        # send replication request to target server
        for target in self.targets:
            body['target'] = database
            if target['username'] is not None:
                self.http.add_credentials(target['username'],
                                          target['password'])
            log.debug('Request replication %r from %s', body,
                      target['scheme'] + target['host'])
            resp, data = self.http.request(
                self.concat_uri(target['scheme'] + target['host'],
                                '_replicate'),
                'POST',
                body=json.encode(body))
            if resp.status != 200:
                log.error('Unexpected HTTP response: %s %s (%s)', resp.status,
                          resp.reason, data)
            self.http.clear_credentials()

    def sync_databases(self):
        """Sync self.databases to all target servers."""
        if len(self.databases) > 0:
            log.debug('Syncing databases after %d change(s)',
                      len(self.databases))
            for operation, database in self.databases:
                try:
                    # not elegant, but we just don't care for problems
                    # CouchDB will relaunch us
                    if operation == 'updated':
                        self.trigger_replication(database)
                    elif operation == 'deleted':
                        self.trigger_deletion(database)
                    elif operation == 'created':
                        self.trigger_creation(database)
                except httplib.HTTPException, e:
                    log.error('HTTP error: %s', e, exc_info=True)
                    sys.exit(0)
            self.databases = []

    def __call__(self):
        """Reads notifications from stdin and triggers replication"""

        options = self.options
        wait_counter = time.time()

        while True:
            # non-blocking readline(), raises IOErrors
            fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)

            try:
                line = sys.stdin.readline()

                # poor man's validation. If we get garbage, we sys.exit
                if not line.endswith('}\n'):
                    sys.exit(0)
                note = json.decode(line)

                log.debug('Received %r', note)

                # we don't care for deletes
                if note['type'] == 'delete' and not options.ignore_deletes:
                    continue

                self.databases.append((note['type'], note['db']))

                # if there are more docs that we want to batch, flush
                if len(self.databases) >= int(options.batch_threshold):
                    self.sync_databases()
                    continue

            except IOError:
                # if we waited longer that we want to wait, flush
                if (time.time() - wait_counter) > int(options.wait_threshold):
                    self.sync_databases()
                    wait_counter = time.time()

                time.sleep(float(options.wait_threshold))
                # implicit continue


URLSPLIT_RE = re.compile(
    r'(?P<scheme>https?://)'               # http:// or https://
    r'((?P<username>.*):(?P<password>.*)@)?' # optional user:pass combo
    r'(?P<host>.*)',                       # hostname:port'''
    re.VERBOSE
)


def main():
    usage = '%prog [options] SOURCE_URL TARGET_URL1 [TARGET_URL2 ...]'

    parser = optparse.OptionParser(usage=usage, version=VERSION)

    parser.add_option('--batch-threshold',
        action='store',
        dest='batch_threshold',
        default=0,
        metavar='NUM',
        help='number of changes that are to be replicated')
    parser.add_option('--wait-threshold',
        action='store',
        dest='wait_threshold',
        default=0.01,
        metavar='SECS',
        help='number of seconds to wait before triggering replication')
    parser.add_option('--ignore-deletes',
        action='store_true',
        dest='ignore_deletes',
        help='whether to ignore "delete" notifications')
    parser.add_option('--debug',
        action='store_true',
        dest='debug',
        help='enable debug logging; requires --log-file to be specified')
    parser.add_option('--log-file',
        action='store',
        dest='log_file',
        metavar='FILE',
        help='name of the file to write log messages to, or "-" to enable '
             'logging to the standard error stream')
    parser.add_option('--json-module',
        action='store',
        dest='json_module',
        metavar='NAME',
        help='the JSON module to use ("simplejson", "cjson", or "json" are '
             'supported)')

    options, args = parser.parse_args()
    if len(args) < 2:
        parser.error("need at least one source and target server")
        sys.exit(1)

    src_url = args[0]
    targets = [
        URLSPLIT_RE.match(url).groupdict()
        for url in args[1:]
    ]

    if options.debug:
        log.setLevel(logging.DEBUG)

    if options.log_file:
        if options.log_file == '-':
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(
                ' -> [%(levelname)s] %(message)s'
            ))
        else:
            handler = logging.FileHandler(options.log_file)
            handler.setFormatter(logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s'
            ))
        log.addHandler(handler)

    if options.json_module:
        json.use(options.json_module)

    log.debug('Syncing changes from %r to %r', src_url, targets)
    try:
        ReplicationHelper(src_url, targets, options)()
    except Exception, e:
        log.exception(e)


if __name__ == '__main__':
    main()
