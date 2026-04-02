#!/usr/bin/env python3
"""DUBFORGE — V9 Stem Mixer (Isolated Process)

Loads pre-rendered V9 stem WAVs and mixes through the full mix bus.
V9 changes vs V8:
  - Vocal bus gain raised 0.72 → 0.80 (singing vocals need presence)
  - Air taming LP raised 10kHz → 12kHz (vocal breathiness/presence)
  - Mid presence boost narrowed to 800-4kHz (+2.5dB, vocal focus)
  - Output path: THE_APOLOGY_THAT_NEVER_CAME_V9

Usage:
    python _v9_stem_mix.py
"""

from __future__ import annotations

import gc
import sys
import time
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _v9_fast_init  # noqa: F401 — bypass engine/__init__.py

from make_apology import build_apology_dna
from make_full_track import SAMPLE_RATE, write_wav_stereo
from engine.dsp_core import dc_block
from engine.mix_bus import MixBusConfig, process_mix_bus

STEM_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9/stems")
OUT_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9")


def load_stem_wav(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load a stereo WAV and return (left, right) as float64 arrays."""
    with wave.open(str(path), 'rb') as wf:
        n = wf.getnframes()
        nch = wf.getnchannels()
        raw = wf.readframes(n)
        sw = wf.getsampwidth()

    if sw == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
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
        samples = i32.astype(np.float64) / 8388608.0
    elif sw == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        samples = np.frombuffer(raw, dtype=np.float32).astype(np.float64)

    if nch >= 2:
        left = samples[0::nch]
        right = samples[1::nch]
    else:
        left = samples.copy()
        right = samples.copy()

    return left, right


# V9 bus gains — vocal bus raised for singing presence
BUS_GAINS = {
    "drums":   0.92,
    "midbass": 1.00,
    "sub":     0.75,
    "lead":    0.85,
    "atmos":   0.50,
    "fx":      0.65,
    "vocals":  0.80,   # V9: raised from 0.72 for singing vocal clarity
    "legacy":  0.70,
}


def main():
    t0 = time.time()

    print(f"\n{'=' * 64}")
    print("  DUBFORGE V9 STEM MIXER — Dojo Mix Pass")
    print("  FX Send/Return | Ninja Focus | Pain Zone | PSBS Stereo")
    print("  V9: Vocal bus +1dB | Air LP 12kHz | Mid focus 800-4kHz")
    print(f"{'=' * 64}")

    # ── Load all stems ───────────────────────────────────────────
    print("\n  [1/4] Loading stems...")
    stems = {}
    stem_names = ["drums", "fx", "lead", "atmos", "midbass", "sub", "vocals", "legacy"]

    for name in stem_names:
        path = STEM_DIR / f"{name}_stem.wav"
        if not path.exists():
            print(f"    ⚠ {name}: NOT FOUND — skipping")
            continue
        left, right = load_stem_wav(path)
        stems[name] = {"left": left, "right": right}
        peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
        rms = np.sqrt(np.mean(left ** 2))
        print(f"    ✓ {name}: {len(left)/SAMPLE_RATE:.1f}s, "
              f"peak={peak:.3f}, rms={rms:.4f}")

    if not stems:
        print("  ERROR: No stems found! Run _v9_stem_render.py first.")
        sys.exit(1)

    total_samples = max(len(s["left"]) for s in stems.values())
    print(f"\n  Track length: {total_samples/SAMPLE_RATE:.1f}s")

    # Pad all stems to same length
    for name, data in stems.items():
        for ch in ("left", "right"):
            if len(data[ch]) < total_samples:
                data[ch] = np.pad(data[ch], (0, total_samples - len(data[ch])))

    # ── Build DNA for section map ────────────────────────────────
    print("\n  [2/4] Building section map...")
    dna = build_apology_dna()
    bar_dur = 60.0 / dna.bpm * 4

    section_starts = []
    cum_bars = 0
    for sec in dna.arrangement:
        section_starts.append(round(cum_bars * bar_dur * SAMPLE_RATE))
        cum_bars += sec.bars
    section_starts.append(total_samples)

    print(f"  Sections: {len(dna.arrangement)}")
    for i, sec in enumerate(dna.arrangement):
        s = section_starts[i]
        e = section_starts[i + 1]
        sec_dur = (e - s) / SAMPLE_RATE
        print(f"    {sec.name:10s}: {sec.bars:3d} bars, "
              f"energy={sec.energy:.2f}, {sec_dur:.1f}s")

    # ── Mix Bus Processing per section ───────────────────────────
    print("\n  [3/4] Mix Bus Processing (per-section)...")
    output_left = np.zeros(total_samples)
    output_right = np.zeros(total_samples)

    mix_config = MixBusConfig(
        enable_freq_stereo=True,
        enable_ninja_focus=True,
        enable_pain_zone=True,
        enable_inter_sidechain=True,
        enable_parallel_comp=True,
        enable_energy_curves=True,
        enable_fx_sends=True,
        parallel_comp_mix=0.25,
        parallel_comp_threshold_db=-18.0,
    )

    for sec_idx, sec in enumerate(dna.arrangement):
        s = section_starts[sec_idx]
        e = section_starts[sec_idx + 1]
        sec_len = e - s

        bus_input = {}
        for stem_name, stem_data in stems.items():
            sec_l = stem_data["left"][s:e].copy()
            sec_r = stem_data["right"][s:e].copy()

            if np.max(np.abs(sec_l)) < 1e-8 and np.max(np.abs(sec_r)) < 1e-8:
                continue

            gain = BUS_GAINS.get(stem_name, 0.6)
            sec_l *= gain
            sec_r *= gain

            bus_input[stem_name] = {"left": sec_l, "right": sec_r}

        if not bus_input:
            print(f"    [{sec.name}] — silent")
            continue

        mix_l, mix_r = process_mix_bus(
            bus_input, sec.name,
            energy_start=sec.energy,
            energy_end=sec.energy,
            config=mix_config,
            sr=SAMPLE_RATE,
        )

        m_len = min(len(mix_l), sec_len)
        output_left[s:s + m_len] += mix_l[:m_len]
        output_right[s:s + m_len] += mix_r[:m_len]

        active = ", ".join(bus_input.keys())
        print(f"    [{sec.name}] {len(bus_input)} buses: {active}")

    del stems
    gc.collect()

    # ── Spectral Correction EQ (V9: vocal-tuned) ─────────────────
    print("\n  [4/4] Spectral Correction EQ (V9: vocal-tuned)...")

    output_left = dc_block(output_left)
    output_right = dc_block(output_right)

    # HP at 30Hz
    hp_sos = butter(4, 30.0, btype='high', fs=SAMPLE_RATE, output='sos')
    output_left = sosfilt(hp_sos, output_left).astype(np.float64)
    output_right = sosfilt(hp_sos, output_right).astype(np.float64)
    print("    ✓ HP 30Hz (4th order)")

    # Sub tilt at 80Hz
    ls_sos = butter(2, 80.0, btype='high', fs=SAMPLE_RATE, output='sos')
    sub_l = output_left - sosfilt(ls_sos, output_left).astype(np.float64)
    sub_r = output_right - sosfilt(ls_sos, output_right).astype(np.float64)
    output_left -= sub_l * 0.75
    output_right -= sub_r * 0.75
    print("    ✓ Sub tilt 80Hz (-6dB shelving)")

    # V9: Mid presence narrowed to 800-4kHz (+2.5dB) for vocal focus
    mid_lo = butter(2, 800.0, btype='high', fs=SAMPLE_RATE, output='sos')
    mid_hi = butter(2, 4000.0, btype='low', fs=SAMPLE_RATE, output='sos')
    mid_l = sosfilt(mid_hi, sosfilt(mid_lo, output_left)).astype(np.float64)
    mid_r = sosfilt(mid_hi, sosfilt(mid_lo, output_right)).astype(np.float64)
    output_left += mid_l * 0.33   # ~+2.5dB
    output_right += mid_r * 0.33
    print("    ✓ Mid presence 800-4kHz (+2.5dB) — vocal focus")

    # V9: Air taming LP raised to 12kHz (preserve vocal breathiness)
    lp_sos = butter(3, 12000.0, btype='low', fs=SAMPLE_RATE, output='sos')
    output_left = sosfilt(lp_sos, output_left).astype(np.float64)
    output_right = sosfilt(lp_sos, output_right).astype(np.float64)
    print("    ✓ Air taming LP 12kHz (3rd order) — V9: raised from 10kHz")

    # Normalize to -1.5 dBFS
    peak = max(np.max(np.abs(output_left)), np.max(np.abs(output_right)))
    target_peak = 10.0 ** (-1.5 / 20.0)
    if peak > 0:
        output_left *= target_peak / peak
        output_right *= target_peak / peak
    print(f"    ✓ Normalized to -1.5 dBFS (peak was {20*np.log10(peak+1e-12):.1f})")

    # ── Write premaster ──────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    premaster_path = OUT_DIR / "THE_APOLOGY_THAT_NEVER_CAME_V9_premaster.wav"
    write_wav_stereo(str(premaster_path), output_left, output_right)

    rms_l = np.sqrt(np.mean(output_left ** 2))
    lufs_approx = 20 * np.log10(rms_l + 1e-12) - 0.691
    elapsed = time.time() - t0

    print(f"\n  ✓ Premaster: {premaster_path}")
    print(f"  ✓ Duration: {len(output_left)/SAMPLE_RATE:.1f}s")
    print(f"  ✓ LUFS (approx): {lufs_approx:.1f}")
    print(f"  ✓ Mix time: {elapsed:.0f}s")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
