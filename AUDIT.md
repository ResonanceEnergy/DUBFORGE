# DUBFORGE v1.4.0 — COMPREHENSIVE TECHNICAL AUDIT

**Date:** 2025-03-07  
**Auditor:** GitHub Copilot (Claude Opus 4.6)  
**Scope:** Every engine module, all configs, all tests, all output artifacts, run_all.py  
**Codebase:** 10,761 lines across 27 source files (13 engine + 14 test + run_all.py)

---

## EXECUTIVE SUMMARY

DUBFORGE is a **math-driven sound design specification framework** for dubstep production. It implements phi/Fibonacci-based algorithms across 13 modules. The honest truth:

- **4 real audio files** (.wav wavetables) are generated — from 2 of 13 modules
- **86 JSON files** describe synth patches, arrangements, analysis, and methodology
- **1 Python script** for Max for Live is generated
- **0 MIDI files**, **0 .fxp presets**, **0 .als projects** exist
- The pipeline runs end-to-end, 209 tests pass, zero lint errors
- ~80% of the codebase generates structured documentation/metadata, not audio

**Bottom line:** DUBFORGE is a well-engineered specification generator with a real DSP kernel buried inside. Two modules produce real audio you can load in Serum today. The other eleven produce JSON blueprints that require manual translation in your DAW.

---

## 1. WHAT EACH MODULE ACTUALLY DOES

### phi_core.py — 231 lines | ✅ PRODUCES REAL AUDIO
The crown jewel. Generates Serum-compatible wavetables using phi-spaced additive synthesis.

- `generate_phi_core_v1()`: 256 frames × 2048 samples, phi-ratio harmonic series. Clean, organic timbre.
- `generate_phi_core_v2_wook()`: Dirtier variant with sub-harmonic folding + tanh saturation.
- `write_wav()`: Proper RIFF/WAV writer with Serum's `clm ` chunk marker (critical for Serum wavetable recognition).
- Helper functions: `phi_harmonic_series()`, `fibonacci_harmonic_series()`, `midi_to_freq()`, `freq_to_midi()`.
- **Output:** 2 WAV files (DUBFORGE_PHI_CORE.wav, DUBFORGE_PHI_CORE_v2_WOOK.wav) — ~1MB each, 16-bit PCM mono 44100Hz.
- **Verdict:** This is real DSP. These wavetables load directly into Serum and sound legitimate.

### growl_resampler.py — 287 lines | ✅ PRODUCES REAL AUDIO
Resample+mangle pipeline for mid-bass growls. 6-step processing chain.

- Pipeline: pitch_shift → waveshape_distortion → frequency_shift → comb_filter → bit_reduce → formant_filter
- `generate_saw_source()`: Raw sawtooth wavetable (256 × 2048)
- `generate_fm_source()`: FM synthesis wavetable with phi-ratio modulator
- Uses `phi_core.write_wav()` for output.
- **Output:** 2 WAV files (DUBFORGE_GROWL_SAW.wav, DUBFORGE_GROWL_FM.wav) — ~1MB each.
- **Caveat:** The "pitch shift" is FFT bin-shifting, not proper resampling. The "formant filter" is a simple frequency-domain window. Good enough for wavetable mangling, not production-grade DSP.
- **Verdict:** Real audio output. The growls are audible and usable as Serum wavetable sources.

### chord_progression.py — 810 lines | ⚠️ JSON ONLY
Full music theory engine. 22 chord qualities, 5 scale types, Roman numeral resolution, 11 dubstep-specific presets.

- `build_chord()`: Constructs chords from root + quality. Real interval math.
- `build_progression()`: Resolves Roman numeral progressions to MIDI note numbers.
- 11 presets: WEAPON_DARK, EMOTIVE_RISE, GOLDEN_RATIO, FIBONACCI_DROP, WOOK_TRIP, FRACTAL_SPIRAL, TESSERACT, 432_SACRED, STEPWISE_GRIND, ANTIFRACTAL, ANDALUSIAN_WEAPON.
- `progression_to_midi_sequence()`: Returns Python dicts with note/velocity/time data — **NOT .mid files**.
- `phi_voice_spread()`, `fibonacci_harmonic_rhythm()`: Real musical algorithms.
- **Output:** 11 JSON files with chord/note data.
- **What's missing:** MIDI file export. The `progression_to_midi_sequence()` function creates perfect data for it, but nobody writes the .mid file. DOCTRINE.md lists this as "L2: MIDI File Export" — future roadmap.

### rco.py — 341 lines | ⚠️ JSON + OPTIONAL PNG
Rollercoaster Optimizer — energy curve modeling for track arrangements.

- 4 curve types: `phi_curve()`, `fibonacci_step_curve()`, `linear_curve()`, `exponential_curve()`.
- 3 built-in presets (subtronics_weapon/emotive/hybrid) + YAML-loaded profiles (WEAPON_16_32, EMOTIVE_LONG, PACK_WEAPON).
- `plot_curve()`: matplotlib PNG output (optional dep — if matplotlib not installed, silently skipped).
- **Output:** 6 JSON files mapping bar×energy curves.
- **Verdict:** Useful for arrangement planning. You'd read the JSON or look at the PNG to plan your drop structure. No DAW integration.

### psbs.py — 373 lines | ⚠️ JSON ONLY (with unused DSP)
Phase-Separated Bass System — 5-layer bass architecture model.

- `phi_crossovers()`: Calculates frequency band boundaries using phi ratios. Real math.
- 3 presets: default, weapon, wook — each defines 5–6 frequency layers with gain/phase/distortion/width parameters.
- `render_psbs_cycle()`: **Actually renders** a single-cycle waveform as np.ndarray by summing sine partials per layer. But this result is **never written to a file** in the default pipeline.
- `calculate_phase_coherence()`: Phase relationship analysis between layers.
- `export_preset()`: Writes JSON.
- **Output:** 3 JSON preset files.
- **Hidden potential:** `render_psbs_cycle()` does real DSP that could produce a wavetable, but the pipeline discards the result.

### serum2.py — 1,584 lines | ⚠️ JSON ONLY (largest module)
Comprehensive Serum 2 synthesizer architecture model.

- Massive enum/dataclass hierarchy: OscillatorType, WarpMode (17 modes), FilterType (20+ types), EffectType (12), DistortionMode (12), UnisonMode (8), LFOShape (12), MatrixSource, ModMatrixSlot.
- `Serum2Patch` dataclass: Full synth state covering oscillators, filters, envelopes, LFOs, effects, mod matrix.
- `build_dubstep_patches()`: Generates 8 named patches — Fractal Sub, Phi Growl, Fibonacci FM Screech, Golden Reese, Spectral Tear, Granular Atmosphere, Weapon, Phi Pad.
- Phi helper functions: `phi_unison_detune()`, `phi_envelope()`, `phi_filter_cutoff()`, `phi_fm_ratio()`, `phi_lfo_rates()`, `phi_distortion_curve()`, `fibonacci_fm_ratios()`.
- `build_init_template()`: Default Serum 2 patch starting point.
- **Output:** 5 JSON files (architecture, patches, presets, wavetable_map, init_template).
- **What's missing:** .fxp preset export. These JSON specs are detailed enough to reconfigure Serum 2 by hand, but there's no automated import. DOCTRINE.md: "L1: Serum 2 .fxp Export" — future.
- **Verdict:** This is a 1,584-line Serum 2 knowledge base serialized as Python dataclasses → JSON. The phi math helpers are real and useful. The patches are manual reference sheets, not loadable presets.

### ableton_live.py — 1,561 lines | ⚠️ JSON + M4L SCRIPT TEXT
Ableton Live session/arrangement template generator + M4L script generator.

- Enums: ABLETON_COLORS, ClipTriggerQuantization, LaunchMode, WarpMode, DeviceType.
- Dataclasses: MidiNote, MidiClip, AudioClip, Track, Scene, SessionTemplate, ArrangementSection, ArrangementTemplate.
- `build_dubstep_session_template()`: 10 tracks (SUB, MID_BASS, TOP_BASS, MID_HIGH, REESE, ARP, CHORD, PAD, VOCAL, DRUMS) + 2 returns (reverb, delay) + 8 scenes.
- `build_arrangement_template()`: Fibonacci bar sections → JSON timeline.
- MIDI clip generators: `generate_sub_bass_clip()`, `generate_mid_bass_clip()`, `generate_arp_clip()`, `generate_chord_stab_clip()` — realistic MIDI patterns.
- `psbs_device_chain()`: Instrument Rack config → JSON.
- `generate_m4l_control_script()`: Generates actual Python code using `import Live` API — valid M4L script.
- `LOM_REFERENCE`: ~200-line dict documenting the Live Object Model.
- **Output:** 11 JSON files + 1 Python M4L script (dubforge_m4l_setup.py).
- **What's missing:** .als file generation. The M4L script is valid Python but needs manual installation as an M4L device. DOCTRINE.md: "L3: Ableton .als Generation" — future.
- **Verdict:** The M4L script generator is the closest thing to real DAW integration. If you paste the generated Python into a Max for Live device, it could configure tracks/devices. But it's not a turnkey solution.

### trance_arp.py — 216 lines | ⚠️ JSON ONLY
Fibonacci-timed arpeggiator patterns.

- 3 patterns: `fibonacci_rise_pattern()` (13 notes), `phi_spiral_pattern()` (21 notes), `golden_gate_pattern()` (also 13 notes, different sequence).
- `pattern_to_midi_data()`: Returns list of dicts with note/velocity/time — **not .mid files**.
- `export_pattern()`: Writes JSON.
- **Output:** 3 JSON arp pattern files.
- **What's missing:** MIDI file export (same gap as chord_progression).

### dojo.py — 1,465 lines | ⚠️ PURE DOCUMENTATION ENGINE
Producer Dojo / ill.Gates methodology serialized as JSON.

- `BELT_SYSTEM`: 7 belt levels (White → Black) with Fibonacci track count requirements.
- `THE_APPROACH`: 7-phase workflow methodology.
- `DOJO_TECHNIQUES`: 8 techniques (128 Rack, Mudpies, Infinite Drum Rack, Sound Sorting, etc.)
- `ARTIST_PROFILE`: ill.Gates bio/discography/awards.
- `DOJO_PLATFORM`: Platform description.
- `build_128_rack()`: 128-zone Drum Rack zone distribution spec.
- `build_dojo_session_template()`: Ableton session layout spec.
- **Output:** 6 JSON methodology documents.
- **Verdict:** This is a knowledge base, not a generative engine. It documents production methodologies as structured data. Zero audio, zero MIDI, zero DAW artifacts. Useful as reference material, but 1,465 lines of code for what is essentially documentation seems like overkill.

### sb_analyzer.py — 528 lines | ⚠️ HARDCODED METADATA ANALYSIS
Subtronics discography analysis — uses hardcoded metadata, not actual audio.

- `build_corpus()`: Returns Album/Track dataclasses for 5 albums (FRACTALS, Antifractals, Tesseract, Fibonacci Pt1, Fibonacci Pt2). 74 total tracks with real durations sourced from Apple Music.
- `analyze_corpus()`: Computes stats (avg BPM, duration, collab rate, key distribution — but BPM/key are hardcoded defaults, not analyzed).
- `build_signature_vector()`: Extracts "SB10 Baseline" — 10 production parameters as a SignatureVector dataclass. The values are partially real (track count, avg duration) and partially assumed (avg_bpm: 150 for all, default_key: "F" for all).
- `vip_delta_analysis()`: Compares FRACTALS originals → Antifractals VIPs by title matching. Duration deltas are real.
- `load_corpus()`: Loads track durations from configs/sb_corpus_v1.yaml (real Apple Music metadata).
- **Output:** 3 JSON files (corpus, signature_vector, vip_deltas).
- **Verdict:** The duration data is real. The BPM/key "analysis" is fake — it assigns defaults, not measured values. The function docstring mentions "spectral analysis" but there is zero FFT/spectral code. This module would need actual audio file analysis to deliver on its implied promise.

### memory.py — 1,008 lines | ✅ FUNCTIONAL PERSISTENCE SYSTEM
Long-term session persistence, asset tracking, growth milestones.

- `MemoryEngine` class: Full lifecycle management — sessions, events, assets, evolution, insights, recall.
- `begin_session()` / `end_session()`: Session lifecycle with Fibonacci snapshot triggers.
- `register_asset()`: Tracks every generated file with metadata, lineage, tagging.
- `track_param_change()`: Evolution tracking with Fibonacci-capped history (1597 changes, 233 per-key).
- `recall()`: Phi-weighted relevance scoring — `φ-recency × quality^φ × log_φ(frequency)`.
- Auto-belt promotion: White → Yellow → Green → Blue → Purple → Brown → Black based on session/asset counts.
- Fibonacci snapshots: Full state captured at Fibonacci-numbered sessions (visible in output/memory/snapshots/).
- **Output:** index.json, asset_registry.json, evolution.json, insights.json, growth.json, session files, snapshot files.
- **Verdict:** This works. Currently at session #29, 306 registered assets, Purple Belt. The phi-weighted recall is genuinely novel. The gamification (belt system) is motivational but doesn't affect output quality.

### config_loader.py — 307 lines | ✅ FUNCTIONAL UTILITY
Centralized YAML config reader.

- `load_config()`: Loads from configs/ directory. PyYAML primary, custom `_parse_yaml_minimal()` fallback.
- `get_config_value()`: Dot-notation key lookup with defaults.
- `validate_config()`: Tests that configs load without errors.
- Constants: PHI = 1.618..., FIBONACCI = [1..233], A4_432, A4_440 — single source of truth.
- **Verdict:** Clean, works correctly, no issues.

### log.py — 30 lines | ✅ FUNCTIONAL UTILITY
Simple centralized logging. `get_logger()` returns configured `logging.Logger` with `[module_name] message` format.

### __init__.py — 256 lines | ✅ FUNCTIONAL
Re-exports all public symbols from all 12 engine modules. Clean namespace management.

---

## 2. WHAT ACTUALLY WORKS END-TO-END

Running `python3 run_all.py` produces **91 output files** in ~0.2 seconds:

| Output Type | Count | Source Modules | Usable Directly? |
|---|---|---|---|
| WAV wavetables | **4** | phi_core, growl_resampler | **YES** — drag into Serum |
| JSON analysis/specs | **86** | all modules | Reference only |
| M4L Python script | **1** | ableton_live | Needs manual M4L setup |
| PNG charts | **0** | rco (requires matplotlib) | N/A |
| MIDI files | **0** | — | **MISSING** |
| Serum .fxp presets | **0** | — | **MISSING** |
| Ableton .als projects | **0** | — | **MISSING** |

### Verified working:
1. **Wavetable generation** — 4 real WAV files, verified RIFF format, 16-bit PCM mono 44100Hz, ~1MB each, Serum clm chunk present.
2. **Full pipeline orchestration** — `run_all.py` runs all 10 modules sequentially, handles errors gracefully, CLI with `--module`, `--list`, `--no-memory`, `--quiet`.
3. **Memory persistence** — Session tracking across runs, Fibonacci snapshots, belt progression, asset registry. 29 sessions logged, 306 assets tracked.
4. **Config system** — 5 YAML configs load correctly, configs are well-structured with phi/Fibonacci constants throughout.
5. **Test suite** — 209/209 tests pass in 0.16s on Python 3.14.3.

---

## 3. WHAT DOESN'T WORK / IS INCOMPLETE

### Critical gaps (blocking "path to first track"):

1. **No MIDI file export** — chord_progression.py and trance_arp.py generate MIDI note data as Python dicts/JSON but never write .mid files. The data structure is 90% there — `progression_to_midi_sequence()` returns note/velocity/start_beat/duration_beats — but nobody calls a MIDI writer. DOCTRINE.md acknowledges: "L2: MIDI File Export."

2. **No Serum .fxp preset export** — serum2.py generates 1,584 lines of patch specifications as JSON. To use them, you must manually recreate each patch in Serum 2 by reading the JSON and turning knobs. The Serum 2 .fxp binary format is undocumented but reverse-engineerable. DOCTRINE.md acknowledges: "L1: Serum 2 .fxp Export."

3. **No Ableton .als project generation** — ableton_live.py generates JSON templates that describe track layouts, device chains, and clips. An Ableton project file is gzipped XML. DOCTRINE.md acknowledges: "L3: Ableton .als Generation."

### Significant gaps:

4. **PSBS render goes nowhere** — `psbs.py:render_psbs_cycle()` does real DSP (sums sine partials per frequency layer) but the result is an in-memory numpy array that is never written to disk. Adding `phi_core.write_wav()` call would produce a 5th wavetable.

5. **sb_analyzer doesn't analyze audio** — Despite the module name and docstring claiming spectral analysis, it uses hardcoded metadata. BPM is assumed (150 for all), keys are defaulted ("F"), there's no FFT or audio file reading. The duration data from Apple Music is real, but calling this "analysis" is generous.

6. **No matplotlib in default install** — rco.py's `plot_curve()` requires matplotlib, which is an optional dependency. Running the pipeline produces 0 PNG charts unless you `pip install matplotlib` separately.

7. **M4L script requires manual installation** — The generated `dubforge_m4l_setup.py` is valid Python using the Live API, but it needs to be manually placed inside a Max for Live device. There's no automated M4L device creation.

### Minor gaps:

8. **No `--dry-run` mode** — run_all.py always writes output.
9. **No input validation on YAML overrides** — config values are trusted without type checking.
10. **Memory evolution tracking is unused** — `track_param_change()` exists but nothing in the pipeline calls it. 0 param changes recorded across 29 sessions.

---

## 4. INTEGRATION GAPS

### Module isolation:
Modules are **largely independent**. They share config_loader.py constants (PHI, FIBONACCI) and log.py, but don't pass data between each other during execution.

| Gap | Description |
|---|---|
| chord_progression → ableton_live | Chord progressions generate MIDI note data. Ableton clip generators generate independent MIDI data. They don't reference each other. |
| rco → ableton_live | RCO energy curves map bar numbers to energy levels. Arrangement templates use Fibonacci bar counts independently. No energy-aware automation. |
| psbs → serum2 | PSBS defines frequency layers. Serum2 patches define filter cutoffs independently. The PSBS layer ranges could drive Serum2 filter/EQ settings but don't. |
| phi_core → serum2 | Phi_core generates wavetables. Serum2 specs reference "DUBFORGE_PHI_CORE.wav" by filename string. No programmatic linkage. |
| sb_analyzer → anything | The Subtronics analysis data (signature vector, VIP deltas) doesn't feed into any other module. It's a standalone report. |
| dojo → anything | Pure documentation. Zero integration with any generative module. |
| memory → modules | Memory tracks what modules ran and what files were produced, but doesn't influence module behavior. The recall system exists but nothing queries it. |

### Cross-module data flow that DOES work:
- `run_all.py` orchestrates sequential execution and memory session wrapping.
- `growl_resampler.py` calls `phi_core.write_wav()` — the only real cross-module function call.
- All modules use `config_loader.load_config()` for YAML reading.
- Config YAML files reference module outputs (e.g., fibonacci_blueprint_pack_v1.yaml references `DUBFORGE_PHI_CORE.wav` and `PSBS WEAPON` preset).

### What integration SHOULD look like:
```
phi_core → wavetable.wav → serum2 .fxp preset (with wavetable embedded)
chord_progression → .mid file → ableton_live .als (MIDI clip on track)
rco energy curve → ableton_live arrangement (automation data)
psbs layer config → serum2 filter bands → ableton_live rack chain zones
```
None of this pipeline exists today. Each module writes its own JSON and moves on.

---

## 5. EXTERNAL DEPENDENCIES REALITY CHECK

### Python dependencies (pyproject.toml):
| Package | Version | Used By | Status |
|---|---|---|---|
| numpy ≥ 1.24 | Required | phi_core, growl_resampler, psbs | ✅ Essential — real DSP |
| pyyaml ≥ 6.0 | Required | config_loader | ✅ Essential — config loading (has fallback parser) |
| matplotlib | Optional | rco (plot_curve only) | ⚠️ Not installed = no PNG charts |
| pytest ≥ 7 | Dev | tests | ✅ Works |
| ruff | Dev | linting | ✅ Works, 0 errors |

### External software required (not installable via pip):
| Software | Required For | Integration Level |
|---|---|---|
| **Serum / Serum 2** | Loading wavetables + using patch specs | WAV wavetables work. JSON specs are manual reference. |
| **Ableton Live** | Using session/arrangement templates | All output is JSON. No .als automation. |
| **Max for Live** | Running M4L control script | Script is valid Python but needs manual M4L device creation. |

### What the codebase claims vs reality:
- **"Serum 2-ready"** → True for wavetables (.wav). False for presets (no .fxp).
- **"Ableton integration"** → False. JSON templates ≠ Ableton projects.
- **"Full production pipeline"** → False. The pipeline produces specifications, not a playable track.
- **"432 Hz tuning"** → True in the math. `A4_432 = 432.0` is used consistently in frequency calculations.

---

## 6. TEST COVERAGE ASSESSMENT

### Quantitative:
- **209 tests**, all passing
- **14 test files** (one per engine module + conftest.py)
- Tests run in **0.16 seconds** (no I/O-heavy tests)
- Python 3.14.3, pytest 9.0.2

### Per-module breakdown:
| Module | Test File | Test Count | Coverage Quality |
|---|---|---|---|
| ableton_live | test_ableton_live.py (278 lines) | 41 | ★★★★ Good — tests enums, dataclasses, clips, templates, M4L script |
| serum2 | test_serum2.py (267 lines) | 37 | ★★★★ Good — tests constants, enums, dataclasses, phi helpers, patch builder |
| dojo | test_dojo.py (203 lines) | 33 | ★★★☆ Adequate — tests data structures and builders, but it's testing static data |
| sb_analyzer | test_sb_analyzer.py (165 lines) | 17 | ★★★☆ Adequate — tests corpus loading, analysis, VIP deltas |
| phi_core | test_phi_core.py | 16 | ★★★☆ Adequate — tests freq math, harmonic series, wavetable generation |
| trance_arp | test_trance_arp.py (127 lines) | 16 | ★★★★ Good — tests all 3 patterns + MIDI data conversion |
| config_loader | test_config_loader.py | 15 | ★★★★ Good — tests constants, loading, validation, error cases |
| rco | test_rco.py | 10 | ★★★☆ Adequate — tests curves, presets, energy curve generation |
| memory | test_memory.py | 8 | ★★☆☆ Light — tests phi scoring and basic lifecycle. Missing: asset registry, recall, evolution, milestones |
| growl_resampler | test_growl_resampler.py | 6 | ★★☆☆ Light — tests individual DSP steps + source generators. Missing: full pipeline test, output file verification |
| psbs | test_psbs.py | 6 | ★★☆☆ Light — tests crossovers, presets, coherence. Missing: render_psbs_cycle() test |
| chord_progression | test_chord_progression.py | 4 | ★☆☆☆ Minimal — tests build_chord, presets dict. Missing: individual preset tests, progression builder, MIDI sequence, phi voice spread |

### What's NOT tested:
1. **No integration tests** — no test runs `run_all.py` end-to-end.
2. **No output file validation** — no test checks that WAV files are valid audio.
3. **chord_progression.py has the worst test coverage** — 810-line module with only 4 tests. The 11 presets, `build_progression()`, `phi_voice_spread()`, `fibonacci_harmonic_rhythm()`, and `progression_to_midi_sequence()` are untested.
4. **memory.py** recall system, evolution tracking, and milestone checking are untested.
5. **No edge case tests** — empty inputs, invalid configs, disk full, etc.
6. **No performance tests** — wavetable generation timing, large corpus analysis.

### Test quality assessment:
Tests are well-structured (unittest.TestCase classes with descriptive names), fast, and deterministic. They test the right things at the unit level. But they're shallow — they verify that functions return the right types and shapes, not that the musical/DSP output is correct. No test verifies that a generated chord progression sounds correct or that a wavetable has the expected harmonic content.

---

## 7. PATH TO FIRST TRACK

### What you can do RIGHT NOW with current output:

1. **Drag wavetables into Serum** — Load DUBFORGE_PHI_CORE.wav, DUBFORGE_PHI_CORE_v2_WOOK.wav, DUBFORGE_GROWL_SAW.wav, DUBFORGE_GROWL_FM.wav as Serum oscillator wavetables. This works today with zero additional effort.

2. **Read JSON specs while building** — Open chord_progression JSONs for note/chord reference. Open RCO energy curve JSONs to plan arrangement structure. Open PSBS JSONs for frequency band reference. Open Serum2 patch JSONs to manually configure Serum patches.

3. **Paste M4L script** — Copy dubforge_m4l_setup.py content into a Max for Live device's Python environment to auto-create tracks and device chains.

### What's needed to go from "specification engine" to "track production tool":

#### Tier 1 — Highest impact, lowest effort:
| Task | Effort | Impact |
|---|---|---|
| **Wire `render_psbs_cycle()` to `write_wav()`** | 1 hour | 5th wavetable — the PSBS render already works, just needs file output |
| **Add `mido` MIDI file export** | 2–4 hours | chord_progression + trance_arp → .mid files you drag into Ableton |
| **Install matplotlib by default** | 5 min | RCO energy curve PNGs for arrangement reference |

#### Tier 2 — Medium effort, high impact:
| Task | Effort | Impact |
|---|---|---|
| **Serum .fxp export** | 1–2 weeks | 8 loadable Serum presets instead of JSON specs. Requires reverse-engineering .fxp binary format. |
| **Cross-module data flow** | 1 week | RCO curves → arrangement automation, chord progressions → MIDI clips in arrangement template |
| **Real audio analysis in sb_analyzer** | 1 week | Actual BPM detection, key detection, spectral analysis using librosa or essentia |

#### Tier 3 — Significant effort, transformative impact:
| Task | Effort | Impact |
|---|---|---|
| **Ableton .als generation** | 2–4 weeks | Full project file output. The .als format is gzipped XML — complex but documented by the community. |
| **Real-time wavetable morphing** | 2 weeks | Generate wavetable animation sequences, not just static tables |
| **Audio rendering** | 2 weeks | Use scipy or pydub to render full audio clips from MIDI + wavetable specs |

### Realistic "first track" workflow today:

1. Run `python3 run_all.py`
2. Open Ableton Live, create 10 tracks manually (reference session_dubforge_dubstep_weapon.json)
3. Load DUBFORGE wavetables into Serum on mid-bass track
4. Manually configure Serum patch (reference serum2_dubstep_patches.json)
5. Read chord_progression_WEAPON_DARK.json, manually input MIDI notes
6. Reference RCO energy curves for arrangement structure (or add matplotlib for PNG charts)
7. Set up PSBS-style frequency splitting manually (reference psbs_psbs_weapon.json)
8. Produce the track through normal Ableton workflow

**Estimated time from `run_all.py` to playable track: 4–8 hours of manual DAW work.** DUBFORGE accelerates the planning/design phase but doesn't eliminate any of the production execution.

---

## APPENDIX: FILE INVENTORY

### Source code (10,761 lines):
```
engine/serum2.py            1,584 lines
engine/ableton_live.py      1,561 lines
engine/dojo.py              1,465 lines
engine/memory.py            1,008 lines
engine/chord_progression.py   810 lines
engine/sb_analyzer.py         528 lines
engine/psbs.py                373 lines
engine/rco.py                 341 lines
engine/config_loader.py       307 lines
engine/growl_resampler.py     287 lines
engine/__init__.py            256 lines
engine/phi_core.py            231 lines
engine/trance_arp.py          216 lines
engine/log.py                  30 lines
run_all.py                    267 lines
```

### Config files (5):
```
configs/rco_psbs_vip_delta_v1.1.yaml    284 lines — RCO profiles, PSBS presets, VIP delta config
configs/serum2_module_pack_v1.yaml      241 lines — 5 Serum module configs
configs/fibonacci_blueprint_pack_v1.yaml ~160 lines — 3 track blueprints (weapon/emotive/hybrid)
configs/sb_corpus_v1.yaml               ~140 lines — Subtronics discography metadata
configs/memory_v1.yaml                  ~100 lines — Memory system config
```

### Output files (91 total):
```
4   .wav  wavetables   (output/wavetables/)
86  .json analysis/specs (output/analysis/, serum2/, ableton/, dojo/, memory/)
1   .py   M4L script     (output/ableton/dubforge_m4l_setup.py)
```

### Pipeline status: 29 sessions run, Purple Belt, 306 registered assets.

---

*This audit was generated by reading every line of every source file, running the full test suite (209/209 pass), executing the full pipeline, and inspecting all output artifacts.*
