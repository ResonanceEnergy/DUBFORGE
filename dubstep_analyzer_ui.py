"""
DUBFORGE -- Reference Intake Studio

Gradio web interface built around engine/reference_intake.py.
Paste a URL or upload a WAV -> full audio DNA extraction, chord/melody/
synth-character analysis, web research, and SongDNA mapping.

Single-page layout with sections:
    SIGNAL CAPTURE   -- URL or WAV input, run pipeline
    ANALYSIS RESULTS -- Summary + accordion details (DNA, chords, synth, web, genome)
    FORGE EMULATION  -- Parameters + FORGE IT with live progress window
    ARCHIVE          -- Browse saved intake reports

Usage:
    python forge.py --launch --ui-only   # canonical entrypoint
    python dubstep_analyzer_ui.py
    python dubstep_analyzer_ui.py --port 7861 --share
"""

from __future__ import annotations

import argparse
import json
import logging
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

# ── File logging (logs/ directory) ───────────────────────────────────────────
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)
_RUN_LOG  = _LOG_DIR / "dubforge_run.log"
_ERR_LOG  = _LOG_DIR / "dubforge_errors.log"

_logger = logging.getLogger("dubforge")
_logger.setLevel(logging.DEBUG)
_logger.propagate = False

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_run_handler = logging.FileHandler(_RUN_LOG, encoding="utf-8")
_run_handler.setLevel(logging.DEBUG)
_run_handler.setFormatter(_fmt)

_err_handler = logging.FileHandler(_ERR_LOG, encoding="utf-8")
_err_handler.setLevel(logging.ERROR)
_err_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_fmt)

for _h in (_run_handler, _err_handler, _console_handler):
    _logger.addHandler(_h)

_logger.info("=" * 60)
_logger.info("DUBFORGE UI starting — run log: %s | error log: %s", _RUN_LOG, _ERR_LOG)
_logger.info("=" * 60)

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    gr = None  # type: ignore[assignment]

gr: Any  # type: ignore[no-redef]

try:
    import matplotlib  # type: ignore[import-not-found]
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    HAS_MPL = True
except ImportError:
    plt = None  # type: ignore[assignment]
    HAS_MPL = False

import math
import os
import signal
import subprocess
import time
import numpy as np

# ── Active forge subprocess (killed on every new forge button press) ──────────
_forge_proc: "subprocess.Popen[str] | None" = None
# Phase-state caches — persist across the four phase generator functions
_forge_p1: dict = {}
_forge_p2: dict = {}
_forge_p3: dict = {}
_forge_files: "list[dict]" = []    # accumulated __FILE_READY__ entries
_forge_song_name: str = ""          # song name used by gate handlers
_run_log_lines:   "list[str]" = []  # all forge stdout lines (all phases)
_error_log_lines: "list[str]" = []  # error/warning lines

from engine.config_loader import (
    A4_432, CPU_CORES, FIBONACCI, IS_APPLE_SILICON, PHI,
    WORKERS_COMPUTE, WORKERS_IO,
)
from engine.reference_intake import (
    IntakeResult,
    intake_from_file,
    intake_from_url,
    save_intake_report,
)
from engine.variation_engine import (
    BPM_RANGES,
    NOTES,
    SCALE_INTERVALS,
    forge_song_dna,
    save_dna,
)
from engine.arrangement_sequencer import (
    arrangement_duration_s,
    arrangement_energy_curve,
    arrangement_total_bars,
    build_arrangement,
    golden_section_check,
)
from engine.audio_preview import render_preview, preview_to_dict
from engine.batch_renderer import ALL_BATCH_BANKS, export_batch_renders_parallel
from engine.chord_progression import build_progression
from engine.galatcia import catalog_galatcia
from engine.render_pipeline import ALL_PIPELINE_BANKS, export_pipeline_stems_parallel
from engine.rco import (
    generate_energy_curve,
    subtronics_emotive_preset,
    subtronics_hybrid_preset,
    subtronics_weapon_preset,
)
from engine.sample_library import CATEGORIES as SAMPLE_CATEGORIES, SampleLibrary
from engine.serum2 import build_dubstep_patches
from engine.session_template import (
    build_dubstep_session,
    get_template_requirements,
    TRACK_MODULES,
    GAP_MODULE_TRACKS,
)
from engine.fxp_writer import FXPPreset, write_fxp, read_fxp
from engine.als_generator import ALSProject, ALSScene, ALSTrack, write_als
from engine.midi_export import NoteEvent, write_midi_file
from engine.mood_engine import MOODS, MOOD_ALIASES, get_mood_suggestion, resolve_mood
from engine.dsp_core import SAMPLE_RATE
from engine.sidechain import (
    ALL_SIDECHAIN_BANKS,
    SidechainPreset,
    generate_sidechain,
)
from engine.mastering_chain import estimate_lufs

OUTPUT_ROOT = Path(__file__).parent / "output"
REPORTS_DIR = OUTPUT_ROOT / "reference_intake" / "reports"

_DUBSTEP_PATCHES: list[dict] = []
try:
    _DUBSTEP_PATCHES = build_dubstep_patches()
except Exception:
    pass

STYLE_OPTIONS = list(BPM_RANGES.keys())
MOOD_OPTIONS = sorted(MOODS.keys())
SCALE_OPTIONS = sorted(SCALE_INTERVALS.keys())
KEY_OPTIONS = list(NOTES)
ARRANGEMENT_OPTIONS = ["weapon", "emotive", "hybrid", "fibonacci"]
ENERGY_PRESETS = ["weapon", "emotive", "hybrid"]
SERUM_PATCH_NAMES = [p.get("name", f"Patch {i}") for i, p in enumerate(_DUBSTEP_PATCHES)]

PREVIEW_MODULES = [
    "sub_bass", "wobble_bass", "lead_synth", "pad_synth",
    "drum_generator", "perc_synth", "riser_synth", "impact_hit",
    "noise_generator", "arp_synth", "granular_synth", "pluck_synth",
    "drone_synth", "formant_synth", "glitch_engine", "riddim_engine",
    "vocal_chop", "fm_synth", "additive_synth", "supersaw",
]

QUICK_MODULES = [
    "phi_core", "rco", "psbs", "serum2", "midi_export", "drum_generator",
    "bass_oneshot", "lead_synth", "pad_synth", "mastering_chain",
    "arrangement_sequencer", "render_pipeline", "batch_renderer",
]

SIDECHAIN_SHAPES = list(ALL_SIDECHAIN_BANKS.keys())
MIX_MODELS = ["Priority-Based", "Camera Focus", "Depth Staging"]

# ── WAV helpers ───────────────────────────────────────────────────────────────
import io
import wave as _wave_mod
import base64
import struct


def _signal_to_wav_bytes(signal: np.ndarray, sr: int = 44100) -> bytes:
    buf = io.BytesIO()
    pcm = np.clip(signal, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    ch = 2 if pcm.ndim == 2 else 1
    with _wave_mod.open(buf, "w") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _require_gradio() -> None:
    if not HAS_GRADIO:
        raise ImportError("Gradio not installed. Run: pip install gradio")


_last_intake: IntakeResult | None = None


def handle_intake(
    audio_file: Optional[str],
    ref_url: str,
    do_research: bool = True,
) -> tuple:  # 16-tuple of intake results + forge defaults + mastering ref URL
    """Run the full intake pipeline.

    Research is ALWAYS enabled for URL inputs — the checkbox is kept
    only for backwards compatibility but URL intake forces research=True
    so that web research data feeds into artwork, reference mastering,
    and mood selection automatically.
    """
    global _last_intake

    has_file = audio_file and Path(audio_file).exists()
    has_url = ref_url and ref_url.strip().startswith("http")

    if not has_file and not has_url:
        empty = "_Paste a URL to begin — all modules auto-populate from the reference._"
        return (empty, "", "", "", "", "", None,
                "", "dubstep", "", "(auto)", "(auto)", 150, "", "",
                "")  # last = master_ref_url

    try:
        if has_url:
            # Always research when URL is provided — this is the central
            # data source that cascades into forge, artwork, mastering, etc.
            result = intake_from_url(ref_url.strip(), research=True)
        else:
            result = intake_from_file(audio_file)  # type: ignore[arg-type]  # guarded by has_file

        _last_intake = result

        summary = _format_summary(result)
        audio_dna = _format_audio_dna(result)
        chords_melody = _format_chords_melody(result)
        synth = _format_synth_character(result)
        web = _format_web_research(result)
        song_dna_json = _format_song_dna(result)

        report_path = save_intake_report(result)

        forge_defaults = _derive_forge_defaults(result)

        # Cascade the reference URL to the mastering section for
        # reference-matched loudness targeting
        ref_url_out = ref_url.strip() if has_url else ""

        return (summary, audio_dna, chords_melody, synth, web,
                song_dna_json, str(report_path)) + forge_defaults + (ref_url_out,)

    except Exception as e:
        err = f"**Intake failed**: {e}\n```\n{traceback.format_exc()}\n```"
        return (err, "", "", "", "", "", None,
                "", "dubstep", "", "(auto)", "(auto)", 150, "", "",
                "")


def _format_summary(r: IntakeResult) -> str:
    dna = r.audio_dna
    song = r.song_dna
    title = r.metadata.title or Path(r.local_path).stem
    artist = r.metadata.artist or "Unknown"
    lines = [
        f"## {title}",
        f"**Artist**: {artist}",
        "",
        "### Quick View",
        "| Field | Value |",
        "|-------|-------|",
        f"| BPM | {dna.rhythm.bpm} (confidence {dna.rhythm.bpm_confidence:.2f}) |",
        f"| Key | {dna.harmonic.key} (confidence {dna.harmonic.key_confidence:.2f}) |",
        f"| Duration | {dna.arrangement.duration_s:.1f}s ({dna.arrangement.duration_s / 60:.1f} min) |",
        f"| Sections | {dna.arrangement.n_sections} ({', '.join(dna.arrangement.section_labels[:6])}) |",
        f"| Drops | {dna.arrangement.drop_count} |",
        f"| LUFS | {dna.loudness.lufs_estimate:.1f} |",
        f"| Dynamic Range | {dna.loudness.dynamic_range_db:.1f} dB |",
        f"| Stereo Width | {dna.stereo.width:.3f} |",
        f"| Sub Weight | {dna.bass.sub_weight:.3f} |",
        f"| Aggression | {dna.style.aggression:.3f} |",
        f"| Energy | {dna.style.energy_level:.3f} |",
        f"| Darkness | {dna.style.darkness:.3f} |",
        "",
        "### Chords",
        f"**Progression**: {' -> '.join(r.chords.chords[:8]) or 'N/A'} "
        f"(confidence {r.chords.confidence:.2f})",
        "",
        "### Bass Synth",
        f"**Waveform**: {r.bass_synth.estimated_waveform} | "
        f"**Filter**: {r.bass_synth.filter_cutoff_est:.2f} | "
        f"**Wobble**: {r.bass_synth.mod_rate_hz:.1f} Hz @ {r.bass_synth.mod_depth:.2f}",
    ]
    if song:
        lines.extend([
            "",
            "### Derived SongDNA",
            f"**Style**: {song.style} | **Mood**: {song.mood_name} | "
            f"**BPM**: {song.bpm} | **Key**: {song.key} {song.scale}",
            f"**Total Bars**: {song.total_bars} | "
            f"**Bass Type**: {song.bass.primary_type}",
        ])
    if r.metadata.url:
        lines.extend(["", f"**Source**: `{r.metadata.url}`"])
    return "\n".join(lines)


def _format_audio_dna(r: IntakeResult) -> str:
    dna = r.audio_dna
    lines = [
        "## Audio DNA -- 13-Category Analysis", "",
        "### 1. Rhythm",
        "| Metric | Value |", "|--------|-------|",
        f"| BPM | {dna.rhythm.bpm} |",
        f"| BPM Confidence | {dna.rhythm.bpm_confidence:.3f} |",
        f"| Beat Stability | {dna.rhythm.beat_stability:.3f} |",
        f"| Swing Ratio | {dna.rhythm.swing_ratio:.3f} |",
        f"| Onset Rate | {dna.rhythm.onset_rate:.1f}/s |", "",
        "### 2. Harmonic",
        "| Metric | Value |", "|--------|-------|",
        f"| Key | {dna.harmonic.key} |",
        f"| Key Confidence | {dna.harmonic.key_confidence:.3f} |",
        f"| Chroma Entropy | {dna.harmonic.chroma_entropy:.3f} |",
        f"| Dissonance | {dna.harmonic.dissonance:.3f} |", "",
        "### 3. Spectral Balance",
        "| Band | Energy |", "|------|--------|",
        f"| Sub (<60 Hz) | {dna.spectral.sub:.4f} |",
        f"| Bass (60-250 Hz) | {dna.spectral.bass:.4f} |",
        f"| Low-Mid (250-500 Hz) | {dna.spectral.low_mid:.4f} |",
        f"| Mid (500-2k Hz) | {dna.spectral.mid:.4f} |",
        f"| High-Mid (2k-6k Hz) | {dna.spectral.high_mid:.4f} |",
        f"| High (6k+ Hz) | {dna.spectral.high:.4f} |", "",
        f"**Centroid**: {dna.spectral.centroid_hz:.0f} Hz | "
        f"**Flatness**: {dna.spectral.flatness:.4f} | "
        f"**Tilt**: {dna.spectral.tilt_db_per_oct:.1f} dB/oct", "",
        "### 4. Loudness",
        "| Metric | Value |", "|--------|-------|",
        f"| LUFS Estimate | {dna.loudness.lufs_estimate:.1f} |",
        f"| Peak dB | {dna.loudness.peak_db:.1f} |",
        f"| Crest Factor | {dna.loudness.crest_factor_db:.1f} dB |",
        f"| Dynamic Range | {dna.loudness.dynamic_range_db:.1f} dB |", "",
        "### 5. Arrangement",
        "| Metric | Value |", "|--------|-------|",
        f"| Duration | {dna.arrangement.duration_s:.1f}s |",
        f"| Sections | {dna.arrangement.n_sections} |",
        f"| Labels | {', '.join(dna.arrangement.section_labels)} |",
        f"| Drops | {dna.arrangement.drop_count} |",
        f"| Intro->Drop Contrast | {dna.arrangement.intro_drop_contrast_db:.1f} dB |",
        f"| Energy Arc | {dna.arrangement.energy_arc_type} |", "",
        "### 6. Stereo",
        "| Metric | Value |", "|--------|-------|",
        f"| Width | {dna.stereo.width:.3f} |",
        f"| Mono Compatibility | {dna.stereo.mono_compat:.3f} |",
        f"| Correlation | {dna.stereo.correlation:.3f} |", "",
        "### 7. Bass",
        "| Metric | Value |", "|--------|-------|",
        f"| Sub Weight | {dna.bass.sub_weight:.3f} |",
        f"| Fundamental Hz | {dna.bass.fundamental_hz:.1f} |",
        f"| Wobble Rate | {dna.bass.wobble_rate_hz:.2f} Hz |",
        f"| Wobble Depth | {dna.bass.wobble_depth:.3f} |",
        f"| Sidechain Pumps | {dna.bass.sidechain_pump_count} |", "",
        "### 8. Production",
        "| Metric | Value |", "|--------|-------|",
        f"| Transient Sharpness | {dna.production.transient_sharpness:.3f} |",
        f"| Reverb Amount | {dna.production.reverb_amount:.3f} |",
        f"| Sidechain Depth | {dna.production.sidechain_depth_db:.1f} dB |",
        f"| Compression Ratio | {dna.production.compression_ratio:.2f}:1 |",
        f"| Distortion | {dna.production.distortion_amount:.3f} |", "",
        "### 9. Style",
        "| Metric | Value |", "|--------|-------|",
        f"| Aggression | {dna.style.aggression:.3f} |",
        f"| Darkness | {dna.style.darkness:.3f} |",
        f"| Energy Level | {dna.style.energy_level:.3f} |",
        f"| Brightness | {dna.style.brightness:.3f} |",
        f"| Density | {dna.style.density:.3f} |", "",
        "### 10. Sound Design",
        "| Metric | Value |", "|--------|-------|",
        f"| Attack Sharpness | {dna.sound_design.attack_sharpness:.3f} |",
        f"| Texture Density | {dna.sound_design.texture_density:.3f} |",
        f"| Spectral Movement | {dna.sound_design.spectral_movement:.3f} |",
        f"| Modulation Depth | {dna.sound_design.modulation_depth:.3f} |",
        f"| Modulation Rate | {dna.sound_design.modulation_rate_hz:.1f} Hz |",
        f"| Inharmonicity | {dna.sound_design.inharmonicity:.3f} |",
        f"| Formant Presence | {dna.sound_design.formant_presence:.3f} |",
        f"| Noise Content | {dna.sound_design.noise_content:.3f} |", "",
        "### 11. Mixing",
        "| Metric | Value |", "|--------|-------|",
        f"| Frequency Balance | {dna.mixing.frequency_balance_score:.3f} |",
        f"| Separation | {dna.mixing.separation_score:.3f} |",
        f"| Headroom | {dna.mixing.headroom_db:.1f} dB |",
        f"| Mud Ratio | {dna.mixing.mud_ratio:.3f} |",
        f"| Phase Coherence | {dna.mixing.phase_coherence:.3f} |", "",
        "### 12. Mastering",
        "| Metric | Value |", "|--------|-------|",
        f"| True Peak | {dna.mastering.true_peak_db:.1f} dB |",
        f"| Limiting Transparency | {dna.mastering.limiting_transparency:.3f} |",
        f"| Loudness Consistency | {dna.mastering.loudness_consistency:.3f} |",
        f"| Dynamic Complexity | {dna.mastering.dynamic_complexity:.3f} |",
        f"| Streaming Penalty | {dna.mastering.streaming_loudness_penalty:.1f} dB |", "",
        "### 13. Quality Score",
        "| Metric | Value |", "|--------|-------|",
        f"| Overall | {dna.quality.overall:.1f} |",
        f"| Spectral | {dna.quality.spectral_score:.1f} |",
        f"| Bass | {dna.quality.bass_score:.1f} |",
        f"| Production | {dna.quality.production_score:.1f} |",
        f"| Mixing | {dna.quality.mixing_score:.1f} |",
        f"| Mastering | {dna.quality.mastering_score:.1f} |",
    ]
    return "\n".join(lines)


def _format_chords_melody(r: IntakeResult) -> str:
    lines = [
        "## Chord Progression", "",
        f"**Detected Chords**: {' -> '.join(r.chords.chords[:16]) or 'None'}",
        f"**Roman Numerals**: {' -> '.join(r.chords.progression_roman[:16]) or 'N/A'}",
        f"**Key**: {r.chords.key or r.audio_dna.harmonic.key or 'Unknown'}",
        f"**Scale**: {r.chords.scale or 'minor'}",
        f"**Source**: {r.chords.source or 'audio_analysis'}",
        f"**Confidence**: {r.chords.confidence:.3f}",
        "", "---", "",
        "## Melody Contour", "",
        f"**Contour Shape**: {r.melody.contour or 'N/A'}",
        f"**Phrase Length**: {r.melody.phrase_length_bars} bars",
        f"**Source**: {r.melody.source}",
        f"**Notes Detected**: {len(r.melody.notes)}",
    ]
    if r.melody.scale_degrees:
        degrees_str = ", ".join(str(d) for d in r.melody.scale_degrees[:16])
        lines.append(f"**Scale Degrees**: {degrees_str}")
    if r.melody.notes:
        lines.extend([
            "", "### Melody Notes (first 16)",
            "| Pitch (Hz) | MIDI | Start (s) | Duration (s) |",
            "|------------|------|-----------|--------------|",
        ])
        for n in r.melody.notes[:16]:
            lines.append(
                f"| {n.get('pitch_hz', 0):.1f} | {n.get('midi', 0)} | "
                f"{n.get('start_s', 0):.2f} | {n.get('duration_s', 0):.3f} |"
            )
    return "\n".join(lines)


def _format_synth_character(r: IntakeResult) -> str:
    lines = ["## Synth Character Analysis", ""]
    for label, synth in [
        ("Bass Layer (30-500 Hz)", r.bass_synth),
        ("Lead Layer (200-8k Hz)", r.lead_synth),
        ("Pad Layer (100-12k Hz)", r.pad_synth),
    ]:
        lines.extend([
            f"### {label}",
            "| Parameter | Value |", "|-----------|-------|",
            f"| Waveform | {synth.estimated_waveform} |",
            f"| Harmonic Content | {synth.harmonic_content} |",
            f"| Odd/Even Ratio | {synth.odd_even_ratio:.3f} |",
            f"| Filter Cutoff | {synth.filter_cutoff_est:.3f} |",
            f"| Filter Resonance | {synth.filter_resonance_est:.3f} |",
            f"| Filter Movement | {synth.filter_movement:.3f} |",
            f"| Mod Rate | {synth.mod_rate_hz:.1f} Hz |",
            f"| Mod Depth | {synth.mod_depth:.3f} |",
            f"| Mod Shape | {synth.mod_shape} |",
            f"| Distortion | {synth.distortion_amount:.3f} |",
            f"| Noise Content | {synth.noise_content:.3f} |",
            f"| Formant Presence | {synth.formant_presence:.3f} |",
            f"| Inharmonicity | {synth.inharmonicity:.3f} |", "",
        ])
    return "\n".join(lines)


def _format_web_research(r: IntakeResult) -> str:
    web = r.web_research
    if not web.sources_consulted and not web.production_notes:
        return "_No web research performed. Use a URL with research enabled._"
    lines = [
        "## Web Research Results", "",
        f"**Sources Consulted**: {len(web.sources_consulted)}",
    ]
    if web.production_notes:
        lines.extend(["", "### Production Notes"])
        for note in web.production_notes[:10]:
            lines.append(f"- {note}")
    if web.chord_progressions_found:
        lines.extend(["", "### Chord Progressions Found Online"])
        for ci in web.chord_progressions_found:
            cs = " -> ".join(ci.chords) if ci.chords else "N/A"
            lines.append(f"- {cs} (confidence {ci.confidence:.2f})")
    if web.synth_info:
        lines.extend(["", "### Synth / Sound Design Info"])
        for info in web.synth_info[:10]:
            lines.append(f"- {info}")
    if web.sample_pack_info:
        lines.extend(["", "### Sample Pack Info"])
        for info in web.sample_pack_info[:10]:
            lines.append(f"- {info}")
    if web.genre_tags:
        lines.extend(["", f"### Genre Tags: {', '.join(web.genre_tags)}"])
    if web.similar_tracks:
        lines.extend(["", "### Similar Tracks"])
        for t in web.similar_tracks[:10]:
            lines.append(f"- {t}")
    if web.sources_consulted:
        lines.extend(["", "### Sources"])
        for src in web.sources_consulted[:10]:
            lines.append(f"- `{src}`")
    return "\n".join(lines)


def _format_song_dna(r: IntakeResult) -> str:
    if not r.song_dna:
        return "{}"
    try:
        import numpy as np
        def _convert(obj):
            if isinstance(obj, np.ndarray): return obj.tolist()
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, (set, frozenset)): return list(obj)
            return obj
        return json.dumps(r.song_dna.to_dict(), indent=2, default=_convert)
    except Exception:
        return json.dumps(asdict(r.song_dna), indent=2, default=str)


def _derive_forge_defaults(r: IntakeResult) -> tuple:
    """Extract forge parameters from an intake result."""
    title = r.metadata.title or Path(r.local_path).stem
    name = f"{title} (DUBFORGE EMULATION)"

    dna = r.audio_dna
    det_key = dna.harmonic.key or ""
    det_bpm = round(dna.rhythm.bpm) if dna.rhythm.bpm else 150

    # Derive style from BPM range
    det_style = "dubstep"
    for s, (lo, hi) in BPM_RANGES.items():
        if lo <= det_bpm <= hi:
            det_style = s
            break

    # Derive mood from style metrics
    mood_parts = []
    if dna.style.darkness > 0.6:
        mood_parts.append("dark")
    if dna.style.aggression > 0.6:
        mood_parts.append("aggressive")
    if dna.style.energy_level > 0.7:
        mood_parts.append("energetic")
    if dna.style.brightness > 0.6:
        mood_parts.append("bright")
    if not mood_parts:
        mood_parts.append("balanced")
    det_mood = ", ".join(mood_parts)

    # Scale from song_dna or chords
    det_scale = ""
    if r.song_dna and r.song_dna.scale:
        det_scale = r.song_dna.scale
    elif r.chords.scale:
        det_scale = r.chords.scale

    # Tags from web research
    tags = ", ".join(r.web_research.genre_tags[:5]) if r.web_research.genre_tags else ""

    # Notes
    notes_parts = []
    if r.metadata.artist:
        notes_parts.append(f"Emulation of {r.metadata.artist} - {title}")
    if r.metadata.url:
        notes_parts.append(f"Source: {r.metadata.url}")
    det_notes = "\n".join(notes_parts)

    # Clamp key/scale to valid dropdown values
    key_val = det_key if det_key in KEY_OPTIONS else "(auto)"
    scale_val = det_scale if det_scale in SCALE_OPTIONS else "(auto)"
    style_val = det_style if det_style in STYLE_OPTIONS else "dubstep"
    bpm_val = max(100, min(200, det_bpm))

    return (name, style_val, det_mood, key_val, scale_val, bpm_val, tags, det_notes)


def _build_progress_html(steps, current_step, pct, errors, done=False):
    """Build the live progress window HTML."""
    title = "\u2705 EMULATION COMPLETE" if done else "\u26A1 EMULATION IN PROGRESS"
    bar_color = "#10b981" if done else "#a855f7"
    glow = f"0 0 12px {bar_color}66" if not done else f"0 0 16px #10b98188"
    html = (
        '<div class="df-progress-window">'
        f'<div class="df-progress-title">{title}</div>'
        '<div class="df-progress-bar-wrap">'
        f'<div class="df-progress-bar" style="width:{pct}%;background:{bar_color};'
        f'box-shadow:{glow}"></div>'
        f'<span class="df-progress-pct">{pct}%</span></div>'
        '<div class="df-progress-steps">'
    )
    for i, step_name in enumerate(steps):
        if i < current_step:
            html += f'<div class="df-step df-step-done">\u2705 {step_name}</div>'
        elif i == current_step and not done:
            html += f'<div class="df-step df-step-active">\u23F3 {step_name}...</div>'
        elif done:
            html += f'<div class="df-step df-step-done">\u2705 {step_name}</div>'
        else:
            html += f'<div class="df-step df-step-pending">\u25CB {step_name}</div>'
    html += '</div>'
    if errors:
        html += '<div class="df-error-log"><div class="df-error-title">\u26A0 Error Log</div>'
        for err in errors:
            html += f'<div class="df-error-entry">{err}</div>'
        html += '</div>'
    html += '</div>'
    return html


_FORGE_STEPS = [
    "Validate parameters",                                          # 0
    "Stage 1: IDENTITY — DNA, harmony, arrangement",               # 1
    "Stage 2: MIDI SEQUENCES — notes for all stems",               # 2
    "Stage 3: SYNTH FACTORY — wavetables + mod routes + FX",      # 3
    "Stage 3: Serum 2 presets + stem configs",                     # 4
    "Stage 3: Build render .als",                                  # 5
    "Stage 3: Live bounce (Serum 2 stems via Ableton)",            # 6
    "Stage 4: DRUM FACTORY — samples, 128 Rack, patterns",         # 7
    "Stage 4: Build drum .als + pattern renders",                  # 8
    "Phase 1: SongMandate complete",                               # 9
    "Phase 2: ARRANGEMENT — place stems, write automation",        # 10
    "Phase 3: MIXING — gain staging, bus routing, bounce",         # 11
    "Phase 4: MASTERING — master chain, QA, release",              # 12
]


def handle_forge(
    song_name, style, mood, key, scale, bpm, arrangement,
    tags_text, notes,
):
    """Generator → 11-tuple (progress, files_html, status, dna, waveform, audio,
                             mixx_btn, mix3_btn, master_btn, run_log, error_log).

    Runs Phase 1 only, then stops and shows the MIXX gate button.
    The subprocess stays alive, blocked on stdin waiting for 'GO_PHASE2'.
    """
    global _forge_proc, _forge_p1, _forge_p2, _forge_p3, _forge_files, _forge_song_name

    gr = _gr_module()
    steps = _FORGE_STEPS
    errors: list[str] = []
    # always 11 outputs
    _NO = gr.update(visible=False)

    def _out(prog_html, files_html=None, status="", dna="",
             waveform=None, audio=None,
             mixx=None, mix3=None, master=None):
        return (prog_html,
                files_html or _file_card_html(_forge_files),
                status, dna,
                waveform if waveform is not None else _NO,
                audio,
                mixx if mixx is not None else _NO,
                mix3 if mix3 is not None else _NO,
                master if master is not None else _NO,
                _run_log_html(_run_log_lines),
                _error_log_html(_error_log_lines))

    def prog(step, pct, done=False):
        return _build_progress_html(steps, step, pct, errors, done)

    _logger.info("FORGE START — song=%r style=%r bpm=%s", song_name, style, bpm)

    # ── Reset state ───────────────────────────────────────────────────────
    _forge_p1 = {}; _forge_p2 = {}; _forge_p3 = {}; _forge_files = []
    _forge_song_name = song_name or ""
    _run_log_lines.clear(); _error_log_lines.clear()

    # ── Kill any existing forge subprocess ────────────────────────────────
    if _forge_proc is not None and _forge_proc.poll() is None:
        _logger.info("Killing previous forge process (pid=%s)", _forge_proc.pid)
        try:
            os.kill(_forge_proc.pid, signal.SIGKILL)
            _forge_proc.wait(timeout=5)
        except Exception as _ke:
            _logger.warning("Could not kill previous forge proc: %s", _ke)
        _forge_proc = None

    # ── Step 0: Validate ─────────────────────────────────────────────────
    yield _out(prog(0, 2))
    if not song_name or not song_name.strip():
        errors.append("Song name is required.")
        yield _out(prog(0, 0), status="**Error**: Song name is required.")
        return

    tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
    clean_key = key if key and key != "(auto)" else ""
    clean_scale = scale if scale and scale != "(auto)" else ""
    clean_arr = arrangement if arrangement and arrangement != "(auto)" else ""
    yield _out(prog(0, 8))

    # ── Launch forge subprocess ───────────────────────────────────────────
    _song_dna_dict = None
    if _last_intake is not None and _last_intake.song_dna is not None:
        try:
            _song_dna_dict = _last_intake.song_dna.to_dict()
        except Exception:
            _song_dna_dict = None
    blueprint_json = json.dumps({
        "name":        song_name.strip(),
        "style":       style or "dubstep",
        "mood":        mood or "",
        "key":         clean_key,
        "scale":       clean_scale,
        "bpm":         int(bpm) if bpm else 0,
        "arrangement": clean_arr,
        "tags":        tags,
        "notes":       notes or "",
        "song_dna":    _song_dna_dict,
    }, default=str)

    _runner = Path(__file__).parent / "tools" / "forge_runner.py"
    try:
        _forge_proc = subprocess.Popen(
            [sys.executable, str(_runner)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout pipe
            text=True,
            bufsize=1,                  # line-buffered
            cwd=str(Path(__file__).parent),
            env={**os.environ, "DUBFORGE_UI_MODE": "1"},  # skip live Ableton bounce
        )
        assert _forge_proc.stdin is not None
        _forge_proc.stdin.write(blueprint_json + "\n")
        _forge_proc.stdin.flush()
        # stdin stays open — gate handlers write GO_PHASEn lines to it later
    except Exception as e:
        errors.append(f"Subprocess launch failed: {e}")
        _logger.error("Forge subprocess failed to launch: %s", e, exc_info=True)
        yield _out(prog(0, 0), status=f"**Launch error**: {e}")
        return

    _logger.info("Forge subprocess launched (pid=%s)", _forge_proc.pid)

    _STAGE_MARKERS: list[tuple[str, int, int]] = [
        ("[Stage 1]",   1,  12),
        ("→ 1B DNA",    1,  16),
        ("→ 1H arran",  1,  22),
        ("[Stage 2]",   2,  30),
        ("→ 2A gener",  2,  34),
        ("[Stage 3]",   3,  42),
        ("3B Generat",  3,  48),
        ("3C Modula",   3,  52),
        ("3D FX chai",  3,  54),
        ("3F Presets",  4,  58),
        ("3H+",         4,  62),
        ("3I Build",    5,  68),
        ("3J Live bo",  6,  72),
        ("3K:",         6,  76),
        ("[Stage 4]",   7,  80),
        ("4D complete", 7,  84),
        ("4F Pattern",  7,  86),
        ("4F+ FX chai", 7,  88),
        ("4G Build",    8,  90),
        ("PHASE 1 CO",  9,  95),
    ]

    current_step, current_pct = 1, 10
    yield _out(prog(current_step, current_pct))

    # ── Stream Phase 1 stdout — stop when PHASE1_DONE received ───────────
    assert _forge_proc is not None and _forge_proc.stdout is not None
    for line in _forge_proc.stdout:
        line = line.rstrip("\n")
        _logger.debug("[forge] %s", line)
        _run_log_lines.append(line)

        if line.startswith("__FILE_READY__ "):
            try:
                _forge_files.append(json.loads(line[len("__FILE_READY__ "):]))
            except Exception:
                pass
            yield _out(prog(current_step, current_pct))
            continue

        if line.startswith("__PHASE1_DONE__ "):
            try:
                _forge_p1 = json.loads(line[len("__PHASE1_DONE__ "):])
            except Exception:
                pass
            # ── Gate: show MIXX button, stop generator (subprocess
            #    is now blocked on stdin waiting for GO_PHASE2)
            yield _out(
                prog(9, 100, done=True),
                status=_p1_status(_forge_p1, song_name, errors),
                dna=_forge_p1.get("dna_json", ""),
                mixx=gr.update(visible=True),
            )
            return   # generator ends; _forge_proc stays alive

        if line.startswith("__PHASE1_ERROR__ "):
            try:
                err_data = json.loads(line[len("__PHASE1_ERROR__ "):])
            except Exception:
                err_data = {"error": line}
            errors.append(f"Phase 1 failed: {err_data.get('error', '?')}")
            _error_log_lines.append(f"[P1 ERR] {err_data.get('error', '?')}")
            yield _out(
                prog(current_step, current_pct),
                status=f"**Phase 1 Error**: {err_data.get('error','?')}\n```\n{err_data.get('tb','')}\n```",
            )
            _forge_proc.wait()
            return

        # Plain progress line
        for marker, step_idx, pct in _STAGE_MARKERS:
            if marker in line and (step_idx > current_step or pct > current_pct):
                current_step, current_pct = step_idx, pct
        yield _out(prog(current_step, current_pct))

    # subprocess exited before PHASE1_DONE
    _forge_proc.wait()
    rc = _forge_proc.returncode
    if rc != 0:
        errors.append(f"Forge exited with code {rc}")
        yield _out(prog(current_step, current_pct),
                   status=f"**Forge failed** (exit {rc}). Check logs.")


# ── helpers for the gate functions ───────────────────────────────────────────

def _gr_module():
    """Return the gradio module (already imported by the time handlers run)."""
    import gradio as gr  # noqa: PLC0415
    return gr


def _gate_send(signal_str: str) -> bool:
    """Write a gate signal to the running forge subprocess stdin.  Returns True on success."""
    global _forge_proc
    if _forge_proc is None or _forge_proc.poll() is not None:
        return False
    try:
        assert _forge_proc.stdin is not None
        _forge_proc.stdin.write(signal_str + "\n")
        _forge_proc.stdin.flush()
        return True
    except Exception as exc:
        _logger.warning("Gate send failed: %s", exc)
        return False


_LOG_MAX = 500  # max run-log lines retained in memory


def _esc(s: str) -> str:
    """Minimal HTML escape for log output."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run_log_html(lines: "list[str]") -> str:
    if not lines:
        return '<div class="df-run-log"><span class="df-log-empty">no output yet…</span></div>'
    tail = lines[-_LOG_MAX:]
    rows = "".join(
        f'<div><span class="df-log-ts">[{i+1:04d}]</span>{_esc(l)}</div>'
        for i, l in enumerate(tail)
    )
    return (
        f'<div class="df-run-log" id="df-rl">{rows}</div>'
        '<script>var _rl=document.getElementById("df-rl");if(_rl)_rl.scrollTop=_rl.scrollHeight;</script>'
    )


def _error_log_html(lines: "list[str]") -> str:
    if not lines:
        return '<div class="df-err-log"><span class="df-log-empty">✓ no errors</span></div>'
    rows = "".join(
        f'<div><span class="df-log-ts">[ERR {i+1:03d}]</span>{_esc(l)}</div>'
        for i, l in enumerate(lines)
    )
    return f'<div class="df-err-log">{rows}</div>'


def _base_out(gr, steps, step, pct, errors, done=False):
    """Minimal 11-tuple (all gate buttons hidden, no waveform)."""
    return (
        _build_progress_html(steps, step, pct, errors, done),
        _file_card_html(_forge_files),
        _p1_status(_forge_p1, _forge_song_name, errors),
        _forge_p1.get("dna_json", ""),
        gr.update(visible=False),           # waveform
        None,                                # audio
        gr.update(visible=False),           # mixx_btn
        gr.update(visible=False),           # mix3_btn
        gr.update(visible=False),           # master_btn
        _run_log_html(_run_log_lines),      # run_log_html
        _error_log_html(_error_log_lines),  # error_log_html
    )


def _gate_phase_stream(
    phase_num: int,
    gate: str,
    step: int,
    start_pct: int,
    markers: "list[tuple[str, int, int]]",
    next_btn_idx: int,        # 0=mixx_btn  1=mix3_btn  2=master_btn
    done_note_fn,             # (p_data: dict) -> str
):
    """Shared streaming generator for gate phases 2 and 3.

    Sends the gate signal, streams stdout from the forge subprocess until the
    phase-done or phase-error sentinel arrives, and yields 11-tuples for the
    Gradio UI.  Phase 4 (handle_master) is not used here because it has a
    different completion output (waveform + audio player).
    """
    global _forge_proc, _forge_files, _forge_p2, _forge_p3
    gr = _gr_module()
    steps = _FORGE_STEPS
    errors: list[str] = []
    sentinel_done  = f"__PHASE{phase_num}_DONE__ "
    sentinel_error = f"__PHASE{phase_num}_ERROR__ "
    err_label      = f"[P{phase_num} ERR]"

    if not _gate_send(gate):
        yield _base_out(gr, steps, step, start_pct - 1,
                        ["No active forge process — run FORGE IT first."])
        return

    yield _base_out(gr, steps, step, start_pct, errors)
    current_step, current_pct = step, start_pct + 1

    assert _forge_proc is not None and _forge_proc.stdout is not None
    for line in _forge_proc.stdout:
        line = line.rstrip("\n")
        _logger.debug("[phase%d] %s", phase_num, line)
        _run_log_lines.append(line)

        if line.startswith("__FILE_READY__ "):
            try:
                _forge_files.append(json.loads(line[len("__FILE_READY__ "):]))
            except Exception:
                pass
            yield _base_out(gr, steps, current_step, current_pct, errors)
            continue

        if line.startswith(sentinel_done):
            p_data: dict = {}
            try:
                p_data = json.loads(line[len(sentinel_done):])
            except Exception:
                pass
            if phase_num == 2:
                _forge_p2 = p_data
            else:
                _forge_p3 = p_data
            note = done_note_fn(p_data)
            # Build button visibility: exactly one of [mixx, mix3, master] is True
            btn_vis = [gr.update(visible=(i == next_btn_idx)) for i in range(3)]
            yield (
                _build_progress_html(steps, step, 100, errors, done=True),
                _file_card_html(_forge_files),
                _p1_status(_forge_p1, _forge_song_name, errors) + note,
                _forge_p1.get("dna_json", ""),
                gr.update(visible=False),   # waveform
                None,                        # audio
                *btn_vis,                    # mixx_btn, mix3_btn, master_btn
                _run_log_html(_run_log_lines),
                _error_log_html(_error_log_lines),
            )
            return

        if line.startswith(sentinel_error):
            try:
                err_data = json.loads(line[len(sentinel_error):])
            except Exception:
                err_data = {"error": line}
            errors.append(f"Phase {phase_num} failed: {err_data.get('error', '?')}")
            _error_log_lines.append(f"{err_label} {err_data.get('error', '?')}")
            yield _base_out(gr, steps, step, current_pct, errors)
            _forge_proc.wait()
            return

        for marker, step_idx, pct in markers:
            if marker.lower() in line.lower() and pct > current_pct:
                current_step, current_pct = step_idx, pct
        yield _base_out(gr, steps, current_step, current_pct, errors)

    _forge_proc.wait()


def handle_mixx():
    """Send GO_PHASE2 to the subprocess, stream Phase 2, stop and show MIX3 button."""
    yield from _gate_phase_stream(
        phase_num=2, gate="GO_PHASE2",
        step=10, start_pct=66,
        markers=[
            ("PHASE 2:",       10, 70), ("Live connected", 10, 73), ("Placing",          10, 76),
            ("automation",     10, 80), ("export",         10, 83), ("Phase 2 complete", 10, 87),
        ],
        next_btn_idx=1,   # mix3_btn
        done_note_fn=lambda p: f"\n\n✓ **Phase 2 complete** — {p.get('total_bars', 0)} bars arranged.",
    )


def handle_mix3():
    """Send GO_PHASE3 to subprocess, stream Phase 3, stop and show MASTER button."""
    yield from _gate_phase_stream(
        phase_num=3, gate="GO_PHASE3",
        step=11, start_pct=80,
        markers=[
            ("PHASE 3:",  11, 82), ("bus groups", 11, 85), ("Loading",  11, 88),
            ("Sidechain", 11, 91), ("bounce",     11, 94),
        ],
        next_btn_idx=2,   # master_btn
        done_note_fn=lambda p: (
            f"\n\n✓ **Phase 3 complete** — mix rendered: `{p.get('wav_path', '')}`"
        ),
    )


def handle_master():
    """Send GO_PHASE4 to subprocess, stream Phase 4, show final waveform + player."""
    global _forge_proc, _forge_files
    gr = _gr_module()
    steps = _FORGE_STEPS
    errors: list[str] = []

    if not _gate_send("GO_PHASE4"):
        yield _base_out(gr, steps, 12, 89, ["No active forge process."])
        return

    yield _base_out(gr, steps, 12, 90, errors)

    _P4_MARKERS = [
        ("PHASE 4:",  12, 92), ("QA",        12, 94), ("export",   12, 96),
        ("release",  12, 97), ("Phase 4",   12, 99),
    ]
    current_step, current_pct = 12, 91

    assert _forge_proc is not None and _forge_proc.stdout is not None
    for line in _forge_proc.stdout:
        line = line.rstrip("\n")
        _logger.debug("[phase4] %s", line)
        _run_log_lines.append(line)

        if line.startswith("__FILE_READY__ "):
            try:
                _forge_files.append(json.loads(line[len("__FILE_READY__ "):]))
            except Exception:
                pass
            yield _base_out(gr, steps, current_step, current_pct, errors)
            continue

        if line.startswith("__PHASE4_DONE__ "):
            p4: dict = {}
            try:
                p4 = json.loads(line[len("__PHASE4_DONE__ "):])
            except Exception:
                pass
            out_path = (p4.get("out_path")
                        or _forge_p3.get("wav_path")
                        or next(iter(_forge_p1.get("delivered_paths", [])), None))
            p1_bpm = float(_forge_p1.get("bpm", 150))
            wf_fig = _make_waveform_plot_with_energy(out_path, bpm=p1_bpm)
            final_status = _build_final_status(
                _forge_p1, _forge_p2, _forge_p3, p4,
                _forge_song_name, errors,
            )
            yield (
                _build_progress_html(steps, len(steps), 100, errors, done=True),
                _file_card_html(_forge_files),
                final_status,
                _forge_p1.get("dna_json", ""),
                gr.update(value=wf_fig, visible=wf_fig is not None),  # waveform
                out_path,                                               # audio player
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                _run_log_html(_run_log_lines),
                _error_log_html(_error_log_lines),
            )
            _forge_proc.wait()
            return

        if line.startswith("__PHASE4_ERROR__ "):
            try:
                err_data = json.loads(line[len("__PHASE4_ERROR__ "):])
            except Exception:
                err_data = {"error": line}
            errors.append(f"Phase 4 failed: {err_data.get('error','?')}")
            _error_log_lines.append(f"[P4 ERR] {err_data.get('error','?')}")
            yield _base_out(gr, steps, 12, current_pct, errors)
            _forge_proc.wait()
            return

        for marker, step_idx, pct in _P4_MARKERS:
            if marker.lower() in line.lower() and pct > current_pct:
                current_step, current_pct = step_idx, pct
        yield _base_out(gr, steps, current_step, current_pct, errors)

    _forge_proc.wait()




# ── Status-building helpers used by handle_forge ─────────────────────────────

def _p1_files(p1: dict) -> str:
    als = p1.get("als_paths", [])
    delivered = p1.get("delivered_paths", [])
    return "\n".join(als + delivered)


_FILE_BADGE_MAP = {
    "WAV": "df-badge-wav", "MID": "df-badge-mid", "MIDI": "df-badge-midi",
    "ALS": "df-badge-als", "JSON": "df-badge-json", "XML": "df-badge-xml",
}


def _file_card_html(files: "list[dict]") -> str:
    """Render live build-log HTML from accumulated __FILE_READY__ payloads."""
    if not files:
        return ('<div class="df-file-log">'
                '<div class="df-file-log-header">◈ BUILD LOG — waiting for outputs…</div>'
                '</div>')
    cards = []
    for f in files:
        kind = f.get("kind", "FILE").upper()
        badge_cls = _FILE_BADGE_MAP.get(kind, "df-badge-json")
        kb = f.get("size_kb", 0)
        size_str = f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"
        ph = f.get("phase", 1)
        cards.append(
            f'<div class="df-file-card">'
            f'<span class="df-file-badge {badge_cls}">{kind}</span>'
            f'<span class="df-file-name">{f.get("name","")}</span>'
            f'<span class="df-file-size">{size_str}</span>'
            f'<span class="df-file-phase">P{ph}</span>'
            f'</div>'
        )
    header = (f'<div class="df-file-log-header">'
              f'\u25c8 BUILD LOG \u2014 {len(cards)} file(s)</div>')
    return f'<div class="df-file-log">{header}{"" .join(cards)}</div>'


def _make_waveform_plot(out_path: "str | None") -> "Any":
    """Generate a waveform matplotlib figure from the final mastered WAV."""
    if not out_path or not Path(out_path).exists():
        return None
    if not HAS_MPL:
        return None
    try:
        import wave as _wave
        with _wave.open(out_path, "rb") as wf:
            n_frames = wf.getnframes()
            sw = wf.getsampwidth()
            nch = wf.getnchannels()
            raw = wf.readframes(min(n_frames, 480_000))
        if sw == 2:
            samp = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sw == 4:
            samp = np.frombuffer(raw, dtype=np.float32)
        else:
            samp = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
        if nch == 2:
            samp = samp[::2]  # left channel only
        # Downsample to ~3000 pts for performance
        N = len(samp)
        if N > 3000:
            step = max(1, N // 3000)
            samp = samp[::step]
        x = np.linspace(0.0, 1.0, len(samp))
        assert plt is not None
        fig, ax = plt.subplots(figsize=(14, 3))
        fig.set_facecolor("#050510")
        ax.set_facecolor("#030312")
        ax.plot(x, samp, color="#a855f7", linewidth=0.4, alpha=0.85)
        ax.fill_between(x, samp, 0.0, alpha=0.11, color="#a855f7")  # type: ignore[arg-type]
        ax.fill_between(x, np.abs(samp), 0.0, alpha=0.06, color="#00e5ff")  # type: ignore[arg-type]
        ax.set_ylim(-1.15, 1.15)
        ax.set_xlim(0.0, 1.0)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"],
                           color="#555", fontsize=7)
        ax.tick_params(colors="#333", left=False, labelleft=False)
        for spine in ax.spines.values():
            spine.set_edgecolor("#1a1a2e")
        ax.grid(axis="x", color="#1a1a2e", linewidth=0.5, alpha=0.6)
        fname = Path(out_path).name
        size_mb = Path(out_path).stat().st_size / 1024 / 1024
        fig.suptitle(
            f"\u25c8  {fname}  \u00b7  {size_mb:.1f} MB  \u00b7  MASTER RENDER",
            color="#a855f7", fontsize=9, y=1.01,
        )
        fig.tight_layout(pad=0.4)
        return fig
    except Exception:
        return None


def _p1_status(p1: dict, song_name: str, errors: list[str]) -> str:
    """Build a Phase 1 status markdown string from p1 sentinel data."""
    if not p1:
        return ""
    bpm = p1.get("bpm", 0)
    total_bars = p1.get("total_bars", 0)
    bar_s = p1.get("bar_s", 2.0)
    duration_min = total_bars * bar_s / 60

    # ── Sections list ──────────────────────────────────────────────────────
    sections_raw = p1.get("sections", "(none)")
    if "→" in sections_raw:
        section_items = "\n".join(f"  - {s.strip()}" for s in sections_raw.split("→"))
    else:
        section_items = f"  - {sections_raw}"

    # ── Stem names list ────────────────────────────────────────────────────
    stem_names = p1.get("stem_names", [])
    stems_list = "\n".join(f"  - {s}" for s in stem_names) if stem_names else "  - (none)"

    # ── Active sequences list ──────────────────────────────────────────────
    seq_names = p1.get("sequence_names", [])
    seq_list = "\n".join(f"  - {s}" for s in seq_names) if seq_names else "  - (none)"

    # ── Wavetable packs list ───────────────────────────────────────────────
    wt_names = p1.get("wt_pack_names", [])
    wt_list = "\n".join(f"  - {w}" for w in wt_names) if wt_names else "  - (none)"

    # ── Session files list ─────────────────────────────────────────────────
    file_lines: list[str] = []
    for p in p1.get("als_paths", []):
        file_lines.append(f"  - `{p}` *(ALS — Ableton Live)*")
    for p in p1.get("delivered_paths", [])[:20]:
        file_lines.append(f"  - `{p}`")
    files_block = "\n".join(file_lines) if file_lines else "  - (none)"

    # ── Artwork assets list ────────────────────────────────────────────────
    artwork = p1.get("artwork_files", {})
    if artwork:
        artwork_items = "\n".join(f"  - `{v}` *({k})*" for k, v in artwork.items())
    else:
        artwork_items = "  - *(generating in background — check output/{track_name}/press/)*"

    # ── Error list ────────────────────────────────────────────────────────
    err_block = ""
    if errors:
        err_block = "\n### ⚠ Warnings\n" + "\n".join(f"- {e}" for e in errors)

    lines = [
        f"## ✦ {song_name} — Phase 1: GENERATION Complete", "",
        "### 🎵 Track Info",
        f"- **Style**: {p1.get('style','')}",
        f"- **Mood**: {p1.get('mood','')}",
        f"- **Key**: {p1.get('key','')} {p1.get('scale','')}",
        f"- **BPM**: {bpm}",
        f"- **Total bars**: {total_bars}",
        f"- **Duration**: {duration_min:.1f} min",
        "",
        "### 🗺 Arrangement Sections",
        section_items,
        "",
        "### 🎛 Sound Design",
        f"- **SongDNA**: 153 fields (7 sub-DNAs) forged",
        f"- **Wavetables**: {p1.get('wt_frames',0)} frames ({p1.get('wt_packs',0)} DNA-driven packs)",
        wt_list,
        f"- **Serum 2 presets**: {p1.get('preset_count',0)} (mutated per stem)",
        f"- **Stem configs**: {p1.get('stem_count',0)}",
        stems_list,
        f"- **Modulation routes**: {p1.get('mod_routes',0)}",
        f"- **FX chains**: {p1.get('fx_slots',0)} slots",
        "",
        "### 🥁 Drum Factory",
        f"- **128 Rack**: {p1.get('rack_slots',0)}/128 slots filled",
        f"- **Drum loops**: {p1.get('drum_patterns',0)} patterns",
        f"- **MIDI sequences**: {p1.get('active_stems',0)} active stems / {p1.get('midi_notes',0)} notes",
        seq_list,
        f"- **Render patterns**: {p1.get('render_secs',0)} sections / {p1.get('render_hits',0)} hits",
        "",
        "### 🎨 Artwork Assets",
        artwork_items,
        "",
        "### 📁 Session Files",
        files_block,
        err_block,
        "",
        "---",
        "> ✓ Phase 1 complete — inspect outputs above, then press **◈ MIXX** to continue to ARRANGEMENT.",
        "> 💡 **Stem renders deferred** — open the Stage 5 ALS in Ableton Live to bounce patterns manually.",
    ]
    return "\n".join(lines)


def _build_final_status(p1: dict, p2: dict, p3: dict, p4: dict,
                        song_name: str, errors: list[str]) -> str:
    lines = [_p1_status(p1, song_name, errors)]
    if p2:
        lines.append(f"\n✓ Phase 2 complete — ArrangedTrack: {p2.get('total_bars',0)} bars")
    if p3:
        lines.append(f"\n✓ Phase 3 complete — MixedTrack: {p3.get('wav_path','')}")
    if p4:
        out = p4.get('out_path', '')
        lines.append(f"\n✓ Phase 4 complete — Master: {out}")
        # ── Live LUFS measurement ──────────────────────────────────────
        if out and Path(out).exists():
            try:
                import wave as _w
                with _w.open(out, "rb") as wf:
                    sw = wf.getsampwidth()
                    raw = wf.readframes(wf.getnframes())
                if sw == 2:
                    sig = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
                elif sw == 4:
                    sig = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
                else:
                    sig = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) / 128.0 - 1.0
                lufs = estimate_lufs(sig)
                peak_db = 20 * np.log10(max(np.max(np.abs(sig)), 1e-10))
                rms_db_val = 20 * np.log10(max(np.sqrt(np.mean(sig ** 2)), 1e-10))
                lines.append(
                    f"\n### LUFS Metering\n"
                    f"| Metric | Value |\n|--------|-------|\n"
                    f"| Integrated LUFS | {lufs:.1f} |\n"
                    f"| True Peak | {peak_db:.1f} dB |\n"
                    f"| RMS | {rms_db_val:.1f} dB |\n"
                    f"| Streaming Penalty | {max(0, lufs - (-14.0)):.1f} dB |"
                )
            except Exception:
                pass
    # Replace "Continuing to Phase 2" footer with final line
    result = "\n".join(lines)
    result = result.replace(
        "> Phase 1 complete. Continuing to Phase 2: ARRANGEMENT via AbletonOSC…",
        "> All 4 phases complete. Track mastered and released.",
    )
    return result


def handle_load_history():
    if not REPORTS_DIR.exists():
        return "_No reports yet._"
    reports = sorted(REPORTS_DIR.glob("intake_*.json"), reverse=True)
    if not reports:
        return "_No reports found._"
    lines = ["## Saved Intake Reports", "", f"**Total**: {len(reports)}", ""]
    for rp in reports[:30]:
        try:
            data = json.loads(rp.read_text())
            title = data.get("metadata", {}).get("title", rp.stem)
            artist = data.get("metadata", {}).get("artist", "")
            rhythm = data.get("audio_dna", {}).get("rhythm", {})
            bpm = rhythm.get("bpm", 0) if isinstance(rhythm, dict) else 0
            harmonic = data.get("audio_dna", {}).get("harmonic", {})
            kv = harmonic.get("key", "") if isinstance(harmonic, dict) else ""
            parts = [p for p in [artist, f"{bpm:.0f} BPM" if bpm else "", kv] if p]
            lines.append(f"- **{title}** -- {' | '.join(parts)}")
            if data.get("url"): lines.append(f"  `{data['url']}`")
            lines.append(f"  File: `{rp.name}`")
        except Exception:
            lines.append(f"- `{rp.name}` (unreadable)")
    return "\n".join(lines)


def handle_load_report(report_name):
    _empty_forge = ("", "dubstep", "", "(auto)", "(auto)", 150, "", "", "")  # +1 for master_ref_url
    if not report_name or not report_name.strip():
        return ("Select a report.", "", "", "", "", "") + _empty_forge
    rp = REPORTS_DIR / report_name.strip()
    if not rp.exists():
        matches = list(REPORTS_DIR.glob(f"*{report_name.strip()}*"))
        rp = matches[0] if matches else rp
    if not rp.exists():
        return (f"Report not found: {report_name}", "", "", "", "", "") + _empty_forge
    try:
        data = json.loads(rp.read_text())
        from engine.reference_analyzer import ReferenceAnalysis
        from engine.reference_intake import ChordInfo, MelodyInfo, SynthProfile, TrackMetadata, WebResearchResult
        result = IntakeResult()
        result.url = data.get("url", "")
        result.local_path = data.get("local_path", "")
        md = data.get("metadata", {})
        if md:
            result.metadata = TrackMetadata(**{k: md[k] for k in TrackMetadata.__dataclass_fields__ if k in md})
        if data.get("audio_dna"):
            result.audio_dna = ReferenceAnalysis.from_dict(data["audio_dna"])
        ci = data.get("chords", {})
        if ci:
            result.chords = ChordInfo(**{k: ci[k] for k in ChordInfo.__dataclass_fields__ if k in ci})
        mi = data.get("melody", {})
        if mi:
            result.melody = MelodyInfo(**{k: mi[k] for k in MelodyInfo.__dataclass_fields__ if k in mi})
        for attr, dk in [("bass_synth","bass_synth"),("lead_synth","lead_synth"),("pad_synth","pad_synth")]:
            sd = data.get(dk, {})
            if sd: setattr(result, attr, SynthProfile(**{k: sd[k] for k in SynthProfile.__dataclass_fields__ if k in sd}))
        wr = data.get("web_research", {})
        if wr:
            cpf = [ChordInfo(**{k: c[k] for k in ChordInfo.__dataclass_fields__ if k in c}) for c in wr.get("chord_progressions_found", [])]
            safe_wr = {k: wr[k] for k in WebResearchResult.__dataclass_fields__ if k in wr and k != "chord_progressions_found"}
            result.web_research = WebResearchResult(chord_progressions_found=cpf, **safe_wr)
        global _last_intake
        _last_intake = result
        forge_defaults = _derive_forge_defaults(result)
        ref_url_out = result.url if result.url else ""
        return (_format_summary(result), _format_audio_dna(result),
                _format_chords_melody(result), _format_synth_character(result),
                _format_web_research(result), _format_song_dna(result)) + forge_defaults + (ref_url_out,)
    except Exception as e:
        return (f"Error: {e}\n```\n{traceback.format_exc()}\n```",
                "", "", "", "", "",
                "", "dubstep", "", "(auto)", "(auto)", 150, "", "", "")


def _get_report_names():
    if not REPORTS_DIR.exists(): return []
    return sorted([f.name for f in REPORTS_DIR.glob("intake_*.json")], reverse=True)


def handle_arrangement_preview(
    arr_type: str, bpm: float, key: str, rco_preset: str = "weapon",
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
            f"**Bars**: {rco_data.get('total_bars', '?')} | **Duration**: {rco_data.get('total_duration_s', 0):.1f}s",
        ])

        try:
            prog = build_progression(
                name=f"{template.name}_preview", key=key, scale_type="minor",
                roman_sequence=["i", "VI", "III", "VII"], bpm=int(bpm),
            )
            chords = prog.chords[:min(8, len(template.sections))]
            if chords:
                lines.extend(["", f"### Chords ({key}m)", " -> ".join(c["symbol"] for c in chords)])
        except Exception:
            pass

        fig = None
        if HAS_MPL and plt is not None:
            fig, ax = plt.subplots(figsize=(12, 5))
            fig.set_facecolor("#0a0a0a")
            ax.set_facecolor("#111111")
            fig.suptitle(f"{template.name} | {key}m | {bpm} BPM", color="#a855f7", fontsize=13, fontweight="bold")
            _cm = {
                "intro": "#4a9eff", "build": "#ffa500", "drop": "#ff2020", "break": "#20ff20",
                "outro": "#888888", "verse": "#ff69b4", "interlude": "#20ffff",
                "seed": "#ffd700", "grow": "#90ee90", "expand": "#ff4500", "transcend": "#da70d6",
            }
            for pt in energy:
                sb, eb = pt["start_bar"], pt["end_bar"]
                val = pt["intensity"]
                name = pt["section"]
                c = next((v for k, v in _cm.items() if k in name), "#ff6b35")
                ax.fill_between([sb, eb], 0, val, alpha=0.3, color=c, step="pre")
                ax.plot([sb, sb, eb], [0, val, val], color=c, linewidth=2)
                ax.text((sb + eb) / 2, val + 0.02, name, ha="center", va="bottom",
                        fontsize=7, color=c, rotation=30)
            rco_times = rco_data.get("time_s", [])
            rco_energies = rco_data.get("energy", [])
            if rco_times and rco_energies:
                spb = (4 * 60) / bpm
                rco_bars = [t / spb for t in rco_times]
                ax.plot(rco_bars, rco_energies, color="#a855f7", linewidth=1.5,
                        alpha=0.8, label=f"RCO: {rco_profile.name}")
                ax.legend(loc="upper right", fontsize=8, facecolor="#222",
                          edgecolor="#555", labelcolor="white")
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
# HANDLERS — DASHBOARD / SYSTEM INFO
# ═══════════════════════════════════════════════════════════════════════════

def handle_sysinfo() -> str:
    import platform
    lines = [
        "## System Status", "",
        f"**Machine**: {platform.machine()}",
        f"**Python**: {platform.python_version()}",
        f"**Apple Silicon**: {'YES' if IS_APPLE_SILICON else 'No'}",
        f"**CPU Cores**: {CPU_CORES['total']} total "
        f"({CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E)",
        f"**Compute Workers**: {WORKERS_COMPUTE}",
        f"**I/O Workers**: {WORKERS_IO}", "",
    ]
    try:
        lines.append(f"**NumPy**: {np.__version__}")
        cfg = str(np.__config__.__dict__ if hasattr(np.__config__, "__dict__") else "")
        if "accelerate" in cfg.lower() or "blas" in cfg.lower():
            lines.append("**BLAS**: Accelerate / ARM NEON ✓")
    except Exception:
        pass
    out_dir = OUTPUT_ROOT
    if out_dir.exists():
        files = list(out_dir.rglob("*"))
        wav = sum(1 for f in files if f.suffix == ".wav")
        als = sum(1 for f in files if f.suffix == ".als")
        mid = sum(1 for f in files if f.suffix in (".mid", ".midi"))
        fxp = sum(1 for f in files if f.suffix == ".fxp")
        lines.extend([
            "", "### Output Directory",
            f"- WAV: {wav} | ALS: {als} | MIDI: {mid} | FXP: {fxp}",
        ])
    return "\n".join(lines)


def handle_quick_build(module_name: str) -> str:
    if not module_name:
        return "Select a module."
    import importlib
    t0 = time.perf_counter()
    try:
        mod = importlib.import_module(f"engine.{module_name}")
        elapsed = (time.perf_counter() - t0) * 1000
        return f"✓ `engine.{module_name}` loaded in {elapsed:.1f}ms"
    except Exception as e:
        return f"✗ `engine.{module_name}` failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — MOOD PREVIEW
# ═══════════════════════════════════════════════════════════════════════════

def handle_mood_preview(mood_text: str, bpm: float) -> str:
    """Return the full 7-parameter mood map."""
    return handle_mood_full_preview(mood_text, bpm)


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — AUDIO PREVIEW
# ═══════════════════════════════════════════════════════════════════════════

def handle_preview(module_name: str, duration: float, freq: float) -> tuple[str, str | None]:
    if not module_name:
        return "Select a module to preview.", None
    try:
        t0 = time.perf_counter()
        preview = render_preview(module_name, duration=duration, freq=freq)
        elapsed = (time.perf_counter() - t0) * 1000
        info = preview_to_dict(preview)
        tmp_dir = OUTPUT_ROOT / "previews"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        wav_path = tmp_dir / f"preview_{module_name}.wav"
        wav_bytes = base64.b64decode(info.get("wav_base64", ""))
        if wav_bytes:
            wav_path.write_bytes(wav_bytes)
        lines = [
            f"**Module**: {module_name}",
            f"**Duration**: {duration:.1f}s | **Frequency**: {freq:.0f} Hz",
            f"**Peak**: {info.get('peak_db', 0):.1f} dB | **RMS**: {info.get('rms_db', 0):.1f} dB",
            f"**Rendered in**: {elapsed:.0f}ms",
        ]
        return "\n".join(lines), str(wav_path) if wav_path.exists() else None
    except Exception as e:
        return f"Error: {e}", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — PARALLEL RENDER
# ═══════════════════════════════════════════════════════════════════════════

def handle_parallel_render(
    render_type: str,
    workers: int,
    progress: Any = None,  # gr.Progress
) -> str:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.perf_counter()
    results: list[str] = []

    def _prog(done, total, name):
        if progress is not None:
            progress(done / total, desc=f"[{done}/{total}] {name}")

    try:
        if render_type == "Pipeline Stems":
            paths = export_pipeline_stems_parallel(workers=workers, progress_callback=_prog)
            results = paths
        elif render_type == "Batch Renders":
            paths = export_batch_renders_parallel(workers=workers, progress_callback=_prog)
            results = paths
        elif render_type == "Full Build (All Modules)":
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
                    _prog(completed, total, label)
                    try:
                        n, ms, err = future.result()
                        results.append(f"FAIL: {n} ({ms:.0f}ms) — {err}" if err else f"OK: {n} ({ms:.0f}ms)")
                    except Exception as e:
                        results.append(f"FAIL: {name} — {e}")
        elapsed = time.perf_counter() - t0
        lines = [
            f"## Render Complete — {elapsed:.1f}s",
            f"**Type**: {render_type} | **Workers**: {workers} | **Files**: {len(results)}",
            "", "### Results",
        ]
        for r in results[:100]:
            lines.append(f"- `{r}`" if "/" in r else f"- {r}")
        if len(results) > 100:
            lines.append(f"_...and {len(results) - 100} more_")
        return "\n".join(lines)
    except Exception as e:
        return f"**Render Error**: {e}\n```\n{traceback.format_exc()}\n```"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — WAV ANALYZE + SPECTROGRAM
# ═══════════════════════════════════════════════════════════════════════════

def handle_analyze_wav(audio_file) -> tuple[str, Any]:
    if audio_file is None:
        return "Upload a WAV file to analyze.", None
    try:
        from engine.web_preview import analyze_wav_bytes
        if isinstance(audio_file, tuple):
            sr, data = audio_file
            wav_bytes = _signal_to_wav_bytes(
                data.astype(np.float64) / 32768.0 if data.dtype == np.int16 else data, sr
            )
        elif isinstance(audio_file, str):
            wav_bytes = Path(audio_file).read_bytes()
        else:
            wav_bytes = audio_file.read()
        result = analyze_wav_bytes(wav_bytes, "uploaded.wav")
        lines = [
            "## Analysis Results",
            f"**Duration**: {result.duration_s:.2f}s",
            f"**Peak**: {20 * np.log10(max(result.peak_amplitude, 1e-10)):.1f} dB",
            f"**RMS**: {20 * np.log10(max(result.rms, 1e-10)):.1f} dB",
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
                if mag and plt is not None:
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
    ref_url: str = "",
    progress: Any = None,  # gr.Progress
) -> tuple[str, str | None]:
    if audio_file is None:
        return "Upload a WAV file to master.", None
    try:
        from engine.mastering_chain import master, dubstep_master_settings
        if isinstance(audio_file, tuple):
            sr, data = audio_file
            signal = data.astype(np.float64) / 32768.0 if data.dtype == np.int16 else data.astype(np.float64)
        elif isinstance(audio_file, str):
            try:
                import soundfile as sf  # type: ignore[import-not-found]
                signal, sr = sf.read(audio_file, dtype="float64")
            except ImportError:
                signal = np.frombuffer(Path(audio_file).read_bytes()[44:], dtype=np.int16).astype(np.float64) / 32768.0
                sr = 44100
        else:
            return "Unsupported audio format.", None
        settings = dubstep_master_settings()
        settings.target_lufs = target_lufs
        settings.ceiling_db = ceiling_db

        # ── Reference-based mastering: analyze reference URL ──────────
        ref_info = ""
        if ref_url and ref_url.strip().startswith("http"):
            try:
                ref_result = intake_from_url(ref_url.strip(), research=False)
                if ref_result.song_dna is not None:
                    ref_dna = ref_result.song_dna
                    ref_lufs = getattr(getattr(ref_dna, 'loudness', None), 'lufs_estimate', None)
                    if ref_lufs is not None:
                        settings.target_lufs = ref_lufs
                        ref_info = f"\n**Reference LUFS**: {ref_lufs:.1f} (target matched)"
            except Exception as ref_e:
                ref_info = f"\n**Reference analysis failed**: {ref_e}"

        mastered, _report = master(signal, sr, settings)
        master_dir = OUTPUT_ROOT / "masters"
        master_dir.mkdir(parents=True, exist_ok=True)
        master_path = master_dir / f"master_{int(time.time())}.wav"
        master_path.write_bytes(_signal_to_wav_bytes(mastered, sr))
        peak_db_val = 20 * np.log10(max(np.max(np.abs(mastered)), 1e-10))
        rms_db_val = 20 * np.log10(max(np.sqrt(np.mean(mastered ** 2)), 1e-10))
        lufs_val = estimate_lufs(mastered, sr)
        lines = [
            "## Mastering Complete",
            f"**Target LUFS**: {settings.target_lufs:.1f} | **Ceiling**: {ceiling_db:.1f} dB",
            f"**Output LUFS**: {lufs_val:.1f} | **Peak**: {peak_db_val:.1f} dB | **RMS**: {rms_db_val:.1f} dB",
            f"**Streaming Penalty**: {max(0, lufs_val - (-14.0)):.1f} dB",
            f"**Output**: `{master_path}`",
            ref_info,
        ]
        return "\n".join(lines), str(master_path)
    except Exception as e:
        return f"Error mastering: {e}\n```\n{traceback.format_exc()}\n```", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — SAMPLE LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

def handle_sample_scan() -> str:
    lines = ["### Sample Library"]
    try:
        lib = SampleLibrary()
        total = lib.total_count
        lines.append(f"**Total samples**: {total}")
        for cat, count in sorted(lib.summary().items()):
            if count > 0:
                lines.append(f"- {cat}: {count}")
        if total == 0:
            lines.append("_No samples found. Run FORGE to generate._")
    except Exception as e:
        lines.append(f"Error: {e}")
    lines.append("\n### GALATCIA Collection")
    try:
        cat = catalog_galatcia()
        lines.extend([
            f"**Presets**: {len(cat.presets)} | **Samples**: {len(cat.samples)}",
            f"**Wavetables**: {len(cat.wavetables)} | **Racks**: {len(cat.racks)}",
        ])
    except Exception as e:
        lines.append(f"Error: {e}")
    return "\n".join(lines)


def handle_download_starter_pack() -> str:
    try:
        lib = SampleLibrary()
        count = lib.download_starter_pack()
        return f"✓ Downloaded {count} CC0 starter samples."
    except Exception as e:
        return f"Error: {e}"


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


def handle_search_samples(query: str) -> str:
    if not query.strip():
        return "Enter a search term."
    try:
        lib = SampleLibrary()
        results = lib.search(query.strip())
        if not results:
            return f"No results for **{query}**."
        lines = [f"### Results for '{query}' — {len(results)} found", ""]
        for s in results[:50]:
            lines.append(f"- `{s.filename}` ({s.category})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_browse_galatcia() -> str:
    try:
        cat = catalog_galatcia()
        lines = [f"## GALATCIA Collection", ""]
        if cat.presets:
            lines.append(f"### Presets ({len(cat.presets)})")
            by_cat: dict[str, list] = {}
            for p in cat.presets:
                by_cat.setdefault(p.category, []).append(p)
            for c in sorted(by_cat):
                lines.append(f"\n**{c}** ({len(by_cat[c])})")
                for p in by_cat[c][:10]:
                    lines.append(f"- `{p.name}` — {p.filename}")
        if cat.samples:
            lines.append(f"\n### Samples ({len(cat.samples)})")
            for s in cat.samples[:20]:
                lines.append(f"- `{s.filename}`")
        if cat.wavetables:
            lines.append(f"\n### Wavetables ({len(cat.wavetables)})")
            for wt in cat.wavetables[:20]:
                lines.append(f"- `{wt.filename}`")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def handle_import_dir(dir_path: str, category: str) -> str:
    if not dir_path.strip():
        return "Enter a directory path."
    if not category:
        return "Select a category."
    p = Path(dir_path.strip())
    if not p.exists():
        return f"Directory not found: `{p}`"
    try:
        lib = SampleLibrary()
        count = lib.import_directory(str(p), category)
        return f"Imported {count} files from `{p}` into **{category}**."
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — RESEARCH SUITE
# ═══════════════════════════════════════════════════════════════════════════

def handle_research(url: str, depth: str) -> str:
    """Run standalone web research on a URL without full intake."""
    if not url or not url.strip().startswith("http"):
        return "_Enter a valid URL to research._"
    try:
        try:
            from engine.reference_intake import _web_research  # type: ignore[attr-defined]
            results = _web_research(url.strip())
            if results:
                lines = ["## Web Research Results", ""]
                for k, v in results.items():
                    lines.append(f"**{k}**: {v}")
                return "\n".join(lines)
            return "Research returned no results — `requests` may not be installed."
        except (ImportError, AttributeError):
            result = intake_from_url(url.strip(), research=True)
            wr = result.web_research
            if wr:
                lines = ["## Research Results (via full intake)", ""]
                wr_dict = wr if isinstance(wr, dict) else vars(wr) if hasattr(wr, '__dict__') else {}
                for k, v in wr_dict.items():
                    lines.append(f"**{k}**: {v}")
                return "\n".join(lines)
            return "Web research unavailable — install `requests`."
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — MOOD PARAMETER PREVIEW (FULL 7-PARAM MAP)
# ═══════════════════════════════════════════════════════════════════════════

def handle_mood_full_preview(mood_text: str, bpm: float) -> str:
    """Return the full 7-parameter mood map, not just name + BPM."""
    if not mood_text:
        return "_Enter a mood to preview._"
    try:
        mood_name = resolve_mood(mood_text)
        suggestion = get_mood_suggestion(mood_text, bpm)
        lines = [
            f"## Mood: {mood_name}",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Energy | {suggestion.energy:.2f} |",
            f"| Darkness | {suggestion.darkness:.2f} |",
            f"| BPM | {suggestion.bpm} |",
            f"| Base Frequency | {suggestion.base_freq:.1f} Hz |",
            f"| Reverb | {suggestion.reverb:.2f} |",
            f"| Distortion | {suggestion.distortion:.2f} |",
            f"| Key | {suggestion.key} {suggestion.scale} |",
            "",
            f"**Suggested Modules**: {', '.join(suggestion.modules[:8])}",
            f"**Tags**: {', '.join(suggestion.tags)}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — ENERGY CURVE OVERLAY ON WAVEFORM
# ═══════════════════════════════════════════════════════════════════════════

def _make_waveform_plot_with_energy(out_path: "str | None", rco_preset: str = "weapon",
                                     bpm: float = 150.0) -> "Any":
    """Generate waveform plot with energy curve overlay."""
    if not out_path or not Path(out_path).exists():
        return None
    if not HAS_MPL:
        return None
    try:
        import wave as _wave
        with _wave.open(out_path, "rb") as wf:
            n_frames = wf.getnframes()
            sw = wf.getsampwidth()
            nch = wf.getnchannels()
            raw = wf.readframes(min(n_frames, 480_000))
        if sw == 2:
            samp = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sw == 4:
            samp = np.frombuffer(raw, dtype=np.float32)
        else:
            samp = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
        if nch == 2:
            samp = samp[::2]
        N = len(samp)
        if N > 3000:
            step = max(1, N // 3000)
            samp = samp[::step]
        x = np.linspace(0.0, 1.0, len(samp))
        assert plt is not None
        fig, ax = plt.subplots(figsize=(14, 3))
        fig.set_facecolor("#050510")
        ax.set_facecolor("#030312")
        ax.plot(x, samp, color="#a855f7", linewidth=0.4, alpha=0.85)
        ax.fill_between(x, samp, 0.0, alpha=0.11, color="#a855f7")  # type: ignore[arg-type]
        ax.fill_between(x, np.abs(samp), 0.0, alpha=0.06, color="#00e5ff")  # type: ignore[arg-type]

        # ── Energy curve overlay ──────────────────────────────────────────
        try:
            rco_fns = {
                "weapon": subtronics_weapon_preset,
                "emotive": subtronics_emotive_preset,
                "hybrid": subtronics_hybrid_preset,
            }
            rco_fn = rco_fns.get(rco_preset, subtronics_weapon_preset)
            rco_profile = rco_fn(bpm)
            rco_data = generate_energy_curve(rco_profile, resolution_per_bar=4)
            rco_energies = rco_data.get("energy", [])
            if rco_energies:
                ex = np.linspace(0.0, 1.0, len(rco_energies))
                ax2 = ax.twinx()
                ax2.set_facecolor("none")
                ax2.plot(ex, rco_energies, color="#ffa500", linewidth=1.2, alpha=0.7,
                         label="Energy Curve")
                ax2.fill_between(ex, rco_energies, 0, alpha=0.08, color="#ffa500")
                ax2.set_ylim(0, 1.3)
                ax2.set_ylabel("Energy", color="#ffa500", fontsize=8)
                ax2.tick_params(colors="#ffa500", labelsize=6)
                ax2.legend(loc="upper right", fontsize=7, facecolor="#111",
                           edgecolor="#555", labelcolor="white")
        except Exception:
            pass

        ax.set_ylim(-1.15, 1.15)
        ax.set_xlim(0.0, 1.0)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"],
                           color="#555", fontsize=7)
        ax.tick_params(colors="#333", left=False, labelleft=False)
        for spine in ax.spines.values():
            spine.set_edgecolor("#1a1a2e")
        ax.grid(axis="x", color="#1a1a2e", linewidth=0.5, alpha=0.6)
        fname = Path(out_path).name
        size_mb = Path(out_path).stat().st_size / 1024 / 1024
        fig.suptitle(
            f"\u25c8  {fname}  \u00b7  {size_mb:.1f} MB  \u00b7  MASTER RENDER + ENERGY",
            color="#a855f7", fontsize=9, y=1.01,
        )
        fig.tight_layout(pad=0.4)
        return fig
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — VST3 STATE SNAPSHOT / RESTORE
# ═══════════════════════════════════════════════════════════════════════════

def handle_export_fxp(preset_name: str) -> tuple[str, str | None]:
    """Export a DUBFORGE Serum 2 patch as .fxp file."""
    if not preset_name:
        return "Select a preset to export.", None
    try:
        idx = SERUM_PATCH_NAMES.index(preset_name) if preset_name in SERUM_PATCH_NAMES else 0
        patch = _DUBSTEP_PATCHES[idx] if idx < len(_DUBSTEP_PATCHES) else {}
        if not patch:
            return "No patch data available.", None
        params = patch.get("params", {})
        from engine.fxp_writer import VSTParam
        vst_params = [
            VSTParam(index=i, name=k, value=float(v), display=str(v))
            for i, (k, v) in enumerate(params.items())
        ]
        preset = FXPPreset(
            name=preset_name.replace(" ", "_")[:24],
            plugin_id="1397572658",  # Serum
            version=1,
            params=vst_params,
        )
        out_dir = OUTPUT_ROOT / "presets" / "fxp"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{preset.name}.fxp"
        write_fxp(preset, str(out_path))
        return f"Exported `{out_path.name}` ({out_path.stat().st_size} bytes)", str(out_path)
    except Exception as e:
        return f"Error: {e}", None


def handle_import_fxp(fxp_file: str | None) -> str:
    """Import an .fxp file and display its parameters."""
    if not fxp_file or not Path(fxp_file).exists():
        return "Upload an .fxp file to inspect."
    try:
        preset = read_fxp(fxp_file)
        lines = [
            f"## FXP Preset: {preset.name}",
            f"**Plugin ID**: {preset.plugin_id}",
            f"**Parameters**: {len(preset.params)}",
            "",
            "| # | Name | Value |",
            "|---|------|-------|",
        ]
        for p in preset.params[:40]:
            lines.append(f"| {p.index} | {p.name} | {p.value:.4f} |")
        if len(preset.params) > 40:
            lines.append(f"| ... | +{len(preset.params)-40} more | ... |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading FXP: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — SIDECHAIN CURVE VISUALIZER
# ═══════════════════════════════════════════════════════════════════════════

def handle_sidechain_preview(shape: str, depth: float, release_ms: float,
                             bpm: float) -> tuple[str, "Any"]:
    """Generate and plot a sidechain envelope curve."""
    if not shape:
        return "Select a sidechain shape.", None
    try:
        preset = SidechainPreset(
            name=f"Preview_{shape}",
            shape=shape,
            depth=depth,
            release_ms=release_ms,
            bpm=bpm,
        )
        envelope = generate_sidechain(preset, duration_s=4 * (60.0 / bpm))
        sr = 44100
        duration_s = len(envelope) / sr

        lines = [
            f"## Sidechain: {shape}",
            f"**Depth**: {depth:.2f} | **Release**: {release_ms:.0f}ms | **BPM**: {bpm:.0f}",
            f"**Envelope samples**: {len(envelope)} ({duration_s:.2f}s)",
        ]

        fig = None
        if HAS_MPL and plt is not None:
            fig, ax = plt.subplots(figsize=(12, 3))
            fig.set_facecolor("#0a0a0a")
            ax.set_facecolor("#111111")
            t = np.linspace(0, duration_s, len(envelope))
            ax.plot(t, envelope, color="#00e5ff", linewidth=1.5, alpha=0.9)
            ax.fill_between(t, envelope, 0, alpha=0.15, color="#00e5ff")  # type: ignore[arg-type]
            ax.set_ylim(-0.05, 1.1)
            ax.set_xlim(0, duration_s)
            ax.set_xlabel("Time (s)", color="#ccc")
            ax.set_ylabel("Gain", color="#ccc")
            ax.set_title(f"Sidechain: {shape} | depth={depth:.2f} | release={release_ms:.0f}ms",
                         color="#a855f7", fontsize=11)
            ax.tick_params(colors="#888")
            ax.grid(axis="both", color="#333", linewidth=0.5, alpha=0.5)
            # Mark beat positions
            beat_dur = 60.0 / bpm
            beat = 0.0
            while beat < duration_s:
                ax.axvline(x=beat, color="#ffa500", linestyle=":", linewidth=0.5, alpha=0.4)
                beat += beat_dur
            fig.tight_layout()

        return "\n".join(lines), fig
    except Exception as e:
        return f"Error: {e}", None


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — MIX MODEL SELECTOR
# ═══════════════════════════════════════════════════════════════════════════

def handle_mix_model(model: str) -> str:
    """Show the selected mix model parameters and philosophy."""
    models = {
        "Priority-Based": {
            "description": "Standard priority-weighted gain staging. Each element type has a priority weight (kick=1.0, snare=0.9, sub=0.95, lead=0.75). Gain is adjusted proportionally to priority.",
            "focus": "Balanced, genre-standard dubstep mix",
            "target_headroom": "3.0 dB",
            "bus_groups": "DRUMS → BASS → MELODIC → FX",
            "key_params": "Element priority weights, target RMS -14 dB",
        },
        "Camera Focus": {
            "description": "Mix strategy where ONE element is in sharp focus at any time. Like a camera rack-focusing between subjects — the focal element gets full bandwidth and volume, everything else blurs into the background with gentle EQ rolloffs and reverb push.",
            "focus": "Drop: bass in focus. Build: lead in focus. Breakdown: pads in focus",
            "target_headroom": "4.0 dB (extra room for focal element)",
            "bus_groups": "FOCAL → CONTEXT → AMBIENT",
            "key_params": "Focal element boost +2dB, context -3dB, ambient -6dB + reverb",
        },
        "Depth Staging": {
            "description": "3D spatial mix model. Elements are placed at perceived distances: FRONT (kick, snare, vocal), MID (bass, lead), BACK (pads, FX, ambience). Distance is achieved through volume, EQ rolloff, reverb amount, and stereo width.",
            "focus": "Immersive spatial depth — front to back staging",
            "target_headroom": "3.5 dB",
            "bus_groups": "FRONT → MID → BACK",
            "key_params": "Front: dry +0dB, Mid: -2dB + 15% verb, Back: -5dB + 40% verb + LP",
        },
    }
    if model not in models:
        return "Select a mix model."
    m = models[model]
    lines = [
        f"## Mix Model: {model}",
        "",
        m["description"],
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Focus Strategy | {m['focus']} |",
        f"| Target Headroom | {m['target_headroom']} |",
        f"| Bus Groups | {m['bus_groups']} |",
        f"| Key Parameters | {m['key_params']} |",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# HANDLERS — ALS SESSION DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════

def handle_als_download() -> tuple[str, str | None]:
    """Find and return the most recent ALS file from forge output."""
    try:
        als_dir = OUTPUT_ROOT / "ableton"
        if not als_dir.exists():
            # Check all output subdirectories
            als_files = sorted(OUTPUT_ROOT.rglob("*.als"), key=lambda f: f.stat().st_mtime, reverse=True)
        else:
            als_files = sorted(als_dir.rglob("*.als"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not als_files:
                als_files = sorted(OUTPUT_ROOT.rglob("*.als"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not als_files:
            return "No .als files found in output/. Run FORGE IT first.", None
        latest = als_files[0]
        size_kb = latest.stat().st_size / 1024
        return (
            f"**Latest ALS**: `{latest.name}` ({size_kb:.1f} KB)\n"
            f"**Path**: `{latest}`\n"
            f"**Modified**: {time.ctime(latest.stat().st_mtime)}",
            str(latest),
        )
    except Exception as e:
        return f"Error: {e}", None


THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=JetBrains+Mono:wght@300;400;500&family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --df-void: #010104;
    --df-surface: #050510;
    --df-panel: #08081a;
    --df-panel-glass: rgba(8, 8, 24, 0.78);
    --df-panel-elevated: rgba(14, 12, 32, 0.85);
    --df-border: #0f0f28;
    --df-border-glow: #2d1b69;
    --df-border-active: rgba(168,85,247,0.4);
    --df-purple: #a855f7;
    --df-purple-dim: #7c3aed;
    --df-purple-deep: #5b21b6;
    --df-purple-ultra: #3b0a7a;
    --df-cyan: #00e5ff;
    --df-cyan-dim: #0097a7;
    --df-cyan-bright: #22f5ff;
    --df-pink: #ff2d7c;
    --df-pink-hot: #ff0055;
    --df-gold: #fbbf24;
    --df-gold-bright: #fde68a;
    --df-green: #10b981;
    --df-green-bright: #34d399;
    --df-text: #eaeaf8;
    --df-text-mid: #8888aa;
    --df-text-dim: #3a3a5c;
    --df-glow-purple: 0 0 10px rgba(168,85,247,0.4), 0 0 40px rgba(168,85,247,0.12), 0 0 80px rgba(168,85,247,0.04);
    --df-glow-cyan: 0 0 10px rgba(0,229,255,0.4), 0 0 40px rgba(0,229,255,0.10);
    --df-glow-pink: 0 0 10px rgba(255,45,124,0.35), 0 0 40px rgba(255,45,124,0.08);
    --df-radius: 16px;
    --df-radius-sm: 10px;
    --df-glass-blur: 20px;
    --df-transition: cubic-bezier(0.22, 1, 0.36, 1);
    --df-transition-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* ── GLOBAL ──────────────────────────────────────────── */
body, .gradio-container {
    font-family: 'Inter', 'Space Grotesk', system-ui, sans-serif !important;
    background: var(--df-void) !important;
    color: var(--df-text) !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}
.gradio-container { max-width: 1440px !important; padding: 0 24px !important; }

/* ── AURORA + GRID BACKGROUND ─────────────────────────── */
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse 90% 50% at 15% 15%, rgba(168,85,247,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 70% 45% at 85% 55%, rgba(0,229,255,0.05) 0%, transparent 55%),
        radial-gradient(ellipse 55% 65% at 50% 95%, rgba(255,45,124,0.035) 0%, transparent 50%),
        radial-gradient(ellipse 40% 30% at 60% 20%, rgba(91,33,182,0.04) 0%, transparent 40%);
    animation: df-aurora 25s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
body::after {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(168,85,247,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(168,85,247,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 50%, black 20%, transparent 70%);
    -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 50%, black 20%, transparent 70%);
    pointer-events: none;
    z-index: 0;
    animation: df-grid-drift 30s linear infinite;
}
@keyframes df-grid-drift {
    0% { background-position: 0 0, 0 0; }
    100% { background-position: 60px 60px, 60px 60px; }
}
@keyframes df-aurora {
    0% { opacity: 0.6; filter: hue-rotate(0deg); }
    33% { opacity: 1; filter: hue-rotate(12deg); }
    66% { opacity: 0.8; filter: hue-rotate(-8deg); }
    100% { opacity: 0.6; filter: hue-rotate(5deg); }
}

/* ── HEADER ──────────────────────────────────────────── */
.df-nexus-header {
    position: relative;
    overflow: hidden;
    background: linear-gradient(160deg, #020210 0%, #0d0828 25%, #1a0535 45%, #120440 60%, #0a0618 80%, #020210 100%);
    border: 1px solid rgba(168,85,247,0.25);
    border-radius: 20px;
    padding: 48px 28px 38px;
    margin-bottom: 28px;
    text-align: center;
    backdrop-filter: blur(24px) saturate(1.3);
    -webkit-backdrop-filter: blur(24px) saturate(1.3);
    box-shadow: 0 0 60px rgba(168,85,247,0.06), 0 20px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03);
}
.df-nexus-header::before {
    content: '';
    position: absolute;
    top: 0; left: -50%; width: 200%; height: 2px;
    background: linear-gradient(90deg, transparent 5%, var(--df-cyan) 30%, var(--df-purple) 50%, var(--df-pink) 70%, transparent 95%);
    animation: df-scanline 6s linear infinite;
    opacity: 0.8;
}
.df-nexus-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: -50%; width: 200%; height: 2px;
    background: linear-gradient(90deg, transparent 5%, var(--df-pink) 30%, var(--df-purple) 50%, var(--df-cyan) 70%, transparent 95%);
    animation: df-scanline 6s linear infinite reverse;
    opacity: 0.8;
}
@keyframes df-scanline {
    0% { transform: translateX(0); }
    100% { transform: translateX(50%); }
}
.df-nexus-header h1 {
    font-family: 'Orbitron', monospace !important;
    font-weight: 900 !important;
    font-size: 3em !important;
    letter-spacing: 0.18em !important;
    color: transparent !important;
    background: linear-gradient(135deg, var(--df-cyan) 0%, var(--df-purple) 45%, var(--df-pink) 100%);
    -webkit-background-clip: text !important;
    background-clip: text !important;
    text-shadow: none !important;
    margin: 0 !important;
    line-height: 1.2 !important;
    filter: drop-shadow(0 0 20px rgba(168,85,247,0.3));
}
.df-nexus-header .df-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78em;
    color: var(--df-text-dim);
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-top: 8px;
}
.df-nexus-header .df-version {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62em;
    color: var(--df-purple-dim);
    margin-top: 10px;
    letter-spacing: 0.12em;
}
.df-nexus-header .df-status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-top: 14px;
    padding: 4px 18px;
    border-radius: 24px;
    border: 1px solid var(--df-green);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58em;
    color: var(--df-green);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    background: rgba(16,185,129,0.05);
    box-shadow: 0 0 12px rgba(16,185,129,0.1);
}
.df-nexus-header .df-dot {
    width: 7px; height: 7px;
    background: var(--df-green);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--df-green), 0 0 16px rgba(16,185,129,0.3);
    animation: df-pulse 2s ease-in-out infinite;
}
@keyframes df-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.3; transform: scale(0.8); }
}

/* ── TABS ────────────────────────────────────────────── */
.tabs > .tab-nav {
    background: var(--df-surface) !important;
    border-bottom: 1px solid var(--df-border) !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 4px 8px 0 !important;
    gap: 2px !important;
}
.tabs > .tab-nav > button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72em !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--df-text-dim) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 14px !important;
    border-radius: 8px 8px 0 0 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.tabs > .tab-nav > button:hover {
    color: var(--df-cyan) !important;
    background: rgba(0,229,255,0.04) !important;
}
.tabs > .tab-nav > button.selected {
    color: var(--df-purple) !important;
    background: rgba(168,85,247,0.06) !important;
    border-bottom: 2px solid var(--df-purple) !important;
    box-shadow: 0 2px 16px rgba(168,85,247,0.15) !important;
}

/* ── PANELS — GLASSMORPHISM ──────────────────────────── */
.tabitem, .panel, .form {
    background: var(--df-panel-glass) !important;
    backdrop-filter: blur(var(--df-glass-blur)) saturate(1.2) !important;
    -webkit-backdrop-filter: blur(var(--df-glass-blur)) saturate(1.2) !important;
    border: 1px solid rgba(45,27,105,0.3) !important;
    border-radius: var(--df-radius) !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
}
.tabitem:hover, .panel:hover {
    border-color: rgba(168,85,247,0.2) !important;
}

/* ── BUTTONS ─────────────────────────────────────────── */
button.primary {
    font-family: 'Orbitron', 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.85em !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    background: linear-gradient(135deg, var(--df-purple-deep) 0%, var(--df-purple) 50%, var(--df-purple-dim) 100%) !important;
    border: 1px solid rgba(168,85,247,0.4) !important;
    box-shadow: var(--df-glow-purple), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative;
    overflow: hidden;
}
button.primary::after {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.05) 50%, transparent 60%);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
}
button.primary:hover::after {
    transform: translateX(100%);
}
button.primary:hover {
    box-shadow: 0 0 20px rgba(168,85,247,0.5), 0 0 50px rgba(168,85,247,0.2),
                0 4px 20px rgba(0,0,0,0.3),
                inset 0 1px 0 rgba(255,255,255,0.12) !important;
    transform: translateY(-2px) !important;
}
button.primary:active {
    transform: translateY(0) !important;
    box-shadow: 0 0 12px rgba(168,85,247,0.4), inset 0 2px 4px rgba(0,0,0,0.3) !important;
}
button.secondary {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    background: var(--df-panel-glass) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
    border: 1px solid var(--df-border-glow) !important;
    color: var(--df-cyan) !important;
    border-radius: 10px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
button.secondary:hover {
    border-color: var(--df-cyan) !important;
    box-shadow: var(--df-glow-cyan) !important;
    transform: translateY(-1px) !important;
}

/* ── INPUTS ──────────────────────────────────────────── */
input[type="text"], textarea, .wrap input, .wrap textarea {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(6,6,15,0.8) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
    border: 1px solid var(--df-border) !important;
    color: var(--df-text) !important;
    border-radius: 8px !important;
    transition: all 0.25s ease !important;
}
input[type="text"]:focus, textarea:focus {
    border-color: var(--df-purple) !important;
    box-shadow: 0 0 0 2px rgba(168,85,247,0.15), 0 0 12px rgba(168,85,247,0.1) !important;
}
label, .label-wrap span {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78em !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: var(--df-text-dim) !important;
}

/* ── MARKDOWN CONTENT ────────────────────────────────── */
.prose h2, .prose h3 {
    font-family: 'Orbitron', monospace !important;
    letter-spacing: 0.08em !important;
}
.prose h2 {
    color: var(--df-purple) !important;
    filter: drop-shadow(0 0 8px rgba(168,85,247,0.2));
}
.prose h3 {
    color: var(--df-cyan) !important;
    filter: drop-shadow(0 0 6px rgba(0,229,255,0.15));
}
.prose table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
    width: 100% !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
.prose table th {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.73em !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--df-purple) !important;
    background: rgba(168,85,247,0.06) !important;
    border-bottom: 1px solid var(--df-border-glow) !important;
    padding: 10px 14px !important;
}
.prose table td {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82em !important;
    color: var(--df-text) !important;
    border-bottom: 1px solid rgba(18,18,42,0.5) !important;
    padding: 8px 14px !important;
    transition: background 0.2s ease !important;
}
.prose table tr:hover td {
    background: rgba(168,85,247,0.03) !important;
}
.prose code {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(10,10,22,0.8) !important;
    border: 1px solid rgba(45,27,105,0.3) !important;
    padding: 2px 6px !important;
    border-radius: 5px !important;
    color: var(--df-cyan) !important;
    font-size: 0.88em !important;
}
.prose pre {
    background: rgba(2,2,8,0.9) !important;
    border: 1px solid var(--df-border-glow) !important;
    border-radius: 10px !important;
    padding: 18px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.prose pre code {
    background: transparent !important;
    border: none !important;
    color: var(--df-text) !important;
}
.prose strong { color: var(--df-gold) !important; }

/* ── ACCORDION — GLASS ───────────────────────────────── */
.accordion {
    background: var(--df-panel-glass) !important;
    backdrop-filter: blur(var(--df-glass-blur)) !important;
    -webkit-backdrop-filter: blur(var(--df-glass-blur)) !important;
    border: 1px solid rgba(45,27,105,0.25) !important;
    border-radius: var(--df-radius) !important;
    transition: all 0.3s ease !important;
    margin-bottom: 6px !important;
}
.accordion:hover {
    border-color: rgba(168,85,247,0.15) !important;
    box-shadow: 0 0 16px rgba(168,85,247,0.05) !important;
}
.accordion > .label-wrap {
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.06em !important;
}

/* ── SLIDER ──────────────────────────────────────────── */
input[type="range"] { accent-color: var(--df-purple) !important; }

/* ── AUDIO PLAYER ────────────────────────────────────── */
audio {
    width: 100% !important;
    border-radius: 10px !important;
    outline: none !important;
    filter: hue-rotate(260deg) brightness(0.85) saturate(1.3) !important;
}
audio::-webkit-media-controls-panel {
    background: rgba(10,10,22,0.9) !important;
}

/* ── CODE BLOCK ──────────────────────────────────────── */
.code-wrap, .cm-editor {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(2,2,8,0.9) !important;
    border: 1px solid var(--df-border-glow) !important;
    border-radius: 10px !important;
}

/* ── SCROLLBAR ───────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: var(--df-border-glow);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: var(--df-purple-dim); }

/* ── FOOTER ──────────────────────────────────────────── */
.df-footer {
    text-align: center;
    padding: 24px 0 10px;
    border-top: 1px solid rgba(45,27,105,0.2);
    margin-top: 20px;
}
.df-footer .df-sigil {
    font-family: 'Orbitron', monospace;
    font-size: 0.62em;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--df-text-dim);
}
.df-footer .df-constants {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58em;
    color: rgba(45,27,105,0.6);
    margin-top: 5px;
    letter-spacing: 0.08em;
}

/* ── DROPDOWN ────────────────────────────────────────── */
.wrap > select, .wrap .secondary-wrap {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(6,6,15,0.8) !important;
    border: 1px solid var(--df-border) !important;
    border-radius: 8px !important;
}

/* ── PLOT ────────────────────────────────────────────── */
.plot-container {
    border: 1px solid var(--df-border-glow) !important;
    border-radius: var(--df-radius) !important;
    overflow: hidden !important;
}

/* ── CHECKBOX ────────────────────────────────────────── */
input[type="checkbox"] { accent-color: var(--df-purple) !important; }

/* ── GLOW DIVIDERS ───────────────────────────────────── */
.prose hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--df-border-glow), var(--df-purple-dim), var(--df-border-glow), transparent) !important;
    margin: 28px 0 !important;
}

/* ── SECTION TITLES ──────────────────────────────────── */
.df-section-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.82em;
    font-weight: 700;
    letter-spacing: 0.18em;
    color: var(--df-cyan);
    padding: 16px 0 10px;
    margin-top: 10px;
    border-top: 1px solid rgba(45,27,105,0.2);
    text-transform: uppercase;
    position: relative;
}
.df-section-title::after {
    content: '';
    display: block;
    width: 40px;
    height: 2px;
    background: linear-gradient(90deg, var(--df-cyan), transparent);
    margin-top: 6px;
    border-radius: 1px;
}

/* ── PROGRESS WINDOW ─────────────────────────────────── */
.df-progress-window {
    background: linear-gradient(160deg, rgba(5,5,16,0.95) 0%, rgba(15,10,42,0.95) 50%, rgba(10,10,24,0.95) 100%);
    backdrop-filter: blur(20px) saturate(1.3);
    -webkit-backdrop-filter: blur(20px) saturate(1.3);
    border: 1px solid rgba(168,85,247,0.25);
    border-radius: var(--df-radius);
    padding: 28px;
    margin: 18px 0;
    font-family: 'JetBrains Mono', monospace;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02);
    position: relative;
    overflow: hidden;
}
.df-progress-window::before {
    content: '';
    position: absolute;
    top: -1px; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--df-purple), var(--df-cyan), transparent);
    animation: df-scanline 4s linear infinite;
}
.df-progress-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.05em;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: var(--df-purple);
    margin-bottom: 18px;
    filter: drop-shadow(0 0 8px rgba(168,85,247,0.3));
}
.df-progress-bar-wrap {
    position: relative;
    height: 30px;
    background: rgba(2,2,8,0.6);
    border: 1px solid rgba(45,27,105,0.3);
    border-radius: 15px;
    overflow: hidden;
    margin-bottom: 22px;
}
.df-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--df-purple-deep), var(--df-purple), var(--df-cyan));
    background-size: 200% 100%;
    animation: df-bar-shimmer 3s ease infinite;
    border-radius: 15px;
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 16px rgba(168,85,247,0.4);
}
@keyframes df-bar-shimmer {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
.df-progress-pct {
    position: absolute;
    top: 0;
    right: 14px;
    line-height: 30px;
    font-size: 0.75em;
    font-weight: 700;
    color: var(--df-text);
    letter-spacing: 0.1em;
    text-shadow: 0 1px 4px rgba(0,0,0,0.9);
}
.df-progress-steps {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-bottom: 14px;
}
.df-step {
    font-size: 0.76em;
    padding: 7px 14px;
    border-radius: 8px;
    border-left: 3px solid transparent;
    transition: all 0.3s ease;
}
.df-step-done {
    color: var(--df-green);
    border-left-color: var(--df-green);
    background: rgba(16,185,129,0.05);
}
.df-step-active {
    color: var(--df-gold);
    border-left-color: var(--df-gold);
    background: rgba(251,191,36,0.07);
    animation: df-step-glow 1.5s ease-in-out infinite;
    box-shadow: inset 0 0 20px rgba(251,191,36,0.03);
}
@keyframes df-step-glow {
    0%, 100% { opacity: 1; border-left-color: var(--df-gold); }
    50% { opacity: 0.6; border-left-color: rgba(251,191,36,0.4); }
}
.df-step-pending {
    color: var(--df-text-dim);
    border-left-color: var(--df-border);
    opacity: 0.6;
}
.df-error-log {
    margin-top: 14px;
    padding: 14px;
    background: rgba(255,45,124,0.04);
    border: 1px solid rgba(255,45,124,0.15);
    border-radius: 10px;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}
.df-error-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.73em;
    font-weight: 700;
    color: var(--df-pink);
    margin-bottom: 8px;
    letter-spacing: 0.1em;
}
.df-error-entry {
    font-size: 0.7em;
    color: var(--df-pink);
    padding: 3px 0;
    border-bottom: 1px solid rgba(255,45,124,0.08);
}

/* ── MICRO-ANIMATION: Fade-in on load ────────────────── */
.gradio-container > * {
    animation: df-fade-up 0.5s ease-out both;
}
@keyframes df-fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ── ROW HOVER GLOW ──────────────────────────────────── */
.gr-group, .gr-box {
    transition: box-shadow 0.3s ease !important;
}
.gr-group:hover, .gr-box:hover {
    box-shadow: 0 0 24px rgba(168,85,247,0.04) !important;
}

/* ── SHELLS / META CARDS ─────────────────────────────── */
.df-hero-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: -6px 0 24px;
}
.df-hero-card {
    position: relative;
    padding: 18px 18px 16px;
    border-radius: 16px;
    border: 1px solid rgba(168,85,247,0.18);
    background: linear-gradient(180deg, rgba(11,11,28,0.88) 0%, rgba(7,7,20,0.72) 100%);
    backdrop-filter: blur(18px) saturate(1.2);
    -webkit-backdrop-filter: blur(18px) saturate(1.2);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 10px 30px rgba(0,0,0,0.18);
    overflow: hidden;
}
.df-hero-card::before {
    content: '';
    position: absolute;
    inset: 0 auto auto 0;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,229,255,0.55), transparent);
    opacity: 0.9;
}
.df-hero-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68em;
    color: var(--df-text-dim);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.df-hero-value {
    font-family: 'Space Grotesk', 'Orbitron', sans-serif;
    font-size: 1.5em;
    font-weight: 700;
    color: var(--df-text);
    letter-spacing: 0.03em;
    line-height: 1.1;
}
.df-hero-note {
    font-size: 0.8em;
    color: var(--df-text-mid);
    margin-top: 8px;
}
.df-shell {
    margin: 0 0 22px !important;
    padding: 18px 18px 10px !important;
    border: 1px solid rgba(168,85,247,0.12) !important;
    border-radius: 18px !important;
    background: linear-gradient(180deg, rgba(10,10,24,0.72) 0%, rgba(6,6,17,0.76) 100%) !important;
    backdrop-filter: blur(20px) saturate(1.15) !important;
    -webkit-backdrop-filter: blur(20px) saturate(1.15) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 18px 50px rgba(0,0,0,0.18) !important;
}
.df-shell-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-end;
    margin-bottom: 12px;
}
.df-shell-copy {
    max-width: 760px;
}
.df-shell-copy p {
    margin: 0;
    font-size: 0.92em;
    color: var(--df-text-mid);
    line-height: 1.6;
}
.df-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 4px;
}
.df-pill {
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(0,229,255,0.18);
    background: rgba(0,229,255,0.05);
    color: var(--df-cyan);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68em;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.df-inline-note {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68em;
    color: var(--df-gold);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
}
.df-accent-copy {
    margin: 0 0 12px !important;
}
.df-accent-copy p {
    color: var(--df-text-mid) !important;
    line-height: 1.7 !important;
}

/* ── URL HERO — PRIMARY INPUT ────────────────────────── */
.df-url-hero {
    border: 1px solid rgba(0,229,255,0.25) !important;
    background: linear-gradient(180deg, rgba(0,30,40,0.45) 0%, rgba(10,10,24,0.72) 100%) !important;
    box-shadow: 0 0 30px rgba(0,229,255,0.06), inset 0 1px 0 rgba(0,229,255,0.08), 0 18px 50px rgba(0,0,0,0.18) !important;
}
.df-url-hero .df-section-title {
    color: var(--df-cyan) !important;
    font-size: 1.3em !important;
}
.df-url-input textarea {
    font-size: 1.1em !important;
    padding: 14px 18px !important;
    border: 1px solid rgba(0,229,255,0.22) !important;
    background: rgba(0,20,30,0.5) !important;
    border-radius: 12px !important;
    transition: border-color 0.3s var(--df-transition), box-shadow 0.3s var(--df-transition) !important;
}
.df-url-input textarea:focus {
    border-color: var(--df-cyan) !important;
    box-shadow: 0 0 20px rgba(0,229,255,0.15) !important;
}

/* ── RESPONSIVE ──────────────────────────────────────── */
@media (max-width: 1100px) {
    .df-hero-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .df-shell-header {
        flex-direction: column;
        align-items: flex-start;
    }
}
@media (max-width: 760px) {
    .gradio-container {
        padding: 0 12px !important;
    }
    .df-nexus-header {
        padding: 34px 18px 28px;
    }
    .df-nexus-header h1 {
        font-size: 2.1em !important;
        letter-spacing: 0.12em !important;
    }
    .df-hero-grid {
        grid-template-columns: 1fr;
    }
    .df-shell {
        padding: 14px 14px 8px !important;
    }
}

/* ── LIVE FILE CARDS ─────────────────────────────────────────── */
.df-file-log {
    padding: 14px 14px 10px;
    background: rgba(2,2,8,0.75);
    border: 1px solid rgba(168,85,247,0.12);
    border-radius: 12px;
    font-family: 'JetBrains Mono', monospace;
    min-height: 52px;
    max-height: 300px;
    overflow-y: auto;
    margin: 6px 0 10px;
}
.df-file-log-header {
    font-size: 0.65em;
    color: var(--df-text-dim);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(168,85,247,0.1);
}
.df-file-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 10px;
    margin: 3px 0;
    background: rgba(168,85,247,0.06);
    border: 1px solid rgba(168,85,247,0.15);
    border-radius: 7px;
    animation: df-card-in 0.25s ease-out;
}
@keyframes df-card-in {
    from { opacity: 0; transform: translateX(-6px); }
    to   { opacity: 1; transform: translateX(0); }
}
.df-file-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 0.6em;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    min-width: 38px;
    text-align: center;
}
.df-badge-wav  { background: rgba(0,229,255,0.10); color: var(--df-cyan);   border: 1px solid rgba(0,229,255,0.28); }
.df-badge-mid  { background: rgba(168,85,247,0.10); color: var(--df-purple); border: 1px solid rgba(168,85,247,0.28); }
.df-badge-midi { background: rgba(168,85,247,0.10); color: var(--df-purple); border: 1px solid rgba(168,85,247,0.28); }
.df-badge-als  { background: rgba(255,215,0,0.10);  color: var(--df-gold);   border: 1px solid rgba(255,215,0,0.28); }
.df-badge-json { background: rgba(120,120,120,0.10); color: #999;            border: 1px solid rgba(120,120,120,0.22); }
.df-badge-xml  { background: rgba(120,120,120,0.10); color: #999;            border: 1px solid rgba(120,120,120,0.22); }
.df-file-name  { color: var(--df-text); font-size: 0.8em; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.df-file-size  { color: var(--df-text-dim); font-size: 0.7em; white-space: nowrap; }
.df-file-phase { color: rgba(168,85,247,0.55); font-size: 0.63em; letter-spacing: 0.06em; text-transform: uppercase; }

/* ── PHASE GATE PANEL ───────────────────────────────────────── */
.df-gate-row {
    display: flex;
    gap: 14px;
    margin: 14px 0 6px;
    justify-content: flex-start;
}
.df-gate-btn button {
    font-family: 'Orbitron', monospace !important;
    font-size: 1.0em !important;
    font-weight: 900 !important;
    letter-spacing: 0.18em !important;
    padding: 13px 44px !important;
    border-radius: 10px !important;
    text-transform: uppercase !important;
    box-shadow: 0 0 22px rgba(168,85,247,0.28), inset 0 1px 0 rgba(255,255,255,0.07) !important;
    transition: box-shadow 0.2s ease, transform 0.1s ease !important;
}
.df-gate-btn button:hover {
    box-shadow: 0 0 36px rgba(168,85,247,0.5), inset 0 1px 0 rgba(255,255,255,0.1) !important;
    transform: translateY(-1px) !important;
}

/* ── WAVEFORM DISPLAY ───────────────────────────────────────── */
.df-waveform-wrap .plot-container {
    border: 1px solid rgba(0,229,255,0.18) !important;
    border-radius: 12px !important;
    background: rgba(3,3,18,0.95) !important;
    overflow: hidden !important;
}

/* ── RUN LOG + ERROR LOG ────────────────────────────────────── */
.df-run-log, .df-err-log {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    max-height: 260px;
    overflow-y: auto;
    background: rgba(2,2,14,0.97);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 10px 14px;
    line-height: 1.6;
}
.df-run-log { color: #b8c4d4; }
.df-run-log .df-log-ts { color: rgba(0,229,255,0.5); margin-right: 6px; }
.df-err-log { color: #ff7070; }
.df-err-log .df-log-ts { color: rgba(255,110,110,0.6); margin-right: 6px; }
.df-log-empty { color: rgba(255,255,255,0.2); font-style: italic; }
"""


def build_ui():
    _require_gradio()
    with gr.Blocks(
        title="DUBFORGE NEXUS",
    ) as app:
        # ── HEADER ───────────────────────────────────────────
        gr.HTML(
            '<div class="df-nexus-header">'
            '<h1>DUBFORGE NEXUS</h1>'
            '<div class="df-subtitle">autonomous emulation engine</div>'
            '<div class="df-version">v9.1.0 &mdash; Aurora Command Surface</div>'
            '<div class="df-status"><span class="df-dot"></span>SYSTEM ONLINE</div>'
            '</div>'
        )

        # ── URL HERO — PRIMARY INPUT ─────────────────────────
        # The URL is the nucleus — everything cascades from here.
        with gr.Group(elem_classes=["df-shell", "df-url-hero"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25C9 REFERENCE URL</div>'
                '<p>Paste a public track URL. DUBFORGE downloads the audio, extracts 153-field DNA, '
                'runs web research (artist intel, production notes, genre tags), derives forge defaults, '
                'and populates every downstream module automatically.</p>'
                '<div class="df-pill-row">'
                '<span class="df-pill">auto-download</span>'
                '<span class="df-pill">13-layer DNA</span>'
                '<span class="df-pill">web research</span>'
                '<span class="df-pill">artwork data</span>'
                '<span class="df-pill">forge defaults</span>'
                '</div>'
                '</div>'
                '<div class="df-inline-note">URL → everything</div>'
                '</div>'
            )
            intake_url = gr.Textbox(
                label="Reference URL",
                placeholder="https://soundcloud.com/artist/track  or  https://youtube.com/watch?v=...",
                lines=1,
                elem_classes=["df-url-input"],
            )
            with gr.Row():
                intake_btn = gr.Button("\u25C9 ANALYZE + POPULATE ALL", variant="primary", size="lg", scale=3)
                intake_research = gr.Checkbox(value=True, label="Web Research", scale=1, interactive=False)
            with gr.Accordion("Or upload a local audio file", open=False):
                intake_audio = gr.Audio(label="Upload WAV / Audio File", type="filepath")

        # ── SECTION 2: ANALYSIS RESULTS (auto-populated from URL) ─────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2261 ANALYSIS RESULTS</div>'
                '<p>Auto-populated from the reference URL. Review the extracted fingerprint — Audio DNA, '
                'chords, synth character, web research, and SongDNA genome — before forging.</p>'
                '</div>'
                '<div class="df-inline-note">auto-filled from URL</div>'
                '</div>'
            )
            intake_summary = gr.Markdown("_Paste a URL above to begin — all modules auto-populate from the reference._", elem_classes=["df-accent-copy"])
            intake_report = gr.File(label="Download Report (JSON)", visible=True)
            with gr.Accordion("\u2261 Audio DNA Matrix (13 categories)", open=False):
                audio_dna_output = gr.Markdown("_Run intake first._")
            with gr.Accordion("\u266B Harmonic // Chords & Melody", open=False):
                chords_output = gr.Markdown("_Run intake first._")
            with gr.Accordion("\u25B2 Synth Character // Layer Decomposition", open=False):
                synth_output = gr.Markdown("_Run intake first._")
            with gr.Accordion("\u2302 Web Research // OSINT", open=False):
                web_output = gr.Markdown("_Run intake first._")
            with gr.Accordion("\u29BF SongDNA Genome (JSON)", open=False):
                song_dna_output = gr.Code(label="SongDNA JSON", language="json", lines=20, value="{}")

        # ── SECTION 2B: MOOD ENGINE (cascades from URL mood data) ─────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2728 MOOD ENGINE</div>'
                '<p>Preview the full 7-parameter mood map. Auto-seeded from URL analysis when a mood is detected.</p>'
                '</div>'
                '<div class="df-inline-note">14 curated moods</div>'
                '</div>'
            )
            with gr.Accordion("\u2728 Mood Parameter Preview", open=False):
                with gr.Row():
                    mood_preview_text = gr.Textbox(label="Mood", placeholder="aggressive, dark, euphoric...", scale=2)
                    mood_preview_bpm = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM", scale=1)
                    mood_preview_btn = gr.Button("Preview Mood", variant="secondary", scale=1)
                mood_preview_result = gr.Markdown("_Enter a mood to see the full parameter map._")
                mood_preview_btn.click(fn=handle_mood_full_preview,
                                       inputs=[mood_preview_text, mood_preview_bpm],
                                       outputs=[mood_preview_result])
                gr.Markdown(f"**Available moods**: {', '.join(sorted(MOODS.keys()))}")

        # ── SECTION 3: FORGE EMULATION (auto-populated from URL) ─────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2726 FORGE EMULATION</div>'
                '<p>Auto-populated from URL analysis — song name, style, mood, key, scale, BPM, and tags '
                'are all derived from the reference. Override any field, then FORGE IT to render.</p>'
                '<div class="df-pill-row"><span class="df-pill">URL-seeded</span><span class="df-pill">arrangement-aware</span><span class="df-pill">mastered export</span></div>'
                '</div>'
                '<div class="df-inline-note">cascaded from reference</div>'
                '</div>'
            )
            with gr.Row():
                song_name = gr.Textbox(label="Song Name", placeholder="e.g. DUBFORGE NEXTS", scale=3)
                style = gr.Dropdown(choices=STYLE_OPTIONS, value="dubstep", label="Style", scale=1)
                mood = gr.Textbox(label="Mood", placeholder="dark, aggressive", scale=1)
            with gr.Row():
                key = gr.Dropdown(choices=["(auto)"] + KEY_OPTIONS, value="(auto)", label="Key")
                scale = gr.Dropdown(choices=["(auto)"] + SCALE_OPTIONS, value="(auto)", label="Scale")
                bpm = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM")
                arrangement = gr.Dropdown(choices=["(auto)"] + ARRANGEMENT_OPTIONS, value="(auto)", label="Arrangement")
            with gr.Row():
                tags_input = gr.Textbox(label="Tags", placeholder="heavy, festival", scale=2)
                artist_notes = gr.Textbox(label="Notes", placeholder="Free-form ideas...", scale=2)
            forge_btn = gr.Button("\u2726 FORGE IT", variant="primary", size="lg")

        # ── SECTION 4: PROGRESS + OUTPUT ─────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2727 FORGE OUTPUT</div>'
                '<p>Watch each phase build in real time. Inspect the generated files, then press the gate button to release the next phase.</p>'
                '</div>'
                '<div class="df-inline-note">live execution telemetry</div>'
                '</div>'
            )
            progress_html = gr.HTML(value="")
            forge_files_html = gr.HTML(value=_file_card_html([]))
            forge_status = gr.Markdown("")
            with gr.Row(elem_classes=["df-gate-row"]):
                mixx_btn = gr.Button("◈ MIXX",      variant="primary", visible=False, elem_classes=["df-gate-btn"])
                mix3_btn = gr.Button("▲ MIX3",      variant="primary", visible=False, elem_classes=["df-gate-btn"])
                master_btn = gr.Button("✦ MASTERR",  variant="primary", visible=False, elem_classes=["df-gate-btn"])
            waveform_plot = gr.Plot(label="◈ MASTER WAVEFORM", visible=False, elem_classes=["df-waveform-wrap"])
            forge_audio = gr.Audio(label="\u266B Rendered Track", type="filepath", interactive=False)
            with gr.Accordion("\u29BF SongDNA Output (JSON)", open=False):
                forge_dna = gr.Code(label="SongDNA", language="json", lines=20)
            with gr.Accordion("⚡ RUN LOG", open=False):
                run_log_html = gr.HTML(value=_run_log_html([]))
            with gr.Accordion("⚠ ERROR LOG", open=False):
                error_log_html = gr.HTML(value=_error_log_html([]))
            with gr.Accordion("📦 ALS Session Download", open=False):
                als_download_btn = gr.Button("Find Latest ALS", variant="secondary")
                als_download_info = gr.Markdown("_Run FORGE IT to generate .als files_")
                als_download_file = gr.File(label="Download ALS", visible=True)
                als_download_btn.click(fn=handle_als_download,
                                       outputs=[als_download_info, als_download_file])

        # ── SECTION 5: ARRANGEMENT PREVIEW ───────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25B2 ARRANGEMENT PREVIEW</div>'
                '<p>Interrogate the section architecture before the forge run. RCO overlay shows Subtronics-derived energy dynamics with phi-curve interpolation.</p>'
                '</div>'
                '<div class="df-inline-note">pre-flight structure view</div>'
                '</div>'
            )
            with gr.Accordion("\u25B2 Arrangement Preview", open=False):
                with gr.Row():
                    arr_type = gr.Dropdown(choices=ARRANGEMENT_OPTIONS, value="weapon", label="Type", scale=1)
                    arr_rco = gr.Dropdown(choices=ENERGY_PRESETS, value="weapon", label="RCO Preset", scale=1)
                    arr_bpm = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM")
                    arr_key = gr.Dropdown(choices=KEY_OPTIONS, value="F", label="Key", scale=1)
                    arr_btn = gr.Button("Preview", variant="secondary")
                arr_info = gr.Markdown("_Click Preview_")
                arr_plot = gr.Plot(label="Energy Curve")
                arr_btn.click(fn=handle_arrangement_preview,
                              inputs=[arr_type, arr_bpm, arr_key, arr_rco],
                              outputs=[arr_info, arr_plot])

        # ── SECTION 6: ARCHIVE ───────────────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25F7 ARCHIVE</div>'
                '<p>Re-open previous intake reports, inspect the stored DNA, and reload the forge controls without re-running the entire capture flow.</p>'
                '</div>'
                '<div class="df-inline-note">report recall</div>'
                '</div>'
            )
            with gr.Accordion("\u25F7 Archive // Saved Reports", open=False):
                with gr.Row():
                    history_refresh = gr.Button("Refresh", variant="secondary")
                    report_dropdown = gr.Dropdown(choices=_get_report_names(), label="Select Report", interactive=True)
                    load_report_btn = gr.Button("Load Report", variant="primary")
                history_list = gr.Markdown("_Click Refresh to see reports._")
                history_refresh.click(fn=handle_load_history, outputs=[history_list])
                def _refresh_dropdown():
                    return gr.Dropdown(choices=_get_report_names())
                history_refresh.click(fn=_refresh_dropdown, outputs=[report_dropdown])
                # load_report_btn wired in EVENT WIRING section (needs master_ref_url)

        # ── SECTION 7: AUDIO PREVIEW ─────────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25B6 AUDIO PREVIEW</div>'
                '<p>Render any engine module as a short audio clip for instant monitoring in the browser.</p>'
                '</div>'
                '<div class="df-inline-note">module monitor</div>'
                '</div>'
            )
            with gr.Accordion("\u25B6 Module Preview", open=False):
                with gr.Row():
                    preview_module = gr.Dropdown(choices=PREVIEW_MODULES, value="sub_bass", label="Module")
                    preview_dur = gr.Slider(minimum=0.1, maximum=5.0, step=0.1, value=1.0, label="Duration (s)")
                    preview_freq = gr.Slider(minimum=20, maximum=2000, step=1, value=100, label="Frequency (Hz)")
                    preview_btn = gr.Button("Generate", variant="secondary")
                preview_info = gr.Markdown("")
                preview_audio_comp = gr.Audio(label="Preview", type="filepath")
                preview_btn.click(fn=handle_preview,
                                  inputs=[preview_module, preview_dur, preview_freq],
                                  outputs=[preview_info, preview_audio_comp])

        # ── SECTION 8: WAV ANALYZE ────────────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u29C9 WAV ANALYSIS</div>'
                '<p>Upload any WAV for spectral + loudness analysis with spectrogram visualization.</p>'
                '</div>'
                '<div class="df-inline-note">signal inspection</div>'
                '</div>'
            )
            with gr.Accordion("\u29C9 WAV Analysis", open=False):
                analyze_audio_inp = gr.Audio(label="Upload Audio", type="filepath")
                analyze_btn = gr.Button("Analyze", variant="secondary")
                analyze_result_md = gr.Markdown("")
                analyze_plot_comp = gr.Plot(label="Spectrogram")
                analyze_btn.click(fn=handle_analyze_wav,
                                  inputs=[analyze_audio_inp],
                                  outputs=[analyze_result_md, analyze_plot_comp])

        # ── SECTION 9: MASTERING ─────────────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2728 MASTERING</div>'
                '<p>Apply the DUBFORGE mastering chain. Reference URL auto-fills from intake — loudness target derived from the reference track LUFS.</p>'
                '</div>'
                '<div class="df-inline-note">reference-matched master</div>'
                '</div>'
            )
            with gr.Accordion("\u2728 Standalone Mastering", open=False):
                master_audio_inp = gr.Audio(label="Upload Track", type="filepath")
                with gr.Row():
                    target_lufs_sl = gr.Slider(minimum=-20, maximum=-4, step=0.5, value=-8.0, label="Target LUFS")
                    ceiling_db_sl = gr.Slider(minimum=-3.0, maximum=0.0, step=0.1, value=-0.3, label="Ceiling (dB)")
                master_ref_url = gr.Textbox(
                    label="Reference URL (auto-filled from intake — override if needed)",
                    placeholder="https://soundcloud.com/artist/reference-track",
                    lines=1,
                )
                master_run_btn = gr.Button("Master It", variant="primary")
                master_result_md = gr.Markdown("")
                master_out_audio = gr.Audio(label="Mastered Output", type="filepath")
                master_run_btn.click(fn=handle_master_track,
                                     inputs=[master_audio_inp, target_lufs_sl, ceiling_db_sl, master_ref_url],
                                     outputs=[master_result_md, master_out_audio])

        # ── SECTION 10: PARALLEL RENDER ──────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u26A1 PARALLEL RENDER</div>'
                f'<p>Leverage all {CPU_CORES["performance"]} performance cores for batch stem and pipeline rendering.</p>'
                '</div>'
                '<div class="df-inline-note">cpu-parallel batch</div>'
                '</div>'
            )
            with gr.Accordion("\u26A1 Parallel Render", open=False):
                with gr.Row():
                    render_type_dd = gr.Dropdown(
                        choices=["Pipeline Stems", "Batch Renders", "Full Build (All Modules)"],
                        value="Pipeline Stems", label="Render Type",
                    )
                    worker_sl = gr.Slider(
                        minimum=1, maximum=CPU_CORES["total"], step=1,
                        value=WORKERS_COMPUTE, label="Worker Cores",
                    )
                render_run_btn = gr.Button("Start Render", variant="primary")
                render_result_md = gr.Markdown("_Select type and click Start_")
                render_run_btn.click(fn=handle_parallel_render,
                                     inputs=[render_type_dd, worker_sl],
                                     outputs=[render_result_md])

        # ── SECTION 10B: VST3 STATE / FXP PRESETS ────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2699 VST3 PRESETS</div>'
                '<p>Export DUBFORGE Serum 2 patches as .fxp files, or import existing .fxp presets to inspect their parameter maps.</p>'
                '<div class="df-pill-row"><span class="df-pill">FXP export</span><span class="df-pill">FXP import</span><span class="df-pill">Serum 2</span></div>'
                '</div>'
                '<div class="df-inline-note">preset I/O</div>'
                '</div>'
            )
            with gr.Accordion("\u2699 Export FXP Preset", open=False):
                with gr.Row():
                    fxp_preset_dd = gr.Dropdown(choices=SERUM_PATCH_NAMES or ["(no patches)"],
                                                label="Select Patch", scale=2)
                    fxp_export_btn = gr.Button("Export .fxp", variant="primary", scale=1)
                fxp_export_info = gr.Markdown("")
                fxp_export_file = gr.File(label="Download FXP", visible=True)
                fxp_export_btn.click(fn=handle_export_fxp, inputs=[fxp_preset_dd],
                                     outputs=[fxp_export_info, fxp_export_file])
            with gr.Accordion("\u2699 Import FXP Preset", open=False):
                fxp_import_file = gr.File(label="Upload .fxp File", file_types=[".fxp"])
                fxp_import_btn = gr.Button("Inspect FXP", variant="secondary")
                fxp_import_info = gr.Markdown("")
                fxp_import_btn.click(fn=lambda f: handle_import_fxp(f.name if f else None),
                                     inputs=[fxp_import_file], outputs=[fxp_import_info])

        # ── SECTION 10C: SIDECHAIN CURVE VISUALIZER ──────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u2248 SIDECHAIN VISUALIZER</div>'
                '<p>Preview sidechain ducking curves for all 5 shapes — pump, hard_cut, smooth, bounce, phi_curve. Adjust depth and release to see the envelope in real time.</p>'
                '<div class="df-pill-row"><span class="df-pill">5 shapes</span><span class="df-pill">20 presets</span><span class="df-pill">phi-curve</span></div>'
                '</div>'
                '<div class="df-inline-note">ducking preview</div>'
                '</div>'
            )
            with gr.Accordion("\u2248 Sidechain Envelope Preview", open=False):
                with gr.Row():
                    sc_shape_dd = gr.Dropdown(choices=SIDECHAIN_SHAPES, value="pump", label="Shape", scale=1)
                    sc_depth_sl = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, value=0.9, label="Depth")
                    sc_release_sl = gr.Slider(minimum=10, maximum=500, step=5, value=150, label="Release (ms)")
                    sc_bpm_sl = gr.Slider(minimum=100, maximum=200, step=1, value=150, label="BPM")
                sc_preview_btn = gr.Button("Preview Curve", variant="secondary")
                sc_info_md = gr.Markdown("")
                sc_plot = gr.Plot(label="Sidechain Envelope")
                sc_preview_btn.click(fn=handle_sidechain_preview,
                                     inputs=[sc_shape_dd, sc_depth_sl, sc_release_sl, sc_bpm_sl],
                                     outputs=[sc_info_md, sc_plot])

        # ── SECTION 10D: MIX MODEL SELECTOR ─────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25CE MIX MODELS</div>'
                '<p>Select a mixing mental model to understand how elements should be balanced. Priority-Based (standard), Camera Focus (focal element), or Depth Staging (3D spatial).</p>'
                '</div>'
                '<div class="df-inline-note">mixing philosophy</div>'
                '</div>'
            )
            with gr.Accordion("\u25CE Mix Model Reference", open=False):
                mix_model_dd = gr.Dropdown(choices=MIX_MODELS, value="Priority-Based", label="Mix Model")
                mix_model_btn = gr.Button("Show Model", variant="secondary")
                mix_model_info = gr.Markdown("_Select a mix model._")
                mix_model_btn.click(fn=handle_mix_model, inputs=[mix_model_dd],
                                    outputs=[mix_model_info])

        # ── SECTION 11: SAMPLE LIBRARY ────────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25A6 SAMPLE LIBRARY</div>'
                '<p>Browse, search, and manage 26 sample categories + the GALATCIA collection.</p>'
                '</div>'
                '<div class="df-inline-note">26 categories</div>'
                '</div>'
            )
            with gr.Accordion("\u25A6 Sample Library", open=False):
                with gr.Row():
                    samp_scan_btn = gr.Button("Scan Library", variant="secondary")
                    samp_dl_btn = gr.Button("Download CC0 Starter Pack", variant="secondary")
                samp_info_md = gr.Markdown("_Click Scan_")
                samp_dl_md = gr.Markdown("")
                samp_scan_btn.click(fn=handle_sample_scan, outputs=[samp_info_md])
                samp_dl_btn.click(fn=handle_download_starter_pack, outputs=[samp_dl_md])
                gr.Markdown("### Browse by Category")
                with gr.Row():
                    samp_cat_dd = gr.Dropdown(choices=sorted(SAMPLE_CATEGORIES), label="Category")
                    samp_browse_btn = gr.Button("Browse", variant="secondary")
                samp_cat_md = gr.Markdown("")
                samp_browse_btn.click(fn=handle_browse_category, inputs=[samp_cat_dd], outputs=[samp_cat_md])
                gr.Markdown("### Search")
                with gr.Row():
                    samp_search_inp = gr.Textbox(label="Search", placeholder="wobble, dark, 808")
                    samp_search_btn = gr.Button("Search", variant="secondary")
                samp_search_md = gr.Markdown("")
                samp_search_btn.click(fn=handle_search_samples, inputs=[samp_search_inp], outputs=[samp_search_md])
                gr.Markdown("### GALATCIA Collection")
                galatcia_btn = gr.Button("Browse GALATCIA", variant="secondary")
                galatcia_md = gr.Markdown("")
                galatcia_btn.click(fn=handle_browse_galatcia, outputs=[galatcia_md])
                gr.Markdown("### Import from Directory")
                with gr.Row():
                    import_path_inp = gr.Textbox(label="Directory Path")
                    import_cat_dd = gr.Dropdown(choices=sorted(SAMPLE_CATEGORIES), label="Category")
                    import_btn = gr.Button("Import", variant="secondary")
                import_md = gr.Markdown("")
                import_btn.click(fn=handle_import_dir,
                                 inputs=[import_path_inp, import_cat_dd],
                                 outputs=[import_md])

        # ── SECTION 12: SYSTEM + PIPELINE ────────────────────
        with gr.Group(elem_classes=["df-shell"]):
            gr.HTML(
                '<div class="df-shell-header">'
                '<div class="df-shell-copy">'
                '<div class="df-section-title">\u25CE SYSTEM &amp; PIPELINE</div>'
                '<p>System status, CPU core info, and full 4-phase pipeline architecture overview.</p>'
                '</div>'
                '<div class="df-inline-note">system health</div>'
                '</div>'
            )
            with gr.Accordion("\u25CE System Info", open=False):
                sysinfo_md = gr.Markdown("_Click Refresh_")
                with gr.Row():
                    sysinfo_refresh_btn = gr.Button("Refresh System Info", variant="secondary")
                    quick_mod_dd = gr.Dropdown(choices=QUICK_MODULES, label="Quick Module Run")
                    quick_run_btn = gr.Button("Run Module", variant="secondary")
                quick_result_md = gr.Markdown("")
                sysinfo_refresh_btn.click(fn=handle_sysinfo, outputs=[sysinfo_md])
                quick_run_btn.click(fn=handle_quick_build, inputs=[quick_mod_dd], outputs=[quick_result_md])
                app.load(fn=handle_sysinfo, outputs=[sysinfo_md])
            _layout = build_dubstep_session()
            _reqs = get_template_requirements(_layout)
            with gr.Accordion("\u25CE 4-Phase Pipeline Architecture", open=False):
                gr.Markdown(f"""### DUBFORGE 4-Phase Production Pipeline

```
INPUT: Song Idea (name, mood, key, BPM, style, energy)
         │
   ┌─────▼──────────────────────────────────────────┐
   │  PHASE 1: GENERATION                          │
   │  Stage 1: IDENTITY — DNA, palette, recipe     │
   │  Stage 2: MIDI SEQUENCES — stems              │
   │  Stage 3: SYNTH FACTORY — wavetables, presets │
   │  Stage 4: DRUM FACTORY — 128 Rack, patterns  │
   │  OUTPUT: ALS + WAV stems                      │
   └─────┬──────────────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────────────┐
   │  PHASE 2: ARRANGEMENT — AbletonOSC            │
   │  DRUMS / BASS / MELODICS / FX / RETURNS       │
   │  OUTPUT: StemPack ({len(_layout.tracks)} tracks + {len(_layout.returns)} returns)        │
   └─────┬──────────────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────────────┐
   │  PHASE 3: MIXING — EQ, compress, sidechain    │
   │  OUTPUT: Mixed stereo WAV (24-bit)             │
   └─────┬──────────────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────────────┐
   │  PHASE 4: MASTERING — multiband, limiter, LUFS│
   │  OUTPUT: Final WAV — DANCEFLOOR READY          │
   └────────────────────────────────────────────────┘
```

### Session Template ({len(_layout.tracks)} tracks + {len(_layout.returns)} returns, {_reqs.total_bars} bars)
- **CPU**: {CPU_CORES['performance']}P + {CPU_CORES['efficiency']}E cores
- **PHI** = {PHI:.10f} | **A4** = {A4_432} Hz
- **Fibonacci** = {FIBONACCI[:13]}
- **Engine modules**: {len(TRACK_MODULES)} tracks wired
- **Gap modules**: {', '.join(list(GAP_MODULE_TRACKS.keys())[:8])}...
""")

        # ── FOOTER ───────────────────────────────────────────
        gr.HTML(
            '<div class="df-footer">'
            '<div class="df-sigil">DUBFORGE NEXUS v9.1.0 // Resonance Energy — Master App</div>'
            f'<div class="df-constants">\u03C6 = {PHI:.10f} &nbsp;|&nbsp; '
            f'A4 = {A4_432} Hz &nbsp;|&nbsp; '
            f'Fib = {FIBONACCI[:8]}</div>'
            '</div>'
        )

        # ── EVENT WIRING ─────────────────────────────────────

        # Intake outputs (16 components — URL cascades to mastering ref)
        _intake_outs = [intake_summary, audio_dna_output, chords_output, synth_output,
                        web_output, song_dna_output, intake_report,
                        song_name, style, mood, key, scale, bpm, tags_input, artist_notes,
                        master_ref_url]

        def _run_intake(audio_file, url, research):
            return handle_intake(audio_file, url, research)

        # Button click triggers intake
        intake_btn.click(fn=_run_intake,
            inputs=[intake_audio, intake_url, intake_research],
            outputs=_intake_outs)

        # Auto-trigger intake when user presses Enter in the URL field
        intake_url.submit(fn=_run_intake,
            inputs=[intake_audio, intake_url, intake_research],
            outputs=_intake_outs)

        _forge_outs = [
            progress_html, forge_files_html, forge_status, forge_dna,
            waveform_plot, forge_audio, mixx_btn, mix3_btn, master_btn,
            run_log_html, error_log_html,
        ]

        forge_btn.click(fn=handle_forge,
            inputs=[song_name, style, mood, key, scale, bpm, arrangement, tags_input, artist_notes],
            outputs=_forge_outs)

        mixx_btn.click(fn=handle_mixx, inputs=[], outputs=_forge_outs)
        mix3_btn.click(fn=handle_mix3, inputs=[], outputs=_forge_outs)
        master_btn.click(fn=handle_master, inputs=[], outputs=_forge_outs)

        # Archive report loading — wired here because master_ref_url is declared below archive
        load_report_btn.click(fn=handle_load_report, inputs=[report_dropdown],
            outputs=[intake_summary, audio_dna_output, chords_output, synth_output,
                     web_output, song_dna_output,
                     song_name, style, mood, key, scale, bpm, tags_input, artist_notes,
                     master_ref_url])

        # ── Reset progress panel on every page load ───────────────────────
        app.load(
            fn=lambda: (
                "",
                _file_card_html([]),
                "",
                "",
                gr.update(visible=False),
                None,
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                _run_log_html([]),
                _error_log_html([]),
            ),
            outputs=_forge_outs,
        )

    return app


def build_theme():
    _require_gradio()
    return gr.themes.Base(
        primary_hue=gr.themes.colors.purple,
        secondary_hue=gr.themes.colors.cyan,
        neutral_hue=gr.themes.colors.slate,
        font=[gr.themes.GoogleFont("Space Grotesk"), gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
        radius_size=gr.themes.sizes.radius_lg,
        text_size=gr.themes.sizes.text_md,
    )


def main():
    parser = argparse.ArgumentParser(description="DUBFORGE NEXUS v9.1.0 — Master App")
    parser.add_argument("--port", type=int, default=7861, help="Server port")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--share", action="store_true", help="Create public link")
    args = parser.parse_args()
    if not HAS_GRADIO:
        print("Gradio not installed. Run: pip install gradio")
        return
    app = build_ui()
    # Attach no-cache middleware so every page load is fresh — avoids stale
    # Gradio JS/state after a server restart without manual hard-reload.
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request as _Req

    class _NoCacheMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: _Req, call_next):
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            if "ETag" in response.headers:
                del response.headers["ETag"]
            return response

    app.app.add_middleware(_NoCacheMiddleware)
    # When spawned by forge.py --launch (DUBFORGE_LAUNCHER=1), let the launcher open
    # the browser so only one tab opens.  When run directly, open it ourselves.
    _open_browser = not os.environ.get("DUBFORGE_LAUNCHER")
    app.launch(server_name=args.host, server_port=args.port, share=args.share,
               inbrowser=_open_browser, css=THEME_CSS, theme=build_theme())


if __name__ == "__main__":
    main()
