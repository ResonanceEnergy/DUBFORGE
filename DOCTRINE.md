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

| Module                 | Code              | Purpose                                         |
|------------------------|-------------------|-------------------------------------------------|
| PHI CORE               | `phi_core`        | Wavetable generator — phi-spaced partials        |
| Rollercoaster Optimizer| `rco`             | Arrangement energy curve engine                  |
| Phase-Separated Bass   | `psbs`            | Multi-layer bass with phase-aligned separation   |
| VIP Delta Loop         | `vip_delta`       | Version comparison and evolution tracker          |
| Trance Arp Engine      | `trance_arp`      | Fibonacci-timed arpeggiator                      |
| Mid-Bass Growl Resampler| `growl_resamp`   | Resample + mangle mid-bass growls                |
| Subtronics Analyzer    | `sb_analyzer`     | Timestamp/metadata analysis of reference tracks  |
| Fibonacci Blueprint    | `fib_blueprint`   | Drop structure templates keyed to Fibonacci      |

---

## Serum Integration Rules

1. Wavetable frames = Fibonacci count (e.g., 8, 13, 21, 34, 55, 89, 144, 233, 256).
2. Macro 1 = phi morph depth. Macro 2 = fractal density. Macro 3 = sub weight. Macro 4 = grit.
3. FM from B oscillator tuned to phi ratio of A.
4. Filter cutoff envelope attack/decay in phi-ratio ms values.
5. Unison detune in cents derived from phi subdivisions.

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
- Serum presets go to `output/serum_presets/`

---

**Version:** 1.0
**Author:** DUBFORGE
**Date:** 2026-03-05
