import sys

if sys.version_info[0] < 3:
    from couchdb.util2 import *
else:
    from couchdb.util3 import *
