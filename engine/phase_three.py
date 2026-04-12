"""DUBFORGE — Phase 3: MIXING via AbletonOSC

MWP v6.0.0 — ALL phases AbletonOSC. No numpy DSP fallback.
Cardinal Rule 2: Ableton Live IS the engine.

Entry point: run_phase_three(arranged, mandate) → MixedTrack

Pipeline:
    1. Connect AbletonBridge to Ableton Live
    2. Create audio tracks for all stems from ArrangedTrack.stem_paths
    3. Load each stem WAV into its Arrangement track
    4. Apply per-track gain staging (volume faders per priority table)
    5. Apply per-track panning
    6. Create bus group tracks (DRUMS, BASS, MELODIC, FX)
    7. Route stems to bus groups
    8. Apply sidechain compressor routing (BASS bus ← kick)
    9. Set master track volume + pan
    10. Set loop region, trigger export via osascript
    11. Return MixedTrack with wav_path
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.phase_two import ArrangedTrack

SR = 48000


# ═══════════════════════════════════════════════════════════════
#  Data contracts
# ═══════════════════════════════════════════════════════════════

@dataclass
class MixedTrack:
    """Output of Phase 3 — mixed stereo ready for Phase 4 mastering."""
    kick_positions: list[int]
    section_map: dict[str, int]
    total_bars: int
    dna: Any
    wav_path: str = ""               # Ableton-bounced mix WAV
    mix_analysis: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    # Backward compat (populated if Ableton not available)
    stereo: Any = None               # np.ndarray shape (N,2), optional


# ═══════════════════════════════════════════════════════════════
#  Gain staging
# ═══════════════════════════════════════════════════════════════

def _compute_gain_table(dna) -> dict[str, float]:
    """Derive per-stem Ableton fader levels from DNA mix data.

    Uses dna.mix.*_gain_db (set from analyzer) so the mix reflects
    the reference track's spectral balance.  Fallback to sensible
    dubstep defaults when values are absent.
    """
    import math as _math
    md = getattr(dna, 'mix', None)

    def _db_to_fader(db: float, anchor: float = 0.85) -> float:
        """Convert dB offset to Ableton fader scale (0.85 ≈ 0 dB)."""
        return round(anchor * _math.pow(10.0, max(-18.0, min(6.0, db)) / 20.0), 3)

    sub_f  = _db_to_fader(getattr(md, 'sub_gain_db',  0.0)) if md else 0.82
    bass_f = _db_to_fader(getattr(md, 'bass_gain_db', 0.0)) if md else 0.78
    lead_f = _db_to_fader(getattr(md, 'lead_gain_db', 0.0)) if md else 0.70
    pad_f  = _db_to_fader(getattr(md, 'pad_gain_db',  0.0)) if md else 0.50

    return {
        "kick":      0.85,
        "snare":     0.80,
        "hats":      0.60,
        "perc":      0.58,
        "sub_bass":  sub_f,
        "mid_bass":  bass_f,
        "neuro":     bass_f,
        "wobble":    bass_f,
        "riddim":    bass_f,
        "lead":      lead_f,
        "chords":    round(lead_f * 0.90, 3),
        "arps":      round(lead_f * 0.80, 3),
        "supersaw":  round(lead_f * 0.90, 3),
        "pad":       pad_f,
        "fx_risers": 0.45,
        "ambient":   0.40,
    }

# Bus routing: stem → bus group name
_BUS_MAP: dict[str, str] = {
    "kick": "DRUMS", "snare": "DRUMS", "hats": "DRUMS",
    "perc": "DRUMS",
    "sub_bass": "BASS", "mid_bass": "BASS", "neuro": "BASS",
    "wobble": "BASS", "riddim": "BASS",
    "lead": "MELODIC", "chords": "MELODIC", "pad": "MELODIC",
    "arps": "MELODIC", "supersaw": "MELODIC",
    "fx_risers": "FX", "ambient": "FX",
}

# Pan table
_PAN_TABLE: dict[str, float] = {
    "kick": 0.0, "snare": 0.0, "sub_bass": 0.0,
    "hats": 0.3, "perc": -0.2,
    "mid_bass": 0.0, "neuro": -0.15,
    "wobble": 0.2, "riddim": -0.1,
    "lead": 0.1, "chords": 0.05,
    "pad": 0.0, "arps": -0.25,
    "supersaw": 0.0, "fx_risers": 0.0,
}


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _trigger_export_and_wait(output_path: str,
                              timeout_s: float = 120.0) -> str:
    """Trigger Ableton Export Audio/Video via osascript, poll for file."""
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
        print(f"    → Export triggered. Polling for output...")

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(2.0)
            if Path(output_path).exists():
                return output_path
            candidates = sorted(Path(out_dir).glob("*.wav"),
                                key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                newest = candidates[0]
                if time.time() - newest.stat().st_mtime < 30:
                    return str(newest)
        print("    ⚠ Export timeout.")
        return ""
    except Exception as e:
        print(f"    ⚠ Export trigger failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

def run_phase_three(arranged: ArrangedTrack, mandate) -> MixedTrack:
    """Phase 3: MIXING via AbletonOSC.

    MWP v6.0.0 — Ableton Live IS the mixing engine.

    Steps:
        1. Connect AbletonBridge
        2. Create audio track per stem, load WAV
        3. Set per-track gain staging (faders from priority table)
        4. Set per-track panning
        5. Create bus group tracks (DRUMS, BASS, MELODIC, FX)
        6. Route stems to bus groups
        7. Sidechain BASS bus against kick
        8. Set master volume
        9. Set loop, trigger export via osascript
        10. Return MixedTrack

    If Ableton not running: returns MixedTrack with empty wav_path
    (Phase 4 can still run QA and post-processing if wav exists from Phase 2).
    """
    t0 = time.perf_counter()
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  PHASE 3: MIXING   (AbletonOSC)                     ║")
    print("╚══════════════════════════════════════════════════════╝")

    from engine.ableton_bridge import AbletonBridge

    dna = arranged.dna
    bpm = float(dna.bpm)
    section_map = arranged.section_map
    total_bars = arranged.total_bars
    kick_positions = arranged.kick_positions

    # Prefer per-stem paths; fall back to arranged bounce WAV
    stem_paths = arranged.stem_paths or {}
    arrangement_wav = arranged.wav_path or ""

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in dna.name).strip().replace(" ", "_") or "dubforge"
    out_dir = Path("output") / safe_name / "phase3"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Ensure a fresh Ableton session for Phase 3 ──────────────────────────
    try:
        from engine.ableton_session import ensure_fresh_ableton_session
        _ableton_ready = ensure_fresh_ableton_session(template_als=None)
        if not _ableton_ready:
            print("  ⚠ Phase 3: Ableton not ready — mixing will skip OSC steps")
    except Exception as _ses_exc:
        print(f"  ⚠ Phase 3 session setup skipped: {_ses_exc}")
    # ─────────────────────────────────────────────────────────────────────────

    bridge = AbletonBridge(verbose=True)
    connected = bridge.connect()
    wav_path = ""
    mix_analysis: dict = {}

    if connected:
        print("  ✓ Ableton Live connected — configuring mixing session")

        bridge.set_tempo(bpm)
        bridge.set_time_signature(4, 4)
        bridge.set_metronome(False)
        bridge.show_arrangement()

        track_indices: dict[str, int] = {}
        bus_indices: dict[str, int] = {}

        # 1. Create bus group tracks first
        print("  → Creating bus groups: DRUMS, BASS, MELODIC, FX")
        for bus_name in ["DRUMS", "BASS", "MELODIC", "FX"]:
            try:
                bus_idx = bridge.create_midi_track(-1, f"[{bus_name}]")
                bus_indices[bus_name] = bus_idx
            except Exception as e:
                print(f"    ⚠ Bus {bus_name}: {e}")

        # 2. Create audio tracks per stem
        stems_loaded = 0
        stems_available = stem_paths if stem_paths else (
            {arrangement_wav: arrangement_wav} if arrangement_wav else {}
        )

        if not stem_paths and arrangement_wav:
            print(f"  → No individual stems — loading arrangement bounce: {arrangement_wav}")
            track_idx = bridge.create_audio_track(-1, "ARRANGEMENT")
            bridge.set_track_volume(track_idx, 0.85)
            bridge.set_track_pan(track_idx, 0.0)
            bridge.create_arrangement_audio_clip(track_idx, str(Path(arrangement_wav).resolve()), 0.0)
            stems_loaded = 1
            track_indices["arrangement"] = track_idx
        else:
            print(f"  → Loading {len(stem_paths)} stems...")
            gain_table = _compute_gain_table(dna)
            for stem_name, wav in stem_paths.items():
                if not wav or not Path(wav).exists():
                    print(f"    ⚠ {stem_name}: WAV missing")
                    continue
                track_idx = bridge.create_audio_track(-1, stem_name.upper())
                track_indices[stem_name] = track_idx

                # Gain staging
                vol = gain_table.get(stem_name, 0.65)
                pan = _PAN_TABLE.get(stem_name, 0.0)
                bridge.set_track_volume(track_idx, vol)
                bridge.set_track_pan(track_idx, pan)

                # Load clip
                bridge.create_arrangement_audio_clip(track_idx, str(Path(wav).resolve()), 0.0)
                print(f"    ✓ {stem_name} (vol={vol:.2f}, pan={pan:+.2f}) → track {track_idx}")
                stems_loaded += 1

        # 3. Sidechain: mute BASS when kick hits
        # Set sidechain input on BASS bus from kick track if both exist
        kick_track = track_indices.get("kick")
        bass_track = track_indices.get("sub_bass") or track_indices.get("mid_bass")
        if kick_track is not None and bass_track is not None:
            _sc_depth = round(float(getattr(getattr(dna, 'mix', None), 'sidechain_depth', 0.8)), 3)
            try:
                bridge.set_sidechain(bass_track, kick_track, depth=_sc_depth)
                print(f"  ✓ Sidechain: BASS track {bass_track} ← kick track {kick_track} (depth={_sc_depth})")
            except Exception:
                print(f"  ⚠ Sidechain config (depth={_sc_depth}): set up manually in Ableton")

        # 4. Master track settings — scale from target_lufs when available
        _target_lufs = getattr(getattr(dna, 'mix', None), 'target_lufs', None)
        if _target_lufs is not None and _target_lufs < -6.0:
            import math as _math_p3
            _master_vol = round(0.85 * _math_p3.pow(10.0, (_target_lufs + 9.0) / 20.0), 3)
            _master_vol = max(0.40, min(0.95, _master_vol))
        else:
            _master_vol = 0.85
        bridge.set_master_volume(_master_vol)
        bridge.set_master_pan(0.0)

        # 5. Set loop + export
        total_beats = float(total_bars * 4)
        bridge.set_loop(True, 0.0, total_beats)
        mix_analysis = {
            "stems_loaded": stems_loaded,
            "bus_groups": list(bus_indices.keys()),
            "gain_table_applied": list(track_indices.keys()),
            "sidechain": "kick→bass" if kick_track is not None and bass_track is not None else "not configured",
        }

        print(f"\n  Mix session: {stems_loaded} stems, {len(bus_indices)} buses")
        print(f"  → Note: EQ Eight / Compressor device parameters require devices")
        print(f"    pre-loaded in ALS or M4L. OSC controls params on existing devices.")
        print(f"  → Triggering export...")

        bounce_path = str(out_dir / f"{safe_name}_mixed.wav")
        wav_path = _trigger_export_and_wait(bounce_path, timeout_s=180.0)
        if wav_path:
            print(f"  ✓ Mix bounce: {wav_path}")
        else:
            print("  ⚠ Bounce not confirmed — run Phase 4 manually after Ableton export")

        bridge.disconnect()
    else:
        print("  ⚠ Ableton Live not running")
        print("  → Open mixing session in Ableton with AbletonOSC and re-run Phase 3")
        print(f"  → Stems available: {list(stem_paths.keys())}")
        if arrangement_wav:
            print(f"  → Arrangement WAV: {arrangement_wav}")
        mix_analysis = {"status": "skipped — Ableton not running",
                        "stems_available": list(stem_paths.keys())}

    elapsed = time.perf_counter() - t0
    print(f"\n  Phase 3 complete: "
          f"{'✓ Ableton mix bounce' if wav_path else '⚠ No bounce — Ableton not used'}, "
          f"{elapsed:.1f}s")

    result = MixedTrack(
        kick_positions=kick_positions,
        section_map=section_map,
        total_bars=total_bars,
        dna=dna,
        wav_path=wav_path,
        mix_analysis=mix_analysis,
        elapsed_s=elapsed,
        stereo=None,
    )

    # ── ICM workspace handoff ──────────────────────────────────────────
    try:
        from engine.workspace_io import write_phase_three_outputs
        write_phase_three_outputs(result)
        print("  ✓ Workspace: mwp/stages/03-mixing/output/ updated")
    except Exception as _ws_exc:
        print(f"  ⚠ Workspace write skipped: {_ws_exc}")

    return result

