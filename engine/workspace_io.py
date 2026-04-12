"""
engine/workspace_io.py — MWP/ICM Stage Artifact I/O

Filesystem-based handoff system. Output of stage N = input for stage N+1.
Every artifact is a human-editable markdown or JSON file in mwp/stages/XX/output/.

Usage:
    from engine.workspace_io import write_stage_output, read_stage_output, write_summary

    write_stage_output("01-generation", "song_mandate.json", {"name": "apology", ...})
    data = read_stage_output("01-generation", "song_mandate.json")
    write_summary("01-generation", ["✓ SongMandate complete", "10 stems bounced"])
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any

# Workspace root: engine/workspace_io.py → engine/ → DUBFORGE/ → mwp/stages/
_WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent / "mwp" / "stages"

STAGE_DIRS = {
    "01-generation": _WORKSPACE_ROOT / "01-generation",
    "02-arrangement": _WORKSPACE_ROOT / "02-arrangement",
    "03-mixing": _WORKSPACE_ROOT / "03-mixing",
    "04-mastering": _WORKSPACE_ROOT / "04-mastering",
}


def _output_dir(stage: str) -> pathlib.Path:
    """Resolve and create output directory for a stage."""
    if stage not in STAGE_DIRS:
        raise ValueError(f"Unknown stage '{stage}'. Valid: {list(STAGE_DIRS)}")
    out = STAGE_DIRS[stage] / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_stage_output(stage: str, filename: str, content: Any) -> pathlib.Path:
    """Write an artifact to mwp/stages/{stage}/output/{filename}.

    JSON files: content is serialized with json.dumps (default=str for non-serializable).
    All other files: content is written as str(content).

    Returns the Path where the artifact was written.
    """
    path = _output_dir(stage) / filename
    if filename.endswith(".json"):
        path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
    else:
        path.write_text(str(content), encoding="utf-8")
    return path


def read_stage_output(stage: str, filename: str) -> Any:
    """Read an artifact from mwp/stages/{stage}/output/{filename}.

    Returns parsed JSON for .json files, raw string otherwise.
    Returns None if the file does not exist.
    """
    path = _output_dir(stage) / filename
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if filename.endswith(".json"):
        return json.loads(text)
    return text


def write_summary(stage: str, lines: list[str]) -> pathlib.Path:
    """Write a human-readable stage_summary.md to mwp/stages/{stage}/output/."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"# Stage {stage} — Summary\n\n_Generated: {now}_\n\n"
    content = header + "\n".join(f"- {line}" for line in lines) + "\n"
    return write_stage_output(stage, "stage_summary.md", content)


# ── Phase-specific helpers ──────────────────────────────────────────────────

def write_phase_one_outputs(mandate: Any) -> None:
    """Write Phase 1 (GENERATION) artifacts from a SongMandate."""
    try:
        dna = mandate.dna
        stem_paths: dict[str, str] = {}

        # Collect all stem paths from mandate
        _kits = [
            ("drums", mandate.drums),
            ("bass", mandate.bass),
            ("leads", mandate.leads),
            ("atmosphere", mandate.atmosphere),
            ("fx", mandate.fx),
        ]
        for _kit_name, _kit in _kits:
            if _kit is None:
                continue
            if hasattr(_kit, "sounds"):
                for s in _kit.sounds:
                    if hasattr(s, "wav_path") and s.wav_path:
                        stem_paths[getattr(s, "name", _kit_name)] = str(s.wav_path)
            elif hasattr(_kit, "wav_path") and _kit.wav_path:
                stem_paths[_kit_name] = str(_kit.wav_path)

        # Also check stage5_renders (drum loop section renders)
        stage5_renders: dict = {}
        if hasattr(mandate, "stage5_renders") and mandate.stage5_renders:
            for sec, hits in mandate.stage5_renders.items():
                stage5_renders[sec] = {k: str(v) for k, v in hits.items()}

        # audio_manifest
        audio_manifest_obj = mandate.audio_manifest if hasattr(mandate, "audio_manifest") else None
        manifest_data: dict[str, Any]
        if audio_manifest_obj is not None:
            manifest_data = {
                "total": getattr(audio_manifest_obj, "total", 0),
                "delivered": getattr(audio_manifest_obj, "delivered_count", 0),
                "stems": stem_paths,
                "pending": [str(p) for p in getattr(audio_manifest_obj, "pending", [])],
            }
        else:
            manifest_data = {"total": len(stem_paths), "delivered": len(stem_paths),
                             "stems": stem_paths, "pending": []}

        # song_mandate summary
        mandate_summary = {
            "name": dna.name,
            "style": dna.style,
            "key": dna.key,
            "scale": dna.scale,
            "bpm": dna.bpm,
            "root_freq": dna.root_freq,
            "total_bars": mandate.total_bars,
            "sections": dict(mandate.sections) if mandate.sections else {},
            "groove_template": mandate.groove_template,
            "arrange_tasks": list(mandate.arrange_tasks)[:20],  # cap for readability
            "als_path": str(mandate.stage5_als_path) if hasattr(mandate, "stage5_als_path")
                        and mandate.stage5_als_path else "",
        }

        write_stage_output("01-generation", "song_mandate.json", mandate_summary)
        write_stage_output("01-generation", "audio_manifest.json", manifest_data)

        als_path = mandate_summary["als_path"]
        if als_path:
            write_stage_output("01-generation", "als_path.txt", als_path)

        write_summary("01-generation", [
            f"SongMandate complete: {dna.name} [{dna.style}, {dna.key} {dna.scale}, {dna.bpm}bpm]",
            f"{mandate.total_bars} bars, {len(mandate.sections or {})} sections",
            f"Stems: {manifest_data['delivered']}/{manifest_data['total']} delivered",
            f"Pending: {len(manifest_data['pending'])} files",
            f"ALS: {als_path or '(not yet generated)'}",
        ])
    except Exception as exc:
        print(f"  ⚠ workspace_io.write_phase_one_outputs: {exc}")


def write_phase_two_outputs(arranged: Any) -> None:
    """Write Phase 2 (ARRANGEMENT) artifacts from an ArrangedTrack."""
    try:
        track_data = {
            "kick_positions": list(arranged.kick_positions or [])[:100],
            "section_map": dict(arranged.section_map or {}),
            "total_bars": arranged.total_bars,
            "wav_path": str(arranged.wav_path) if getattr(arranged, "wav_path", None) else "",
            "elapsed_s": round(getattr(arranged, "elapsed_s", 0.0), 2),
        }

        stem_paths: dict[str, str] = {}
        if hasattr(arranged, "stem_paths") and arranged.stem_paths:
            stem_paths = {k: str(v) for k, v in arranged.stem_paths.items()}

        write_stage_output("02-arrangement", "arranged_track.json", track_data)
        write_stage_output("02-arrangement", "stems_manifest.json", stem_paths)

        write_summary("02-arrangement", [
            f"ArrangedTrack complete: {arranged.total_bars} bars",
            f"Kick positions: {len(track_data['kick_positions'])} hits",
            f"Sections: {list(arranged.section_map.keys()) if arranged.section_map else '[]'}",
            f"Stems: {len(stem_paths)} bounced",
            f"Bounce: {track_data['wav_path'] or '(not yet bounced — open ALS and export)'}",
            f"Elapsed: {track_data['elapsed_s']}s",
        ])
    except Exception as exc:
        print(f"  ⚠ workspace_io.write_phase_two_outputs: {exc}")


def write_phase_three_outputs(mixed: Any) -> None:
    """Write Phase 3 (MIXING) artifacts from a MixedTrack."""
    try:
        mix_data = {
            "kick_positions": list(getattr(mixed, "kick_positions", []) or [])[:100],
            "section_map": dict(getattr(mixed, "section_map", {}) or {}),
            "total_bars": getattr(mixed, "total_bars", 0),
            "wav_path": str(mixed.wav_path) if getattr(mixed, "wav_path", None) else "",
            "mix_analysis": dict(getattr(mixed, "mix_analysis", {}) or {}),
            "elapsed_s": round(getattr(mixed, "elapsed_s", 0.0), 2),
        }

        write_stage_output("03-mixing", "mixed_track.json", mix_data)

        wav_status = mix_data["wav_path"] or "(not yet bounced — open ALS and export)"
        write_summary("03-mixing", [
            f"MixedTrack complete: {mix_data['total_bars']} bars",
            f"Mix bounce: {wav_status}",
            f"Status: {mix_data['mix_analysis'].get('status', 'unknown')}",
            f"Stems loaded: {mix_data['mix_analysis'].get('stems_loaded', '?')}",
            f"Elapsed: {mix_data['elapsed_s']}s",
        ])
    except Exception as exc:
        print(f"  ⚠ workspace_io.write_phase_three_outputs: {exc}")


def write_phase_four_outputs(out_path: str, report_card: dict | None = None,
                              belt: dict | None = None, dna: Any = None) -> None:
    """Write Phase 4 (MASTERING) artifacts."""
    try:
        master_info: dict[str, Any] = {
            "track_name": getattr(dna, "name", "untitled") if dna else "untitled",
            "final_wav": str(out_path) if out_path else "",
            "phi_normalized": True,
        }
        if report_card:
            master_info.update({
                "grade": report_card.get("grade", "?"),
                "overall_score": report_card.get("overall_score", 0),
            })
        if belt:
            master_info.update({
                "belt": belt.get("current_belt", "white"),
                "promoted": belt.get("promoted", False),
            })

        write_stage_output("04-mastering", "master_info.json", master_info)

        # Write report card as markdown
        if report_card:
            lines = [f"# Report Card — {master_info['track_name']}",
                     f"\nGrade: **{master_info.get('grade', '?')}** "
                     f"({master_info.get('overall_score', '?')}/100)",
                     f"\nBelt: {master_info.get('belt', 'white').upper()}",
                     f"{'**PROMOTED!**' if master_info.get('promoted') else ''}"]
            write_stage_output("04-mastering", "report_card.md", "\n".join(lines))

        write_summary("04-mastering", [
            f"Mastering complete: {master_info['track_name']}",
            f"Final WAV: {master_info['final_wav'] or '(see output/)'}",
            f"Grade: {master_info.get('grade', '?')} ({master_info.get('overall_score', '?')}/100)",
            f"Belt: {master_info.get('belt', 'white').upper()}",
        ])
    except Exception as exc:
        print(f"  ⚠ workspace_io.write_phase_four_outputs: {exc}")
