#!/usr/bin/env python3
"""DUBFORGE — V9 Stem Health Check (runs per-stem after rendering).

Called automatically by the pipeline after each stem renders.
Checks: peak level, RMS, bit depth, spectral balance, anomalies.

V9: Same health gates as V8, paths updated to V9 output.

Usage:
    python _v9_stem_health_check.py drums
    python _v9_stem_health_check.py vocals
    python _v9_stem_health_check.py --all
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _v9_fast_init  # noqa: F401 — bypass engine/__init__.py

from make_full_track import SAMPLE_RATE

STEM_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9/stems")
OUT_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9")

EXPECTED = {
    "drums":    (-6.0, 0.0,  -28.0, -14.0),
    "fx":       (-20.0, 0.0, -50.0, -20.0),
    "lead":     (-6.0, 0.0,  -28.0, -14.0),
    "atmos":    (-30.0, -5.0,-55.0, -25.0),
    "midbass":  (-6.0, 0.0,  -22.0, -8.0),
    "sub":      (-10.0, 0.0, -16.0, -5.0),
    "vocals":   (-10.0, 0.0, -30.0, -12.0),
    "legacy":   (-25.0, 0.0, -50.0, -20.0),
    "premaster": (-3.0, 0.0, -18.0, -8.0),
}


def load_mono(path: Path) -> np.ndarray:
    """Load WAV → mono float64."""
    with wave.open(str(path), "rb") as wf:
        n = wf.getnframes()
        nch = wf.getnchannels()
        raw = wf.readframes(n)
        sw = wf.getsampwidth()
    if sw == 2:
        s = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sw == 3:
        # 24-bit PCM: unpack 3-byte little-endian signed integers
        raw_bytes = np.frombuffer(raw, dtype=np.uint8)
        n_samples = len(raw_bytes) // 3
        raw_bytes = raw_bytes[:n_samples * 3].reshape(-1, 3)
        i32 = (raw_bytes[:, 0].astype(np.int32)
               | (raw_bytes[:, 1].astype(np.int32) << 8)
               | (raw_bytes[:, 2].astype(np.int32) << 16))
        # Sign-extend from 24-bit
        i32[i32 >= 0x800000] -= 0x1000000
        s = i32.astype(np.float64) / 8388608.0
    elif sw == 4:
        s = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        s = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    if nch >= 2:
        left = s[0::nch]
        right = s[1::nch]
        return (left + right) / 2.0
    return s


def check_stem(name: str) -> dict:
    """Run health check on one stem (or premaster)."""
    if name == "premaster":
        path = OUT_DIR / "THE_APOLOGY_THAT_NEVER_CAME_V9_premaster.wav"
    else:
        path = STEM_DIR / f"{name}_stem.wav"
    if not path.exists():
        return {"name": name, "status": "MISSING", "issues": ["File not found"]}

    mono = load_mono(path)
    issues = []
    warnings = []

    peak = np.max(np.abs(mono))
    rms = np.sqrt(np.mean(mono ** 2))
    peak_db = 20 * np.log10(peak + 1e-12)
    rms_db = 20 * np.log10(rms + 1e-12)
    active_pct = np.sum(np.abs(mono) > 1e-6) / len(mono) * 100
    duration = len(mono) / SAMPLE_RATE

    nonzero = mono[np.abs(mono) > 1e-6]
    if len(nonzero) > SAMPLE_RATE:
        chunk = nonzero[:SAMPLE_RATE * 5]
        unique = len(np.unique(np.round(chunk * 32768).astype(int)))
        eff_bits = np.log2(unique) if unique > 1 else 0
    else:
        eff_bits = 0 if len(nonzero) == 0 else 16.0

    clip_samples = np.sum(np.abs(mono) >= 0.9999)
    clip_pct = clip_samples / len(mono) * 100
    dc_offset = np.mean(mono)

    from scipy.signal import butter, sosfilt

    def band_rms(lo, hi):
        sos = butter(4, [lo, hi], btype="band", fs=SAMPLE_RATE, output="sos")
        return np.sqrt(np.mean(sosfilt(sos, mono) ** 2))

    sub_e = band_rms(20, 80)
    low_e = band_rms(80, 200)
    mid_e = band_rms(200, 2000)
    high_e = band_rms(2000, 8000)
    air_e = band_rms(8000, min(16000, SAMPLE_RATE // 2 - 1))
    total_e = sub_e + low_e + mid_e + high_e + air_e
    air_pct = air_e / total_e * 100 if total_e > 0 else 0

    expected = EXPECTED.get(name, (-10.0, 0.0, -40.0, -10.0))
    pk_lo, pk_hi, rms_lo, rms_hi = expected

    if peak_db < pk_lo:
        warnings.append(f"Peak too low ({peak_db:.1f}dB, expect >{pk_lo}dB)")
    if rms_db < rms_lo:
        warnings.append(f"RMS too low ({rms_db:.1f}dB, expect >{rms_lo}dB)")
    if rms_db > rms_hi:
        issues.append(f"RMS too hot ({rms_db:.1f}dB, expect <{rms_hi}dB)")

    if active_pct < 10:
        issues.append(f"Very low activity ({active_pct:.1f}%)")
    elif active_pct < 20:
        warnings.append(f"Low activity ({active_pct:.1f}%)")

    if eff_bits < 10 and len(nonzero) > SAMPLE_RATE:
        issues.append(f"Low bit depth ({eff_bits:.1f} bits)")

    if clip_pct > 0.1:
        issues.append(f"Clipping ({clip_pct:.2f}% samples at ceiling)")
    elif clip_pct > 0.01:
        warnings.append(f"Minor clipping ({clip_pct:.3f}%)")

    if abs(dc_offset) > 0.005:
        issues.append(f"DC offset ({dc_offset:.4f})")

    if air_pct > 25 and name not in ("atmos",):
        issues.append(f"Excess air band ({air_pct:.1f}%)")
    elif air_pct > 15 and name not in ("atmos", "fx"):
        warnings.append(f"High air band ({air_pct:.1f}%)")

    status = "FAIL" if issues else ("WARN" if warnings else "PASS")

    return {
        "name": name,
        "status": status,
        "peak_db": peak_db,
        "rms_db": rms_db,
        "active_pct": active_pct,
        "eff_bits": eff_bits,
        "clip_pct": clip_pct,
        "dc_offset": dc_offset,
        "air_pct": air_pct,
        "duration": duration,
        "issues": issues,
        "warnings": warnings,
    }


def print_result(r: dict):
    """Print health check result for one stem."""
    icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "MISSING": "✗"}[r["status"]]
    print(f"  [{icon}] {r['name']:10s}  {r['status']:4s}  ", end="")

    if r["status"] == "MISSING":
        print("File not found")
        return

    print(f"peak={r['peak_db']:+.1f}dB  rms={r['rms_db']:+.1f}dB  "
          f"active={r['active_pct']:.0f}%  bits={r['eff_bits']:.0f}  "
          f"air={r['air_pct']:.0f}%")

    for issue in r["issues"]:
        print(f"         ✗ {issue}")
    for warn in r["warnings"]:
        print(f"         ⚠ {warn}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DUBFORGE V9 stem health check")
    parser.add_argument("stem", nargs="?", default="--all",
                        help="Stem name or --all")
    args = parser.parse_args()

    print(f"\n  DUBFORGE V9 STEM HEALTH CHECK")
    print(f"  {'─' * 50}")

    if args.stem == "--all":
        stems = list(EXPECTED.keys())
    else:
        stems = [args.stem]

    results = []
    for s in stems:
        r = check_stem(s)
        print_result(r)
        results.append(r)

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] in ("FAIL", "MISSING"))

    print(f"  {'─' * 50}")
    print(f"  {pass_count} PASS  {warn_count} WARN  {fail_count} FAIL")

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
