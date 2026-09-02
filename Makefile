.PHONY: install test check clean

install:
	python -m pip install -e .

test:
	python -m pytest -q tests

check: test

clean:
	rm -rf build dist *.egg-info .pytest_cache
	discarded
