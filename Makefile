.PHONY: test doc upload-doc

test:
	PYTHONPATH=. python couchdb/tests/__init__.py

doc:
	python setup.py build_sphinx

upload-doc:
	python setup.py upload_sphinx
