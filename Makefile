# DUBFORGE — Build & Quality Targets
# ─────────────────────────────────────
.PHONY: build test test-fast test-slow test-parallel parallel lint fmt check clean help track song all verify nightly nightly-install nightly-uninstall launch launch-ui wild-ones apology template serum-presets state-template state-extract

# Use venv Python when available, fall back to system python3
PYTHON := $(if $(wildcard .venv/bin/python3),.venv/bin/python3,python3)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

build: ## Run the full engine build
	$(PYTHON) forge.py --all

track: ## Quick dubstep track render (output/dubstep_track.wav)
	$(PYTHON) forge.py --song "Quick Dubstep Track" --style dubstep --bpm 140

song: ## Full production pipeline (NAME="MY SONG" make song)
	$(PYTHON) forge.py --song "$(or $(NAME),Untitled)" $(ARGS)

wild-ones: ## Produce Wild Ones V12 (MIDI+ALS+GALATCIA)
	$(PYTHON) forge.py --song "Wild Ones V12" --style dubstep --bpm 150

apology: ## Produce The Apology That Never Came V4 (MIDI+ALS)
	$(PYTHON) forge.py --song "The Apology That Never Came V4" --style dubstep --bpm 140

template: ## Generate base template ALS (NAME="MY TRACK" BPM=150 KEY=D make template)
	$(PYTHON) make_template.py $(if $(NAME),--name "$(NAME)") $(if $(BPM),--bpm $(BPM)) $(if $(KEY),--key $(KEY)) $(if $(CONFIG),--config $(CONFIG))

serum-presets: ## Install DUBFORGE presets to Serum 2 User folder
	$(PYTHON) -c "from engine.serum2_preset import install_all_presets; p=install_all_presets(); print(f'Installed {len(p)} presets')"

state-template: ## Create template ALS for Serum 2 state capture
	$(PYTHON) tools/make_state_template.py

state-extract: ## Extract VST3 state from Ableton-saved template ALS
	$(PYTHON) tools/extract_vst3_state.py output/ableton/_state_capture_template.als -p 'Serum 2' --first -o engine/_captured_serum2_state.py

test: ## Run full pytest suite
	$(PYTHON) -m pytest tests/ -v

test-fast: ## Fast tests only (~88 files, <30s)
	$(PYTHON) -m pytest tests/ -m fast -q

test-slow: ## Slow DSP tests only (~40 files)
	$(PYTHON) -m pytest tests/ -m slow -q

test-parallel: ## Full suite in parallel (needs pytest-xdist)
	$(PYTHON) -m pytest tests/ -n auto -q

parallel: ## Build with all P-cores (parallel wavetable gen) + run tests in parallel
	$(PYTHON) forge.py --parallel
	$(PYTHON) -m pytest tests/ -n auto -q

lint: ## Lint with ruff
	$(PYTHON) -m ruff check engine/ forge.py tests/

fmt: ## Auto-format with ruff
	$(PYTHON) -m ruff format engine/ forge.py tests/

check: lint test ## Lint + test together

all: build track ## Full engine build + track render

launch: ## Render track + launch NEXUS UI (TRACK=wild-ones|apology|forge|quick)
	$(PYTHON) forge.py --launch --track $(or $(TRACK),quick)

launch-ui: ## Launch NEXUS UI only — no track render
	$(PYTHON) forge.py --launch --ui-only

nightly: ## Run nightly health check (manual trigger)
	$(PYTHON) tools/nightly.sh 2>/dev/null || bash tools/nightly.sh

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
