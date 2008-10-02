# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Christopher Lenz
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Support for streamed reading and writing of multipart MIME content."""

from cgi import parse_header

__all__ = ['read_multipart']
__docformat__ = 'restructuredtext en'


def read_multipart(fileobj, boundary=None):
    """Simple streaming MIME multipart parser.
    
    This function takes a file-like object reading a MIME envelope, and yields
    a ``(headers, is_multipart, payload)`` tuple for every part found, where
    ``headers`` is a dictionary containing the MIME headers of that part (with
    names lower-cased), ``is_multipart`` is a boolean indicating whether the
    part is itself multipart, and ``payload`` is either a string (if
    ``is_multipart`` is false), or an iterator over the nested parts.
    
    Note that the iterator produced for nested multipart payloads MUST be fully
    consumed, even if you wish to skip over the content.
    
    :param fileobj: a file-like object
    :param boundary: the part boundary string, will generally be determined
                     automatically from the headers of the outermost multipart
                     envelope
    :return: an iterator over the parts
    """
    headers = {}
    buf = []
    outer = in_headers = boundary is None

    next_boundary = boundary and '--' + boundary + '\n' or None
    last_boundary = boundary and '--' + boundary + '--\n' or None

    def _current_part():
        payload = ''.join(buf)
        if payload.endswith('\n'):
            payload = payload[:-1]
        return headers, False, payload

    for line in fileobj:
        if in_headers:
            if line != '\n':
                name, value = line.split(':', 1)
                headers[name.lower().strip()] = value.strip()
            else:
                in_headers = False
                mimetype, params = parse_header(headers.get('content-type'))
                if mimetype.startswith('multipart/'):
                    sub_boundary = params['boundary']
                    sub_parts = read_multipart(fileobj, boundary=sub_boundary)
                    if boundary is not None:
                        yield headers, True, sub_parts
                    else:
                        for part in sub_parts:
                            yield part
                    return

        elif line == next_boundary:
            # We've reached the start of a new part, as indicated by the
            # boundary
            if headers:
                if not outer:
                    yield _current_part()
                else:
                    outer = False
                headers.clear()
                del buf[:]
            in_headers = True
        elif line == last_boundary:
            # We're done with this multipart envelope
            break

        else:
            buf.append(line)

    if not outer:
        yield _current_part()
