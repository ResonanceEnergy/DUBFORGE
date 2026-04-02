#!/usr/bin/env python3
"""DUBFORGE — V9 Post-Processing Analysis (Dojo + Subtronics Audit)

Runs AFTER mixing, BEFORE mastering. Analyzes the V9 premaster against
Dojo methodology and Subtronics production benchmarks.

V9 changes vs V8:
  - Harmonized singing vocals with double-tracking
  - Vocal-tuned spectral analysis
  - Paths point to THE_APOLOGY_THAT_NEVER_CAME_V9

Usage:
    python _v9_stem_postprocess.py
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _v9_fast_init  # noqa: F401 — bypass engine/__init__.py

from make_apology import build_apology_dna
from make_full_track import SAMPLE_RATE

STEM_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9/stems")
OUT_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9")


def load_wav_stereo(path):
    """Load stereo WAV → (left, right) float64."""
    with wave.open(str(path), 'rb') as wf:
        n = wf.getnframes()
        nch = wf.getnchannels()
        raw = wf.readframes(n)
        sw = wf.getsampwidth()
    if sw == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sw == 3:
        raw_bytes = np.frombuffer(raw, dtype=np.uint8)
        n_samp = len(raw_bytes) // 3
        raw_bytes = raw_bytes[:n_samp * 3].reshape(-1, 3)
        i32 = (raw_bytes[:, 0].astype(np.int32)
               | (raw_bytes[:, 1].astype(np.int32) << 8)
               | (raw_bytes[:, 2].astype(np.int32) << 16))
        i32[i32 >= 0x800000] -= 0x1000000
        samples = i32.astype(np.float64) / 8388608.0
    elif sw == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        samples = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    if nch >= 2:
        return samples[0::nch], samples[1::nch]
    return samples.copy(), samples.copy()


def band_energy(spec, freqs, lo, hi):
    mask = (freqs >= lo) & (freqs < hi)
    return np.sqrt(np.mean(spec[mask] ** 2)) if mask.sum() > 0 else 0.0


def main():
    print(f"\n{'=' * 64}")
    print("  DUBFORGE V9 POST-PROCESSING AUDIT")
    print("  Dojo Methodology + Subtronics Benchmarks")
    print("  V9: Harmonized Singing | Double-Track | Per-Section Dynamics")
    print(f"{'=' * 64}")

    dna = build_apology_dna()
    bar_dur = 60.0 / dna.bpm * 4
    beat_dur = 60.0 / dna.bpm

    section_starts = []
    cum_bars = 0
    for sec in dna.arrangement:
        section_starts.append(round(cum_bars * bar_dur * SAMPLE_RATE))
        cum_bars += sec.bars
    total_samples = round(cum_bars * bar_dur * SAMPLE_RATE)
    section_starts.append(total_samples)

    issues = []
    passes = []

    # ═══ 1. PER-STEM ANALYSIS ═══
    print(f"\n{'─' * 64}")
    print("  1. PER-STEM ANALYSIS")
    print(f"{'─' * 64}")

    stem_names = ["drums", "fx", "lead", "atmos", "midbass", "sub", "vocals", "legacy"]

    for name in stem_names:
        path = STEM_DIR / f"{name}_stem.wav"
        if not path.exists():
            print(f"  ⚠ {name}: MISSING")
            issues.append(f"Stem missing: {name}")
            continue

        left, right = load_wav_stereo(path)
        mono = (left + right) / 2.0
        peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
        rms = np.sqrt(np.mean(mono ** 2))
        peak_db = 20 * np.log10(peak + 1e-12)
        rms_db = 20 * np.log10(rms + 1e-12)

        unique = len(np.unique(np.round(left[:SAMPLE_RATE * 10] * 32768).astype(int)))

        N = min(len(mono), SAMPLE_RATE * 10)
        spec = np.abs(np.fft.rfft(mono[:N] * np.hanning(N)))
        flatness = np.exp(np.mean(np.log(spec + 1e-12))) / (np.mean(spec) + 1e-12)

        status = "OK"
        notes = []
        if rms_db < -40:
            status = "WEAK"
            notes.append("very low RMS")
            issues.append(f"Stem weak: {name} (RMS {rms_db:.1f}dB)")
        if unique < 5000:
            status = "8BIT"
            notes.append(f"only {unique} unique values")
            issues.append(f"Stem quantized: {name} ({unique} unique vals)")
        if flatness > 0.6 and name not in ("atmos", "fx"):
            notes.append(f"noise-like (flatness={flatness:.2f})")

        note_str = f" — {', '.join(notes)}" if notes else ""
        print(f"  {name:10s}: peak={peak_db:+6.1f}dB  rms={rms_db:+6.1f}dB  "
              f"uniq={unique:6d}  flat={flatness:.3f}  [{status}]{note_str}")

        del left, right, mono, spec

    # ═══ 2-10. PREMASTER ANALYSIS ═══
    premaster_path = OUT_DIR / "THE_APOLOGY_THAT_NEVER_CAME_V9_premaster.wav"
    if not premaster_path.exists():
        print(f"\n  ⚠ Premaster not found: {premaster_path}")
        print("    Run _v9_stem_mix.py first.")
        return

    left, right = load_wav_stereo(premaster_path)
    mono = (left + right) / 2.0

    # ═══ 2. SECTION ENERGY CONTRAST ═══
    print(f"\n{'─' * 64}")
    print("  2. SECTION ENERGY CONTRAST")
    print(f"{'─' * 64}")

    section_rms = {}
    for i, sec in enumerate(dna.arrangement):
        s = section_starts[i]
        e = min(section_starts[i + 1], len(mono))
        chunk = mono[s:e]
        rms = np.sqrt(np.mean(chunk ** 2))
        rms_db = 20 * np.log10(rms + 1e-12)
        section_rms[sec.name] = rms
        bar_vis = "#" * int(max(0, rms * 100))
        print(f"    {sec.name:10s}: RMS={rms:.4f} ({rms_db:+.1f}dB) {bar_vis}")

    for quiet, loud in [("intro", "drop1"), ("break", "drop2")]:
        if quiet in section_rms and loud in section_rms:
            contrast = 20 * np.log10(
                section_rms[loud] / (section_rms[quiet] + 1e-12))
            ok = 6 <= contrast <= 18
            tag = "PASS" if ok else "FAIL"
            print(f"    {quiet}→{loud}: {contrast:.1f}dB [{tag}]")
            if ok:
                passes.append(f"Contrast {quiet}→{loud}: {contrast:.1f}dB")
            else:
                issues.append(f"Contrast {quiet}→{loud}: {contrast:.1f}dB")

    # ═══ 3. SPECTRAL BALANCE ═══
    print(f"\n{'─' * 64}")
    print("  3. SPECTRAL BALANCE — PSBS (drop1)")
    print(f"{'─' * 64}")

    drop1_idx = next((i for i, s in enumerate(dna.arrangement)
                      if "drop1" == s.name), None)
    if drop1_idx is not None:
        s = section_starts[drop1_idx]
        e = min(section_starts[drop1_idx + 1], len(mono))
        drop = mono[s:e]
        N = len(drop)
        freqs = np.fft.rfftfreq(N, 1 / SAMPLE_RATE)
        spectrum = np.abs(np.fft.rfft(drop * np.hanning(N)))

        sub_e = band_energy(spectrum, freqs, 20, 80)
        low_e = band_energy(spectrum, freqs, 80, 200)
        mid_e = band_energy(spectrum, freqs, 200, 2000)
        high_e = band_energy(spectrum, freqs, 2000, 8000)
        air_e = band_energy(spectrum, freqs, 8000, 20000)
        total = sub_e + low_e + mid_e + high_e + air_e + 1e-12

        bands = [
            ("SUB  20-80Hz", sub_e, 15, 30),
            ("LOW  80-200Hz", low_e, 10, 40),
            ("MID  200-2kHz", mid_e, 20, 40),
            ("HIGH 2k-8kHz", high_e, 3, 22),
            ("AIR  8k-20kHz", air_e, 2, 12),
        ]
        for label, val, lo_t, hi_t in bands:
            pct = val / total * 100
            ok = lo_t <= pct <= hi_t
            tag = "OK" if ok else "MISS"
            print(f"    {label}: {pct:5.1f}%  [{lo_t}-{hi_t}%]  [{tag}]")
            if not ok:
                issues.append(f"Spectrum {label}: {pct:.0f}%")

    # ═══ 4. SIDECHAIN PUMP DEPTH ═══
    print(f"\n{'─' * 64}")
    print("  4. SIDECHAIN PUMP DEPTH (drop1 bar 0)")
    print(f"{'─' * 64}")

    if drop1_idx is not None:
        drop_start = section_starts[drop1_idx]
        for beat in range(4):
            beat_s = drop_start + int(beat * beat_dur * SAMPLE_RATE)
            kick_peak = np.max(np.abs(
                mono[beat_s:beat_s + int(0.010 * SAMPLE_RATE)]))
            trough_s = beat_s + int(0.030 * SAMPLE_RATE)
            trough_e = beat_s + int(0.060 * SAMPLE_RATE)
            trough_rms = np.sqrt(np.mean(mono[trough_s:trough_e] ** 2))
            rec_s = beat_s + int(0.150 * SAMPLE_RATE)
            rec_e = beat_s + int(0.250 * SAMPLE_RATE)
            rec_rms = np.sqrt(np.mean(mono[rec_s:rec_e] ** 2))
            pump_db = 20 * np.log10(
                rec_rms / (trough_rms + 1e-12)) if trough_rms > 0.001 else 0
            print(f"    Beat {beat}: kick={kick_peak:.3f} "
                  f"trough={trough_rms:.4f} recovery={rec_rms:.4f} "
                  f"pump={pump_db:+.1f}dB")

    # ═══ 5. TRANSIENT DENSITY ═══
    print(f"\n{'─' * 64}")
    print("  5. TRANSIENT DENSITY (drop1, 8 bars)")
    print(f"{'─' * 64}")

    if drop1_idx is not None:
        drop_start = section_starts[drop1_idx]
        drop_8bars = mono[drop_start:drop_start + int(8 * bar_dur * SAMPLE_RATE)]
        env = np.abs(drop_8bars)
        win = int(0.005 * SAMPLE_RATE)
        env_smooth = np.convolve(env, np.ones(win) / win, mode='same')
        log_env = np.log10(env_smooth + 1e-10)
        log_diff = np.diff(log_env, prepend=log_env[0])
        log_diff = np.maximum(log_diff, 0)
        onset_win = int(0.005 * SAMPLE_RATE)
        onset_env = np.convolve(log_diff, np.ones(onset_win) / onset_win,
                                mode='same')
        onset_nz = onset_env[onset_env > 0]
        if len(onset_nz) > 0:
            onset_thresh = np.percentile(onset_nz, 92)
            peaks_idx, _ = find_peaks(
                onset_env, height=onset_thresh,
                distance=int(0.06 * SAMPLE_RATE))
            hits_per_bar = len(peaks_idx) / 8
            ok = 8 <= hits_per_bar <= 20
            tag = "PASS" if ok else "MISS"
            print(f"    Hits: {len(peaks_idx)}, per bar: {hits_per_bar:.1f} [{tag}]")
            if not ok:
                issues.append(f"Transient density: {hits_per_bar:.1f}/bar")
            else:
                passes.append(f"Transient density: {hits_per_bar:.1f}/bar")

    # ═══ 6. STEREO FIELD ═══
    print(f"\n{'─' * 64}")
    print("  6. STEREO FIELD ANALYSIS")
    print(f"{'─' * 64}")

    mid_sig = (left + right) / 2.0
    side_sig = (left - right) / 2.0
    mid_rms = np.sqrt(np.mean(mid_sig ** 2))
    side_rms = np.sqrt(np.mean(side_sig ** 2))
    width = side_rms / (mid_rms + 1e-12)
    ok = 0.2 <= width <= 0.7
    tag = "PASS" if ok else "MISS"
    print(f"    Mid RMS: {mid_rms:.4f}  Side RMS: {side_rms:.4f}")
    print(f"    Width (side/mid): {width:.3f} [{tag}]")
    if not ok:
        issues.append(f"Stereo width: {width:.3f}")
    else:
        passes.append(f"Stereo width: {width:.3f}")

    # ═══ 7. SUB BASS PURITY ═══
    print(f"\n{'─' * 64}")
    print("  7. SUB BASS PURITY CHECK")
    print(f"{'─' * 64}")

    if drop1_idx is not None:
        s = section_starts[drop1_idx]
        e = min(section_starts[drop1_idx + 1], len(mono))
        drop = mono[s:e]
        N = len(drop)
        freqs = np.fft.rfftfreq(N, 1 / SAMPLE_RATE)
        spectrum = np.abs(np.fft.rfft(drop * np.hanning(N)))
        sub_mask = (freqs >= 20) & (freqs < 120)
        sub_spec = spectrum[sub_mask]
        sub_freqs = freqs[sub_mask]
        peak_idx = np.argmax(sub_spec)
        f0 = sub_freqs[peak_idx]
        print(f"    Sub fundamental: {f0:.1f} Hz")

        f0_mask = (freqs >= f0 - 5) & (freqs <= f0 + 5)
        f1_mask = (freqs >= f0 * 2 - 10) & (freqs <= f0 * 2 + 10)
        f0_e = np.max(spectrum[f0_mask]) if f0_mask.sum() > 0 else 0
        f1_e = np.max(spectrum[f1_mask]) if f1_mask.sum() > 0 else 0
        if f0_e > 0:
            ratio_db = 20 * np.log10(f1_e / f0_e)
            ok = ratio_db < -10
            tag = "OK" if ok else "MISS"
            print(f"    2nd harmonic ratio: {ratio_db:+.1f}dB [{tag}]")

    # ═══ 8. QUANTIZATION DEPTH ═══
    print(f"\n{'─' * 64}")
    print("  8. QUANTIZATION DEPTH CHECK")
    print(f"{'─' * 64}")

    for i, sec in enumerate(dna.arrangement):
        s = section_starts[i]
        e = min(section_starts[i + 1], len(mono))
        chunk = mono[s:e]
        if len(chunk) < SAMPLE_RATE:
            continue
        sample = chunk[:SAMPLE_RATE * 5]
        int_vals = np.round(sample * 32768).astype(int)
        unique = len(np.unique(int_vals))
        eff_bits = np.log2(unique) if unique > 1 else 0
        steps = np.abs(np.diff(int_vals))
        med_step = int(np.median(steps[steps > 0])) if np.sum(steps > 0) else 0

        status = "OK" if eff_bits > 12 else ("WARN" if eff_bits > 10 else "BAD")
        print(f"    {sec.name:10s}: unique={unique:6d}  "
              f"bits={eff_bits:.1f}  medStep={med_step:4d}  [{status}]")
        if eff_bits <= 10:
            issues.append(f"Quantization: {sec.name} only {eff_bits:.1f} bits")

    # ═══ 9. SILENCE DETECTION ═══
    print(f"\n{'─' * 64}")
    print("  9. SILENCE / DEAD SECTION CHECK")
    print(f"{'─' * 64}")

    window_samples = int(2.0 * SAMPLE_RATE)
    dead_spots = []
    for pos in range(0, len(mono) - window_samples, window_samples):
        chunk = mono[pos:pos + window_samples]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms < 0.0005:
            t = pos / SAMPLE_RATE
            dead_spots.append(t)
            print(f"    ⚠ Dead spot at {t:.1f}s (RMS={rms:.6f})")

    if not dead_spots:
        print("    ✓ No dead spots detected")
        passes.append("No dead sections")
    else:
        issues.append(f"{len(dead_spots)} dead spots found")

    # ═══ 10. QA VALIDATION ═══
    print(f"\n{'─' * 64}")
    print("  10. QA VALIDATION (12 gates)")
    print(f"{'─' * 64}")

    from engine.qa_validator import validate_render
    has_vocals = any("chops" in sec.elements for sec in dna.arrangement)
    qa = validate_render(left, right, SAMPLE_RATE, has_vocals=has_vocals)
    print(qa.summary())
    if qa.passed:
        passes.append("QA: all 12 gates pass")
    else:
        failed = [g.name for g in qa.gates if not g.passed]
        issues.append(f"QA failed: {', '.join(failed)}")

    # ═══ SCORECARD ═══
    print(f"\n{'=' * 64}")
    print("  DUBFORGE V9 POST-PROCESSING SCORECARD")
    print(f"{'=' * 64}")

    if passes:
        print(f"\n  PASSES ({len(passes)}):")
        for p in passes:
            print(f"    [+] {p}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    [-] {iss}")

    total_checks = len(passes) + len(issues)
    score = len(passes) / max(total_checks, 1) * 100
    print(f"\n  Score: {score:.0f}% ({len(passes)}/{total_checks})")

    if score >= 80:
        print("  ✓ Ready for mastering")
    elif score >= 60:
        print("  ⚠ Minor issues — proceed with caution")
    else:
        print("  ✗ Significant issues — review stems before mastering")

    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
