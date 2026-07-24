.PHONY: setup test lint coverage example

setup:
	uv sync --dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

coverage:
	uv run pytest --cov=diagram_creator --cov-report=term-missing

example:
	uv run diagram-creator examples/agent-workflow.json examples/agent-workflow.png
