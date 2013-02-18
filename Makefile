.PHONY: test doc upload-doc

test:
	PYTHONPATH=. python -m couchdb.tests

doc:
	python setup.py build_sphinx

upload-doc:
	python setup.py upload_sphinx
