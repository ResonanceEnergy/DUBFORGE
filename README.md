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
│   ├── phi_core.py                      # PHI CORE wavetable generator
│   ├── rco.py                           # Rollercoaster Optimizer
│   ├── psbs.py                          # Phase-Separated Bass System
│   ├── sb_analyzer.py                   # Subtronics corpus analyzer
│   ├── trance_arp.py                    # Fibonacci arpeggiator
│   └── growl_resampler.py               # Mid-bass growl resampler
│
├── configs/                             # YAML configurations
│   ├── serum2_module_pack_v1.yaml       # Serum 2 module specs
│   ├── rco_psbs_vip_delta_v1.1.yaml     # RCO + PSBS + VIP delta configs
│   └── fibonacci_blueprint_pack_v1.yaml # Drop structure blueprints
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
    └── analysis/                        # JSON reports + PNG charts
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
```

## Requirements

- Python 3.10+
- NumPy (`pip install numpy`)
- matplotlib (optional, for RCO curve plots)

## Engine Modules

| Module | Description |
|--------|-------------|
| **PHI CORE** | Wavetable generator using phi-spaced additive partials. Outputs Serum-compatible .wav files. |
| **RCO** | Rollercoaster Optimizer — models track energy as time-series, optimizes drop/build/break placement. |
| **PSBS** | Phase-Separated Bass System — 5-layer bass architecture with phi-ratio crossovers. |
| **SB Analyzer** | Subtronics discography analysis engine. Extracts signature vectors and VIP deltas. |
| **Trance Arp** | Fibonacci-timed arpeggiator with phi-ratio gate times. |
| **Growl Resampler** | Resample + mangle pipeline for mid-bass growls. Distortion, formant shifting, bit reduction. |

## Configs

| Config | Description |
|--------|-------------|
| **Serum 2 Module Pack v1** | Complete Serum 2 preset specs: PHI CORE WT, FM Bass, Sub Layer, Trance Arp, Growl Resampler. |
| **RCO/PSBS/VIP Delta v1.1** | Arrangement profiles (WEAPON/EMOTIVE/PACK_WEAPON), bass layer presets, version tracking. |
| **Fibonacci Blueprint Pack** | Three drop structure templates: WEAPON, EMOTIVE, HYBRID — all Fibonacci-timed. |

## Doctrine

See [DOCTRINE.md](DOCTRINE.md) for the full DUBFORGE Doctrine v1.0 — the foundational rules governing all engine design decisions.

**Key principles:**
- Golden ratio (phi = 1.618...) is the master constant
- Fibonacci sequence governs all structural decisions
- 432 Hz coherence tuning as optional reference
- Fractality over linearity at every scale
- Self-similar structures from macro arrangement to micro grain

---

**Version:** 1.0  
**Author:** DUBFORGE
