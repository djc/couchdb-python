#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Jan lehnardt <jan@apache.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Simple functional test for the replication notification trigger"""

import time

from couchdb import client


def set_up_database(server, database):
    """Deletes and creates a `database` on a `server`"""
    if database in server:
        del server[database]

    return server.create(database)


def run_tests():
    """Inserts a doc into database a, waits and tries to read it back from 
    database b
    """

    # set things up
    database = 'replication_notification_test'
    server_a = client.Server('http://localhost:5984')
    server_b = client.Server('http://localhost:5985')
    # server_c = client.Server('http://localhost:5986')

    db_a = set_up_database(server_a, database)
    db_b = set_up_database(server_b, database)
    # db_c = set_up_database(server_c, database)

    doc = {'jan':'cool'}
    docId = 'testdoc'
    # add doc to node a

    print 'Inserting document in to database "a"'
    db_a[docId] = doc

    # wait a bit. Adjust depending on your --wait-threshold setting
    time.sleep(5)

    # read doc from node b and compare to a
    try:
        db_b[docId] == db_a[docId] # == db_c[docId]
        print 'SUCCESS at reading it back from database "b"'
    except client.ResourceNotFound:
        print 'FAILURE at reading it back from database "b"'


def main():
    print 'Running functional replication test...'
    run_tests()
    print 'Done.'


if __name__ == '__main__':
    main()
