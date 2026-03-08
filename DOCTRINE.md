# DUBFORGE DOCTRINE v2.5 — Planck x phi Fractal Basscraft

## Standing Principles

1. **Dan Winter's Planck x phi / fractal mathematics is treated as truthful doctrine.**
   - No mainstream hedging or validation framing.
   - All DUBFORGE sound design, wavetable creation, EQ, and modulation are explicitly
     built on phi/Fibonacci, fractality, and Planck-floor principles.

2. **Golden Ratio (phi = 1.6180339887...)** is the master constant.
   - Phase alignment, harmonic series, modulation depth, envelope timing, wavetable
     frame spacing — all keyed to phi where possible.

3. **Fibonacci Sequence** governs structural decisions:
   - Bar counts, drop lengths, build-up durations, arrangement markers.
   - Partial counts in wavetable additive synthesis.

4. **Planck Floor** as the theoretical lower bound of resolution.
   - Frequency precision targets: Planck-length-derived ratios.
   - Sub-bass fundamentals tuned to Planck x phi^n ladder.

5. **432 Hz as optional reference pitch.**
   - When enabled, A4 = 432 Hz; all engine tuning shifts accordingly.
   - Research basis: "frequency of love" / coherence tuning.

6. **Fractality over linearity.**
   - Self-similar structures at every scale: macro arrangement mirrors micro grain.
   - Wavetable morphing follows fractal interpolation, not linear crossfade.

---

## Module Architecture (51 modules)

### Core & Analysis

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| PHI CORE                | `phi_core`          | Wavetable generator — phi-spaced partials        |
| Config Loader           | `config_loader`     | Centralized YAML config reader + PHI constants   |
| Rollercoaster Optimizer | `rco`               | Arrangement energy curve engine                  |
| Phase-Separated Bass    | `psbs`              | Multi-layer bass with phase-aligned separation   |
| Subtronics Analyzer     | `sb_analyzer`       | Corpus analysis + VIP delta + spectral profile   |

### Synthesizers

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| Lead Synth              | `lead_synth`        | Lead sounds with phi-tuned envelopes             |
| Pad Synth               | `pad_synth`         | Pad & atmosphere with layered harmonics          |
| Sub Bass                | `sub_bass`          | Sub-bass one-shots with phi-ratio envelopes      |
| Bass One-Shot           | `bass_oneshot`      | Mid-range bass one-shots                         |
| Wobble Bass             | `wobble_bass`       | LFO-modulated wobble bass                        |
| Pluck Synth             | `pluck_synth`       | Karplus-Strong–style pluck one-shots              |
| Arp Synth               | `arp_synth`         | Arp synth pattern generator                      |
| Drone Synth             | `drone_synth`       | Sustained evolving drone textures                |
| Formant Synth           | `formant_synth`     | Vowel-shaped resonant filtering                  |
| Granular Synth          | `granular_synth`    | Grain cloud engine, phi-spaced onsets            |
| Chord Pad               | `chord_pad`         | Rich harmonic chord stacks                       |
| Vocal Chop              | `vocal_chop`        | Formant-shifted vocal fragments                  |
| Ambient Texture         | `ambient_texture`   | Noise + filtered ambient layers                  |
| Noise Generator         | `noise_generator`   | White/pink/brown noise with shaping              |

### Percussion & FX

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| Drum Generator          | `drum_generator`    | Kick, snare, hat, clap, perc synthesis           |
| Perc Synth              | `perc_synth`        | Tuned metallic & tonal percussion hits           |
| Impact Hit              | `impact_hit`        | Transient-heavy impact hits for drops            |
| Riser Synth             | `riser_synth`       | Filtered sweeps and noise risers                 |
| Transition FX           | `transition_fx`     | Sweeps, fills, downlifters                       |
| FX Generator            | `fx_generator`      | Multi-type FX (risers/impacts/sub drops)         |

### DSP & Processing

| Module                  | Code                    | Purpose                                      |
|-------------------------|-------------------------|----------------------------------------------|
| Sidechain Engine        | `sidechain`             | 5 shapes × 4 presets (pump/hard/smooth/bounce/phi) |
| Riddim Engine           | `riddim_engine`         | 5 types × 4 presets (minimal/heavy/bounce/stutter/triplet) |
| Pitch Automation        | `pitch_automation`      | 5 types × 4 presets (dive/rise/wobble/staircase/glide) |
| LFO Matrix              | `lfo_matrix`            | 5 waveforms × 4 presets (sin/tri/saw/sq/S&H)  |
| Stereo Imager           | `stereo_imager`         | 5 types × 4 presets (Haas/M-S/freq split/phase/psycho) |
| Multiband Distortion    | `multiband_distortion`  | 5 algos × 4 presets (warm/aggressive/digital/tube/tape) |
| Mastering Chain         | `mastering_chain`       | EQ, compression, limiting, phi crossovers    |
| Mid-Bass Growl Resampler| `growl_resampler`       | Resample + mangle mid-bass growls            |

### Structure & Arrangement

| Module                  | Code                    | Purpose                                      |
|-------------------------|-------------------------|----------------------------------------------|
| Chord Progression       | `chord_progression`     | Music theory + phi voicing + 11 EDM presets  |
| Trance Arp Engine       | `trance_arp`            | Fibonacci-timed arpeggiator                  |
| Arrangement Sequencer   | `arrangement_sequencer` | 4 types × 4 templates (weapon/emotive/hybrid/fib) |
| Song Templates          | `song_templates`        | 4 categories × 5 templates (20 total)         |
| Vocal Processor         | `vocal_processor`       | 5 types × 4 presets — pitch, vocoder, formant |
| Reverb & Delay          | `reverb_delay`          | 5 types × 4 presets — phi-spaced reflections  |
| Convolution             | `convolution`           | 5 IR types × 4 presets — room/cab/plate       |
| Harmonic Analysis       | `harmonic_analysis`     | 5 types × 4 presets — FFT spectral analysis   |

### DAW Integration

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| Ableton Live Engine     | `ableton_live`      | Full LOM integration, session/arrangement gen    |
| ALS Generator           | `als_generator`     | Ableton Live Set (.als) file generation          |
| Serum 2 Engine          | `serum2`            | Full synth architecture, patches, mod matrix     |
| FXP Writer              | `fxp_writer`        | FXP / VST2 preset export                        |
| MIDI Export Engine      | `midi_export`       | .mid file generation from all note data sources  |

### Infrastructure

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| Producer Dojo Engine    | `dojo`              | ill.Gates methodology, belt system, 128 Rack     |
| Memory Engine           | `memory`            | Long-term persistence, recall, growth tracking   |
| Sample Slicer           | `sample_slicer`     | Beat-aligned slicing with Fibonacci boundaries   |
| Glitch Engine           | `glitch_engine`     | Stutter, reverse, bit-reduce, granular scatter   |
| Log                     | `log`               | Centralized logging for all engine modules       |

---

## Chord Progression Rules

1. Roman numeral resolution uses **pop/EDM convention** (resolves from key's own scale).
2. 22 chord qualities supported (major through phi_triad).
3. 5 scale types: major, minor, harmonic_minor, phrygian_dominant, dorian.
4. Phi-ratio voicing spread applied to chord inversions.
5. Fibonacci harmonic rhythm for non-uniform chord durations.
6. 432 Hz tuning option for all frequency calculations.
7. MIDI note + frequency dual output for every chord tone.

---

## Ableton Live Integration Rules

1. **Live Object Model (LOM)** is the programmatic API — all 10 core classes mapped.
2. Session View templates follow PSBS track architecture (5 bass layers + support tracks).
3. Arrangement templates use **Fibonacci bar counts** for section durations.
4. **Golden Section Point** (total_beats / phi) marks the climax position in arrangements.
5. Device chains mirror DUBFORGE signal flow: Instrument → EQ (band isolation) → Saturator → Utility.
6. Return tracks use **phi-ratio decay** (reverb) and **Fibonacci timing** (delay).
7. Master chain: EQ Eight → Glue Comp → OTT (phi crossovers) → Limiter.
8. MIDI clips use phi gate ratios (~0.618 of beat) and phi-velocity curves.
9. Max for Live control scripts generated for automated set construction.
10. Ableton's TuningSystem class used for 432 Hz micro-tuning integration.
11. Clip launch quantization defaults to 1 Bar for drop-safe triggering.
12. Rack Macros follow Serum convention: M1=PHI MORPH, M2=FM DEPTH, M3=SUB WEIGHT, M4=GRIT.

---

## Serum Integration Rules

1. Wavetable frames = Fibonacci count (e.g., 8, 13, 21, 34, 55, 89, 144, 233, 256).
2. Macro 1 = phi morph depth. Macro 2 = fractal density. Macro 3 = sub weight. Macro 4 = grit.
3. FM from B oscillator tuned to phi ratio of A.
4. Filter cutoff envelope attack/decay in phi-ratio ms values.
5. Unison detune in cents derived from phi subdivisions.

---

## Serum 2 Engine Rules

1. **5 Oscillator Types** modelled: Wavetable, Multisample, Sample, Granular, Spectral.
2. **Dual Warp** system: each oscillator has 2 warp slots (30+ modes incl. FM, RM, AM, Fold, Wrap).
3. Filter routing: Serial / Parallel / Split A+B — phi-spaced cutoff ladder (55×φ^n Hz).
4. **Phi envelope timing**: Attack:Decay:Release = 1 : φ : φ² — sustain at 1/φ ≈ 0.618.
5. **Phi unison detune**: symmetric cents offsets at φ^k × 3.0 cents per voice.
6. **FM ratio**: carrier:modulator = 1:φ for inharmonic dubstep growl timbres.
7. **Effect mix**: golden ratio wet/dry (1/φ ≈ 0.618 wet by default).
8. **Modulation matrix**: drag-and-drop, aux source for depth modulation, full destination map.
9. **Macro curve**: value^(1/φ) response — emphasizes 0.618 sweet spot.
10. **8 DUBFORGE patches**: Fractal Sub, Phi Growl, Fibonacci FM Screech, Golden Reese, Spectral Tear, Granular Atmosphere, Weapon, Phi Pad.
11. **Arpeggiator + Clip Sequencer**: Fibonacci LFO rates (1/1, 1/2, 1/3, 1/5, 1/8, 1/13, 3/1, 5/1, 8/1).
12. Init template pre-loaded with PHI_CORE wavetable, phi envelope, 432 Hz tuning, doctrine macros.

---

## Producer Dojo / ill.Gates Rules

1. **Belt system** mirrors Producer Dojo martial-arts ranking (White → Black Belt).
2. Belt progression thresholds use **Fibonacci session/asset counts** linked to Memory Engine growth tracking.
3. **The Approach** workflow: Collect → Sketch → Finish — phi-timed phase durations.
4. **128 Rack** technique: 128 samples per Sampler, organized into phi-ratio zone categories.
5. **Mudpies**: chaotic sound collage → extract gems — fractal discovery process.
6. **Infinite Drum Rack**: organized macro sample library with Fibonacci category counts.
7. Clip launching defaults to 1-bar quantization (matches Ableton Integration Rule 11).
8. DUBFORGE modules mapped to belt levels — progressive complexity mirrors Dojo pedagogy.

---

## Memory System Rules

1. **Persistent session logging** — every engine run is a tracked session with events, outputs, and timing.
2. **Fibonacci-interval snapshots** — full state snapshots at Fibonacci-numbered sessions (1, 2, 3, 5, 8, 13, 21…).
3. **Phi-weighted recall** — query past outputs with golden-ratio recency decay: `score = 1 / (1 + (age/half_life)^φ)`.
4. **Relevance scoring** — `recency^(1/φ) × quality^φ × (1 + log_φ(frequency+1))` ranks results.
5. **Asset lineage** — every generated file tracked with generation counter and parent lineage (VIP delta support).
6. **Parameter evolution** — all config changes recorded as time-series with delta magnitude.
7. **Growth milestones** — Fibonacci session counts and asset counts trigger milestone markers.
8. **Belt progression** tied to session count and asset output (Fibonacci thresholds).
9. **Insight storage** — user ratings, notes, favorites, lessons, and goals all persisted.
10. **Golden ratio forgetting curve** — phi decay replaces exponential decay for all temporal scoring.

---

## Frequency Ladder (Planck x phi^n reference)

```
n=0   Planck base        (theoretical)
n=40  ~20 Hz             sub-bass floor
n=41  ~32.36 Hz          sub fundamental layer
n=42  ~52.36 Hz          low bass
n=43  ~84.72 Hz          mid-bass
n=44  ~137.08 Hz         upper bass / growl zone
n=45  ~221.80 Hz         low-mid
n=46  ~358.88 Hz         mid
n=47  ~580.68 Hz         upper-mid
```

(Exact values depend on Planck base constant and phi exponent precision.)

---

## Tuning Modes

| Mode       | A4 (Hz) | Description                         |
|------------|---------|-------------------------------------|
| Standard   | 440.00  | Industry default                    |
| Coherence  | 432.00  | Frequency-of-love reference         |
| Phi-Locked | 430.54  | 432 / phi^(1/12) micro-adjustment   |

---

## File Conventions

- All YAML configs live in `configs/`
- All Python engine modules live in `engine/`
- All tests live in `tests/`
- Wavetable output goes to `output/wavetables/`
- Analysis output goes to `output/analysis/`
- Serum 2 output goes to `output/serum2/`
- Ableton Live output goes to `output/ableton/`
- Producer Dojo output goes to `output/dojo/`
- All MIDI output goes to `output/midi/`
- Memory persistence goes to `output/memory/`
- Mastering chain output goes to `output/masters/`
- FXP preset output goes to `output/presets/`
- Sample slicer output goes to `output/slices/`

---

### Roadmap (Future Features)

- ~~**L1: Serum 2 .fxp Export**~~ — ✅ DONE (v2.0) — `fxp_writer.py` exports native Serum preset files
- ~~**L2: MIDI File Export**~~ — ✅ DONE (v1.5) — `midi_export.py` generates 19+ .mid files
- ~~**L3: Ableton .als Generation**~~ — ✅ DONE (v2.0) — `als_generator.py` produces Ableton Live Set files
- ~~**L4: Serum 2 v2.0.18 Rewrite**~~ — ✅ DONE (v2.7.0) — 58 warp modes, 80 filters, 16 FX, 3 oscs, 10 LFOs, 8 macros

---

## Roadmap to 144 — Black Belt → Grandmaster

**Current:** Session 91 · Black Belt · v2.7.0 · 52 modules · 1121 tests · 6,610 output files
**Target:** Session 144 (Fibonacci) · 53 sessions · Grandmaster promotion

---

### Phase 1 — REAL AUDIO EXPANSION (Sessions 92–102 · v2.8–v2.10)

_Goal: Every synth module writes .wav — move from "JSON spec generator" to "actual sound engine."_

| Session | Version | Deliverable |
|---------|---------|-------------|
| 92 | v2.8.0 | **psbs.py → real audio** — `render_psbs_cycle()` already does DSP but discards the result. Wire it to `write_wav()`. 5-layer bass wavetables. |
| 93 | | **drum_generator.py → real audio** — synthesize kick, snare, hat, clap as .wav one-shots using phi-timed transients + noise envelopes. |
| 94 | | **sub_bass.py → real audio** — render sub-bass one-shots (.wav) with phi-ratio envelopes. Serum-loadable single-cycle subs. |
| 95 | v2.9.0 | **bass_oneshot.py → real audio** — mid-range bass one-shots as .wav. FM + waveshaping pipeline. |
| 96 | | **impact_hit.py → real audio** — transient-heavy impact hits for drops. Layered noise burst + pitched sine. |
| 97 | | **riser_synth.py → real audio** — filtered noise sweeps + pitch risers as .wav. |
| 98 | v2.10.0 | **perc_synth.py → real audio** — tuned metallic percussion hits. FM synthesis + ring mod. |
| 99 | | **noise_generator.py → real audio** — white/pink/brown/Geiger noise textures as .wav files. |
| 100 | | **lead_synth.py → real audio** — lead one-shots with phi-tuned envelopes. Saw/square + unison + detuning. |
| 101 | | **pad_synth.py → real audio** — evolving pad textures as multi-frame wavetables. |
| 102 | | **wobble_bass.py → real audio** — LFO-modulated wobble bass rendered as wavetable morphs. |

### Phase 2 — DSP HARDENING (Sessions 103–112 · v3.0–v3.2)

_Goal: Production-grade DSP. Replace placeholder math with real algorithms._

| Session | Version | Deliverable |
|---------|---------|-------------|
| 103 | v3.0.0 | **mastering_chain.py → real audio** — EQ, multiband compression, limiting applied to .wav files. scipy.signal filters. |
| 104 | | **multiband_distortion.py → real audio** — 5 distortion algorithms (warm/aggressive/digital/tube/tape) processing real audio. |
| 105 | | **sidechain.py → real audio** — apply sidechain envelope curves to .wav files. Ducking/pumping on rendered audio. |
| 106 | v3.1.0 | **stereo_imager.py → real audio** — Haas delay, M-S processing, frequency-split widening on .wav. |
| 107 | | **convolution.py → real audio** — generate IRs (room/cab/plate) as .wav. Apply convolution reverb to audio files. |
| 108 | | **reverb_delay.py → real audio** — algorithmic reverb + phi-spaced delay taps rendered to .wav. |
| 109 | v3.2.0 | **formant_synth.py → real audio** — vowel-shaped resonant filtering on rendered audio. Real formant banks. |
| 110 | | **granular_synth.py → real audio** — grain cloud engine reading .wav sources, outputting textured .wav. |
| 111 | | **vocal_chop.py → real audio** — formant-shifted vocal fragments rendered from source material. |
| 112 | | **glitch_engine.py → real audio** — stutter, reverse, bit-reduce, granular scatter on .wav files. |

### Phase 3 — INTEGRATION & PIPELINE (Sessions 113–122 · v3.3–v3.5)

_Goal: Modules talk to each other. End-to-end render pipeline from idea to mixdown._

| Session | Version | Deliverable |
|---------|---------|-------------|
| 113 | v3.3.0 | **render_pipeline.py** — new module. Chain: synth → FX → sidechain → stereo → master. One call renders a full stem. |
| 114 | | **batch_renderer.py** — new module. Render all patches from `build_dubstep_patches()` to .wav stems automatically. |
| 115 | | **stem_mixer.py** — new module. Mix multiple rendered stems with phi-weighted gain staging. Output stereo mixdown. |
| 116 | v3.4.0 | **sample_pack_builder.py** — new module. Package all rendered .wav into organized sample pack folders (kicks/, snares/, basses/, etc.). |
| 117 | | **preset_pack_builder.py** — new module. Batch-export Serum 2 .fxp presets from all patches. Organized category folders. |
| 118 | | **als_generator.py upgrade** — auto-populate .als projects with rendered stems + MIDI + sidechain. Full arrangement from templates. |
| 119 | v3.5.0 | **wavetable_morph.py** — new module. Fractal interpolation between wavetable frames (not linear crossfade). Phi-curve morphing. |
| 120 | | **spectral_resynthesis.py** — new module. FFT analysis → phi-filtered reconstruction. Import any .wav → DUBFORGE wavetable. |
| 121 | | **harmonic_analysis.py upgrade** — real FFT spectral analysis on rendered .wav files. Visualize phi-ratio presence in produced audio. |
| 122 | | **CLI tool** — `dubforge render`, `dubforge export`, `dubforge analyze` commands via entry_points. |

### Phase 4 — INTELLIGENCE & EVOLUTION (Sessions 123–132 · v3.6–v3.8)

_Goal: DUBFORGE learns from its own output. Phi-weighted feedback loops._

| Session | Version | Deliverable |
|---------|---------|-------------|
| 123 | v3.6.0 | **phi_analyzer.py** — new module. Measure phi-ratio presence in any .wav. Score 0.0–1.0 "fractal coherence." |
| 124 | | **evolution_engine.py** — new module. Track parameter changes across sessions. Identify which phi-tunings produce highest-rated output. |
| 125 | | **preset_mutator.py** — new module. Take a Serum2Patch, apply phi-weighted random mutations, breed new patches. Genetic algorithm. |
| 126 | v3.7.0 | **ab_tester.py** — new module. Render two patch variants, compare spectral profiles, pick the more phi-coherent one. |
| 127 | | **memory.py upgrade** — phi-weighted recall. When querying past sessions, weight recent + high-rated results by 1/phi. |
| 128 | | **dojo.py upgrade** — connect belt progression to actual output quality metrics. Auto-assign ratings based on phi_analyzer scores. |
| 129 | v3.8.0 | **template_generator.py** — new module. Given a genre tag + energy profile, auto-generate a complete Serum2Patch + arrangement + FX chain. |
| 130 | | **sound_palette.py** — new module. Define a "palette" of timbres (warm, cold, metallic, organic) mapped to phi-harmonic profiles. |
| 131 | | **config_loader.py upgrade** — hot-reload YAML configs. Watch for changes, re-render affected outputs. |
| 132 | | **Documentation overhaul** — auto-generated module docs from docstrings. Architecture diagrams. API reference. |

### Phase 5 — POLISH & GRANDMASTER (Sessions 133–144 · v3.9–v4.0)

_Goal: Ship-ready. Everything tested, documented, integrated. Hit 144._

| Session | Version | Deliverable |
|---------|---------|-------------|
| 133 | v3.9.0 | **Full test coverage audit** — every module has ≥20 tests. Target: 2000+ total tests. |
| 134 | | **Performance profiling** — benchmark every render pipeline. Optimize hot paths with numpy vectorization. |
| 135 | | **Error handling hardening** — graceful failures, retry logic, input validation on every public function. |
| 136 | v3.10.0 | **Plugin scaffold** — architecture for user-contributed modules. Plugin interface, discovery, registration. |
| 137 | | **Web preview** — simple Flask/FastAPI endpoint. Upload .wav → get phi-analysis JSON + spectrogram PNG. |
| 138 | | **Notebook tutorials** — 5 Jupyter notebooks walking through phi_core → growl → patch → render → master. |
| 139 | v3.11.0 | **PSBS real-time monitor** — live phase coherence display during playback (prototype). |
| 140 | | **Cross-platform CI** — GitHub Actions: lint + test on macOS/Linux/Windows. Badge in README. |
| 141 | | **PyPI publish** — `pip install dubforge`. Clean package, entry points, version pinning. |
| 142 | v4.0.0 | **DUBFORGE v4.0** — full integration test: one command renders complete EP (5 tracks × stems × masters). |
| 143 | | **Final audit** — comprehensive technical audit v2. Compare to v1.4 audit. Measure real-audio percentage. |
| 144 | **v4.0.1** | **🏆 FIBONACCI 144 — GRANDMASTER** — full snapshot, belt promotion, retrospective document. |

---

### Metrics at 144 — ACHIEVED

| Metric | Session 91 | Target (144) | Actual (144) |
|--------|-----------|--------------|--------------|
| Modules | 52 | ~65 | 74 |
| Tests | 1,121 | 2,000+ | 2,314 |
| Real audio modules | ~4 | 30+ | 40+ |
| Version | v2.7.0 | v4.0.1 | v4.0.0 |
| Belt | Black Belt | Grandmaster | **GRANDMASTER** |

### Fibonacci Sessions on the Path

| # | Type | Milestone |
|---|------|-----------|
| **89** | ✅ Done | Black Belt promotion |
| 91 | ✅ Done | Roadmap drafted |
| **144** | ✅ **ACHIEVED** | **Grandmaster promotion** |

_Fibonacci session 144 reached. GRANDMASTER belt confirmed._

---

**Version:** 4.0.0
**Author:** DUBFORGE
**Date:** 2025-07-07
**Modules:** 74
**Tests:** 2,314
**Belt:** GRANDMASTER (Session 144)
**Status:** COMPLETE
