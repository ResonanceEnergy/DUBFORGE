# DUBFORGE — Build & Quality Targets
# ─────────────────────────────────────
.PHONY: build test test-fast test-slow test-parallel lint fmt check clean help track auto song fury v3 all verify

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

build: ## Run the full engine build
	python3 run_all.py

auto: ## Full auto: DNA → Serum install → Ableton open → play
	python3 -m engine.auto_producer "$(or $(NAME),DUBFORGE AUTO)" $(ARGS)

song: ## Auto-produce a named song (NAME="MY SONG" make song)
	python3 forge.py --auto "$(or $(NAME),Untitled)" $(ARGS)

fury: ## Produce GOLDEN FURY (full auto)
	python3 make_golden_fury.py

track: ## Produce default dubstep track (full auto)
	python3 make_track.py

test: ## Run full pytest suite
	python3 -m pytest tests/ -v

test-fast: ## Fast tests only (~88 files, <30s)
	python3 -m pytest tests/ -m fast -q

test-slow: ## Slow DSP tests only (~40 files)
	python3 -m pytest tests/ -m slow -q

test-parallel: ## Full suite in parallel (needs pytest-xdist)
	python3 -m pytest tests/ -n auto -q

lint: ## Lint with ruff
	python3 -m ruff check engine/ run_all.py tests/

fmt: ## Auto-format with ruff
	python3 -m ruff format engine/ run_all.py tests/

check: lint test ## Lint + test together

clean: ## Remove generated outputs and caches
	rm -rf output/ __pycache__ engine/__pycache__ .pytest_cache
	find . -name '*.pyc' -delete
