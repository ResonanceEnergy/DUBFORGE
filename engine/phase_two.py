# pyright: basic, reportUndefinedVariable=false
"""DUBFORGE — Phase 2: ARRANGEMENT via AbletonOSC

MWP v6.0.0 — ALL phases AbletonOSC. No numpy DSP fallback.
Cardinal Rule 2: Ableton Live IS the engine.

Entry point: run_phase_two(mandate) → ArrangedTrack

Pipeline:
    1. Connect AbletonBridge to Ableton Live
    2. Open Phase 1 render ALS in Ableton
    3. Place WAV stems in Arrangement View per section map
    4. Write section volume automation (subtractive map)
    5. Configure returns (reverb/delay sends)
    6. Set loop region + trigger export via osascript (Cmd+Shift+R)
    7. Poll for output WAV, return ArrangedTrack
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SR = 48000


# ═══════════════════════════════════════════════════════════════
#  Data contracts
# ═══════════════════════════════════════════════════════════════

@dataclass
class ArrangedTrack:
    """Output of Phase 2 — arrangement ready for Phase 3 mixing.

    stem_paths: individual stem WAV paths (from Phase 1 bounce or Phase 2 bounce)
    wav_path: full arrangement mixdown WAV (from Ableton bounce), if available
    L/R: kept for backward compat but not populated by AbletonOSC path
    """
    kick_positions: list[int]
    section_map: dict[str, int]
    total_bars: int
    total_samples: int
    dna: Any
    stem_paths: dict[str, str] = field(default_factory=dict)
    wav_path: str = ""                # full arrangement bounce WAV
    track_indices: dict[str, int] = field(default_factory=dict)  # Ableton track index map
    L: list[float] = field(default_factory=list)   # compat — empty if Ableton path
    R: list[float] = field(default_factory=list)   # compat — empty if Ableton path
    _subtract_map: dict = field(default_factory=dict)
    _energy_curve: Any = None
    elapsed_s: float = 0.0
    _session_arrangement: Any = None


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _build_section_map(mandate) -> tuple[dict[str, int], int]:
    """Extract section bar lengths from SongMandate."""
    sec_map: dict[str, int] = {}
    if hasattr(mandate, 'arrangement_template') and mandate.arrangement_template:
        for sec in mandate.arrangement_template.sections:
            sec_map[sec.name] = sec.bars
    elif hasattr(mandate, 'sections') and mandate.sections:
        sec_map = dict(mandate.sections)

    defaults = {"intro": 8, "build": 4, "drop1": 16,
                "breakdown": 8, "build2": 4, "drop2": 16, "outro": 8}
    for k, v in defaults.items():
        sec_map.setdefault(k, v)

    total_bars = sum(sec_map.values())
    return sec_map, total_bars


def _section_map_to_beats(section_map: dict[str, int]) -> dict[str, float]:
    """Convert section bar map to cumulative beat offsets."""
    order = ["intro", "build", "build_1", "drop1", "drop_1",
             "breakdown", "build2", "build_2", "drop2", "drop_2", "outro"]
    offsets: dict[str, float] = {}
    cursor = 0.0
    for name in order:
        if name in section_map:
            offsets[name] = cursor
            cursor += section_map[name] * 4.0
    # Any remaining sections not in order list
    for name, bars in section_map.items():
        if name not in offsets:
            offsets[name] = cursor
            cursor += bars * 4.0
    return offsets


def _extract_kick_positions(mandate, bpm: float) -> list[int]:
    """Estimate kick sample positions from MIDI sequences or drum rack data."""
    kick_positions: list[int] = []
    beat_samples = int(SR * 60.0 / max(bpm, 1.0))

    midi_seqs = getattr(mandate, 'midi_sequences', {}) or {}
    kick_seq = midi_seqs.get('kick') or midi_seqs.get('drums') or []
    if kick_seq:
        for note in kick_seq:
            beat = note.get('start_time', 0.0) if isinstance(note, dict) else getattr(note, 'start_time', 0.0)
            kick_positions.append(int(beat * beat_samples))
    else:
        # Fallback: halftime kick at beat 1 and 3 of every bar
        section_map, total_bars = _build_section_map(mandate)
        for bar in range(total_bars):
            for beat in [0, 2]:
                kick_positions.append((bar * 4 + beat) * beat_samples)

    return kick_positions


def _compute_subtractive_map(mandate, section_map: dict[str, int]) -> dict[str, dict[str, float]]:
    """Compute volume levels per stem per section (1.0 = full, 0.0 = muted)."""
    try:
        from engine.stage_integrations import compute_subtractive_map as _csm
        dna = mandate.dna
        return _csm({}, dna, {})
    except Exception:
        pass

    # Fallback: section/stem volume map per dubstep arrangement
    # Derive peak levels from DNA mix data (dB → linear scale)
    import math as _math
    _dna = getattr(mandate, 'dna', None)
    _md = getattr(_dna, 'mix', None) if _dna else None

    def _db_scale(db: float) -> float:
        return round(_math.pow(10.0, max(-18.0, min(6.0, db)) / 20.0), 3)

    _sub  = _db_scale(getattr(_md, 'sub_gain_db',  0.0)) if _md else 1.0
    _bass = _db_scale(getattr(_md, 'bass_gain_db', 0.0)) if _md else 1.0
    _lead = _db_scale(getattr(_md, 'lead_gain_db', 0.0)) if _md else 1.0
    _pad  = _db_scale(getattr(_md, 'pad_gain_db',  0.0)) if _md else 1.0

    full = {
        "kick": 1.0, "snare": 1.0, "hats": 1.0, "perc": 1.0,
        "sub_bass": _sub, "mid_bass": _bass,
        "neuro": _bass, "wobble": _bass, "riddim": _bass,
        "lead": _lead, "chords": _lead,
        "pad": _pad, "arps": _pad, "supersaw": _lead,
        "fx_risers": 1.0,
    }
    intro = {**full, "neuro": 0.0, "wobble": 0.0, "riddim": 0.0, "lead": 0.0,
             "chords": 0.3, "kick": 0.5, "sub_bass": 0.4, "mid_bass": 0.4}
    build = {**full, "neuro": 0.0, "wobble": 0.0, "riddim": 0.0,
             "lead": 0.5, "sub_bass": 0.5}
    drop = full
    breakdown = {**full, "kick": 0.0, "snare": 0.4, "sub_bass": 0.0,
                 "mid_bass": 0.0, "neuro": 0.0, "wobble": 0.0, "riddim": 0.0,
                 "lead": 0.5, "pad": 1.0, "supersaw": 0.0}
    outro = {**intro, "fx_risers": 0.0}

    return {
        "intro":      intro,
        "build":      build,  "build_1": build,
        "drop1":      drop,   "drop_1": drop,
        "breakdown":  breakdown,
        "build2":     build,  "build_2": build,
        "drop2":      drop,   "drop_2": drop,
        "outro":      outro,
    }


def _open_als_in_ableton(als_path: str) -> bool:
    """Open an ALS file in Ableton Live 12 via osascript."""
    abs_path = str(Path(als_path).resolve())
    # Auto-detect installed Ableton edition to avoid hardcoded app name
    try:
        from engine.ableton_session import detect_ableton_app as _det_app
        _app = _det_app()
    except Exception:
        _app = "Ableton Live 12 Standard"
    script = f'''
    tell application "{_app}"
        activate
        open POSIX file "{abs_path}"
    end tell
    '''
    try:
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"    ⚠ osascript open failed: {e}")
        return False


def _trigger_export_and_wait(output_path: str,
                              timeout_s: float = 120.0,
                              total_beats: float = 256.0) -> str:
    """Trigger Ableton Export Audio/Video (Cmd+Shift+R) via osascript, poll for output.

    AbletonOSC cannot directly trigger export — this uses macOS System Events.
    Ableton's export dialog must use default settings (or be pre-configured).
    """
    script = '''
    tell application "Ableton Live 12 Suite" to activate
    delay 0.5
    tell application "System Events"
        key code 15 using {command down, shift down}
        delay 1.5
        key code 36
    end tell
    '''
    try:
        out_dir = str(Path(output_path).parent)
        os.makedirs(out_dir, exist_ok=True)

        subprocess.run(['osascript', '-e', script],
                       capture_output=True, text=True, timeout=15)
        print(f"    → Export triggered. Waiting for output (~{int(total_beats / 4 / 2)}s)...")

        # Poll for output file
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(2.0)
            # Check the expected output path or any new WAV in output dir
            if Path(output_path).exists():
                return output_path
            # Also check if Ableton wrote to a default location
            candidates = sorted(Path(out_dir).glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                newest = candidates[0]
                if time.time() - newest.stat().st_mtime < 30:
                    return str(newest)

        print("    ⚠ Export timeout — file not found.")
        return ""
    except Exception as e:
        print(f"    ⚠ Export trigger failed: {e}")
        return ""


def _write_section_automation(bridge, track_indices: dict[str, int],
                               subtractive: dict[str, dict[str, float]],
                               section_map: dict[str, int],
                               bpm: float):
    """Write track volume automation per section via AbletonBridge.

    Uses multiple set_track_volume calls at section boundaries.
    Note: This sets the current volume — for real per-section automation,
    ALS XML-baked envelopes (via als_generator) are more reliable.
    """
    beat_offsets = _section_map_to_beats(section_map)
    for section_name, beat_offset in beat_offsets.items():
        levels = subtractive.get(section_name, {})
        for stem_name, level in levels.items():
            track_idx = track_indices.get(stem_name)
            if track_idx is None:
                continue
            # AbletonOSC: 0.85 = 0 dB, scale accordingly
            volume = 0.85 * max(0.0, min(1.0, level))
            bridge.set_track_volume(track_idx, volume)
        time.sleep(0.01)  # throttle OSC messages


def _setup_return_tracks(bridge, mandate, track_indices: dict[str, int]) -> dict[str, int]:
    """Create reverb + delay return tracks and configure sends."""
    return_map: dict[str, int] = {}
    try:
        rev_idx = bridge.create_return_track("REV")
        return_map["reverb"] = rev_idx
        dly_idx = bridge.create_return_track("DLY")
        return_map["delay"] = dly_idx
        print(f"    ✓ Returns: REV={rev_idx}, DLY={dly_idx}")

        # Send pads/leads to reverb, leads to delay
        send_map = {
            "pad": (0.4, 0.1), "lead": (0.2, 0.3), "chords": (0.15, 0.1),
            "arps": (0.1, 0.2), "fx_risers": (0.5, 0.0),
        }
        for stem_name, (rev_amt, dly_amt) in send_map.items():
            t = track_indices.get(stem_name)
            if t is not None:
                bridge.set_track_send(t, rev_idx, rev_amt)
                bridge.set_track_send(t, dly_idx, dly_amt)
    except Exception as e:
        print(f"    ⚠ Return setup partial: {e}")
    return return_map


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

def run_phase_two(mandate) -> ArrangedTrack:
    """Phase 2: ARRANGEMENT via AbletonOSC.

    MWP v6.0.0 — Ableton Live IS the engine.

    Steps:
        1. Connect AbletonBridge to Ableton Live
        2. Open Phase 1 render ALS
        3. Create audio tracks + place WAV stems in Arrangement View
        4. Write section volume automation (subtractive map)
        5. Configure return tracks (reverb/delay sends)
        6. Set loop region, trigger Ableton export via osascript
        7. Return ArrangedTrack with stem_paths + kick_positions

    If Ableton is not running: session config is skipped, Phase 1
    audio_manifest WAVs are forwarded directly to Phase 3.
    """
    t0 = time.perf_counter()
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  PHASE 2: ARRANGEMENT   (AbletonOSC)                ║")
    print("╚══════════════════════════════════════════════════════╝")

    from engine.ableton_bridge import AbletonBridge

    dna = mandate.dna
    bpm = float(dna.bpm)

    # Phase 1 delivers AudioManifest (dataclass); convert to dict[str, str]
    # mapping stem_name → wav_path for delivered stems.
    _raw_manifest = getattr(mandate, 'audio_manifest', None)
    if _raw_manifest is not None and hasattr(_raw_manifest, 'files'):
        # AudioManifest object — extract delivered stems
        audio_manifest: dict[str, str] = {
            f.name: str(f.path) for f in _raw_manifest.files
            if f.delivered and f.path
        }
    elif isinstance(_raw_manifest, dict):
        audio_manifest = _raw_manifest
    else:
        audio_manifest = {}
    stem_configs: dict[str, dict] = getattr(mandate, 'stem_configs', {}) or {}
    section_map, total_bars = _build_section_map(mandate)
    total_beats = float(total_bars * 4)
    kick_positions = _extract_kick_positions(mandate, bpm)
    subtractive = _compute_subtractive_map(mandate, section_map)

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in dna.name).strip().replace(" ", "_") or "dubforge"
    out_dir = Path("output") / safe_name / "phase2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Ensure a fresh Ableton session for Phase 2 ──────────────────────────
    _als_template = (getattr(mandate, 'render_als_path', None)
                     or getattr(mandate, 'stage5_als_path', None)
                     or getattr(mandate, 'production_als_path', None))
    try:
        from engine.ableton_session import ensure_fresh_ableton_session
        _ableton_ready = ensure_fresh_ableton_session(
            template_als=str(_als_template) if _als_template else None,
        )
        if not _ableton_ready:
            print("  ⚠ Phase 2: Ableton not ready — arrangement will skip OSC steps")
    except Exception as _ses_exc:
        print(f"  ⚠ Phase 2 session setup skipped: {_ses_exc}")
    # ─────────────────────────────────────────────────────────────────────────

    bridge = AbletonBridge(verbose=True)
    connected = bridge.connect()
    track_indices: dict[str, int] = {}
    wav_path = ""

    if connected:
        print("  ✓ Ableton Live connected")

        # 1. Set session tempo + time sig
        bridge.set_tempo(bpm)
        bridge.set_time_signature(4, 4)
        bridge.set_metronome(False)
        bridge.show_arrangement()

        # 2. ALS already opened by ensure_fresh_ableton_session above
        als_path = (getattr(mandate, 'render_als_path', None)
                    or getattr(mandate, 'stage5_als_path', None)
                    or getattr(mandate, 'production_als_path', None))
        if als_path and Path(als_path).exists():
            print(f"  → ALS loaded: {als_path}")
        else:
            print("  ⚠ No render ALS path from Phase 1 — using fresh session")

        # 3. Create audio tracks + place WAV stems
        print(f"  → Placing {len(audio_manifest)} stems in Arrangement View...")
        for stem_name, wav in audio_manifest.items():
            if not wav or not Path(wav).exists():
                print(f"    ⚠ {stem_name}: WAV not found ({wav})")
                continue
            track_idx = bridge.create_audio_track(-1, stem_name.upper())
            track_indices[stem_name] = track_idx

            cfg = stem_configs.get(stem_name, {})
            vol = 0.85 * max(0.0, min(1.0, float(cfg.get('volume', 1.0))))
            pan = float(cfg.get('pan', 0.0))
            bridge.set_track_volume(track_idx, vol)
            bridge.set_track_pan(track_idx, pan)

            # Place audio clip at beat 0 (full arrangement length)
            bridge.create_arrangement_audio_clip(track_idx, str(Path(wav).resolve()), 0.0)
            print(f"    ✓ {stem_name} → track {track_idx}")

        # 4. Write section automation
        print("  → Writing section volume automation...")
        _write_section_automation(bridge, track_indices, subtractive, section_map, bpm)

        # 5. Configure returns
        print("  → Setting up return tracks...")
        _setup_return_tracks(bridge, mandate, track_indices)

        # 6. Set loop region + trigger export
        bridge.set_loop(True, 0.0, total_beats)
        print(f"  → Loop: 0 → {total_beats} beats ({total_bars} bars @ {bpm} BPM)")

        bounce_path = str(out_dir / f"{safe_name}_arranged.wav")
        print(f"  → Triggering Ableton export → {bounce_path}")
        wav_path = _trigger_export_and_wait(bounce_path, timeout_s=180.0,
                                            total_beats=total_beats)
        if wav_path:
            print(f"  ✓ Arrangement bounce: {wav_path}")
        else:
            print("  ⚠ Bounce not confirmed — forwarding Phase 1 stems to Phase 3")

        bridge.disconnect()
    else:
        print("  ⚠ Ableton Live not running")
        print("  → Phase 1 audio_manifest stems forwarded directly to Phase 3")
        print(f"  → To run full Phase 2: open the render ALS in Ableton with AbletonOSC, then re-run")
        als_path = (getattr(mandate, 'render_als_path', None)
                    or getattr(mandate, 'stage5_als_path', None))
        if als_path:
            print(f"  → ALS ready: {als_path}")

    # Populate stem_paths from audio_manifest (Phase 1 bounced stems)
    stem_paths = {k: v for k, v in audio_manifest.items() if v and Path(v).exists()}

    elapsed = time.perf_counter() - t0
    print(f"\n  Phase 2 complete: {total_bars} bars, {len(stem_paths)} stems, "
          f"{'✓ Ableton bounce' if wav_path else '⚠ Ableton not used — Phase 1 stems forwarded'}, "
          f"{elapsed:.1f}s")

    result = ArrangedTrack(
        kick_positions=kick_positions,
        section_map=section_map,
        total_bars=total_bars,
        total_samples=total_bars * 4 * int(SR * 60.0 / max(bpm, 1.0)),
        dna=dna,
        stem_paths=stem_paths,
        wav_path=wav_path,
        track_indices=track_indices,
        L=[],
        R=[],
        _subtract_map=subtractive,
        elapsed_s=elapsed,
    )

    # ── ICM workspace handoff ──────────────────────────────────────────
    try:
        from engine.workspace_io import write_phase_two_outputs
        write_phase_two_outputs(result)
        print("  ✓ Workspace: mwp/stages/02-arrangement/output/ updated")
    except Exception as _ws_exc:
        print(f"  ⚠ Workspace write skipped: {_ws_exc}")

    return result

    if arr is None:
        return [0.0] * int(0.5 * SR)
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return list(arr)


def _to_np(signal) -> np.ndarray:
    if isinstance(signal, np.ndarray):
        return signal.astype(np.float64)
    return np.array(signal, dtype=np.float64)


def _mix_into(target: list[float], source: list[float],
              offset: int, gain: float = 1.0):
    end = min(offset + len(source), len(target))
    for i in range(max(0, offset), end):
        target[i] += source[i - offset] * gain


def _fade_in(sig: list[float], dur_s: float = 0.5) -> list[float]:
    n = min(int(dur_s * SR), len(sig))
    out = list(sig)
    for i in range(n):
        out[i] *= i / n
    return out


def _fade_out(sig: list[float], dur_s: float = 0.5) -> list[float]:
    n = min(int(dur_s * SR), len(sig))
    out = list(sig)
    L = len(out)
    for i in range(n):
        out[L - 1 - i] *= i / n
    return out


def _lowpass(sig: list[float], cutoff: float = 0.3) -> list[float]:
    out = list(sig)
    prev = 0.0
    for i in range(len(out)):
        out[i] = prev + cutoff * (out[i] - prev)
        prev = out[i]
    return out


def _normalize(sig: list[float], target: float = 0.95) -> list[float]:
    peak = max(abs(s) for s in sig) if sig else 0
    if peak < 1e-10:
        return sig
    scale = target / peak
    return [s * scale for s in sig]


def _sidechain(sig: list[float], depth: float = 0.7,
               attack: float = 0.005, release: float = 0.25,
               bpm: float = 0.0) -> list[float]:
    if bpm <= 0:
        return sig
    period = int(60.0 / bpm * SR)
    attack_n = max(1, int(attack * SR))
    release_n = max(1, int(release * SR))
    out = list(sig)
    pos = 0
    while pos < len(out):
        end = min(pos + period, len(out))
        for i in range(pos, min(pos + attack_n, end)):
            t = (i - pos) / attack_n
            out[i] *= 1.0 - depth * (1.0 - t)
        for i in range(pos + attack_n, end):
            rel_pos = i - pos - attack_n
            t = min(rel_pos / release_n, 1.0)
            out[i] *= 1.0 - depth * max(0.0, 1.0 - t)
        pos += period
    return out


def _pitch_shift_bass(sig: list[float], semitones: float) -> list[float]:
    if abs(semitones) < 0.01:
        return sig
    ratio = 2.0 ** (semitones / 12.0)
    n_out = int(len(sig) / ratio)
    if n_out < 2:
        return sig
    out = [0.0] * n_out
    for i in range(n_out):
        src = i * ratio
        idx = int(src)
        frac = src - idx
        if idx + 1 < len(sig):
            out[i] = sig[idx] * (1.0 - frac) + sig[idx + 1] * frac
        elif idx < len(sig):
            out[i] = sig[idx]
    return out


# ═══════════════════════════════════════════════════════════════
#  Mandate unpacker — extracts audio/timing from SongMandate
# ═══════════════════════════════════════════════════════════════

def _unpack_mandate(mandate):
    """Extract all audio arrays and timing from SongMandate → dict of locals."""
    dna = mandate.dna
    BEAT = mandate.beat_s
    BAR = mandate.bar_s

    intervals = SCALE_INTERVALS.get(dna.scale, [0, 2, 3, 5, 7, 8, 10])

    def n(degree: int, octave: int) -> float:
        semi = intervals[degree % len(intervals)]
        return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semi / 12.0))

    FREQ = dict(mandate.freq_table)
    _note_aliases = {
        "F1": n(0, 1), "F2": n(0, 2), "F3": n(0, 3), "F4": n(0, 4),
        "G2": n(1, 2), "G3": n(1, 3), "G4": n(1, 4),
        "Ab1": n(2, 1), "Ab2": n(2, 2), "Ab3": n(2, 3), "Ab4": n(2, 4),
        "Bb1": n(3, 1), "Bb2": n(3, 2), "Bb3": n(3, 3),
        "C2": n(4, 1), "C3": n(4, 2), "C4": n(4, 3),
        "Db2": n(5, 1), "Db3": n(5, 2), "Db4": n(5, 3),
        "Eb2": n(6, 1), "Eb3": n(6, 2), "Eb4": n(6, 3),
    }
    FREQ.update(_note_aliases)

    dd = dna.drums
    bd = dna.bass
    ld = dna.lead
    ad = dna.atmosphere
    fd = dna.fx
    md = dna.mix

    # ── Section bars from mandate.arrangement_template ──
    # USE the mandate arrangement_template (the proper Phase 1 output)
    # instead of re-deriving from dna.arrangement
    if mandate.arrangement_template is not None:
        sec_map = {}
        for sec in mandate.arrangement_template.sections:
            sec_map[sec.name] = sec.bars
    else:
        sec_map = dict(mandate.sections) if mandate.sections else {}

    INTRO = sec_map.get("intro", 8)
    BUILD = sec_map.get("build", sec_map.get("build_1", 4))
    DROP1 = sec_map.get("drop1", sec_map.get("drop", sec_map.get("drop_1", 16)))
    BREAK_ = sec_map.get("break", sec_map.get("breakdown", 8))
    BUILD2 = sec_map.get("build2", sec_map.get("build_2", BUILD))
    DROP2 = sec_map.get("drop2", sec_map.get("drop_2", DROP1))
    OUTRO = sec_map.get("outro", 8)
    total_bars = INTRO + BUILD + DROP1 + BREAK_ + BUILD2 + DROP2 + OUTRO

    def samples(beats: float) -> int:
        return int(beats * BEAT * SR)

    total_s = samples(total_bars * 4)

    # ── Audio arrays from mandate ──
    kick = _to_list(mandate.drums.kick)
    snare = _to_list(mandate.drums.snare)
    hat_c = _to_list(mandate.drums.hat_closed)
    hat_o = _to_list(mandate.drums.hat_open)
    clap = _to_list(mandate.drums.clap)

    sub = _to_list(mandate.bass.sub)
    reese = _to_list(mandate.bass.reese)

    _bass_rotation = mandate.bass.rotation_order or list(mandate.bass.sounds.keys())
    bass_arsenal = []
    for _bt in _bass_rotation:
        _bs = mandate.bass.sounds.get(_bt)
        if _bs is not None:
            bass_arsenal.append(_to_list(_bs))
    if not bass_arsenal:
        bass_arsenal = [reese]

    fm_growl = bass_arsenal[0] if len(bass_arsenal) > 0 else reese

    # ── Leads ──
    lead_notes = {}
    lead_notes_long = {}
    for _deg in range(7):
        for _oct in [3, 4]:
            _freq = n(_deg, _oct)
            _best_key = min(mandate.leads.screech.keys(),
                            key=lambda f: abs(f - _freq),
                            default=None) if mandate.leads.screech else None
            if _best_key is not None:
                lead_notes[(_deg, _oct)] = _to_list(mandate.leads.screech[_best_key])
                lead_notes_long[(_deg, _oct)] = _to_list(mandate.leads.screech[_best_key])
            elif mandate.leads.fm_lead:
                _fk = min(mandate.leads.fm_lead.keys(),
                          key=lambda f: abs(f - _freq), default=None)
                if _fk is not None:
                    lead_notes[(_deg, _oct)] = _to_list(mandate.leads.fm_lead[_fk])
                    lead_notes_long[(_deg, _oct)] = _to_list(mandate.leads.fm_lead[_fk])

    lead_f = lead_notes.get((0, 4), [0.0] * int(0.3 * SR))
    lead_eb = lead_notes.get((6, 3), lead_f)
    lead_c = lead_notes.get((4, 3), lead_f)
    lead_ab = lead_notes.get((2, 4), lead_f)

    # ── Chords ──
    chord_f_l = _to_list(mandate.leads.chord_l)
    chord_f_r = _to_list(mandate.leads.chord_r)
    chord_notes_l = {}
    chord_notes_r = {}
    _chord_prog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
    for _cdeg in set(_chord_prog):
        chord_notes_l[_cdeg] = chord_f_l
        chord_notes_r[_cdeg] = chord_f_r

    # ── Pads / Atmosphere ──
    dark_pad = _to_list(mandate.atmosphere.dark_pad)
    lush = _to_list(mandate.atmosphere.lush_pad)
    drone = _to_list(mandate.atmosphere.drone)
    drop_noise = _to_list(mandate.atmosphere.noise_bed)

    # ── FX ──
    riser = _to_list(mandate.fx.riser)
    boom = _to_list(mandate.fx.boom)
    hit = _to_list(mandate.fx.hit)
    tape_stop = _to_list(mandate.fx.tape_stop)
    pitch_dive = _to_list(mandate.fx.pitch_dive)
    rev_crash = _to_list(mandate.fx.rev_crash)
    stutter = _to_list(mandate.fx.stutter)
    gate_chop = _to_list(mandate.fx.gate_chop)

    # ── Vocals ──
    _vowel_list = mandate.vocals.vowels or ["ah", "oh", "ee", "oo"]
    chop_ah = _to_list(mandate.vocals.chops.get(_vowel_list[0])) if len(_vowel_list) > 0 else [0.0] * int(0.2 * SR)
    chop_oh = _to_list(mandate.vocals.chops.get(_vowel_list[1])) if len(_vowel_list) > 1 else chop_ah
    chop_ee_stut = _to_list(mandate.vocals.chops.get(_vowel_list[2])) if len(_vowel_list) > 2 else chop_ah
    chop_yoi = _to_list(mandate.vocals.chops.get(_vowel_list[3])) if len(_vowel_list) > 3 else chop_ah
    vocal_chops = [chop_ah, chop_oh, chop_ee_stut, chop_yoi]

    return {
        "dna": dna, "BEAT": BEAT, "BAR": BAR, "FREQ": FREQ,
        "intervals": intervals, "n": n, "samples": samples,
        "dd": dd, "bd": bd, "ld": ld, "ad": ad, "fd": fd, "md": md,
        "INTRO": INTRO, "BUILD": BUILD, "DROP1": DROP1, "BREAK_": BREAK_,
        "BUILD2": BUILD2, "DROP2": DROP2, "OUTRO": OUTRO,
        "total_bars": total_bars, "total_s": total_s,
        "kick": kick, "snare": snare, "hat_c": hat_c, "hat_o": hat_o, "clap": clap,
        "sub": sub, "reese": reese, "bass_arsenal": bass_arsenal, "fm_growl": fm_growl,
        "lead_notes": lead_notes, "lead_notes_long": lead_notes_long,
        "lead_f": lead_f, "lead_eb": lead_eb, "lead_c": lead_c, "lead_ab": lead_ab,
        "chord_notes_l": chord_notes_l, "chord_notes_r": chord_notes_r,
        "chord_f_l": chord_f_l, "chord_f_r": chord_f_r,
        "dark_pad": dark_pad, "lush": lush, "drone": drone, "drop_noise": drop_noise,
        "riser": riser, "boom": boom, "hit": hit,
        "tape_stop": tape_stop, "pitch_dive": pitch_dive,
        "rev_crash": rev_crash, "stutter": stutter, "gate_chop": gate_chop,
        "vocal_chops": vocal_chops, "chop_ah": chop_ah, "chop_oh": chop_oh,
        "chop_ee_stut": chop_ee_stut, "chop_yoi": chop_yoi,
        "mandate": mandate,
    }


# ═══════════════════════════════════════════════════════════════
#  ARRANGE — build stereo mix from mandate audio + timing  [LEGACY — kept for ref]
# ═══════════════════════════════════════════════════════════════

def _run_phase_two_legacy(mandate) -> ArrangedTrack:
    """Phase 2 legacy numpy DSP path — superseded by run_phase_two (AbletonOSC).
    Kept for reference only; NOT called by the pipeline.
    Original: ARRANGE + DESIGN.

    Consumes SongMandate from Phase 1, arranges all audio into a
    stereo mix using the mandate's arrangement_template, rco_profile,
    and section structure.

    Pipeline:
        1. Phase 2 Setup — build structured SessionArrangement
           (bus routing, track mapping, energy curve, sidechain)
        2. Flat stereo mix — existing section-by-section placement
        3. DESIGN — spatial reverb + bus routing

    Returns ArrangedTrack with L/R arrays ready for Phase 3 (MIX).
    The structured SessionArrangement is stored in _session_arrangement.
    """
    t0 = time.perf_counter()
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  PHASE 2: ARRANGE + DESIGN                          ║")
    print("╚══════════════════════════════════════════════════════╝")

    # ── Phase 2 Setup: Build structured session from template ──
    _session_arrangement = None
    try:
        from engine.phase_two_setup import setup_phase_two
        _session_arrangement = setup_phase_two(mandate)
    except Exception as exc:
        print(f"  ⚠ Phase 2 Setup skipped: {exc}")

    p = _unpack_mandate(mandate)
    dna = p["dna"]
    BEAT, BAR, FREQ = p["BEAT"], p["BAR"], p["FREQ"]
    intervals, n_fn, samples = p["intervals"], p["n"], p["samples"]
    dd, bd, ld = p["dd"], p["bd"], p["ld"]
    md = p["md"]

    INTRO, BUILD, DROP1 = p["INTRO"], p["BUILD"], p["DROP1"]
    BREAK_, BUILD2, DROP2, OUTRO = p["BREAK_"], p["BUILD2"], p["DROP2"], p["OUTRO"]
    total_bars, total_s = p["total_bars"], p["total_s"]

    kick, snare = p["kick"], p["snare"]
    hat_c, hat_o, clap = p["hat_c"], p["hat_o"], p["clap"]
    sub, reese = p["sub"], p["reese"]
    bass_arsenal, fm_growl = p["bass_arsenal"], p["fm_growl"]
    lead_notes, lead_notes_long = p["lead_notes"], p["lead_notes_long"]
    lead_f, lead_eb, lead_c, lead_ab = p["lead_f"], p["lead_eb"], p["lead_c"], p["lead_ab"]
    chord_notes_l, chord_notes_r = p["chord_notes_l"], p["chord_notes_r"]
    chord_f_l, chord_f_r = p["chord_f_l"], p["chord_f_r"]
    dark_pad, lush, drone, drop_noise = p["dark_pad"], p["lush"], p["drone"], p["drop_noise"]
    riser, boom, hit = p["riser"], p["boom"], p["hit"]
    tape_stop, pitch_dive = p["tape_stop"], p["pitch_dive"]
    rev_crash, stutter, gate_chop = p["rev_crash"], p["stutter"], p["gate_chop"]
    vocal_chops = p["vocal_chops"]
    chop_oh, chop_ee_stut, chop_yoi = p["chop_oh"], p["chop_ee_stut"], p["chop_yoi"]

    # ── Engines ──
    _energy = getattr(dna, 'energy', 0.7)
    sat = SaturationEngine(sample_rate=SR)
    panner = PanningEngine(sample_rate=SR)
    groove_eng = GrooveEngine(bpm=dna.bpm, sample_rate=SR)
    rhythm_eng = RhythmEngine.from_drum_dna(
        dd, bpm=dna.bpm, energy=_energy, seed=hash(dna.name) & 0xFFFF)

    # ── Energy map — derive from DNA arrangement sections ──
    energy_map: dict[str, tuple[float, float]] = {}
    try:
        for sec in dna.arrangement:
            energy_map[sec.name] = (sec.energy, sec.energy)
    except Exception:
        from engine.stage_integrations import build_energy_map
        energy_map = build_energy_map(dna)

    # ── Fat loop analysis (Dojo Sprint 3) ──
    from engine.stage_integrations import (
        build_fat_loop_map, extract_ghost_markers,
        compute_subtractive_map, measure_section_contrast,
        compute_arrangement_energy_curve,
    )
    _sketch_sounds: dict[str, list[float]] = {}
    for name, sig in [("kick", kick), ("snare", snare), ("hat_c", hat_c),
                      ("hat_o", hat_o), ("clap", clap), ("sub", sub),
                      ("fm_growl", fm_growl), ("dark_pad", dark_pad),
                      ("lush", lush), ("drone", drone), ("riser", riser),
                      ("boom", boom), ("hit", hit), ("drop_noise", drop_noise)]:
        if sig:
            _sketch_sounds[name] = sig
    for idx, bs in enumerate(bass_arsenal[1:], 1):
        _sketch_sounds[f"bass_{idx}"] = bs

    _fat_loop = build_fat_loop_map(dna, _sketch_sounds, SR)
    _ghost_markers = extract_ghost_markers(dna, SR)
    _subtract_map = compute_subtractive_map(_fat_loop, dna, energy_map)
    _section_contrast = measure_section_contrast(_subtract_map, dna)
    _energy_curve = compute_arrangement_energy_curve(dna, _ghost_markers, energy_map)

    # ─────────────────────────────────────────────────────
    #  STEREO MIX
    # ─────────────────────────────────────────────────────
    L = [0.0] * total_s
    R = [0.0] * total_s

    def mx(mono, offset, gl=0.7, gr=0.7):
        _mix_into(L, mono, offset, gl)
        _mix_into(R, mono, offset, gr)

    def mx_stereo(left, right, offset, gain=1.0):
        _mix_into(L, left, offset, gain)
        _mix_into(R, right, offset, gain)

    def mx_panned(mono, offset, gain=0.7, pan=0.0):
        angle = (pan + 1.0) * 0.25 * math.pi
        gl = gain * math.cos(angle)
        gr = gain * math.sin(angle)
        _mix_into(L, mono, offset, gl)
        _mix_into(R, mono, offset, gr)

    def mx_wide(mono, offset, gain=0.7, delay_ms=5.0):
        delay_samp = int(delay_ms * 0.001 * SR)
        _mix_into(L, mono, offset, gain)
        _mix_into(R, mono, offset + delay_samp, gain)

    # ── Drum dispatcher ──
    _drum_sounds = {
        "kick": kick, "snare": snare, "clap": clap,
        "hat_c": hat_c, "hat_o": hat_o,
    }
    kick_positions: list[int] = []

    def place_drums(events: list[DrumEvent], bar_offset: int):
        for ev in events:
            snd = _drum_sounds.get(ev.instrument)
            if snd is None:
                continue
            pos = bar_offset + int(ev.beat * BEAT * SR)
            if abs(ev.pan) < 0.01:
                mx(snd, pos, ev.gain, ev.gain)
            else:
                mx_panned(snd, pos, ev.gain, ev.pan)
            if ev.instrument == "kick":
                kick_positions.append(pos)

    # ── Hat pattern ──
    def make_hat_events_bar():
        events = []
        _hat_steps = getattr(dd, 'hat_density', 16)
        for i in range(_hat_steps):
            vel = 0.6 + 0.3 * ((i % 4) == 0)
            if i % 4 == 2:
                vel *= 0.7
            events.append(NoteEvent(
                time=i * (BAR / _hat_steps),
                duration=0.03, pitch=42, velocity=vel
            ))
        grooved = groove_eng.apply_groove(
            events, GROOVE_TEMPLATES.get("dubstep_halftime"))
        return groove_eng.humanize(grooved, timing_ms=5, velocity_pct=8)

    hat_pattern = make_hat_events_bar()

    cursor = 0

    # ══════════════════════════════════════════════════
    #  INTRO
    # ══════════════════════════════════════════════════
    print("  Intro...")
    drone_st = panner.haas_delay(drone[:samples(INTRO * 4)], delay_ms=18.0)
    mx_stereo(drone_st.left, drone_st.right, cursor, 0.40)

    ip = dark_pad[:samples(INTRO * 4)]
    ip = _fade_in(ip, BAR * 0.5)
    ip = _lowpass(ip, 0.25)
    ip_np = _to_np(ip)
    ip_np = svf_highpass(ip_np, 250.0, 0.7, SR)
    ip = ip_np.tolist()
    mx(ip, cursor, 0.45, 0.45)

    in_noise = drop_noise[:samples(INTRO * 4)]
    in_noise = _fade_in(in_noise, BAR * 0.5)
    mx_wide(in_noise, cursor, 0.40, 15.0)

    for bar in range(INTRO):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.intro_bar(bar, INTRO)
        place_drums(drum_evs, off)

    ir = reese[:samples(INTRO * 4)]
    ir = _lowpass(ir, 0.08)
    ir_np = _to_np(ir)
    ir_np = svf_highpass(ir_np, 80.0, 0.7, SR)
    ir = ir_np.tolist()
    ir = _fade_in(ir, BAR * 0.5)
    mx(ir, cursor, 0.30, 0.30)
    cursor += samples(INTRO * 4)

    # ══════════════════════════════════════════════════
    #  BUILD 1
    # ══════════════════════════════════════════════════
    print("  Build 1...")
    for bar in range(BUILD):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.build_bar(bar, BUILD, is_build2=False)
        place_drums(drum_evs, off)

    r_seg = riser[:samples(BUILD * 4)]
    mx_wide(r_seg, cursor, 0.55)
    gc_seg = gate_chop[:samples(BUILD * 4)]
    mx(gc_seg, cursor, 0.2, 0.2)
    bp = dark_pad[:samples(BUILD * 4)]
    mx(bp, cursor, 0.65, 0.65)
    mx_wide(chop_ee_stut, cursor + samples(3 * 4), 0.35)
    cursor += samples(BUILD * 4)

    # ══════════════════════════════════════════════════
    #  DROP 1
    # ══════════════════════════════════════════════════
    print("  Drop 1...")
    mx(boom, cursor, 0.85, 0.85)
    mx(hit, cursor, 0.7, 0.7)

    for bar in range(DROP1):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.drop_bar(bar, DROP1, intensity=1)
        place_drums(drum_evs, off)

        sub_sc = _sidechain(sub, depth=0.93, release=0.15, bpm=dna.bpm)
        _sw = bd.sub_weight
        mx(sub_sc, off, 0.12 * _sw, 0.12 * _sw)
        mx(sub_sc, off + samples(2), 0.08 * _sw, 0.08 * _sw)

        dn = drop_noise[:min(samples(4), len(drop_noise))]
        mx_wide(dn, off, 0.32, 20.0)

        _pad_seg = dark_pad[:min(samples(4), len(dark_pad))]
        mx_wide(_pad_seg, off, 0.18)

        _md_drive = 0.5 + 0.5 * bd.mid_drive
        _bass_riff = getattr(bd, 'bass_riff', None)
        bass_idx = bar % len(bass_arsenal)
        bass_snd = bass_arsenal[bass_idx]
        _bass_semi = 0
        if _bass_riff and len(_bass_riff) > 0:
            _riff_pat = _bass_riff[bar % len(_bass_riff)]
            if _riff_pat:
                _bdeg = _riff_pat[0][0]
                _bass_semi = intervals[_bdeg % len(intervals)]

        _b = _pitch_shift_bass(bass_snd, _bass_semi) if _bass_semi else bass_snd
        _b_np = _to_np(_b)
        _b_np = svf_highpass(_b_np, 180.0, 0.7, SR)
        _b = _b_np.tolist()
        mx_wide(_b, off + samples(0.5), 0.12 * _md_drive)

        if bar % 4 == 0:
            chop = vocal_chops[bar // 4 % len(vocal_chops)]
            mx_wide(chop, off, 0.45)
        if bar % 4 == 2:
            mx_panned(chop_oh, off + samples(2), 0.45, 0.35)

        _melody_pats = getattr(ld, 'melody_patterns', None)
        if _melody_pats and len(_melody_pats) > 0:
            _phrase_len = getattr(ld, 'phrase_length', 4)
            _pat_idx = (bar // _phrase_len) % len(_melody_pats)
            _pattern = _melody_pats[_pat_idx]
            for (deg, bt, dur, vel) in _pattern:
                _oct = 4 if deg >= 4 else 3
                _lnote = lead_notes_long if dur > 0.6 else lead_notes
                _key = (deg % 7, _oct)
                if _key in _lnote:
                    _pan = -0.35 + 0.20 * math.sin(bar * 0.5 + bt * 0.3)
                    mx_panned(_lnote[_key], off + samples(bt), 0.65 * vel, _pan)
        else:
            notes = [(lead_f, 0.0), (lead_eb, 1.0), (lead_c, 2.0), (lead_ab, 3.0)]
            for snd, bt in notes:
                mx_panned(snd, off + samples(bt), 0.78, 0.30 + 0.20 * math.sin(bar * 0.5))

        if bar % 4 == 0:
            _cprog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
            _cidx = (bar // 4) % len(_cprog)
            _cdeg = _cprog[_cidx]
            _cl = chord_notes_l.get(_cdeg, chord_f_l)
            _cr = chord_notes_r.get(_cdeg, chord_f_r)
            mx_stereo(_cl, _cr, off, 0.85)

        if bar % 4 == 0 and bar > 0:
            _crash = synthesize_noise(NoisePreset(
                name="Crash", noise_type="white", duration_s=BEAT * 3,
                attack_s=0.001, release_s=0.8, brightness=0.9, gain=0.7))
            _crash_np = _to_np(_crash)
            _crash_np = svf_highpass(_crash_np, 6000.0, 0.3, SR)
            _crash = _normalize(_crash_np.tolist(), 0.35)
            mx_wide(_crash, off, 0.30, 25.0)

    mx(tape_stop, cursor + samples((DROP1 - 1) * 4 + 2), 0.55, 0.55)
    cursor += samples(DROP1 * 4)

    # ══════════════════════════════════════════════════
    #  BREAKDOWN
    # ══════════════════════════════════════════════════
    print("  Breakdown...")
    mx(pitch_dive, cursor - samples(1), 0.4, 0.4)

    bp = lush[:samples(BREAK_ * 4)]
    bp = _fade_in(bp, BAR * 0.25)
    bp = _fade_out(bp, BAR * 0.5)
    bp_np = _to_np(bp)
    bp_np = svf_highpass(bp_np, 250.0, 0.7, SR)
    bp = bp_np.tolist()
    bp_st = panner.haas_delay(bp, delay_ms=14.0, side="right")
    mx_stereo(bp_st.left, bp_st.right, cursor, 0.60)

    bk_noise = drop_noise[:samples(BREAK_ * 4)]
    bk_noise = _fade_in(bk_noise, BAR * 0.25)
    bk_noise = _fade_out(bk_noise, BAR * 0.5)
    mx_wide(bk_noise, cursor, 0.40, 18.0)

    pluck_freqs = [FREQ["F3"], FREQ["Ab3"], FREQ["C4"], FREQ["Eb4"]]
    for bar in range(BREAK_):
        off = cursor + samples(bar * 4)
        for q in range(4):
            freq = pluck_freqs[(bar + q) % 4]
            plk = render_ks(KarplusStrongPatch(
                frequency=freq, duration=BEAT * 0.8,
                damping=0.4, brightness=0.65, stretch=0.0,
                feedback=0.992, noise_mix=0.9, pluck_position=0.3))
            plk_np = apply_reverb_delay(_to_np(plk), ReverbDelayPreset(
                name="PlkDly", effect_type="delay", decay_time=0.5,
                bpm=float(dna.bpm), delay_feedback=0.35, num_taps=3, mix=0.22))
            plk = plk_np.tolist()
            pan = -0.45 + 0.9 * (q / 3)
            mx_panned(plk, off + samples(q), 0.38, pan)
        drum_evs = rhythm_eng.breakdown_bar(bar, BREAK_)
        place_drums(drum_evs, off)

    mx_wide(rev_crash, cursor + samples((BREAK_ - 2) * 4), 0.35)
    cursor += samples(BREAK_ * 4)

    # ══════════════════════════════════════════════════
    #  BUILD 2
    # ══════════════════════════════════════════════════
    print("  Build 2...")
    for bar in range(BUILD2):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.build_bar(bar, BUILD2, is_build2=True)
        place_drums(drum_evs, off)

    r2 = riser[:samples(BUILD2 * 4)]
    mx_wide(r2, cursor, 0.6)

    swell_l, swell_r = render_supersaw(SupersawPatch(
        name="Swell", n_voices=ld.supersaw_voices,
        detune_cents=ld.supersaw_detune, mix=0.8,
        stereo_width=md.stereo_width * 0.61,
        cutoff_hz=ld.supersaw_cutoff * 0.64, resonance=0.42,
        attack=2.5, decay=0.1, sustain=0.9, release=0.5,
        master_gain=0.5
    ), freq=FREQ["F3"], duration=BAR * BUILD2)
    seg_l = swell_l[:samples(BUILD2 * 4)]
    seg_r = swell_r[:samples(BUILD2 * 4)]
    mx_stereo(seg_l, seg_r, cursor, 0.42)

    gc2 = gate_chop[:samples(BUILD2 * 4)]
    mx(gc2, cursor, 0.22, 0.22)
    mx_wide(chop_ee_stut, cursor + samples(3 * 4), 0.4)
    cursor += samples(BUILD2 * 4)

    # ══════════════════════════════════════════════════
    #  DROP 2
    # ══════════════════════════════════════════════════
    print("  Drop 2...")
    mx(boom, cursor, 0.90, 0.90)
    mx(hit, cursor, 0.75, 0.75)
    mx(clap, cursor, 0.50, 0.50)

    for bar in range(DROP2):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.drop_bar(bar, DROP2, intensity=2)
        place_drums(drum_evs, off)

        sub_sc = _sidechain(sub, depth=0.94, release=0.14, bpm=dna.bpm)
        _sw = bd.sub_weight
        mx(sub_sc, off, 0.14 * _sw, 0.14 * _sw)
        mx(sub_sc, off + samples(2), 0.10 * _sw, 0.10 * _sw)

        dn = drop_noise[:min(samples(4), len(drop_noise))]
        mx_wide(dn, off, 0.35, 22.0)

        _pad_seg = dark_pad[:min(samples(4), len(dark_pad))]
        mx_wide(_pad_seg, off, 0.16)

        _md_drive = 0.5 + 0.5 * bd.mid_drive
        _bass_riff = getattr(bd, 'bass_riff', None)
        bass_idx = bar % len(bass_arsenal)
        _bass_semi = 0
        if _bass_riff and len(_bass_riff) > 0:
            _riff_pat = _bass_riff[bar % len(_bass_riff)]
            if _riff_pat:
                _bdeg = _riff_pat[0][0]
                _bass_semi = intervals[_bdeg % len(intervals)]

        bass_snd = bass_arsenal[bass_idx]
        _b = _pitch_shift_bass(bass_snd, _bass_semi) if _bass_semi else bass_snd
        _b_np = _to_np(_b)
        _b_np = svf_highpass(_b_np, 180.0, 0.7, SR)
        _b = _b_np.tolist()
        mx_wide(_b, off + samples(0.5), 0.14 * _md_drive)

        if bar % 2 == 0:
            chop = vocal_chops[bar // 2 % len(vocal_chops)]
            mx_wide(chop, off, 0.42)
        if bar % 4 == 3:
            mx_panned(chop_yoi, off + samples(2), 0.45, -0.25)

        _melody_pats = getattr(ld, 'melody_patterns', None)
        if _melody_pats and len(_melody_pats) > 0:
            _phrase_len = getattr(ld, 'phrase_length', 4)
            _n_pats = len(_melody_pats)
            _pat_idx = (_n_pats // 2 + (bar // _phrase_len)) % _n_pats
            _pattern = _melody_pats[_pat_idx]
            for (deg, bt, dur, vel) in _pattern:
                _oct = 4 if deg >= 4 else 3
                _lnote = lead_notes_long if dur > 0.6 else lead_notes
                _key = (deg % 7, _oct)
                if _key in _lnote:
                    _pan = -0.40 + 0.22 * math.sin(bar * 0.9 + bt * 0.4)
                    mx_panned(_lnote[_key], off + samples(bt), 0.68 * vel, _pan)
        else:
            notes_d2 = [(lead_ab, 0.0), (lead_c, 1.0), (lead_eb, 2.0), (lead_f, 3.0)]
            for snd, bt in notes_d2:
                mx_panned(snd, off + samples(bt), 0.68, -0.35 + 0.20 * math.sin(bar * 0.9))

        if bar % 2 == 0:
            _cprog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
            _cidx = (bar // 2) % len(_cprog)
            _cdeg = _cprog[_cidx]
            _cl = chord_notes_l.get(_cdeg, chord_f_l)
            _cr = chord_notes_r.get(_cdeg, chord_f_r)
            mx_stereo(_cl, _cr, off, 0.85)

        if bar % 4 == 0 and bar > 0:
            _crash = synthesize_noise(NoisePreset(
                name="Crash", noise_type="white", duration_s=BEAT * 3,
                attack_s=0.001, release_s=0.8, brightness=0.9, gain=0.7))
            _crash_np = _to_np(_crash)
            _crash_np = svf_highpass(_crash_np, 6000.0, 0.3, SR)
            _crash = _normalize(_crash_np.tolist(), 0.35)
            mx_wide(_crash, off, 0.30, 25.0)

    mx(tape_stop, cursor + samples((DROP2 - 1) * 4 + 2), 0.55, 0.55)
    mx_wide(stutter, cursor + samples((DROP2 - 2) * 4), 0.35)
    mx_wide(stutter, cursor + samples((DROP2 - 1) * 4), 0.4)
    mx(fm_growl, cursor + samples((DROP2 - 1) * 4 + 2), 0.50, 0.50)
    cursor += samples(DROP2 * 4)

    # ══════════════════════════════════════════════════
    #  OUTRO
    # ══════════════════════════════════════════════════
    print("  Outro...")
    mx(pitch_dive, cursor, 0.35, 0.35)

    op = dark_pad[:samples(OUTRO * 4)]
    op = _fade_out(op, BAR * 1)
    op_np = _to_np(op)
    op_np = svf_highpass(op_np, 250.0, 0.7, SR)
    op = op_np.tolist()
    mx_wide(op, cursor, 0.60)

    out_noise = drop_noise[:samples(OUTRO * 4)]
    out_noise = _fade_in(out_noise, BAR * 0.25)
    out_noise = _fade_out(out_noise, BAR * 1)
    mx_wide(out_noise, cursor, 0.40, 15.0)

    for bar in range(OUTRO):
        off = cursor + samples(bar * 4)
        drum_evs = rhythm_eng.outro_bar(bar, OUTRO)
        place_drums(drum_evs, off)

    # ══════════════════════════════════════════════════
    #  PHASE 6: DESIGN — spatial reverb + bus routing
    # ══════════════════════════════════════════════════
    print("  Design (spatial reverb + bus routing)...")
    from engine.stage_integrations import apply_convolution_reverb, setup_bus_routing

    _conv_L = apply_convolution_reverb(np.array(L, dtype=np.float64),
                                       room_type="plate", mix=0.05, sr=SR)
    _conv_R = apply_convolution_reverb(np.array(R, dtype=np.float64),
                                       room_type="plate", mix=0.05, sr=SR)
    L = _conv_L.tolist()
    R = _conv_R.tolist()

    _sketch_stems = {}
    for _sn, _sv in [("kick", kick), ("snare", snare), ("hat_c", hat_c),
                     ("hat_o", hat_o), ("clap", clap), ("sub", sub),
                     ("fm_growl", fm_growl), ("dark_pad", dark_pad),
                     ("lush", lush), ("drone", drone)]:
        if _sv:
            _sketch_stems[_sn] = _sv
    setup_bus_routing(_sketch_stems, SR)

    elapsed = time.perf_counter() - t0
    section_map = {
        "intro": INTRO, "build": BUILD, "drop1": DROP1,
        "break": BREAK_, "build2": BUILD2, "drop2": DROP2,
        "outro": OUTRO,
    }
    print(f"  Phase 2 complete: {total_bars} bars, "
          f"{len(kick_positions)} kicks, {elapsed:.1f}s")

    result = ArrangedTrack(
        L=L, R=R,
        kick_positions=kick_positions,
        section_map=section_map,
        total_bars=total_bars,
        total_samples=total_s,
        dna=dna,
        _subtract_map=_subtract_map,
        _energy_curve=_energy_curve,
        elapsed_s=elapsed,
        _session_arrangement=_session_arrangement,
    )

    # ── ICM workspace handoff ──────────────────────────────────────────
    try:
        from engine.workspace_io import write_phase_two_outputs
        write_phase_two_outputs(result)
        print("  ✓ Workspace: mwp/stages/02-arrangement/output/ updated")
    except Exception as _ws_exc:
        print(f"  ⚠ Workspace write skipped: {_ws_exc}")

    return result
