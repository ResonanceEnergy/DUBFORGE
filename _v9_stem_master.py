#!/usr/bin/env python3
"""DUBFORGE — V9 Stem Master (Isolated Process)

Loads V9 premaster and runs the full 14-stage mastering chain.
V9 changes vs V8:
  - Target LUFS: -8.0 (punchier than V8's -8.5)
  - Compression attack: 3ms (tighter transients, V8 was 5ms)
  - Air band taming: -70% above 9kHz (V8 was -80% above 8kHz)
    → preserves more vocal air/breathiness
  - Side channel: ×0.90 (V8 was ×0.85) — wider for harmonized vocals
  - Output path: THE_APOLOGY_THAT_NEVER_CAME_V9

Usage:
    python _v9_stem_master.py
"""

from __future__ import annotations

import gc
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _v9_fast_init  # noqa: F401 — bypass engine/__init__.py

from make_apology import build_apology_dna
from make_full_track import SAMPLE_RATE, write_wav_stereo

OUT_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9")

V9_LYRICS = """\
THE APOLOGY THAT NEVER CAME..
by DUBFORGE

═══════════════════════════════════

[Verse 1 — The Waiting]

I kept your silence like a scar
Wore it underneath my skin
Counting every day you chose
To pretend we never happened

I left the door open wide
For three words you'd never find
But the hallway stayed as empty
As the promise left behind


[Pre-Chorus — The Rising]

And I waited..
Through the seasons turning cold
And I waited..
Till the waiting took its toll


[Chorus — The Revelation]

This is the apology that never came
The silence wearing your name
The letters never written
The words that died in shame

This is the ending you chose to leave
With ashes where we used to breathe
But I found my own beginning
In everything you couldn't be


[DROP 1 — THE WEIGHT]
  (instrumental — the crushing weight
   of unspoken words. Heavy bass = the
   silence made physical. Micro-pauses =
   the gaps where words should have been.)


[Verse 2 — The Acceptance]

You taught me how to hold my breath
In rooms you'll never enter again
How to build a castle from
The rubble of a broken friend

I stopped looking at the door
Stopped listening for your voice
Found the answer in the silence —
Your silence was your choice


[Pre-Chorus 2 — The Letting Go]

And I'm letting go..
Of the ghost of who you were
And I'm letting go..
Of the hurt I didn't deserve


[Chorus 2 — The Liberation]

This was the apology that never came
But I wrote my own rain
Washed the ruins into rivers
And I'll never be the same

This is the end and the start of beginning
A heart that stopped and started beating
I don't need your three words anymore
I found my own healing


[DROP 2 — THE LIBERATION]
  (the biggest moment. Not anger —
   power. The bass doesn't crush, it lifts.
   The silence between the hits is no longer
   absence — it's space you claimed.)


[Outro — Peace]

The apology.. that never came..
Set me free..


═══════════════════════════════════

V9 — Harmonized singing vocals with double-tracking.
Chorus sections feature 3rd harmony layers and
wide stereo placement. Per-section vocal dynamics
shape the emotional arc from intimate verse to
soaring chorus to peaceful resolution.

"The apology that never came" represents the
void left when someone who hurt you refuses to
acknowledge it. The waiting becomes its own prison.
But this song is about the moment you stop waiting —
when you realize their silence is their answer,
and your freedom is your own to take.

This is the end. And the start of beginning.

═══════════════════════════════════
"""


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


def main():
    t0 = time.time()

    print(f"\n{'=' * 64}")
    print("  DUBFORGE V9 STEM MASTER — Dojo Master Pass")
    print("  14-Stage Chain | Subtronics Targets | Final QA")
    print("  V9: LUFS -8.0 | Attack 3ms | Air 9kHz | Side ×0.90")
    print(f"{'=' * 64}")

    # ── Load premaster ───────────────────────────────────────────
    premaster_path = OUT_DIR / "THE_APOLOGY_THAT_NEVER_CAME_V9_premaster.wav"
    if not premaster_path.exists():
        print(f"  ERROR: Premaster not found: {premaster_path}")
        print("  Run _v9_stem_mix.py first.")
        sys.exit(1)

    print("\n  [1/4] Loading premaster...")
    synth_l, synth_r = load_wav_stereo(premaster_path)
    duration_s = len(synth_l) / SAMPLE_RATE
    print(f"    ✓ Loaded: {duration_s:.1f}s ({len(synth_l)} samples)")

    # ── Mastering chain ──────────────────────────────────────────
    print("\n  [2/4] Mastering (14-stage chain, V9 settings)...")
    from engine.mastering_chain import (
        db_to_linear,
        dubstep_master_settings,
        estimate_lufs,
        master,
    )

    settings = dubstep_master_settings()
    settings.target_lufs = -8.0          # V9: punchier (V8 was -8.5)
    settings.ceiling_db = -0.3
    settings.compression_ratio = 3.5
    settings.compression_threshold_db = -14.0
    settings.compression_attack_ms = 3.0  # V9: tighter transients (V8 was 5ms)
    settings.compression_release_ms = 45.0
    if hasattr(settings, "exciter_mix"):
        settings.exciter_mix = 0.08

    print("    Mastering left channel...")
    mastered_l, report = master(synth_l, sr=SAMPLE_RATE, settings=settings)
    print(f"      Input LUFS: {report.input_lufs:.1f}")
    print(f"      Output LUFS: {report.output_lufs:.1f}")

    print("    Mastering right channel...")
    mastered_r, _ = master(synth_r, sr=SAMPLE_RATE, settings=settings)

    del synth_l, synth_r
    gc.collect()

    print(f"    ✓ True peak: {report.output_true_peak_dbtp:.1f} dBTP")

    ceiling_lin = db_to_linear(settings.ceiling_db)

    # Loudness maximization (soft clip, up to 4 passes)
    for pass_num in range(4):
        stereo_peak = max(np.max(np.abs(mastered_l)),
                          np.max(np.abs(mastered_r)))
        rms_val = np.sqrt(np.mean(mastered_l ** 2))
        crest_db = 20 * np.log10(stereo_peak / max(rms_val, 1e-12))
        if crest_db <= 11.0:
            break
        drive = 1.0 / (stereo_peak * 0.65)
        denom = np.tanh(drive * stereo_peak)
        if abs(denom) > 1e-8:
            mastered_l = np.tanh(mastered_l * drive) / denom * ceiling_lin
            mastered_r = np.tanh(mastered_r * drive) / denom * ceiling_lin
        print(f"    Pass {pass_num + 1}: crest={crest_db:.1f}dB → soft clipped")

    # V9: Air band taming — -70% above 9kHz (V8 was -80% above 8kHz)
    # Preserves more vocal breathiness and harmonic air
    from scipy.signal import butter, sosfilt
    air_sos = butter(4, 9000, btype='high', fs=SAMPLE_RATE, output='sos')
    air_l = sosfilt(air_sos, mastered_l)
    air_r = sosfilt(air_sos, mastered_r)
    mastered_l -= air_l * 0.70
    mastered_r -= air_r * 0.70
    del air_l, air_r
    print("    ✓ Air band tamed (-70% above 9kHz, V9: preserves vocal air)")

    # V9: Stereo control — side ×0.90 (V8 was ×0.85)
    # Wider for harmonized vocal stereo spread
    mid = (mastered_l + mastered_r) * 0.5
    side = (mastered_l - mastered_r) * 0.5
    side *= 0.90
    mastered_l = mid + side
    mastered_r = mid - side
    print("    ✓ M/S stereo: side ×0.90 (V9: wider for harmonized vocals)")

    # Final peak normalization to ceiling
    final_peak = max(np.max(np.abs(mastered_l)),
                     np.max(np.abs(mastered_r)))
    if final_peak > 0:
        mastered_l = mastered_l / final_peak * ceiling_lin
        mastered_r = mastered_r / final_peak * ceiling_lin

    final_lufs = estimate_lufs(mastered_l, SAMPLE_RATE)

    # Write master
    safe_name = "THE_APOLOGY_THAT_NEVER_CAME_V9"
    master_path = str(OUT_DIR / f"{safe_name}_master.wav")
    write_wav_stereo(master_path, mastered_l, mastered_r)
    print(f"\n    ✓ Final LUFS: {final_lufs:.1f}")
    print(f"    ✓ Master: {master_path}")

    # ── QA Validation ────────────────────────────────────────────
    print("\n  [3/4] QA Validation (12 gates)...")
    from engine.qa_validator import validate_render

    dna = build_apology_dna()
    has_vocals = any("chops" in sec.elements for sec in dna.arrangement)
    qa = validate_render(mastered_l, mastered_r, SAMPLE_RATE,
                         has_vocals=has_vocals)
    print(qa.summary())

    if not qa.passed:
        failed = [g.name for g in qa.gates if not g.passed]
        print(f"    ⚠ FAILED: {', '.join(failed)}")

    # ── Artwork + Lyrics ─────────────────────────────────────────
    print("\n  [4/4] Press package...")

    lyrics_path = OUT_DIR / f"{safe_name}_lyrics.txt"
    lyrics_path.write_text(V9_LYRICS, encoding="utf-8")
    print(f"    ✓ Lyrics: {lyrics_path}")

    try:
        from engine.artwork_generator import generate_full_artwork
        art = generate_full_artwork(
            track_name="THE APOLOGY THAT NEVER CAME V9",
            artist_name="DUBFORGE",
            palette_name="obsidian",
            output_dir=str(OUT_DIR / "press"),
            energy=0.88, darkness=0.95,
        )
        for k, v in art.items():
            print(f"    ✓ {k}: {v}")
    except Exception as e:
        print(f"    ⚠ Artwork: {e}")

    # ── Summary ──────────────────────────────────────────────────
    elapsed = time.time() - t0

    print(f"\n{'=' * 64}")
    print(f'  COMPLETE: "The Apology That Never Came.." V9')
    print(f"  Duration: {duration_s:.1f}s  |  LUFS: {final_lufs:.1f}")
    print(f"  QA: {'ALL PASS' if qa.passed else 'FAILED'}")
    print(f"  V9: Harmonized singing | Double-track | Per-section dynamics")
    print(f"  Time: {elapsed:.0f}s")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
