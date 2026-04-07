# DUBFORGE — Dojo-Guided Integration Roadmap

**Date:** 2025-07-22
**Framework:** ill.Gates / Producer Dojo Methodology (34 Rules, 23 Techniques, 7 Approach Phases, 7 Belt Levels, 3 Mixing Mental Models)
**Scope:** All ~139 unwired engine modules across 12 categories
**Current state:** 48 modules wired in render (23.4%), 18 imported-unused, ~139 unwired

---

## Mapping Framework

### The Approach → Render Pipeline
| Approach Phase | Forge Stage | Brain Mode | Priority Window |
|---|---|---|---|
| COLLECT | Pre-render: sample gathering, reference analysis, library prep | Child (prep) | Before render |
| SKETCH | Phase 1: DNA setup, sound palette selection | Child | Generation |
| ARRANGE | Phase 2: Section sequencing, energy curves, structure | Architect | Arrangement |
| SOUND_DESIGN | Phase 2-3: Synthesis refinement, spectral work, FX | Child→Architect | Enhancement |
| MIX | Phase 3: Gain staging, frequency slotting, bus routing | Critic | Mixdown |
| MASTER | Phase 4: Limiting, dither, normalize, loudness | Critic | Mastering |
| RELEASE | Phase 5: Export, metadata, distribution, VIP packaging | Critic | Output |

### Priority Tiers
| Tier | Meaning | Integration Sprint |
|---|---|---|
| **P0** | Directly improves render quality NOW | Sprint 1 (immediate) |
| **P1** | Fills critical pipeline gaps | Sprint 2 (next) |
| **P2** | Adds professional depth | Sprint 3 (soon) |
| **P3** | Specialized / DAW / future | Sprint 4+ (later) |

### Belt Mapping
| Belt | Tracks | Module Scope |
|---|---|---|
| WHITE (1) | Core forge.py baseline only |
| YELLOW (3) | + analysis + basic mixing |
| GREEN (5) | + phi_core, rco, psbs, growl_resampler, serum2 |
| BLUE (8) | + advanced synthesis + pipelines |
| PURPLE (13) | + spectral processing + AI evolution |
| BROWN (21) | + full DAW integration + live performance |
| BLACK (34) | ALL MODULES |

---

## CATEGORY 1 — Spectral Processing (8 modules)

**Dojo Phase:** SOUND_DESIGN (spectral refinement) + MIX (frequency analysis for slotting)
**Belt Level:** PURPLE (advanced — spectral domain is expert territory)
**Dojo Rules:** #26 "Every mix is a Tetris board" • #27 "High-pass everything"
**Technique:** Frequency Slotting (Tetris Board), Ninja Sounds (Singer vs Band)

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **frequency_analyzer** | DFT band energy, centroid, bandwidth, rolloff | **P0** | MIX | Feeds mix_assistant + auto_mixer | Functional |
| **harmonic_gen** | Generate overtone series from fundamentals | **P1** | SOUND_DESIGN | Feeds spectral_morph + wavetable generation | Functional |
| **spectral_gate** | Band-specific noise gating | **P1** | MIX | Post-render cleanup before mastering | Functional |
| **spectral_morph** | PHI-weighted spectral interpolation between signals | **P2** | SOUND_DESIGN | VIP technique — morph between versions | Functional |
| **wavetable_morph** | Phi-curve interpolation between WT frames | **P2** | SOUND_DESIGN | Feeds phi_core wavetable generation | Partial |
| **harmonic_analysis** | Overtone tracking, roughness, phi-ratio detection | **P2** | MIX | QA gate — verify phi coherence | Partial |
| **spectral_resynthesis** | FFT→phi-filter→reconstruct (5 modes) | **P3** | SOUND_DESIGN | Advanced resampling chains | Partial |
| **spectrogram_chat** | Base64 spectrogram PNG for browser display | **P3** | RELEASE | SUBPHONICS chatbot visual feedback | Functional |

**Workflow Chain:** `harmonic_gen` → `spectral_morph` / `wavetable_morph` → `spectral_gate` → `frequency_analyzer` → mix decisions
**Alignment Opportunity:** `frequency_analyzer` + `harmonic_analysis` could share FFT computation — unified spectral analysis pass
**Redundancy:** None — each module handles a distinct spectral domain

### Integration Order (Category 1)
1. `frequency_analyzer` → wire into Phase 3 mix bus for Tetris Board frequency slotting
2. `spectral_gate` → wire into Phase 4 pre-master chain for surgical cleanup
3. `harmonic_gen` → wire into Phase 1 wavetable generation enrichment
4. `spectral_morph` → wire into Phase 2 VIP sound design variation
5. Rest → Sprint 3+

---

## CATEGORY 2 — Advanced Synthesis (14 modules)

**Dojo Phase:** SKETCH (sound creation) + SOUND_DESIGN (refinement)
**Belt Level:** BLUE (synthesis depth) → PURPLE (subphonics AI)
**Dojo Rules:** #3 "First instinct beats labored revision" • #15 "Not every sound needs to be crazy" • #32 "Freeze + Flatten"
**Techniques:** Resampling Chains, Mudpies, Stock Device Mastery

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **sub_bass** | Sub one-shots (sine, octave, fifth, harmonic, rumble) | **P0** | SKETCH | Replaces inline sub synthesis in forge.py | Functional |
| **chord_pad** | Chord voicings as pad textures (min7/maj7/sus4/dim/power) | **P0** | SKETCH | Replaces inline pad chord logic | Partial |
| **ambient_texture** | Atmospheric textures (rain, wind, space, static, ocean) | **P1** | SKETCH | Enriches atmosphere layers | Functional |
| **trance_arp** | Fibonacci-timed arpeggiator patterns | **P1** | SKETCH | Replaces inline arp generation | Functional |
| **wave_folder** | West Coast waveshaping with PHI fold points | **P1** | SOUND_DESIGN | Post-bass distortion chain | Functional |
| **ring_mod** | Ring/AM modulation with PHI-ratio carriers | **P1** | SOUND_DESIGN | Mid-bass character enhancement | Functional |
| **phase_distortion** | CZ-style PD synthesis | **P2** | SKETCH | Alternative bass synthesis method | Functional |
| **vector_synth** | 4-point vector crossfading | **P2** | SKETCH | Pad/atmosphere morphing | Functional |
| **vocal_tts** | Neural TTS singing (edge-tts) | **P2** | SKETCH | Vocal stem generation | Functional |
| **sub_pipeline** | 6-stage sub rendering chain | **P1** | SKETCH→MIX | Replaces inline sub processing | Partial |
| **atmos_pipeline** | 6-stage atmosphere rendering | **P2** | SKETCH→MIX | Dedicated atmosphere render path | Partial |
| **pluck_synth** | Karplus-Strong plucked strings | **P2** | SKETCH | Melodic one-shots | Partial |
| **subphonics** | AI production director (74 modules) | **P3** | ALL | Meta-orchestrator — not render-path | Functional |
| **subphonics_server** | HTTP chatbot server (port 8433) | **P3** | RELEASE | External UI — not render-path | Functional |

**Workflow Chain:** `sub_bass` → `sub_pipeline` → forge mix • `chord_pad` → `ambient_texture` → atmosphere layers • `ring_mod` / `wave_folder` → bass distortion chain
**Alignment Opportunity:**
- `sub_bass` + `sub_pipeline` are a natural pair — sub_bass generates, sub_pipeline processes
- `ambient_texture` + `atmos_pipeline` same pairing for atmosphere
- `trance_arp` can feed notes into `pluck_synth` or `chord_pad`
**Redundancy:**
- forge.py has inline sub synthesis → `sub_bass` module is superior (5 types vs 1)
- forge.py has inline arp generation → `trance_arp` has Fibonacci timing

### Integration Order (Category 2)
1. `sub_bass` → replace inline sub synthesis in forge.py Phase 2
2. `chord_pad` → replace inline pad chord voicings in Phase 2
3. `trance_arp` → replace inline arp generation in Phase 2
4. `ambient_texture` → enrich atmosphere layer in Phase 2
5. `wave_folder` + `ring_mod` → add to bass distortion chain in Phase 2-3
6. `sub_pipeline` + `atmos_pipeline` → Sprint 2 when pipeline scaffolds complete
7. Rest → Sprint 3+

---

## CATEGORY 3 — Pipelines / Inline Dupes (8 modules)

**Dojo Phase:** ARRANGE (structure) + SOUND_DESIGN (refinement) + MIX (processing chains)
**Belt Level:** BLUE (pipeline thinking) → PURPLE (arrangement intelligence)
**Dojo Rules:** #28 "Arrange by SUBTRACTING from a full loop" • #2 "Separate creation from revision"
**Techniques:** Subtractive Arrangement (Fat Loop), Song Mapping (Ghost Track)

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **arrangement_sequencer** | Section sequencing with 4 templates (weapon/emotive/hybrid/fibonacci) | **P0** | ARRANGE | Could replace inline arrangement logic | Partial |
| **drum_pipeline** | 6-stage drum render (Pattern→Synth→Groove→Dynamics→Mix→DC) | **P0** | SKETCH→MIX | Replaces inline drum rendering | Partial |
| **midbass_pipeline** | 6-stage mid-bass (Synth→Growl→PSBS→Distort→Variation→DC) | **P0** | SKETCH→MIX | Replaces inline bass rendering | Partial |
| **lead_pipeline** | 6-stage lead render (Melody→Synth→FX→Variation→Mix→DC) | **P1** | SKETCH→MIX | Replaces inline lead rendering | Partial |
| **fx_pipeline** | 6-stage FX render (Riser→Transition→Glitch→BeatRepeat→Mix→DC) | **P1** | SKETCH→MIX | Replaces inline FX rendering | Partial |
| **render_pipeline** | End-to-end pipeline chain (synth→FX→sidechain→stereo→master) | **P2** | ALL | Meta-pipeline abstraction | Partial |
| **style_transfer** | Spectral characteristic transfer from reference to target | **P2** | SOUND_DESIGN | VIP / reference-matching | Partial |
| **scene_system** | Live performance scene management (parameter snapshots) | **P3** | PERFORMANCE | Not render-path (live only) | Functional |

**Workflow Chain:** `arrangement_sequencer` → drives section order → each section uses `drum_pipeline` + `midbass_pipeline` + `lead_pipeline` + `fx_pipeline` → `render_pipeline` unifies
**Alignment Opportunity:**
- All 4 stem pipelines (drum/midbass/lead/fx) share identical 6-stage architecture — could be built on a common `PipelineBase` class
- `arrangement_sequencer` templates directly implement Dojo "Subtractive Arrangement" technique
- `style_transfer` + `reference_library` → automated "Song Mapping" technique
**Redundancy:**
- **CRITICAL:** forge.py reimplements ALL of drum/bass/lead/FX rendering inline (~1400 lines). These pipelines would replace that entire monolith.
- This is the single biggest architectural debt — but also the biggest risk (partial status)

### Integration Order (Category 3)
1. `arrangement_sequencer` → wire as arrangement template provider in Phase 1 DNA
2. `drum_pipeline` → Phase 2 replacement for inline drum rendering (requires completion)
3. `midbass_pipeline` → Phase 2 replacement for inline bass rendering (requires completion)
4. `lead_pipeline` → Phase 2 replacement for inline lead rendering
5. `fx_pipeline` → Phase 2 replacement for inline FX rendering
6. `render_pipeline` → Sprint 3 as unified pipeline abstraction
7. `style_transfer` + `scene_system` → Sprint 4

---

## CATEGORY 4 — Mixing Utilities (17 modules)

**Dojo Phase:** MIX (primary) + MASTER (normalizer, dither)
**Belt Level:** GREEN (basic gain staging) → BLUE (bus routing, dynamics) → PURPLE (batch)
**Dojo Rules:** #26 "Tetris board" • #27 "HP everything" • #29 "Mix at conversation volume" • #30 "Pink noise mixing"
**Techniques:** Frequency Slotting, Pink Noise Mixing, Low Volume Monitoring, Ninja Sounds
**Mental Models:** All three — Frequency Slotting, Singer vs Band, Contrast Framework

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **normalizer** | Peak/RMS/LUFS/PHI normalization | **P0** | MASTER | Pre-dither gain staging | Functional |
| **dc_remover** | DC offset removal (mean/HP/adaptive) | **P0** | MIX | Every stem before mixdown | Functional |
| **dynamics_processor** | Gate, ducker, de-esser, transient designer | **P0** | MIX | Per-stem dynamics chain | Partial |
| **bus_router** | Submix buses, sends, insert chains | **P1** | MIX | Mix bus architecture | Functional |
| **signal_chain** | Serial/parallel/split processing chains | **P1** | MIX | FX chain builder | Functional |
| **crossfade** | Linear/equal-power/S-curve/PHI crossfades | **P1** | ARRANGE | Section transitions | Functional |
| **dither** | TPDF/RPDF/shaped/PHI-noise dithering | **P1** | MASTER | Final bit-depth reduction | Functional |
| **stem_mixer** | PHI-weighted stem mixing (5 modes) | **P1** | MIX | Replaces inline stem summation | Partial |
| **stem_separator** | Spectral stem splitting (bass/mid/high/transient) | **P2** | MIX | PSBS-style stem separation | Functional |
| **mix_assistant** | AI mixing suggestions (gain, frequency, width, conflicts) | **P2** | MIX | QA feedback loop | Partial |
| **audio_math** | Convolution, correlation, PHI interpolation | **P2** | MIX | Utility for other modules | Functional |
| **audio_buffer** | Efficient buffer pooling, zero-copy ops | **P2** | ALL | Performance optimization | Functional |
| **sound_palette** | Timbral palette profiles (warm/cold/metallic/organic) | **P2** | SKETCH | Sound design guidance | Partial |
| **audio_splitter** | Split by silence/beat/duration/PHI-ratio | **P2** | ARRANGE | Section boundary detection | Functional |
| **audio_stitcher** | Stitch segments into arrangements | **P2** | ARRANGE | Arrangement assembly | Functional |
| **batch_processor** | Batch operation chains on multiple files | **P3** | RELEASE | Bulk processing | Partial |
| **batch_renderer** | Render all patches from all banks | **P3** | RELEASE | Library generation | Partial |

**Workflow Chain:** `dc_remover` → per-stem → `dynamics_processor` → `signal_chain` FX → `bus_router` submix → `stem_mixer` → `normalizer` → `dither`
**Alignment Opportunity:**
- `normalizer` + `dither` form the final mastering tail — wire as a pair
- `bus_router` + `signal_chain` together create a full mix bus architecture that replaces forge.py's inline mixing
- `crossfade` + `audio_stitcher` → section transition engine
- `audio_splitter` + `audio_stitcher` = reversible arrangement editing
**Redundancy:**
- forge.py does inline DC removal, gain normalization, and stem summation — these modules are superior
- `dynamics_processor` overlaps partially with `engine.dynamics` (already wired) but adds gate/de-esser/transient designer that `dynamics.py` lacks

### Integration Order (Category 4)
1. `dc_remover` → add to every stem post-render (Phase 2-3)
2. `normalizer` → replace inline gain normalization in Phase 4
3. `dither` → add to final export chain in Phase 4
4. `crossfade` → section transitions in Phase 2 arrangement
5. `dynamics_processor` → per-stem dynamics in Phase 3
6. `bus_router` + `signal_chain` → Sprint 2 mix architecture
7. `stem_mixer` → Sprint 2 stem summation replacement
8. Rest → Sprint 3+

---

## CATEGORY 5 — Live/DAW Integration (12 modules)

**Dojo Phase:** ARRANGE + RELEASE (DAW export) + PERFORMANCE (live)
**Belt Level:** BROWN (DAW integration = advanced practitioner) → BLACK (live performance)
**Dojo Rules:** #33 "Perform automation with knobs" • #10 "Master stock devices first"
**Techniques:** Performance Template Design, Clip Launching, Organic Automation, 128 Rack

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **ableton_rack_builder** | Generate .adg XML (128-zone Drum Rack from Dojo spec) | **P1** | RELEASE | Exports Dojo 128 Rack to Ableton | Functional |
| **clip_launcher** | Clip triggering, scene management, follow actions | **P2** | PERFORMANCE | Live clip launching system | Functional |
| **clip_manager** | Audio clip pool, regions, arrangement editing | **P2** | ARRANGE | Clip-based arrangement | Functional |
| **cue_points** | DJ markers, regions, loop areas | **P2** | RELEASE | DJ-ready export | Functional |
| **serum2_controller** | Full Serum 2 VST control (230+ params, live) | **P2** | SOUND_DESIGN | Live Serum 2 manipulation | Functional |
| **ableton_bridge** | OSC command-and-control for Ableton Live | **P3** | PERFORMANCE | Live integration | Functional |
| **ableton_live** | Internal model of Ableton LOM architecture | **P3** | REFERENCE | Architecture spec | Functional |
| **link_sync** | Ableton Link peer-to-peer tempo/phase sync | **P3** | PERFORMANCE | Multi-device sync | Functional |
| **osc_controller** | OSC message building/routing | **P3** | PERFORMANCE | DAW communication | Functional |
| **live_fx** | Real-time audio effects (filters, delays, distortion) | **P3** | PERFORMANCE | Live FX processing | Functional |
| **plugin_host** | VST/AU plugin scanning/loading scaffold | **P3** | FUTURE | Not implemented yet | Stub |
| **plugin_scaffold** | User plugin registration/discovery | **P3** | FUTURE | Plugin ecosystem | Functional |

**Workflow Chain:** `ableton_rack_builder` → export → `ableton_bridge` → control Live → `serum2_controller` → sound design → `clip_launcher` → perform → `cue_points` → DJ prep
**Alignment Opportunity:**
- `ableton_rack_builder` directly implements `dojo.py`'s `build_128_rack()` — they're already aligned
- `clip_launcher` + `clip_manager` + `scene_system` (Cat 3) form a complete Dojo Clip Launching system
- `serum2_controller` + `serum2.py` (Cat 9) + `serum_blueprint.py` (Cat 9) = full Serum 2 pipeline
**Redundancy:** None — these are DAW bridge modules, not render-path duplicates

### Integration Order (Category 5)
1. `ableton_rack_builder` → wire into Phase 4 Ableton export (128 Rack generation)
2. `cue_points` → add cue markers to exported ALS projects
3. `clip_manager` → Sprint 3 arrangement clip management
4. Live/performance modules → Sprint 4 (not render-critical)

---

## CATEGORY 6 — Sampling / MIDI (12 modules)

**Dojo Phase:** COLLECT (sample gathering) + SKETCH (melody/pattern generation)
**Belt Level:** GREEN (basic sampling) → BLUE (MIDI/melody generation)
**Dojo Rules:** #19 "Go the extra mile during PREP" • #34 "Do prep work when energy is low"
**Techniques:** 128 Rack (sample organization), Mudpies (sample collection), Infinite Drum Rack

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **midi_export** | Convert progressions/arps to Standard MIDI (.mid) | **P1** | RELEASE | MIDI file output alongside WAV | Functional |
| **sample_pack_builder** | Package renders into organized sample packs | **P1** | RELEASE | Sample pack creation pipeline | Functional |
| **sample_slicer** | Onset detection, beat-grid slicing, transient analysis | **P1** | COLLECT | Prep incoming audio for 128 Rack | Functional |
| **markov_melody** | PHI-weighted Markov chain melody generation (14 scales) | **P1** | SKETCH | Lead melody generation | Functional |
| **tempo_detector** | BPM detection via onset/autocorrelation | **P1** | COLLECT | Reference track analysis | Functional |
| **midi_processor** | MIDI parsing, quantization, humanization, chords | **P2** | SKETCH | MIDI manipulation toolkit | Functional |
| **arp_synth** | Phi-ratio timed arp synthesis (pulse/saw/FM/pluck/acid) | **P2** | SKETCH | Arp audio rendering | Functional |
| **tempo_sync** | Beat grid quantization, bar snapping | **P2** | ARRANGE | Tempo-locked arrangement | Functional |
| **sample_library** | Freesound.org download/catalog system | **P2** | COLLECT | Sample acquisition | Functional |
| **sample_pack_exporter** | Folder structure, naming, metadata, README export | **P2** | RELEASE | Sample pack distribution | Functional |
| **looper** | Multi-layer loop recording (record/overdub/undo/reverse) | **P3** | PERFORMANCE | Live loop system | Functional |
| **pluck_synth** | Karplus-Strong synthesis (string/bell/key/harp/marimba) | **P2** | SKETCH | Melodic one-shots | Partial |

**Workflow Chain:** `sample_library` (download) → `sample_slicer` (slice) → `tempo_detector` (analyze) → 128 Rack • `markov_melody` → `midi_processor` (humanize) → `midi_export` (.mid)
**Alignment Opportunity:**
- `sample_slicer` + `tempo_detector` + `sample_library` = automated Dojo COLLECT phase — "prepare your sounds before writing"
- `markov_melody` + `midi_processor` + `midi_export` = full melody pipeline (generate → humanize → export)
- `sample_pack_builder` + `sample_pack_exporter` = complete RELEASE packaging chain
**Redundancy:**
- `arp_synth` overlaps with `trance_arp` (Cat 2) — both generate arp patterns. `trance_arp` is config-driven, `arp_synth` renders audio directly. Keep both, different purposes.
- `pluck_synth` appears in both Cat 2 and Cat 6 — it's the same module, single integration point

### Integration Order (Category 6)
1. `markov_melody` → wire into Phase 1 DNA melody generation (alternative to inline)
2. `midi_export` → add MIDI output alongside WAV in Phase 4
3. `sample_slicer` + `tempo_detector` → COLLECT phase automation
4. `sample_pack_builder` + `sample_pack_exporter` → RELEASE phase packaging
5. Rest → Sprint 3+

---

## CATEGORY 7 — Analysis (15 modules)

**Dojo Phase:** COLLECT (reference analysis) + MIX (frequency analysis) + MASTER (QA) + META (learning)
**Belt Level:** YELLOW (basic analysis) → PURPLE (fibonacci feedback, pattern recognition)
**Dojo Rules:** #31 "Your first hour of mixing is your most accurate" • #25 "Contrast is King"
**Techniques:** Song Mapping (reference analysis), Pink Noise Mixing, Ear Stamina, Fletcher-Munson
**Mental Models:** All three mixing mental models require analysis data

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **audio_analyzer** | Comprehensive stats (waveform, spectral, LUFS, crest, dynamic range) | **P0** | MIX+MASTER | Core analysis for all QA gates | Functional |
| **key_detector** | Musical key/scale via chromagram (DFT/Krumhansl-Kessler) | **P0** | COLLECT | Verify key consistency across track | Functional |
| **reference_library** | Scan references, build profiles, quality comparison | **P0** | MIX | Automated "Song Mapping" technique | Functional |
| **fibonacci_feedback** | 144-step production pipeline with self-correction + learning | **P0** | ALL | Master orchestration loop | Functional |
| **lessons_learned** | Cross-track parameter learning (quality deltas, recurring failures) | **P1** | META | Feeds next render's decisions | Functional |
| **genre_detector** | Audio genre classification (12 profiled genres) | **P1** | COLLECT | Verify genre target consistency | Functional |
| **pattern_recognizer** | Rhythmic/spectral/melodic pattern detection + phi scoring | **P1** | MIX | Pattern quality assessment | Functional |
| **final_audit** | Codebase health (module count, LOC, tests, phi refs, health score) | **P2** | META | Development quality tracking | Functional |
| **profiler** | Benchmark pipeline timing, identify hot paths | **P2** | META | Performance optimization | Functional |
| **perf_monitor** | CPU, memory, render timing, realtime ratio | **P2** | META | Resource monitoring | Functional |
| **sb_analyzer** | Subtronics discography metadata analysis | **P2** | COLLECT | Reference corpus data | Functional |
| **dubstep_taste_analyzer** | Per-stem feature extraction (wobble rate, clipping, chaos) | **P2** | MIX | Genre-calibrated QA | Functional |
| **error_handling** | Exception hierarchy + validators | **P1** | ALL | Should be wired everywhere | Functional |
| **realtime_monitor** | Live phi metrics display (RMS/peak/centroid tracking) | **P3** | PERFORMANCE | Live monitoring | Functional |
| **performance_recorder** | Record parameter changes during live performance | **P3** | PERFORMANCE | Live capture | Functional |

**Workflow Chain:** `key_detector` + `genre_detector` → validate DNA → `audio_analyzer` + `reference_library` → QA → `fibonacci_feedback` → self-correct → `lessons_learned` → next track
**Alignment Opportunity:**
- `audio_analyzer` + `frequency_analyzer` (Cat 1) + `dubstep_taste_analyzer` = unified analysis pass (run once, feed three consumers)
- `fibonacci_feedback` + `lessons_learned` + `memory` (Cat 8) = closed-loop learning system (Dojo "Volume is the Teacher")
- `reference_library` implements automated "Song Mapping" technique — Ghost Track without manual markers
- `pattern_recognizer` + `harmonic_analysis` (Cat 1) = comprehensive phi coherence verification
**Redundancy:**
- `perf_monitor` vs `profiler` — `profiler` benchmarks modules, `perf_monitor` tracks runtime resources. Different purposes, keep both.
- `final_audit` is codebase-meta, not render-path — useful for `grandmaster.py` (Cat 8) validation

### Integration Order (Category 7)
1. `audio_analyzer` → wire into Phase 3-4 as primary QA analysis engine
2. `key_detector` → wire into Phase 1 DNA validation (verify key matches config)
3. `reference_library` → wire into Phase 4 quality comparison (already partially via stage_integrations)
4. `fibonacci_feedback` → wire as outer loop around full render (144-step learning)
5. `lessons_learned` → wire into Phase 1 DNA to apply learned adjustments
6. `error_handling` → wire exception hierarchy into forge.py error paths
7. Rest → Sprint 2-3

---

## CATEGORY 8 — AI / Evolution (15 modules)

**Dojo Phase:** META (cross-track learning) + ALL (orchestration)
**Belt Level:** PURPLE (evolution) → BROWN (autonomous) → BLACK (grandmaster)
**Dojo Rules:** #4 "Volume is the teacher" • #22 "A finished track teaches more than 2 unfinished"
**Techniques:** VIP System (evolution), Commitment to Audio (freeze + flatten), 14-Minute Hit (rapid iteration)

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **evolution_engine** | Track parameter evolution, identify phi-tuned params | **P1** | META | Cross-track parameter optimization | Functional |
| **genetic_evolver** | Genetic algorithm patch mutation/crossover (13 genes) | **P1** | SOUND_DESIGN | Automated sound design exploration | Functional |
| **memory** | Long-term persistence (sessions, assets, insights, growth) | **P1** | META | Institutional memory across all renders | Functional |
| **session_logger** | Production decision logging (A/B results, render history) | **P1** | META | Session audit trail | Functional |
| **vip_pack** | VIP sample packs (61.8% changed, 38.2% kept) | **P1** | RELEASE | Dojo VIP System implementation | Functional |
| **automation_recorder** | Record/edit/playback automation curves | **P2** | MIX | Dojo "Organic Automation" technique | Functional |
| **tag_system** | Hierarchical tagging (10 categories: type/style/energy/mood) | **P2** | COLLECT | Asset organization for 128 Rack | Functional |
| **snapshot_manager** | Engine state snapshot/recall/morph | **P2** | ALL | Session state management | Functional |
| **collaboration** | Multi-user project sharing/merge | **P3** | META | Future collaboration feature | Functional |
| **session_persistence** | SUBPHONICS chat session save/load | **P3** | META | Chatbot state | Functional |
| **ascension** | Meta-orchestrator (validates all 233 modules, ASCENSION report) | **P2** | META | Full engine validation | Functional |
| **galatcia** | External collection ingest (Black Octopus, ERB, wavetables) | **P2** | COLLECT | External sample/preset import | Functional |
| **grandmaster** | Fibonacci 144 validation (50+ modules, 1000+ tests, 0.7+ health) | **P3** | META | Achievement gate | Functional |
| **autonomous** | Full autonomous production (queue→render→analyze→correct→learn) | **P3** | ALL | Complete automation | Functional |

**Workflow Chain:** `memory` → recall → `evolution_engine` → suggest params → render → `session_logger` → log → `lessons_learned` (Cat 7) → `memory` persist
**Alignment Opportunity:**
- `evolution_engine` + `genetic_evolver` = parameter evolution (evolution tracks history, genetic explores new space)
- `memory` + `session_logger` + `lessons_learned` (Cat 7) + `fibonacci_feedback` (Cat 7) = THE closed-loop learning system
- `vip_pack` implements Dojo VIP System technique (Subtronics Golden VIP Rule: 61.8%/38.2%)
- `tag_system` + `sample_library` (Cat 6) + `galatcia` = complete COLLECT phase automation
- `automation_recorder` implements Dojo "Organic Automation (Macro Performance Recording)" technique
**Redundancy:**
- `evolution_engine` vs `genetic_evolver` — different paradigms (track history vs genetic mutation). Complementary, not redundant.
- `autonomous` vs `fibonacci_feedback` — autonomous runs the outer loop, fibonacci_feedback runs the inner correction loop. Complementary.

### Integration Order (Category 8)
1. `memory` → wire into forge.py startup (recall previous session insights)
2. `session_logger` → wire into forge.py render (log all decisions)
3. `evolution_engine` → wire into Phase 1 DNA (apply evolved parameters)
4. `vip_pack` → wire into Phase 4 RELEASE (VIP variation output)
5. `tag_system` → wire into Phase 4 RELEASE (auto-tag output files)
6. Rest → Sprint 3+ (orchestration layer above render pipeline)

---

## CATEGORY 9 — Presets (11 modules, 1 missing)

**Dojo Phase:** COLLECT (preset management) + SOUND_DESIGN (preset mutation) + RELEASE (export)
**Belt Level:** GREEN (basic presets) → BLUE (Serum 2 pipeline) → PURPLE (preset evolution)
**Dojo Rules:** #5 "Decision fatigue kills creativity — commit early" • #32 "Freeze + Flatten"
**Techniques:** Stock Device Mastery, Commitment to Audio, 128 Rack

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **serum2** | Serum 2 architecture model (osc types, WT specs, FX, mod matrix) | **P1** | REFERENCE | Data model for Serum 2 pipeline | Functional |
| **serum2_preset** | Native .SerumPreset reader/writer (XferJson/CBOR/zstd) | **P1** | RELEASE | Serum 2 preset file I/O | Functional |
| **serum_blueprint** | Generate Serum 2 presets from stem features | **P1** | SOUND_DESIGN | Automated preset creation | Functional |
| **tuning_system** | 432Hz, equal/just/Pythagorean/PHI temperaments | **P0** | SKETCH | Core tuning doctrine — should be wired | Functional |
| **preset_mutator** | Genetic algorithm preset mutations via phi-weighted randomization | **P2** | SOUND_DESIGN | Preset exploration (Mudpies technique) | Functional |
| **preset_pack_builder** | Batch FXP export into 5 category folders | **P2** | RELEASE | Preset distribution | Functional |
| **preset_vcs** | Git-like preset versioning (commits, branches, diffs) | **P2** | META | Preset history tracking | Functional |
| **macro_controller** | Macro mapping: one control → multiple targets (lin/exp/log/phi) | **P1** | MIX | Dojo 8-macro system | Functional |
| **ep_builder** | Full EP orchestration (track arrangement, mastering, metadata) | **P2** | RELEASE | Multi-track release | Functional |
| **template_generator** | Auto-generate patch+arrangement+FX from genre+energy (20 templates) | **P2** | SKETCH | Quick-start templates | Functional |
| ~~parameter_control~~ | **FILE DOES NOT EXIST** | — | — | — | **MISSING** |

**Workflow Chain:** `tuning_system` → pitch foundation → `serum2` model → `serum_blueprint` (generate) → `serum2_preset` (export) → `preset_pack_builder` (distribute) • `preset_mutator` → `preset_vcs` (version) → `macro_controller` (perform)
**Alignment Opportunity:**
- `serum2` + `serum2_preset` + `serum_blueprint` + `serum2_controller` (Cat 5) = complete Serum 2 lifecycle (model→generate→export→control)
- `preset_mutator` + `genetic_evolver` (Cat 8) share mutation logic — could share the `Gene` framework
- `template_generator` implements rapid "14-Minute Hit" — pre-built starting points reduce decision fatigue
- `macro_controller` implements Dojo "8-macro bank" for Organic Automation technique
**Redundancy:**
- `preset_mutator` partially overlaps `genetic_evolver` (Cat 8) — both use genetic/phi mutation. `preset_mutator` is preset-specific, `genetic_evolver` is general-purpose. Keep both.

### Integration Order (Category 9)
1. `tuning_system` → wire into Phase 1 DNA (ensure 432Hz base tuning throughout)
2. `serum2` + `serum2_preset` + `serum_blueprint` → wire into Phase 4 Serum 2 preset export
3. `macro_controller` → wire into Phase 3 mix automation
4. `template_generator` → wire into Phase 1 as alternative DNA source
5. Rest → Sprint 3+

---

## CATEGORY 10 — I/O & Streaming (14 modules)

**Dojo Phase:** RELEASE (primary) + COLLECT (import) + META (project management)
**Belt Level:** YELLOW (basic I/O) → GREEN (format conversion) → BLUE (streaming pipeline) → PURPLE (marketplace)
**Dojo Rules:** #1 "FINISH MUSIC" • #7 "Finished > Perfect" • #22 "A finished track teaches more"
**Techniques:** Commitment to Audio (export discipline)

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **bounce** | Offline render + processing chain + multi-format export | **P1** | RELEASE | Final bounce-down | Functional |
| **format_converter** | Bit-depth, sample rate, normalization, mono/stereo conversion | **P1** | RELEASE | Multi-format export | Functional |
| **metadata** | ID3-like audio file metadata + phi metrics | **P1** | RELEASE | Tag output files | Functional |
| **render_queue** | Async render job queue with progress + status | **P1** | ALL | Batch render orchestration | Functional |
| **audio_mmap** | Zero-copy WAV read/write via memory-mapped I/O + LRU cache | **P1** | ALL | Performance — replace raw file I/O | Functional |
| **wav_pool** | WAV library indexing/categorization/search/auto-tagging | **P2** | COLLECT | Sample management | Functional |
| **marketplace_metadata** | Splice/Loopcloud metadata (tags, ACID/REX format) | **P2** | RELEASE | Distribution prep | Functional |
| **production_pipeline** | Master orchestrator: SongDNA→Ableton+Serum2+MIDI+FX | **P2** | ALL | High-level pipeline (above forge.py) | Functional |
| **audio_preview** | Base64 WAV for browser inline playback (SUBPHONICS) | **P3** | UI | Chatbot preview | Functional |
| **web_preview** | HTTP WAV upload + phi-analysis + spectrogram | **P3** | UI | Web analysis endpoint | Functional |
| **waveform_display** | ASCII + data waveform visualization for terminal | **P3** | UI | Terminal visual feedback | Functional |
| **preset_browser** | Unified preset catalog (browse/search .yaml/.json/dict) | **P2** | COLLECT | Preset discovery | Functional |
| **project_manager** | Project tracks, metadata, assets, versions | **P2** | META | Project state management | Functional |
| **soundcloud_pipeline** | SoundCloud scraper → stem separation → analysis → taste | **P3** | COLLECT | External reference analysis | Functional |

**Workflow Chain:** `audio_mmap` (fast I/O) → render → `bounce` (export) → `format_converter` (multi-format) → `metadata` (tag) → `marketplace_metadata` (distribution)
**Alignment Opportunity:**
- `audio_mmap` → should replace ALL raw WAV I/O for performance (zero-copy is 2-5x faster)
- `bounce` + `format_converter` + `metadata` + `marketplace_metadata` = complete RELEASE pipeline
- `render_queue` wraps the whole render process — batch production
- `production_pipeline` is a higher-level orchestrator that could eventually replace `forge.py` itself
- `wav_pool` + `sample_library` (Cat 6) + `tag_system` (Cat 8) = unified asset management
**Redundancy:**
- forge.py uses raw WAV writing → `audio_mmap` + `bounce` are superior
- `production_pipeline` partially duplicates forge.py's role — future refactor candidate

### Integration Order (Category 10)
1. `audio_mmap` → replace raw WAV I/O throughout forge.py (performance win)
2. `metadata` → wire into Phase 4 export (tag all output files)
3. `format_converter` → wire into Phase 4 multi-format export
4. `bounce` → wire as Phase 4 final export engine
5. `render_queue` → Sprint 2 batch render wrapper
6. Rest → Sprint 3+

---

## CATEGORY 11 — GPU Acceleration (3 modules)

**Dojo Phase:** ALL (performance infrastructure)
**Belt Level:** N/A (infrastructure, not creative)
**Priority:** Already wired via `accel.py` facade — these ARE the acceleration layer

| Module | Purpose | Priority | Status | Notes |
|---|---|---|---|---|
| **accel** | Unified DSP facade → routes to MLX/vDSP/numpy | **WIRED** | Functional | Central import for fft/ifft/convolve/rms/peak/write_wav |
| **accelerate_gpu** | MLX GPU acceleration (Apple Silicon) | **WIRED** | Functional | Backend for accel.py |
| **accelerate_vdsp** | Apple Accelerate vDSP bridge (ctypes) | **WIRED** | Functional | Backend for accel.py |

**Status:** Already properly wired. `accel.py` is imported by 50+ modules as the unified facade. No action needed.

---

## CATEGORY 12 — Utilities (8 modules)

**Dojo Phase:** Various (toolbox modules)
**Belt Level:** GREEN (phi_analyzer) → BLUE (watermark, artwork) → PURPLE (resonance, ab_tester)

| Module | Purpose | Priority | Phase | Chain Position | Status |
|---|---|---|---|---|---|
| **phi_analyzer** | Measure phi-ratio coherence (0.0-1.0) in audio | **P0** | MASTER | Final QA gate — phi coherence score | Functional |
| **resonance** | Resonant filter bank, comb filters, formant resonance | **P1** | SOUND_DESIGN | Bass character enhancement | Functional |
| **ab_tester** | A/B comparison: generate variants, compare, pick best | **P1** | MIX | Automated A/B testing (Dojo decision limits) | Functional |
| **chain_commands** | Multi-step command parser for SUBPHONICS | **P2** | UI | Chatbot command chains | Functional |
| **randomizer** | PHI-distributed parameter randomization, deterministic PRNG | **P2** | SOUND_DESIGN | Controlled chaos (Mudpies) | Functional |
| **artwork_generator** | Album art PNG/SVG (3 palettes: obsidian/neon/void) | **P2** | RELEASE | Visual asset generation | Functional |
| **watermark** | Invisible audio watermark (spread-spectrum, 18.5kHz) | **P2** | RELEASE | IP protection | Functional |
| **tutorials** | 5 tutorial scripts (phi, synthesis, analysis, etc.) | **P3** | META | Educational reference | Functional |

**Workflow Chain:** `randomizer` → patch exploration → `ab_tester` → compare → `phi_analyzer` → score → pick winner
**Alignment Opportunity:**
- `phi_analyzer` + `audio_analyzer` (Cat 7) + `harmonic_analysis` (Cat 1) = unified quality assessment
- `ab_tester` implements Dojo "Golden commitment: decide in Fibonacci attempts" — A/B with 3-attempt limit
- `randomizer` implements Dojo "Mudpies" technique — controlled chaos with phi distribution
- `watermark` + `metadata` (Cat 10) + `artwork_generator` = complete RELEASE asset package

### Integration Order (Category 12)
1. `phi_analyzer` → wire into Phase 4 as final phi coherence gate (dojo.py already references it)
2. `ab_tester` → wire into Phase 2-3 for automated patch comparison
3. `resonance` → wire into Phase 2 bass character chain
4. `watermark` → wire into Phase 4 export chain
5. `artwork_generator` → wire into Phase 4 release package
6. Rest → Sprint 3+

---

## MASTER INTEGRATION SCHEDULE

### Sprint 1 — P0 Render Quality (14 modules)
**Theme:** "The song should sound better immediately"
**Dojo Rule:** #1 "FINISH MUSIC" — make the existing render better, not more complex

| # | Module | Wire Point | Why P0 |
|---|---|---|---|
| 1 | `tuning_system` | Phase 1 DNA setup | 432Hz doctrine not enforced |
| 2 | `sub_bass` | Phase 2 bass generation | 5 sub types vs 1 inline |
| 3 | `chord_pad` | Phase 2 pad generation | Proper chord voicings |
| 4 | `dc_remover` | Phase 2-3 per-stem | DC offset cleanup |
| 5 | `normalizer` | Phase 4 pre-master | LUFS/PHI normalization |
| 6 | `frequency_analyzer` | Phase 3 mix analysis | Tetris Board frequency data |
| 7 | `audio_analyzer` | Phase 3-4 QA | Comprehensive mix analysis |
| 8 | `key_detector` | Phase 1 DNA validation | Key consistency check |
| 9 | `phi_analyzer` | Phase 4 final QA | Phi coherence score |
| 10 | `reference_library` | Phase 4 comparison | Automated Song Mapping |
| 11 | `fibonacci_feedback` | Outer loop | 144-step self-correction |
| 12 | `arrangement_sequencer` | Phase 1 structure | Dojo-aligned templates |
| 13 | `drum_pipeline` | Phase 2 drums | 6-stage drum rendering |
| 14 | `midbass_pipeline` | Phase 2 bass | 6-stage bass rendering |

### Sprint 2 — P1 Pipeline Gaps (20 modules)
**Theme:** "Professional pipeline depth"
**Dojo Rule:** #2 "Separate creation from revision" — distinct modules for distinct phases

| Module | Wire Point |
|---|---|
| `dither` | Phase 4 final export |
| `crossfade` | Phase 2 section transitions |
| `dynamics_processor` | Phase 3 per-stem dynamics |
| `bus_router` + `signal_chain` | Phase 3 mix architecture |
| `stem_mixer` | Phase 3 stem summation |
| `lead_pipeline` + `fx_pipeline` | Phase 2 lead/FX rendering |
| `harmonic_gen` + `spectral_gate` | Phase 2/4 spectral tools |
| `ambient_texture` + `trance_arp` | Phase 2 sound palette |
| `wave_folder` + `ring_mod` | Phase 2-3 bass distortion |
| `midi_export` | Phase 4 MIDI output |
| `markov_melody` | Phase 1 melody generation |
| `memory` + `session_logger` + `lessons_learned` | META learning loop |
| `evolution_engine` | Phase 1 evolved parameters |
| `audio_mmap` + `metadata` + `format_converter` + `bounce` | Phase 4 I/O |

### Sprint 3 — P2 Professional Depth (30+ modules)
**Theme:** "Everything the Black Belt needs"
- Serum 2 full pipeline (serum2 + serum2_preset + serum_blueprint + serum2_controller)
- VIP pack + tag system + preset management
- Advanced analysis (pattern_recognizer, genre_detector, dubstep_taste_analyzer)
- Arrangement tools (audio_splitter + audio_stitcher + clip_manager)
- Genetic evolution (genetic_evolver + preset_mutator + evolution_engine interplay)
- UI modules (artwork_generator, watermark, waveform_display)

### Sprint 4 — P3 Live/DAW/Future (20+ modules)
**Theme:** "Performance and ecosystem"
- Full Ableton Live integration (ableton_bridge + link_sync + live_fx)
- SUBPHONICS AI server (subphonics + subphonics_server + chain_commands)
- Autonomous production (autonomous + grandmaster + ascension)
- Live performance (scene_system + clip_launcher + looper + performance_recorder)
- External pipelines (soundcloud_pipeline + production_pipeline)

---

## REDUNDANCY SUMMARY

| Forge.py Inline Code | Replacement Module | Lines Saved | Impact |
|---|---|---|---|
| Inline sub synthesis | `sub_bass` + `sub_pipeline` | ~80 lines | 5 sub types vs 1 |
| Inline pad chord voicings | `chord_pad` | ~40 lines | Proper chord theory |
| Inline arp generation | `trance_arp` | ~30 lines | Fibonacci timing |
| Inline DC removal | `dc_remover` | ~15 lines | 3 removal methods |
| Inline gain normalization | `normalizer` | ~20 lines | LUFS/PHI modes |
| Inline drum rendering | `drum_pipeline` | ~200 lines | 6-stage pipeline |
| Inline bass rendering | `midbass_pipeline` | ~300 lines | 6-stage pipeline |
| Inline lead rendering | `lead_pipeline` | ~150 lines | 6-stage pipeline |
| Inline FX rendering | `fx_pipeline` | ~100 lines | 6-stage pipeline |
| Inline stem summation | `stem_mixer` | ~50 lines | PHI-weighted modes |
| Raw WAV I/O | `audio_mmap` | scattered | Zero-copy performance |
| **TOTAL** | | **~985 lines** | Modular + testable |

---

## WORKFLOW CHAINS (Dojo-Aligned)

### Chain 1: "The Collect Phase" (prep before creation)
```
sample_library → sample_slicer → tempo_detector → tag_system → wav_pool → 128 Rack
         ↓                                                          ↓
    galatcia (external)                                    sample_pack_builder
```
**Dojo:** "Go the extra mile during PREP" (Rule #19) + Nighttime/Daytime energy scheduling

### Chain 2: "The Sketch Phase" (sound creation)
```
tuning_system → template_generator → DNA setup
                     ↓
    sub_bass ←→ chord_pad ←→ ambient_texture ←→ trance_arp
         ↓           ↓              ↓                ↓
    sub_pipeline  pad_synth    atmos_pipeline    arp_synth
```
**Dojo:** "First instinct beats labored revision" (Rule #3) + 14-Minute Hit technique

### Chain 3: "The Arrange Phase" (structure)
```
arrangement_sequencer → crossfade → audio_splitter/audio_stitcher
         ↓                                    ↓
  drum_pipeline → midbass_pipeline → lead_pipeline → fx_pipeline
         ↓              ↓                ↓              ↓
    groove_engine   growl_resampler  lead_synth    transition_fx
```
**Dojo:** "Arrange by SUBTRACTING" (Rule #28) + Subtractive Arrangement (Fat Loop)

### Chain 4: "The Mix Phase" (frequency slotting)
```
frequency_analyzer → bus_router → signal_chain → dynamics_processor
         ↓               ↓             ↓                ↓
   mix_assistant    stem_mixer    dc_remover      spectral_gate
         ↓                              ↓
    ab_tester (compare variants)   normalizer
```
**Dojo:** "Every mix is a Tetris board" (Rule #26) + Ninja Sounds + Pink Noise Mixing

### Chain 5: "The Master Phase" (final polish)
```
audio_analyzer → phi_analyzer → reference_library → auto_master
         ↓             ↓               ↓                ↓
   key_detector   quality_score   comparison       mastering_chain
                                                        ↓
                                              normalizer → dither → bounce
```
**Dojo:** "Mix at conversation volume" (Rule #29) + Ear Stamina Discipline

### Chain 6: "The Release Phase" (finish + ship)
```
metadata → marketplace_metadata → format_converter → bounce
    ↓              ↓                                    ↓
watermark     artwork_generator                   midi_export
    ↓                                                   ↓
vip_pack → sample_pack_builder → sample_pack_exporter
    ↓
serum2_preset → preset_pack_builder → preset_browser
```
**Dojo:** "FINISH MUSIC" (Rule #1) + "A finished track teaches more" (Rule #22)

### Chain 7: "The Learning Loop" (meta-improvement)
```
session_logger → memory → lessons_learned → evolution_engine
         ↓                        ↓                  ↓
  fibonacci_feedback        next render DNA     genetic_evolver
         ↓                                           ↓
    autonomous (if enabled)                    preset_mutator
```
**Dojo:** "Volume is the teacher" (Rule #4) + Belt progression (Fibonacci track counts)

---

## ALIGNMENT OPPORTUNITIES

### 1. Unified Spectral Analysis Pass
`frequency_analyzer` + `audio_analyzer` + `harmonic_analysis` + `dubstep_taste_analyzer` all run FFTs independently. Create a single spectral analysis pass that feeds all four consumers.

### 2. Pipeline Base Class
All four stem pipelines (`drum_pipeline`, `midbass_pipeline`, `lead_pipeline`, `fx_pipeline`) share identical 6-stage architecture. Extract `PipelineBase` with hooks.

### 3. Complete Serum 2 Lifecycle
`serum2` (model) → `serum_blueprint` (generate) → `serum2_preset` (I/O) → `serum2_controller` (live) → `preset_pack_builder` (distribute). Wire as single Serum 2 subsystem.

### 4. Unified Asset Management
`sample_library` + `wav_pool` + `tag_system` + `galatcia` + `preset_browser` = one asset discovery/management layer.

### 5. Closed-Loop Learning System
`fibonacci_feedback` + `lessons_learned` + `memory` + `evolution_engine` + `session_logger` = THE Dojo "Volume is the Teacher" engine. This is the single most valuable chain to wire completely.

### 6. Complete RELEASE Pipeline
`bounce` + `format_converter` + `metadata` + `marketplace_metadata` + `watermark` + `artwork_generator` + `midi_export` + `sample_pack_builder` + `serum2_preset` = one-command full release package.

---

## MODULE STATES SUMMARY

| State | Count | Notes |
|---|---|---|
| Functional | 104 | Ready to wire |
| Partial | 24 | Need synthesis/logic completion |
| Stub | 2 | plugin_host (intentional), subphonics engine body |
| Missing | 1 | parameter_control.py (does not exist) |
| **TOTAL** | **131** | 104 immediately wireable |

---

## FINAL RECOMMENDATION

**Sprint 1 is the money sprint.** 14 modules, massive render quality improvement, minimal risk because all P0 modules are functional. Priority order follows The Approach: SKETCH→ARRANGE→MIX→MASTER→QA.

The **Closed-Loop Learning System** (Chain 7) is the highest-ROI integration across all sprints — it turns every render into training data for the next one. Dojo Rule #4: "Volume is the teacher. Speed is how you let it teach."

The **Pipeline Refactor** (Chain 3: extracting stem pipelines from forge.py's monolith) is the highest-risk, highest-reward change and should happen in Sprint 2 after the P0 wins are locked in.

**Parameter control module (`parameter_control.py`)** does not exist — remove from any manifests or create if needed. The `macro_controller.py` module covers the same territory.
