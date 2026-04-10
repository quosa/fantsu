.PHONY: test cov lint fmt typecheck check build run

test:
	pytest; [ $$? -ne 1 ] && [ $$? -ne 2 ] && [ $$? -ne 3 ] && [ $$? -ne 4 ] || exit 1

cov:
	pytest --cov=fantsu --cov-report=term-missing

lint:
	ruff check fantsu/ tests/

fmt:
	ruff format fantsu/ tests/

typecheck:
	mypy fantsu/

check: lint typecheck test

build:
	python -m build

run:
	python -m fantsu.main
