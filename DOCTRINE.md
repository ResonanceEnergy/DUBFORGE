# DUBFORGE DOCTRINE v1.0 — Planck x phi Fractal Basscraft

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

## Module Architecture

| Module                  | Code                | Purpose                                          |
|-------------------------|---------------------|-------------------------------------------------|
| PHI CORE                | `phi_core`          | Wavetable generator — phi-spaced partials        |
| Config Loader           | `config_loader`     | Centralized YAML config reader + PHI constants   |
| Rollercoaster Optimizer | `rco`               | Arrangement energy curve engine                  |
| Phase-Separated Bass    | `psbs`              | Multi-layer bass with phase-aligned separation   |
| Subtronics Analyzer     | `sb_analyzer`       | Corpus analysis + VIP delta evolution tracker     |
| Trance Arp Engine       | `trance_arp`        | Fibonacci-timed arpeggiator                      |
| Mid-Bass Growl Resampler| `growl_resampler`   | Resample + mangle mid-bass growls                |
| Chord Progression       | `chord_progression` | Music theory + phi voicing + 11 EDM presets      |
| Ableton Live Engine     | `ableton_live`      | Full LOM integration, session/arrangement gen    |
| Serum 2 Engine          | `serum2`            | Full synth architecture, patches, mod matrix     |
| Producer Dojo Engine    | `dojo`              | ill.Gates methodology, belt system, 128 Rack     |
| Memory Engine           | `memory`            | Long-term persistence, recall, growth tracking   |
| MIDI Export Engine      | `midi_export`       | .mid file generation from all note data sources  |

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
- Wavetable output goes to `output/wavetables/`
- Analysis output goes to `output/analysis/`
- Serum 2 output goes to `output/serum2/`
- Ableton Live output goes to `output/ableton/`
- Producer Dojo output goes to `output/dojo/`
- All MIDI output goes to `output/midi/`
- Memory persistence goes to `output/memory/`

---

### Roadmap (Future Features)

- **L1: Serum 2 .fxp Export** — Generate native Serum preset files from `serum2.py` patch definitions
- ~~**L2: MIDI File Export**~~ — ✅ DONE (v1.5) — `midi_export.py` generates 19 .mid files from chord progressions, arp patterns, Ableton clips, and full arrangements
- **L3: Ableton .als Generation** — Produce Ableton Live Set files from session/arrangement templates

---

**Version:** 1.5
**Author:** DUBFORGE
**Date:** 2026-03-07
**Modules:** 14 (phi_core, config_loader, log, rco, psbs, sb_analyzer, trance_arp, growl_resampler, chord_progression, ableton_live, serum2, dojo, memory, midi_export)
