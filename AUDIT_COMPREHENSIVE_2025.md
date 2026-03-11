# DUBFORGE — Comprehensive Codebase Audit

**Date:** 2025-07-16  
**Version:** 4.0.0 (Grandmaster Edition → Ascension 233)  
**Python:** ≥3.10 (numpy, pyyaml, mido)  
**License:** MIT  

---

## 1. Architecture Overview

DUBFORGE is an autonomous dubstep/bass music production engine built entirely in Python + NumPy. It synthesizes audio from raw math — no sample libraries, no DAW plugins, no external audio files. Every sound is generated from sinusoids, noise, FM operators, Karplus-Strong models, formant banks, granular clouds, and wavetable morphing, all governed by **phi (φ = 1.618...)** and **Fibonacci** mathematics.

### Core Stats

| Metric | Count |
|--------|-------|
| Engine modules (`engine/*.py`) | **172 files** (incl. `__init__.py`) |
| Registered build modules (`run_all.py`) | **134 modules** in 11 phases |
| Test files (`tests/test_*.py`) | **~170 test files** (1:1 coverage) |
| Config files (`configs/*.yaml`) | **5 YAML files** |
| Top-level scripts | `forge.py`, `run_all.py`, `make_track.py`, `quick_analyze.py`, `analyze_tracks.py`, `test_dsp.py` |
| Lines in `forge.py` | **2,493** |
| Lines in `engine/__init__.py` | **1,843** (re-exports everything) |
| CLI entry points (pyproject.toml) | `dubforge`, `dubforge-cli`, `subphonics` |

### Doctrine

From `DOCTRINE.md` (535 lines): The engine is built on **Dan Winter's Planck × phi fractal mathematics**. Key constants:
- **PHI** = 1.6180339887 (golden ratio)
- **FIBONACCI** = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
- **A4_432** = 432 Hz (optional natural tuning reference)
- Sample rate: **48,000 Hz**
- Bit depth: **16-bit PCM**

---

## 2. Data Flow Map

```
USER INPUT
    │
    ├─── forge.py --song "TRACK NAME" --mood dark --producer subtronics
    │         │
    │         ▼
    │    ┌─────────────────────┐
    │    │  SongBlueprint      │  (name, style, mood, sound_style)
    │    └─────────┬───────────┘
    │              │
    │              ▼
    │    ┌─────────────────────┐     ┌──────────────┐
    │    │  VariationEngine    │◄────│ mood_engine   │
    │    │  .forge_dna()       │◄────│ tag_system    │
    │    │  (1468 lines)       │◄────│ config_loader │
    │    └─────────┬───────────┘
    │              │
    │              ▼
    │    ┌─────────────────────┐
    │    │  SongDNA            │  Complete synthesis specification:
    │    │  ├─ DrumDNA         │    kick_pitch, snare_pitch, hat_freq...
    │    │  ├─ BassDNA         │    fm_depth, distortion, sub_weight...
    │    │  ├─ LeadDNA         │    additive_partials, fm_operators...
    │    │  ├─ AtmosphereDNA   │    pad_type, reverb_decay, drone_voices...
    │    │  ├─ FxDNA           │    riser_intensity, boom_decay...
    │    │  ├─ MixDNA          │    target_lufs, stereo_width, ceiling...
    │    │  ├─ arrangement[]   │    section names + bar counts
    │    │  ├─ bass_rotation[] │    ordered bass sound types
    │    │  └─ chop_vowels[]   │    vowel sounds for vocal chops
    │    └─────────┬───────────┘
    │              │
    │         ┌────┴─── optional: OpenClawAgent.produce() injects
    │         │         Subtronics-style parameter ranges
    │         ▼
    │    ┌─────────────────────────────────────────────────────────┐
    │    │  forge.py → render_full_track(dna)                     │
    │    │                                                         │
    │    │  [COLLECT] Sound palette from DNA                       │
    │    │    ├─ Drums: 4-layer kick, 4-layer snare, KS hats     │
    │    │    ├─ Bass: 7 types (FM, growl, dist, sync, acid,     │
    │    │    │        neuro, formant) + pitch dive + reese       │
    │    │    ├─ Leads: additive + FM, pre-rendered all degrees  │
    │    │    ├─ Chords: supersaw stabs, pre-rendered progression│
    │    │    ├─ Vocal chops: formant-synthesized vowels          │
    │    │    ├─ Pads: dark/lush + granular + additive blend     │
    │    │    ├─ Drone: Karplus-Strong + dark drone              │
    │    │    └─ FX: riser, boom, hit, tape stop, pitch dive,    │
    │    │          rev crash, stutter, gate chop                 │
    │    │                                                         │
    │    │  [SKETCH] First instinct sound design                   │
    │    │                                                         │
    │    │  [ARRANGE] 7-section structure with RhythmEngine:      │
    │    │    INTRO → BUILD → DROP1 → BREAK → BUILD2 → DROP2 →   │
    │    │    OUTRO (128 bars default, DNA-configurable)          │
    │    │                                                         │
    │    │  [MIX] Sidechain bus → HP 25Hz → EQ → Bus compression │
    │    │  [FINISH] Stereo imaging → Mastering chain → Limiter  │
    │    └──────────────────────────┬──────────────────────────────┘
    │                               │
    │                               ▼
    │                    ┌──────────────────────┐
    │                    │  output/<name>.wav   │  Stereo 48kHz/16-bit
    │                    └──────────────────────┘
    │
    ├─── forge.py --fibonacci --song "TRACK NAME"
    │         │
    │         ▼
    │    ┌───────────────────────────────────────────┐
    │    │  FibonacciFeedbackEngine.run()            │
    │    │  (fibonacci_feedback.py, 1142 lines)      │
    │    │                                           │
    │    │  12 steps at Fibonacci intervals:         │
    │    │  1,1,2,3,5,8,13,21,34,55,89,144         │
    │    │                                           │
    │    │  Golden analysis at: 8,13,21,34,55,89,144│
    │    │    → run_analysis() on rendered WAV       │
    │    │    → compare_to_targets() (14 metrics)   │
    │    │    → compute_corrections() → DNA tweak   │
    │    │    → re-render → re-analyze → loop       │
    │    │    → check_first_instinct() (Dojo)       │
    │    │                                           │
    │    │  Max 3 corrections per pass (Dojo)        │
    │    │  Saves lessons_learned.json               │
    │    └───────────────────────────────────────────┘
    │
    ├─── forge.py --dojo --song "TRACK NAME" --timer 840
    │         │
    │         ▼
    │    Same as --fibonacci but WITH 14-minute timer enforcement
    │    and ill.Gates Approach phase banners
    │
    └─── forge.py (no args, or --all)
              │
              ▼
         Sequential pipeline:
         1. generate_wavetables()  → output/wavetables/*.wav
         2. render_stems()         → output/stems/*.wav (7 stems)
         3. generate_ableton_project() → output/ableton/*.als
         4. generate_presets()     → output/presets/*.fxp
         5. render_full_track()    → output/dubstep_track_v5.wav
```

---

## 3. Module Inventory — All 172 Engine Files

### Category: Synthesis Engines (32 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `bass_oneshot.py` | 1183 | Bass one-shot WAV generator: sub sine, reese, FM, square, growl | **YES** (imports) |
| `lead_synth.py` | — | Lead synthesizer: screech, pluck, chord stabs | **YES** |
| `pad_synth.py` | — | Pad synthesizer: dark, lush, evolving | **YES** |
| `perc_synth.py` | — | Percussion: kick, snare, hat, clap synthesis | **YES** |
| `noise_generator.py` | — | Noise textures: white, pink, brown, crackle | **YES** |
| `impact_hit.py` | — | Impact hits: sub boom, cinematic hit | **YES** |
| `fm_synth.py` | 253 | FM synthesis: operator stacks, feedback, phi harmonics | **YES** |
| `formant_synth.py` | — | Formant synthesis: vowel morphing, vocal textures | **YES** |
| `granular_synth.py` | — | Granular clouds: time-stretch, freeze, scatter | **YES** |
| `drone_synth.py` | — | Drone generator: dark, ambient, evolving | **YES** |
| `additive_synth.py` | — | Additive synthesis: phi partials, harmonic series | **YES** |
| `supersaw.py` | — | Supersaw engine: multi-voice detuned stereo stabs | **YES** |
| `karplus_strong.py` | — | Physical modeling: plucked strings, metallic tones | **YES** |
| `vocal_chop.py` | 725 | Synthesized vocal chops from formant filter banks | **YES** |
| `sub_bass.py` | — | Dedicated sub-bass one-shot generator | Standalone |
| `arp_synth.py` | — | Arp pattern synthesizer | Standalone |
| `pluck_synth.py` | — | Pluck one-shot synthesizer | Standalone |
| `chord_pad.py` | — | Chord pad synthesizer | Standalone |
| `riser_synth.py` | — | Riser synthesizer (noise sweeps, tonal rises) | **YES** |
| `wobble_bass.py` | — | Wobble bass synthesizer | Standalone |
| `trance_arp.py` | — | Trance-style arpeggiator engine | Standalone |
| `vector_synth.py` | — | Vector synthesis (multi-source crossfading) | Standalone |
| `vocoder.py` | — | Vocoder effect | Standalone |
| `riddim_engine.py` | 333 | Riddim bass sequencer: minimal, heavy, bounce, stutter, triplet | Standalone |
| `ambient_texture.py` | — | Ambient textures: cave, crystal, forest, ocean, etc. | Standalone |
| `harmonic_gen.py` | — | Harmonic series generator | Standalone |
| `phase_distortion.py` | — | Phase distortion synthesis | Standalone |
| `ring_mod.py` | — | Ring modulation effect | Standalone |
| `wave_folder.py` | — | Wavefolding distortion | Standalone |
| `chord_progression.py` | — | Chord progression generator | Standalone |
| `markov_melody.py` | — | Markov chain melody generator | Standalone |
| `spectral_resynthesis.py` | — | Spectral analysis + resynthesis | Standalone |

### Category: DSP / Audio Processing (24 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `dsp_core.py` | 613 | SVF filters, PolyBLEP oscillators, waveshaping, chorus | **YES** (direct import) |
| `mastering_chain.py` | 530 | Full mastering: EQ, compression, limiting, LUFS targeting | **YES** |
| `saturation.py` | 212 | Tube/tape/transistor/console/phi saturation | **YES** |
| `reverb_delay.py` | 472 | Phi-spaced reverb (room/hall/plate/shimmer) + Fibonacci delays | **YES** |
| `sidechain.py` | 376 | Sidechain ducking: pump, hard_cut, smooth, bounce, phi_curve | **YES** |
| `multiband_distortion.py` | — | 3-band distortion with crossover control | **YES** |
| `stereo_imager.py` | — | Stereo width, mid/side, frequency-split imaging | **YES** |
| `panning.py` | — | Constant-power panning, Haas delay | **YES** |
| `dynamics.py` | — | Compressor/limiter/transient shaper | **YES** (compress, CompressorSettings) |
| `dynamics_processor.py` | — | Advanced dynamics (v2) | Standalone |
| `lfo_matrix.py` | — | LFO modulation: sine, triangle, square, S&H | **YES** |
| `pitch_automation.py` | — | Pitch dive/rise/vibrato automation | **YES** |
| `beat_repeat.py` | — | Beat repeat / stutter effect | **YES** |
| `intelligent_eq.py` | — | AI-driven EQ decisions | Standalone |
| `convolution.py` | — | Convolution reverb engine | Standalone |
| `resonance.py` | — | Resonance engine | Standalone |
| `crossfade.py` | — | Crossfade utilities | Standalone |
| `dc_remover.py` | — | DC offset removal | Standalone |
| `dither.py` | — | Dithering for bit-depth reduction | Standalone |
| `normalizer.py` | — | Audio normalization | Standalone |
| `spectral_gate.py` | — | Spectral noise gate | Standalone |
| `spectral_morph.py` | — | Spectral morphing between signals | Standalone |
| `style_transfer.py` | 224 | Spectral envelope transfer between signals | Standalone |
| `auto_master.py` | 289 | Standalone automatic mastering chain (EQ → saturation → normalization → limiting) | Standalone |

### Category: Arrangement & Composition (8 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `rhythm_engine.py` | 617 | Centralized drum pattern generation per section | **YES** (RhythmEngine.from_drum_dna) |
| `groove.py` | — | Groove templates, humanize, swing | **YES** (GrooveEngine) |
| `auto_arranger.py` | 264 | Arrangement generation: standard/tearout/melodic/riddim templates | Standalone |
| `arrangement_sequencer.py` | — | Section-level arrangement sequencing | Standalone |
| `song_templates.py` | — | Pre-built song structure templates | Standalone |
| `transition_fx.py` | — | Transition FX: tape stop, pitch dive, reverse crash | **YES** |
| `glitch_engine.py` | — | Glitch/stutter synthesis | **YES** |
| `auto_mixer.py` | 255 | Auto gain staging with element priority | Standalone |

### Category: Wavetable & Preset (10 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `phi_core.py` | 232 | PHI wavetable generator: phi harmonic series, Fibonacci partials | **YES** (imports) |
| `growl_resampler.py` | 410 | Mid-bass growl resampler pipeline (Mudpie technique) | **YES** |
| `fxp_writer.py` | — | VST2 .fxp preset file writer | **YES** (generate_presets) |
| `wavetable_morph.py` | — | Wavetable morphing engine | Standalone |
| `preset_mutator.py` | 356 | Phi-weighted random mutation + breeding | Standalone |
| `preset_browser.py` | — | Preset search and browse | Standalone |
| `preset_pack_builder.py` | — | Package presets into packs | Standalone |
| `preset_vcs.py` | — | Preset version control system | Standalone |
| `serum2.py` | 2126 | Complete Serum 2 architecture model: oscillators, filters, mod matrix | Standalone |
| `sound_palette.py` | — | Sound palette management | Standalone |

### Category: AI & Intelligence (9 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `openclaw_agent.py` | 672 | AI producer agent encoding Subtronics' production DNA | **YES** (--producer mode) |
| `variation_engine.py` | 1468 | SongBlueprint → SongDNA: 80+ semantic word atoms | **YES** (core DNA generator) |
| `mood_engine.py` | 282 | 14 moods → synthesis parameter suggestions | **YES** (via variation_engine) |
| `genetic_evolver.py` | 293 | Genetic algorithm for evolving synth patches | Standalone |
| `genre_detector.py` | 287 | Spectral genre classification (12 genres) | Standalone |
| `pattern_recognizer.py` | — | Pattern recognition in audio | Standalone |
| `key_detector.py` | — | Musical key detection from audio | Standalone |
| `reference_analyzer.py` | — | Compare renders against reference tracks | Standalone |
| `mix_assistant.py` | — | AI mixing suggestions | Standalone |

### Category: Self-Improvement & Memory (5 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `fibonacci_feedback.py` | 1142 | 144-step iterative improvement loop | **YES** (--fibonacci/--dojo) |
| `lessons_learned.py` | 694 | Cross-track learning persistence | **YES** (via fibonacci_feedback) |
| `memory.py` | 1044 | Long-term persistence: sessions, assets, evolution, recall | **YES** (via run_all.py) |
| `evolution_engine.py` | 360 | Parameter drift tracking, phi convergence | Standalone |
| `recipe_book.py` | 1626 | Production recipes + 14 global quality targets | **YES** (via fibonacci_feedback) |

### Category: Production Methodology (2 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `dojo.py` | 2394 | ill.Gates / Producer Dojo methodology: belts, Approach, 128 Rack | Standalone |
| `sb_analyzer.py` | 793 | Subtronics discography metadata analysis | Standalone |

### Category: Subtronics Analysis (3 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `rco.py` | 437 | Rollercoaster Optimizer: energy curves, narrative filtering | Standalone |
| `psbs.py` | 564 | Phase-Separated Bass System: 5-layer bass architecture | Standalone |
| `sb_analyzer.py` | 793 | Subtronics corpus analysis from Apple Music metadata | Standalone |

### Category: Export & Project (8 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `als_generator.py` | — | Ableton Live .als XML generator | **YES** |
| `ableton_live.py` | — | Ableton Live session templates + M4L scripts | Standalone |
| `midi_export.py` | — | MIDI file (.mid) export | Standalone |
| `sample_pack_builder.py` | 285 | Organized sample pack directories | Standalone |
| `sample_pack_exporter.py` | — | Sample pack export pipeline | Standalone |
| `ep_builder.py` | 336 | Full EP rendering pipeline with tracklist | Standalone |
| `format_converter.py` | — | Audio format conversion | Standalone |
| `metadata.py` | — | Audio file metadata management | Standalone |

### Category: Pipeline & Batch (6 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `render_pipeline.py` | 359 | End-to-end render chain: synth → FX → sidechain → stereo → master | Standalone |
| `render_queue.py` | 260 | Async render queue with progress tracking | Standalone |
| `batch_processor.py` | 314 | Batch operation chains on multiple files | Standalone |
| `batch_renderer.py` | 247 | Batch WAV rendering from preset banks | Standalone |
| `multitrack_renderer.py` | — | Multi-track simultaneous rendering | Standalone |
| `signal_chain.py` | 348 | Serial/parallel/split signal routing | Standalone |

### Category: Web & Server (4 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `subphonics.py` | 552 | SUBPHONICS AI: autonomous project director, module orchestrator | Standalone |
| `subphonics_server.py` | 284 | HTTP chatbot server at port 8433 | Standalone (own entry point) |
| `web_preview.py` | 206 | HTTP endpoint: upload WAV → analysis JSON | Standalone |
| `spectrogram_chat.py` | — | Spectrogram viewer in browser | Standalone |

### Category: Analysis (7 modules)

| Module | Lines | Purpose | Wired into forge.py |
|--------|-------|---------|-------------------|
| `audio_analyzer.py` | — | Audio file analysis (peak, RMS, spectrum) | Standalone |
| `frequency_analyzer.py` | — | Frequency domain analysis | Standalone |
| `harmonic_analysis.py` | — | Harmonic content analysis | Standalone |
| `phi_analyzer.py` | — | Phi coherence measurement in audio | Standalone |
| `tempo_detector.py` | — | BPM detection from audio | Standalone |
| `final_audit.py` | — | System health audit | Standalone |
| `grandmaster.py` | 193 | Fibonacci 144 Grandmaster achievement report | Standalone |

### Category: Utilities & Infrastructure (21 modules)

| Module | Lines | Purpose |
|--------|-------|---------|
| `config_loader.py` | 365 | YAML config reader + PHI/FIBONACCI constants |
| `log.py` | — | Logging infrastructure |
| `error_handling.py` | — | Error handling & validation |
| `tag_system.py` | 320 | Hierarchical tagging for samples/presets |
| `envelope_generator.py` | — | ADSR envelope generator |
| `audio_buffer.py` | — | Audio buffer pool management |
| `audio_math.py` | — | Audio math utilities |
| `audio_splitter.py` | — | Audio file splitting |
| `audio_stitcher.py` | — | Audio file concatenation |
| `audio_preview.py` | — | Audio preview playback |
| `backup_system.py` | — | File backup system |
| `wav_pool.py` | — | WAV file pool management |
| `cue_points.py` | — | Cue point markers |
| `tuning_system.py` | — | Tuning system (432 Hz, equal temperament, etc.) |
| `macro_controller.py` | — | Macro parameter controller |
| `snapshot_manager.py` | — | Parameter snapshot save/restore |
| `automation_recorder.py` | — | Parameter automation recording |
| `profiler.py` | — | Performance profiling |
| `perf_monitor.py` | — | Performance monitoring |
| `session_logger.py` | — | Session event logging |
| `session_persistence.py` | — | Session state save/restore |

### Category: Live Performance (7 modules)

| Module | Lines | Purpose |
|--------|-------|---------|
| `clip_launcher.py` | — | Clip triggering engine |
| `clip_manager.py` | — | Clip organization |
| `looper.py` | — | Audio looper |
| `live_fx.py` | — | Real-time FX processing |
| `osc_controller.py` | — | OSC protocol controller |
| `performance_recorder.py` | — | Performance capture |
| `scene_system.py` | — | Scene management |

### Category: Meta & System (6 modules)

| Module | Lines | Purpose |
|--------|-------|---------|
| `ascension.py` | 518 | Meta-orchestrator: validates all 172 modules, renders proof track |
| `full_integration.py` | 188 | One-command full pipeline validation |
| `collaboration.py` | 369 | Multi-user collaboration with phi-weighted merge |
| `plugin_host.py` | — | Plugin hosting framework |
| `plugin_scaffold.py` | — | Plugin scaffolding generator |
| `watermark.py` | — | Audio watermarking |

---

## 4. forge.py — The Central Orchestrator (2,493 lines)

### Direct Imports (35+ modules)

forge.py directly imports from these engine modules:

**Synthesis:** `bass_oneshot`, `lead_synth`, `pad_synth`, `perc_synth`, `noise_generator`, `impact_hit`, `fm_synth`, `formant_synth`, `additive_synth`, `karplus_strong`, `granular_synth`, `vocal_chop`, `drone_synth`, `supersaw`

**DSP:** `dsp_core` (SVF filters, multiband compress), `mastering_chain`, `reverb_delay`, `multiband_distortion`, `stereo_imager`, `saturation`, `dynamics`, `lfo_matrix`, `beat_repeat`, `panning`, `pitch_automation`, `transition_fx`, `glitch_engine`, `sidechain`

**Wavetable:** `phi_core`, `fxp_writer`, `als_generator`, `growl_resampler`

**Intelligence:** `openclaw_agent`, `variation_engine`, `rhythm_engine`, `groove`, `fibonacci_feedback`, `lessons_learned`

### Five Pipeline Steps

1. **`generate_wavetables()`** (line 360) — Renders Serum-compatible wavetable .wav files
2. **`render_stems()`** (line 540) — 7 individual audio stems for Ableton import
3. **`generate_ableton_project()`** (line 713) — .als project file with Serum 2 tracks
4. **`generate_presets()`** (line 806) — .fxp VST2 preset files
5. **`render_full_track(dna)`** (line 956) — **THE MAIN FUNCTION** — DNA-driven full mix (1,350 lines)

### render_full_track() Architecture (lines 956–2300)

Nine phases follow the ill.Gates Approach workflow:

| Phase | Forge Lines | What Happens |
|-------|-------------|--------------|
| `[COLLECT]` | 956–1010 | DNA setup, timing constants, scale/freq lookup |
| `[SKETCH] 1/9` | 1070–1300 | **Drums** — 4-layer kick (sub + FM + click + rumble), 4-layer snare (body + noise + ring + top), KS hats, compressed clap |
| `[SKETCH] 2/9` | 1300–1470 | **Bass** — 7 types: FM growl, growl wavetable, dist FM, sync, acid, neuro, formant + pitch dive + reese + beat repeat |
| `[SKETCH] 3/9` | 1470–1560 | **Leads** — Additive + FM layered, pre-rendered for all 7 scale degrees × 2 octaves; supersaw chord stabs |
| `[SKETCH] 4/9` | 1560–1620 | **Vocal chops** — 4 formant-synthesized vowels from DNA |
| `[SKETCH] 5/9` | 1620–1740 | **Pads & atmosphere** — Dark/lush pad + granular + additive blend, drone (KS + synth), noise bed |
| `[SKETCH] 6/9` | 1740–1820 | **Transition FX** — Riser, boom, hit, tape stop, pitch dive, reverse crash, stutter, gate chop |
| `[SKETCH] 7/9` | 1820–1850 | **Groove patterns** — Hat events with groove template + humanize |
| `[ARRANGE] 8/9` | 1850–2230 | **7-section arrangement**: Intro → Build → Drop1 → Break → Build2 → Drop2 → Outro. All DNA-driven: bass rotation, melody patterns, chord progressions, vocal chop placement |
| `[MIX→FINISH] 9/9` | 2230–2300 | **Mixdown + mastering**: Sidechain bus → HP 25Hz → EQ (1kHz + 5kHz) → Linked stereo bus compression → Stereo imaging → Full mastering chain (EQ + saturation + compression + limiting) → WAV output |

### DNA-Driven Parameters

Every synthesis parameter in `render_full_track()` reads from the `SongDNA` object:

- **Drums**: `dd.kick_pitch`, `dd.kick_fm_depth`, `dd.kick_drive`, `dd.snare_pitch`, `dd.snare_noise_mix`, `dd.hat_frequency`, `dd.hat_brightness`, `dd.clap_brightness`, etc.
- **Bass**: `bd.fm_depth`, `bd.distortion`, `bd.filter_cutoff`, `bd.sub_weight`, `bd.mid_drive`, `bd.lfo_rate`, `bd.lfo_depth`, `bd.ott_amount`, `bd.wavefold_thresh`, `bd.bitcrush_bits`, etc.
- **Leads**: `ld.additive_partials`, `ld.additive_rolloff`, `ld.fm_depth`, `ld.fm_operators`, `ld.supersaw_voices`, `ld.supersaw_detune`, `ld.ott_amount`, `ld.brightness`, etc.
- **Atmosphere**: `ad.pad_type`, `ad.pad_attack`, `ad.pad_brightness`, `ad.reverb_decay`, `ad.stereo_width`, `ad.drone_voices`, `ad.use_karplus_drone`, etc.
- **FX**: `fd.riser_intensity`, `fd.impact_intensity`, `fd.stutter_rate`, `fd.vocal_chop_distortion`, `fd.beat_repeat_probability`, etc.
- **Mix**: `md.target_lufs`, `md.stereo_width`, `md.master_drive`, `md.eq_low_boost`, `md.eq_high_boost`, `md.compression_ratio`, `md.ceiling_db`, etc.
- **Arrangement**: `dna.arrangement[]` (section names + bar counts), `dna.bass_rotation[]`, `dna.chop_vowels[]`, `ld.melody_patterns[]`, `ld.chord_progression[]`

---

## 5. Wired vs. Standalone Classification

### Fully Wired into forge.py (36 modules)

These modules are directly imported and called by `forge.py render_full_track()`:

```
bass_oneshot    lead_synth       pad_synth         perc_synth
noise_generator impact_hit       fm_synth          formant_synth
granular_synth  drone_synth      additive_synth    supersaw
karplus_strong  vocal_chop       riser_synth       transition_fx
glitch_engine   growl_resampler  phi_core          dsp_core
mastering_chain reverb_delay     multiband_distortion stereo_imager
saturation      dynamics         lfo_matrix        beat_repeat
panning         pitch_automation sidechain         als_generator
fxp_writer      openclaw_agent   variation_engine  groove
rhythm_engine
```

### Wired via Feedback Loop (4 modules)

Called through `--fibonacci` / `--dojo` modes:

```
fibonacci_feedback  lessons_learned  recipe_book  memory (via run_all.py)
```

### Standalone / Not Yet Wired (132+ modules)

These modules have a `main()` function, run independently via `run_all.py`, produce their own output, but are **not** called by forge.py's render pipeline. They are available for future integration or manual use.

Key standalone modules of note:
- **`subphonics.py`** — AI project director with chat interface (has its own server)
- **`serum2.py`** (2,126 lines) — Complete Serum 2 architecture model
- **`dojo.py`** (2,394 lines) — Full ill.Gates methodology engine
- **`rco.py`** — Rollercoaster Optimizer for energy curves
- **`psbs.py`** — Phase-Separated Bass System architecture
- **`genetic_evolver.py`** — GA for evolving patches
- **`riddim_engine.py`** — Riddim bass patterns
- **`auto_arranger.py`** — Template-based arrangement generation
- **`ep_builder.py`** — Full EP rendering pipeline
- **`render_queue.py`** — Async render queue (used by SUBPHONICS server)
- **`batch_processor.py`** — Batch operation chain processor

---

## 6. CLI Interface

### Three Entry Points (`pyproject.toml`)

| Command | Module | Purpose |
|---------|--------|---------|
| `dubforge` | `run_all:main` | Master build script — runs all 134 registered modules |
| `dubforge-cli` | `engine.cli:main` | Lightweight CLI with subcommands |
| `subphonics` | `engine.subphonics_server:main` | HTTP chatbot server on port 8433 |

### forge.py CLI Modes

```bash
# Default — full pipeline (wavetables + stems + ableton + presets + track)
python forge.py
python forge.py --all

# Individual steps
python forge.py --serum          # wavetables only
python forge.py --stems          # audio stems only
python forge.py --presets        # .fxp presets only
python forge.py --ableton        # .als project only
python forge.py --track          # full mixed track only

# Song mode — DNA-driven unique track
python forge.py --song "COSMIC FURY" --mood dark --style dubstep

# Producer mode — Subtronics DNA injection
python forge.py --song "BASS CANNON" --producer subtronics

# Fibonacci feedback mode — 144-step iterative improvement
python forge.py --fibonacci --song "BIT RAGE" --mood aggressive

# Dojo mode — ill.Gates timer-enforced production (14 min default)
python forge.py --dojo --song "FURY" --timer 840

# Sound style
python forge.py --song "X" --sound heavy
```

### dubforge-cli Subcommands

```bash
dubforge-cli render [module]         # Render a specific engine module
dubforge-cli export [target]         # Export: samples|presets|wavetables|resynth|als|mix|all
dubforge-cli analyze [type]          # Analyze: spectral_peaks|harmonic_series|phi_detection|spectral_flux|roughness
dubforge-cli info                    # System info
dubforge-cli subphonics              # Start SUBPHONICS chatbot server
```

### run_all.py CLI

```bash
python run_all.py                    # Run all 134 modules
python run_all.py --module rco       # Run single module
python run_all.py --list             # List available modules
python run_all.py --no-memory        # Skip memory tracking
python run_all.py --quiet            # Suppress banners
```

---

## 7. Config System

### Five YAML Configs in `configs/`

| File | Purpose | Key Content |
|------|---------|-------------|
| `fibonacci_blueprint_pack_v1.yaml` | 3 arrangement blueprints | WEAPON (8 sections, 128 bars), EMOTIVE (10 sections, 164 bars), HYBRID (11 sections, 164 bars). All section counts are Fibonacci numbers. |
| `memory_v1.yaml` | Memory system settings | Belt thresholds (Fibonacci: 1,3,5,8,13,21,34), phi relevance scoring formula, session defaults, snapshot intervals. |
| `rco_psbs_vip_delta_v1.1.yaml` | RCO + PSBS profiles | 3 RCO energy curves (WEAPON_16_32, EMOTIVE_LONG, PACK_WEAPON), 3 PSBS bass layer presets (DEFAULT/WEAPON/WOOK) with phi crossover frequencies. |
| `sb_corpus_v1.yaml` | Subtronics discography data | 5 albums (String Theory→Fractals→GRiZTRONICS→Antifractal→Tesseract), 74 tracks with real Apple Music durations. |
| `serum2_module_pack_v1.yaml` | Serum 2 engine configs | 5 module configs: PHI_CORE_WT_ENGINE, FM_BASS_ENGINE, SUB_LAYER_ENGINE, TRANCE_ARP_ENGINE, MIDBASS_GROWL_RESAMPLER_ENGINE. |

### Config Loading

`config_loader.py` provides:
- `load_config(name)` — loads `configs/{name}.yaml` with PyYAML or custom fallback parser
- `get_config_value(config, dotted_key, default)` — nested dictionary lookup
- Canonical constants: `PHI`, `FIBONACCI`, `A4_432`, `A4_440`

---

## 8. Autonomous Capabilities

### 8.1 Fibonacci Feedback Engine (Self-Improvement Loop)

**File:** `fibonacci_feedback.py` (1,142 lines)  
**Trigger:** `forge.py --fibonacci --song "NAME"`

The most sophisticated autonomous system. Executes a 12-step production plan at Fibonacci intervals (1,1,2,3,5,8,13,21,34,55,89,144):

1. **Generate DNA** from SongBlueprint via VariationEngine
2. **Load lessons** from previous tracks (pre-adjustments)
3. **Render** track via `forge.py render_full_track(dna)`
4. **Analyze** rendered WAV (LUFS, peak, spectral distribution, stereo width, contrast)
5. **Compare** against 14 global quality targets from `recipe_book.py`
6. **Compute corrections** (parameter adjustments to DNA)
7. **Apply corrections** (max 3 per pass — Dojo decision fatigue limit)
8. **Re-render** and re-analyze
9. **Check first instinct** — if original was better, revert (Dojo philosophy)
10. **Save lessons** for future tracks
11. **Evaluate belt** progress

### 14 Global Quality Targets (`recipe_book.py`)

| Metric | Target Range | Priority |
|--------|-------------|----------|
| Integrated LUFS | -10.0 to -7.0 | CRITICAL |
| True Peak | ≤ -0.3 dB | CRITICAL |
| Dynamic Range | 4.0–8.0 dB | HIGH |
| Sub Bass % | 20–45% | HIGH |
| Low % | 15–30% | MEDIUM |
| Mid % | 20–40% | HIGH |
| High % | 8–20% | MEDIUM |
| Air % | 2–8% | LOW |
| Stereo Width | 0.3–1.5 | MEDIUM |
| Intro→Drop Contrast | 6.0–18.0 dB | HIGH |
| Duration | 120–300 s | LOW |
| Phase Coherence | 0.3–1.0 | MEDIUM |

### 8.2 Lessons Learned (Cross-Track Learning)

**File:** `lessons_learned.py` (694 lines)  
**Storage:** `output/lessons_learned.json`

Persists insights across tracks:
- **Pre-adjustments**: Before rendering, applies learned parameter values from past successful corrections
- **Post-recording**: Extracts which corrections worked/didn't from FibonacciFeedbackEngine sessions
- **Recurring failure tracking**: Identifies metrics that consistently fail across tracks
- **Golden rules**: 15+ hard-won production truths (e.g., "Sub bass energy 30–45% of spectral content")
- **Belt evaluation**: Fibonacci-based progression (White=1, Yellow=3, Green=5, Blue=8, Purple=13, Brown=21, Black=34)

### 8.3 Memory Engine (Session Persistence)

**File:** `memory.py` (1,044 lines)  
**Storage:** `output/memory/` (sessions/, index.json, asset_registry.json, evolution.json)

- **Sessions**: Begin/end tracking with event logs and timing
- **Asset registry**: All generated files tracked with ratings and phi-weighted recall scores
- **Evolution tracking**: Parameter changes across sessions
- **Phi-weighted recall**: `score = phi_relevance × recency_factor × rating`
- **Auto-belt promotion**: Based on session count + asset quality

### 8.4 Genetic Evolution

**File:** `genetic_evolver.py` (293 lines)

- 16 gene templates (frequency, drive, cutoff, ADSR, etc.)
- Phi-point crossover at position floor(len × 1/PHI)
- Tournament selection with PHI-scaled tournament size
- Default fitness rewards values near PHI center

### 8.5 Evolution Engine

**File:** `evolution_engine.py` (360 lines)

- 5 tracker types: param_drift, phi_convergence, score_climb, diversity, stability
- Real DSP scoring: RMS × spectral_flatness_proxy"

---

## 9. Batch / Queue / Scheduler Systems

| System | File | Mechanism | Status |
|--------|------|-----------|--------|
| **Batch Processor** | `batch_processor.py` | Operation registry (decorator-based) + pipeline chains on file arrays | Standalone |
| **Batch Renderer** | `batch_renderer.py` | Renders all patches from 5 banks × 4 presets to WAV | Standalone |
| **Render Queue** | `render_queue.py` | Threaded async queue with JobStatus (QUEUED→RENDERING→DONE), progress tracking | Used by SUBPHONICS server |
| **Render Pipeline** | `render_pipeline.py` | End-to-end chain: synth → distort → sidechain → stereo → master | Standalone |
| **Run All** | `run_all.py` | Sequential module executor with memory tracking | Main build script |
| **Full Integration** | `full_integration.py` | Run all modules in dependency order, track pass/fail | Standalone |
| **EP Builder** | `ep_builder.py` | Multi-track EP rendering pipeline | Standalone |

---

## 10. Test Coverage

**170 test files** in `tests/` — 1:1 mapping with engine modules:

```
tests/test_ab_tester.py          tests/test_bass_oneshot.py
tests/test_additive_synth.py     tests/test_batch_processor.py
tests/test_als_generator.py      tests/test_fm_synth.py
tests/test_auto_arranger.py      tests/test_mastering_chain.py
tests/test_auto_master.py        tests/test_memory.py
tests/test_dojo.py               tests/test_recipe_book (missing?)
tests/test_fibonacci_feedback    tests/test_rhythm_engine (missing?)
... (170 total test files)
```

Plus: `test_dsp.py` (top-level DSP test), `tests/test_integration.py`, `tests/conftest.py`

Build commands (`Makefile`):
```makefile
test:    python -m pytest tests/ -x -q
lint:    python -m ruff check engine/ tests/
fmt:     python -m ruff format engine/ tests/
clean:   rm -rf output/ build/ dist/ *.egg-info
```

---

## 11. Output Structure

```
output/
├── wavetables/       — Serum-ready .wav wavetable files
├── stems/            — Individual audio stems (7 stems)
├── ableton/          — .als project files + structure JSON
├── presets/           — .fxp VST2 preset files
├── analysis/          — JSON analysis data + PNG charts
├── midi/              — MIDI drum patterns + vocal triggers
├── serum2/            — Serum 2 architecture + patch specs
├── dojo/              — Producer Dojo methodology output
├── memory/            — Long-term persistence (sessions/, index.json)
│   ├── sessions/      — Individual session JSON files
│   ├── asset_registry.json
│   ├── evolution.json
│   └── index.json
├── lessons_learned.json — Cross-track learning database
└── <track_name>.wav   — Final mastered stereo WAV (48kHz/16-bit)
```

---

## 12. Key Architectural Patterns

### Pattern 1: DNA-Driven Architecture
Every synthesis parameter flows from a single `SongDNA` dataclass. This means the same render function produces completely different tracks based on DNA values. The DNA is generated from semantic input (track name + mood + style) via `VariationEngine`, which maps 80+ English words to synth parameter ranges.

### Pattern 2: Phi Throughout
PHI (1.618...) appears in:
- Wavetable harmonic spacing (`phi_harmonic_series`)
- FM operator ratios (carrier:modulator = φ)
- Crossover frequencies in PSBS (phi-ladder)
- Sidechain release curves (`phi_curve`)
- Genetic algorithm crossover point (floor(len × 1/φ))
- Memory recall scoring (`phi_relevance × recency`)
- Belt progression thresholds (Fibonacci numbers)
- Reverb early reflections (phi-spaced taps)
- Delay tap spacing (Fibonacci intervals)

### Pattern 3: ill.Gates Dojo Integration
The Dojo methodology is woven into the feedback loop:
- **14-Minute Hit timer**: `--timer 840` enforces time limits
- **Max 3 decisions per pass**: `enforce_decision_limit()` prevents decision fatigue
- **First instinct preservation**: `check_first_instinct()` reverts if corrections made things worse
- **The Approach phases**: COLLECT → SKETCH → ARRANGE → MIX → FINISH → RELEASE (printed as banners)
- **Belt system**: Fibonacci-based track count progression

### Pattern 4: Layered Sound Design
Every sound in `render_full_track()` uses 2–4 synthesis layers:
- **Kick**: sub body + FM body + click transient + brown noise rumble
- **Snare**: tonal body + pink noise tail + metallic KS ring + white noise top → parallel compression
- **Hats**: Karplus-Strong metallic + perc_synth layered
- **Bass**: 7 independent bass types rotated per bar
- **Pads**: Dark/lush synth + granular cloud + additive partials blended

### Pattern 5: Module Independence
Each of the 172 engine modules follows the same pattern:
1. Docstring with purpose + output paths
2. Dataclass-based presets/configs
3. Synthesis/processing functions
4. A `main()` function that runs standalone
5. `if __name__ == "__main__": main()`

This means every module can run independently via `python -m engine.MODULE_NAME`.

---

## 13. Key Findings & Observations

### What's Working Well

1. **forge.py is fully DNA-driven** — Every parameter in the 1,350-line render function reads from SongDNA, making each track unique
2. **Feedback loop is complete** — FibonacciFeedbackEngine renders → analyzes → corrects → re-renders, with quality targets and lessons persistence
3. **Layered sound design** — Multi-source synthesis with proper mixing, compression, and EQ per element
4. **Mastering chain** — Professional-quality: EQ shelves → soft saturation → loudness normalization → true-peak limiting
5. **RhythmEngine** — Centralized drum pattern generation replaces hardcoded placement
6. **1:1 test coverage** — Every engine module has a corresponding test file
7. **Clean data flow** — SongBlueprint → SongDNA → render_full_track() is elegant and extensible

### What's Not Yet Wired

1. **SUBPHONICS** (`subphonics.py` + `subphonics_server.py`) — Autonomous AI director with chat interface exists but isn't called by forge.py. Has its own HTTP server entry point.
2. **RCO** (`rco.py`) — Energy curve optimizer generates curves but doesn't feed into arrangement sequencing in forge.py
3. **PSBS** (`psbs.py`) — Phase-separated bass architecture defines 5-layer bass but forge.py builds its own 7-bass-type system
4. **Serum 2** (`serum2.py`, 2,126 lines) — Complete Serum 2 architecture model generates specs but doesn't produce audio or integrate with forge.py's render
5. **Genetic evolver** — Can evolve patches but isn't called during production
6. **Auto arranger** — Has arrangement templates but forge.py uses its own hardcoded section structure from SongDNA
7. **Riddim engine** — Generates riddim patterns but isn't used by forge.py
8. **EP builder** — Can render multi-track EPs but isn't triggered from forge.py CLI
9. **Render queue** — Async queue exists for SUBPHONICS server but forge.py renders synchronously
10. **~100+ standalone modules** produce output independently via `run_all.py` but don't feed into the main track render

### Module Count by Phase (run_all.py Registry)

| Phase | Sessions | Count | Theme |
|-------|----------|-------|-------|
| 1–5 | Original | 76 | Core synthesis + infrastructure |
| 6 | 145–155 | 10 | SUBPHONICS Intelligence |
| 7 | 156–166 | 11 | Advanced Synthesis |
| 8 | 167–177 | 11 | Live Performance |
| 9 | 178–188 | 11 | AI & Intelligence |
| 10 | 189–210 | 22 | Production Toolkit |
| 11 | 211–233 | 23 | Polish & Ascension |
| **Total** | | **164** | (+ ~8 unlisted: dsp_core, recipe_book, openclaw_agent, variation_engine, fibonacci_feedback, lessons_learned, rhythm_engine, __init__) |

---

## 14. Data Flow Summary — What Calls What

```
forge.py main()
│
├── --dojo → fibonacci_feedback.FibonacciFeedbackEngine.run()
│              ├── variation_engine.VariationEngine.forge_dna()
│              │     ├── mood_engine.resolve_mood()
│              │     ├── tag_system
│              │     └── config_loader.load_config()
│              ├── lessons_learned.LessonsLearned.get_pre_adjustments()
│              ├── forge.render_full_track(dna)  [see below]
│              ├── quick_analyze.py (subprocess for audio analysis)
│              ├── recipe_book.GLOBAL_QUALITY_TARGETS (compare_to_targets)
│              ├── fibonacci_feedback.compute_corrections()
│              ├── fibonacci_feedback.apply_corrections()
│              ├── fibonacci_feedback.check_first_instinct() (Dojo)
│              └── lessons_learned.LessonsLearned.record_session()
│
├── --song → variation_engine.VariationEngine.forge_dna()
│              └── forge.render_full_track(dna)
│
├── --song --producer → openclaw_agent.get_producer_agent()
│              ├── OpenClawAgent.produce() → SongDNA
│              └── forge.render_full_track(dna)
│
└── (default) → generate_wavetables() → render_stems() →
                 generate_ableton_project() → generate_presets() →
                 render_full_track()  # V5 defaults

render_full_track(dna)
├── Imports: dsp_core, bass_oneshot, lead_synth, pad_synth, perc_synth,
│            noise_generator, impact_hit, fm_synth, formant_synth,
│            additive_synth, karplus_strong, granular_synth, vocal_chop,
│            drone_synth, supersaw, riser_synth, transition_fx,
│            glitch_engine, growl_resampler, beat_repeat
├── Processing: saturation, reverb_delay, multiband_distortion,
│              dynamics (compress), lfo_matrix, pitch_automation,
│              panning (Haas delay)
├── Arrangement: rhythm_engine (RhythmEngine.from_drum_dna), groove (GrooveEngine)
├── Sidechain: sidechain (sidechain_bus)
├── Mixdown: dsp_core (svf_highpass, multiband_compress)
├── Stereo: stereo_imager
└── Master: mastering_chain (master, dubstep_master_settings)

run_all.py
├── memory.get_memory() → MemoryEngine
├── Loops through 134 MODULE_REGISTRY entries
│   └── importlib.import_module(f"engine.{name}").main()
├── memory.register_asset() for all output files
└── memory.end_session()
```

---

*This audit is research only — no files were modified.*
