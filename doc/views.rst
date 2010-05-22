Writing views in Python
=======================

The couchdb-python package comes with a view server to allow you to write
views in Python instead of JavaScript. When couchdb-python is installed, it
will install a script called couchpy that runs the view server. To enable
this for your CouchDB server, add the following section to local.ini::

    [query_servers]
    python=/usr/bin/couchpy

After restarting CouchDB, the Futon view editor should show ``python`` in
the language pull-down menu. Here's some sample view code to get you started::

    def fun(doc):
        if doc['date']:
            yield doc['date'], doc

Note that the ``map`` function uses the Python ``yield`` keyword to emit
values, where JavaScript views use an ``emit()`` function.
