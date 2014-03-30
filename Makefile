.PHONY: test doc upload-doc

test: test2 test3

test2:
	PYTHONPATH=. python -m couchdb.tests

test3:
	PYTHONPATH=. python3 -m couchdb.tests

doc:
	python setup.py build_sphinx

upload-doc:
	python setup.py upload_sphinx
