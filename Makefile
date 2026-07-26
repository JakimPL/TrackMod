.PHONY: test
test:
	uv run pytest

.PHONY: coverage
coverage:
	uv run pytest --cov

.PHONY: lint
lint:
	uv run mypy
	uv run pylint src/trackmod

.PHONY: format
format:
	uv run isort .
	uv run black .
