Release procedure
=================

A list of steps to perform when releasing.

* Run tests against latest CouchDB release (ideally also trunk)
* Run tests on different Python versions
* Update ChangeLog and add a release date, then commit
* Merge changes from default to stable
* Edit setup.cfg (in the tag), remove the egg_info section and commit
* Tag the just-committed changeset, then update to the tag
* python setup.py bdist_wheel sdist --formats=gztar upload
* Revert the setup.cfg change.
* Update the version number on the branch to 0.10.1
