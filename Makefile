.PHONY: test doc upload-doc

test:
	tox

test2:
	PYTHONPATH=. python -m couchdb.tests

test3:
	PYTHONPATH=. python3 -m couchdb.tests

doc:
	python setup.py build_sphinx

upload-doc:
	python setup.py upload_sphinx
