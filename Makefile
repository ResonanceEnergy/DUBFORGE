# DUBFORGE — Build & Quality Targets
# ─────────────────────────────────────
.PHONY: build test lint fmt check clean help track v3 all verify

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

build: ## Run the full engine build
	python3 run_all.py

test: ## Run pytest suite
	python3 -m pytest tests/ -v

lint: ## Lint with ruff
	python3 -m ruff check engine/ run_all.py tests/

fmt: ## Auto-format with ruff
	python3 -m ruff format engine/ run_all.py tests/

check: lint test ## Lint + test together

track: ## Render Apology V3 (full automated pipeline)
	python3 make_apology_v3.py

v3: track ## Alias for track

all: build track ## Full engine build + V3 track render

verify: ## Verify V3 output artifacts
	python3 _verify.py

clean: ## Remove generated outputs and caches
	rm -rf output/ __pycache__ engine/__pycache__ .pytest_cache
	find . -name '*.pyc' -delete
