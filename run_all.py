"""
DUBFORGE — Run All Engines

Master script to generate all wavetables, analysis, and configs.
Integrated with DUBFORGE Memory System for long-term persistence.

Usage:
    python3 run_all.py              # Run all modules
    python3 run_all.py --module rco # Run a single module
    python3 run_all.py --list       # List available modules
    python3 run_all.py --no-memory  # Skip memory tracking
    python3 run_all.py --quiet      # Suppress per-module output
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).parent))

from engine.log import get_logger
from engine.memory import get_memory

_log = get_logger("dubforge.build")


def _run_module(mem, step_label: str, module_name: str, import_and_run, failures: list):
    """Run an engine module with memory tracking. Appends to failures on error."""
    print(f"{step_label}")
    print("-" * 40)
    t0 = time.time()
    try:
        import_and_run()
        elapsed_ms = (time.time() - t0) * 1000
        mem.log_event(
            module=module_name,
            action="build",
            params={"step": step_label},
            result_summary=f"{module_name} build completed",
            duration_ms=elapsed_ms,
        )
        return True
    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        mem.log_event(
            module=module_name,
            action="build_error",
            params={"step": step_label, "error": str(e)},
            result_summary=f"ERROR: {e}",
            duration_ms=elapsed_ms,
        )
        failures.append((module_name, str(e)))
        print(f"  ⚠ {module_name} error: {e}")
        return False
    finally:
        print()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE REGISTRY — maps name → (import_path, label)
# ═══════════════════════════════════════════════════════════════════════════

MODULE_REGISTRY: list[tuple[str, str]] = [
    ("phi_core",          "PHI CORE Wavetable Generator"),
    ("rco",               "Rollercoaster Optimizer (RCO)"),
    ("psbs",              "Phase-Separated Bass System (PSBS)"),
    ("sb_analyzer",       "Subtronics Analyzer"),
    ("trance_arp",        "Trance Arp Engine"),
    ("chord_progression", "Chord Progression Engine"),
    ("ableton_live",      "Ableton Live Engine"),
    ("serum2",            "Serum 2 Engine"),
    ("dojo",              "Producer Dojo Engine"),
    ("growl_resampler",   "Mid-Bass Growl Resampler"),
    ("midi_export",       "MIDI File Export Engine"),
    ("drum_generator",    "Drum & Percussion Generator"),
    ("sample_slicer",     "Sample Slicer"),
    ("mastering_chain",   "Mastering Chain"),
    ("als_generator",     "Ableton Live Set (.als) Generator"),
    ("fxp_writer",        "FXP / VST2 Preset Writer"),
    ("vocal_chop",        "Vocal Chop Synthesizer"),
    ("fx_generator",      "FX Generator (Risers/Impacts/Sub Drops)"),
    ("bass_oneshot",      "Bass One-Shot Generator"),
    ("transition_fx",     "Transition FX Generator"),
    ("pad_synth",         "Pad & Atmosphere Synthesizer"),
    ("lead_synth",        "Lead Sound Synthesizer"),
    ("perc_synth",        "Percussion One-Shot Synthesizer"),
    ("ambient_texture",   "Ambient Texture Generator"),
    ("sub_bass",          "Sub-Bass One-Shot Generator"),
    ("noise_generator",   "Noise Texture Generator"),
    ("arp_synth",         "Arp Synth Pattern Generator"),
    ("pluck_synth",       "Pluck One-Shot Synthesizer"),
    ("granular_synth",    "Granular Synthesizer"),
    ("chord_pad",         "Chord Pad Synthesizer"),
    ("riser_synth",       "Riser Synthesizer"),
    ("impact_hit",        "Impact Hit Synthesizer"),
    ("wobble_bass",       "Wobble Bass Synthesizer"),
    ("formant_synth",     "Formant Synthesizer"),
    ("glitch_engine",     "Glitch Engine"),
    ("drone_synth",       "Drone Synthesizer"),
]

MODULE_NAMES = [m[0] for m in MODULE_REGISTRY]


def _import_and_run_module(name: str):
    """Dynamically import and run a module's main()."""
    import importlib
    mod = importlib.import_module(f"engine.{name}")
    mod.main()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dubforge",
        description="DUBFORGE — Planck x phi Fractal Basscraft Engine",
    )
    parser.add_argument(
        "--module", "-m",
        choices=MODULE_NAMES,
        help="Run a single engine module instead of all",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        dest="list_modules",
        help="List available modules and exit",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Skip memory tracking",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress build banner (modules still print their own output)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    # --- --list mode ---
    if args.list_modules:
        print("Available DUBFORGE modules:")
        for name, label in MODULE_REGISTRY:
            print(f"  {name:<22s} {label}")
        sys.exit(0)

    # --- Banner ---
    if not args.quiet:
        use_memory = not args.no_memory
        print("=" * 60)
        print("  DUBFORGE — Full Engine Build")
        print("  Doctrine: Planck x phi Fractal Basscraft v1.0")
        print(f"  Memory:   {'ACTIVE' if use_memory else 'DISABLED'}")
        print("=" * 60)
        print()

    # --- Determine which modules to run ---
    if args.module:
        modules_to_run = [(n, lbl) for n, lbl in MODULE_REGISTRY if n == args.module]
    else:
        modules_to_run = list(MODULE_REGISTRY)

    total = len(modules_to_run)

    # --- Memory init ---
    mem = None
    if not args.no_memory:
        mem = get_memory()
        note = f"{'Single module: ' + args.module if args.module else 'Full engine build'} via run_all.py"
        mem.begin_session(notes=note)

        # Show top recalled assets from previous sessions
        if not args.quiet:
            try:
                top = mem.recall(limit=5)
                if top:
                    print("[MEMORY] Top recalled assets:")
                    for asset in top:
                        name = asset.get("filename", asset.get("asset_type", "?"))
                        score = asset.get("recall_score", 0)
                        print(f"  • {name}  (score {score:.3f})")
                    print()
            except Exception as exc:
                _log.warning("Recall failed: %s", exc)
            print()

    failures: list[tuple[str, str]] = []

    # --- Run modules ---
    for idx, (mod_name, label) in enumerate(modules_to_run, 1):
        step_label = f"[{idx}/{total}] {label}"

        def runner(_n=mod_name):
            return _import_and_run_module(_n)

        if mem:
            _run_module(mem, step_label, mod_name, runner, failures)
        else:
            # No memory — run directly with basic error handling
            print(f"{step_label}")
            print("-" * 40)
            try:
                runner()
            except Exception as e:
                failures.append((mod_name, str(e)))
                print(f"  ⚠ {mod_name} error: {e}")
            print()

    # --- Auto-register generated output assets ---
    if mem:
        print("[MEMORY] Scanning output assets...")
        print("-" * 40)
        output_root = Path("output")
        asset_type_map = {
            "wavetables": "wavetable",
            "analysis": "analysis",
            "serum2": "preset",
            "ableton": "arrangement",
            "dojo": "methodology",
            "memory": None,
        }
        registered = 0
        for subdir, asset_type in asset_type_map.items():
            if asset_type is None:
                continue
            scan_dir = output_root / subdir
            if scan_dir.exists():
                for f in scan_dir.iterdir():
                    if f.is_file() and not f.name.startswith("."):
                        mem.register_asset(
                            asset_type=asset_type,
                            filename=str(f),
                            module=subdir,
                            params={"auto_registered": True},
                            tags=[subdir, asset_type],
                        )
                        registered += 1
        print(f"  Registered {registered} output assets")
        print()

        # Evolution summary + end session
        if not args.quiet:
            try:
                evo = mem.get_evolution_summary()
                if evo:
                    print("[MEMORY] Evolution summary:")
                    for key, val in evo.items():
                        print(f"  {key}: {val}")
                    print()
            except Exception as exc:
                _log.warning("Evolution summary failed: %s", exc)
        mem.end_session(notes="Build complete")
        print()

        # Print memory status
        mem.print_status()

    # --- Build result ---
    if failures:
        print("=" * 60)
        print(f"  BUILD FINISHED WITH {len(failures)} ERROR(S)")
        print("=" * 60)
        for mod, err in failures:
            print(f"  ✗ {mod}: {err}")
        print()
    else:
        print("=" * 60)
        print("  BUILD COMPLETE — ALL ENGINES" + (" + MEMORY" if mem else ""))
        print("=" * 60)

    if not args.quiet:
        print()
        print("Outputs:")
        print("  output/wavetables/   — Serum-ready .wav + vocal chops + FX")
        print("  output/analysis/     — JSON data + PNG charts + manifests")
        print("  output/midi/         — MIDI drum patterns + vocal triggers")
        print("  output/serum2/       — Serum 2 architecture + patches")
        print("  output/ableton/      — Ableton Live templates")
        print("  output/dojo/         — Producer Dojo methodology")
        print("  output/memory/       — Long-term memory persistence")
        print("  configs/             — YAML module packs + blueprints")
        print()

    sys.exit(len(failures))


if __name__ == '__main__':
    main()
