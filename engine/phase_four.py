"""DUBFORGE — Phase 4: MASTER + RELEASE + REFLECT

MWP v6.0.0 — ALL phases AbletonOSC. No numpy DSP mastering.
Cardinal Rule 2: Ableton Live IS the engine.

Entry point: run_phase_four(mixed, mandate, output_dir) -> str (output path)

Pipeline:
    1. Load mixed WAV from MixedTrack.wav_path
    2. Connect AbletonBridge to Ableton Live
    3. Create mastering session (1 audio track + master chain devices)
    4. Load mixed WAV into Arrangement track
    5. Set master track volume + configure any pre-loaded devices
    6. Trigger export via osascript (Cmd+Shift+R), poll for output
    7. Read mastered WAV back for Python QA / phi / dither / watermark
    8. Write final 24-bit WAV + run RELEASE (MIDI, metadata, artwork, etc.)
    9. Run REFLECT (assess belt, report card, lessons)
"""
from __future__ import annotations

import array as _array_mod
import math
import os
import struct
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

from engine.ableton_bridge import AbletonBridge
from engine.phase_three import MixedTrack

from engine.stage_integrations import (
    # Phase 4 — QA
    validate_output, apply_auto_master, get_reference_insights,
    # Sprint 1 — Phi
    normalize_phi_master, analyze_phi_coherence,
    # Sprint 2 — Dither + watermark
    apply_final_dither, embed_audio_watermark,
    # Sprint 1 (P0) — Analysis
    run_audio_analysis, validate_key_consistency,
    compare_to_reference, run_fibonacci_quality_check,
    # Sprint 2 (P1) — MIDI + metadata
    export_midi_file, write_audio_metadata, export_bounce_stems,
    begin_render_session, end_render_session,
    record_render_lessons, log_milestone,
    create_session_logger,
    # Sprint 3 (P2) — Creative exports
    detect_genre, detect_patterns,
    generate_artwork, export_serum2_preset,
    build_ep_metadata, set_cue_points,
    export_ableton_rack, tag_output_file,
    # Sprint 4 (P3) — Grandmaster
    build_grandmaster_report_hook, get_ascension_manifest,
    check_autonomous_director,
    # Sprint 5 — Belt
    generate_report_card, assess_belt_promotion,
    persist_belt_progress,
)

SR = 48000


# =================================================================
#  Audio I/O helpers
# =================================================================

def _write_stereo_wav(path: str, left: list[float], right: list[float]):
    """Write 24-bit stereo WAV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    n = min(len(left), len(right))
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(SR)
        chunk_size = SR
        for start in range(0, n, chunk_size):
            end = min(start + chunk_size, n)
            frames = b""
            for i in range(start, end):
                l_s = max(-8388608, min(8388607, int(left[i] * 8388607)))
                r_s = max(-8388608, min(8388607, int(right[i] * 8388607)))
                frames += struct.pack("<i", l_s)[:3]
                frames += struct.pack("<i", r_s)[:3]
            wf.writeframes(frames)


def _read_stereo_wav(path: str) -> tuple[list[float], list[float], int]:
    """Read a stereo (or mono) WAV. Returns (L, R, framerate) as float lists."""
    with wave.open(path, "r") as wf:
        nch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    fmt = {1: "b", 2: "h"}
    if sampwidth in fmt:
        ints = _array_mod.array(fmt[sampwidth])
        ints.frombytes(raw)
        scale = float(1 << (sampwidth * 8 - 1))
        floats = [s / scale for s in ints]
    else:
        # 24-bit or wider: manual little-endian signed decode
        scale = float((1 << (sampwidth * 8 - 1)) - 1)
        floats = []
        for k in range(len(raw) // sampwidth):
            chunk = raw[k * sampwidth:(k + 1) * sampwidth]
            val = int.from_bytes(chunk, byteorder="little", signed=True)
            floats.append(val / scale)

    if nch >= 2:
        return floats[0::2], floats[1::2], framerate
    return floats[:], floats[:], framerate


def _trigger_export_and_wait(
    output_path: str,
    timeout_s: float = 300.0,
    total_beats: float = 256.0,
) -> str:
    """Trigger Ableton Cmd+Shift+R export and poll for the output WAV.

    AbletonOSC cannot trigger file export directly. macOS osascript
    simulates Cmd+Shift+R then polls until the file size stabilises.
    """
    script = (
        'tell application "Ableton Live 12 Suite" to activate\n'
        "delay 0.5\n"
        'tell application "System Events"\n'
        "    key code 15 using {command down, shift down}\n"
        "    delay 2.0\n"
        "    key code 36\n"
        "end tell\n"
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)

    deadline = time.time() + timeout_s
    last_size = -1
    while time.time() < deadline:
        p = Path(output_path)
        if p.exists():
            size = p.stat().st_size
            if size > 0 and size == last_size:
                return output_path
            last_size = size
        time.sleep(2.0)

    return output_path  # return path regardless; caller checks existence


# =================================================================
#  Entry point
# =================================================================

def run_phase_four(mixed: MixedTrack, mandate,
                   output_dir: str = "output",
                   mem_engine: Any = None) -> str:
    """Phase 4: MASTER + RELEASE + REFLECT.

    Consumes MixedTrack.wav_path + SongMandate.
    Masters via Ableton Live (osascript export), then runs Python QA,
    phi normalization, dither/watermark, and all release exports.

    Returns: final output WAV path.
    """
    t0 = time.perf_counter()
    print("\n====================================================")
    print("  PHASE 4: MASTER + RELEASE + REFLECT")
    print("====================================================")

    dna = mixed.dna
    md = dna.mix

    safe_name = "".join(c if c.isalnum() or c in "-_ " else ""
                        for c in dna.name).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "dubforge_track"

    OUTPUT = Path(output_dir) / safe_name
    OUTPUT.mkdir(parents=True, exist_ok=True)

    _session_logger = create_session_logger(dna.name)

    # ========================================================
    #  MASTER via Ableton Live + osascript
    # ========================================================
    print("  Mastering via Ableton Live...")

    mix_wav_path = mixed.wav_path or ""
    if not mix_wav_path or not Path(mix_wav_path).exists():
        raise RuntimeError(
            f"Phase 4 has no mixed WAV input — mixed.wav_path={mix_wav_path!r}. "
            "Phase 3 must complete successfully first."
        )

    # ── Ensure a fresh Ableton session for Phase 4 ──────────────────────────
    try:
        from engine.ableton_session import ensure_fresh_ableton_session
        _ableton_ready = ensure_fresh_ableton_session(template_als=None)
        if not _ableton_ready:
            print("  ⚠ Phase 4: Ableton not ready — mastering will skip OSC steps")
    except Exception as _ses_exc:
        print(f"  ⚠ Phase 4 session setup skipped: {_ses_exc}")
    # ─────────────────────────────────────────────────────────────────────────

    ableton_master_wav = str(OUTPUT / f"{safe_name}_ableton_master.wav")
    _ableton_ok = False

    try:
        bridge = AbletonBridge()
        if bridge.connect():
            bridge.set_tempo(float(dna.bpm))
            bridge.set_time_signature(4, 4)
            bridge.show_arrangement()

            # One audio track carries the full mix into the master chain
            mix_track = bridge.create_audio_track(0, "MASTER_IN")
            bridge.set_track_volume(mix_track, 0.85)
            bridge.set_track_pan(mix_track, 0.0)
            bridge.create_arrangement_audio_clip(mix_track, mix_wav_path, 0.0)
            print(f"  loaded mixed WAV into MASTER_IN track")

            # Master bus
            bridge.set_master_volume(0.9)
            bridge.set_master_pan(0.0)

            # Try to configure pre-loaded master devices (Glue / Limiter)
            ceiling = getattr(md, "ceiling_db", -0.3)
            try:
                bridge.set_device_parameter_by_name(mix_track, 0, "Ceiling", ceiling)
            except Exception:
                pass  # No device pre-loaded; configure manually in Ableton

            # Target LUFS → Limiter Threshold (offset by +3 dB headroom margin)
            _target_lufs = getattr(md, 'target_lufs', None)
            if _target_lufs is not None and abs(_target_lufs - (-9.0)) > 0.5:
                try:
                    bridge.set_device_parameter_by_name(mix_track, 0, "Threshold", _target_lufs + 3.0)
                except Exception:
                    pass

            # Master drive → Saturator device at chain index 1
            _master_drive = getattr(md, 'master_drive', 0.0)
            if _master_drive and _master_drive > 0.1:
                try:
                    bridge.set_device_parameter_by_name(mix_track, 1, "Drive", _master_drive)
                except Exception:
                    pass

            # Reference EQ curve — log for manual application
            _eq_curve = getattr(md, 'reference_eq_curve', None) or []
            if _eq_curve:
                print(f"  → Reference EQ curve (10-band): {[round(v, 2) for v in _eq_curve[:10]]}")
                print(f"    Apply in EQ Eight on master chain if OSC device not pre-loaded")

            # Set loop to exact mix duration
            with wave.open(mix_wav_path, "r") as _wf:
                _dur_s = _wf.getnframes() / _wf.getframerate()
            total_beats = (_dur_s / 60.0) * float(dna.bpm)
            bridge.set_loop(True, 0.0, total_beats)
            bridge.disconnect()

            print(f"  Triggering export (Cmd+Shift+R) -> {ableton_master_wav}")
            _trigger_export_and_wait(ableton_master_wav, timeout_s=300.0,
                                     total_beats=total_beats)

            if Path(ableton_master_wav).exists() and Path(ableton_master_wav).stat().st_size > 0:
                _ableton_ok = True
                print(f"  Ableton mastered WAV: {ableton_master_wav}")
            else:
                print("  Export timed out or file missing - using mixed WAV as master")
        else:
            print("  Ableton not reachable - using mixed WAV as pass-through master")
    except Exception as _exc:
        print(f"  Ableton mastering failed: {_exc}")

    master_wav = ableton_master_wav if _ableton_ok else mix_wav_path
    if not _ableton_ok:
        print(f"  Using mixed WAV as master: {master_wav}")

    # Read mastered audio back for Python post-processing
    print("  Reading mastered audio for QA + post-processing...")
    master_L, master_R, _framerate = _read_stereo_wav(master_wav)

    _all = master_L + master_R
    _peak = max((abs(x) for x in _all), default=0.0)
    _rms = (sum(x * x for x in _all) / max(len(_all), 1)) ** 0.5
    _peak_db = 20.0 * math.log10(max(_peak, 1e-10))
    _rms_db = 20.0 * math.log10(max(_rms, 1e-10))

    # -- QA validation --
    print("  QA validation + reference insights...")
    validate_output(master_L, master_R, SR)
    apply_auto_master(master_L, dna, SR)
    get_reference_insights(dna)

    # -- Phi normalization --
    print("  Phi normalization...")
    master_L, master_R = normalize_phi_master(master_L, master_R, SR)
    _phi_score = analyze_phi_coherence(master_L, master_R, SR)

    # -- Dither + watermark --
    print("  Dither + watermark...")
    master_L, master_R = apply_final_dither(master_L, master_R)
    master_L = embed_audio_watermark(master_L, dna, SR)
    master_R = embed_audio_watermark(master_R, dna, SR)

    # -- Write final 24-bit WAV --
    out_path = str(OUTPUT / f"{safe_name}.wav")
    _write_stereo_wav(out_path, master_L, master_R)

    duration = len(master_L) / SR
    fsize = os.path.getsize(out_path)
    print(f"  Output:   {out_path}")
    print(f"  Duration: {duration:.1f}s ({int(duration // 60)}:{int(duration % 60):02d})")
    print(f"  Peak:     {_peak_db:.1f} dB")
    print(f"  RMS:      {_rms_db:.1f} dB")
    print(f"  Size:     {fsize / 1024 / 1024:.1f} MB")

    _master_elapsed = time.perf_counter() - t0

    # ========================================================
    #  RELEASE
    # ========================================================
    print("  Release - exports + metadata...")
    _t_release = time.perf_counter()

    print("  Post-export QA (analysis, key, reference, Fibonacci)...")
    _analysis = run_audio_analysis(out_path, SR)
    _key_check = validate_key_consistency(out_path, dna, SR)
    _ref_compare = compare_to_reference(out_path)
    _fib_check = run_fibonacci_quality_check(out_path, dna)

    print("  MIDI export + metadata + bounce...")
    _midi_path = export_midi_file(dna, out_dir=str(OUTPUT / "midi"), bpm=int(dna.bpm))
    _meta = write_audio_metadata(out_path, dna, SR)
    _bounce_info = export_bounce_stems(out_path, master_L, master_R, SR)
    log_milestone(_session_logger, "Export complete")

    print("  Genre detection + artwork + Serum2 + ALS...")
    _genre_info = detect_genre(master_L, SR, dna.bpm)
    _pattern_info = detect_patterns(master_L, bpm=dna.bpm, sr=SR)
    _artwork = generate_artwork(dna)
    _serum2 = export_serum2_preset(dna)
    _ep_info = build_ep_metadata(dna, out_path)
    _cue_info = set_cue_points(out_path, dna, duration=duration)
    _rack = export_ableton_rack()
    tag_output_file(out_path, dna)

    print("  Ableton Live project + 128 Rack ADG...")
    try:
        from engine.als_generator import generate_ableton_project  # type: ignore
        _als_path = generate_ableton_project()
    except Exception as _als_exc:
        print(f"  Warning: ALS generation skipped: {_als_exc}")
        _als_path = None

    try:
        from engine.ableton_rack_builder import export_128_rack_adg
        _rack_adg = export_128_rack_adg(str(OUTPUT))
        print("  128 Rack ADG exported")
    except Exception as _adg_exc:
        print(f"  Warning: 128 Rack ADG skipped: {_adg_exc}")
        _rack_adg = None

    print("  Grandmaster report + Ascension check...")
    _gm_report = build_grandmaster_report_hook()
    _asc_manifest = get_ascension_manifest()
    check_autonomous_director(dna)

    log_milestone(_session_logger, "Sprint 3 exports complete")
    _release_elapsed = time.perf_counter() - _t_release

    # ========================================================
    #  REFLECT
    # ========================================================
    print("  Reflect - lessons + belt assessment...")
    _t_reflect = time.perf_counter()

    record_render_lessons(dna)
    log_milestone(_session_logger, "Render complete - all sprints executed")

    if mem_engine is not None:
        end_render_session(mem_engine, out_path)

    print("  Belt assessment + report card...")
    _report_card = generate_report_card(dna, out_path, master_L, master_R, SR)

    if mem_engine is not None:
        _belt_assessment = assess_belt_promotion(mem_engine, 0, 0)
        _belt_persist = persist_belt_progress(
            mem_engine, _report_card, _belt_assessment, dna)
    else:
        _belt_assessment = {"current_belt": "white", "promoted": False,
                            "message": "No memory engine - belt tracking disabled"}
        _belt_persist = {"total_tracks": "?"}

    _reflect_elapsed = time.perf_counter() - _t_reflect
    total_elapsed = time.perf_counter() - t0

    print(f"  Belt: {_belt_assessment.get('current_belt', 'white').upper()}")
    print(f"  Report Card: {_report_card.get('grade', '?')} "
          f"({_report_card.get('overall_score', '?')})/100)")
    if _belt_assessment.get("promoted"):
        print(f"  {_belt_assessment['message']}")
    elif _belt_assessment.get("next_belt"):
        print(f"  -> {_belt_assessment['message']}")

    print(f"  Phase 4 complete: MASTER {_master_elapsed:.1f}s + "
          f"RELEASE {_release_elapsed:.1f}s + REFLECT {_reflect_elapsed:.1f}s "
          f"= {total_elapsed:.1f}s total")

    # ── ICM workspace handoff ──────────────────────────────────────────
    try:
        from engine.workspace_io import write_phase_four_outputs
        write_phase_four_outputs(
            out_path=out_path,
            report_card=_report_card,
            belt=_belt_assessment,
            dna=dna,
        )
        print("  ✓ Workspace: mwp/stages/04-mastering/output/ updated")
    except Exception as _ws_exc:
        print(f"  ⚠ Workspace write skipped: {_ws_exc}")

    return out_path
