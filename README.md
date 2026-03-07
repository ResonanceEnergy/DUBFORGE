# DUBFORGE

**Planck x phi Fractal Basscraft Engine**

A Python-powered sound design engine built on Dan Winter's Planck x phi fractal mathematics. Every module — wavetable generation, arrangement optimization, bass layering, analysis — is keyed to the golden ratio, Fibonacci sequence, and fractal self-similarity.

## Project Structure

```
DUBFORGE/
├── DOCTRINE.md                          # Core principles & rules
├── run_all.py                           # Master build script
├── README.md                            # This file
│
├── engine/                              # Python engine modules
│   ├── __init__.py
│   ├── config_loader.py                 # Centralized YAML config reader
│   ├── phi_core.py                      # PHI CORE wavetable generator
│   ├── rco.py                           # Rollercoaster Optimizer
│   ├── psbs.py                          # Phase-Separated Bass System
│   ├── sb_analyzer.py                   # Subtronics corpus analyzer
│   ├── trance_arp.py                    # Fibonacci arpeggiator
│   ├── growl_resampler.py               # Mid-bass growl resampler
│   ├── chord_progression.py             # Chord progression engine
│   ├── ableton_live.py                  # Ableton Live integration
│   ├── serum2.py                        # Serum 2 synthesizer engine
│   ├── dojo.py                          # Producer Dojo / ill.Gates engine
│   ├── midi_export.py                    # MIDI file export engine
│   ├── memory.py                        # Long-term memory persistence
│   └── log.py                           # Centralized logging
│
├── configs/                             # YAML configurations
│   ├── serum2_module_pack_v1.yaml       # Serum 2 module specs
│   ├── rco_psbs_vip_delta_v1.1.yaml     # RCO + PSBS + VIP delta configs
│   ├── fibonacci_blueprint_pack_v1.yaml # Drop structure blueprints
│   ├── memory_v1.yaml                   # Memory system configuration
│   └── sb_corpus_v1.yaml               # Subtronics discography corpus
│
├── tools/                               # Utility tools
│   └── chat_export/                     # Chat transcript exporter
│       ├── export_chat.py
│       ├── chat_transcript.txt
│       ├── INSTRUCTIONS.md
│       ├── run.sh
│       └── run.ps1
│
└── output/                              # Generated outputs (gitignored)
    ├── wavetables/                       # Serum-ready .wav files
    ├── analysis/                         # JSON reports + PNG charts
    ├── serum2/                           # Serum 2 architecture + patches
    ├── ableton/                          # Ableton Live session/arrangement templates
    ├── midi/                             # DAW-ready .mid files (drag & drop)
    ├── dojo/                             # Producer Dojo methodology outputs
    └── memory/                           # Long-term memory persistence data
```

## Quick Start

```bash
# Run the full engine build
python3 run_all.py

# Or run individual modules
python3 -m engine.phi_core          # Generate wavetables
python3 -m engine.rco               # Generate RCO curves
python3 -m engine.psbs              # Generate PSBS presets
python3 -m engine.sb_analyzer       # Run Subtronics analysis
python3 -m engine.trance_arp        # Generate arp patterns
python3 -m engine.growl_resampler   # Generate growl wavetables
python3 -m engine.chord_progression # Generate chord progressions
python3 -m engine.ableton_live      # Generate Ableton templates
python3 -m engine.serum2            # Generate Serum 2 patches
python3 -m engine.dojo              # Generate Dojo methodology
python3 -m engine.midi_export        # Export all MIDI files
python3 -m engine.memory            # Memory system diagnostics
python3 -m engine.config_loader     # List all configs
```

## Requirements

- Python 3.10+
- NumPy (`pip install numpy`)
- PyYAML (`pip install pyyaml`)
- mido (`pip install mido`) — MIDI file export
- matplotlib (optional, for RCO curve plots)

## Engine Modules

| Module | Description |
|--------|-------------|
| **PHI CORE** | Wavetable generator using phi-spaced additive partials. Outputs Serum-compatible .wav files. |
| **Config Loader** | Centralized YAML config reader. Single source of truth for PHI, FIBONACCI, and all config values. |
| **RCO** | Rollercoaster Optimizer — models track energy as time-series, optimizes drop/build/break placement. |
| **PSBS** | Phase-Separated Bass System — 5-layer bass architecture with phi-ratio crossovers. |
| **SB Analyzer** | Subtronics discography analysis engine. Extracts signature vectors and VIP deltas. |
| **Trance Arp** | Fibonacci-timed arpeggiator with phi-ratio gate times. |
| **Growl Resampler** | Resample + mangle pipeline for mid-bass growls. Distortion, formant shifting, bit reduction. |
| **Chord Progression** | Music theory engine — 22 chord qualities, 5 scales, 11 EDM presets, phi voicings. |
| **Ableton Live** | Full LOM integration — session/arrangement templates, device chains, M4L scripts. |
| **Serum 2** | Complete synth architecture — oscillators, filters, mod matrix, 8 DUBFORGE patches. |
| **Producer Dojo** | ill.Gates methodology — belt system, The Approach, 128 Rack, session templates. |
| **MIDI Export** | MIDI file generator — exports chord progressions, arps, bass clips, and full arrangements as DAW-ready .mid files. |
| **Memory Engine** | Long-term persistence — session logging, asset registry, parameter evolution, phi-weighted recall, growth tracking. |

## Configs

| Config | Description |
|--------|-------------|
| **Serum 2 Module Pack v1** | Complete Serum 2 preset specs: PHI CORE WT, FM Bass, Sub Layer, Trance Arp, Growl Resampler. |
| **RCO/PSBS/VIP Delta v1.1** | Arrangement profiles (WEAPON/EMOTIVE/PACK_WEAPON), bass layer presets, version tracking. |
| **Fibonacci Blueprint Pack** | Three drop structure templates: WEAPON, EMOTIVE, HYBRID — all Fibonacci-timed. |
| **Memory v1** | Memory system config — storage paths, recall settings, phi scoring, growth belt thresholds. |
| **SB Corpus v1** | Subtronics discography metadata — 5 albums, 74 tracks with duration/collab/VIP data. |

## CLI Options

```bash
python3 run_all.py                   # Run all modules
python3 run_all.py --module phi_core  # Run a single module
python3 run_all.py --list             # List available modules
python3 run_all.py --no-memory        # Skip memory persistence
python3 run_all.py --quiet            # Suppress per-module banners
```

## Doctrine

See [DOCTRINE.md](DOCTRINE.md) for the full DUBFORGE Doctrine v1.0 — the foundational rules governing all engine design decisions.

**Key principles:**
- Golden ratio (phi = 1.618...) is the master constant
- Fibonacci sequence governs all structural decisions
- 432 Hz coherence tuning as optional reference
- Fractality over linearity at every scale
- Self-similar structures from macro arrangement to micro grain
- Long-term memory with Fibonacci snapshots and phi-weighted recall

---

## MIDI Output

The MIDI export engine generates **19 .mid files** from all DUBFORGE note data:

- **11 chord progressions** — WEAPON_DARK, EMOTIVE_RISE, FRACTAL_SPIRAL, GOLDEN_RATIO, etc.
- **3 arp patterns** — fibonacci_rise, phi_spiral, golden_gate
- **4 Ableton clips** — sub_bass, mid_bass, arp, chord_stab
- **1 full arrangement** — DUBFORGE_FULL.mid with 6 tracks (sub, mid, arp, chords, fib arp, stab)

All files land in `output/midi/`. Drag any `.mid` into Ableton, FL Studio, or any DAW.

---

**Version:** 1.5  
**Author:** DUBFORGE
