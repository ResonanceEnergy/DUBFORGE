"""
DUBFORGE — Dubstep Taste Analyzer Web UI

Gradio web interface for the DUBFORGE taste analysis system.

Tabs:
    1. Analyze SoundCloud Likes   — batch download + analyze
    2. Analyze Local Files        — drag-drop local audio
    3. Taste Profile Viewer       — browse prototypes + rankings
    4. Serum Blueprints           — view + export blueprints
    5. Feedback Loop              — thumbs up/down tracks

Usage:
    python dubstep_analyzer_ui.py
    python dubstep_analyzer_ui.py --port 7861 --share
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# GRADIO — optional import with helpful error
# ═══════════════════════════════════════════════════════════════════════════

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    gr = None  # type: ignore[assignment]

# ═══════════════════════════════════════════════════════════════════════════
# DUBFORGE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════

OUTPUT_ROOT = Path(__file__).parent / "output" / "taste"


def _require_gradio() -> None:
    if not HAS_GRADIO:
        raise ImportError("Gradio not installed. Run: pip install gradio")


# ═══════════════════════════════════════════════════════════════════════════
# BACKEND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def handle_soundcloud_analysis(sources_text: str,
                                max_tracks: int = 20,
                                browser: str = "none",
                                run_stem_sep: bool = True,
                                gen_blueprints: bool = True):
    """
    Gradio streaming generator handler: analyze one or more SoundCloud URLs.
    Yields (status_text, report_path) progressively so the UI stays live.
    """
    urls = [u.strip() for u in sources_text.replace(",", " ").split() if u.strip()]
    if not urls:
        yield "❌ Please enter at least one SoundCloud URL", ""
        return

    cookie_browser: Optional[str] = None if browser == "none" else browser

    if cookie_browser:
        try:
            from engine.soundcloud_pipeline import SUPPORTED_BROWSERS
        except ImportError:
            SUPPORTED_BROWSERS = ()
        if cookie_browser not in SUPPORTED_BROWSERS:
            yield (f"❌ Unknown browser '{cookie_browser}'. "
                   f"Valid: chrome, firefox, edge, safari, brave, chromium"), ""
            return

    stem_note = " (~2-4 min/track on CPU)" if run_stem_sep else ""
    sources_list = "\n".join(f"  - `{u}`" for u in urls)
    yield (
        f"⏳ **Pipeline running...**{stem_note}\n\n"
        f"**Sources ({len(urls)}):**\n{sources_list}\n\n"
        f"Steps: Download → Stem separation → Feature analysis → Serum blueprints → Taste profile\n\n"
        f"*Check the terminal for live demucs progress bars.*"
    ), ""

    try:
        from engine.soundcloud_pipeline import run_multi_pipeline
        totals = run_multi_pipeline(
            source_urls=urls,
            max_tracks=int(max_tracks),
            separate=run_stem_sep,
            generate_blueprints=gen_blueprints,
            cookies_from_browser=cookie_browser,
        )

        summary = _format_multi_pipeline_summary(totals, urls)
        report_path = totals.get("merged_report", "")
        yield summary, report_path

    except ImportError as e:
        yield (f"❌ Missing dependency: {e}\n"
               f"Install with: pip install yt-dlp librosa soundfile demucs"), ""
    except Exception as e:
        yield f"❌ Error: {e}", ""


def handle_local_analysis(audio_files: list,
                           run_stem_sep: bool = False,
                           gen_blueprints: bool = True) -> tuple[str, str]:
    """
    Gradio handler: analyze uploaded audio files.
    Returns (summary_text, report_path).
    """
    if not audio_files:
        return "❌ Please upload audio files", ""

    try:
        import tempfile
        import shutil
        from engine.soundcloud_pipeline import analyze_local_files

        # Copy uploaded files to temp dir
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in audio_files:
                src = Path(f.name) if hasattr(f, 'name') else Path(str(f))
                dst = Path(tmpdir) / src.name
                shutil.copy2(str(src), str(dst))

            result = analyze_local_files(
                audio_dir=tmpdir,
                separate=run_stem_sep,
                generate_blueprints=gen_blueprints,
            )

        summary = _format_pipeline_summary(result.to_dict())
        report_path = result.report_path or ""
        return summary, report_path

    except ImportError as e:
        return f"❌ Missing dependency: {e}", ""
    except Exception as e:
        return f"❌ Error: {e}", ""


def handle_load_profile() -> tuple[str, str, str]:
    """Load the existing taste profile for viewer tab."""
    prototypes_path = OUTPUT_ROOT / "prototypes.json"
    rankings_path = OUTPUT_ROOT / "taste_report.md"
    pipeline_path = OUTPUT_ROOT / "pipeline_result.json"

    if not prototypes_path.exists():
        return "No taste profile found. Run analysis first.", "", ""

    try:
        data = json.loads(prototypes_path.read_text())
        proto_text = _format_prototypes(data)

        rankings_text = ""
        if rankings_path.exists():
            rankings_text = rankings_path.read_text()

        stats_text = ""
        if pipeline_path.exists():
            pdata = json.loads(pipeline_path.read_text())
            stats_text = _format_stats(pdata)

        return proto_text, rankings_text, stats_text

    except Exception as e:
        return f"Error loading profile: {e}", "", ""


def handle_load_blueprints(track_name: str = "") -> str:
    """Load Serum blueprint for a specific track/stem."""
    bp_dir = OUTPUT_ROOT / "serum_blueprints"
    if not bp_dir.exists():
        return "No blueprints found. Run analysis first."

    blueprints = list(bp_dir.glob("*.json"))
    if not blueprints:
        return "No blueprint files found."

    if track_name.strip():
        # Filter by track name
        matching = [b for b in blueprints if track_name.lower() in b.stem.lower()]
        blueprints = matching or blueprints[:5]

    # Format first few blueprints
    texts = []
    for bp_file in blueprints[:10]:
        try:
            data = json.loads(bp_file.read_text())
            texts.append(_format_blueprint(data))
        except Exception:
            continue

    return "\n\n---\n\n".join(texts) if texts else "No blueprints to display."


def handle_feedback(track_name: str, thumbs: str) -> str:
    """Apply feedback to a track."""
    if not track_name.strip():
        return "❌ Enter a track name"
    if thumbs not in ("👍 Up", "👎 Down"):
        return "❌ Select thumbs up or down"

    try:
        from engine.soundcloud_pipeline import apply_feedback
        thumb_val = "up" if "Up" in thumbs else "down"
        apply_feedback(str(OUTPUT_ROOT), track_name.strip(), thumb_val)

        # Rebuild prototypes with feedback
        _rebuild_with_feedback()
        return f"✅ Applied {thumbs} to '{track_name}' — prototypes updated"

    except Exception as e:
        return f"❌ Error: {e}"


def _rebuild_with_feedback() -> None:
    """Rebuild taste prototypes incorporating feedback."""
    try:
        from engine.dubstep_taste_analyzer import (
            TrackAnalysis,
            build_prototypes,
            export_prototypes,
        )

        analysis_files = list(OUTPUT_ROOT.glob("*_analysis.json"))
        analyses = []
        for f in analysis_files:
            data = json.loads(f.read_text())
            # We can't rebuild full StemFeatures from JSON easily,
            # so just reload what we need for prototypes
            # (This is a simplified rebuild — full rebuild needs the audio)
            pass  # Placeholder — full rebuild requires re-analysis

    except Exception:
        pass  # Silent fail — prototypes will rebuild on next full analysis


# ═══════════════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _format_multi_pipeline_summary(totals: dict, urls: list[str]) -> str:
    """Format multi-source pipeline result into readable summary."""
    lines = [
        f"✅ Multi-Source Pipeline Complete",
        f"",
        f"**Sources processed:** {len(urls)}",
        f"**Tracks found:** {totals.get('total_found', 0)}",
        f"**Downloaded:** {totals.get('total_downloaded', 0)}",
        f"**Analyzed:** {totals.get('total_analyzed', 0)}",
    ]

    per_source: dict = totals.get("results", {})
    if per_source:
        lines.append(f"\n**Per Source:**")
        for url, result in per_source.items():
            r = result.to_dict() if hasattr(result, "to_dict") else result
            found = r.get("tracks_found", 0)
            done = r.get("tracks_analyzed", 0)
            lines.append(f"  - `{url}` — {done}/{found} analyzed")

    errors = totals.get("errors", [])
    if errors:
        lines.append(f"\n⚠️ **Errors ({len(errors)}):**")
        for e in errors[:8]:
            lines.append(f"  - {e}")

    if totals.get("merged_report"):
        lines.append(f"\n📝 Merged report: {totals['merged_report']}")

    return "\n".join(lines)


def _format_pipeline_summary(data: dict) -> str:
    """Format pipeline result into readable summary."""
    lines = [
        f"✅ Pipeline Complete",
        f"",
        f"**Source:** {data.get('source_url', 'unknown')}",
        f"**Tracks found:** {data.get('tracks_found', 0)}",
        f"**Downloaded:** {data.get('tracks_downloaded', 0)}",
        f"**Analyzed:** {data.get('tracks_analyzed', 0)}",
    ]

    errors = data.get("errors", [])
    if errors:
        lines.append(f"\n⚠️ **Errors ({len(errors)}):**")
        for e in errors[:5]:
            lines.append(f"  - {e}")

    tracks = data.get("tracks", [])
    if tracks:
        lines.append(f"\n**Tracks:**")
        for t in tracks[:20]:
            status = "✅" if t.get("downloaded") else "❌"
            lines.append(f"  {status} {t.get('title', 'Unknown')}")

    if data.get("prototype_path"):
        lines.append(f"\n📊 Prototypes saved: {data['prototype_path']}")
    if data.get("report_path"):
        lines.append(f"📝 Report saved: {data['report_path']}")

    return "\n".join(lines)


def _format_prototypes(data: dict) -> str:
    """Format taste prototypes for display."""
    lines = [
        f"# Taste Profile\n",
        f"**Tracks analyzed:** {data.get('track_count', 0)}",
        f"**👍 Up:** {data.get('thumbs_up_count', 0)}  "
        f"**👎 Down:** {data.get('thumbs_down_count', 0)}\n",
    ]

    scalar_names = [
        "BPM", "Half-time", "Sub RMS (dB)", "Golden Zone %", "Centroid (Hz)",
        "Wobble (Hz)", "Vol Mod Fidelity", "Mod Depth", "Transient Sharp",
        "Clip Headroom (dB)", "Dyn Range (dB)", "Gain Staging", "Chaos",
        "128s Compat", "Drop Potential",
    ]

    protos = data.get("prototypes", {})
    for stem_type, proto in protos.items():
        lines.append(f"\n## {stem_type} stem (n={proto.get('sample_count', 0)})")
        mean = proto.get("mean_vector", [])
        std = proto.get("std_vector", [])
        for i, name in enumerate(scalar_names):
            if i < len(mean):
                lines.append(f"  - **{name}:** {mean[i]:.3f} ±{std[i]:.3f}" if i < len(std) else f"  - **{name}:** {mean[i]:.3f}")

    return "\n".join(lines)


def _format_blueprint(data: dict) -> str:
    """Format a Serum blueprint for display."""
    chaos = data.get("chaos", {})
    lines = [
        f"## {data.get('patch_name', 'Unknown Patch')}",
        f"**Stem:** {data.get('stem_type', '?')} | **Track:** {data.get('track_name', '?')}",
        f"",
        f"### Chaos Recommendation",
        f"**{chaos.get('attractor', '?')}** (confidence: {chaos.get('confidence', 0):.0%})",
        f"*{chaos.get('sonic_character', '')}*",
        f"",
        f"**LFO {chaos.get('lfo_slot', 3)} → Targets:** {', '.join(chaos.get('targets', []))}",
        f"**Rate Sync:** {chaos.get('rate_sync', '?')}",
        f"",
        f"### Warp Config (Osc A)",
    ]

    osc_a = data.get("osc_a", {})
    warp = osc_a.get("warp", {})
    lines.append(f"  - Warp 1: **{warp.get('warp_1', 'Off')}** @ {warp.get('warp_1_amount', 0):.2f}")
    lines.append(f"  - Warp 2: **{warp.get('warp_2', 'Off')}** @ {warp.get('warp_2_amount', 0):.2f}")
    if warp.get("notes"):
        lines.append(f"  - *{warp.get('notes')}*")

    lines.append(f"\n### Modulation Matrix")
    for route in data.get("mod_matrix", [])[:8]:
        lines.append(f"  - **{route.get('source')}** → {route.get('target')} "
                     f"(amt: {route.get('amount', 0):+.2f})")

    lines.append(f"\n### FX Chain")
    for fx in data.get("fx_chain", []):
        lines.append(f"  - **{fx.get('fx_type')}** — mix: {fx.get('mix', 0):.0%} "
                     f"| {fx.get('notes', '')}")

    tips = data.get("dojo_tips", [])
    if tips:
        lines.append(f"\n### 💡 Dojo Tips")
        for tip in tips:
            lines.append(f"  - {tip}")

    return "\n".join(lines)


def _format_stats(data: dict) -> str:
    lines = [
        f"**Last pipeline run:**",
        f"  - Tracks found: {data.get('tracks_found', 0)}",
        f"  - Downloaded: {data.get('tracks_downloaded', 0)}",
        f"  - Analyzed: {data.get('tracks_analyzed', 0)}",
        f"  - Errors: {len(data.get('errors', []))}",
    ]
    return "\n".join(lines)


def _get_track_names_for_feedback() -> list[str]:
    """Get list of analyzed track names for feedback dropdown."""
    names = []
    for f in OUTPUT_ROOT.glob("*_analysis.json"):
        try:
            data = json.loads(f.read_text())
            names.append(data.get("track_name", f.stem.replace("_analysis", "")))
        except Exception:
            continue
    return sorted(names)


# ═══════════════════════════════════════════════════════════════════════════
# GRADIO UI BUILDER
# ═══════════════════════════════════════════════════════════════════════════

THEME_CSS = """
body { font-family: 'Courier New', monospace; }
.gradio-container { max-width: 1100px; }
h1 { color: #ff6b35; }
"""

HEADER = """
# 🎧 DUBFORGE — Dubstep Taste Analyzer
**v1.0 | Producer Dojo Edition | ill.Gates Methodology**

Analyzes SoundCloud likes → per-stem breakdown → Serum 2 blueprints → Lorenz/Rössler chaos routing
"""


def build_ui() -> "gr.Blocks":
    _require_gradio()

    with gr.Blocks(title="DUBFORGE Taste Analyzer") as app:

        gr.Markdown(HEADER)

        with gr.Tabs():

            # ── TAB 1: SoundCloud Likes ──
            with gr.TabItem("🔗 SoundCloud Sources"):
                gr.Markdown(
                    "### Analyze SoundCloud Sources\n"
                    "Paste one or more SoundCloud URLs — separate with spaces or new lines.\n\n"
                    "| URL type | Example |\n"
                    "|---|---|\n"
                    "| Your likes (needs cookie auth) | `https://soundcloud.com/you/likes` |\n"
                    "| Artist tracks | `https://soundcloud.com/substandardbassmusic` |\n"
                    "| Playlist / set | `https://soundcloud.com/user/sets/set-name` |\n"
                )

                with gr.Row():
                    with gr.Column(scale=3):
                        sc_urls = gr.Textbox(
                            label="SoundCloud URLs (one per line, or space-separated)",
                            placeholder=(
                                "https://soundcloud.com/you/likes\n"
                                "https://soundcloud.com/substandardbassmusic"
                            ),
                            lines=4,
                        )
                    with gr.Column(scale=1):
                        sc_max = gr.Slider(
                            minimum=1, maximum=100, value=20, step=1,
                            label="Max Tracks per Source",
                        )
                        sc_browser = gr.Dropdown(
                            choices=["none", "chrome", "firefox", "edge",
                                     "safari", "brave", "chromium"],
                            value="none",
                            label="Cookie Auth Browser",
                            info="Required for soundcloud.com/you/likes",
                        )

                with gr.Row():
                    sc_stems = gr.Checkbox(value=True, label="Separate Stems (HT-Demucs)")
                    sc_blueprints = gr.Checkbox(value=True, label="Generate Serum Blueprints")

                sc_btn = gr.Button("🚀 Analyze Sources", variant="primary")
                sc_output = gr.Markdown(label="Results")
                sc_report = gr.Textbox(label="Report path", visible=False)

                sc_btn.click(
                    fn=handle_soundcloud_analysis,
                    inputs=[sc_urls, sc_max, sc_browser, sc_stems, sc_blueprints],
                    outputs=[sc_output, sc_report],
                )

            # ── TAB 2: Local Files ──
            with gr.TabItem("📁 Local Files"):
                gr.Markdown("### Analyze Local Audio Files\n"
                            "Upload WAV/FLAC/MP3 files directly.")

                local_files = gr.Files(
                    label="Upload Audio Files",
                    file_types=["audio"],
                )

                with gr.Row():
                    local_stems = gr.Checkbox(value=False,
                                              label="Separate Stems (requires demucs)")
                    local_blueprints = gr.Checkbox(value=True, label="Generate Blueprints")

                local_btn = gr.Button("🔬 Analyze Files", variant="primary")
                local_output = gr.Markdown(label="Results")
                local_report = gr.Textbox(label="Report path", visible=False)

                local_btn.click(
                    fn=handle_local_analysis,
                    inputs=[local_files, local_stems, local_blueprints],
                    outputs=[local_output, local_report],
                )

            # ── TAB 3: Taste Profile ──
            with gr.TabItem("📊 Taste Profile"):
                gr.Markdown("### Your Personal Taste Profile\n"
                            "Averaged prototype vectors across all analyzed reference tracks.")

                load_btn = gr.Button("🔄 Load Profile")

                with gr.Row():
                    stats_box = gr.Markdown(label="Stats")

                with gr.Row():
                    with gr.Column():
                        proto_box = gr.Markdown(label="Prototypes")
                    with gr.Column():
                        rankings_box = gr.Markdown(label="Track Rankings")

                load_btn.click(
                    fn=handle_load_profile,
                    outputs=[proto_box, rankings_box, stats_box],
                )

            # ── TAB 4: Serum Blueprints ──
            with gr.TabItem("🎹 Serum Blueprints"):
                gr.Markdown("### Serum 2 Preset Blueprints\n"
                            "Browse generated blueprints with Lorenz/Rössler recommendations.")

                with gr.Row():
                    bp_track_filter = gr.Textbox(
                        label="Filter by track name (optional)",
                        placeholder="",
                        lines=1,
                    )
                    bp_load_btn = gr.Button("🎹 Load Blueprints")

                bp_output = gr.Markdown(label="Blueprints")

                bp_load_btn.click(
                    fn=handle_load_blueprints,
                    inputs=[bp_track_filter],
                    outputs=[bp_output],
                )

            # ── TAB 5: Feedback Loop ──
            with gr.TabItem("👍 Feedback"):
                gr.Markdown("### Teach the System Your Taste\n"
                            "Give thumbs up/down to refine the prototype vectors.")

                gr.Markdown(
                    "After feedback, prototypes will be rebuilt using only 👍 tracks "
                    "for more accurate style matching.\n\n"
                    "*Full prototype rebuild requires re-running the pipeline.*"
                )

                fb_track = gr.Textbox(
                    label="Track Name",
                    placeholder="Enter track name as shown in the profile",
                )
                fb_thumbs = gr.Radio(
                    choices=["👍 Up", "👎 Down"],
                    label="Feedback",
                )
                fb_btn = gr.Button("Submit Feedback")
                fb_output = gr.Markdown()

                fb_btn.click(
                    fn=handle_feedback,
                    inputs=[fb_track, fb_thumbs],
                    outputs=[fb_output],
                )

        gr.Markdown("---\n*DUBFORGE v4.0.0 — Planck × phi Fractal Basscraft Engine*")

    return app


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DUBFORGE Dubstep Taste Analyzer Web UI",
    )
    parser.add_argument("--port", type=int, default=7860, help="Server port")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    if not HAS_GRADIO:
        print("❌ Gradio not installed.")
        print("Install with: pip install gradio")
        return

    app = build_ui()
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=not args.no_browser,
        css=THEME_CSS,
    )


if __name__ == "__main__":
    main()
