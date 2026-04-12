"""forge_runner.py — Subprocess entry point for DUBFORGE forge pipeline.

Reads a SongBlueprint JSON LINE from stdin, executes all 4 phases with
inter-phase human-gate pauses, and streams output to the parent via
line-by-line pipe.

Sentinel lines emitted to stdout:
    __FILE_READY__ {json}    — new output file detected (WAV/MIDI/ALS/JSON)
    __PHASE1_DONE__ {json}   — phase 1 complete, stats for display
    __PHASE2_DONE__ {json}   — phase 2 complete
    __PHASE3_DONE__ {json}   — phase 3 complete
    __PHASE4_DONE__ {json}   — phase 4 complete
    __ABORTED__     {json}   — gate received unexpected signal

Gate protocol (stdin — parent sends one line per gate):
    Line 1: blueprint JSON
    Line 2: "GO_PHASE2"  — user approved Phase 1, proceed
    Line 3: "GO_PHASE3"  — user approved Phase 2, proceed
    Line 4: "GO_PHASE4"  — user approved Phase 3, proceed

Usage (internal — launched by dubstep_analyzer_ui.py):
    python tools/forge_runner.py  (stdin = command channel)
"""
from __future__ import annotations

import json
import sys
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path

# Ensure repo root is on sys.path when run as subprocess
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))



def _emit(sentinel: str, payload: dict) -> None:
    print(f"{sentinel} {json.dumps(payload)}", flush=True)


_WATCH_EXTS = frozenset({".wav", ".mid", ".midi", ".als", ".json", ".xml"})
_WATCH_MIN_BYTES = 512


def _start_file_watcher(
    stop_event: threading.Event, seen: set, phase_num: int
) -> threading.Thread:
    """Background thread: poll output/ and emit __FILE_READY__ for new files."""
    def _watch() -> None:
        watch_root = Path("output")
        while not stop_event.is_set():
            try:
                if watch_root.exists():
                    for f in watch_root.rglob("*.*"):
                        key = str(f)
                        if key in seen:
                            continue
                        seen.add(key)
                        try:
                            sz = f.stat().st_size
                        except OSError:
                            continue
                        if sz < _WATCH_MIN_BYTES:
                            continue
                        if f.suffix.lower() in _WATCH_EXTS:
                            _emit("__FILE_READY__", {
                                "path": key,
                                "name": f.name,
                                "size_kb": round(sz / 1024, 1),
                                "kind": f.suffix.lstrip(".").upper(),
                                "phase": phase_num,
                            })
            except Exception:
                pass
            time.sleep(0.5)
    t = threading.Thread(target=_watch, daemon=True)
    t.start()
    return t


def _gate(expected: str) -> bool:
    """Block stdin until parent sends the expected gate string.  Returns False on mismatch/EOF."""
    try:
        line = sys.stdin.readline().strip()
        if line == expected:
            return True
        if line:
            _emit("__ABORTED__", {"reason": f"Expected {expected!r}, got {line!r}"})
        else:
            _emit("__ABORTED__", {"reason": "stdin closed before gate signal"})
        return False
    except Exception as exc:
        _emit("__ABORTED__", {"reason": str(exc)})
        return False


def _exec_phase(phase_num: int, phase_fn, seen: set, *phase_args):
    """Run a phase function with file-watching + error sentinel emit.

    Starts a background watcher thread, calls phase_fn(*phase_args), stops
    the watcher, and returns the result.  On any exception, emits
    __PHASE{N}_ERROR__ and exits with code phase_num.
    """
    stop = threading.Event()
    _start_file_watcher(stop, seen, phase_num)
    try:
        return phase_fn(*phase_args)
    except Exception as exc:
        _emit(f"__PHASE{phase_num}_ERROR__", {
            "error": str(exc),
            "tb": traceback.format_exc(),
        })
        sys.exit(phase_num)
    finally:
        stop.set()


def main() -> None:
    raw = sys.stdin.readline()   # blueprint JSON on first line
    data = json.loads(raw)

    from engine.variation_engine import SongBlueprint
    blueprint = SongBlueprint(
        name=data["name"],
        style=data.get("style", "dubstep"),
        theme=data.get("theme", ""),
        mood=data.get("mood", ""),
        sound_style=data.get("sound_style", ""),
        key=data.get("key", ""),
        scale=data.get("scale", ""),
        bpm=int(data.get("bpm", 0)),
        arrangement=data.get("arrangement", ""),
        tags=data.get("tags", []),
        seed=int(data.get("seed", 0)),
        notes=data.get("notes", ""),
    )

    # Pre-populate seen_files with every file already on disk so the watcher
    # only emits __FILE_READY__ for files created by THIS run, not old outputs.
    seen_files: set = {str(f) for f in Path("output").rglob("*.*") if f.is_file()} if Path("output").exists() else set()

    # ── Phase 1 ──────────────────────────────────────────────────────────
    from engine.phase_one import run_phase_one
    stop1 = threading.Event()
    _start_file_watcher(stop1, seen_files, phase_num=1)
    try:
        # If a pre-built SongDNA was passed (from reference intake),
        # use it directly to maximise emulation fidelity.
        song_dna = None
        if data.get("song_dna"):
            try:
                from engine.variation_engine import (  # noqa: PLC0415
                    ArrangementSection, AtmosphereDNA, BassDNA,
                    DrumDNA, FxDNA, LeadDNA, MixDNA, SongDNA,
                )
                d = dict(data["song_dna"])
                arrangement = [ArrangementSection(**s) for s in d.pop("arrangement", [])]
                drums = DrumDNA(**d.pop("drums", {}))
                bass = BassDNA(**d.pop("bass", {}))
                lead = LeadDNA(**d.pop("lead", {}))
                atmosphere = AtmosphereDNA(**d.pop("atmosphere", {}))
                fx = FxDNA(**d.pop("fx", {}))
                mix = MixDNA(**d.pop("mix", {}))
                d.pop("freq_table", None)  # rebuilt by phase_one
                song_dna = SongDNA(
                    arrangement=arrangement,
                    drums=drums, bass=bass, lead=lead,
                    atmosphere=atmosphere, fx=fx, mix=mix,
                    **d,
                )
            except Exception as _de:
                print(f"[forge_runner] SongDNA deserialize warning: {_de}", flush=True)
        mandate = run_phase_one(dna=song_dna) if song_dna else run_phase_one(blueprint=blueprint)
    except Exception as exc:
        stop1.set()
        _emit("__PHASE1_ERROR__", {"error": str(exc), "tb": traceback.format_exc()})
        sys.exit(1)
    finally:
        stop1.set()

    dna = mandate.dna

    # ── Artwork generation (Phase 1 deliverable) ──────────────────────────
    artwork_files: dict[str, str] = {}
    try:
        from engine.artwork_generator import generate_full_artwork  # noqa: PLC0415
        track_name = dna.name or blueprint.name
        artist_name = getattr(dna, "artist", "") or "RESONANCE ENERGY"
        # Pick palette based on mood/style
        style_lower = (dna.style or "").lower()
        palette = "neon" if "melodic" in style_lower else ("void" if "cemetery" in style_lower else "obsidian")
        # Use analyzer-derived energy if available; fallback to BPM formula
        _dna_energy = getattr(dna, 'energy', None)
        energy = _dna_energy if _dna_energy is not None else (
            min(1.0, max(0.5, (dna.bpm - 120) / 80)) if dna.bpm else 0.85
        )
        # Darkness from analyzer atmosphere (inverted pad_brightness); fallback by style
        _pad_brightness = getattr(getattr(dna, 'atmosphere', None), 'pad_brightness', None)
        if _pad_brightness is not None:
            darkness = round(max(0.0, min(1.0, 1.0 - _pad_brightness)), 2)
        else:
            darkness = 0.9 if any(s in style_lower for s in ("riddim", "tearout", "void", "cemetery")) else 0.75
        artwork_files = generate_full_artwork(
            track_name=track_name,
            artist_name=artist_name,
            palette_name=palette,
            output_dir=f"output/{track_name.replace(' ', '_').lower()}/press",
            energy=energy,
            darkness=darkness,
        )
        # Emit each artwork file so the UI file-watcher picks them up
        for asset_name, file_path in artwork_files.items():
            from pathlib import Path as _Path  # noqa: PLC0415
            try:
                p = _Path(file_path)
                _emit("__FILE_READY__", {
                    "path": file_path,
                    "name": p.name,
                    "size_kb": round(p.stat().st_size / 1024, 1),
                    "kind": p.suffix.lstrip(".").upper(),
                    "phase": 1,
                    "label": asset_name,
                })
            except Exception:
                pass
    except Exception as _ae:
        print(f"[forge_runner] artwork warning: {_ae}", flush=True)
    als_paths: list[str] = []
    for attr in ("render_als_path", "stage5_als_path", "production_als_path"):
        v = getattr(mandate, attr, None)
        if v:
            als_paths.append(str(v))

    manifest = mandate.audio_manifest
    delivered_paths = [
        str(f.path) for f in manifest.files if f.delivered and f.path
    ]

    try:
        dna_json = json.dumps(asdict(dna), default=str)[:8000]
    except Exception:
        dna_json = str(dna)[:8000]

    sections_str = " → ".join(
        f"{k}({v})" for k, v in mandate.sections.items()
    ) if mandate.sections else "(none)"

    _emit("__PHASE1_DONE__", {
        "song_name":      dna.name,
        "style":          dna.style,
        "mood":           getattr(dna, "mood_name", ""),
        "key":            dna.key,
        "scale":          getattr(dna, "scale", ""),
        "bpm":            dna.bpm,
        "total_bars":     mandate.total_bars,
        "bar_s":          getattr(mandate, "bar_s", 2.0),
        "sections":       sections_str,
        "preset_count":   len(mandate.serum2_presets),
        "stem_count":     len(mandate.stem_configs),
        "midi_notes":     sum(len(v) for v in mandate.midi_sequences.values()),
        "active_stems":   sum(1 for v in mandate.midi_sequences.values() if v),
        "render_secs":    len(mandate.render_patterns),
        "render_hits":    sum(
            sum(len(h) for h in zones.values())
            for zones in mandate.render_patterns.values()
        ),
        "rack_slots":     sum(mandate.rack_128.zone_counts.values()) if mandate.rack_128 else 0,
        "wt_frames":      len(mandate.wavetables.frames),
        "wt_packs":       len(mandate.wavetable_packs),
        "mod_routes":     sum(
            len(v.get("mod_matrix", [])) for v in mandate.modulation_routes.values()
        ),
        "fx_slots":       sum(
            len(v) for v in mandate.fx_chains.values() if isinstance(v, list)
        ),
        "drum_patterns":  len(mandate.drum_loops.patterns),
        "als_paths":      als_paths,
        "delivered_paths": delivered_paths[:30],
        "dna_json":       dna_json,
        # Artwork assets generated in Phase 1
        "artwork_files":  artwork_files,
        # Audit: stem names present
        "stem_names":     list(mandate.stem_configs.keys())[:20],
        # Audit: wavetable pack names
        "wt_pack_names":  [getattr(p, "name", str(p)) for p in mandate.wavetable_packs][:10],
        # Audit: sequence names
        "sequence_names": [k for k, v in mandate.midi_sequences.items() if v][:20],
    })

    # ── Gate: wait for user to approve Phase 1 output ────────────────────
    if not _gate("GO_PHASE2"):
        sys.exit(0)

    # ── Phase 2 ──────────────────────────────────────────────────────────
    from engine.phase_two import run_phase_two  # noqa: PLC0415
    arranged = _exec_phase(2, run_phase_two, seen_files, mandate)

    _emit("__PHASE2_DONE__", {
        "total_bars": getattr(arranged, "total_bars", 0),
    })

    # ── Gate: wait for user to approve Phase 2 output ────────────────────
    if not _gate("GO_PHASE3"):
        sys.exit(0)

    # ── Phase 3 ──────────────────────────────────────────────────────────
    from engine.phase_three import run_phase_three  # noqa: PLC0415
    mixed = _exec_phase(3, run_phase_three, seen_files, arranged, mandate)

    _emit("__PHASE3_DONE__", {
        "wav_path": str(getattr(mixed, "wav_path", "")),
    })

    # ── Gate: wait for user to approve Phase 3 output ────────────────────
    if not _gate("GO_PHASE4"):
        sys.exit(0)

    # ── Phase 4 ──────────────────────────────────────────────────────────
    from engine.phase_four import run_phase_four  # noqa: PLC0415
    out_path = _exec_phase(4, run_phase_four, seen_files, mixed, mandate)

    _emit("__PHASE4_DONE__", {
        "out_path": str(out_path),
    })


if __name__ == "__main__":
    main()
