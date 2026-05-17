.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: help setup demo lint test check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install the package + dev tools
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -e ".[dev]"

demo: ## Run every example scenario end to end
	@$(PY) -m expense_pipeline run examples/reports/small_trip.json
	@echo
	@$(PY) -m expense_pipeline run examples/reports/large_trip.json
	@echo
	@$(PY) -m expense_pipeline run examples/reports/blurry_receipt.json
	@echo
	@$(PY) -m expense_pipeline run examples/reports/blurry_receipt.json --no-validation
	@echo
	@$(PY) -m expense_pipeline run examples/reports/gift_highrisk.json
	@echo
	-@$(PY) -m expense_pipeline run examples/reports/eu_resident.json
	@echo
	@$(PY) -m expense_pipeline run examples/reports/eu_resident.json --region EU
	@echo
	@$(PY) -m expense_pipeline cost

lint: ## Run ruff
	$(PY) -m ruff check .

test: ## Run the test suite
	$(PY) -m pytest

check: lint test ## Lint and test

clean: ## Remove caches
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache *.egg-info src/*.egg-info
