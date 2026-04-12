#!/usr/bin/env python3
"""DUBFORGE Launchpad — Production Setup Wizard.

Interactive web UI for the DUBFORGE 4-phase production pipeline.
Walks through Phase 1 (Generation) as an idea sandbox, then launches
Phase 2 (Arrangement) by generating all outputs.

Usage:
    python dubforge_launchpad.py
    python dubforge_launchpad.py --port 7870 --share
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from dataclasses import asdict
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
    print("Gradio not installed. Run: pip install gradio")
    sys.exit(1)

try:
    import matplotlib  # type: ignore[import-not-found]
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

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
from engine.chord_progression import build_progression
from engine.config_loader import A4_432, FIBONACCI, PHI
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

# Build patch collection once at import time
_DUBSTEP_PATCHES: list[dict] = []
try:
    _DUBSTEP_PATCHES = build_dubstep_patches()
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS FOR UI DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════════
STYLE_OPTIONS = list(BPM_RANGES.keys())
MOOD_OPTIONS = sorted(MOODS.keys())
SCALE_OPTIONS = sorted(SCALE_INTERVALS.keys())
KEY_OPTIONS = list(NOTES)
ARRANGEMENT_OPTIONS = ["weapon", "emotive", "hybrid", "fibonacci"]
ENERGY_PRESETS = ["weapon", "emotive", "hybrid"]
SERUM_PATCH_NAMES = [p.get("name", f"Patch {i}") for i, p in enumerate(_DUBSTEP_PATCHES)]


# ═══════════════════════════════════════════════════════════════════════════
# BACKEND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def handle_mood_preview(mood_text: str, bpm: float) -> str:
    """Resolve mood and return suggestion preview."""
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
            f"**Base Frequency**: {suggestion.base_freq:.1f} Hz",
            f"**Reverb**: {suggestion.reverb:.2f}",
            f"**Distortion**: {suggestion.distortion:.2f}",
            f"**Tags**: {', '.join(suggestion.tags)}",
            f"**Modules**: {', '.join(suggestion.modules[:8])}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_arrangement_preview(
    arr_type: str, bpm: float, key: str, rco_preset: str
) -> tuple[str, Any]:
    """Build arrangement preview with energy curve plot."""
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
            f"**Bars**: {total_bars}  |  **Duration**: {duration:.1f}s "
            f"({duration / 60:.1f} min)",
            f"**Golden Bar**: {golden.get('golden_bar', '?')}  |  "
            f"**Peak**: {golden.get('peak_section', '?')} "
            f"({golden.get('peak_intensity', 0):.2f})  |  "
            f"**Aligned**: {'YES' if golden.get('aligned') else 'No'}",
            "",
            "### Sections",
        ]
        for sec in template.sections:
            els = ", ".join(sec.elements[:5]) if sec.elements else ""
            lines.append(
                f"- **{sec.name}** | {sec.bars} bars | "
                f"intensity {sec.intensity:.1f} | {els}"
            )

        # RCO energy data
        rco_fns = {
            "weapon": subtronics_weapon_preset,
            "emotive": subtronics_emotive_preset,
            "hybrid": subtronics_hybrid_preset,
        }
        rco_fn = rco_fns.get(rco_preset, subtronics_weapon_preset)
        rco_profile = rco_fn(bpm)
        rco_data = generate_energy_curve(rco_profile, resolution_per_bar=4)

        lines.extend([
            "",
            f"### RCO: {rco_profile.name}",
            f"**Bars**: {rco_data.get('total_bars', '?')}  |  "
            f"**Duration**: {rco_data.get('total_duration_s', 0):.1f}s",
        ])

        # Chord progression info
        try:
            progression = build_progression(
                name=f"{template.name}_preview",
                key=key,
                scale_type="minor",
                roman_sequence=["i", "VI", "III", "VII"],
                bpm=int(bpm),
            )
            chords = progression.chords[: min(8, len(template.sections))]
            if chords:
                chord_str = " -> ".join(chord["symbol"] for chord in chords)
                lines.extend(["", f"### Chords ({key}m)", chord_str])
        except Exception:
            pass

        # Build matplotlib plot
        fig = None
        if HAS_MPL:
            fig, ax = plt.subplots(figsize=(12, 5))
            fig.set_facecolor("#0a0a0a")
            ax.set_facecolor("#111111")
            fig.suptitle(
                f"{template.name}  |  {key}m  |  {bpm} BPM",
                color="#a855f7", fontsize=13, fontweight="bold",
            )

            # Section color map
            _cm = {
                "intro": "#4a9eff", "build": "#ffa500", "drop": "#ff2020",
                "break": "#20ff20", "outro": "#888888", "verse": "#ff69b4",
                "interlude": "#20ffff", "seed": "#ffd700", "grow": "#90ee90",
                "expand": "#ff4500", "transcend": "#da70d6",
            }

            # Section energy regions
            for pt in energy:
                sb, eb = pt["start_bar"], pt["end_bar"]
                val = pt["intensity"]
                name = pt["section"]
                c = next((v for k, v in _cm.items() if k in name), "#ff6b35")
                ax.fill_between([sb, eb], 0, val, alpha=0.3, color=c, step="pre")
                ax.plot([sb, sb, eb], [0, val, val], color=c, linewidth=2)
                ax.text(
                    (sb + eb) / 2, val + 0.02, name,
                    ha="center", va="bottom", fontsize=7, color=c, rotation=30,
                )

            # RCO smooth energy overlay
            rco_times = rco_data.get("time_s", [])
            rco_energies = rco_data.get("energy", [])
            if rco_times and rco_energies:
                spb = (4 * 60) / bpm
                rco_bars = [t / spb for t in rco_times]
                ax.plot(
                    rco_bars, rco_energies, color="#a855f7", linewidth=1.5,
                    alpha=0.8, label=f"RCO: {rco_profile.name}",
                )
                ax.legend(
                    loc="upper right", fontsize=8,
                    facecolor="#222", edgecolor="#555", labelcolor="white",
                )

            # Golden section line
            gb = golden.get("golden_bar", 0)
            ax.axvline(
                x=gb, color="#ffd700", linestyle="--", linewidth=1.5, alpha=0.8,
            )
            ax.text(gb + 0.5, 1.05, f"phi bar {gb}", color="#ffd700", fontsize=8)

            ax.set_xlim(0, total_bars)
            ax.set_ylim(0, 1.15)
            ax.set_ylabel("Energy", color="#ccc", fontsize=10)
            ax.set_xlabel("Bar", color="#ccc", fontsize=10)
            ax.tick_params(colors="#888")
            ax.grid(axis="x", color="#333", linewidth=0.5)
            fig.tight_layout()

        # Fallback text chart if no matplotlib
        if fig is None:
            curve_lines = ["### Energy Curve"]
            for pt in energy:
                bar = int(pt.get("start_bar", 0))
                val = pt.get("intensity", 0)
                bar_chart = "X" * int(val * 30)
                curve_lines.append(
                    f"Bar {bar:3d} | {bar_chart} {val:.2f} | "
                    f"{pt.get('section', '')}"
                )
            return "\n".join(lines + [""] + curve_lines), None

        return "\n".join(lines), fig
    except Exception as e:
        return f"Error: {e}\n```\n{traceback.format_exc()}\n```", None


def handle_sample_scan() -> str:
    """Scan sample library and GALATCIA, return summary."""
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
            lines.append(
                "_No samples found. Run `python forge.py` to generate, "
                "or use the Download Starter Pack button._"
            )
    except Exception as e:
        lines.append(f"Error scanning library: {e}")

    lines.append("")
    lines.append("### GALATCIA Collection")
    try:
        cat = catalog_galatcia()
        lines.append(f"**Presets**: {len(cat.presets)}")
        lines.append(f"**Samples**: {len(cat.samples)}")
        lines.append(f"**Wavetables**: {len(cat.wavetables)}")
        lines.append(f"**Racks**: {len(cat.racks)}")
        if cat.presets:
            by_cat: dict[str, int] = {}
            for p in cat.presets:
                by_cat[p.category] = by_cat.get(p.category, 0) + 1
            for c, n in sorted(by_cat.items()):
                lines.append(f"  - {c}: {n} presets")
        if cat.samples:
            by_cat2: dict[str, int] = {}
            for s in cat.samples:
                by_cat2[s.category] = by_cat2.get(s.category, 0) + 1
            for c, n in sorted(by_cat2.items()):
                lines.append(f"  - {c}: {n} samples")
    except Exception as e:
        lines.append(f"Error scanning GALATCIA: {e}")

    return "\n".join(lines)


def handle_download_starter_pack() -> str:
    """Download CC0 starter sample pack."""
    try:
        lib = SampleLibrary()
        result = lib.download_starter_pack()
        if isinstance(result, dict):
            total = sum(result.values()) if result else 0
            return f"Downloaded {total} samples to {lib.sample_dir}\n{result}"
        return f"Downloaded samples to {lib.sample_dir}"
    except Exception as e:
        return f"Error: {e}"


def handle_browse_category(category: str) -> str:
    """Browse samples in a specific category with metadata."""
    if not category:
        return "Select a category."
    try:
        lib = SampleLibrary()
        samples = lib.list_category(category)
        if not samples:
            return (
                f"No samples in **{category}**. "
                "Download a starter pack or import from a directory."
            )
        lines = [f"### {category} -- {len(samples)} samples", ""]
        for s in samples[:50]:
            parts = []
            if s.duration > 0:
                parts.append(f"{s.duration:.2f}s")
            if s.sample_rate and s.sample_rate != 44100:
                parts.append(f"{s.sample_rate}Hz")
            if s.bpm > 0:
                parts.append(f"{s.bpm:.0f}bpm")
            if s.key:
                parts.append(s.key)
            if s.tags:
                parts.append(", ".join(s.tags[:3]))
            info = f" | {' | '.join(parts)}" if parts else ""
            lines.append(f"- `{s.filename}`{info}")
            if s.path:
                lines.append(f"  Path: `{s.path}`")
        if len(samples) > 50:
            lines.append(f"\n*...and {len(samples) - 50} more*")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_search_samples(query: str) -> str:
    """Search samples by name, description, or tags."""
    if not query.strip():
        return "Enter a search query."
    try:
        lib = SampleLibrary()
        results = lib.search(query.strip())
        if not results:
            return f"No samples matching **'{query}'**."
        lines = [f"### Search: '{query}' -- {len(results)} results", ""]
        for s in results[:30]:
            lines.append(f"- `{s.filename}` ({s.category})")
            if s.path:
                lines.append(f"  Path: `{s.path}`")
        if len(results) > 30:
            lines.append(f"\n*...and {len(results) - 30} more*")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_browse_galatcia() -> str:
    """Browse GALATCIA presets and samples by category."""
    try:
        cat = catalog_galatcia()
        lines = [
            "### GALATCIA Collection",
            f"**Root**: `{cat.root}`",
            "",
        ]
        if cat.presets:
            lines.append(f"### Presets ({len(cat.presets)})")
            by_cat: dict[str, list] = {}
            for p in cat.presets:
                by_cat.setdefault(p.category, []).append(p)
            for c in sorted(by_cat):
                lines.append(f"\n**{c}** ({len(by_cat[c])})")
                for p in by_cat[c][:10]:
                    lines.append(f"- `{p.name}` -- {p.filename}")
                if len(by_cat[c]) > 10:
                    lines.append(f"  *...and {len(by_cat[c]) - 10} more*")
        if cat.samples:
            lines.append(f"\n### Samples ({len(cat.samples)})")
            by_cat2: dict[str, list] = {}
            for s in cat.samples:
                by_cat2.setdefault(s.category, []).append(s)
            for c in sorted(by_cat2):
                lines.append(f"\n**{c}** ({len(by_cat2[c])})")
                for s in by_cat2[c][:10]:
                    lines.append(f"- `{s.filename}`")
                if len(by_cat2[c]) > 10:
                    lines.append(f"  *...and {len(by_cat2[c]) - 10} more*")
        if cat.wavetables:
            lines.append(f"\n### Wavetables ({len(cat.wavetables)})")
            for wt in cat.wavetables[:20]:
                lines.append(f"- `{wt.filename}`")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_import_dir(dir_path: str, category: str) -> str:
    """Import samples from a local directory into the library."""
    if not dir_path.strip():
        return "Enter a directory path."
    if not category:
        return "Select a category for the imported files."
    p = Path(dir_path.strip())
    if not p.exists():
        return f"Directory not found: `{p}`"
    if not p.is_dir():
        return f"Not a directory: `{p}`"
    try:
        lib = SampleLibrary()
        count = lib.import_directory(str(p), category)
        return f"Imported {count} files from `{p}` into **{category}**."
    except Exception as e:
        return f"Error: {e}"


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
    """Run the full Phase 1 generation pipeline.

    Returns (status_md, dna_json, file_listing).
    """
    if not song_name.strip():
        return "**Error**: Song name is required.", "", ""

    progress(0.0, desc="Building SongBlueprint...")

    # Parse tags
    tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []

    progress(0.1, desc="Forging SongDNA...")

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in song_name)
    safe_name = safe_name.strip().replace(" ", "_")

    # Clean up auto-select values
    clean_key = key if key and key != "(auto)" else ""
    clean_scale = scale if scale and scale != "(auto)" else ""
    clean_arr = arrangement if arrangement and arrangement != "(auto)" else ""

    try:
        dna = forge_song_dna(
            name=song_name.strip(),
            style=style or "dubstep",
            mood=mood or "",
            key=clean_key,
            scale=clean_scale,
            bpm=bpm or 0,
            arrangement=clean_arr,
            tags=tags,
            notes=notes or "",
        )
    except Exception as e:
        return f"**Error forging DNA**: {e}\n```\n{traceback.format_exc()}\n```", "", ""

    progress(0.3, desc="Saving SongDNA...")

    # Save DNA JSON
    dna_dir = OUTPUT_ROOT / "dna"
    dna_dir.mkdir(parents=True, exist_ok=True)
    dna_path = dna_dir / f"{safe_name}_dna.json"
    try:
        save_dna(dna, str(dna_path))
    except Exception:
        dna_path.write_text(
            json.dumps(asdict(dna), indent=2, default=str), encoding="utf-8"
        )

    progress(0.4, desc="Generating Serum 2 presets...")

    # Generate FXP presets
    preset_dir = OUTPUT_ROOT / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[str] = []

    for i, patch_dict in enumerate(_DUBSTEP_PATCHES):
        try:
            patch_name = patch_dict.get("name", f"patch_{i}").replace(" ", "_")
            fxp_path = preset_dir / f"{safe_name}_{patch_name}.fxp"
            preset = FXPPreset(
                plugin_id="XfsP",
                version=2,
                name=f"DF_{patch_name}"[:24],
                params=[],
            )
            write_fxp(preset, str(fxp_path))
            generated_files.append(f"presets/{fxp_path.name}")
        except Exception:
            pass  # Some patches may not have exportable params

    progress(0.6, desc="Generating MIDI...")

    # Generate MIDI file from DNA
    midi_dir = OUTPUT_ROOT / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    midi_path = midi_dir / f"{safe_name}.mid"
    try:
        events: list[NoteEvent] = []
        actual_bpm = dna.bpm or bpm or 150
        # Build bass notes from DNA's bass riff patterns
        root_midi = 36  # C2 default
        # Map key name to MIDI
        key_map = {n: (36 + i) for i, n in enumerate(NOTES)}
        if dna.key in key_map:
            root_midi = key_map[dna.key]
        for bar in range(min(16, dna.total_bars)):
            events.append(NoteEvent(
                pitch=root_midi, velocity=100,
                start_beat=bar * 4.0, duration_beats=2.0,
            ))
        # write_midi_file expects list[tuple[str, list[NoteEvent]]]
        write_midi_file(
            [("Bass", events)], str(midi_path), bpm=actual_bpm
        )
        generated_files.append(f"midi/{midi_path.name}")
    except Exception:
        pass

    progress(0.8, desc="Generating ALS...")

    # Generate ALS project
    als_dir = OUTPUT_ROOT / "ableton"
    als_dir.mkdir(parents=True, exist_ok=True)
    als_path = als_dir / f"{safe_name}_PHASE2_ARRANGEMENT.als"
    try:
        actual_bpm_val = float(dna.bpm or bpm or 150)
        tracks = [
            ALSTrack(name="SUB BASS", color=1),
            ALSTrack(name="MID BASS", color=2),
            ALSTrack(name="GROWL", color=3),
            ALSTrack(name="LEAD", color=4),
            ALSTrack(name="CHORDS", color=5),
            ALSTrack(name="PAD", color=6),
            ALSTrack(name="ARP", color=7),
            ALSTrack(name="FX", color=8),
            ALSTrack(name="DRUMS", color=9),
            ALSTrack(name="RISER", color=10),
        ]
        scenes = [
            ALSScene(name=sec_name)
            for sec_name in [
                "INTRO", "BUILD", "DROP 1", "BREAK",
                "BUILD 2", "DROP 2", "OUTRO",
            ]
        ]
        project = ALSProject(
            name=safe_name,
            bpm=actual_bpm_val,
            tracks=tracks,
            scenes=scenes,
        )
        write_als(project, str(als_path))
        generated_files.append(f"ableton/{als_path.name}")
    except Exception:
        pass

    progress(1.0, desc="Done!")

    # Build result
    status_lines = [
        f"## {song_name} — Generation Complete",
        "",
        f"**Style**: {style or 'dubstep'}",
        f"**Mood**: {mood or 'auto'}",
        f"**Key**: {dna.key or key or 'auto'}",
        f"**BPM**: {dna.bpm or bpm or 'auto'}",
        f"**Scale**: {dna.scale or scale or 'auto'}",
        f"**Arrangement**: {arrangement or 'auto'}",
        "",
        "### Generated Files",
    ]
    for f in generated_files:
        status_lines.append(f"- `output/{f}`")

    status_lines.extend([
        "",
        "### Next Steps",
        f"1. Open `output/{als_path.relative_to(OUTPUT_ROOT)}` in Ableton Live 12",
        "2. Load Serum 2 on each synth track",
        "3. Load presets from `output/presets/`",
        "4. Load wavetables from `output/wavetables/`",
        "5. Load drum samples into Drum Racks",
        "6. Tweak, play, add automation",
        "7. Export stems (24-bit WAV) for Phase 3: Mixing",
    ])

    try:
        dna_display = json.dumps(asdict(dna), indent=2, default=str)[:5000]
    except Exception:
        dna_display = str(dna)[:5000]

    file_listing = "\n".join(f"output/{f}" for f in generated_files)
    return "\n".join(status_lines), dna_display, file_listing


# ═══════════════════════════════════════════════════════════════════════════
# GRADIO UI
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
.dubforge-header h1 {
    color: #a855f7 !important;
    font-size: 2em !important;
    margin: 0 !important;
}
.dubforge-header p {
    color: #9ca3af !important;
    margin: 4px 0 0 0 !important;
}
.phase-box {
    border-left: 3px solid #6b21a8;
    padding-left: 12px;
    margin: 8px 0;
}
"""

def build_ui() -> gr.Blocks:
    """Build the Gradio Blocks UI."""
    with gr.Blocks(
        title="DUBFORGE Launchpad",
    ) as app:
        # Header
        gr.HTML(
            '<div class="dubforge-header">'
            "<h1>DUBFORGE LAUNCHPAD</h1>"
            "<p>Underground Industrial Bass Factory &mdash; "
            "Phase 1: Generation Wizard</p>"
            "</div>"
        )

        with gr.Tabs():
            # ─── TAB 1: IDEA SANDBOX ──────────────────────────────────
            with gr.Tab("1. Idea Sandbox", id="idea"):
                gr.Markdown(
                    "### Define Your Track\n"
                    "Set the core parameters. Everything else is derived "
                    "from these inputs via phi ratios and the SongDNA engine."
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        song_name = gr.Textbox(
                            label="Song Name",
                            placeholder="e.g. CYCLOPS FURY, HOLLOW POINT, ALIEN REQUIEM",
                            info="Semantic words drive sound design params via 81 WORD_ATOMS",
                        )
                        with gr.Row():
                            style = gr.Dropdown(
                                choices=STYLE_OPTIONS,
                                value="dubstep",
                                label="Style",
                                info="Sets BPM range + sound character",
                            )
                            mood = gr.Textbox(
                                label="Mood",
                                placeholder="e.g. dark, aggressive, euphoric, chaotic",
                                info="14 moods + 20 aliases + blending (dark+aggressive)",
                            )
                        with gr.Row():
                            key = gr.Dropdown(
                                choices=["(auto)"] + KEY_OPTIONS,
                                value="(auto)",
                                label="Key",
                            )
                            scale = gr.Dropdown(
                                choices=["(auto)"] + SCALE_OPTIONS,
                                value="(auto)",
                                label="Scale",
                            )
                            bpm = gr.Slider(
                                minimum=100,
                                maximum=200,
                                step=1,
                                value=150,
                                label="BPM",
                                info="0 = auto from style",
                            )
                        with gr.Row():
                            arrangement = gr.Dropdown(
                                choices=["(auto)"] + ARRANGEMENT_OPTIONS,
                                value="(auto)",
                                label="Arrangement Template",
                                info="weapon / emotive / hybrid / fibonacci",
                            )
                            tags_input = gr.Textbox(
                                label="Tags",
                                placeholder="heavy, festival, crowd-killer",
                                info="Comma-separated tags for categorization",
                            )
                        artist_notes = gr.Textbox(
                            label="Artist Notes",
                            placeholder="Free-form: vibe, reference tracks, ideas...",
                            lines=3,
                        )
                    with gr.Column(scale=1):
                        gr.Markdown("### Mood Preview")
                        mood_preview = gr.Markdown("_Enter a mood to preview_")
                        mood_btn = gr.Button("Preview Mood", variant="secondary")

                mood_btn.click(
                    fn=handle_mood_preview,
                    inputs=[mood, bpm],
                    outputs=[mood_preview],
                )
                # Auto-preview on mood change
                mood.change(
                    fn=handle_mood_preview,
                    inputs=[mood, bpm],
                    outputs=[mood_preview],
                )

            # ─── TAB 2: ARRANGEMENT ───────────────────────────────────
            with gr.Tab("2. Arrangement", id="arrangement"):
                gr.Markdown(
                    "### Arrangement Blueprint\n"
                    "Preview song structure with energy curve visualization. "
                    "RCO (Resonance Curve Orchestrator) overlays Subtronics-derived "
                    "energy dynamics with phi-curve interpolation."
                )
                with gr.Row():
                    arr_type = gr.Dropdown(
                        choices=ARRANGEMENT_OPTIONS,
                        value="weapon",
                        label="Arrangement Type",
                    )
                    rco_preset = gr.Dropdown(
                        choices=ENERGY_PRESETS,
                        value="weapon",
                        label="RCO Energy Preset",
                        info="Subtronics-derived energy dynamics",
                    )
                with gr.Row():
                    arr_bpm = gr.Slider(
                        minimum=100, maximum=200, step=1, value=150,
                        label="BPM",
                    )
                    arr_key = gr.Dropdown(
                        choices=KEY_OPTIONS, value="F", label="Key",
                    )
                arr_preview_btn = gr.Button(
                    "Preview Arrangement", variant="primary"
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        arr_info = gr.Markdown(
                            "_Click Preview to see arrangement_"
                        )
                    with gr.Column(scale=2):
                        arr_plot = gr.Plot(label="Energy Curve")

                arr_preview_btn.click(
                    fn=handle_arrangement_preview,
                    inputs=[arr_type, arr_bpm, arr_key, rco_preset],
                    outputs=[arr_info, arr_plot],
                )

            # ─── TAB 3: SAMPLE PACKS ─────────────────────────────────
            with gr.Tab("3. Sample Packs", id="samples"):
                gr.Markdown(
                    "### Sample Library & GALATCIA Collection\n"
                    "Browse, search, and manage your sample library. "
                    "26 categories from kicks to textures."
                )
                with gr.Row():
                    scan_btn = gr.Button(
                        "Scan Library", variant="secondary"
                    )
                    download_btn = gr.Button(
                        "Download CC0 Starter Pack", variant="secondary"
                    )
                sample_info = gr.Markdown(
                    "_Click Scan to see available samples_"
                )
                download_status = gr.Markdown("")

                scan_btn.click(
                    fn=handle_sample_scan,
                    inputs=[],
                    outputs=[sample_info],
                )
                download_btn.click(
                    fn=handle_download_starter_pack,
                    inputs=[],
                    outputs=[download_status],
                )

                gr.Markdown("---")
                gr.Markdown("### Browse by Category")
                with gr.Row():
                    cat_dropdown = gr.Dropdown(
                        choices=sorted(SAMPLE_CATEGORIES),
                        label="Category",
                        info="26 categories: kick, snare, bass_hit, "
                             "fx_riser, vocal, texture...",
                    )
                    browse_cat_btn = gr.Button(
                        "Browse", variant="secondary"
                    )
                cat_output = gr.Markdown("")
                browse_cat_btn.click(
                    fn=handle_browse_category,
                    inputs=[cat_dropdown],
                    outputs=[cat_output],
                )

                gr.Markdown("### Search Samples")
                with gr.Row():
                    search_input = gr.Textbox(
                        label="Search",
                        placeholder="e.g. wobble, dark, 808",
                    )
                    search_btn = gr.Button(
                        "Search", variant="secondary"
                    )
                search_output = gr.Markdown("")
                search_btn.click(
                    fn=handle_search_samples,
                    inputs=[search_input],
                    outputs=[search_output],
                )

                gr.Markdown("### GALATCIA Collection")
                galatcia_btn = gr.Button(
                    "Browse GALATCIA Presets & Samples",
                    variant="secondary",
                )
                galatcia_output = gr.Markdown("")
                galatcia_btn.click(
                    fn=handle_browse_galatcia,
                    inputs=[],
                    outputs=[galatcia_output],
                )

                gr.Markdown("### Import from Directory")
                with gr.Row():
                    import_path = gr.Textbox(
                        label="Directory Path",
                        placeholder=r"C:\Users\...\samples",
                        info="Auto-categorizes by folder name or "
                             "filename pattern",
                    )
                    import_category = gr.Dropdown(
                        choices=sorted(SAMPLE_CATEGORIES),
                        label="Import Category",
                    )
                    import_btn = gr.Button(
                        "Import", variant="secondary"
                    )
                import_output = gr.Markdown("")
                import_btn.click(
                    fn=handle_import_dir,
                    inputs=[import_path, import_category],
                    outputs=[import_output],
                )

            # ─── TAB 4: SERUM 2 PATCHES ──────────────────────────────
            with gr.Tab("4. Serum 2 Patches", id="serum"):
                gr.Markdown(
                    "### DUBFORGE Serum 2 Patches\n"
                    "8 phi-derived patches for bass, lead, pad, and FX. "
                    "Each preset is generated as .fxp during Phase 1."
                )
                patch_lines = []
                for p in _DUBSTEP_PATCHES:
                    pname = p.get("name", "?")
                    cat = p.get("category", "")
                    desc = ", ".join(p.get("tags", [])[:5])
                    patch_lines.append(
                        f"- **{pname}** ({cat}) — {desc}"
                    )
                gr.Markdown("\n".join(patch_lines) if patch_lines else "_No patches found_")

            # ─── TAB 5: FORGE — GENERATE ALL ─────────────────────────
            with gr.Tab("5. FORGE IT", id="forge"):
                gr.Markdown(
                    "### Launch Phase 1: Generation\n"
                    "Generate SongDNA, Serum 2 presets, MIDI, and ALS "
                    "from the parameters defined in the Idea Sandbox.\n\n"
                    "**This creates everything needed for Phase 2: Arrangement.**"
                )
                forge_btn = gr.Button(
                    "FORGE IT",
                    variant="primary",
                    size="lg",
                )
                with gr.Row():
                    forge_status = gr.Markdown("_Ready to forge_")
                with gr.Accordion("SongDNA (JSON)", open=False):
                    dna_output = gr.Code(
                        label="SongDNA", language="json", lines=20
                    )
                with gr.Accordion("Generated Files", open=False):
                    file_output = gr.Textbox(
                        label="Files", lines=10, interactive=False
                    )

                forge_btn.click(
                    fn=handle_forge,
                    inputs=[
                        song_name,
                        style,
                        mood,
                        key,
                        scale,
                        bpm,
                        arrangement,
                        tags_input,
                        artist_notes,
                    ],
                    outputs=[forge_status, dna_output, file_output],
                )

            # ─── TAB 6: PIPELINE VIEW ────────────────────────────────
            with gr.Tab("Pipeline", id="pipeline"):
                gr.Markdown(
                    """### DUBFORGE 4-Phase Production Pipeline

```
INPUT: Song Idea (name, mood, key, BPM, style, energy)
         │
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 1: GENERATION — "The Idea Sandbox"           │
   │  Sound design + sample selection + preset creation   │
   │  OUTPUT: Sound palette (FXP, WAV, ADG, MIDI)        │
   └─────┬───────────────────────────────────────────────┘
         │ sounds + samples ready
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 2: ARRANGEMENT — "The Creation Session"      │
   │  Ableton Session #1: full song structure             │
   │  INTRO → BUILD → DROP → BREAK → DROP 2 → OUTRO     │
   │  OUTPUT: Mix stems (24-bit WAV)                      │
   └─────┬───────────────────────────────────────────────┘
         │ stems exported
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 3: MIXING — "The Mix Session"                │
   │  Ableton Session #2: EQ, compress, spatial, balance  │
   │  OUTPUT: Mixed stems (24-bit WAV)                    │
   └─────┬───────────────────────────────────────────────┘
         │ mixed stems exported
   ┌─────▼───────────────────────────────────────────────┐
   │  PHASE 4: MASTERING — "The Master Session"          │
   │  Ableton Session #3: multiband, limiting, LUFS      │
   │  OUTPUT: Final WAV — DANCEFLOOR BANGER              │
   └─────────────────────────────────────────────────────┘
```

### Doctrine Constants
- **PHI** = {phi:.10f}
- **A4_432** = {a4} Hz
- **Fibonacci** = {fib}
""".format(phi=PHI, a4=A4_432, fib=str(FIBONACCI[:13]))
                )

    return app


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="DUBFORGE Launchpad")
    parser.add_argument("--port", type=int, default=7870)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    app = build_ui()
    app.launch(
        server_port=args.port,
        share=args.share,
        inbrowser=True,
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
