# DUBFORGE — Reference Context File
**v4.0.0 · Underground Industrial Bass Factory**
**Last Updated: 2026-03-31**

---

## 1. WHAT IS DUBFORGE

DUBFORGE is an **underground industrial bass factory** that generates the filthiest, cleanest **dubstep** — future-proof to 2100. It is a **hit track producing machine** that takes a song idea as input and outputs a polished dancefloor banger in WAV format.

DUBFORGE combines:
- **ill.Gates (Producer Dojo)** — The sacred production methodology. Belt system, 128 Rack, Mudpies, The Approach, 14-Minute Hit, stock device mastery, ninja sounds, volume is the teacher. Backed by `engine/dojo.py` (belt system, 128 Rack technique, The Approach workflow, 23 codified production rules).
- **SUBTRONICS** — The insane genius. Sound design, sample selection, huge drops, double drops, crowd excitement, track arrangement. Backed by `configs/sb_corpus_v1.yaml` (Subtronics discography corpus + VIP deltas + spectral profiles).
- **Dan Winter's phase coherence** — Golden mean phi ratio (φ = 1.618...) and Planck × phi fractal mathematics. Every parameter — envelope timing, filter cutoffs, bar counts, unison detune, arrangement structure, modulation depth — is keyed to phi, Fibonacci, and fractal self-similarity. Backed by `engine/config_loader.py` (PHI, FIBONACCI, A4_432 constants) flowing into all 168 engine modules.
- **TurboQuant** — Psychoacoustic compression from arXiv:2504.19874 (ICLR 2026). 10-band quantization integrated across 50 engine modules. Backed by `engine/turboquant.py`.

The weapons: **Serum 2** for sound generation, **bass-heavy sample packs** for drums/FX/one-shots, and **Ableton Live 12** for arrangement, mixing, and mastering.

### Stats
- **168 engine modules** in `engine/`
- **170 test files** in `tests/` (~2838 tests passing)
- **Dependencies**: numpy ≥ 1.24, pyyaml ≥ 6.0, mido ≥ 1.3
- **Python**: ≥ 3.10 (tested on 3.10–3.13)
- **License**: MIT

---

## 2. THE FOUR PHASES — IDEA TO DANCEFLOOR BANGER

DUBFORGE operates in **four distinct phases**, each producing a fresh Ableton Live session. This enforces ill.Gates' cardinal rule: **separate creation from revision — never mix while creating, never create while mixing.**

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    DUBFORGE PRODUCTION PIPELINE                        ║
║                                                                        ║
║   INPUT: Song Idea (name, mood, key, BPM, style, energy)              ║
║                         │                                              ║
║   ┌─────────────────────▼──────────────────────────────────────────┐   ║
║   │  PHASE 1: GENERATION                                          │   ║
║   │  Sound design + sample selection + idea sandbox                │   ║
║   │  Create all sounds, choose all samples, build palettes         │   ║
║   │  OUTPUT: Sound palette (Serum 2 presets, samples, racks)       │   ║
║   └─────────────────────┬──────────────────────────────────────────┘   ║
║                         │ sounds + samples ready                       ║
║   ┌─────────────────────▼──────────────────────────────────────────┐   ║
║   │  PHASE 2: ARRANGEMENT                                         │   ║
║   │  Ableton Session #1 — "The Creation Session"                  │   ║
║   │  Place all sounds into full song structure                     │   ║
║   │  INTRO → BUILD → DROP → BREAK → BUILD 2 → DROP 2 → OUTRO     │   ║
║   │  MIDI + audio tracks, effects, modulation, automation          │   ║
║   │  OUTPUT: Mix stems (24-bit WAV per track group)                │   ║
║   └─────────────────────┬──────────────────────────────────────────┘   ║
║                         │ stems exported manually                      ║
║   ┌─────────────────────▼──────────────────────────────────────────┐   ║
║   │  PHASE 3: MIXING                                              │   ║
║   │  Ableton Session #2 — "The Mix Session"                       │   ║
║   │  Analyze stems + EQ + compress + effects + spatial + balance   │   ║
║   │  OUTPUT: Mixed stems (24-bit WAV)                              │   ║
║   └─────────────────────┬──────────────────────────────────────────┘   ║
║                         │ mixed stems exported manually                ║
║   ┌─────────────────────▼──────────────────────────────────────────┐   ║
║   │  PHASE 4: MASTERING                                           │   ║
║   │  Ableton Session #3 — "The Master Session"                    │   ║
║   │  Peak performance across all speaker ranges                    │   ║
║   │  OUTPUT: Final mastered WAV — DANCEFLOOR BANGER                │   ║
║   └────────────────────────────────────────────────────────────────┘   ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

### PHASE 1: GENERATION — "The Idea Sandbox"

The sound design and sample selection phase. Define the song idea, generate the SongDNA, choose sample packs, build drum racks, and generate all Serum 2 presets and wavetables. The output is a complete **sound palette** — every sonic ingredient the track needs, ready to be arranged.

No arrangement happens here. No DAW session. Just sounds.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: IDEA INPUT                                                     │
│  Song name, key, BPM, mood, scale, energy level, style                  │
│  → Define in make_track script OR forge.py --song "NAME"                │
│                                                                         │
│  BACKEND:                                                               │
│    engine/variation_engine.py  — SongBlueprint → SongDNA                │
│    engine/mood_engine.py       — mood → parameter mapping               │
│    engine/song_templates.py    — 20 structure templates                  │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 2: IDEA GENERATOR / ENGINE                                        │
│  SongDNA: complete synthesis spec generated from semantic name           │
│  Decides chord progression, harmonic rhythm, energy curve, section map   │
│                                                                         │
│  BACKEND:                                                               │
│    engine/variation_engine.py  — forge_dna() semantic→params             │
│    engine/chord_progression.py — music theory + phi voicing              │
│    engine/rco.py               — Rollercoaster energy curve              │
│    engine/rhythm_engine.py     — drum pattern DNA                        │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 3: DECIDE PARAMETERS                                              │
│  Arrangement blueprint (Fibonacci bar counts), section structure,        │
│  track layout, effects chain, modulation routing, phi-derived timing     │
│                                                                         │
│  BACKEND:                                                               │
│    engine/arrangement_sequencer.py — 4 templates (weapon/emotive/hybrid) │
│    engine/config_loader.py         — PHI, FIBONACCI, A4_432 constants    │
│    configs/fibonacci_blueprint_pack_v1.yaml — 3 blueprints:              │
│      WEAPON (13+8+21 bar drops), EMOTIVE (13+21 bars),                   │
│      HYBRID (Golden-section climax at bar 89)                            │
│    engine/psbs.py — Phase-Separated Bass System (5 phi bands)            │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 4: SELECT SAMPLE PACK                                             │
│  Choose drum kit, FX, vocals, one-shots from bass-heavy sample packs     │
│  GALATCIA collection: Black Octopus Brutal Dubstep, ERB NEURO WT        │
│  + Freesound.org API integration for CC0 samples                         │
│                                                                         │
│  BACKEND:                                                               │
│    engine/galatcia.py      — GALATCIA pack: 229 wav, 95 fxp, 12 WT      │
│      Categories: kicks, snares, hihats, claps, impacts, risers,          │
│      fx_falling, fx_rising, shepard_tones, buildups, reverses            │
│    engine/sample_library.py — SampleLibrary: 25 categories               │
│      kick, snare, clap, hat_closed, hat_open, crash, ride, perc,         │
│      tom, 808, fx_riser, fx_downlifter, fx_impact, fx_sweep,             │
│      vocal, foley, texture, one_shot, bass_hit + more                    │
│    engine/sample_slicer.py — Beat-aligned Fibonacci slicing              │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 5: LOAD DRUMS, EFFECTS, VOCALS & ONE-SHOTS INTO RACKS             │
│  128 Rack (ill.Gates technique): 128 samples per Sampler,               │
│  organized into phi-ratio zone categories (Fibonacci: 5/8/13 zones)      │
│  Drum Rack .adg files with category-mapped pads                          │
│                                                                         │
│  BACKEND:                                                               │
│    engine/dojo.py              — build_128_rack() (128 zones,            │
│      Fibonacci distribution, phi-position "favorite" selector)           │
│    engine/ableton_rack_builder.py — Drum Rack .adg XML generation        │
│      Full DrumGroupDevice with 128 DrumBranch zones                      │
│    engine/galatcia.py          — FXP_PREFIX_MAP + SAMPLE_CATEGORY_MAP    │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 6: GENERATE ALL SOUNDS WITH SERUM 2                                │
│  FXP presets with phi-derived parameters for every synth track            │
│  Custom wavetables (PHI_CORE, GROWL_SAW, GROWL_FM) loaded into Serum     │
│  Macro curves: M1=PHI MORPH, M2=FM DEPTH, M3=SUB WEIGHT, M4=GRIT       │
│                                                                         │
│  BACKEND:                                                               │
│    engine/serum2.py       — Full Serum 2 architecture model               │
│      5 oscillator types: Wavetable, Multisample, Sample, Granular,       │
│      Spectral. Dual warp (30+ modes incl FM, RM, AM, Fold, Wrap).       │
│      8 DUBFORGE patches: Fractal Sub, Phi Growl, Fibonacci FM Screech,   │
│      Golden Reese, Spectral Tear, Granular Atmosphere, Weapon, Phi Pad   │
│    engine/serum2_controller.py — parameter control + preset dispatch      │
│    engine/fxp_writer.py        — .fxp binary writer (CcnK magic)         │
│    engine/phi_core.py          — PHI CORE wavetable generator             │
│    engine/wavetable_morph.py   — wavetable morphing                       │
│    engine/wavetable_pack.py    — wavetable pack builder                   │
│  OUTPUT: output/presets/*.fxp, output/wavetables/*.wav                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key scripts**: `forge.py --serum` (wavetables + presets), `forge.py --song "NAME"` (full SongDNA), `dubforge_launchpad.py` (web UI)

---

### PHASE 2: ARRANGEMENT — "The Creation Session"

The arrangement and composition phase. A **fresh Ableton Live session** receives all the sounds, samples, presets, and wavetables from Phase 1. Everything is placed into the full song structure with MIDI, audio, effects, and modulation.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: BUILD ALS — ARRANGE MIDI + AUDIO ACROSS ALL TRACKS             │
│  Load Ableton with Serum 2 instances (MIDI tracks) and sample racks      │
│  (audio tracks). Full arrangement: INTRO → BUILD → DROP → BREAK →       │
│  BUILD 2 → DROP 2 → OUTRO. Fibonacci bar counts, golden section cue.    │
│                                                                         │
│  Track types:                                                            │
│    MIDI tracks — BASS, SUB, GROWL, WOBBLE, RIDDIM, FORMANT, LEAD,       │
│                  CHORDS, PAD, ARP, FX, RISER (Serum 2 on each)           │
│    Audio tracks — DRUMS (kick, snare, hats via rack), FX one-shots,     │
│                   vocals, impacts, risers (sample-based)                 │
│    Return tracks — REVERB (phi-ratio decay), DELAY (Fibonacci timing)    │
│                                                                         │
│  BACKEND:                                                               │
│    engine/als_generator.py     — ALS gzip XML writer                     │
│      Schema "12.0_12117", Creator "Ableton Live 12.1d1"                  │
│      MIDI tracks with embedded clips, scenes, cue points                 │
│      Global NoteId counter for corruption-free KeyTracks                 │
│    engine/ableton_live.py      — Full LOM: 10 tracks + 2 returns,        │
│      7 scenes, PSBS device chains, Max for Live script generation        │
│    engine/midi_export.py       — .mid file export                        │
│    engine/arrangement_sequencer.py — section placement engine             │
│  OUTPUT: output/ableton/*_PHASE2_ARRANGEMENT.als                         │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 2: ADD EFFECTS & MODULATION                                        │
│  Sidechain pump on bass elements, reverb sends, delay throws,            │
│  distortion/saturation on mids, stereo imaging, filter automation,       │
│  pitch dives on drops, LFO modulation matrix                             │
│                                                                         │
│  BACKEND:                                                               │
│    engine/sidechain.py         — 5 shapes × 4 presets                    │
│    engine/reverb_delay.py      — 5 types, phi-spaced reflections         │
│    engine/multiband_distortion.py — 5 algos × 4 presets                  │
│    engine/stereo_imager.py     — Haas/M-S/freq split/psychoacoustic      │
│    engine/lfo_matrix.py        — 5 waveforms × 4 presets                 │
│    engine/pitch_automation.py  — dive/rise/wobble/staircase/glide        │
│    engine/saturation.py        — tape/tube/digital                        │
│    engine/convolution.py       — 5 IR types × 4 presets                  │
│    engine/beat_repeat.py       — stutter/repeat                          │
│    engine/dynamics.py          — compressor + transient shaper            │
│    engine/riddim_engine.py     — 5 types × 4 presets                     │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 3: PREPARE FOR STEM EXPORT                                         │
│  Session is 100% complete. All sounds designed, all audio placed,        │
│  all effects applied, all modulation programmed. Ready to render.        │
│                                                                         │
│  ► USER ACTION: Manually export stems from Ableton (24-bit WAV)          │
│    → Solo each track group → File > Export Audio/Video                    │
│    → Save to output/stems/phase2/ directory                              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key scripts**: `make_wild_ones_v10.py` (13 tracks, 3824 notes, 144 bars), `forge.py --live --song "NAME"`

---

### PHASE 3: MIXING — "The Mix Session"

A **fresh Ableton session** receives the raw stems from Phase 2. The stems are analyzed, gain-staged, EQ'd, compressed, spatially placed, and balanced into a cohesive mix. No new sounds are created — only sculpted.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: LOAD STEMS INTO FRESH SESSION                                   │
│  New Ableton session with one audio track per stem group                 │
│  Import all 24-bit WAV stems from Phase 2                                │
│                                                                         │
│  BACKEND:                                                               │
│    engine/als_generator.py — generates Phase 3 ALS with audio tracks     │
│    engine/audio_analyzer.py — pre-mix analysis (peak, RMS, spectrum)     │
│    engine/frequency_analyzer.py — FFT spectral profile per stem          │
│    engine/tempo_detector.py — BPM verification                           │
│    engine/key_detector.py — key verification                             │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 2: ANALYZE STEMS                                                   │
│  Frequency analysis, dynamic range, phase coherence check                │
│  Reference track comparison against Subtronics corpus                    │
│  Identify masking, energy distribution, stereo field gaps                │
│                                                                         │
│  BACKEND:                                                               │
│    engine/reference_analyzer.py — compare vs reference tracks             │
│    engine/phi_analyzer.py       — phi ratio analysis                     │
│    engine/harmonic_analysis.py  — FFT harmonic 5 types                   │
│    engine/pattern_recognizer.py — pattern recognition                    │
│    configs/sb_corpus_v1.yaml    — Subtronics reference corpus             │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 3: MIX — EQ, COMPRESS, EFFECTS, SPATIAL, BALANCE                  │
│  Gain staging (phi-ratio priority levels per element type)               │
│  EQ: clear Pain Zone (2–4.5 kHz) for "singer" elements                  │
│  Compression: dynamics control per stem                                  │
│  Spatial: stereo width, panning (phi-derived L/R positions)              │
│  Effects: mix-stage reverb/delay for glue and depth                      │
│  Sidechain: bass → kick ducking for clarity                              │
│                                                                         │
│  BACKEND:                                                               │
│    engine/auto_mixer.py        — gain staging (phi priority levels)       │
│      SUB=1.0, SNARE=0.9, BASS=0.85, LEAD=0.75, PAD=0.5, FX=0.4        │
│    engine/mix_assistant.py     — mix guidance + suggestions               │
│    engine/intelligent_eq.py    — auto-EQ with spectral analysis          │
│    engine/dynamics.py          — compressor + transient shaper            │
│    engine/dynamics_processor.py — advanced dynamics                       │
│    engine/stereo_imager.py     — spatial placement                       │
│    engine/sidechain.py         — kick-triggered ducking                   │
│    engine/dc_remover.py        — 5 Hz highpass on all stems              │
│    engine/normalizer.py        — level normalization                     │
│  OUTPUT: output/ableton/*_PHASE3_MIXING.als                              │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 4: EXPORT MIXED STEMS                                              │
│                                                                         │
│  ► USER ACTION: Export mixed stems from Ableton (24-bit WAV)             │
│    → Save to output/stems/phase2/ directory                              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Backend analysis**: `engine/auto_mixer.py` (gain staging), `engine/intelligent_eq.py` (spectral EQ), `engine/reference_analyzer.py` (A/B comparison)

---

### PHASE 4: MASTERING — "The Master Session"

A **fresh Ableton session** receives the mixed stems. The final polish for peak performance and maximum loudness across all speaker systems — from festival PA rigs to phone speakers.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: LOAD MIXED STEMS INTO MASTERING SESSION                         │
│  Fresh Ableton session, import mixed stems, verify alignment             │
│                                                                         │
│  BACKEND:                                                               │
│    engine/als_generator.py — Phase 4 mastering session ALS               │
│    engine/audio_analyzer.py — pre-master analysis                        │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 2: MASTERING CHAIN                                                 │
│  EQ → Multiband Compression (phi crossovers) → Stereo Enhancement →     │
│  Limiting → LUFS Normalization                                           │
│                                                                         │
│  Phi crossover frequencies: 89 Hz / 233 Hz / 610 Hz / 1597 Hz           │
│  (Fibonacci-approximate, matching PSBS band boundaries)                  │
│  Target: -8.0 LUFS (dancefloor), ceiling -0.3 dB                        │
│                                                                         │
│  BACKEND:                                                               │
│    engine/auto_master.py     — auto-mastering engine                     │
│      EQ matching, multiband processing, stereo enhancement,              │
│      bass boost (+1.5 dB), air boost (+1.0 dB), limiting                 │
│    engine/mastering_chain.py — EQ → comp → limiter → LUFS target         │
│    engine/normalizer.py      — loudness normalization                    │
│    engine/dither.py          — PHI dithering for bit depth               │
│  OUTPUT: output/ableton/*_PHASE4_MASTERING.als                           │
├─────────────────────────────────────────────────────────────────────────┤
│  STEP 3: FINAL EXPORT — DANCEFLOOR BANGER                               │
│                                                                         │
│  ► USER ACTION: Export final master from Ableton                         │
│    → 24-bit / 48 kHz WAV                                                │
│    → Save to output/masters/<TRACK_NAME>_MASTER.wav                      │
│                                                                         │
│    ████████████████████████████████████████████████                       │
│    █  DONE. DANCEFLOOR BANGER IN WAV FORMAT.   █                         │
│    ████████████████████████████████████████████████                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Backend**: `engine/auto_master.py` (target -8.0 LUFS, ceiling -0.3 dB), `engine/mastering_chain.py` (EQ → comp → limit)

---

### LEGACY: Python DSP Pipeline (V5–V9)

The original full-audio-in-Python approach still works for prototyping and headless rendering when Ableton isn't available. Not the canonical pipeline.

```
SongBlueprint → SongDNA → 29+ synthesis steps → arrange → DSP →
TurboQuant → stems → mixdown → mastering → export
```

**Scripts**: `make_wild_ones_v9.py` (2961 lines), `forge.py` (2700+ lines with `--stems`, `--track`, `--song`, `--dojo`, `--fibonacci` modes)

---

## 3. ENGINE MODULE INVENTORY (189 modules)

Organized by which phase of production they serve.

### 3A. PHASE 1 — Sound Generation & Synthesis (20 modules)
| Module | Purpose |
|--------|---------|
| `additive_synth.py` | Additive synthesis with phi-spaced partials |
| `arp_synth.py` | Fibonacci arpeggiator patterns |
| `bass_oneshot.py` | Mid-range bass one-shots |
| `chord_pad.py` | Rich harmonic chord stacks |
| `drone_synth.py` | Sustained evolving drones |
| `fm_synth.py` | FM synthesis (6-operator) |
| `formant_synth.py` | Vowel-shaped resonant filtering |
| `granular_synth.py` | Grain cloud engine, phi-spaced onsets |
| `impact_hit.py` | Transient-heavy impact hits |
| `karplus_strong.py` | Pluck synthesis |
| `lead_synth.py` | Lead sounds, phi-tuned envelopes |
| `noise_generator.py` | White/pink/brown noise |
| `pad_synth.py` | Pad & atmosphere layers |
| `perc_synth.py` | Tuned metallic percussion |
| `pluck_synth.py` | Pluck one-shots |
| `riser_synth.py` | Filtered sweeps and noise risers |
| `sub_bass.py` | Sub-bass one-shots |
| `supersaw.py` | Supersaw oscillator |
| `vector_synth.py` | Vector synthesis |
| `wobble_bass.py` | LFO-modulated wobble bass |

### 3B. PHASE 1 — Sample Packs & Asset Management (10 modules)
| Module | Purpose |
|--------|---------|
| `galatcia.py` | GALATCIA collection: 229 wav + 95 fxp + 12 WT + 2 adg |
| `sample_library.py` | Sample Library: 25 categories, Freesound API, catalog |
| `sample_slicer.py` | Beat-aligned Fibonacci slicing |
| `sample_pack_builder.py` | Sample pack building |
| `sample_pack_exporter.py` | Sample pack export |
| `preset_browser.py` | Preset browsing |
| `preset_mutator.py` | Preset mutation/evolution |
| `preset_pack_builder.py` | Preset pack builder |
| `preset_vcs.py` | Preset version control |
| `ep_builder.py` | EP builder |

### 3C. PHASE 1 — Serum 2 & Wavetable Engine (6 modules)
| Module | Purpose |
|--------|---------|
| `serum2.py` | Full Serum 2 architecture model (5 osc types, dual warp, mod matrix) |
| `serum2_controller.py` | Serum 2 parameter control + preset dispatch |
| `fxp_writer.py` | FXP/FXB VST2 preset binary writer (CcnK magic) |
| `phi_core.py` | PHI CORE wavetable generator (phi-spaced partials) |
| `wavetable_morph.py` | Wavetable morphing (fractal interpolation) |
| `wavetable_pack.py` | Wavetable pack builder for Serum import |

### 3D. PHASE 2 — Arrangement & Composition (8 modules)
| Module | Purpose |
|--------|---------|
| `arrangement_sequencer.py` | Arrangement engine (4 templates: weapon/emotive/hybrid/fib) |
| `chord_progression.py` | Music theory, phi voicing, 11 EDM presets |
| `groove.py` | Groove templates + swing |
| `rhythm_engine.py` | Rhythm DNA, drum patterns |
| `riddim_engine.py` | Riddim patterns (5 types × 4 presets) |
| `song_templates.py` | 20 song structure templates |
| `trance_arp.py` | Fibonacci-timed arpeggiator |
| `variation_engine.py` | SongBlueprint → SongDNA semantic engine |

### 3E. PHASE 1 & 2 — DAW Integration & ALS Generation (10 modules)
| Module | Purpose |
|--------|---------|
| `als_generator.py` | ALS file writer (gzip XML, schema 12.0_12117) |
| `ableton_live.py` | Full LOM, session/arrangement templates, PSBS chains |
| `ableton_bridge.py` | OSC bridge to live Ableton instance |
| `ableton_rack_builder.py` | Drum Rack .adg builder (128 zones) |
| `midi_export.py` | MIDI file export (.mid) |
| `midi_processor.py` | MIDI processing utilities |
| `osc_controller.py` | OSC remote control |
| `production_pipeline.py` | SongDNA → Ableton+Serum2 orchestrator |
| `render_pipeline.py` | Render pipeline |
| `render_queue.py` | Render queue management |

### 3F. PHASE 2 & 3 — DSP & Effects (18 modules)
| Module | Purpose |
|--------|---------|
| `beat_repeat.py` | Beat repeat / stutter |
| `convolution.py` | Convolution engine (5 IR types × 4 presets) |
| `crossfade.py` | Audio crossfading |
| `dc_remover.py` | DC offset removal (5 Hz highpass) |
| `dither.py` | PHI dithering for bit depth reduction |
| `dsp_core.py` | SVF filter, oversampling, PolyBLEP oscillators, waveshapers |
| `dynamics.py` | Compressor, transient shaper |
| `dynamics_processor.py` | Advanced dynamics processing |
| `intelligent_eq.py` | Auto-EQ with spectral analysis |
| `lfo_matrix.py` | LFO modulation matrix (5 waveforms × 4 presets) |
| `multiband_distortion.py` | 5 algorithms × 4 presets |
| `normalizer.py` | Audio normalization |
| `phase_distortion.py` | Phase distortion synthesis |
| `pitch_automation.py` | Pitch dive/rise/wobble/staircase/glide |
| `reverb_delay.py` | Reverb & delay (5 types, phi-spaced reflections) |
| `ring_mod.py` | Ring modulation |
| `saturation.py` | Tape/tube/digital saturation |
| `stereo_imager.py` | Haas/M-S/freq split/psychoacoustic |
| `wave_folder.py` | Wavefolder distortion |

### 3G. PHASE 3 — Mixing (5 modules)
| Module | Purpose |
|--------|---------|
| `auto_mixer.py` | Auto gain staging (phi-ratio priority per element) |
| `mix_assistant.py` | Mix guidance + suggestions |
| `stem_mixer.py` | Stem mixing |
| `multitrack_renderer.py` | Multi-track rendering |
| `batch_renderer.py` | Batch rendering |

### 3H. PHASE 4 — Mastering (3 modules)
| Module | Purpose |
|--------|---------|
| `auto_master.py` | Auto-mastering: EQ match, multiband, limiting, -8.0 LUFS |
| `mastering_chain.py` | Mastering chain: EQ → comp → limit → LUFS normalization |
| `batch_processor.py` | Batch processing for multiple masters |

### 3I. PHASE 1 & 2 — Bass System (4 modules)
| Module | Purpose |
|--------|---------|
| `psbs.py` | Phase-Separated Bass System (5 phi-spaced bands) |
| `growl_resampler.py` | Mid-bass growl resampler + mangle |
| `rco.py` | Rollercoaster Optimizer (energy curves) |
| `sidechain.py` | Sidechain engine (5 shapes × 4 presets) |

### 3J. ALL PHASES — Analysis & Intelligence (18 modules)
| Module | Purpose |
|--------|---------|
| `audio_analyzer.py` | Audio analysis (peak, RMS, spectrum) |
| `audio_math.py` | Audio math utilities |
| `frequency_analyzer.py` | FFT frequency analysis |
| `genre_detector.py` | Genre classification |
| `harmonic_analysis.py` | FFT harmonic analysis (5 types × 4 presets) |
| `key_detector.py` | Key detection |
| `pattern_recognizer.py` | Pattern recognition |
| `phi_analyzer.py` | Phi ratio analysis |
| `reference_analyzer.py` | Reference track comparison (vs Subtronics corpus) |
| `tempo_detector.py` | BPM detection |
| `autonomous.py` | Autonomous production agent |
| `evolution_engine.py` | Evolutionary sound design |
| `genetic_evolver.py` | Genetic algorithm evolver |
| `markov_melody.py` | Markov chain melody generation |
| `mood_engine.py` | Mood-based parameter mapping |
| `openclaw_agent.py` | OpenClaw AI agent |
| `style_transfer.py` | Style transfer |
| `turboquant.py` | TurboQuant psychoacoustic compression (10-band) |

### 3K. Infrastructure & Utilities (20+ modules)
| Module | Purpose |
|--------|---------|
| `audio_buffer.py` | Audio buffer management |
| `audio_splitter.py` | Audio splitting |
| `audio_stitcher.py` | Audio stitching |
| `backup_system.py` | Project backup |
| `cli.py` | CLI interface |
| `config_loader.py` | YAML config + PHI/FIBONACCI/A4_432 constants |
| `dojo.py` | ill.Gates Producer Dojo: belt system, 128 Rack, The Approach |
| `envelope_generator.py` | Envelope generator |
| `error_handling.py` | Error handling |
| `fibonacci_feedback.py` | Fibonacci quality feedback loop |
| `lessons_learned.py` | Belt system + lessons |
| `log.py` | Centralized logging |
| `memory.py` | Long-term persistence |
| `profiler.py` | Performance profiling |
| `session_persistence.py` | Session save/load |
| `tag_system.py` | Asset tagging |
| `tuning_system.py` | 432 Hz tuning |
| `watermark.py` | Audio watermarking |
| `auto_arranger.py` | Automatic arrangement |

*(Plus ~30 more: collaboration, clip_launcher, scene_system, snapshot_manager, link_sync, live_fx, bounce, bus_router, etc.)*

---

## 4. CORE ARCHITECTURE

### 4A. PSBS — Phase-Separated Bass System
The foundation of DUBFORGE bass: 5 phi-spaced frequency bands, each processed independently for maximum clarity and weight.

| Band | Range (Hz) | Role | Serum 2 Patch |
|------|-----------|------|---------------|
| SUB | 20–89 | Foundation, mono sine | Fractal Sub |
| LOW | 89–144 | Warmth, body | Golden Reese |
| MID | 144–233 | Growl, presence | Phi Growl |
| HIGH | 233–377 | Grit, character | Fibonacci FM Screech |
| CLICK | 377–610 | Attack, transient | Spectral Tear |

Each band: Serum 2 → EQ Eight (band isolation) → Saturator → Utility. Crossovers are Fibonacci-approximate Hz.
Backend: `engine/psbs.py`

### 4B. TurboQuant — Psychoacoustic Compression
Based on arXiv:2504.19874 (ICLR 2026, Google Research). Algorithm: Random rotation (FWHT) → Lloyd-Max scalar quantization → optional QJL residual correction.

Three integration points:
1. **Wavetable compression** — 2048-sample frames at 3 bits (~5× smaller)
2. **Audio buffer compression** — chunk-based, for idle buffer archival
3. **Spectral vector search** — nearest-neighbor via cosine similarity

Integrated across 50 engine modules. Backend: `engine/turboquant.py`

### 4C. SongDNA System
The brain of DUBFORGE. Translates a song name/mood/style into every parameter needed for production.

```
SongBlueprint (name, mood, style, key, bpm)
       ↓  variation_engine.forge_dna()
SongDNA (complete synthesis + arrangement spec)
       ↓  Phase 1 → Phase 2 pipeline
Full Ableton session (ready for stem export)
```

Semantic word→parameter mappings: "CYCLOPS FURY" → aggressive FM ratios, heavy sidechain, fast attack.
Backend: `engine/variation_engine.py`, `engine/mood_engine.py`

### 4D. The Three Influences — Integrated

| Influence | What it provides | Where it lives |
|-----------|-----------------|----------------|
| **ill.Gates / Producer Dojo** | Workflow methodology, belt system, 128 Rack, Mudpies, The Approach, 14-Minute Hit, ninja sounds, stock device mastery, 23 production rules | `engine/dojo.py`, DOCTRINE.md rules 1–23 |
| **SUBTRONICS** | Sound design reference, sample selection strategy, arrangement patterns, huge drops, double drops, crowd excitement, spectral profiles, VIP deltas | `configs/sb_corpus_v1.yaml`, `engine/reference_analyzer.py` |
| **Dan Winter** | Phi (1.618...) = master constant, Fibonacci structure, Planck × phi^n frequency ladder, 432 Hz tuning, fractal self-similarity, phase coherence | `engine/config_loader.py` (PHI, FIBONACCI, A4_432), every engine module |

### 4E. Doctrine Constants
- **PHI** = 1.6180339887... — golden ratio, master constant
- **A4_432** = 432 Hz — optional reference pitch
- **Fibonacci sequence** — governs bar counts, drop lengths, partial counts, envelope timing
- **Phi envelope timing** — Attack:Decay:Release = 1 : φ : φ²
- **Phi gate ratio** — ~0.618 of beat length
- **FM ratio** — carrier:modulator = 1:φ (inharmonic dubstep growl)
- **Unison detune** — φ^k × 3.0 cents per voice
- **Filter cutoff ladder** — 55 × φ^n Hz (89, 144, 233, 377, 610, 987...)
- **Macro curve** — value^(1/φ), emphasizes 0.618 sweet spot

---

## 5. DAW ENVIRONMENT

### 5A. Ableton Live 12.3.6 Standard
- ALS format: gzip-compressed XML
- Schema: `12.0_12117`, Creator: `Ableton Live 12.1d1`
- **Three sessions per track** (one per production phase):
  - Session #1: Arrangement (MIDI + audio tracks, Serum 2 instruments, racks — Phase 2)
  - Session #2: Mixing (audio tracks only, stems from Phase 2 — Phase 3)
  - Session #3: Mastering (audio tracks, mixed stems from Phase 3 — Phase 4)
- Session template: 10 tracks + 2 returns (Reverb/Delay), 7 scenes
- Arrangement template: Fibonacci bar counts with golden section cue point
- Return tracks: phi-ratio decay (reverb), Fibonacci timing (delay)
- Master chain: EQ Eight → Glue Comp → OTT (phi crossovers) → Limiter

### 5B. Serum 2 VST3 v2.0.24 (Xfer Records)
- Path: `C:\Program Files\Common Files\VST3\Serum2.vst3`
- Audio CID: `56534558667350736572756D20320000`
- 5 oscillator types: Wavetable, Multisample, Sample, Granular, Spectral
- Dual warp system, 30+ warp modes (FM, RM, AM, Fold, Wrap, etc.)
- Phi-derived params: unison detune, filter cutoff, envelope timing, FM ratios
- 8 DUBFORGE patches: Fractal Sub, Phi Growl, Fibonacci FM Screech, Golden Reese, Spectral Tear, Granular Atmosphere, Weapon, Phi Pad
- Macro mapping: M1=PHI MORPH, M2=FM DEPTH, M3=SUB WEIGHT, M4=GRIT
- Arpeggiator LFO rates: Fibonacci (1/1, 1/2, 1/3, 1/5, 1/8, 1/13)

### 5C. VST3 Auto-Loading — DISABLED
Ableton crashes with "invalid uuid string" during VST3 state restore. The binary preset buffer can only be generated by a running plugin instance. User loads Serum 2 manually on each MIDI track and loads the .fxp presets.

### 5D. Sample Pack Integration
- **GALATCIA** (`C:\dev\DUBFORGE GALATCIA`): Black Octopus Brutal Dubstep & Riddim (95 .fxp, 229 .wav, 12 WT, 2 .adg racks)
- **SampleLibrary**: Freesound.org API for CC0 samples, local file import, 25 categories
- Samples are loaded into Drum Racks (128 Rack technique) and audio tracks in the ALS

---

## 6. KEY FILES

### 6A. Production Scripts
| File | Purpose |
|------|---------|
| `forge.py` | Master pipeline (all modes: --stems, --serum, --ableton, --live, --song, --dojo, --fibonacci) |
| `make_wild_ones_v10.py` | V10 MIDI-first track (13 tracks, 3824 notes, 144 bars) |
| `make_wild_ones_v9.py` | V9 Python DSP track (2961 lines, legacy audio render) |
| `make_track.py` | Generic track builder |
| `run_all.py` | Run all engine modules sequentially |

### 6B. Web UIs
| File | Purpose | Port |
|------|---------|------|
| `dubforge_launchpad.py` | Phase 1 Launchpad — 6-tab Gradio UI (Idea Sandbox, Arrangement, Sample Packs, Serum 2 Patches, FORGE IT, Pipeline). Full end-to-end: name/mood/key/BPM → SongDNA → FXP + MIDI + ALS | 7870 |
| `dubstep_analyzer_ui.py` | Taste Analyzer — 5-tab Gradio UI (SoundCloud, Local Files, Taste Profile, Serum Blueprints, Feedback) | 7862 |

### 6C. Configuration Files
| File | Purpose |
|------|---------|
| `configs/fibonacci_blueprint_pack_v1.yaml` | 3 arrangement blueprints (WEAPON/EMOTIVE/HYBRID) |
| `configs/rco_psbs_vip_delta_v1.1.yaml` | RCO + PSBS + VIP delta configs |
| `configs/serum2_module_pack_v1.yaml` | 5 Serum 2 module specs |
| `configs/production_queue.yaml` | Autonomous batch queue (5 tracks) |
| `configs/sb_corpus_v1.yaml` | Subtronics discography corpus + VIP deltas |
| `configs/memory_v1.yaml` | Memory system config |

### 6D. Documentation
| File | Purpose |
|------|---------|
| `CONTEXT.md` | This file — complete pipeline reference |
| `DOCTRINE.md` | Core principles, module tables, all rules |
| `README.md` | Project structure, quick start |
| `AUDIT.md` / `AUDIT_COMPREHENSIVE_2025.md` | System audits |
| `reports/TURBOQUANT_APPLICATION_MAP.md` | 75 TQ integration points |
| `reports/150_INSIGHTS_DEEP_DIVE.md` | 150 production insights |

---

## 7. OUTPUT STRUCTURE

```
output/
├── ableton/          # .als files (3 per track: PHASE2, PHASE3, PHASE4)
├── midi/             # .mid files (drag & drop into DAW)
├── presets/           # .fxp files (Serum 2 presets, one per synth track)
├── wavetables/        # .wav files (import into Serum 2 oscillators)
├── stems/
│   ├── phase2/       # Raw stems from Arrangement session
│   └── phase3/       # Mixed stems from Mix session
├── masters/           # Final mastered WAV — THE DANCEFLOOR BANGER
├── mixes/             # Mix outputs
├── analysis/          # JSON reports + PNG charts
├── serum2/            # Serum 2 architecture + patch definitions
├── drums/             # Synthesized drum hits
├── galatcia/          # Organized GALATCIA samples + presets
├── samples/           # SampleLibrary downloads (25 categories)
├── memory/            # Persistence data
├── sample_packs/      # Built sample packs
├── m4l/               # Max for Live scripts
├── batch/             # Batch processing outputs
└── dojo/              # ill.Gates methodology exports (belt system, 128 rack)
```

---

## 8. COMMANDS CHEAT SHEET

```bash
# ═══ PHASE 1: GENERATION + PHASE 2: ARRANGEMENT ═══
python dubforge_launchpad.py              # Web UI (Gradio, port 7870)
python dubforge_launchpad.py --share      # Web UI with public share link
python forge.py --song "TRACK NAME"      # Full pipeline from song name
python forge.py --live --song "NAME"     # Ableton + Serum 2 live session
python forge.py --dojo                   # ill.Gates 14-Minute Hit mode
python make_wild_ones_v10.py             # V10 MIDI-first (13 tracks, 144 bars)
python forge.py                          # Full pipeline (wavetables + stems + ALS + presets)
python forge.py --serum                  # Wavetables only
python forge.py --ableton                # ALS project only
python forge.py --fibonacci              # Fibonacci feedback loop mode

# ═══ LEGACY: Python DSP ═══
python make_wild_ones_v9.py              # V9 full audio render (2961 lines)
python forge.py --stems                  # Audio stems only (Python DSP)
python forge.py --track                  # Mixed track only (Python DSP)

# ═══ BATCH / AUTONOMOUS ═══
python -m engine.autonomous --queue configs/production_queue.yaml
python run_all.py                        # Run all engine modules

# ═══ TEST & LINT ═══
python -m pytest tests/ -v               # Full test suite (~2838 tests)
python -m ruff check engine/ tests/      # Lint (line-length=100)
make test                                # pytest
make lint                                # ruff
make fmt                                 # Auto-format
make check                               # Lint + test
```

---

## 9. KNOWN LIMITATIONS & IMPLEMENTATION GAPS

### Working Now
1. **MIDI track generation** — als_generator.py creates Serum 2 MIDI tracks with embedded clips
2. **FXP preset generation** — fxp_writer.py creates binary Serum 2 presets with phi params
3. **Wavetable generation** — phi_core.py creates wavetables, auto-copies to Serum folder
4. **ALS file generation** — clean gzip XML, opens in Ableton Live 12 without errors
5. **Sample library & GALATCIA** — cataloging, categorization, Freesound API integration
6. **Drum Rack .adg files** — ableton_rack_builder.py generates 128-zone racks
7. **Full Python DSP pipeline** — V9 renders complete audio from Python (legacy)
8. **Web UI Launchpad** — dubforge_launchpad.py Gradio app with 6 tabs, end-to-end forge pipeline

### Needs Implementation
1. **Audio tracks in ALS** — als_generator.py currently creates MIDI tracks only. For Phase 1 to fully load drum samples / vocals / FX one-shots as audio clips, `ALSTrack(is_audio=True)` with FileRef pointing to .wav files needs to be added.
2. **Phase 3 ALS template** — A dedicated mixing session ALS generator that creates audio tracks for stem import.
3. **Phase 4 ALS template** — A mastering session ALS generator.
4. **VST3 auto-loading** — DISABLED. Ableton crashes on binary preset buffer restore. User loads Serum 2 manually.
5. **SAMPLE_RATE mismatches** — 72 engine modules use hardcoded SR (44100/48000). TurboQuant uses 48000.

### Gotchas
- **NoteId uniqueness** — Must use `global_note_id` counter across ALL KeyTracks. Per-KeyTrack IDs cause ALS corruption.
- **24-bit WAV** — `_pack_24bit()` / `_interleave_24bit_stereo()` helpers needed; `bytearray[i::6] = numpy_slice` fails.
- **Windows encoding** — Set `$env:PYTHONUTF8="1"` before running. Mastering chain logs use non-ASCII characters.

---

## 10. PRODUCTION WORKFLOW QUICK-REFERENCE

### Starting a New Track
1. Decide: song name, key, BPM, mood, energy
2. **Web UI**: Run `python dubforge_launchpad.py` → open http://localhost:7870 → use Idea Sandbox tab to preview mood/SongDNA → FORGE IT tab to generate all assets
   **CLI**: Run `python forge.py --song "YOUR TRACK NAME"` (or copy `make_wild_ones_v10.py` as template)
3. Script generates: SongDNA → MIDI patterns → FXP presets → wavetables → ALS
4. Open `output/ableton/*_PHASE2_ARRANGEMENT.als` in Ableton Live 12
5. Load Serum 2 on each synth track → load .fxp presets from `output/presets/`
6. Drag wavetables from `output/wavetables/` into Serum oscillators
7. Load drum samples from `output/galatcia/samples/` into Drum Racks
8. Play, tweak, add automation — the arrangement is already there
9. Export stems (24-bit WAV) → `output/stems/phase2/`
10. Open Phase 3 mixing session → import stems → mix → export mixed stems
11. Open Phase 4 mastering session → import mixed stems → master → export final WAV
12. **DANCEFLOOR BANGER COMPLETE**

---

## 11. DOCTRINE RULES

### Dan Winter / Phi Doctrine
1. **PHI = 1.618...** is the master constant (phase, harmony, modulation, timing)
2. **Fibonacci** governs all structural decisions (bar counts, drops, partials)
3. **432 Hz** optional reference pitch (A4 = 432 Hz, coherence tuning)
4. **Fractality over linearity** — self-similar structures at every scale
5. **Planck Floor** as theoretical lower bound of frequency resolution
6. **Phi envelope**: Attack:Decay:Release = 1 : φ : φ², Sustain at 1/φ ≈ 0.618

### ill.Gates / Producer Dojo Doctrine
7. **The 14-Minute Hit** — speed = depth. First instinct > labored revision
8. **Separate creation from revision** — NEVER mix while creating (enforced by 3-phase pipeline)
9. **Ninja Sounds** — most sounds avoid listener attention, only the "singer" demands focus
10. **Pain Zone (2–4.5 kHz)** — clear for the "singer"; band elements don't compete
11. **Decision fatigue kills creativity** — Fibonacci limit on alternatives (3/5/8 max)
12. **Volume is the teacher** — write MORE, not better. Speed lets volume teach
13. **Stock Device Mastery** — Sampler, Operator, Saturator, OTT, Erosion, Glue Comp, Echo, Roar
14. **128 Rack** — 128 samples per Sampler, phi-ratio zones, Fibonacci distribution
15. **Don't Resist What's Easy** — the direct route is usually best

### Subtronics Doctrine
16. **Huge drops** — PSBS bass layering for maximum weight
17. **Double drops** — arrangement engine supports back-to-back drop sections
18. **Sound design fearlessness** — every parameter available for mangling (growl_resampler, wave_folder, ring_mod)
19. **Sample selection** — GALATCIA + SampleLibrary + Freesound for the filthiest source material
20. **Crowd excitement** — RCO energy curves mapped to Subtronics-style arrangement dynamics
