# DUBFORGE — Build & Quality Targets
# ─────────────────────────────────────
.PHONY: build test test-fast test-slow test-parallel lint fmt check clean help track song all verify nightly nightly-install nightly-uninstall launch launch-ui wild-ones apology serum-presets

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

build: ## Run the full engine build
	python3 run_all.py

track: ## Quick dubstep track render (output/dubstep_track.wav)
	python3 make_track.py

song: ## Full production pipeline (NAME="MY SONG" make song)
	python3 forge.py --auto "$(or $(NAME),Untitled)" $(ARGS)

wild-ones: ## Produce Wild Ones V12 (MIDI+ALS+GALATCIA)
	python3 make_wild_ones_v12.py

apology: ## Produce The Apology That Never Came V4 (MIDI+ALS)
	python3 make_apology_v4.py

serum-presets: ## Install DUBFORGE presets to Serum 2 User folder
	python3 -c "from engine.serum2_preset import install_all_presets; p=install_all_presets(); print(f'Installed {len(p)} presets')"

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

all: build track ## Full engine build + track render

launch: ## Render track + launch all browser UIs (TRACK=wild-ones|apology|forge|quick)
	python3 launch.py --track $(or $(TRACK),quick)

launch-ui: ## Launch all browser UIs only (no render)
	python3 launch.py --ui-only

nightly: ## Run nightly health check (manual trigger)
	bash tools/nightly.sh

nightly-install: ## Install nightly launchd agent (runs at 3 AM)
	cp tools/com.resonance.dubforge.nightly.plist ~/Library/LaunchAgents/
	launchctl load ~/Library/LaunchAgents/com.resonance.dubforge.nightly.plist
	@echo "✓ Nightly agent installed — runs at 03:00 daily"
	@echo "  Manual trigger: launchctl start com.resonance.dubforge.nightly"

nightly-uninstall: ## Remove nightly launchd agent
	launchctl unload ~/Library/LaunchAgents/com.resonance.dubforge.nightly.plist 2>/dev/null || true
	rm -f ~/Library/LaunchAgents/com.resonance.dubforge.nightly.plist
	@echo "✓ Nightly agent removed"

clean: ## Remove generated outputs and caches
	rm -rf output/ __pycache__ engine/__pycache__ .pytest_cache
	find . -name '*.pyc' -delete
