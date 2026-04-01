# DUBFORGE — Build & Quality Targets (v4.1 — Apple Silicon Optimized)
# ─────────────────────────────────────
.PHONY: build test lint fmt check clean help track v3 all verify setup setup-full bench parallel

PYTHON := .venv/bin/python3
UV := uv

# CPU cores for parallel builds (Apple Silicon performance/efficiency)
JOBS := $(shell sysctl -n hw.perflevel0.logicalcpu 2>/dev/null || sysctl -n hw.performancecores 2>/dev/null || nproc 2>/dev/null || echo 4)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup: ## Bootstrap venv + core deps (uv)
	$(UV) venv --python 3.14 .venv
	$(UV) pip install -e ".[dev]"
	@echo "✓ venv ready — run:  source .venv/bin/activate"

setup-full: ## Bootstrap venv + ALL deps (audio, plot, ui, dev)
	$(UV) venv --python 3.14 .venv
	$(UV) pip install -e ".[full,dev]"
	@echo "✓ full venv ready — run:  source .venv/bin/activate"

build: ## Run the full engine build
	$(PYTHON) run_all.py

parallel: ## Run full engine build with parallel modules
	$(PYTHON) run_all.py --parallel --workers $(JOBS)

test: ## Run pytest suite (parallel)
	$(PYTHON) -m pytest tests/ -v -n $(JOBS)

test-seq: ## Run pytest suite (sequential)
	$(PYTHON) -m pytest tests/ -v

lint: ## Lint with ruff
	$(PYTHON) -m ruff check engine/ run_all.py tests/

fmt: ## Auto-format with ruff
	$(PYTHON) -m ruff format engine/ run_all.py tests/

check: lint test ## Lint + test together

track: ## Render Apology V3 (full automated pipeline)
	$(PYTHON) make_apology_v3.py

v3: track ## Alias for track

all: build track ## Full engine build + V3 track render

verify: ## Verify V3 output artifacts
	$(PYTHON) _verify.py

bench: ## Benchmark all modules
	$(PYTHON) -c "from engine.profiler import run_full_benchmark, BenchmarkResult; \
		results = run_full_benchmark(); \
		[print(f'  {r.module:<24s} {r.elapsed_ms:>8.1f}ms  {r.status}') for r in sorted(results, key=lambda x: -x.elapsed_ms)]"

sysinfo: ## Show system info for debugging
	@echo "── DUBFORGE System Info ──"
	@$(PYTHON) --version
	@$(PYTHON) -c "import platform; print(f'Arch: {platform.machine()}')"
	@$(PYTHON) -c "import numpy; print(f'NumPy: {numpy.__version__}'); numpy.show_config()" 2>/dev/null || echo "NumPy not installed"
	@echo "P-cores: $(JOBS)"

clean: ## Remove generated outputs and caches
	rm -rf output/ __pycache__ engine/__pycache__ .pytest_cache .ruff_cache
	find . -name '*.pyc' -delete
