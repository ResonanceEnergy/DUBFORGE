# DUBFORGE — Phi Constants Reference
> Layer 3 stable config. All timing and frequency parameters derive from these.

---

## Dan Winter Foundation

DUBFORGE uses **phi ratio (φ = 1.618033...)** and **Planck×phi fractal mathematics**
as the organizing principle for all timing, envelope, and frequency parameters.
This creates self-similar structure at every scale — from microsecond transients
to 8-bar sections.

---

## Core Constants

```python
PHI      = 1.6180339887498948
PHI_INV  = 0.6180339887498948   # 1/φ = φ - 1
PHI2     = 2.6180339887498948   # φ²
SQRT5    = 2.23606797749979

# Fibonacci sequence (used for bar counts, note divisions, filter steps)
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]

# A4 tuning (Dan Winter: 432Hz = more coherent than 440Hz)
A4_432 = 432.0
A4_440 = 440.0   # standard — use 432 for DUBFORGE output

# Reference: C at 432-tuning
C4_432 = 256.0   # 2^8 — pure octave integer
```

---

## Frequency Table (A4 = 432 Hz)

| Note | Hz | Note | Hz |
|------|----|------|----|
| A0 | 27.0 | B3 | 242.7 |
| A1 | 54.0 | C4 | 256.0 |
| A2 | 108.0 | D4 | 287.4 |
| A3 | 216.0 | E4 | 323.1 |
| B2 | 121.4 | A4 | 432.0 |
| C3 | 128.0 | C5 | 512.0 |
| D3 | 144.0 | A5 | 864.0 |
| E3 | 161.6 | A6 | 1728.0 |
| F3 | 171.2 | A7 | 3456.0 |

Sub bass root = **A1 = 54 Hz** (matches A4=432 octave series)  
Key of F: **F1 = 43.65 Hz** → standard DUBFORGE sub root

---

## Phi Timing (at 140 BPM)

```
beat_s  = 60 / bpm                        # 0.4286s at 140bpm
bar_s   = beat_s × 4                      # 1.7143s
phi_bar = bar_s × PHI                     # 2.7725s (≈ 5-beat phi crossing)

# Envelope targets (phi-derived)
ATTACK_PHI   = beat_s × PHI_INV           # 0.265s — snappy but not click
DECAY_PHI    = beat_s × 1.0               # 0.429s — one beat decay
SUSTAIN_PHI  = 0.618                      # 61.8% sustain level
RELEASE_PHI  = bar_s × PHI_INV            # 1.059s — φ bar tail
```

---

## Section Length Fibonacci Rule

Section lengths MUST be Fibonacci numbers of bars:

| Section | Fibonacci Bars | At 140 BPM |
|---------|---------------|-----------|
| Intro | 8 | 13.7s |
| Build 1 | 16 | 27.4s |
| Drop 1 | 32 | 54.9s |
| Breakdown | 8 | 13.7s |
| Build 2 | 8 | 13.7s |
| Drop 2 | 32 | 54.9s |
| Outro | 8 | 13.7s |
| **Total** | **112 bars** | **3.2 min** |

Minimum viable: [8, 8, 16, 8, 8, 16, 8] = 72 bars = 2.1 min

---

## Phi Modulation Rates

| Rate Name | Beats | At 140 BPM |
|----------|-------|-----------|
| Phi Fast | 1/φ~0.618 beats | Tremolo |
| Phi Slow | φ beats | Wobble mid |
| Phi Bar | φ bars | Filter sweep |
| Phi Section | φ×8 = 13 bars | Macro evolution |

## LFO Rate Lock (Serum 2)

All LFOs must sync to DAW tempo. Rate divisions:
```
1/32, 1/16, 1/8, 1/4, 1/2, 1/1, 2/1, 4/1, 8/1
Preferred rates: 1/2 (wobble), 1/8 (tremolo), 4/1 (filter sweep)
```
