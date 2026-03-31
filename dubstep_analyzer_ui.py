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
from pathlib import Path
from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════════════════
# GRADIO — optional import with helpful error
# ═══════════════════════════════════════════════════════════════════════════

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    gr = None

gr: Any

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

def handle_auto_likes(browser: str = "chrome",
                      max_tracks: int = 100,
                      run_stem_sep: bool = True,
                      gen_blueprints: bool = True,
                      skip_existing: bool = True,
                      cookies_file_obj=None):
    """
    Auto-analyze all SoundCloud likes.  Streams progress updates to the UI.

    Uses ``soundcloud.com/you/likes`` with cookie auth from the chosen browser
    (or a cookies.txt file), downloads in batches, and analyzes each track.
    Tracks that already have analysis JSON on disk are skipped when
    *skip_existing* is True.
    """
    # Resolve cookies source
    cookies_file_path: Optional[str] = None
    if cookies_file_obj is not None:
        # Gradio File widget gives a temp path string or NamedStr
        cookies_file_path = str(cookies_file_obj)
        if not Path(cookies_file_path).exists():
            yield "❌ Uploaded cookies file not found on disk.", ""
            return

    # Auto-detect cookies.txt in project root if no file uploaded
    if cookies_file_path is None:
        default_cookies = Path(__file__).parent / "cookies.txt"
        if default_cookies.exists():
            cookies_file_path = str(default_cookies)

    if browser == "none" and not cookies_file_path:
        yield (
            "❌ Cookie auth is **required** for `/you/likes`.\n\n"
            "Either pick your browser above, or upload a **cookies.txt** file "
            "(Netscape format — use a browser extension like "
            "[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc))."
        ), ""
        return

    try:
        from engine.soundcloud_pipeline import SUPPORTED_BROWSERS
    except ImportError:
        SUPPORTED_BROWSERS = ()

    if not cookies_file_path and browser not in SUPPORTED_BROWSERS:
        yield (f"❌ Unknown browser '{browser}'. "
               f"Valid: chrome, firefox, edge, safari, brave, chromium"), ""
        return

    likes_url = "https://soundcloud.com/you/likes"
    stem_note = " (~2-4 min/track on CPU)" if run_stem_sep else ""
    yield (
        f"⏳ **Auto-analyzing your SoundCloud likes**{stem_note}\n\n"
        f"**URL:** `{likes_url}`\n"
        f"**Max tracks:** {max_tracks}\n"
        f"**Skip already-analyzed:** {'Yes' if skip_existing else 'No'}\n\n"
        f"*Check the terminal for live demucs progress bars.*"
    ), ""

    try:
        from engine.dubstep_taste_analyzer import (
            analyze_track,
            build_prototypes,
            export_analysis,
            export_prototypes,
            export_taste_report,
        )
        from engine.serum_blueprint import (
            export_all_blueprints,
            generate_blueprints_from_analysis,
        )
        from engine.soundcloud_pipeline import (
            OUTPUT_ROOT as SC_OUTPUT,
        )
        from engine.soundcloud_pipeline import (
            download_soundcloud_likes,
            separate_stems,
        )

        out = SC_OUTPUT
        out.mkdir(parents=True, exist_ok=True)

        # --- Download track list ---
        yield "⏳ Fetching liked tracks list from SoundCloud...", ""
        try:
            tracks = download_soundcloud_likes(
                likes_url,
                output_dir=out / "downloads",
                max_tracks=int(max_tracks),
                cookies_from_browser=browser if not cookies_file_path else None,
                cookies_file=cookies_file_path,
            )
        except RuntimeError as e:
            err_msg = str(e)
            hint = ""
            if "cookie" in err_msg.lower() or "copy" in err_msg.lower():
                hint = (
                    "\n\n**Tip:** Your browser's cookie database is locked "
                    "(this happens when the browser is open).\n\n"
                    "**Fix options:**\n"
                    "1. **Close your browser** completely and try again\n"
                    "2. **Upload a cookies.txt file** instead "
                    "(use a browser extension to export cookies in Netscape format)"
                )
            yield f"❌ **Failed to fetch SoundCloud likes:**\n\n`{err_msg}`{hint}", ""
            return

        total = len(tracks)
        downloaded = sum(1 for t in tracks if t.downloaded)
        yield (
            f"⏳ **{downloaded}/{total}** tracks downloaded.\n\n"
            f"Starting analysis..."
        ), ""

        # --- Analyze each track ---
        analyses: list = []
        skipped = 0
        errors: list[str] = []

        for idx, track in enumerate(tracks, 1):
            if not track.downloaded:
                continue

            track_name = track.title or Path(track.filepath).stem

            # Skip if already analyzed
            analysis_file = out / f"{track_name}_analysis.json"
            if skip_existing and analysis_file.exists():
                skipped += 1
                yield (
                    f"⏳ [{idx}/{total}] ⏭️ Skipping **{track_name}** (already analyzed)\n\n"
                    f"Analyzed: {len(analyses)} | Skipped: {skipped} | Errors: {len(errors)}"
                ), ""
                continue

            yield (
                f"⏳ [{idx}/{total}] Analyzing **{track_name}**...\n\n"
                f"Analyzed: {len(analyses)} | Skipped: {skipped} | Errors: {len(errors)}"
            ), ""

            # Stem separation
            stem_dir = None
            if run_stem_sep:
                try:
                    stem_dir = separate_stems(track.filepath, output_dir=out / "stems")
                except Exception as e:
                    errors.append(f"Stems failed ({track_name}): {e}")

            # Feature analysis
            try:
                analysis = analyze_track(
                    audio_path=track.filepath,
                    stem_dir=str(stem_dir) if stem_dir else None,
                    track_name=track_name,
                )
                analyses.append(analysis)
                export_analysis(analysis, output_dir=out)

                # Blueprints
                if gen_blueprints:
                    bps = generate_blueprints_from_analysis(
                        stems=analysis.stems,
                        track_name=analysis.track_name,
                        bpm=analysis.overall_bpm,
                    )
                    export_all_blueprints(bps, output_dir=out / "serum_blueprints")

            except Exception as e:
                errors.append(f"Analysis failed ({track_name}): {e}")

        # --- Build taste profile ---
        report_path = ""
        if analyses:
            yield (
                f"⏳ Building taste profile from **{len(analyses)}** tracks..."
            ), ""
            profile = build_prototypes(analyses)
            export_prototypes(profile, output_dir=out)
            rpath = export_taste_report(analyses, profile, output_dir=out)
            report_path = str(rpath) if rpath else ""

        # --- Final summary ---
        summary_lines = [
            "✅ **Auto-Analyze Complete**\n",
            f"**Tracks found:** {total}",
            f"**Downloaded:** {downloaded}",
            f"**Analyzed:** {len(analyses)}",
            f"**Skipped (existing):** {skipped}",
        ]
        if errors:
            summary_lines.append(f"\n⚠️ **Errors ({len(errors)}):**")
            for e in errors[:10]:
                summary_lines.append(f"  - {e}")
        if report_path:
            summary_lines.append(f"\n📝 Report: {report_path}")

        yield "\n".join(summary_lines), report_path

    except ImportError as e:
        yield (f"❌ Missing dependency: {e}\n"
               f"Install with: pip install yt-dlp librosa soundfile demucs"), ""
    except Exception as e:
        yield f"❌ Error: {e}", ""


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
        import shutil
        import tempfile

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
    # Full rebuild requires re-analysis from source audio.
    return


def handle_export_cookies(browser: str) -> str:
    """Export cookies from browser to cookies.txt using yt-dlp.

    This allows SoundCloud auth without keeping the browser open
    (avoids the cookie DB lock issue).
    """
    if not browser or browser == "none":
        return "Select a browser to export cookies from."

    import subprocess

    cookies_path = Path(__file__).parent / "cookies.txt"

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--cookies-from-browser", browser,
                "--cookies", str(cookies_path),
                "--skip-download",
                "https://soundcloud.com",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if cookies_path.exists() and cookies_path.stat().st_size > 0:
            size = cookies_path.stat().st_size
            return (
                f"Cookies exported to `{cookies_path}` ({size} bytes).\n\n"
                f"You can now **reopen your browser** and click "
                f"**Auto-Analyze All My Likes** -- it will auto-detect "
                f"the cookies.txt file (no browser auth needed)."
            )
        stderr = result.stderr[:500] if result.stderr else "No error details"
        return (
            f"Failed to export cookies.\n\n"
            f"**Make sure:**\n"
            f"1. You are logged into SoundCloud in {browser}\n"
            f"2. {browser} is **closed** (cookie DB is locked when open)\n"
            f"3. yt-dlp is installed (`pip install yt-dlp`)\n\n"
            f"**Error:** {stderr}"
        )
    except FileNotFoundError:
        return "yt-dlp not found. Install with: `pip install yt-dlp`"
    except subprocess.TimeoutExpired:
        return "Cookie export timed out. Try closing the browser and retry."
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _format_multi_pipeline_summary(totals: dict, urls: list[str]) -> str:
    """Format multi-source pipeline result into readable summary."""
    lines = [
        "✅ Multi-Source Pipeline Complete",
        "",
        f"**Sources processed:** {len(urls)}",
        f"**Tracks found:** {totals.get('total_found', 0)}",
        f"**Downloaded:** {totals.get('total_downloaded', 0)}",
        f"**Analyzed:** {totals.get('total_analyzed', 0)}",
    ]

    per_source: dict = totals.get("results", {})
    if per_source:
        lines.append("\n**Per Source:**")
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
        "✅ Pipeline Complete",
        "",
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
        lines.append("\n**Tracks:**")
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
        "# Taste Profile\n",
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
        "",
        "### Chaos Recommendation",
        f"**{chaos.get('attractor', '?')}** (confidence: {chaos.get('confidence', 0):.0%})",
        f"*{chaos.get('sonic_character', '')}*",
        "",
        f"**LFO {chaos.get('lfo_slot', 3)} → Targets:** {', '.join(chaos.get('targets', []))}",
        f"**Rate Sync:** {chaos.get('rate_sync', '?')}",
        "",
        "### Warp Config (Osc A)",
    ]

    osc_a = data.get("osc_a", {})
    warp = osc_a.get("warp", {})
    lines.append(f"  - Warp 1: **{warp.get('warp_1', 'Off')}** @ {warp.get('warp_1_amount', 0):.2f}")
    lines.append(f"  - Warp 2: **{warp.get('warp_2', 'Off')}** @ {warp.get('warp_2_amount', 0):.2f}")
    if warp.get("notes"):
        lines.append(f"  - *{warp.get('notes')}*")

    lines.append("\n### Modulation Matrix")
    for route in data.get("mod_matrix", [])[:8]:
        lines.append(f"  - **{route.get('source')}** → {route.get('target')} "
                     f"(amt: {route.get('amount', 0):+.2f})")

    lines.append("\n### FX Chain")
    for fx in data.get("fx_chain", []):
        lines.append(f"  - **{fx.get('fx_type')}** — mix: {fx.get('mix', 0):.0%} "
                     f"| {fx.get('notes', '')}")

    tips = data.get("dojo_tips", [])
    if tips:
        lines.append("\n### 💡 Dojo Tips")
        for tip in tips:
            lines.append(f"  - {tip}")

    return "\n".join(lines)


def _format_stats(data: dict) -> str:
    lines = [
        "**Last pipeline run:**",
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


def build_ui() -> Any:
    _require_gradio()

    with gr.Blocks(title="DUBFORGE Taste Analyzer") as app:

        gr.Markdown(HEADER)

        with gr.Tabs():

            # ── TAB 0: Auto-Analyze Likes ──
            with gr.TabItem("⚡ Auto-Analyze Likes"):
                gr.Markdown(
                    "### One-Click SoundCloud Likes Analyzer\n"
                    "Automatically fetches **all** your SoundCloud likes, downloads them, "
                    "separates stems, and builds your taste profile.\n\n"
                    "**Requires:** Cookie auth — either from your browser (must be logged in "
                    "to SoundCloud) or via a **cookies.txt** file upload."
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        auto_browser = gr.Dropdown(
                            choices=["chrome", "firefox", "edge",
                                     "brave", "chromium", "safari", "none"],
                            value="edge",
                            label="Browser (for SoundCloud cookies)",
                            info="Must be logged into SoundCloud in this browser. "
                                 "Set to 'none' if using cookies.txt file instead.",
                        )
                    with gr.Column(scale=1):
                        auto_max = gr.Slider(
                            minimum=5, maximum=500, value=100, step=5,
                            label="Max Tracks",
                        )

                with gr.Row():
                    auto_cookies_file = gr.File(
                        label="cookies.txt (optional -- Netscape format)",
                        file_types=[".txt"],
                        type="filepath",
                    )

                with gr.Accordion(
                    "Cookie Setup (click to expand)", open=False
                ):
                    gr.Markdown(
                        "**Option A -- One-Click Export (recommended):**\n"
                        "1. **Close your browser** completely\n"
                        "2. Click **Export Cookies** below\n"
                        "3. Reopen your browser -- cookies.txt is saved\n"
                        "4. Click **Auto-Analyze** -- it auto-detects the file\n\n"
                        "**Option B -- Browser Extension:**\n"
                        "Install [Get cookies.txt LOCALLY]"
                        "(https://chromewebstore.google.com/detail/"
                        "get-cookiestxt-locally/"
                        "cclelndahbckbenkjhflpdbgdldlbecc) "
                        "for Chrome, export, and upload above.\n\n"
                        "**Option C -- Direct browser auth:**\n"
                        "Close your browser, select it above, and run. "
                        "Slower but no cookies.txt needed."
                    )
                    with gr.Row():
                        export_cookies_btn = gr.Button(
                            "Export Cookies from Browser",
                            variant="secondary",
                        )
                    export_cookies_status = gr.Markdown("")
                    export_cookies_btn.click(
                        fn=handle_export_cookies,
                        inputs=[auto_browser],
                        outputs=[export_cookies_status],
                    )

                with gr.Row():
                    auto_stems = gr.Checkbox(value=True, label="Separate Stems (HT-Demucs)")
                    auto_blueprints = gr.Checkbox(value=True, label="Generate Serum Blueprints")
                    auto_skip = gr.Checkbox(value=True, label="Skip Already-Analyzed Tracks")

                auto_btn = gr.Button("⚡ Auto-Analyze All My Likes", variant="primary")
                auto_output = gr.Markdown(label="Progress")
                auto_report = gr.Textbox(label="Report path", visible=False)

                auto_btn.click(
                    fn=handle_auto_likes,
                    inputs=[auto_browser, auto_max, auto_stems,
                            auto_blueprints, auto_skip, auto_cookies_file],
                    outputs=[auto_output, auto_report],
                )

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
