PYTHON ?= python3.12

.PHONY: check test

check: test

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
