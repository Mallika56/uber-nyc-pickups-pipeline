.PHONY: setup db pipeline dashboard serve dev test lint

setup:  ## create the virtualenv and install Python and npm dependencies
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd dashboard && npm install

db:  ## create the main and test databases
	createdb uber_nyc || true
	createdb uber_nyc_test || true

pipeline:  ## download, validate, load and build marts
	.venv/bin/python -m pipeline.run

dashboard:  ## type-check and build the React dashboard
	cd dashboard && npm run build

serve:  ## run the API and the built dashboard on http://localhost:8000
	.venv/bin/uvicorn api.main:app

test:  ## run the test suite
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .
