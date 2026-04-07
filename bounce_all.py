#!/usr/bin/env python3
"""Bounce all 5 tracks to WAV using forge.py's render pipeline.

Reads each YAML config, builds SongDNA via VariationEngine, and
calls render_full_track() to produce listenable .wav files.

Usage:
    python bounce_all.py
"""

import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

import yaml

from engine.variation_engine import SongBlueprint, VariationEngine
from forge import render_full_track

CONFIGS = [
    "configs/track_cyclops_fury.yaml",
    "configs/track_void_walker.yaml",
    "configs/track_fractal_descent.yaml",
    "configs/track_golden_membrane.yaml",
    "configs/track_tesseract_ritual.yaml",
]


def parse_key_scale(key_str: str) -> tuple[str, str]:
    """Parse 'E_minor' → ('E', 'minor'), 'F#_phrygian' → ('F#', 'phrygian')."""
    parts = key_str.split("_", 1)
    key = parts[0]
    scale = parts[1] if len(parts) > 1 else "minor"
    return key, scale


def bounce_track(config_path: str) -> str | None:
    """Load YAML config and render to WAV. Returns output path or None."""
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        print(f"  SKIP: {config_path} not found")
        return None

    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    g = cfg.get("global", {})
    name = cfg.get("template_name", cfg_path.stem)
    bpm = g.get("bpm", 140)
    key_raw = g.get("key", "F_minor")
    key, scale = parse_key_scale(key_raw)

    # Infer mood from the YAML comment or name
    name_lower = name.lower()
    if any(w in name_lower for w in ("fury", "rage", "ritual")):
        mood = "aggressive"
    elif any(w in name_lower for w in ("void", "descent")):
        mood = "dark"
    elif any(w in name_lower for w in ("golden", "membrane")):
        mood = "ethereal"
    else:
        mood = "dark"

    display_name = name.replace("_", " ").title()

    print(f"\n{'=' * 60}")
    print(f"  BOUNCING: {display_name}")
    print(f"  Key: {key} {scale} | BPM: {bpm} | Mood: {mood}")
    print(f"{'=' * 60}")

    bp = SongBlueprint(
        name=display_name,
        style="dubstep",
        mood=mood,
        key=key,
        scale=scale,
        bpm=bpm,
    )

    engine = VariationEngine(artistic_variance=0.15)
    dna = engine.forge_dna(bp)

    print(dna.summary())
    out_path = render_full_track(dna=dna)
    return out_path


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║  DUBFORGE — BATCH BOUNCE (5 Tracks)         ║")
    print("╚══════════════════════════════════════════════╝")

    results = []
    for cfg in CONFIGS:
        try:
            path = bounce_track(cfg)
            if path:
                results.append(path)
        except Exception as e:
            print(f"\n  ERROR bouncing {cfg}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"  BOUNCE COMPLETE — {len(results)}/{len(CONFIGS)} tracks rendered")
    print(f"{'=' * 60}")
    for p in results:
        size_mb = os.path.getsize(p) / 1024 / 1024
        print(f"  {p}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
