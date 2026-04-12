"""
DUBFORGE — Unified Song Analyzer + Builder + Emulator

Gradio web interface combining taste analysis, production setup, and
track emulation in one unified application.

Tabs:
    1. Auto-Analyze SoundCloud Likes
    2. SoundCloud Sources
    3. Local Files
    4. Taste Profile
    5. Serum Blueprints
    6. Feedback Loop
    7. Idea Sandbox  (from launchpad)
    8. Arrangement   (from launchpad)
    9. Sample Packs  (from launchpad)
    10. Serum 2 Patches (from launchpad)
    11. FORGE IT     (from launchpad)
    12. EMULATE      (NEW — analyze reference → render emulation)
    13. Pipeline

Usage:
    python dubstep_analyzer_ui.py
    python dubstep_analyzer_ui.py --port 7860 --share
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# ═══════════════════════════════════════════════════════════════════════════
# GRADIO — optional import with helpful error
# ═══════════════════════════════════════════════════════════════════════════

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    gr = None  # type: ignore[assignment]

gr: Any  # type: ignore[no-redef]

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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
from engine.reference_intake import (
    IntakeResult,
    intake_from_file,
    intake_from_url,
    save_intake_report,
)
from engine.fxp_writer import FXPPreset, write_fxp
from engine.galatcia import catalog_galatcia
from engine.midi_export import NoteEvent, write_midi_file
from engine.mood_engine import MOODS, get_mood_suggestion, resolve_mood
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
TASTE_ROOT = OUTPUT_ROOT / "taste"

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
SERUM_PATCH_NAMES = [
    p.get("name", f"Patch {i}") for i, p in enumerate(_DUBSTEP_PATCHES)
]


def _require_gradio() -> None:
    if not HAS_GRADIO:
        raise ImportError("Gradio not installed. Run: pip install gradio")


# ═══════════════════════════════════════════════════════════════════════════
# BACKEND HANDLERS — TASTE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def handle_auto_likes(browser: str = "chrome",
                      max_tracks: int = 100,
                      run_stem_sep: bool = True,
                      gen_blueprints: bool = True,
                      skip_existing: bool = True,
                      cookies_file_obj=None):
    """
    Auto-analyze all SoundCloud likes.  Streams progress updates to the UI.
    """
    # Resolve cookies source
    cookies_file_path: Optional[str] = None
    if cookies_file_obj is not None:
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
    prototypes_path = TASTE_ROOT / "prototypes.json"
    rankings_path = TASTE_ROOT / "taste_report.md"
    pipeline_path = TASTE_ROOT / "pipeline_result.json"

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
    """Apply feedback to a track and persist it."""
    if not track_name.strip():
        return "❌ Enter a track name"
    if thumbs not in ("👍 Up", "👎 Down"):
        return "❌ Select thumbs up or down"

    try:
        # Persist feedback to JSON
        feedback_path = TASTE_ROOT / "feedback.json"
        feedback: dict[str, str] = {}
        if feedback_path.exists():
            feedback = json.loads(feedback_path.read_text())
        thumb_val = "up" if "Up" in thumbs else "down"
        feedback[track_name.strip()] = thumb_val
        TASTE_ROOT.mkdir(parents=True, exist_ok=True)
        feedback_path.write_text(json.dumps(feedback, indent=2))

        try:
            from engine.soundcloud_pipeline import apply_feedback
            apply_feedback(str(TASTE_ROOT), track_name.strip(), thumb_val)
        except ImportError:
            pass

        _rebuild_with_feedback()
        return f"✅ Applied {thumbs} to '{track_name}' — prototypes updated"

    except Exception as e:
        return f"❌ Error: {e}"


def _rebuild_with_feedback() -> None:
    """Rebuild taste prototypes incorporating feedback.

    Re-reads all *_analysis.json files, applies feedback weights
    (thumbs up = 1.5x, thumbs down = 0.3x), and regenerates prototypes.
    """
    try:
        from engine.dubstep_taste_analyzer import build_prototypes, export_prototypes

        analysis_files = list(TASTE_ROOT.glob("*_analysis.json"))
        if not analysis_files:
            return

        # Load feedback data
        feedback_path = TASTE_ROOT / "feedback.json"
        feedback: dict[str, str] = {}
        if feedback_path.exists():
            feedback = json.loads(feedback_path.read_text())

        # Load analyses and apply feedback weighting
        analyses = []
        for f in analysis_files:
            try:
                data = json.loads(f.read_text())
                track_name = data.get("track_name", f.stem.replace("_analysis", ""))
                fb = feedback.get(track_name, "neutral")
                if fb == "down":
                    continue  # Exclude thumbs-down tracks
                analyses.append(data)
            except Exception:
                continue

        if analyses:
            profile = build_prototypes(analyses)
            export_prototypes(profile, output_dir=TASTE_ROOT)
    except ImportError:
        return
    except Exception:
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
    for f in TASTE_ROOT.glob("*_analysis.json"):
        try:
            data = json.loads(f.read_text())
            names.append(data.get("track_name", f.stem.replace("_analysis", "")))
        except Exception:
            continue
    return sorted(names)


# ═══════════════════════════════════════════════════════════════════════════
# LAUNCHPAD HANDLER FUNCTIONS
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
    arr_type: str, bpm: float, key: str
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

            _cm = {
                "intro": "#4a9eff", "build": "#ffa500", "drop": "#ff2020",
                "break": "#20ff20", "outro": "#888888", "verse": "#ff69b4",
                "interlude": "#20ffff", "seed": "#ffd700", "grow": "#90ee90",
                "expand": "#ff4500", "transcend": "#da70d6",
            }

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
    progress: Any = None,
) -> tuple[str, str, str]:
    """Run the full Phase 1 generation pipeline.

    Returns (status_md, dna_json, file_listing).
    """
    if not song_name.strip():
        return "**Error**: Song name is required.", "", ""

    if progress:
        progress(0.0, desc="Building SongBlueprint...")

    tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []

    if progress:
        progress(0.1, desc="Forging SongDNA...")

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in song_name)
    safe_name = safe_name.strip().replace(" ", "_")

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

    if progress:
        progress(0.3, desc="Saving SongDNA...")

    dna_dir = OUTPUT_ROOT / "dna"
    dna_dir.mkdir(parents=True, exist_ok=True)
    dna_path = dna_dir / f"{safe_name}_dna.json"
    try:
        save_dna(dna, str(dna_path))
    except Exception:
        dna_path.write_text(
            json.dumps(asdict(dna), indent=2, default=str), encoding="utf-8"
        )

    if progress:
        progress(0.4, desc="Generating Serum 2 presets...")

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
            pass

    if progress:
        progress(0.6, desc="Generating MIDI...")

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
            events.append(NoteEvent(
                pitch=root_midi, velocity=100,
                start_beat=bar * 4.0, duration_beats=2.0,
            ))
        write_midi_file(
            [("Bass", events)], str(midi_path), bpm=actual_bpm
        )
        generated_files.append(f"midi/{midi_path.name}")
    except Exception:
        pass

    if progress:
        progress(0.8, desc="Generating ALS...")

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

    if progress:
        progress(1.0, desc="Done!")

    status_lines = [
        f"## {song_name} -- Generation Complete",
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
# EMULATE HANDLER
# ═══════════════════════════════════════════════════════════════════════════

def handle_emulate(
    audio_file: Optional[str],
    ref_url: str,
) -> tuple[str, Optional[str]]:
    """Analyze a reference WAV/URL via the full intake pipeline.

    Returns (status_markdown, report_file_path_or_None).
    """
    has_file = audio_file and Path(audio_file).exists()
    has_url = ref_url and ref_url.strip().startswith("http")

    if not has_file and not has_url:
        return "Upload a WAV file **or** paste a URL to analyze.", None

    try:
        if has_url:
            result = intake_from_url(ref_url.strip())
        else:
            result = intake_from_file(audio_file)  # type: ignore[arg-type]

        dna = result.audio_dna
        song = result.song_dna

        lines = [
            "## Reference Intake — Complete DNA",
            "",
            f"**Source**: `{result.metadata.title or Path(result.local_path).name}`",
            f"**Artist**: {result.metadata.artist or 'Unknown'}",
            "",
            "### Rhythm",
            f"- **BPM**: {dna.rhythm.bpm} "
            f"(confidence {dna.rhythm.bpm_confidence:.2f})",
            f"- Beat Stability: {dna.rhythm.beat_stability:.3f}",
            f"- Swing: {dna.rhythm.swing_ratio:.3f}",
            f"- Onset Rate: {dna.rhythm.onset_rate:.1f}/s",
            "",
            "### Harmony",
            f"- **Key**: {dna.harmonic.key} "
            f"(confidence {dna.harmonic.key_confidence:.2f})",
            f"- Chroma Entropy: {dna.harmonic.chroma_entropy:.3f}",
            f"- Dissonance: {dna.harmonic.dissonance:.3f}",
            "",
            "### Spectral Balance",
            f"- Sub: {dna.spectral.sub:.3f}  |  Bass: {dna.spectral.bass:.3f}",
            f"- Low-Mid: {dna.spectral.low_mid:.3f}  |  Mid: {dna.spectral.mid:.3f}",
            f"- High-Mid: {dna.spectral.high_mid:.3f}  |  High: {dna.spectral.high:.3f}",
            f"- Centroid: {dna.spectral.centroid_hz:.0f} Hz",
            f"- Flatness: {dna.spectral.flatness:.3f}",
            f"- Tilt: {dna.spectral.tilt_db_per_oct:.1f} dB/oct",
            "",
            "### Loudness",
            f"- LUFS: {dna.loudness.lufs_estimate:.1f}",
            f"- Peak: {dna.loudness.peak_db:.1f} dB",
            f"- Crest Factor: {dna.loudness.crest_factor_db:.1f} dB",
            f"- Dynamic Range: {dna.loudness.dynamic_range_db:.1f} dB",
            "",
            "### Arrangement",
            f"- Duration: {dna.arrangement.duration_s:.1f}s",
            f"- Sections: {dna.arrangement.n_sections} "
            f"({', '.join(dna.arrangement.section_labels)})",
            f"- Drops: {dna.arrangement.drop_count}",
            f"- Intro→Drop Contrast: {dna.arrangement.intro_drop_contrast_db:.1f} dB",
            f"- Arc: {dna.arrangement.energy_arc_type}",
            "",
            "### Stereo",
            f"- Width: {dna.stereo.width:.3f}",
            f"- Mono Compat: {dna.stereo.mono_compat:.3f}",
            f"- Correlation: {dna.stereo.correlation:.3f}",
            "",
            "### Bass",
            f"- Sub Weight: {dna.bass.sub_weight:.3f}",
            f"- Fundamental: {dna.bass.fundamental_hz:.1f} Hz",
            f"- Wobble Rate: {dna.bass.wobble_rate_hz:.2f} Hz",
            f"- Wobble Depth: {dna.bass.wobble_depth:.3f}",
            f"- Sidechain Pumps: {dna.bass.sidechain_pump_count}",
            "",
            "### Production",
            f"- Transient Sharpness: {dna.production.transient_sharpness:.3f}",
            f"- Reverb: {dna.production.reverb_amount:.3f}",
            f"- Sidechain Depth: {dna.production.sidechain_depth_db:.1f} dB",
            f"- Compression: {dna.production.compression_ratio:.2f}:1",
            f"- Distortion: {dna.production.distortion_amount:.3f}",
            "",
            "### Style",
            f"- Aggression: {dna.style.aggression:.3f}",
            f"- Darkness: {dna.style.darkness:.3f}",
            f"- Energy: {dna.style.energy_level:.3f}",
            f"- Brightness: {dna.style.brightness:.3f}",
            f"- Density: {dna.style.density:.3f}",
            "",
            "### Chords Detected",
            f"- Progression: {' → '.join(result.chords.chords[:8]) or 'N/A'}",
            f"- Confidence: {result.chords.confidence:.2f}",
            "",
            "### Synth Character (Bass Layer)",
            f"- Waveform: {result.bass_synth.estimated_waveform}",
            f"- Filter Cutoff: {result.bass_synth.filter_cutoff_est:.2f}",
            f"- Mod Rate: {result.bass_synth.mod_rate_hz:.1f} Hz",
            f"- Mod Depth: {result.bass_synth.mod_depth:.3f}",
            f"- Distortion: {result.bass_synth.distortion_amount:.3f}",
            "",
        ]

        # ── SongDNA summary ──
        if song:
            lines.extend([
                "---",
                "## Derived SongDNA",
                "",
                f"- **Name**: {song.name}",
                f"- **Style**: {song.style}",
                f"- **Mood**: {song.mood_name}",
                f"- **BPM**: {song.bpm}",
                f"- **Key**: {song.key} {song.scale}",
                f"- **Total Bars**: {song.total_bars}",
                f"- **Bass Type**: {song.bass.primary_type}",
                "",
            ])

        # ── Save report ──
        report_path = save_intake_report(result)
        lines.append(f"**Report saved**: `{report_path}`")

        return "\n".join(lines), str(report_path)

    except Exception as e:
        return (
            f"**Intake failed**: {e}\n```\n{traceback.format_exc()}\n```",
            None,
        )


# ═══════════════════════════════════════════════════════════════════════════
# GRADIO UI BUILDER
# ═══════════════════════════════════════════════════════════════════════════

THEME_CSS = """
body { font-family: 'Courier New', monospace; }
.gradio-container { max-width: 1200px; }
h1 { color: #a855f7; }
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


def build_ui() -> Any:
    """Build the unified 13-tab Gradio UI."""
    _require_gradio()

    with gr.Blocks(title="DUBFORGE -- Unified Studio") as app:

        gr.HTML(
            '<div class="dubforge-header">'
            "<h1>DUBFORGE</h1>"
            "<p>Unified Studio -- Taste Analyzer + Song Builder + "
            "Track Emulator</p>"
            "</div>"
        )

        with gr.Tabs():

            # ══════════════════════════════════════════════════════════
            # ANALYZER TABS (1-6)
            # ══════════════════════════════════════════════════════════

            # ── TAB 1: Auto-Analyze Likes ──
            with gr.TabItem("1. Auto-Analyze Likes"):
                gr.Markdown(
                    "### One-Click SoundCloud Likes Analyzer\n"
                    "Automatically fetches **all** your SoundCloud likes, "
                    "downloads them, separates stems, and builds your "
                    "taste profile.\n\n"
                    "**Requires:** Cookie auth -- either from your browser "
                    "(must be logged in to SoundCloud) or via a "
                    "**cookies.txt** file upload."
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        auto_browser = gr.Dropdown(
                            choices=["chrome", "firefox", "edge",
                                     "brave", "chromium", "safari", "none"],
                            value="edge",
                            label="Browser (for SoundCloud cookies)",
                            info="Must be logged into SoundCloud in this "
                                 "browser. Set to 'none' if using "
                                 "cookies.txt file instead.",
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
                        "4. Click **Auto-Analyze** -- it auto-detects the "
                        "file\n\n"
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
                    auto_stems = gr.Checkbox(
                        value=True, label="Separate Stems (HT-Demucs)"
                    )
                    auto_blueprints = gr.Checkbox(
                        value=True, label="Generate Serum Blueprints"
                    )
                    auto_skip = gr.Checkbox(
                        value=True, label="Skip Already-Analyzed Tracks"
                    )

                auto_btn = gr.Button(
                    "Auto-Analyze All My Likes", variant="primary"
                )
                auto_output = gr.Markdown(label="Progress")
                auto_report = gr.Textbox(label="Report path", visible=False)

                auto_btn.click(
                    fn=handle_auto_likes,
                    inputs=[auto_browser, auto_max, auto_stems,
                            auto_blueprints, auto_skip, auto_cookies_file],
                    outputs=[auto_output, auto_report],
                )

            # ── TAB 2: SoundCloud Sources ──
            with gr.TabItem("2. SoundCloud Sources"):
                gr.Markdown(
                    "### Analyze SoundCloud Sources\n"
                    "Paste one or more SoundCloud URLs -- separate with "
                    "spaces or new lines.\n\n"
                    "| URL type | Example |\n"
                    "|---|---|\n"
                    "| Your likes | "
                    "`https://soundcloud.com/you/likes` |\n"
                    "| Artist tracks | "
                    "`https://soundcloud.com/substandardbassmusic` |\n"
                    "| Playlist / set | "
                    "`https://soundcloud.com/user/sets/set-name` |\n"
                )

                with gr.Row():
                    with gr.Column(scale=3):
                        sc_urls = gr.Textbox(
                            label="SoundCloud URLs (one per line)",
                            placeholder=(
                                "https://soundcloud.com/you/likes\n"
                                "https://soundcloud.com/"
                                "substandardbassmusic"
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
                    sc_stems = gr.Checkbox(
                        value=True, label="Separate Stems (HT-Demucs)"
                    )
                    sc_blueprints = gr.Checkbox(
                        value=True, label="Generate Serum Blueprints"
                    )

                sc_btn = gr.Button("Analyze Sources", variant="primary")
                sc_output = gr.Markdown(label="Results")
                sc_report = gr.Textbox(label="Report path", visible=False)

                sc_btn.click(
                    fn=handle_soundcloud_analysis,
                    inputs=[sc_urls, sc_max, sc_browser,
                            sc_stems, sc_blueprints],
                    outputs=[sc_output, sc_report],
                )

            # ── TAB 3: Local Files ──
            with gr.TabItem("3. Local Files"):
                gr.Markdown(
                    "### Analyze Local Audio Files\n"
                    "Upload WAV/FLAC/MP3 files directly."
                )

                local_files = gr.Files(
                    label="Upload Audio Files",
                    file_types=["audio"],
                )

                with gr.Row():
                    local_stems = gr.Checkbox(
                        value=False,
                        label="Separate Stems (requires demucs)",
                    )
                    local_blueprints = gr.Checkbox(
                        value=True, label="Generate Blueprints"
                    )

                local_btn = gr.Button("Analyze Files", variant="primary")
                local_output = gr.Markdown(label="Results")
                local_report = gr.Textbox(
                    label="Report path", visible=False
                )

                local_btn.click(
                    fn=handle_local_analysis,
                    inputs=[local_files, local_stems, local_blueprints],
                    outputs=[local_output, local_report],
                )

            # ── TAB 4: Taste Profile ──
            with gr.TabItem("4. Taste Profile"):
                gr.Markdown(
                    "### Your Personal Taste Profile\n"
                    "Averaged prototype vectors across all analyzed "
                    "reference tracks."
                )

                load_btn = gr.Button("Load Profile")

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

            # ── TAB 5: Serum Blueprints ──
            with gr.TabItem("5. Serum Blueprints"):
                gr.Markdown(
                    "### Serum 2 Preset Blueprints\n"
                    "Browse generated blueprints with Lorenz/Rossler "
                    "recommendations."
                )

                with gr.Row():
                    bp_track_filter = gr.Textbox(
                        label="Filter by track name (optional)",
                        placeholder="",
                        lines=1,
                    )
                    bp_load_btn = gr.Button("Load Blueprints")

                bp_output = gr.Markdown(label="Blueprints")

                bp_load_btn.click(
                    fn=handle_load_blueprints,
                    inputs=[bp_track_filter],
                    outputs=[bp_output],
                )

            # ── TAB 6: Feedback Loop ──
            with gr.TabItem("6. Feedback"):
                gr.Markdown(
                    "### Teach the System Your Taste\n"
                    "Give thumbs up/down to refine the prototype vectors."
                )

                gr.Markdown(
                    "After feedback, prototypes will be rebuilt using "
                    "only thumbs-up tracks for more accurate style "
                    "matching.\n\n"
                    "*Full prototype rebuild requires re-running the "
                    "pipeline.*"
                )

                fb_track = gr.Textbox(
                    label="Track Name",
                    placeholder="Enter track name as shown in the profile",
                )
                fb_thumbs = gr.Radio(
                    choices=["thumbs-up", "thumbs-down"],
                    label="Feedback",
                )
                fb_btn = gr.Button("Submit Feedback")
                fb_output = gr.Markdown()

                fb_btn.click(
                    fn=handle_feedback,
                    inputs=[fb_track, fb_thumbs],
                    outputs=[fb_output],
                )

            # ══════════════════════════════════════════════════════════
            # LAUNCHPAD TABS (7-11)
            # ══════════════════════════════════════════════════════════

            # ── TAB 7: Idea Sandbox ──
            with gr.TabItem("7. Idea Sandbox"):
                gr.Markdown(
                    "### Define Your Track\n"
                    "Set core parameters. Everything else is derived "
                    "from these inputs via phi ratios and the SongDNA "
                    "engine."
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        song_name = gr.Textbox(
                            label="Song Name",
                            placeholder="e.g. CYCLOPS FURY, HOLLOW POINT",
                            info="Semantic words drive sound design via "
                                 "81 WORD_ATOMS",
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
                                placeholder="dark, aggressive, euphoric",
                                info="14 moods + 20 aliases + blending",
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
                                minimum=100, maximum=200, step=1,
                                value=150, label="BPM",
                                info="0 = auto from style",
                            )
                        with gr.Row():
                            arrangement = gr.Dropdown(
                                choices=["(auto)"] + ARRANGEMENT_OPTIONS,
                                value="(auto)",
                                label="Arrangement Template",
                                info="weapon / emotive / hybrid / "
                                     "fibonacci",
                            )
                            tags_input = gr.Textbox(
                                label="Tags",
                                placeholder="heavy, festival, crowd-killer",
                                info="Comma-separated tags",
                            )
                        artist_notes = gr.Textbox(
                            label="Artist Notes",
                            placeholder="Free-form: vibe, reference "
                                        "tracks, ideas...",
                            lines=3,
                        )
                    with gr.Column(scale=1):
                        gr.Markdown("### Mood Preview")
                        mood_preview = gr.Markdown(
                            "_Enter a mood to preview_"
                        )
                        mood_btn = gr.Button(
                            "Preview Mood", variant="secondary"
                        )

                mood_btn.click(
                    fn=handle_mood_preview,
                    inputs=[mood, bpm],
                    outputs=[mood_preview],
                )
                mood.change(
                    fn=handle_mood_preview,
                    inputs=[mood, bpm],
                    outputs=[mood_preview],
                )

            # ── TAB 8: Arrangement ──
            with gr.TabItem("8. Arrangement"):
                gr.Markdown(
                    "### Arrangement Blueprint\n"
                    "Preview song structure with energy curve "
                    "visualization. Energy curves derive directly "
                    "from DNA arrangement section intensity."
                )
                with gr.Row():
                    arr_type = gr.Dropdown(
                        choices=ARRANGEMENT_OPTIONS,
                        value="weapon",
                        label="Arrangement Type",
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
                    inputs=[arr_type, arr_bpm, arr_key],
                    outputs=[arr_info, arr_plot],
                )

            # ── TAB 9: Sample Packs ──
            with gr.TabItem("9. Sample Packs"):
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
                    fn=handle_sample_scan, inputs=[], outputs=[sample_info],
                )
                download_btn.click(
                    fn=handle_download_starter_pack,
                    inputs=[], outputs=[download_status],
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
                    inputs=[cat_dropdown], outputs=[cat_output],
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
                    inputs=[search_input], outputs=[search_output],
                )

                gr.Markdown("### GALATCIA Collection")
                galatcia_btn = gr.Button(
                    "Browse GALATCIA Presets & Samples",
                    variant="secondary",
                )
                galatcia_output = gr.Markdown("")
                galatcia_btn.click(
                    fn=handle_browse_galatcia,
                    inputs=[], outputs=[galatcia_output],
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

            # ── TAB 10: Serum 2 Patches ──
            with gr.TabItem("10. Serum 2 Patches"):
                gr.Markdown(
                    "### DUBFORGE Serum 2 Patches\n"
                    "8 phi-derived patches for bass, lead, pad, and FX. "
                    "Each preset is generated as .fxp during Phase 1."
                )
                patch_lines = []
                for p in _DUBSTEP_PATCHES:
                    pname = p.get("name", "?")
                    pcat = p.get("category", "")
                    desc = ", ".join(p.get("tags", [])[:5])
                    patch_lines.append(
                        f"- **{pname}** ({pcat}) -- {desc}"
                    )
                gr.Markdown(
                    "\n".join(patch_lines)
                    if patch_lines else "_No patches found_"
                )

            # ── TAB 11: FORGE IT ──
            with gr.TabItem("11. FORGE IT"):
                gr.Markdown(
                    "### Launch Phase 1: Generation\n"
                    "Generate SongDNA, Serum 2 presets, MIDI, and ALS "
                    "from the parameters defined in the Idea Sandbox.\n\n"
                    "**This creates everything needed for Phase 2: "
                    "Arrangement.**"
                )
                forge_btn = gr.Button(
                    "FORGE IT", variant="primary", size="lg",
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
                        song_name, style, mood, key, scale, bpm,
                        arrangement, tags_input, artist_notes,
                    ],
                    outputs=[forge_status, dna_output, file_output],
                )

            # ══════════════════════════════════════════════════════════
            # EMULATE TAB (12)
            # ══════════════════════════════════════════════════════════

            # ── TAB 12: EMULATE ──
            with gr.TabItem("12. EMULATE"):
                gr.Markdown(
                    "### Reference Intake\n"
                    "Upload a WAV file **or** paste a URL (SoundCloud, "
                    "YouTube, etc.) and DUBFORGE will run the full "
                    "intake pipeline: deep audio DNA extraction, chord/"
                    "melody/synth-character analysis, and SongDNA "
                    "mapping.\n\n"
                    "**File**: WAV (16/24/32-bit) &nbsp; | &nbsp; "
                    "**URL**: anything yt-dlp supports"
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        emu_audio = gr.Audio(
                            label="Reference Track (WAV)",
                            type="filepath",
                        )
                    with gr.Column(scale=1):
                        emu_url = gr.Textbox(
                            label="Reference URL",
                            placeholder="https://soundcloud.com/artist/track",
                            info="Paste a SoundCloud/YouTube URL "
                                 "(requires yt-dlp)",
                        )

                emu_btn = gr.Button(
                    "Analyze Reference", variant="primary", size="lg"
                )

                emu_status = gr.Markdown(
                    "_Upload a WAV or paste a URL to begin_"
                )
                emu_download = gr.File(
                    label="Download Intake Report", visible=True
                )

                def _run_emulate(audio_file: Any, url: str) -> tuple:
                    status, path = handle_emulate(audio_file, url)
                    return status, path

                emu_btn.click(
                    fn=_run_emulate,
                    inputs=[emu_audio, emu_url],
                    outputs=[emu_status, emu_download],
                )

            # ══════════════════════════════════════════════════════════
            # PIPELINE TAB (13)
            # ══════════════════════════════════════════════════════════

            # ── TAB 13: Pipeline ──
            with gr.TabItem("13. Pipeline"):
                gr.Markdown(
                    """### DUBFORGE 4-Phase Production Pipeline

```
INPUT: Song Idea (name, mood, key, BPM, style, energy)
         |
   +-----v-----------------------------------------------+
   |  PHASE 1: GENERATION -- "The Idea Sandbox"          |
   |  Sound design + sample selection + preset creation   |
   |  OUTPUT: Sound palette (FXP, WAV, ADG, MIDI)        |
   +-----+-----------------------------------------------+
         | sounds + samples ready
   +-----v-----------------------------------------------+
   |  PHASE 2: ARRANGEMENT -- "The Creation Session"     |
   |  Ableton Session #1: full song structure             |
   |  INTRO > BUILD > DROP > BREAK > DROP 2 > OUTRO      |
   |  OUTPUT: Mix stems (24-bit WAV)                      |
   +-----+-----------------------------------------------+
         | stems exported
   +-----v-----------------------------------------------+
   |  PHASE 3: MIXING -- "The Mix Session"               |
   |  Ableton Session #2: EQ, compress, spatial, balance  |
   |  OUTPUT: Mixed stems (24-bit WAV)                    |
   +-----+-----------------------------------------------+
         | mixed stems exported
   +-----v-----------------------------------------------+
   |  PHASE 4: MASTERING -- "The Master Session"         |
   |  Ableton Session #3: multiband, limiting, LUFS      |
   |  OUTPUT: Final WAV -- DANCEFLOOR BANGER              |
   +----------------------------------------------------- +
```

### Doctrine Constants
- **PHI** = {phi:.10f}
- **A4_432** = {a4} Hz
- **Fibonacci** = {fib}
""".format(phi=PHI, a4=A4_432, fib=str(FIBONACCI[:13]))
                )

        gr.Markdown(
            "---\n*DUBFORGE v4.0.0 -- Planck x phi Fractal "
            "Basscraft Engine -- Unified Studio*"
        )

    return app


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DUBFORGE Unified Studio Web UI",
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Server port"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Server host"
    )
    parser.add_argument(
        "--share", action="store_true", help="Create public Gradio link"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser"
    )
    args = parser.parse_args()

    if not HAS_GRADIO:
        print("Gradio not installed.")
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
