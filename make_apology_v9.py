#!/usr/bin/env python3
"""DUBFORGE — "The Apology That Never Came.." V9

Stem-by-stem rendering pipeline with HARMONIZED SINGING VOCALS.

═══════════════════════════════════════════════════════════════════
V9 Changes vs V8:
  - Harmonized singing: 3rd harmony layers in chorus sections
    → chord-aware harmony via RubberBand R3 pitch matching
  - Double-tracked lead vocal with ±5 cent detune for richness
  - Per-section vocal dynamics:
      verse = intimate (0.50 gain, centered)
      pre-chorus = rising (0.55, slight width)
      chorus = open (0.60 + harmony 0.35, wide stereo)
      outro = fading (0.45, peaceful)
  - Vocal bus gain: 0.72 → 0.80 (singing needs presence)
  - Mix EQ: mid focus narrowed 800-4kHz (+2.5dB, vocal clarity)
  - Air LP: 10kHz → 12kHz (preserve vocal breathiness)
  - Master: LUFS -8.0 (punchier), attack 3ms (tighter transients)
  - Master air: 9kHz/-70% (V8 was 8kHz/-80%, preserves vocal air)
  - Master side: ×0.90 (V8 was ×0.85, wider for harmony spread)

V8 foundation retained:
  - RubberBand R3 --fine --formant (formant-preserving pitch shift)
  - Edge TTS pitch param tuned toward target note
  - Per-line pitch shift (not blind syllable segmentation)
  - Correct pitch anchor (~200 Hz)

Dojo Approach (ill.Gates / Producer Dojo):
  Phase 1 — SOUND DESIGN: Render each stem in isolation
  Phase 2 — MIX: Load stems, apply mix bus + FX sends
  Phase 3 — POST-PROCESS: Analyze against Subtronics benchmarks
  Phase 4 — MASTER: 14-stage mastering chain
═══════════════════════════════════════════════════════════════════

Pipeline:
  [1]  Render DRUMS stem    → stems/drums_stem.wav    → free RAM
  [2]  Render FX stem       → stems/fx_stem.wav       → free RAM
  [3]  Render LEAD stem     → stems/lead_stem.wav     → free RAM
  [4]  Render ATMOS stem    → stems/atmos_stem.wav    → free RAM
  [5]  Render MIDBASS stem  → stems/midbass_stem.wav  → free RAM
  [6]  Render SUB stem      → stems/sub_stem.wav      → free RAM
  [7]  Render VOCALS stem   → stems/vocals_stem.wav   → free RAM
  [8]  Render LEGACY stem   → stems/legacy_stem.wav   → free RAM
  [9]  Mix all stems        → premaster.wav           → free RAM
  [10] Post-process audit   → analysis report
  [11] Master               → master.wav              → DONE

Usage:
    python make_apology_v9.py
    python make_apology_v9.py --skip-stems     # skip to mix if stems exist
    python make_apology_v9.py --start-from mix  # resume from mix step
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PYTHON = str(Path(sys.executable))
PROJECT = Path(__file__).resolve().parent

STEM_DIR = PROJECT / "output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9/stems"
OUT_DIR = PROJECT / "output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9"

STEMS = ["drums", "fx", "lead", "atmos", "midbass", "sub", "vocals", "legacy"]

# Build steps: each stem render is followed by its health check
_stem_steps = []
for s in STEMS:
    _stem_steps.append(
        (f"stem_{s}", f"Render {s.upper()} stem",
         [PYTHON, str(PROJECT / "_v9_stem_render.py"), "--stem", s]))
    _stem_steps.append(
        (f"health_{s}", f"Health check {s.upper()}",
         [PYTHON, str(PROJECT / "_v9_stem_health_check.py"), s]))

STEPS = [
    *_stem_steps,
    ("mix", "Mix all stems (Dojo mix pass + FX sends)",
     [PYTHON, str(PROJECT / "_v9_stem_mix.py")]),
    ("postprocess", "Post-processing audit (Subtronics benchmarks)",
     [PYTHON, str(PROJECT / "_v9_stem_postprocess.py")]),
    ("health_premaster", "Health check PRE-MASTER",
     [PYTHON, str(PROJECT / "_v9_stem_health_check.py"), "premaster"]),
    ("master", "Master (14-stage chain)",
     [PYTHON, str(PROJECT / "_v9_stem_master.py")]),
]


def run_step(name: str, description: str, cmd: list[str],
             step_num: int, total: int) -> bool:
    """Run a pipeline step as a subprocess. Returns True on success."""
    print(f"\n{'╔' + '═' * 62 + '╗'}", flush=True)
    print(f"║  [{step_num}/{total}] {description:55s} ║", flush=True)
    print(f"{'╚' + '═' * 62 + '╝'}", flush=True)

    t0 = time.time()
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT),
        timeout=1200,
        stdout=None,
        stderr=None,
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"\n  ✓ {name} COMPLETE ({elapsed:.0f}s)", flush=True)
        return True
    else:
        print(f"\n  ✗ {name} FAILED (exit code {result.returncode}, {elapsed:.0f}s)", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='TATNC V9 — Harmonized singing vocals pipeline')
    parser.add_argument("--skip-stems", action="store_true",
                        help="Skip stem rendering (use existing stems)")
    parser.add_argument("--start-from",
                        choices=["stems", "mix", "postprocess", "master"],
                        default="stems",
                        help="Resume from a specific phase")
    args = parser.parse_args()

    t0 = time.time()

    print("╔══════════════════════════════════════════════════════════════╗")
    print('║  DUBFORGE — "The Apology That Never Came.." V9             ║')
    print("║  Harmonized Singing | Double-Track | Per-Section Dynamics   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("  V9 Vocal Upgrades (vs V8):")
    print("    - Harmonized singing: 3rd harmony in chorus sections")
    print("    - Double-tracked lead vocal (±5 cent detune)")
    print("    - Per-section dynamics (verse→chorus→drop→outro)")
    print("    - Vocal bus +1dB (0.72→0.80 for singing clarity)")
    print("    - Mix EQ: 800-4kHz vocal focus (+2.5dB)")
    print("    - Air LP raised 10kHz→12kHz (vocal breathiness)")
    print("    - Master: LUFS -8.0, attack 3ms, side ×0.90")
    print()
    print("  V8 Foundation Retained:")
    print("    - RubberBand R3 --fine --formant (formant-preserving)")
    print("    - Edge TTS pitch param pre-tuned to target")
    print("    - Per-line pitch shift (no blind segmentation)")
    print("    - Correct anchor: ~200 Hz")
    print()
    print("  Pipeline:")
    print("    Phase 1: Render 8 stems (isolated subprocesses)")
    print("    Phase 2: Mix stems (FX sends + Ninja Focus + PSBS)")
    print("    Phase 3: Post-process (Subtronics benchmarks)")
    print("    Phase 4: Health check pre-master")
    print("    Phase 5: Master (14-stage chain)")
    print()

    skip_map = {
        "stems": 0,
        "mix": len(STEMS) * 2,
        "postprocess": len(STEMS) * 2 + 1,
        "master": len(STEMS) * 2 + 3,
    }
    start_idx = skip_map.get(args.start_from, 0)

    if args.skip_stems:
        start_idx = max(start_idx, len(STEMS) * 2)

    steps_to_run = STEPS[start_idx:]
    total = len(steps_to_run)

    if start_idx > 0:
        print(f"  Resuming from step {start_idx + 1} ({steps_to_run[0][0]})")
        print()

    STEM_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for i, (name, desc, cmd) in enumerate(steps_to_run):
        success = run_step(name, desc, cmd, start_idx + i + 1, start_idx + total)
        results[name] = success

        if not success:
            if name.startswith("health_") or name == "postprocess":
                print("  ⚠ Non-fatal step failed, continuing...")
                continue
            else:
                print(f"\n  ✗ Pipeline HALTED at {name}")
                break

    elapsed = time.time() - t0
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"\n{'═' * 64}")
    print(f'  "The Apology That Never Came.." V9 — PIPELINE SUMMARY')
    print(f"{'═' * 64}")

    for name, success in results.items():
        icon = "✓" if success else "✗"
        print(f"    [{icon}] {name}")

    print(f"\n  Steps: {passed} passed, {failed} failed")
    print(f"  Total time: {elapsed:.0f}s ({elapsed/60:.1f} min)")

    if failed == 0:
        master_path = OUT_DIR / "THE_APOLOGY_THAT_NEVER_CAME_V9_master.wav"
        if master_path.exists():
            print(f"\n  ✓ Master: {master_path}")

    print(f"\n  Stems ({STEM_DIR}):")
    for s in STEMS:
        p = STEM_DIR / f"{s}_stem.wav"
        if p.exists():
            size_mb = p.stat().st_size / 1024 / 1024
            print(f"    ✓ {s}_stem.wav ({size_mb:.1f} MB)")
        else:
            print(f"    ✗ {s}_stem.wav (missing)")

    print()
    print("  V9 = Harmonized Singing | Double-Track | Per-Section Dynamics")
    print()


if __name__ == "__main__":
    main()
