PY := .venv/bin/python

.PHONY: install build demo cli test

install:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	cd web && npm ci

build:
	cd web && npm run build

demo: install build
	$(PY) -m uvicorn app.server:app --port 8000

cli:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	$(PY) -m app.cli

test:
	$(PY) -m pytest -q
