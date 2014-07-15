Release procedure
=================

A list of steps to perform when releasing.

* Run tests against latest CouchDB release (ideally also trunk)
* Run tests on different Python versions
* Update ChangeLog and add a release date, then commit
* Merge changes from default to stable
* Edit setup.cfg (in the tag), remove the egg_info? and commit
* Tag the just-committed changeset, then update to the tag
* Run setup.py build_doc again to build the docs for inclusion in the tarball
* python setup.py bdist_egg sdist --formats=gztar upload (ideally also 2.4, 2.5 and 2.6)
* Revert the setup.cfg change.
* Update the version number on the branch to 0.8.1 and on trunk to 0.9.0 (in setup.py and doc/conf.py)
