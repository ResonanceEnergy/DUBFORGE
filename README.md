# DUBFORGE

**Planck x phi Fractal Basscraft Engine**

A Python-powered sound design engine built on Dan Winter's Planck x phi fractal mathematics. Every module — wavetable generation, arrangement optimization, bass layering, analysis, DSP processing — is keyed to the golden ratio, Fibonacci sequence, and fractal self-similarity.

**51 engine modules · 1021 tests · v2.6.0**

## Project Structure

```
DUBFORGE/
├── DOCTRINE.md                          # Core principles & rules
├── run_all.py                           # Master build script
├── README.md                            # This file
├── pyproject.toml                       # Package metadata & deps
│
├── engine/                              # Python engine modules (47)
│   ├── __init__.py                      # Unified public API
│   ├── config_loader.py                 # Centralized YAML config reader
│   ├── log.py                           # Centralized logging
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
│   ├── midi_export.py                   # MIDI file export engine
│   ├── memory.py                        # Long-term memory persistence
│   ├── drum_generator.py               # Drum & percussion generator
│   ├── sample_slicer.py                # Sample slicer
│   ├── mastering_chain.py              # Mastering chain processor
│   ├── als_generator.py                # Ableton Live Set (.als) generator
│   ├── fxp_writer.py                   # FXP / VST2 preset writer
│   ├── vocal_chop.py                   # Vocal chop synthesizer
│   ├── fx_generator.py                 # FX generator (risers/impacts/sub drops)
│   ├── bass_oneshot.py                 # Bass one-shot generator
│   ├── transition_fx.py               # Transition FX generator
│   ├── pad_synth.py                    # Pad & atmosphere synthesizer
│   ├── lead_synth.py                   # Lead sound synthesizer
│   ├── perc_synth.py                   # Percussion one-shot synthesizer
│   ├── ambient_texture.py             # Ambient texture generator
│   ├── sub_bass.py                     # Sub-bass one-shot generator
│   ├── noise_generator.py             # Noise texture generator
│   ├── arp_synth.py                    # Arp synth pattern generator
│   ├── pluck_synth.py                  # Pluck one-shot synthesizer
│   ├── granular_synth.py              # Granular synthesizer
│   ├── chord_pad.py                    # Chord pad synthesizer
│   ├── riser_synth.py                  # Riser synthesizer
│   ├── impact_hit.py                   # Impact hit synthesizer
│   ├── wobble_bass.py                  # Wobble bass synthesizer
│   ├── formant_synth.py               # Formant synthesizer
│   ├── glitch_engine.py               # Glitch engine
│   ├── drone_synth.py                  # Drone synthesizer
│   ├── sidechain.py                    # Sidechain engine (5 shapes)
│   ├── riddim_engine.py               # Riddim pattern engine (5 types)
│   ├── pitch_automation.py            # Pitch automation curves
│   ├── lfo_matrix.py                   # LFO modulation matrix
│   ├── stereo_imager.py               # Stereo imaging processor
│   ├── multiband_distortion.py        # Multiband distortion (5 algorithms)
│   ├── arrangement_sequencer.py       # Arrangement sequencer + templates
│   ├── song_templates.py              # Song structure templates (20 templates)
│   ├── vocal_processor.py             # Vocal processing (5 types, 20 presets)
│   ├── reverb_delay.py                # Reverb & delay (5 types, 20 presets)
│   ├── convolution.py                 # Convolution engine (5 IR types, 20 presets)
│   └── harmonic_analysis.py           # FFT harmonic analysis (5 types, 20 presets)
│
├── tests/                               # Test suite (1021 tests)
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
│
└── output/                              # Generated outputs (gitignored)
    ├── wavetables/                       # Serum-ready .wav files
    ├── analysis/                         # JSON reports + PNG charts
    ├── serum2/                           # Serum 2 architecture + patches
    ├── ableton/                          # Ableton Live session/arrangement templates
    ├── midi/                             # DAW-ready .mid files (drag & drop)
    ├── dojo/                             # Producer Dojo methodology outputs
    ├── memory/                           # Long-term memory persistence data
    ├── masters/                          # Mastering chain outputs
    ├── presets/                          # FXP preset files
    └── slices/                          # Sample slicer outputs
```

## Quick Start

```bash
# Run the full engine build (all 44 generator modules)
python3 run_all.py

# Run a single module
python3 run_all.py --module phi_core
python3 run_all.py --module sidechain
python3 run_all.py --module riddim_engine

# List all available modules
python3 run_all.py --list

# Core modules
python3 -m engine.phi_core              # Generate wavetables
python3 -m engine.rco                   # Generate RCO curves
python3 -m engine.psbs                  # Generate PSBS presets
python3 -m engine.sb_analyzer           # Run Subtronics analysis
python3 -m engine.chord_progression     # Generate chord progressions

# Synthesizers
python3 -m engine.lead_synth            # Lead sounds
python3 -m engine.pad_synth             # Pad atmospheres
python3 -m engine.sub_bass              # Sub-bass one-shots
python3 -m engine.bass_oneshot          # Bass one-shots
python3 -m engine.wobble_bass           # Wobble bass
python3 -m engine.pluck_synth           # Pluck one-shots
python3 -m engine.arp_synth             # Arp patterns
python3 -m engine.drone_synth           # Drones
python3 -m engine.formant_synth         # Formant textures
python3 -m engine.granular_synth        # Granular synthesis
python3 -m engine.chord_pad             # Chord pads
python3 -m engine.vocal_chop            # Vocal chops
python3 -m engine.ambient_texture       # Ambient textures
python3 -m engine.noise_generator       # Noise textures

# Percussion & FX
python3 -m engine.drum_generator        # Drums & percussion
python3 -m engine.perc_synth            # Percussion one-shots
python3 -m engine.impact_hit            # Impact hits
python3 -m engine.riser_synth           # Risers
python3 -m engine.transition_fx         # Transition effects
python3 -m engine.fx_generator          # Risers/impacts/sub drops

# DSP & Processing
python3 -m engine.sidechain             # Sidechain envelopes (5 shapes)
python3 -m engine.riddim_engine         # Riddim patterns (5 types)
python3 -m engine.pitch_automation      # Pitch automation curves
python3 -m engine.lfo_matrix            # LFO modulation matrix
python3 -m engine.stereo_imager         # Stereo imaging
python3 -m engine.multiband_distortion  # Multiband distortion
python3 -m engine.mastering_chain       # Mastering chain
python3 -m engine.growl_resampler       # Growl resampling
python3 -m engine.glitch_engine         # Glitch effects
python3 -m engine.sample_slicer         # Sample slicing

# DAW Integration
python3 -m engine.ableton_live          # Ableton templates
python3 -m engine.als_generator         # Ableton .als generation
python3 -m engine.serum2                # Serum 2 patches
python3 -m engine.fxp_writer            # FXP preset export
python3 -m engine.midi_export           # MIDI file export
python3 -m engine.dojo                  # Producer Dojo methodology

# Structure & Arrangement
python3 -m engine.trance_arp            # Fibonacci arp patterns
python3 -m engine.arrangement_sequencer # Arrangement templates
python3 -m engine.song_templates        # Song structure templates
python3 -m engine.vocal_processor       # Vocal processing engine
python3 -m engine.reverb_delay          # Reverb & delay engine
python3 -m engine.convolution           # Convolution engine
python3 -m engine.harmonic_analysis     # Harmonic analysis engine

# Infrastructure
python3 -m engine.memory                # Memory system diagnostics
python3 -m engine.config_loader         # List all configs
```

## Requirements

- Python 3.10+
- NumPy (`pip install numpy`)
- PyYAML (`pip install pyyaml`)
- mido (`pip install mido`) — MIDI file export
- matplotlib (optional, for RCO curve plots)
- soundfile (optional, for audio I/O)

## Engine Modules

### Core & Analysis (5)

| Module | Description |
|--------|-------------|
| **PHI CORE** | Wavetable generator using phi-spaced additive partials. Outputs Serum-compatible .wav files. |
| **Config Loader** | Centralized YAML config reader. Single source of truth for PHI, FIBONACCI, and all config values. |
| **RCO** | Rollercoaster Optimizer — models track energy as time-series, optimizes drop/build/break placement. |
| **PSBS** | Phase-Separated Bass System — 5-layer bass architecture with phi-ratio crossovers. |
| **SB Analyzer** | Subtronics discography analysis — 74-track corpus, signature vectors, VIP deltas, key distribution, spectral profiles. |

### Synthesizers (14)

| Module | Description |
|--------|-------------|
| **Lead Synth** | Lead sound synthesizer with phi-tuned envelopes and filter sweeps. |
| **Pad Synth** | Pad & atmosphere synthesizer with layered harmonic textures. |
| **Sub Bass** | Sub-bass one-shot generator — pure sines with phi-ratio envelopes. |
| **Bass One-Shot** | Mid-range bass one-shot generator with distortion and saturation. |
| **Wobble Bass** | Wobble bass synthesizer with LFO-modulated filter cutoff. |
| **Pluck Synth** | Pluck one-shot synthesizer — Karplus-Strong–style plucks. |
| **Arp Synth** | Arp synth pattern generator — Fibonacci-timed sequences. |
| **Drone Synth** | Drone synthesizer — sustained evolving textures. |
| **Formant Synth** | Formant synthesizer — vowel-shaped resonant filtering. |
| **Granular Synth** | Granular synthesizer — grain cloud engine with phi-spaced onsets. |
| **Chord Pad** | Chord pad synthesizer — rich harmonic stacks. |
| **Vocal Chop** | Vocal chop synthesizer — formant-shifted vocal fragments. |
| **Ambient Texture** | Ambient texture generator — noise + filtered layers. |
| **Noise Generator** | Noise texture generator — white/pink/brown with shaping. |

### Percussion & FX (6)

| Module | Description |
|--------|-------------|
| **Drum Generator** | Drum & percussion generator — kick, snare, hat, clap, perc synthesis. |
| **Perc Synth** | Percussion one-shot synthesizer — tuned metallic & tonal hits. |
| **Impact Hit** | Impact hit synthesizer — transient-heavy hits for drops. |
| **Riser Synth** | Riser synthesizer — filtered sweeps and noise risers. |
| **Transition FX** | Transition FX generator — sweeps, fills, downlifters. |
| **FX Generator** | Multi-type FX generator — risers, impacts, sub drops, combined. |

### DSP & Processing (8)

| Module | Description |
|--------|-------------|
| **Sidechain** | Sidechain engine — 5 shapes (pump, hard cut, smooth, bounce, phi curve) × 4 presets each. |
| **Riddim Engine** | Riddim pattern engine — 5 types (minimal, heavy, bounce, stutter, triplet) × 4 presets each. |
| **Pitch Automation** | Pitch automation — 5 types (dive, rise, wobble, staircase, glide) × 4 presets each. |
| **LFO Matrix** | LFO modulation matrix — 5 waveforms (sine, tri, saw, square, S&H) × 4 presets each. |
| **Stereo Imager** | Stereo imaging — 5 types (Haas, mid/side, frequency split, phase, psychoacoustic) × 4 presets. |
| **Multiband Distortion** | Multiband distortion — 5 algorithms (warm, aggressive, digital, tube, tape) × 4 presets. |
| **Mastering Chain** | Mastering chain — EQ, compression, limiting, phi-ratio crossovers. |
| **Growl Resampler** | Resample + mangle pipeline for mid-bass growls. Distortion, formant shifting, bit reduction. |

### Structure & Arrangement (4)

| Module | Description |
|--------|-------------|
| **Chord Progression** | Music theory engine — 22 chord qualities, 5 scales, 11 EDM presets, phi voicings. |
| **Trance Arp** | Fibonacci-timed arpeggiator with phi-ratio gate times. |
| **Arrangement Sequencer** | Arrangement engine — 4 types (weapon, emotive, hybrid, fibonacci) × 4 templates each. |
| **Song Templates** | Song structure templates — 4 categories (weapon, emotive, hybrid, experimental) × 5 each. |

### DAW Integration (5)

| Module | Description |
|--------|-------------|
| **Ableton Live** | Full LOM integration — session/arrangement templates, device chains, M4L scripts. |
| **ALS Generator** | Ableton Live Set (.als) file generator from session/arrangement templates. |
| **Serum 2** | Complete synth architecture — oscillators, filters, mod matrix, 8 DUBFORGE patches. |
| **FXP Writer** | FXP / VST2 preset writer — exports Serum presets as native .fxp files. |
| **MIDI Export** | MIDI file generator — chord progressions, arps, bass clips, full arrangements as .mid files. |

### Infrastructure (5)

| Module | Description |
|--------|-------------|
| **Memory Engine** | Long-term persistence — session logging, asset registry, parameter evolution, phi-weighted recall. |
| **Producer Dojo** | ill.Gates methodology — belt system, The Approach, 128 Rack, session templates. |
| **Sample Slicer** | Sample slicer — beat-aligned slicing with Fibonacci boundaries. |
| **Glitch Engine** | Glitch engine — stutter, reverse, bit-reduce, granular scatter effects. |
| **Log** | Centralized logging utility for all engine modules. |

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

See [DOCTRINE.md](DOCTRINE.md) for the full DUBFORGE Doctrine — the foundational rules governing all engine design decisions.

**Key principles:**
- Golden ratio (phi = 1.618...) is the master constant
- Fibonacci sequence governs all structural decisions
- 432 Hz coherence tuning as optional reference
- Fractality over linearity at every scale
- Self-similar structures from macro arrangement to micro grain
- Long-term memory with Fibonacci snapshots and phi-weighted recall

---

## MIDI Output

The MIDI export engine generates **19+ .mid files** from all DUBFORGE note data:

- **11 chord progressions** — WEAPON_DARK, EMOTIVE_RISE, FRACTAL_SPIRAL, GOLDEN_RATIO, etc.
- **3 arp patterns** — fibonacci_rise, phi_spiral, golden_gate
- **4 Ableton clips** — sub_bass, mid_bass, arp, chord_stab
- **1 full arrangement** — DUBFORGE_FULL.mid with 6 tracks (sub, mid, arp, chords, fib arp, stab)

All files land in `output/midi/`. Drag any `.mid` into Ableton, FL Studio, or any DAW.

---

**Version:** 2.5.0  
**Modules:** 47  
**Tests:** 922  
**Author:** DUBFORGE
