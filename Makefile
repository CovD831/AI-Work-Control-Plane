.PHONY: lint test test-quick ci ui-build compliance

PYTHON ?= python
PYTHONPATH ?= src

lint:
	ruff check src tests

test:
	PYTHONPATH=$(PYTHONPATH) pytest

test-quick:
	PYTHONPATH=$(PYTHONPATH) pytest -m "not slow_integration"

ui-build:
	cd ui_frontend && npm run build

compliance:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agent_orchestrator.cli team check-compliance

ci: lint test-quick
