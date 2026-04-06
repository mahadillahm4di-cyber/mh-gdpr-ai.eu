.PHONY: install test lint type-check clean examples

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

test:
	pytest -v --tb=short

test-cov:
	pytest -v --cov=sovereign_gateway --cov-report=html --cov-report=term

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

type-check:
	mypy sovereign_gateway/

examples:
	python examples/basic_routing.py
	python examples/pii_detection.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
