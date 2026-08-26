.PHONY: venv seed init-warehouse load test test-unit test-integration lint clean

PY := .venv/Scripts/python.exe
PIP := uv pip install

venv:
	uv venv .venv --python 3.13
	$(PIP) -r requirements/dev.txt --python $(PY)

seed:
	$(PY) scripts/seed/generate_sources.py

init-warehouse:
	$(PY) -m ingestion.cli init-warehouse

load-customers:
	$(PY) -m ingestion.cli load --source customers --full

load-orders:
	$(PY) -m ingestion.cli load --source orders

test:
	$(PY) -m pytest tests/unit tests/integration -m "not requires_postgres" -v

test-unit:
	$(PY) -m pytest tests/unit -v

test-integration:
	$(PY) -m pytest tests/integration -v

lint:
	.venv/Scripts/ruff.exe check ingestion scripts services tests

clean:
	$(PY) -c "import shutil; shutil.rmtree('data', ignore_errors=True)"
