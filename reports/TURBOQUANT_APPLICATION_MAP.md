# TurboQuant Universal Application Map

> **Generated**: Session 4 — Post-commit cb797ae  
> **Source**: arXiv:2504.19874 (ICLR 2026, Google Research)  
> **Algorithm**: FWHT rotation → Lloyd-Max scalar quantization → optional QJL residual  
> **Performance**: ~19× compression, MSE 0.038, cosine-similarity search on compressed vectors

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Already Integrated (8 Modules)](#2-already-integrated)
3. [DUBFORGE Engine — Tier 1 Candidates (25 Modules)](#3-tier-1-candidates)
4. [DUBFORGE Engine — Tier 2 Candidates (19 Modules)](#4-tier-2-candidates)
5. [Serum 2 Integration Points](#5-serum-2-integration-points)
6. [Ableton Live 12 Integration Points](#6-ableton-live-12-integration-points)
7. [Cross-Domain Data Type Matrix](#7-data-type-matrix)
8. [Priority Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Executive Summary

TurboQuant compresses float arrays via random rotation + scalar quantization. Any system that **stores, caches, transmits, or indexes** dense float vectors benefits. Three capability pillars:

| Pillar | What It Does | Best For |
|--------|-------------|----------|
| **Compress** | ~19× lossless-enough storage reduction | Wavetable banks, audio buffers, automation curves, IR libraries |
| **Decompress** | Reconstruct from 3-bit quantized representation | Real-time playback, on-demand preset loading |
| **Search** | Cosine similarity on compressed feature vectors | Preset browsers, sample matching, timbre fingerprinting |

---

## 2. Already Integrated

| Module | TQ Feature | What It Does |
|--------|-----------|--------------|
| `engine/turboquant.py` | Core engine | FWHT + Lloyd-Max + QJL, all primitives |
| `engine/audio_buffer.py` | `compress_audio_buffer()` | Idle buffer archival with eviction-to-archive |
| `engine/phi_core.py` | `compress_wavetable()` | Wavetable frame compression (2048 samples, 3 bits) |
| `engine/frequency_analyzer.py` | `SpectralVectorIndex` | FFT feature vector similarity search |
| `engine/wav_pool.py` | Pool archival | Evict cold WAVs to compressed archive |
| `engine/audio_stitcher.py` | Segment caching | Compress completed arrangement segments |
| `engine/batch_renderer.py` | Render archival | Compress finished renders before export |
| `engine/audio_preview.py` | Preview cache | Compressed preview buffer storage |
| `forge.py` | Pipeline integration | TQ step in master pipeline |

---

## 3. Tier 1 Candidates — DUBFORGE Engine (25 Modules)

### 3A. Wavetable Pipeline (HIGHEST VALUE)

These modules generate, transform, and store wavetable frames — the **exact data shape** TQ was designed for (fixed-length float arrays, 2048 samples/frame).

| Module | Opportunity | TQ Feature | Impact |
|--------|------------|-----------|--------|
| `engine/wavetable_morph.py` | Morph interpolation cache — store start/end + intermediate frames | `compress_wavetable()` | 10-20× reduction in morph bank storage |
| `engine/wavetable_pack.py` | Pack/bundle wavetable sets for export | `compress_wavetable()` | Smaller .wavetable export files |
| `engine/growl_resampler.py` | Growl wavetable resampling cache | `compress_wavetable()` | Keep more growl variants in memory |
| `engine/additive_synth.py` | Partial → wavetable bake cache | `compress_wavetable()` | Additive synthesis precompute storage |
| `engine/granular_synth.py` | Grain buffer pool | `compress_audio_buffer()` | Compress grain library when grains exceed threshold |
| `engine/fm_matrix.py` | FM operator output cache | `compress_wavetable()` | Cache complex FM ratio results |

### 3B. Track Storage Chain

Audio stems, bounces, and renders — **large contiguous float arrays** that compress extremely well.

| Module | Opportunity | TQ Feature | Impact |
|--------|------------|-----------|--------|
| `engine/ep_builder.py` | EP track storage (multi-track project) | `compress_audio_buffer()` | Compress idle tracks during arrangement |
| `engine/multitrack_renderer.py` | Multi-stem render buffer | `compress_audio_buffer()` | Archive rendered stems pre-mixdown |
| `engine/bounce.py` | Bounce-to-audio output | `compress_audio_buffer()` | Compressed bounce cache |
| `engine/stem_export.py` | Stem export buffers | `compress_audio_buffer()` | Compress before WAV write |
| `engine/audio_splitter.py` | Split audio segments | `compress_audio_buffer()` | Archive split segments |
| `engine/mastering_chain.py` | Pre/post master buffers | `compress_audio_buffer()` | Store intermediate mastering stages |

### 3C. Preset & Patch Storage

Preset parameters are dense float vectors — perfect for both compression and similarity search.

| Module | Opportunity | TQ Feature | Impact |
|--------|------------|-----------|--------|
| `engine/serum2.py` | Serum 2 patch parameter vectors | `compress()` + `SpectralVectorIndex` | Compress presets, find similar patches |
| `engine/serum_blueprint.py` | Blueprint parameter storage | `compress()` | Compact blueprint bank |
| `engine/fxp_writer.py` | FXP parameter chunk compression | `compress()` | Smaller FXP files on disk |
| `engine/preset_manager.py` | Cross-format preset cache | `compress()` + `SpectralVectorIndex` | Unified preset library with search |

### 3D. Automation & Modulation Data

Automation curves are time-series float arrays — breakpoint envelopes, LFO shapes, modulation curves.

| Module | Opportunity | TQ Feature | Impact |
|--------|------------|-----------|--------|
| `engine/automation_recorder.py` | Recorded automation curve storage | `compress()` | 10-20× smaller automation banks |
| `engine/als_generator.py` | ALS FloatEvent envelope storage | `compress()` | Compact automation in project files |
| `engine/arrangement_sequencer.py` | Sequenced automation lanes | `compress()` | Multi-lane automation compression |
| `engine/auto_arranger.py` | Auto-generated arrangement data | `compress()` | Compress arrangement templates |
| `engine/lfo.py` | Custom LFO shape storage | `compress_wavetable()` | LFO waveforms = single-cycle wavetables |

### 3E. Analysis & Fingerprinting

Spectral features, MFCCs, pitch contours — dense vector data ideal for TQ's similarity search.

| Module | Opportunity | TQ Feature | Impact |
|--------|------------|-----------|--------|
| `engine/audio_analyzer.py` | Spectral analysis feature vectors | `SpectralVectorIndex` | Content-based audio search |
| `engine/dubstep_taste_analyzer.py` | Taste profile vectors | `SpectralVectorIndex` | Find tracks with similar "taste" |
| `engine/soundcloud_pipeline.py` | Track fingerprint storage | `compress()` + `SpectralVectorIndex` | Compress + search track DB |

---

## 4. Tier 2 Candidates — DUBFORGE Engine (19 Modules)

Moderate opportunity — primarily benefit from **similarity search** rather than storage compression.

| Module | Opportunity | TQ Feature |
|--------|------------|-----------|
| `engine/ambient_texture.py` | Texture parameter similarity | `SpectralVectorIndex` |
| `engine/arp_synth.py` | Arp pattern vectors | `compress()` |
| `engine/bass_oneshot.py` | One-shot sample cache | `compress_audio_buffer()` |
| `engine/chord_engine.py` | Voicing parameter vectors | `compress()` |
| `engine/compressor.py` | Compressor setting presets | `SpectralVectorIndex` |
| `engine/delay_engine.py` | Delay feedback buffer | `compress_audio_buffer()` |
| `engine/distortion.py` | Waveshaper curve storage | `compress_wavetable()` |
| `engine/drone_engine.py` | Drone buffer archival | `compress_audio_buffer()` |
| `engine/eq_engine.py` | EQ curve storage | `compress()` |
| `engine/filter_engine.py` | Filter coefficient presets | `SpectralVectorIndex` |
| `engine/noise_generator.py` | Noise table seeding | `compress_wavetable()` |
| `engine/pad_synth.py` | Pad texture buffers | `compress_audio_buffer()` |
| `engine/reverb.py` | IR storage/retrieval | `compress_audio_buffer()` + `SpectralVectorIndex` |
| `engine/riser_engine.py` | Riser sweep cache | `compress_audio_buffer()` |
| `engine/sample_slicer.py` | Slice buffer pool | `compress_audio_buffer()` |
| `engine/saturation.py` | Saturation curve tables | `compress_wavetable()` |
| `engine/sub_synth.py` | Sub bass wavetables | `compress_wavetable()` |
| `engine/vocoder.py` | Filterbank coefficient sets | `compress()` |
| `engine/pitch_shifter.py` | Overlap-add buffer | `compress_audio_buffer()` |

---

## 5. Serum 2 Integration Points

Based on Serum 2 v2.1.1 manual research (Xfer Records, $249).

### 5A. Wavetable Data (PRIMARY)

| Data Type | Serum 2 Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Wavetable frames** | 2048 samples/frame, 256 frames/table | `compress_wavetable()` | Core use case — PHI_CORE, GROWL_SAW, GROWL_FM tables |
| **Spectral warp output** | FM/AM/RM/PD/Sync warp modes generate new frames | `compress_wavetable()` | Cache warped variants without regenerating |
| **Sample-to-WT conversion** | Frequency estimation → wavetable extraction | `compress_wavetable()` | Compress converted tables (pitch detection + slicing) |
| **Morph interpolations** | Cross/Crossfade/Spectral morph between frames | `compress_wavetable()` | Store morph trajectory snapshots |
| **Unison stack output** | 3-7 detuned voices per oscillator | `compress_audio_buffer()` | Cache pre-summed unison stacks |

### 5B. Modulation Curves

| Data Type | Serum 2 Feature | TQ Application |
|-----------|----------------|---------------|
| **LFO shapes** | Custom LFO curves (drag-draw) | `compress_wavetable()` (single-cycle) |
| **Envelope curves** | ADSR + custom breakpoints | `compress()` |
| **Macro automation** | 4 macros with curve mapping | `compress()` |
| **Chaos modulator output** | Random/drift modulation curves | `compress()` |
| **CLIP module automation** | Preset preview macro automation sequences | `compress()` |

### 5C. FX Processing Data

| Data Type | Serum 2 Feature | TQ Application |
|-----------|----------------|---------------|
| **Bode frequency shifter** | Feedback + delay + blur output | `compress_audio_buffer()` |
| **Multipass bands** | Multi-band mid/side FX processing | `compress_audio_buffer()` |
| **Disperser/Diffuser** | Phase diffusion output | `compress_audio_buffer()` |
| **Distortion curves** | Non-linear waveshaper tables | `compress_wavetable()` |
| **Reverb IRs** | Convolution impulse responses | `compress_audio_buffer()` |

### 5D. Preset Search

| Data Type | Serum 2 Feature | TQ Application |
|-----------|----------------|---------------|
| **Patch parameter vectors** | ~150+ float parameters per patch | `SpectralVectorIndex` |
| **CLIP audio fingerprints** | Preset preview audio clips | `SpectralVectorIndex` |
| **Oscillator timbre vectors** | FFT of rendered oscillator output | `SpectralVectorIndex` |
| **FXP binary chunks** | Full patch state data | `compress()` |

### 5E. DUBFORGE ↔ Serum 2 Pipeline

```
DUBFORGE wavetables (phi_core.py)
  → compress_wavetable() → .tq archive
  → decompress on demand
  → export to ~/Documents/Xfer/Serum Presets/Tables/DUBFORGE/
  → Serum 2 loads WAV wavetable

DUBFORGE patches (serum2.py)
  → FXP parameter vector → compress()
  → SpectralVectorIndex → find similar patches
  → fxp_writer.py → .fxp binary export
```

---

## 6. Ableton Live 12 Integration Points

Based on Ableton Live 12 manual research (42 chapters, all instruments + effects + workflow).

### 6A. Wavetable Instrument Data (CRITICAL)

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Wavetable OSC frames** | Wavetable instrument — 2 WT OSCs, load ANY WAV/AIFF | `compress_wavetable()` | Direct match — DUBFORGE exports wavetables Ableton can load |
| **Wavetable effects** | FM/Classic/Modern effects per OSC | `compress_wavetable()` | Cache effect-processed frames |
| **Sub oscillator** | Dedicated sub OSC in Wavetable | `compress_wavetable()` | Simple waveform, but still compressible |
| **Unison modes** | 6 modes: Classic/Shimmer/Noise/Phase Sync/Position Spread/Random Note | `compress_audio_buffer()` | Cache unison voice stacks |

### 6B. FM/Additive Synthesis Data

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Operator waveforms** | 4-OSC FM, 11 algorithms, 16/32/64 partial editor | `compress_wavetable()` | User-drawn partials → wavetable = prime TQ target |
| **FM algorithm output** | Complex FM ratio results | `compress_audio_buffer()` | Cache rendered FM combinations |
| **Operator user waves** | Draw custom waves via partial editing | `compress_wavetable()` | Custom partials are dense float arrays |

### 6C. Physical Modeling Parameters

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Collision resonators** | 7 types: Beam/Marimba/String/Membrane/Plate/Pipe/Tube | `compress()` | Resonator parameter sets → similarity search |
| **Tension models** | Exciter + String + Body + Damper + Finger/Fret models | `compress()` | Physical model parameter vectors |
| **Corpus resonators** | 7 resonator types in audio effect | `compress()` | Same architecture as Collision resonators |
| **Analog components** | 2 OSCs + noise + 2 filters + LFOs + envelopes | `compress()` | Analog model parameter presets |

### 6D. Sample/Audio Data

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Sampler zones** | Multi-sample instruments with zone mapping | `compress_audio_buffer()` | Compress samples across velocity/key zones |
| **Simpler playback** | Warped sample with Classic/One-Shot/Slice modes | `compress_audio_buffer()` | Cache warped playback buffers |
| **Drum Sampler effects** | 9 effects: Stretch/Loop/FM/Ring Mod/8-Bit/Sub/Noise | `compress_audio_buffer()` | Cache processed one-shots |
| **Impulse slots** | 8-slot drum sampler with time-stretch | `compress_audio_buffer()` | Slot buffer archival |
| **Stem separation** | Vocals/Drums/Bass/Others (deep learning model) | `compress_audio_buffer()` | **MASSIVE** — 4 stems per song, all need storage |
| **Bounce to audio** | Rendered track output | `compress_audio_buffer()` | Archive bounced audio |
| **Warped audio** | 5 warp modes: Beats/Tones/Texture/Re-Pitch/Complex Pro | `compress_audio_buffer()` | Cache time-stretched results |

### 6E. Automation & Envelope Data (CRITICAL)

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Arrangement automation** | Breakpoint envelopes — float values over time, curved segments | `compress()` | Time-series float arrays, exactly what TQ handles |
| **Session clip automation** | Per-clip modulation envelopes | `compress()` | Dense per-clip parameter curves |
| **Automation shapes** | Sine/triangle/saw/square/ADSR presets | `compress_wavetable()` | Shape = single-cycle waveform |
| **Tempo automation** | Song tempo envelope (BPM over time) | `compress()` | Critical for live performance sets |
| **Clip envelopes** | Per-clip parameter modulation | `compress()` | Every clip can have multi-param envelopes |
| **ALS FloatEvent** | XML automation events with CurveControl bezier handles | `compress()` | DUBFORGE already writes these — can store compressed |

### 6F. Audio Effects Data

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Hybrid Reverb IRs** | Convolution engine — user IR import + 5 algorithmic modes | `compress_audio_buffer()` | IR = long float array, compresses perfectly |
| **Looper buffers** | Live audio looping with overdub | `compress_audio_buffer()` | Streaming loop archival |
| **Corpus/Resonator parameters** | Physical model → audio effect chain | `compress()` + `SpectralVectorIndex` | Parameter preset search |
| **Spectral Resonator FFT** | FFT-based tuned resonances, 4 mod modes + unison | `compress()` | Spectral bin data = dense float arrays |
| **Roar shaper curves** | 12 waveshaper curves, 3 stages | `compress_wavetable()` | Shaper = nonlinear transfer function table |
| **Saturator waveshaper** | 8 curve types + user waveshaper | `compress_wavetable()` | Drive/Curve/Depth parameters |
| **Vocoder filterbank** | Adjustable bands/range/bandwidth | `compress()` | Filter coefficient vectors |
| **Auto Filter curves** | 10 filter types + Cytomic circuit models | `compress()` | Filter response curves |
| **EQ Eight curves** | 8-band parametric with Cytomic filters | `compress()` | Frequency response curve data |
| **Redux tables** | Downsampling + bit reduction with filters | `compress_wavetable()` | Quantization lookup tables |
| **Grain Delay buffers** | Granular delay feedback | `compress_audio_buffer()` | Grain buffer pool |
| **Echo delay lines** | Dual delay + modulation + character | `compress_audio_buffer()` | Delay line buffers |

### 6G. Filter Data

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Cytomic filters** | Used in Wavetable, EQ Eight, Auto Filter + elsewhere | `compress()` | State-variable filter coefficients |
| **Meld Vowel filter** | Vowel/Comb/Plate formant filters | `compress()` | Formant frequency vectors |
| **Drift shape control** | Curated waveform shapes with Shape morphing | `compress_wavetable()` | Shape = continuous waveform morph |

### 6H. Modulation Data

| Data Type | Ableton Feature | TQ Application | Notes |
|-----------|----------------|---------------|-------|
| **Sampler LFOs** | 3 LFOs with 21 waveforms each | `compress_wavetable()` | LFO = single-cycle table |
| **Auto Pan/Tremolo LFOs** | 7 shapes: Sine/Tri/Shark/Saw/Square/Random/Wander/S&H | `compress_wavetable()` | Modulation waveforms |
| **Phaser-Flanger LFOs** | 2 LFOs + envelope follower | `compress()` | Modulation curves |
| **Roar mod sources** | LFO1/LFO2/Envelope/Noise → 4 modulation sources | `compress()` | Multi-source mod matrix |
| **Wavetable mod matrix** | Full modulation matrix with multiple sources | `compress()` | Mod routing parameter vectors |

---

## 7. Cross-Domain Data Type Matrix

Mapping **data types** to **compression opportunities** across all three domains:

| Data Type | Size (typical) | TQ Feature | DUBFORGE | Serum 2 | Ableton 12 |
|-----------|---------------|-----------|----------|---------|------------|
| **Wavetable frame** | 2048 floats (8 KB) | `compress_wavetable()` | phi_core, additive, granular, growl, fm_matrix | All 5 OSC types, warp output, sample-to-WT | Wavetable instrument, Operator partials, Drift shapes |
| **Audio buffer** | 44100-2M+ floats | `compress_audio_buffer()` | audio_buffer, wav_pool, stitcher, stems, bounce | Unison output, FX buffers, Multipass | Stems, bounce, warped clips, delay lines, IRs, Looper |
| **Automation curve** | 100-10K floats | `compress()` | automation_recorder, als_generator, arranger | LFO/env curves, macro automation, CLIP | FloatEvent envelopes, clip envelopes, tempo automation |
| **Preset params** | 50-500 floats | `compress()` + `SpectralVectorIndex` | serum2.py, preset_manager, fxp_writer | ~150+ patch params, FXP chunks | Device presets, rack macros, effect chains |
| **Spectral features** | 128-4096 floats | `SpectralVectorIndex` | audio_analyzer, taste_analyzer, frequency_analyzer | OSC timbre FFT, CLIP fingerprints | Spectral Resonator bins, Vocoder bands |
| **Filter coefficients** | 5-50 floats | `compress()` | filter_engine, eq_engine | Analog/digital filters, formant | Cytomic, Vowel, Comb, EQ Eight |
| **Waveshaper curve** | 256-2048 floats | `compress_wavetable()` | distortion, saturation | Distortion curves | Roar (12 curves), Saturator, Redux |
| **Impulse response** | 44K-200K floats | `compress_audio_buffer()` | reverb | Convolution reverb | Hybrid Reverb IR import |
| **LFO waveform** | 128-2048 floats | `compress_wavetable()` | lfo.py | Custom LFO + chaos mod | Sampler 3×LFO, Auto Pan, Phaser, Roar |
| **Physical model params** | 20-100 floats | `compress()` | — | — | Collision, Tension, Corpus, Analog, Electric |

---

## 8. Priority Implementation Roadmap

### Phase 1: Wavetable Pipeline (Immediate — Highest ROI)

1. **`wavetable_morph.py`** — Add `compress_wavetable()` to morph interpolation cache
2. **`wavetable_pack.py`** — TQ-compressed wavetable bundles for export
3. **`growl_resampler.py`** — Compressed growl variant storage
4. **`additive_synth.py`** — Partial → wavetable bake cache compression
5. **`fm_matrix.py`** — FM ratio output cache

**Why first**: These produce the **exact same data shape** as existing TQ integration (2048-sample frames). Minimal code, maximum payoff.

### Phase 2: Track Storage Chain (High Value)

6. **`ep_builder.py`** — Idle track compression in EP projects
7. **`multitrack_renderer.py`** — Stem render buffer archival
8. **`bounce.py`** — Bounce output compression
9. **`mastering_chain.py`** — Intermediate mastering stage archival
10. **`stem_export.py`** — Pre-export stem compression

**Why second**: Largest absolute storage savings — stems are 10-100 MB each.

### Phase 3: Preset Intelligence (Medium Value, High Creativity)

11. **`serum2.py`** — Patch parameter vector compression + similarity search
12. **`preset_manager.py`** — Cross-format preset library with TQ search
13. **`fxp_writer.py`** — Compressed FXP parameter storage
14. **`serum_blueprint.py`** — Blueprint bank compression

**Why third**: Enables "find me a patch similar to this one" — creative discovery tool.

### Phase 4: Automation & Modulation (Medium Value)

15. **`automation_recorder.py`** — Compressed automation curve banks
16. **`als_generator.py`** — TQ-compressed automation in ALS exports
17. **`arrangement_sequencer.py`** — Multi-lane automation compression
18. **`lfo.py`** — Custom LFO shape compression

**Why fourth**: Automation curves are smaller data but high volume — hundreds per project.

### Phase 5: Analysis & Search (Creative Value)

19. **`audio_analyzer.py`** — Content-based audio similarity search
20. **`dubstep_taste_analyzer.py`** — "Find tracks that taste like this"
21. **`soundcloud_pipeline.py`** — Track fingerprint database with search

**Why last**: Requires feature extraction pipeline changes, but unlocks powerful creative search.

---

## Appendix A: Serum 2 Feature Summary

| Feature | Data Types Generated | TQ Relevance |
|---------|---------------------|-------------|
| 5 oscillator types (Wavetable/Multisample/Sample/Granular/Spectral) | Wavetable frames, audio buffers, spectral data | HIGH |
| Warp modes (FM/AM/RM/PD/Sync + spectral warps) | Transformed wavetable frames | HIGH |
| Mod matrix (LFOs, envelopes, chaos, custom curves) | Modulation curves (float arrays) | MEDIUM |
| FX chain (distortion, reverb, delay, Bode shifter, Multipass, disperser) | Audio buffers, waveshaper tables | MEDIUM |
| CLIP module (preset preview audio + macro automation) | Audio fingerprints, automation curves | MEDIUM |
| Arpeggiator/sequencer | Pattern data (small) | LOW |
| Analog filters (ladder, SVF, comb, formant) | Filter coefficients | LOW |

## Appendix B: Ableton Live 12 Feature Summary

| Feature | Data Types Generated | TQ Relevance |
|---------|---------------------|-------------|
| Wavetable instrument (2 WT OSCs, load WAV/AIFF, 6 unison modes, mod matrix) | Wavetable frames, unison buffers | CRITICAL |
| Operator (4-OSC FM, 11 algorithms, 16/32/64 partial editor) | User waveforms, FM output | CRITICAL |
| Stem separation (Vocals/Drums/Bass/Others, deep learning) | 4 full-length audio buffers per song | CRITICAL |
| Automation envelopes (breakpoints, curved segments, shapes, tempo) | Time-series float arrays | HIGH |
| Hybrid Reverb (convolution + algorithmic, user IR import) | Impulse responses (44K-200K samples) | HIGH |
| Sampler (multi-sample zones, FM/AM mod OSC, 3 LFOs, waveshaper) | Audio buffers, modulation curves | HIGH |
| Collision/Corpus/Tension (physical modeling, 7+ resonator types) | Model parameter vectors | MEDIUM |
| Spectral Resonator (FFT tuned resonances, unison, MIDI sidechain) | Spectral bin data | MEDIUM |
| Roar (12 shaper curves, 9 filter types, 4 mod sources, feedback) | Waveshaper tables, modulation curves | MEDIUM |
| Warping (5 modes: Beats/Tones/Texture/Re-Pitch/Complex Pro) | Time-stretched audio buffers | MEDIUM |
| Clip envelopes (per-clip parameter modulation) | Dense modulation curves | MEDIUM |
| Meld (dual OSC + Vowel/Comb/Plate filters + morphing) | Filter formant vectors | LOW-MEDIUM |
| Bounce to audio (rendered track output) | Audio buffers | LOW (one-shot) |

## Appendix C: Combined TQ Opportunity Count

| Category | DUBFORGE | Serum 2 | Ableton 12 | Total |
|----------|---------|---------|-----------|-------|
| Wavetable compression | 6 modules | 5 data types | 4 instruments | **15** |
| Audio buffer compression | 12 modules | 3 data types | 10 features | **25** |
| Automation/modulation | 5 modules | 5 data types | 6 features | **16** |
| Preset/parameter search | 4 modules | 4 data types | 3 features | **11** |
| Spectral/analysis search | 3 modules | 2 data types | 3 features | **8** |
| **TOTAL** | **30** | **19** | **26** | **75** |

---

*75 total TQ application points across the production ecosystem. 8 already integrated, 44 Tier 1-2 DUBFORGE candidates, 19 Serum 2 data types, 26 Ableton Live 12 features.*
