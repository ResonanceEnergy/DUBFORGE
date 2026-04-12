# Phase 1: GENERATION — Module Map

> v4.2.1 — Code-audited truth. Every entry verified against `phase_one.py` imports and call sites.

Only modules with confirmed call sites in `run_phase_one()` are listed.
Modules that exist in `engine/` but are never imported or called in Phase 1 are in the **Dead / Unwired** section at the bottom.

---

## Stage 1: IDENTITY (1A–1D)

| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 1 | `variation_engine.py` | 1B | `VariationEngine().forge_dna()` in `_oracle()` | SongDNA, beat_s, bar_s, SCALE_INTERVALS, NOTES |
| 2 | `recipe_book.py` | 1D | `rb_select_recipe(style, mood)` | 29 recipes, quality targets, Fib checkpoints |

Steps 1A, 1C (`_design_palette_intent`) and 1D (`_extract_sections`, `_build_recipes`) are **inline functions** — no external engine modules.

> **Note:** `mood_engine.py` is NOT called. Mood resolution happens inside `variation_engine._resolve_mood()`.
> **Note:** Step 1A has a code comment referencing `config_loader` constants (PHI, FIBONACCI, A4_432), but `PHI` is not used until Stage 4 (L1951), and `FIBONACCI`/`A4_432` are **never imported**. `config_loader.py` is a Stage 4 module.

---

## Stage 2: STRUCTURE (2A–2D)

| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 1 | `rco.py` | 2B | `subtronics_weapon/emotive/hybrid_preset(bpm)` | RCOProfile — energy curve + LP filter narrative |

Steps 2A, 2C, 2D are **inline functions**:
- 2A: `_build_arrangement_from_dna(dna)` — builds ArrangementTemplate from `dna.arrangement` sections (uses `ArrangementTemplate`/`SectionDef` types from `arrangement_sequencer.py` but calls no functions from it)
- 2C: `_sections_from_arrangement()` — pure Python dict collapse
- 2D: `_build_audio_manifest()` — enumerates expected bounce targets

> **Note:** `arrangement_sequencer.py` provides type imports only (`ArrangementTemplate`, `SectionDef`). No builder functions are called. `song_templates.py` is dead — never imported.

---

## Stage 3: HARMONIC BLUEPRINT (3A–3C + pre-S4)

| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 1 | `chord_progression.py` | 3A | `ALL_PRESETS[preset]()` in `_build_chord_progression()` | 11 presets, 22 chord qualities (`build_progression` is imported but never called — dead import) |
| 2 | `variation_engine.py` | 3B | `SCALE_INTERVALS` in `_build_freq_table()` | 5-octave freq lookup |
| 3 | `sample_library.py` | pre-S4 | `SampleLibrary().list_category()` in `_collect_fx_samples()` | Galactia FX (risers, impacts, sweeps, etc.) |

Steps 3B, 3C are **inline functions**:
- 3B: `_build_freq_table(dna)` — math using `SCALE_INTERVALS`
- 3C: `_configure_stem_specs()` → `_generate_midi_sequences()` — uses `ALSMidiNote` type from `als_generator.py` + `NOTES` from `variation_engine.py`

> **Note:** `markov_melody.py` is NOT called in Stage 3. It's called in 4G `_sketch_melody()`. `galatcia.py` is NOT called in pre-S4 — FX comes from `sample_library.py`.

---

## Stage 4: SYNTH FACTORY (4A–4K)
### Constants
| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------||
| 0 | `config_loader.py` | S4 | Module-level import (L60): `PHI` | PHI constant — first use at L1951 in 4B wavetable generation |
### Wavetable Pipeline (4A–4B, 4E)
| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 1 | `galatcia.py` | 4A | `catalog_galatcia()`, `read_wavetable_frames()` | Galactia wavetable intake |
| 2 | `phi_core.py` | 4A/4B | `generate_phi_core_v1()` (4A fallback), `phi_harmonic_series/generate_frame/amplitude_curve/morph_frames` (4B) | PHI CORE wavetables |
| 3 | `wavetable_pack.py` | 4B | `generate_fm_ratio_sweep/harmonic_sweep/growl_vowel_pack/morph_pack()` | DNA-driven WT packs |
| 4 | `growl_resampler.py` | 4B/4G | `growl_resample_pipeline()` (4B), `generate_fm_source()` (4G growl) | Growl resampling pipeline |
| 5 | `wavetable_morph.py` | 4E | `MorphPreset`, `morph_wavetable()` | 5 morph types |

### Modulation + FX Design (4C–4D)
| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 6 | `serum2.py` | 4C | `ModulationRoute` constructed per stem group | Serum 2 data model |
| 7 | `lfo_matrix.py` | 4C | `LFOPreset` constructed per stem group | LFO presets, BPM-sync |
| 8 | `saturation.py` | 4D/4G/5C | `SatConfig` (4D), `SaturationEngine().saturate()` (4G bass, 5C drums) | 7 saturation types |
| 9 | `sidechain.py` | 4D | `SidechainPreset` constructed | 5 sidechain shapes |
| 10 | `stereo_imager.py` | 4D | `StereoPreset` constructed | 5 stereo imaging types |
| 11 | `reverb_delay.py` | 4D | `ReverbDelayPreset` constructed | 5 reverb/delay types |
| 12 | `wave_folder.py` | 4D | `WaveFolderPatch` constructed (bass only) | 5 wave-folder algos |
| 13 | `pitch_automation.py` | 4D | `PitchAutoPreset` constructed (bass + fx) | 5 pitch auto types |

### Serum 2 Presets (4F, 4H+)
| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 14 | `serum2_preset.py` | 4F/4H+ | `s2_build_all_presets()`, `s2_get_preset_state_map()`, `SerumPreset` | Preset build + VST3 state serialization |

> **Note:** `_captured_serum2_state.py` is consumed internally by `serum2_preset.py` — not imported directly in `phase_one.py`.

### Audio Rendering — 4G Sketch Functions

#### Bass — `_sketch_bass()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 15 | `bass_oneshot.py` | `synthesize_sub_sine()`, `synthesize_reese()`, `synthesize_fm_bass()`, `BassPreset` | Sub/reese/FM bass one-shots |
| 16 | `fm_synth.py` | `render_fm_patch()`, `FMPatch` (fallback if bass_oneshot.synthesize_fm_bass unavailable) | FM synthesis fallback |

#### Leads — `_sketch_leads()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 17 | `lead_synth.py` | `synthesize_screech_lead()`, `synthesize_pluck_lead()`, `synthesize_fm_lead()`, `LeadPreset` | Screech/pluck/FM leads |

#### Melody — `_sketch_melody()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 18 | `markov_melody.py` | `MarkovMelody().generate()`, `render_melody()` | Markov chain melody |
| 19 | `arp_synth.py` | `synthesize_arp()`, `ArpSynthPreset` | 3–4 Fibonacci arp patterns |

#### Atmosphere — `_sketch_atmosphere()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 20 | `pad_synth.py` | `synthesize_dark_pad()`, `synthesize_lush_pad()`, `PadPreset` | Dark + lush pads |
| 21 | `drone_synth.py` | `synthesize_drone()`, `DronePreset` | Multi-voice drones |
| 22 | `noise_generator.py` | `synthesize_noise()`, `NoisePreset` | White/pink/brown noise beds |

#### FX — `_sketch_fx()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 23 | `riser_synth.py` | `synthesize_noise_sweep()`, `synthesize_pitch_rise()`, `RiserPreset` | Risers |
| 24 | `impact_hit.py` | `synthesize_sub_boom()`, `synthesize_reverse_hit()`, `ImpactPreset` | Sub boom + reverse hits |
| 25 | `transition_fx.py` | `synthesize_tape_stop()`, `synthesize_gate_chop()`, `synthesize_pitch_dive()`, `TransitionPreset` | Tape stop / gate chop / pitch dive |
| 26 | `glitch_engine.py` | `synthesize_stutter()`, `GlitchPreset` | Stutter effects |

#### Vocals — `_sketch_vocals()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 27 | `vocal_chop.py` | `synthesize_chop()`, `VocalChop` | Vowel chop synthesis |

#### Wobble — `_sketch_wobble_bass()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 28 | `wobble_bass.py` | `synthesize_wobble()`, `WobblePreset` | 4 wobble types (classic/slow/fast/vowel) |

#### Riddim — `_sketch_riddim_bass()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 29 | `riddim_engine.py` | `generate_riddim()`, `RiddimPreset` | 4 riddim variants (minimal/heavy/bounce/stutter) |

#### Growl — `_sketch_growl_textures()`
| # | Module | Call Site | Purpose |
|---|--------|-----------|---------|
| 30 | `growl_resampler.py` | `generate_fm_source()`, `growl_resample_pipeline()` | (also listed in 4B — shared module) |

### ALS + Bounce (4I–4K)
| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 31 | `als_generator.py` | 4I/4K | `_ALSProject`, `_ALSTrack`, `_write_als()`, `ALSMidiClip`, `ALSMidiNote` | ALS file generation |
| 32 | `ableton_bridge.py` | 4J | `AbletonBridge().connect()/.disconnect()` | OSC bridge for auto-bounce |

---

## Stage 5: DRUM FACTORY (5A–5G)

| # | Module | Step | Call Site | Purpose |
|---|--------|------|-----------|---------|
| 1 | `sample_library.py` | 5A | `SampleLibrary().list_category()` — kick, snare, hat, clap, crash, ride, perc | Drum sample collection |
| 2 | `galatcia.py` | 5B+ | `map_galactia_to_zones()` → `GalactiaZoneMap` | Zone mapping for empty rack slots |
| 3 | `dynamics.py` | 5C | `compress()`, `CompressorSettings` in `_process_drum()` | Drum compression |
| 4 | `saturation.py` | 5C | `SaturationEngine().saturate()` in `_process_drum()` | Drum saturation (shared with 4D/4G) |
| 5 | `intelligent_eq.py` | 5C | `apply_eq_band()` for kick/hat EQ | Drum EQ |
| 6 | `als_generator.py` | 5G | `_ALSProject`, `_ALSTrack`, `_ALSDrumPad`, `_write_als()` | Stage 5 ALS (shared with 4I) |
| 7 | `ableton_bridge.py` | 5G | `AbletonBridge()` in `_bounce_stage5_patterns()` | Stage 5 bounce (shared with 4J) |

Steps 5D, 5E, 5F are **inline functions**:
- 5D: `_build_128_rack()` — all rack logic inline (`_rack_add`, `_ZONE_RANGES`, `_ZONE_IDX`, `_ZONE_MAX`)
- 5E: `_build_drum_loops()` + `_build_loop_midi_maps()` — numpy audio mixing
- 5F: Pattern Factory — section × zone_group patterns, all inline

---

## Dead / Unwired Modules

### Dead Imports from Wired Modules

These functions/classes are imported but never called in `phase_one.py`:

| Import | From Module | Why Dead |
|--------|------------|----------|
| `build_progression` | `chord_progression.py` | Only `ALL_PRESETS[preset]()` is called in S3A |
| `dojo_narrative_preset` | `rco.py` | Not in S2B style→preset map |
| `RecipeBook` | `recipe_book.py` | Only `rb_select_recipe` (aliased `select_recipe`) is called |
| `RCOProfile` | `rco.py` | Type never referenced directly — preset functions return it |
| `BassDNA`, `DrumDNA`, `FxDNA`, `LeadDNA`, `MixDNA`, `AtmosphereDNA` | `variation_engine.py` | Accessed via `dna.bass`, `dna.drums` attributes — explicit imports unused |

### Dead Modules

These modules exist in `engine/` but have **zero call sites** in `phase_one.py`:

| Module | Expected Stage | Why Dead |
|--------|---------------|----------|
| `mood_engine.py` | S1 | Mood resolved inside `variation_engine._resolve_mood()` |
| `song_templates.py` | S2 | Never imported — arrangement built from `dna.arrangement` |
| `sub_bass.py` | S4 bass | Sub bass comes from `bass_oneshot.synthesize_sub_sine()` |
| `pluck_synth.py` | S4 leads | Plucks come from `lead_synth.synthesize_pluck_lead()` |
| `supersaw.py` | S4 leads | Supersaw is MIDI-only — no audio render module called |
| `additive_synth.py` | S4 leads | Not imported or referenced |
| `formant_synth.py` | S4 vocals | Not imported — vocal chops come from `vocal_chop.py` |
| `ambient_texture.py` | S4 atmos | Not imported or referenced |
| `granular_synth.py` | S4 atmos | Not imported or referenced |
| `beat_repeat.py` | S4 fx | Not imported or referenced |
| `chord_pad.py` | S4 leads | Not imported or referenced |
| `drum_generator.py` | S5 | Not imported — drums come from `sample_library.py` |
| `drum_pipeline.py` | S5 | Not imported — processing done inline in `_process_drum()` |
| `dojo.py` | S5 | Rack logic reimplemented inline in `_build_128_rack()` |
| `rhythm_engine.py` | S5 | Not imported — patterns generated inline in `run_phase_one()` |
| `ableton_rack_builder.py` | S5 | Not imported or referenced |
| `_captured_serum2_state.py` | S4 | Internal to `serum2_preset.py` — not imported in `phase_one.py` |

---

## Module Count Summary

| Stage | Wired Modules | Inline Steps | Total |
|-------|--------------|-------------|-------|
| 1. IDENTITY | 2 | 3 (1A, 1C, 1D) | 2 |
| 2. STRUCTURE | 1 | 3 (2A, 2C, 2D) | 1 |
| 3. HARMONIC BLUEPRINT | 3 | 2 (3B, 3C) | 3 |
| 4. SYNTH FACTORY | 28 (unique) | — | 28 |
| 5. DRUM FACTORY | 5 (unique) + 2 shared | 3 (5D, 5E, 5F) | 5 |
| **Total unique** | **36** | **10** | **36** |

> 4 modules are shared across stages: `saturation.py` (4D/4G/5C), `als_generator.py` (4I/4K/5G), `ableton_bridge.py` (4J/5G), `growl_resampler.py` (4B/4G). `variation_engine.py` is shared S1/S3. `sample_library.py` is shared pre-S4/5A. Counting unique modules only = **36**.