# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import doctest
from StringIO import StringIO
import unittest

from couchdb import multipart


class ReadMultiPartTestCase(unittest.TestCase):

    def test_flat(self):
        text = '''MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="===============1946781859=="

--===============1946781859==
Content-Type: application/json
Content-ID: bar
ETag: "1-4229094393"

{
  "_id": "bar",
  "_rev": "1-4229094393"
}
--===============1946781859==
Content-Type: application/json
Content-ID: foo
ETag: "1-2182689334"

{
  "_id": "foo",
  "_rev": "1-2182689334",
  "something": "cool"
}
--===============1946781859==--
'''
        num = 0
        parts =  multipart.read_multipart(StringIO(text))
        for headers, is_multipart, payload in parts:
            self.assertEqual(is_multipart, False)
            self.assertEqual('application/json', headers['content-type'])
            if num == 0:
                self.assertEqual('bar', headers['content-id'])
                self.assertEqual('"1-4229094393"', headers['etag'])
                self.assertEqual('{\n  "_id": "bar",\n  '
                                 '"_rev": "1-4229094393"\n}', payload)
            elif num == 1:
                self.assertEqual('foo', headers['content-id'])
                self.assertEqual('"1-2182689334"', headers['etag'])
                self.assertEqual('{\n  "_id": "foo",\n  "_rev": "1-2182689334",'
                                 '\n  "something": "cool"\n}', payload)
            num += 1
        self.assertEqual(num, 2)

    def test_nested(self):
        text = '''MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="===============1946781859=="

--===============1946781859==
Content-Type: application/json
Content-ID: bar
ETag: "1-4229094393"

{
  "_id": "bar", 
  "_rev": "1-4229094393"
}
--===============1946781859==
Content-Type: multipart/mixed; boundary="===============0909101126=="
Content-ID: foo
ETag: "1-919589747"

--===============0909101126==
Content-Type: application/json

{
  "_id": "foo", 
  "_rev": "1-919589747", 
  "something": "cool"
}
--===============0909101126==
Content-Type: text/plain
Content-ID: mail.txt

Hello, friends.
How are you doing?

Regards, Chris
--===============0909101126==--
--===============1946781859==
Content-Type: application/json
Content-ID: baz
ETag: "1-3482142493"

{
  "_id": "baz", 
  "_rev": "1-3482142493"
}
--===============1946781859==--
'''
        num = 0
        parts = multipart.read_multipart(StringIO(text))
        for headers, is_multipart, payload in parts:
            if num == 0:
                self.assertEqual(is_multipart, False)
                self.assertEqual('application/json', headers['content-type'])
                self.assertEqual('bar', headers['content-id'])
                self.assertEqual('"1-4229094393"', headers['etag'])
                self.assertEqual('{\n  "_id": "bar", \n  '
                                 '"_rev": "1-4229094393"\n}', payload)
            elif num == 1:
                self.assertEqual(is_multipart, True)
                self.assertEqual('foo', headers['content-id'])
                self.assertEqual('"1-919589747"', headers['etag'])

                partnum = 0
                for headers, is_multipart, payload in payload:
                    self.assertEqual(is_multipart, False)
                    if partnum == 0:
                        self.assertEqual('application/json',
                                         headers['content-type'])
                        self.assertEqual('{\n  "_id": "foo", \n  "_rev": '
                                         '"1-919589747", \n  "something": '
                                         '"cool"\n}', payload)
                    elif partnum == 1:
                        self.assertEqual('text/plain', headers['content-type'])
                        self.assertEqual('mail.txt', headers['content-id'])
                        self.assertEqual('Hello, friends.\nHow are you doing?'
                                         '\n\nRegards, Chris', payload)

                    partnum += 1

            elif num == 2:
                self.assertEqual(is_multipart, False)
                self.assertEqual('application/json', headers['content-type'])
                self.assertEqual('baz', headers['content-id'])
                self.assertEqual('"1-3482142493"', headers['etag'])
                self.assertEqual('{\n  "_id": "baz", \n  '
                                 '"_rev": "1-3482142493"\n}', payload)


            num += 1
        self.assertEqual(num, 3)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(multipart))
    suite.addTest(unittest.makeSuite(ReadMultiPartTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
