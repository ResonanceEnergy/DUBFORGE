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
    python3 run_all.py --parallel   # Run independent modules in parallel
    python3 run_all.py --workers 8  # Set parallel worker count
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).parent))

from engine.log import get_logger
from engine.memory import get_memory
from engine.config_loader import WORKERS_COMPUTE

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
    ("sidechain",         "Sidechain Engine"),
    ("riddim_engine",     "Riddim Engine"),
    ("pitch_automation",  "Pitch Automation"),
    ("lfo_matrix",        "LFO Modulation Matrix"),
    ("stereo_imager",     "Stereo Imager"),
    ("multiband_distortion", "Multiband Distortion"),
    ("arrangement_sequencer", "Arrangement Sequencer"),
    ("song_templates",    "Song Templates"),
    ("vocal_processor",  "Vocal Processor"),
    ("reverb_delay",     "Reverb & Delay"),
    ("convolution",      "Convolution Engine"),
    ("harmonic_analysis", "Harmonic Analysis"),
    ("render_pipeline",   "Render Pipeline"),
    ("batch_renderer",    "Batch Renderer"),
    ("stem_mixer",        "Stem Mixer"),
    ("sample_pack_builder", "Sample Pack Builder"),
    ("preset_pack_builder", "Preset Pack Builder"),
    ("wavetable_morph",   "Wavetable Morph Engine"),
    ("spectral_resynthesis", "Spectral Resynthesis"),
    ("phi_analyzer",       "Phi Coherence Analyzer"),
    ("evolution_engine",   "Evolution Engine"),
    ("preset_mutator",     "Preset Mutator"),
    ("ab_tester",          "A/B Tester"),
    ("template_generator", "Template Generator"),
    ("sound_palette",      "Sound Palette"),
    ("profiler",           "Performance Profiler"),
    ("error_handling",     "Error Handling & Validation"),
    ("plugin_scaffold",    "Plugin Scaffold"),
    ("web_preview",        "Web Preview Server"),
    ("tutorials",          "Tutorial Scripts"),
    ("realtime_monitor",   "Real-Time Monitor"),
    ("full_integration",   "v4.0 Full Integration"),
    ("final_audit",        "Final Audit"),
    ("grandmaster",        "GRANDMASTER 144"),
    ("subphonics",         "SUBPHONICS — Project Director"),

    # Phase 6 — SUBPHONICS Intelligence (Sessions 145-155)
    ("audio_preview",       "Audio Preview"),
    ("spectrogram_chat",    "Spectrogram Chat"),
    ("session_persistence", "Session Persistence"),
    ("chain_commands",      "Chain Commands"),
    ("param_control",       "Parameter Control"),
    ("render_queue",        "Render Queue"),
    ("preset_browser",      "Preset Browser"),
    ("mix_assistant",       "Mix Assistant"),
    ("genre_detector",      "Genre Detector"),
    ("mood_engine",         "Mood Engine"),

    # Phase 7 — Advanced Synthesis (Sessions 156-166)
    ("fm_synth",            "FM Synthesis"),
    ("additive_synth",      "Additive Synthesis"),
    ("supersaw",            "Supersaw Engine"),
    ("wave_folder",         "Wave Folder"),
    ("ring_mod",            "Ring Modulation"),
    ("phase_distortion",    "Phase Distortion"),
    ("vector_synth",        "Vector Synthesis"),
    ("vocoder",             "Vocoder"),
    ("beat_repeat",         "Beat Repeat"),
    ("auto_mixer",          "Auto Mixer"),
    ("reference_analyzer",  "Reference Analyzer"),

    # Phase 8 — Live Performance (Sessions 167-177)
    ("clip_launcher",       "Clip Launcher"),
    ("looper",              "Looper"),
    ("osc_controller",      "OSC Controller"),
    ("performance_recorder", "Performance Recorder"),
    ("markov_melody",       "Markov Melody"),
    ("genetic_evolver",     "Genetic Evolver"),
    ("pattern_recognizer",  "Pattern Recognizer"),
    ("tempo_sync",          "Tempo Sync"),
    ("midi_processor",      "MIDI Processor"),
    ("scene_system",        "Scene System"),
    ("live_fx",             "Live FX"),

    # Phase 9 — AI & Intelligence (Sessions 178-188)
    ("intelligent_eq",      "Intelligent EQ"),
    ("dynamics",            "Dynamics Processor"),
    ("spectral_morph",      "Spectral Morph"),
    ("auto_arranger",       "Auto Arranger"),
    ("stem_separator",      "Stem Separator"),
    ("project_manager",     "Project Manager"),
    ("watermark",           "Audio Watermark"),
    ("preset_vcs",          "Preset VCS"),
    ("karplus_strong",      "Karplus-Strong"),
    ("style_transfer",      "Style Transfer"),
    ("auto_master",         "Auto Master"),

    # Phase 10 — Production Toolkit (Sessions 189-210)
    ("metadata",            "Metadata Manager"),
    ("wav_pool",            "WAV Pool"),
    ("backup_system",       "Backup System"),
    ("sample_pack_exporter", "Sample Pack Exporter"),
    ("format_converter",    "Format Converter"),
    ("batch_processor",     "Batch Processor"),
    ("ep_builder",          "EP Builder"),
    ("collaboration",       "Collaboration Engine"),
    ("multitrack_renderer", "Multitrack Renderer"),
    ("audio_analyzer",      "Audio Analyzer"),
    ("tag_system",          "Tag System"),
    ("cue_points",          "Cue Points"),
    ("tuning_system",       "Tuning System"),
    ("envelope_generator",  "Envelope Generator"),
    ("macro_controller",    "Macro Controller"),
    ("signal_chain",        "Signal Chain"),
    ("randomizer",          "Randomizer"),
    ("snapshot_manager",    "Snapshot Manager"),
    ("automation_recorder", "Automation Recorder"),
    ("audio_buffer",        "Audio Buffer Pool"),
    ("key_detector",        "Key Detector"),
    ("audio_splitter",      "Audio Splitter"),

    # Phase 11 — Polish & Ascension (Sessions 211-233)
    ("crossfade",           "Crossfade Engine"),
    ("frequency_analyzer",  "Frequency Analyzer"),
    ("dither",              "Dither Engine"),
    ("normalizer",          "Audio Normalizer"),
    ("dc_remover",          "DC Remover"),
    ("tempo_detector",      "Tempo Detector"),
    ("audio_stitcher",      "Audio Stitcher"),
    ("bus_router",          "Bus Router"),
    ("harmonic_gen",        "Harmonic Generator"),
    ("panning",             "Panning Engine"),
    ("dynamics_processor",  "Dynamics Processor v2"),
    ("bounce",              "Bounce Engine"),
    ("clip_manager",        "Clip Manager"),
    ("spectral_gate",       "Spectral Gate"),
    ("saturation",          "Saturation Engine"),
    ("resonance",           "Resonance Engine"),
    ("groove",              "Groove Engine"),
    ("audio_math",          "Audio Math"),
    ("plugin_host",         "Plugin Host"),
    ("session_logger",      "Session Logger"),
    ("waveform_display",    "Waveform Display"),
    ("perf_monitor",        "Performance Monitor"),
    ("ascension",           "ASCENSION — Fibonacci 233"),
]

MODULE_NAMES = [m[0] for m in MODULE_REGISTRY]


def _import_and_run_module(name: str):
    """Dynamically import and run a module's main()."""
    import importlib
    mod = importlib.import_module(f"engine.{name}")
    mod.main()


def _run_module_standalone(name: str) -> tuple[str, float, str | None]:
    """Run a single module in a worker process. Returns (name, elapsed_ms, error)."""
    t0 = time.perf_counter()
    try:
        _import_and_run_module(name)
        return (name, (time.perf_counter() - t0) * 1000, None)
    except Exception as e:
        return (name, (time.perf_counter() - t0) * 1000, str(e))


def _default_workers() -> int:
    """Use detected performance core count from config_loader."""
    return WORKERS_COMPUTE


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
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run independent modules in parallel (uses ProcessPoolExecutor)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel workers (default: P-core count)",
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
    if args.parallel and not args.module:
        # Parallel mode — run independent modules across P-cores
        workers = args.workers or _default_workers()
        if not args.quiet:
            print(f"[PARALLEL] Running {total} modules across {workers} workers")
            print("=" * 60)
            print()

        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_module_standalone, mod_name): (mod_name, label)
                for mod_name, label in modules_to_run
            }
            completed = 0
            for future in as_completed(futures):
                mod_name, label = futures[future]
                completed += 1
                name, elapsed_ms, error = future.result()
                if error:
                    failures.append((name, error))
                    print(f"  [{completed}/{total}] ✗ {label} ({elapsed_ms:.0f}ms) — {error}")
                else:
                    print(f"  [{completed}/{total}] ✓ {label} ({elapsed_ms:.0f}ms)")
        print()
    else:
        # Sequential mode (original behavior)
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
