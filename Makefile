# DUBFORGE — Build & Quality Targets
# ─────────────────────────────────────
.PHONY: build test lint fmt check clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

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

test: ## Run pytest suite
	python3 -m pytest tests/ -v

lint: ## Lint with ruff
	python3 -m ruff check engine/ run_all.py tests/

fmt: ## Auto-format with ruff
	python3 -m ruff format engine/ run_all.py tests/

check: lint test ## Lint + test together

clean: ## Remove generated outputs and caches
	rm -rf output/ __pycache__ engine/__pycache__ .pytest_cache
	find . -name '*.pyc' -delete
