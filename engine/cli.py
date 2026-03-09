"""
DUBFORGE — CLI Tool  (Session 122)

Provides ``dubforge-cli`` entry point with sub-commands:

    dubforge-cli render   — run render pipeline / batch renderer
    dubforge-cli export   — export sample packs, presets, wavetables
    dubforge-cli analyze  — run harmonic analysis on .wav files
    dubforge-cli info     — show engine info & module count
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure engine is importable when invoked from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
# SUB-COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def cmd_render(args: argparse.Namespace) -> None:
    """Run render pipeline or batch renderer."""
    t0 = time.time()
    out = args.output

    if args.batch:
        from engine.batch_renderer import export_batch_renders
        paths = export_batch_renders(out)
        print(f"Batch render complete — {len(paths)} .wav files in {time.time()-t0:.1f}s")
    else:
        from engine.render_pipeline import export_pipeline_stems
        paths = export_pipeline_stems(out)
        print(f"Pipeline render complete — {len(paths)} .wav files in {time.time()-t0:.1f}s")


def cmd_export(args: argparse.Namespace) -> None:
    """Export sample packs, preset packs, or wavetable morphs."""
    t0 = time.time()
    out = args.output
    target = args.target

    if target == "samples":
        from engine.sample_pack_builder import export_all_packs
        paths = export_all_packs(out)
        print(f"Sample packs: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "presets":
        from engine.preset_pack_builder import export_all_preset_packs
        paths = export_all_preset_packs(out)
        print(f"Preset packs: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "wavetables":
        from engine.wavetable_morph import export_morph_wavetables
        paths = export_morph_wavetables(out)
        print(f"Wavetable morphs: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "resynth":
        from engine.spectral_resynthesis import export_resynth_wavetables
        paths = export_resynth_wavetables(out)
        print(f"Resynthesised wavetables: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "als":
        from engine.als_generator import export_all_als
        paths = export_all_als(out)
        print(f"Ableton sets: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "mix":
        from engine.stem_mixer import export_mix_demos
        paths = export_mix_demos(out)
        print(f"Mix demos: {len(paths)} files in {time.time()-t0:.1f}s")

    elif target == "all":
        from engine.als_generator import export_all_als
        from engine.preset_pack_builder import export_all_preset_packs
        from engine.sample_pack_builder import export_all_packs
        from engine.spectral_resynthesis import export_resynth_wavetables
        from engine.stem_mixer import export_mix_demos
        from engine.wavetable_morph import export_morph_wavetables

        total: list[str] = []
        total.extend(export_all_packs(out))
        total.extend(export_all_preset_packs(out))
        total.extend(export_morph_wavetables(out))
        total.extend(export_resynth_wavetables(out))
        total.extend(export_all_als(out))
        total.extend(export_mix_demos(out))
        print(f"All exports: {len(total)} files in {time.time()-t0:.1f}s")
    else:
        print(f"Unknown target: {target}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run harmonic analysis on a .wav file or directory."""
    import json

    from engine.harmonic_analysis import analyze_wav_file

    target = Path(args.path)
    analysis_type = args.type

    if target.is_file():
        wavs = [target]
    elif target.is_dir():
        wavs = sorted(target.rglob("*.wav"))[:50]
    else:
        print(f"Not found: {target}")
        return

    results: list[dict] = []
    for wf in wavs:
        try:
            r = analyze_wav_file(str(wf), analysis_type)
            results.append(r)
            print(f"  ✓ {wf.name} — {analysis_type}")
        except Exception as e:
            print(f"  ✗ {wf.name} — {e}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {out_path}")

    print(f"Analysed {len(results)}/{len(wavs)} files.")


def cmd_info(_args: argparse.Namespace) -> None:
    """Print engine information."""
    from engine.phi_core import FIBONACCI, PHI, SAMPLE_RATE

    # Count engine modules
    eng_dir = Path(__file__).parent
    modules = sorted(f.stem for f in eng_dir.glob("*.py") if not f.stem.startswith("_"))

    print("DUBFORGE — Planck × φ Fractal Basscraft Engine")
    print(f"  Modules:     {len(modules)}")
    print(f"  PHI:         {PHI}")
    print(f"  FIBONACCI:   {FIBONACCI[:8]}…")
    print(f"  Sample rate: {SAMPLE_RATE}")
    print()
    for m in modules:
        print(f"    {m}")


def cmd_subphonics(args: argparse.Namespace) -> None:
    """Launch the SUBPHONICS chatbot server."""
    from engine.subphonics_server import start_server
    port = args.port
    print(f"Launching SUBPHONICS on port {port}...")
    start_server(port=port)


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dubforge-cli",
        description="DUBFORGE CLI — render, export, analyse",
    )
    sub = parser.add_subparsers(dest="command")

    # --- render ---
    p_render = sub.add_parser("render", help="Run render pipeline / batch")
    p_render.add_argument("--batch", action="store_true", help="Use batch renderer")
    p_render.add_argument("--output", "-o", default="output", help="Output directory")

    # --- export ---
    p_export = sub.add_parser("export", help="Export packs / wavetables / ALS")
    p_export.add_argument(
        "target",
        choices=["samples", "presets", "wavetables", "resynth", "als", "mix", "all"],
        help="What to export",
    )
    p_export.add_argument("--output", "-o", default="output", help="Output directory")

    # --- analyze ---
    p_analyze = sub.add_parser("analyze", help="Harmonic analysis on .wav files")
    p_analyze.add_argument("path", help="Path to .wav file or directory")
    p_analyze.add_argument(
        "--type", "-t", default="spectral_peaks",
        choices=["spectral_peaks", "harmonic_series", "phi_detection",
                 "spectral_flux", "roughness"],
        help="Analysis type",
    )
    p_analyze.add_argument("--json-out", "-j", help="Write results to JSON file")

    # --- info ---
    sub.add_parser("info", help="Show engine info")

    # --- subphonics ---
    p_sub = sub.add_parser("subphonics", help="Launch SUBPHONICS chatbot server")
    p_sub.add_argument("--port", "-p", type=int, default=8433,
                       help="Server port (default: 8433)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    handlers = {
        "render": cmd_render,
        "export": cmd_export,
        "analyze": cmd_analyze,
        "info": cmd_info,
        "subphonics": cmd_subphonics,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
