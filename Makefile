.PHONY: install build demo cli test

install:
	uv sync
	cd web && npm ci

build:
	cd web && npm run build

demo: install build
	uv run uvicorn app.server:app --port 8000

cli:
	uv run python -m app.cli

test:
	uv run pytest -q
