Release procedure
=================

A list of steps to perform when releasing.

* Run tests against latest CouchDB release (ideally also trunk)
* Make sure the version number in setup.py is correct
* Update ChangeLog and add a release date, then commit
* Edit setup.cfg, remove the egg_info section and commit
* Tag the just-committed changeset
* python setup.py bdist_wheel sdist --formats=gztar upload
* Revert the setup.cfg change
* Update the version number in setup.py
* Upload docs to PyPI with ``make upload-doc``
