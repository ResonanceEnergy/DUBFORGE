#!/usr/bin/env python3
"""DUBFORGE STUDIO — Standalone Browser App (Mac Mini Optimized)

Complete start-to-finish production studio running in the browser.
Leverages all CPU cores for parallel DSP rendering.

Tabs:
    1. DASHBOARD   — System status, CPU cores, quick actions
    2. IDEA        — Song concept definition (SongDNA)
    3. FORGE       — Generate all outputs (parallel CPU rendering)
    4. RENDER      — Render stems + batch audio (parallel)
    5. PREVIEW     — Live audio preview of any engine module
    6. ARRANGEMENT — Energy curve visualization
    7. SAMPLES     — Sample library browser
    8. ANALYZE     — Audio file analysis
    9. MASTERING   — Master & export final track
   10. PIPELINE    — Architecture overview

Usage:
    python dubforge_studio.py                    # Default: localhost:7860
    python dubforge_studio.py --port 8000        # Custom port
    python dubforge_studio.py --share            # Public URL via Gradio
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import struct
import sys
import time
import traceback
import wave
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# ═══════════════════════════════════════════════════════════════════════════
# GRADIO
# ═══════════════════════════════════════════════════════════════════════════
try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Run: uv pip install gradio")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# DUBFORGE ENGINE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
from engine.als_generator import ALSProject, ALSScene, ALSTrack, write_als
from engine.arrangement_sequencer import (
    arrangement_duration_s,
    arrangement_energy_curve,
    arrangement_total_bars,
    build_arrangement,
    golden_section_check,
)
from engine.audio_preview import render_preview, preview_to_dict
from engine.batch_renderer import (
    ALL_BATCH_BANKS,
    export_batch_renders_parallel,
)
from engine.chord_progression import build_progression
from engine.config_loader import (
    A4_432,
    CPU_CORES,
    FIBONACCI,
    IS_APPLE_SILICON,
    PHI,
    WORKERS_COMPUTE,
    WORKERS_IO,
)
from engine.fxp_writer import FXPPreset, write_fxp
from engine.galatcia import catalog_galatcia
from engine.midi_export import NoteEvent, write_midi_file
from engine.mood_engine import MOODS, get_mood_suggestion, resolve_mood
from engine.rco import (
    generate_energy_curve,
    subtronics_emotive_preset,
    subtronics_hybrid_preset,
    subtronics_weapon_preset,
)
from engine.render_pipeline import (
    ALL_PIPELINE_BANKS,
    export_pipeline_stems_parallel,
)
from engine.sample_library import CATEGORIES as SAMPLE_CATEGORIES
from engine.sample_library import SampleLibrary
from engine.serum2 import build_dubstep_patches
from engine.variation_engine import (
    BPM_RANGES,
    NOTES,
    SCALE_INTERVALS,
    forge_song_dna,
    save_dna,
)

OUTPUT_ROOT = Path(__file__).parent / "output"

# Patch collection
_DUBSTEP_PATCHES: list[dict] = []
try:
    _DUBSTEP_PATCHES = build_dubstep_patches()
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# UI CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
STYLE_OPTIONS = list(BPM_RANGES.keys())
MOOD_OPTIONS = sorted(MOODS.keys())
SCALE_OPTIONS = sorted(SCALE_INTERVALS.keys())
KEY_OPTIONS = list(NOTES)
ARRANGEMENT_OPTIONS = ["weapon", "emotive", "hybrid", "fibonacci"]
ENERGY_PRESETS = ["weapon", "emotive", "hybrid"]
SERUM_PATCH_NAMES = [p.get("name", f"Patch {i}") for i, p in enumerate(_DUBSTEP_PATCHES)]

# Preview module list
PREVIEW_MODULES = [
    "sub_bass", "wobble_bass", "lead_synth", "pad_synth",
    "drum_generator", "perc_synth", "riser_synth", "impact_hit",
    "noise_generator", "arp_synth", "granular_synth", "pluck_synth",
    "drone_synth", "formant_synth", "glitch_engine", "riddim_engine",
    "vocal_chop", "fm_synth", "additive_synth", "supersaw",
]

# ═══════════════════════════════════════════════════════════════════════════
# WAV HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _signal_to_wav_bytes(signal: np.ndarray, sr: int = 44100) -> bytes:
    """Convert numpy signal to WAV bytes for browser playback."""
    buf = io.BytesIO()
    pcm = np.clip(signal, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    ch = 2 if pcm.ndim == 2 else 1
    with wave.open(buf, "w") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _wav_to_base64_html(wav_bytes: bytes) -> str:
    """Convert WAV bytes to HTML audio player."""
    b64 = base64.b64encode(wav_bytes).decode()
    return f'<audio controls src="data:audio/wav;base64,{b64}"></audio>'


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

def handle_sysinfo() -> str:
    """Return system information markdown."""
    import platform
    lines = [
        "## System Status",
        "",
        f"**Machine**: {platform.machine()}",
        f"**Python**: {platform.python_version()}",
        f"**Apple Silicon**: {'YES' if IS_APPLE_SILICON else 'No'}",
        f"**CPU Cores**: {CPU_CORES['total']} total "
        f"({CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E)",
        f"**Compute Workers**: {WORKERS_COMPUTE}",
        f"**I/O Workers**: {WORKERS_IO}",
        "",
    ]
    try:
        lines.append(f"**NumPy**: {np.__version__}")
        # Check BLAS
        config_info = np.__config__
        if hasattr(config_info, "show"):
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                np.show_config()
            cfg = buf.getvalue()
            if "accelerate" in cfg.lower():
                lines.append("**BLAS**: Apple Accelerate (native ARM NEON)")
            elif "openblas" in cfg.lower():
                lines.append("**BLAS**: OpenBLAS")
    except Exception:
        pass

    # Output directory stats
    output = Path("output")
    if output.exists():
        wav_count = len(list(output.rglob("*.wav")))
        fxp_count = len(list(output.rglob("*.fxp")))
        mid_count = len(list(output.rglob("*.mid")))
        als_count = len(list(output.rglob("*.als")))
        lines.extend([
            "",
            "### Output Directory",
            f"- WAV files: {wav_count}",
            f"- FXP presets: {fxp_count}",
            f"- MIDI files: {mid_count}",
            f"- ALS projects: {als_count}",
        ])
    else:
        lines.append("\n_No output directory yet. Run FORGE to generate._")

    return "\n".join(lines)


def handle_quick_build(module_name: str) -> str:
    """Run a single engine module and return status."""
    if not module_name:
        return "Select a module."
    try:
        import importlib
        t0 = time.perf_counter()
        mod = importlib.import_module(f"engine.{module_name}")
        mod.main()
        elapsed = (time.perf_counter() - t0) * 1000
        return f"**{module_name}** completed in {elapsed:.0f}ms"
    except Exception as e:
        return f"**{module_name}** failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — IDEA / SONGDNA
# ═══════════════════════════════════════════════════════════════════════════

def handle_mood_preview(mood_text: str, bpm: float) -> str:
    if not mood_text:
        return "Enter a mood to preview."
    try:
        resolved = resolve_mood(mood_text)
        suggestion = get_mood_suggestion(mood_text, bpm)
        lines = [
            f"**Resolved Mood**: {resolved}",
            f"**Suggested Key**: {suggestion.key} {suggestion.scale}",
            f"**Suggested BPM**: {suggestion.bpm:.0f}",
            f"**Energy**: {suggestion.energy:.2f}",
            f"**Darkness**: {suggestion.darkness:.2f}",
            f"**Reverb**: {suggestion.reverb:.2f}",
            f"**Distortion**: {suggestion.distortion:.2f}",
            f"**Tags**: {', '.join(suggestion.tags)}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — FORGE (Full Generation)
# ═══════════════════════════════════════════════════════════════════════════

def handle_forge(
    song_name: str,
    style: str,
    mood: str,
    key: str,
    scale: str,
    bpm: int,
    arrangement: str,
    tags_text: str,
    notes: str,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str, str]:
    """Full Phase 1 generation pipeline with parallel processing."""
    if not song_name.strip():
        return "**Error**: Song name is required.", "", ""

    t0 = time.perf_counter()
    progress(0.0, desc="Building SongBlueprint...")

    tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in song_name)
    safe_name = safe_name.strip().replace(" ", "_")

    clean_key = key if key and key != "(auto)" else ""
    clean_scale = scale if scale and scale != "(auto)" else ""
    clean_arr = arrangement if arrangement and arrangement != "(auto)" else ""

    progress(0.1, desc="Forging SongDNA...")
    try:
        dna = forge_song_dna(
            name=song_name.strip(), style=style or "dubstep",
            mood=mood or "", key=clean_key, scale=clean_scale,
            bpm=bpm or 0, arrangement=clean_arr, tags=tags, notes=notes or "",
        )
    except Exception as e:
        return f"**Error forging DNA**: {e}\n```\n{traceback.format_exc()}\n```", "", ""

    # Save DNA
    progress(0.2, desc="Saving SongDNA...")
    dna_dir = OUTPUT_ROOT / "dna"
    dna_dir.mkdir(parents=True, exist_ok=True)
    dna_path = dna_dir / f"{safe_name}_dna.json"
    try:
        save_dna(dna, str(dna_path))
    except Exception:
        dna_path.write_text(json.dumps(asdict(dna), indent=2, default=str), encoding="utf-8")

    generated_files: list[str] = []

    # FXP presets
    progress(0.3, desc=f"Generating Serum 2 presets ({WORKERS_COMPUTE} cores)...")
    preset_dir = OUTPUT_ROOT / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    for i, patch_dict in enumerate(_DUBSTEP_PATCHES):
        try:
            patch_name = patch_dict.get("name", f"patch_{i}").replace(" ", "_")
            fxp_path = preset_dir / f"{safe_name}_{patch_name}.fxp"
            preset = FXPPreset(plugin_id="XfsP", version=2, name=f"DF_{patch_name}"[:24], params=[])
            write_fxp(preset, str(fxp_path))
            generated_files.append(f"presets/{fxp_path.name}")
        except Exception:
            pass

    # MIDI
    progress(0.5, desc="Generating MIDI patterns...")
    midi_dir = OUTPUT_ROOT / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    midi_path = midi_dir / f"{safe_name}.mid"
    try:
        events: list[NoteEvent] = []
        actual_bpm = dna.bpm or bpm or 150
        root_midi = 36
        key_map = {n: (36 + i) for i, n in enumerate(NOTES)}
        if dna.key in key_map:
            root_midi = key_map[dna.key]
        for bar in range(min(16, dna.total_bars)):
            events.append(NoteEvent(pitch=root_midi, velocity=100, start_beat=bar * 4.0, duration_beats=2.0))
        write_midi_file([("Bass", events)], str(midi_path), bpm=actual_bpm)
        generated_files.append(f"midi/{midi_path.name}")
    except Exception:
        pass

    # ALS project
    progress(0.7, desc="Generating Ableton Live Set...")
    als_dir = OUTPUT_ROOT / "ableton"
    als_dir.mkdir(parents=True, exist_ok=True)
    als_path = als_dir / f"{safe_name}_SESSION.als"
    try:
        actual_bpm_val = float(dna.bpm or bpm or 150)
        tracks = [
            ALSTrack(name="SUB BASS", color=1), ALSTrack(name="MID BASS", color=2),
            ALSTrack(name="GROWL", color=3), ALSTrack(name="LEAD", color=4),
            ALSTrack(name="CHORDS", color=5), ALSTrack(name="PAD", color=6),
            ALSTrack(name="ARP", color=7), ALSTrack(name="FX", color=8),
            ALSTrack(name="DRUMS", color=9), ALSTrack(name="RISER", color=10),
        ]
        scenes = [ALSScene(name=s) for s in ["INTRO", "BUILD", "DROP 1", "BREAK", "BUILD 2", "DROP 2", "OUTRO"]]
        project = ALSProject(name=safe_name, bpm=actual_bpm_val, tracks=tracks, scenes=scenes)
        write_als(project, str(als_path))
        generated_files.append(f"ableton/{als_path.name}")
    except Exception:
        pass

    elapsed = time.perf_counter() - t0
    progress(1.0, desc=f"Done! ({elapsed:.1f}s)")

    status_lines = [
        f"## {song_name} — Generation Complete ({elapsed:.1f}s)",
        "", f"**Style**: {style or 'dubstep'} | **Mood**: {mood or 'auto'}",
        f"**Key**: {dna.key or key or 'auto'} | **BPM**: {dna.bpm or bpm or 'auto'}",
        f"**Workers Used**: {WORKERS_COMPUTE} P-cores",
        "", "### Generated Files",
    ]
    for f in generated_files:
        status_lines.append(f"- `output/{f}`")

    try:
        dna_display = json.dumps(asdict(dna), indent=2, default=str)[:5000]
    except Exception:
        dna_display = str(dna)[:5000]

    file_listing = "\n".join(f"output/{f}" for f in generated_files)
    return "\n".join(status_lines), dna_display, file_listing


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — PARALLEL RENDER
# ═══════════════════════════════════════════════════════════════════════════

def handle_parallel_render(
    render_type: str,
    workers: int,
    progress: gr.Progress = gr.Progress(),
) -> str:
    """Render audio using all CPU cores."""
    t0 = time.perf_counter()
    results: list[str] = []

    def _progress_cb(done, total, name):
        progress(done / total, desc=f"[{done}/{total}] {name}")

    try:
        if render_type == "Pipeline Stems":
            progress(0.0, desc="Rendering pipeline stems...")
            paths = export_pipeline_stems_parallel(
                workers=workers, progress_callback=_progress_cb,
            )
            results = paths
        elif render_type == "Batch Renders":
            progress(0.0, desc="Rendering batch presets...")
            paths = export_batch_renders_parallel(
                workers=workers, progress_callback=_progress_cb,
            )
            results = paths
        elif render_type == "Full Build (All Modules)":
            progress(0.0, desc="Running full parallel build...")
            from run_all import MODULE_REGISTRY, _run_module_standalone
            total = len(MODULE_REGISTRY)
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_run_module_standalone, name): (name, label)
                    for name, label in MODULE_REGISTRY
                }
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    name, label = futures[future]
                    progress(completed / total, desc=f"[{completed}/{total}] {label}")
                    try:
                        n, ms, err = future.result()
                        if err:
                            results.append(f"FAIL: {n} ({ms:.0f}ms) — {err}")
                        else:
                            results.append(f"OK: {n} ({ms:.0f}ms)")
                    except Exception as e:
                        results.append(f"FAIL: {name} — {e}")

        elapsed = time.perf_counter() - t0
        lines = [
            f"## Render Complete — {elapsed:.1f}s",
            f"**Type**: {render_type}",
            f"**Workers**: {workers} cores",
            f"**Files**: {len(results)}",
            f"**Throughput**: {len(results) / max(elapsed, 0.001):.1f} files/sec",
            "",
            "### Results",
        ]
        for r in results[:100]:
            lines.append(f"- `{r}`" if "/" in r else f"- {r}")
        if len(results) > 100:
            lines.append(f"_...and {len(results) - 100} more_")
        return "\n".join(lines)

    except Exception as e:
        return f"**Render Error**: {e}\n```\n{traceback.format_exc()}\n```"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — AUDIO PREVIEW
# ═══════════════════════════════════════════════════════════════════════════

def handle_preview(module_name: str, duration: float, freq: float) -> tuple[str, str | None]:
    """Preview a synth module — returns (info_md, wav_path)."""
    if not module_name:
        return "Select a module to preview.", None
    try:
        t0 = time.perf_counter()
        preview = render_preview(module_name, duration=duration, freq=freq)
        elapsed = (time.perf_counter() - t0) * 1000
        info = preview_to_dict(preview)

        # Write temp wav for Gradio audio component
        tmp_dir = OUTPUT_ROOT / "previews"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        wav_path = tmp_dir / f"preview_{module_name}.wav"

        # Decode base64 wav
        wav_bytes = base64.b64decode(info.get("wav_base64", ""))
        if wav_bytes:
            wav_path.write_bytes(wav_bytes)

        lines = [
            f"**Module**: {module_name}",
            f"**Duration**: {duration:.1f}s",
            f"**Frequency**: {freq:.0f} Hz",
            f"**Peak**: {info.get('peak_db', 0):.1f} dB",
            f"**RMS**: {info.get('rms_db', 0):.1f} dB",
            f"**Rendered in**: {elapsed:.0f}ms",
        ]
        return "\n".join(lines), str(wav_path) if wav_path.exists() else None
    except Exception as e:
        return f"Error: {e}", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — ARRANGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def handle_arrangement_preview(
    arr_type: str, bpm: float, key: str, rco_preset: str,
) -> tuple[str, Any]:
    if not arr_type:
        return "Select an arrangement type.", None
    try:
        template = build_arrangement(arr_type, bpm, key + "m")
        total_bars = arrangement_total_bars(template)
        duration = arrangement_duration_s(template)
        golden = golden_section_check(template)
        energy = arrangement_energy_curve(template)

        lines = [
            f"**Template**: {template.name}",
            f"**Bars**: {total_bars} | **Duration**: {duration:.1f}s ({duration / 60:.1f} min)",
            f"**Golden Bar**: {golden.get('golden_bar', '?')} | "
            f"**Peak**: {golden.get('peak_section', '?')} ({golden.get('peak_intensity', 0):.2f}) | "
            f"**Aligned**: {'YES' if golden.get('aligned') else 'No'}",
            "", "### Sections",
        ]
        for sec in template.sections:
            els = ", ".join(sec.elements[:5]) if sec.elements else ""
            lines.append(f"- **{sec.name}** | {sec.bars} bars | intensity {sec.intensity:.1f} | {els}")

        rco_fns = {"weapon": subtronics_weapon_preset, "emotive": subtronics_emotive_preset, "hybrid": subtronics_hybrid_preset}
        rco_fn = rco_fns.get(rco_preset, subtronics_weapon_preset)
        rco_profile = rco_fn(bpm)
        rco_data = generate_energy_curve(rco_profile, resolution_per_bar=4)

        lines.extend(["", f"### RCO: {rco_profile.name}",
            f"**Bars**: {rco_data.get('total_bars', '?')} | **Duration**: {rco_data.get('total_duration_s', 0):.1f}s"])

        fig = None
        if HAS_MPL:
            fig, ax = plt.subplots(figsize=(12, 5))
            fig.set_facecolor("#0a0a0a")
            ax.set_facecolor("#111111")
            fig.suptitle(f"{template.name} | {key}m | {bpm} BPM", color="#a855f7", fontsize=13, fontweight="bold")

            _cm = {"intro": "#4a9eff", "build": "#ffa500", "drop": "#ff2020", "break": "#20ff20",
                   "outro": "#888888", "verse": "#ff69b4", "interlude": "#20ffff",
                   "seed": "#ffd700", "grow": "#90ee90", "expand": "#ff4500", "transcend": "#da70d6"}

            for pt in energy:
                sb, eb = pt["start_bar"], pt["end_bar"]
                val = pt["intensity"]
                name = pt["section"]
                c = next((v for k, v in _cm.items() if k in name), "#ff6b35")
                ax.fill_between([sb, eb], 0, val, alpha=0.3, color=c, step="pre")
                ax.plot([sb, sb, eb], [0, val, val], color=c, linewidth=2)
                ax.text((sb + eb) / 2, val + 0.02, name, ha="center", va="bottom", fontsize=7, color=c, rotation=30)

            rco_times = rco_data.get("time_s", [])
            rco_energies = rco_data.get("energy", [])
            if rco_times and rco_energies:
                spb = (4 * 60) / bpm
                rco_bars = [t / spb for t in rco_times]
                ax.plot(rco_bars, rco_energies, color="#a855f7", linewidth=1.5, alpha=0.8, label=f"RCO: {rco_profile.name}")
                ax.legend(loc="upper right", fontsize=8, facecolor="#222", edgecolor="#555", labelcolor="white")

            gb = golden.get("golden_bar", 0)
            ax.axvline(x=gb, color="#ffd700", linestyle="--", linewidth=1.5, alpha=0.8)
            ax.text(gb + 0.5, 1.05, f"phi bar {gb}", color="#ffd700", fontsize=8)
            ax.set_xlim(0, total_bars)
            ax.set_ylim(0, 1.15)
            ax.set_ylabel("Energy", color="#ccc", fontsize=10)
            ax.set_xlabel("Bar", color="#ccc", fontsize=10)
            ax.tick_params(colors="#888")
            ax.grid(axis="x", color="#333", linewidth=0.5)
            fig.tight_layout()

        return "\n".join(lines), fig
    except Exception as e:
        return f"Error: {e}\n```\n{traceback.format_exc()}\n```", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — SAMPLE LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

def handle_sample_scan() -> str:
    lines = ["### Sample Library"]
    try:
        lib = SampleLibrary()
        summary = lib.summary()
        total = lib.total_count
        lines.append(f"**Total samples**: {total}")
        for cat, count in sorted(summary.items()):
            if count > 0:
                lines.append(f"- {cat}: {count}")
        if total == 0:
            lines.append("_No samples found. Run FORGE to generate._")
    except Exception as e:
        lines.append(f"Error: {e}")

    lines.append("\n### GALATCIA Collection")
    try:
        cat = catalog_galatcia()
        lines.extend([f"**Presets**: {len(cat.presets)}", f"**Samples**: {len(cat.samples)}",
                       f"**Wavetables**: {len(cat.wavetables)}", f"**Racks**: {len(cat.racks)}"])
    except Exception as e:
        lines.append(f"Error: {e}")
    return "\n".join(lines)


def handle_browse_category(category: str) -> str:
    if not category:
        return "Select a category."
    try:
        lib = SampleLibrary()
        samples = lib.list_category(category)
        if not samples:
            return f"No samples in **{category}**."
        lines = [f"### {category} — {len(samples)} samples", ""]
        for s in samples[:50]:
            parts = []
            if s.duration > 0:
                parts.append(f"{s.duration:.2f}s")
            if s.bpm > 0:
                parts.append(f"{s.bpm:.0f}bpm")
            if s.key:
                parts.append(s.key)
            info = f" | {' | '.join(parts)}" if parts else ""
            lines.append(f"- `{s.filename}`{info}")
        if len(samples) > 50:
            lines.append(f"\n_...and {len(samples) - 50} more_")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — ANALYZE
# ═══════════════════════════════════════════════════════════════════════════

def handle_analyze_wav(audio_file) -> tuple[str, Any]:
    """Analyze an uploaded audio file."""
    if audio_file is None:
        return "Upload a WAV file to analyze.", None
    try:
        from engine.web_preview import analyze_wav_bytes

        # Gradio supplies (sample_rate, np_array) tuple or file path
        if isinstance(audio_file, tuple):
            sr, data = audio_file
            wav_bytes = _signal_to_wav_bytes(data.astype(np.float64) / 32768.0 if data.dtype == np.int16 else data, sr)
        elif isinstance(audio_file, str):
            wav_bytes = Path(audio_file).read_bytes()
        else:
            wav_bytes = audio_file.read()

        result = analyze_wav_bytes(wav_bytes, "uploaded.wav")

        lines = [
            "## Analysis Results",
            f"**Duration**: {result.duration_s:.2f}s",
            f"**Peak**: {result.peak_amplitude:.4f} ({20 * np.log10(max(result.peak_amplitude, 1e-10)):.1f} dB)",
            f"**RMS**: {result.rms:.4f} ({20 * np.log10(max(result.rms, 1e-10)):.1f} dB)",
            f"**Spectral Centroid**: {result.spectral_centroid:.0f} Hz",
            f"**Crest Factor**: {result.crest_factor:.2f}",
            f"**Phi Ratio**: {result.phi_ratio:.6f}",
        ]

        fig = None
        if HAS_MPL:
            try:
                from engine.web_preview import generate_spectrogram_data
                spec_data = generate_spectrogram_data(wav_bytes)
                mag = spec_data.get("magnitude", [])
                if mag:
                    fig, ax = plt.subplots(figsize=(12, 4))
                    fig.set_facecolor("#0a0a0a")
                    ax.set_facecolor("#111111")
                    mag_arr = np.array(mag)
                    ax.imshow(mag_arr.T, aspect="auto", origin="lower", cmap="magma",
                              extent=[0, result.duration_s, 0, 24000])
                    ax.set_xlabel("Time (s)", color="#ccc")
                    ax.set_ylabel("Frequency (Hz)", color="#ccc")
                    ax.set_title("Spectrogram", color="#a855f7")
                    ax.tick_params(colors="#888")
                    fig.tight_layout()
            except Exception:
                pass

        return "\n".join(lines), fig
    except Exception as e:
        return f"Error analyzing: {e}", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — MASTERING
# ═══════════════════════════════════════════════════════════════════════════

def handle_master_track(
    audio_file,
    target_lufs: float,
    ceiling_db: float,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str | None]:
    """Apply mastering chain to uploaded audio."""
    if audio_file is None:
        return "Upload a WAV file to master.", None
    try:
        from engine.mastering_chain import master, MasterSettings, dubstep_master_settings

        progress(0.1, desc="Loading audio...")

        if isinstance(audio_file, tuple):
            sr, data = audio_file
            if data.dtype != np.float64:
                signal = data.astype(np.float64) / 32768.0 if data.dtype == np.int16 else data.astype(np.float64)
            else:
                signal = data
        elif isinstance(audio_file, str):
            import soundfile as sf
            signal, sr = sf.read(audio_file, dtype="float64")
        else:
            return "Unsupported audio format.", None

        progress(0.3, desc="Applying mastering chain...")
        settings = dubstep_master_settings()
        settings.target_lufs = target_lufs
        settings.ceiling_db = ceiling_db

        mastered = master(signal, settings)

        progress(0.8, desc="Writing master file...")
        master_dir = OUTPUT_ROOT / "masters"
        master_dir.mkdir(parents=True, exist_ok=True)
        master_path = master_dir / f"master_{int(time.time())}.wav"

        wav_bytes = _signal_to_wav_bytes(mastered, sr)
        master_path.write_bytes(wav_bytes)

        peak_db = 20 * np.log10(max(np.max(np.abs(mastered)), 1e-10))
        rms_db = 20 * np.log10(max(np.sqrt(np.mean(mastered ** 2)), 1e-10))

        progress(1.0, desc="Done!")
        lines = [
            "## Mastering Complete",
            f"**Target LUFS**: {target_lufs:.1f}",
            f"**Ceiling**: {ceiling_db:.1f} dB",
            f"**Peak**: {peak_db:.1f} dB",
            f"**RMS**: {rms_db:.1f} dB",
            f"**Output**: `{master_path}`",
        ]
        return "\n".join(lines), str(master_path)
    except Exception as e:
        return f"Error mastering: {e}\n```\n{traceback.format_exc()}\n```", None


# ═══════════════════════════════════════════════════════════════════════════
# GRADIO UI BUILD
# ═══════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
.dubforge-header {
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0a2e 50%, #0a0a0a 100%);
    border: 1px solid #6b21a8;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
    text-align: center;
}
.dubforge-header h1 { color: #a855f7 !important; font-size: 2em !important; margin: 0 !important; }
.dubforge-header p { color: #9ca3af !important; margin: 4px 0 0 0 !important; }
"""

# Quick-run module list for dashboard
QUICK_MODULES = [
    "phi_core", "rco", "psbs", "serum2", "midi_export", "drum_generator",
    "bass_oneshot", "lead_synth", "pad_synth", "mastering_chain",
    "arrangement_sequencer", "render_pipeline", "batch_renderer",
]


def build_ui() -> gr.Blocks:
    """Build the complete DUBFORGE Studio interface."""
    with gr.Blocks(
        title="DUBFORGE STUDIO",
    ) as app:
        gr.HTML(
            '<div class="dubforge-header">'
            '<h1>DUBFORGE STUDIO</h1>'
            '<p>Underground Industrial Bass Factory &mdash; '
            f'Mac Mini Optimized &mdash; {CPU_CORES["performance"]}P + {CPU_CORES["efficiency"]}E cores</p>'
            '</div>'
        )

        with gr.Tabs():
            # ─── TAB 1: DASHBOARD ────────────────────────────────────
            with gr.Tab("Dashboard", id="dashboard"):
                with gr.Row():
                    with gr.Column(scale=2):
                        sysinfo_md = gr.Markdown("_Click Refresh to load system info_")
                        refresh_btn = gr.Button("Refresh System Info", variant="secondary")
                    with gr.Column(scale=1):
                        gr.Markdown("### Quick Module Run")
                        quick_module = gr.Dropdown(choices=QUICK_MODULES, label="Module", info="Run a single engine module")
                        quick_run_btn = gr.Button("Run Module", variant="primary")
                        quick_result = gr.Markdown("")

                refresh_btn.click(fn=handle_sysinfo, outputs=[sysinfo_md])
                quick_run_btn.click(fn=handle_quick_build, inputs=[quick_module], outputs=[quick_result])

                # Auto-load on page
                app.load(fn=handle_sysinfo, outputs=[sysinfo_md])

            # ─── TAB 2: IDEA SANDBOX ─────────────────────────────────
            with gr.Tab("Idea", id="idea"):
                gr.Markdown("### Define Your Track\nSet core parameters — everything is derived via phi ratios and SongDNA.")
                with gr.Row():
                    with gr.Column(scale=2):
                        song_name = gr.Textbox(label="Song Name", placeholder="e.g. CYCLOPS FURY")
                        with gr.Row():
                            style = gr.Dropdown(choices=STYLE_OPTIONS, value="dubstep", label="Style")
                            mood = gr.Textbox(label="Mood", placeholder="dark, aggressive, euphoric")
                        with gr.Row():
                            key = gr.Dropdown(choices=["(auto)"] + KEY_OPTIONS, value="(auto)", label="Key")
                            scale_dd = gr.Dropdown(choices=["(auto)"] + SCALE_OPTIONS, value="(auto)", label="Scale")
                            bpm = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM")
                        with gr.Row():
                            arrangement = gr.Dropdown(choices=["(auto)"] + ARRANGEMENT_OPTIONS, value="(auto)", label="Arrangement")
                            tags_input = gr.Textbox(label="Tags", placeholder="heavy, festival")
                        artist_notes = gr.Textbox(label="Artist Notes", placeholder="Free-form ideas...", lines=3)
                    with gr.Column(scale=1):
                        gr.Markdown("### Mood Preview")
                        mood_preview = gr.Markdown("_Enter a mood_")
                        mood.change(fn=handle_mood_preview, inputs=[mood, bpm], outputs=[mood_preview])

            # ─── TAB 3: FORGE ─────────────────────────────────────────
            with gr.Tab("FORGE", id="forge"):
                gr.Markdown("### Generate Everything\nCreates SongDNA → FXP presets → MIDI → Ableton Live Set")
                forge_btn = gr.Button("FORGE IT", variant="primary", size="lg")
                forge_status = gr.Markdown("_Ready to forge_")
                with gr.Accordion("SongDNA (JSON)", open=False):
                    dna_output = gr.Code(label="SongDNA", language="json", lines=20)
                with gr.Accordion("Generated Files", open=False):
                    file_output = gr.Textbox(label="Files", lines=10, interactive=False)

                forge_btn.click(
                    fn=handle_forge,
                    inputs=[song_name, style, mood, key, scale_dd, bpm, arrangement, tags_input, artist_notes],
                    outputs=[forge_status, dna_output, file_output],
                )

            # ─── TAB 4: RENDER (CPU-PARALLEL) ────────────────────────
            with gr.Tab("Render", id="render"):
                gr.Markdown(
                    f"### Parallel CPU Rendering\n"
                    f"Leverage all **{CPU_CORES['performance']} performance cores** "
                    f"for batch audio rendering."
                )
                with gr.Row():
                    render_type = gr.Dropdown(
                        choices=["Pipeline Stems", "Batch Renders", "Full Build (All Modules)"],
                        value="Pipeline Stems",
                        label="Render Type",
                    )
                    worker_slider = gr.Slider(
                        minimum=1, maximum=CPU_CORES["total"],
                        step=1, value=WORKERS_COMPUTE,
                        label="Worker Cores",
                        info=f"Max {CPU_CORES['total']} ({CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E)",
                    )
                render_btn = gr.Button("Start Render", variant="primary", size="lg")
                render_result = gr.Markdown("_Select a render type and click Start_")

                render_btn.click(
                    fn=handle_parallel_render,
                    inputs=[render_type, worker_slider],
                    outputs=[render_result],
                )

            # ─── TAB 5: PREVIEW ──────────────────────────────────────
            with gr.Tab("Preview", id="preview"):
                gr.Markdown("### Audio Preview\nListen to any engine module in the browser.")
                with gr.Row():
                    preview_module = gr.Dropdown(choices=PREVIEW_MODULES, value="sub_bass", label="Module")
                    preview_dur = gr.Slider(minimum=0.1, maximum=5.0, step=0.1, value=1.0, label="Duration (s)")
                    preview_freq = gr.Slider(minimum=20, maximum=2000, step=1, value=100, label="Frequency (Hz)")
                preview_btn = gr.Button("Generate Preview", variant="primary")
                with gr.Row():
                    preview_info = gr.Markdown("")
                    preview_audio = gr.Audio(label="Preview", type="filepath")

                preview_btn.click(
                    fn=handle_preview,
                    inputs=[preview_module, preview_dur, preview_freq],
                    outputs=[preview_info, preview_audio],
                )

            # ─── TAB 6: ARRANGEMENT ──────────────────────────────────
            with gr.Tab("Arrangement", id="arrangement"):
                gr.Markdown("### Arrangement Blueprint\nEnergy curve + RCO dynamics + golden section analysis.")
                with gr.Row():
                    arr_type = gr.Dropdown(choices=ARRANGEMENT_OPTIONS, value="weapon", label="Template")
                    rco_preset = gr.Dropdown(choices=ENERGY_PRESETS, value="weapon", label="RCO Preset")
                with gr.Row():
                    arr_bpm = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM")
                    arr_key = gr.Dropdown(choices=KEY_OPTIONS, value="F", label="Key")
                arr_btn = gr.Button("Preview Arrangement", variant="primary")
                with gr.Row():
                    with gr.Column(scale=1):
                        arr_info = gr.Markdown("_Click Preview_")
                    with gr.Column(scale=2):
                        arr_plot = gr.Plot(label="Energy Curve")

                arr_btn.click(
                    fn=handle_arrangement_preview,
                    inputs=[arr_type, arr_bpm, arr_key, rco_preset],
                    outputs=[arr_info, arr_plot],
                )

            # ─── TAB 7: SAMPLES ──────────────────────────────────────
            with gr.Tab("Samples", id="samples"):
                gr.Markdown("### Sample Library\n26 categories of sounds.")
                scan_btn = gr.Button("Scan Library", variant="secondary")
                sample_info = gr.Markdown("_Click Scan_")
                scan_btn.click(fn=handle_sample_scan, outputs=[sample_info])

                gr.Markdown("---\n### Browse by Category")
                with gr.Row():
                    cat_dd = gr.Dropdown(choices=sorted(SAMPLE_CATEGORIES), label="Category")
                    browse_btn = gr.Button("Browse", variant="secondary")
                cat_output = gr.Markdown("")
                browse_btn.click(fn=handle_browse_category, inputs=[cat_dd], outputs=[cat_output])

            # ─── TAB 8: ANALYZE ──────────────────────────────────────
            with gr.Tab("Analyze", id="analyze"):
                gr.Markdown("### Audio Analysis\nUpload a WAV file for spectral analysis.")
                analyze_audio = gr.Audio(label="Upload Audio", type="filepath")
                analyze_btn = gr.Button("Analyze", variant="primary")
                analyze_result = gr.Markdown("")
                analyze_plot = gr.Plot(label="Spectrogram")

                analyze_btn.click(
                    fn=handle_analyze_wav,
                    inputs=[analyze_audio],
                    outputs=[analyze_result, analyze_plot],
                )

            # ─── TAB 9: MASTERING ────────────────────────────────────
            with gr.Tab("Master", id="master"):
                gr.Markdown("### Mastering Chain\nApply the DUBFORGE mastering chain to finish your track.")
                master_audio = gr.Audio(label="Upload Track", type="filepath")
                with gr.Row():
                    target_lufs = gr.Slider(minimum=-20, maximum=-4, step=0.5, value=-8.0, label="Target LUFS")
                    ceiling_db = gr.Slider(minimum=-3.0, maximum=0.0, step=0.1, value=-0.3, label="Ceiling (dB)")
                master_btn = gr.Button("Master It", variant="primary", size="lg")
                master_result = gr.Markdown("")
                master_output = gr.Audio(label="Mastered Output", type="filepath")

                master_btn.click(
                    fn=handle_master_track,
                    inputs=[master_audio, target_lufs, ceiling_db],
                    outputs=[master_result, master_output],
                )

            # ─── TAB 10: PIPELINE ────────────────────────────────────
            with gr.Tab("Pipeline", id="pipeline"):
                gr.Markdown(f"""### DUBFORGE 4-Phase Production Pipeline

```
INPUT: Song Idea (name, mood, key, BPM, style, energy)
         │
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 1: GENERATION — "The Idea Sandbox"           │
   │  Sound design + preset creation + MIDI export        │
   │  OUTPUT: Sound palette (FXP, WAV, ADG, MIDI)        │
   └─────┬───────────────────────────────────────────────┘
         │
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 2: ARRANGEMENT — "The Creation Session"      │
   │  Full song structure in Ableton Live                  │
   │  OUTPUT: Mix stems (24-bit WAV)                      │
   └─────┬───────────────────────────────────────────────┘
         │
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 3: MIXING — "The Mix Session"                │
   │  EQ, compression, spatial balance                    │
   │  OUTPUT: Mixed stems (24-bit WAV)                    │
   └─────┬───────────────────────────────────────────────┘
         │
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 4: MASTERING — "The Master Session"          │
   │  Multiband dynamics, limiting, LUFS normalization    │
   │  OUTPUT: Final WAV — DANCEFLOOR READY               │
   └─────────────────────────────────────────────────────┘
```

### System Architecture
- **Python**: 3.14 | **NumPy**: Accelerate BLAS (ARM NEON)
- **CPU**: {CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E cores
- **PHI** = {PHI:.10f}
- **A4** = {A4_432} Hz
- **Fibonacci** = {FIBONACCI[:13]}
""")

    return app


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Launch Standalone App
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="DUBFORGE Studio — Standalone Browser App")
    parser.add_argument("--port", type=int, default=7860, help="Server port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Create public URL")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    app = build_ui()

    print("=" * 60)
    print("  DUBFORGE STUDIO — Standalone Browser App")
    print(f"  CPU: {CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E cores")
    print(f"  Apple Silicon: {'YES' if IS_APPLE_SILICON else 'No'}")
    print(f"  Port: {args.port}")
    print("=" * 60)

    app.launch(
        server_port=args.port,
        share=args.share,
        inbrowser=not args.no_browser,
        theme=gr.themes.Base(primary_hue="purple", neutral_hue="gray"),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
