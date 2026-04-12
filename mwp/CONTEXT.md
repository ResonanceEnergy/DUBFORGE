# DUBFORGE — MWP/ICM Stage Index
> Layer 1: Where do I go? Read this after CLAUDE.md.

---

## Pipeline Overview

One direction. Four stages. Each produces a filesystem artifact. Human reviews between.

Canonical runner for the project:
- `python forge.py --launch --ui-only` (UI only)
- `python forge.py --launch --track quick` (render + UI)
- `python forge.py --song "TRACK NAME"` (CLI pipeline)

```
SONG IDEA
    │
    ▼ stages/01-generation/
  [GENERATION]  →  output/song_mandate.json + output/audio_manifest.json
    │               output/als_path.txt
    ▼ stages/02-arrangement/
  [ARRANGEMENT] →  output/arranged_track.json + output/stems_manifest.json
    │               output/arrangement_bounce.wav
    ▼ stages/03-mixing/
  [MIXING]      →  output/mixed_track.json
    │               output/mix_bounce.wav
    ▼ stages/04-mastering/
  [MASTERING]   →  output/master_info.json + output/report_card.md
                    output/master.wav
```

---

## Stage Routing

| Stage | Folder | Entry | Human Gate |
|-------|--------|-------|------------|
| 01 — GENERATION | `stages/01-generation/` | `engine/phase_one.py::run_phase_one()` | Load Serum 2 presets in ALS |
| 02 — ARRANGEMENT | `stages/02-arrangement/` | `engine/phase_two.py::run_phase_two()` | Set up sidechain compressor in Ableton |
| 03 — MIXING | `stages/03-mixing/` | `engine/phase_three.py::run_phase_three()` | Pre-load EQ Eight + Compressor on mix buses |
| 04 — MASTERING | `stages/04-mastering/` | `engine/phase_four.py::run_phase_four()` | Pre-load Master chain (EQ Eight + Glue Comp + Limiter) |

---

## Handoff Protocol

1. Stage N writes `output/stage_summary.md` — human-readable completion status
2. Human reads summary, edits any output/*.json if adjustment needed
3. Human opens Ableton, performs manual gate action (see Human Gate above)
4. Stage N+1 reads `../stages/0N/output/` as its input — never the raw Python objects

---

## Workspace Config Lock

These files are **stable across all runs**. Edit them to reconfigure the factory, not each product.

| Config | Controls |
|--------|---------|
| `_config/conventions.md` | Naming, file format, 15 ICM rules |
| `_config/voice.md` | ill.Gates + Subtronics aesthetic targets |
| `_config/ableton_rules.md` | AbletonOSC Cardinal Rules |
| `_config/phi_constants.md` | Phi/Fibonacci timing and frequency constants |

---

## Quick Status Check

```bash
# See what stages have output
ls mwp/stages/*/output/*.json 2>/dev/null | sort

# Read last generation summary
cat mwp/stages/01-generation/output/stage_summary.md

# Check for pending stages
for d in mwp/stages/*/output; do
  echo "=== $d ==="; ls "$d"/ 2>/dev/null || echo "(empty)"; done
```
