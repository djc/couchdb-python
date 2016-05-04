#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load design documents from the filesystem into a dict.
Subset of couchdbkit/couchapp functionality.

Description
-----------

Convert a target directory into an object (dict).

Each filename (without extension) or subdirectory name is a key in this object.

For files, the utf-8-decoded contents are the value, except for .json files
which are first decoded as json.

Subdirectories are converted into objects using the same procedure and then
added to the parent object.

Typically used for design documents. This directory tree::

  .
    ├── filters
    │   └── forms_only.js
    ├── _id
    ├── language
    ├── lib
    │   └── validate.js
    └── views
        ├── view_a
        │   └── map.js
        ├── view_b
        │   └── map.js
        └── view_c
            └── map.js

Becomes this object::

    {
      "views": {
        "view_a": {
          "map": "function(doc) { ... }"
        },
        "view_b": {
          "map": "function(doc) { ... }"
        },
        "view_c": {
          "map": "function(doc) { ... }"
        }
      },
      "_id": "_design/name_of_design_document",
      "filters": {
        "forms_only": "function(doc, req) { ... }"
      },
      "language": "javascript",
      "lib": {
        "validate": "// A library for validations ..."
      }
    }

"""

from __future__ import unicode_literals, absolute_import

import os.path
import pprint
import codecs
import json

def load_design_doc(directory, strip_files=False):
    """
    Load a design document from the filesystem.

    strip_files: remove leading and trailing whitespace from file contents,
        like couchdbkit.
    """
    objects = {}

    for (dirpath, dirnames, filenames) in os.walk(directory, topdown=False):
        key = os.path.split(dirpath)[-1]
        ob = {}
        objects[dirpath] = (key, ob)

        for name in filenames:
            fkey = os.path.splitext(name)[0]
            fullname = os.path.join(dirpath, name)
            with codecs.open(fullname, 'r', 'utf-8') as f:
                contents = f.read()
                if name.endswith('.json'):
                    contents = json.loads(contents)
                elif strip_files:
                    contents = contents.strip()
                ob[fkey] = contents

        for name in dirnames:
            if name == '_attachments':
                raise NotImplementedError()
            subkey, subthing = objects[os.path.join(dirpath, name)]
            ob[subkey] = subthing

    return ob


def main():
    import sys
    try:
        directory = sys.argv[1]
    except IndexError:
        sys.stderr.write("Usage:\n\t{} [directory]\n".format(sys.argv[0]))
        sys.exit(1)
    obj = load_design_doc(directory)
    sys.stdout.write(json.dumps(obj, indent=2))


if __name__ == "__main__":
    main()
