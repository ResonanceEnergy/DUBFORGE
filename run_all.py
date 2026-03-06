"""
DUBFORGE — Run All Engines

Master script to generate all wavetables, analysis, and configs.
"""

from pathlib import Path
import sys

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("=" * 60)
    print("  DUBFORGE — Full Engine Build")
    print("  Doctrine: Planck x phi Fractal Basscraft v1.0")
    print("=" * 60)
    print()

    # 1. PHI CORE wavetables
    print("[1/5] PHI CORE Wavetable Generator")
    print("-" * 40)
    from engine.phi_core import main as phi_main
    phi_main()
    print()

    # 2. Rollercoaster Optimizer
    print("[2/5] Rollercoaster Optimizer (RCO)")
    print("-" * 40)
    from engine.rco import main as rco_main
    rco_main()
    print()

    # 3. Phase-Separated Bass System
    print("[3/5] Phase-Separated Bass System (PSBS)")
    print("-" * 40)
    from engine.psbs import main as psbs_main
    psbs_main()
    print()

    # 4. Subtronics Analyzer
    print("[4/5] Subtronics Analyzer")
    print("-" * 40)
    from engine.sb_analyzer import main as sb_main
    sb_main()
    print()

    # 5. Trance Arp Engine
    print("[5/7] Trance Arp Engine")
    print("-" * 40)
    from engine.trance_arp import main as arp_main
    arp_main()
    print()

    # 6. Chord Progression Engine
    print("[6/7] Chord Progression Engine")
    print("-" * 40)
    from engine.chord_progression import main as chord_main
    chord_main()
    print()

    # 7. Ableton Live Engine
    print("[7/7] Ableton Live Engine")
    print("-" * 40)
    from engine.ableton_live import main as ableton_main
    ableton_main()
    print()

    # 8. Growl Resampler (optional — takes longer)
    print("[BONUS] Mid-Bass Growl Resampler")
    print("-" * 40)
    from engine.growl_resampler import main as growl_main
    growl_main()
    print()

    print("=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    print()
    print("Outputs:")
    print("  output/wavetables/   — Serum-ready .wav files")
    print("  output/analysis/     — JSON data + PNG charts")
    print("  configs/             — YAML module packs + blueprints")
    print()


if __name__ == '__main__':
    main()
