"""DUBFORGE — Phase 2 Setup: Template → Ableton Session

Bridges Phase 1 output (SongMandate) into the canonical session template
(engine/session_template.py) and prepares the Ableton Live session.

This module replaces the flat stereo-mix approach with structured
bus-routed arrangement.  It runs BETWEEN Phase 1 and Phase 2's
section placement.

Pipeline:
    Phase 1 (SongMandate) → Phase 2 Setup → Phase 2 Arrange → Phase 3 Mix

Responsibilities:
    1. Build the canonical session layout (from session_template)
    2. Map SongMandate stems → template track slots
    3. Create Ableton session (SessionTemplate → AbletonBridge or ALS)
    4. Apply per-track processing chains (EQ, compression, sidechain)
    5. Configure bus routing, sends, and return effects
    6. Build scene structure from arrangement sections
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engine.session_template import (
    SessionLayout,
    TrackDef,
    SceneDef,
    build_dubstep_session,
    get_template_requirements,
    MANDATE_TO_TRACK,
    TRACK_TO_MANDATE,
    TRACK_MODULES,
    GAP_MODULE_TRACKS,
    BUS_GAINS,
    RETURN_GAINS,
    to_ableton_live_template,
    to_bus_router,
)
from engine.log import get_logger

_log = get_logger("dubforge.phase_two_setup")

SR = 48000


# ═══════════════════════════════════════════════════════════════════════════
#  DATA MODEL — Structured arrangement (replaces flat L/R)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TrackArrangement:
    """Audio content for a single track in the session."""
    name: str
    bus: str
    samples: np.ndarray | None = None
    midi_clips: list[Any] = field(default_factory=list)
    # Processing state
    gain: float = 0.85
    pan: float = 0.0
    mute: bool = False
    sends: dict[str, float] = field(default_factory=dict)
    # Section placement (section_name → bar offset within track)
    section_offsets: dict[str, int] = field(default_factory=dict)


@dataclass
class BusArrangement:
    """All tracks routed through a single bus."""
    name: str
    gain: float = 1.0
    tracks: list[TrackArrangement] = field(default_factory=list)


@dataclass
class SessionArrangement:
    """Complete structured arrangement — Phase 2 output.

    Replaces the flat ArrangedTrack (L/R lists) with per-bus/per-track
    structure that Phase 3 can mix properly.
    """
    buses: dict[str, BusArrangement] = field(default_factory=dict)
    returns: dict[str, TrackArrangement] = field(default_factory=dict)
    layout: SessionLayout | None = None
    # Timing
    bpm: float = 150.0
    total_bars: int = 0
    total_samples: int = 0
    # Section map (name → bar offset)
    section_map: dict[str, int] = field(default_factory=dict)
    # Sidechain data
    kick_positions: list[int] = field(default_factory=list)
    # Energy curve
    energy_curve: np.ndarray | None = None
    elapsed_s: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
#  STEM RESOLVER — SongMandate → track assignment
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_attr(obj: Any, dotted_path: str) -> Any:
    """Resolve a dotted attribute path like 'drums.kick' against an object."""
    parts = dotted_path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def _to_np(signal: Any) -> np.ndarray | None:
    """Convert audio to numpy, return None if empty."""
    if signal is None:
        return None
    if isinstance(signal, np.ndarray):
        if signal.size == 0:
            return None
        return signal.astype(np.float64)
    if isinstance(signal, (list, tuple)):
        if len(signal) == 0:
            return None
        return np.array(signal, dtype=np.float64)
    if isinstance(signal, dict):
        # For dicts (like bass.sounds, leads.screech), return first non-None value
        for v in signal.values():
            result = _to_np(v)
            if result is not None:
                return result
        return None
    return None


def resolve_mandate_stems(mandate: Any, layout: SessionLayout) -> dict[str, np.ndarray | None]:
    """Map SongMandate fields to track names using the canonical mapping.

    Returns {track_name: np.ndarray or None} for every track in the layout.
    """
    result: dict[str, np.ndarray | None] = {}

    for track_def in layout.tracks:
        track_name = track_def.name
        mandate_paths = TRACK_TO_MANDATE.get(track_name, [])

        # Try each path until we find audio
        audio = None
        for path in mandate_paths:
            resolved = _resolve_attr(mandate, path)
            audio = _to_np(resolved)
            if audio is not None:
                break

        result[track_name] = audio

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  PROCESSING — Per-track signal chain setup
# ═══════════════════════════════════════════════════════════════════════════

def _apply_track_processing(audio: np.ndarray, track_def: TrackDef,
                            sr: int = SR) -> np.ndarray:
    """Apply basic per-track processing based on track definition.

    - Mono collapse (if track_def.mono)
    - High-pass filter (if track_def.low_cut_hz > 0)
    - Low-pass filter (if track_def.high_cut_hz > 0)
    - Gain staging
    """
    if audio is None or audio.size == 0:
        return audio

    from engine.dsp_core import svf_highpass, svf_lowpass

    out = audio.copy()

    # Mono collapse
    if track_def.mono and out.ndim > 1 and out.shape[0] >= 2:
        out = (out[0] + out[1]) * 0.5
    elif out.ndim > 1:
        out = out[0]  # Take first channel for mono processing

    # HPF
    if track_def.low_cut_hz > 0:
        out = svf_highpass(out, track_def.low_cut_hz, 0.707, sr)

    # LPF
    if track_def.high_cut_hz > 0:
        out = svf_lowpass(out, track_def.high_cut_hz, 0.707, sr)

    # Gain
    out = out * track_def.volume

    return out


def _apply_sidechain(audio: np.ndarray, kick_positions: list[int],
                     sr: int = SR) -> np.ndarray:
    """Apply sidechain ducking to audio based on kick positions."""
    if audio is None or audio.size == 0 or not kick_positions:
        return audio

    try:
        from engine.sidechain import apply_sidechain, SidechainPreset
        preset = SidechainPreset(shape="pump", depth=0.8, release_ms=150.0)  # type: ignore[call-arg]
        return apply_sidechain(audio, kick_positions, preset, sr)  # type: ignore[call-arg]
    except ImportError:
        # Fallback: simple envelope
        out = audio.copy()
        duck_samples = int(0.1 * sr)  # 100ms duck
        for pos in kick_positions:
            if pos < len(out):
                end = min(pos + duck_samples, len(out))
                for i in range(pos, end):
                    t = (i - pos) / duck_samples
                    out[i] *= t  # Linear fade-in
        return out


# ═══════════════════════════════════════════════════════════════════════════
#  SCENE BUILDER — Arrangement sections → Ableton scenes
# ═══════════════════════════════════════════════════════════════════════════

def build_scene_map(mandate: Any, layout: SessionLayout) -> dict[str, int]:
    """Build section_name → bar_offset map from SongMandate arrangement.

    Uses the mandate's arrangement_template if available, falls back to
    the session template's default scene structure.
    """
    scene_map: dict[str, int] = {}
    offset = 0

    # Try mandate's arrangement_template first
    arr = getattr(mandate, "arrangement_template", None)
    if arr is not None and hasattr(arr, "sections"):
        for section in arr.sections:
            name = section.name.upper()
            scene_map[name] = offset
            offset += section.bars
    else:
        # Fall back to template scenes
        for scene in layout.scenes:
            scene_map[scene.name] = offset
            offset += scene.bars

    return scene_map


# ═══════════════════════════════════════════════════════════════════════════
#  ENERGY CURVE — Section-driven energy for mixing decisions
# ═══════════════════════════════════════════════════════════════════════════

def build_energy_curve(mandate: Any, total_samples: int,
                       sr: int = SR) -> np.ndarray:
    """Build a per-sample energy curve from arrangement section intensities.

    This drives per-section gain, sidechain depth, and effects sends.
    """
    bpm = getattr(mandate, "dna", None)
    if bpm is not None:
        bpm = getattr(bpm, "bpm", 150.0)
    else:
        bpm = 150.0

    beat_s = 60.0 / bpm
    bar_s = beat_s * 4
    bar_samples = int(bar_s * sr)

    curve = np.zeros(total_samples, dtype=np.float64)

    arr = getattr(mandate, "arrangement_template", None)
    if arr is not None and hasattr(arr, "sections"):
        offset = 0
        for section in arr.sections:
            n_samples = section.bars * bar_samples
            end = min(offset + n_samples, total_samples)
            energy = getattr(section, "intensity", 0.5)
            curve[offset:end] = energy
            offset = end
    else:
        curve[:] = 0.5

    return curve


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY — Phase 2 Setup
# ═══════════════════════════════════════════════════════════════════════════

def setup_phase_two(mandate: Any) -> SessionArrangement:
    """Set up the structured session from SongMandate.

    This is the bridge between Phase 1 (IDEA → MANDATE) and
    Phase 2 (ARRANGE section-by-section placement).

    Steps:
        1. Build canonical layout (session_template)
        2. Convert mandate sections → scene map
        3. Resolve mandate stems → track slots
        4. Apply per-track processing (EQ, gain, mono)
        5. Build bus structure
        6. Apply sidechain to marked tracks
        7. Initialize return track processing
        8. Build energy curve

    Returns SessionArrangement ready for section placement.
    """
    t0 = time.perf_counter()
    print("\n═══ PHASE 2 SETUP: Template → Session ═══")

    # ── 1. Build canonical layout ──
    dna = getattr(mandate, "dna", None)
    bpm = getattr(dna, "bpm", 150.0) if dna else 150.0
    layout = build_dubstep_session(bpm=bpm)
    requirements = get_template_requirements(layout)

    print(f"  Template: {len(layout.tracks)} tracks + "
          f"{len(layout.returns)} returns, "
          f"{len(layout.scenes)} scenes, "
          f"{requirements.total_bars} default bars")
    print(f"  Required stems: {len(requirements.required_stems)} audio + "
          f"{len(requirements.required_instruments)} MIDI")

    # ── 2. Scene map from mandate arrangement ──
    scene_map = build_scene_map(mandate, layout)
    total_bars = sum(scene_map.values()) if not scene_map else max(
        offset + next(
            (s.bars for s in layout.scenes if s.name == name),
            8
        )
        for name, offset in scene_map.items()
    )
    # Use mandate's total if available
    mandate_bars = getattr(mandate, "total_bars", 0)
    if mandate_bars > 0:
        total_bars = mandate_bars

    beat_s = 60.0 / bpm
    bar_s = beat_s * 4
    total_samples = int(total_bars * 4 * beat_s * SR)

    print(f"  Arrangement: {len(scene_map)} sections, {total_bars} bars, "
          f"{total_samples / SR:.1f}s")

    # ── 3. Resolve mandate stems → track slots ──
    stem_map = resolve_mandate_stems(mandate, layout)
    filled = sum(1 for v in stem_map.values() if v is not None)
    print(f"  Stems resolved: {filled}/{len(stem_map)} tracks have audio")

    # ── 4–6. Build buses with processed tracks ──
    buses: dict[str, BusArrangement] = {}
    kick_positions: list[int] = []

    # Extract kick positions from mandate if available
    drums = getattr(mandate, "drums", None)
    if drums is not None:
        kick_audio = getattr(drums, "kick", None)
        if kick_audio is not None:
            kick_np = _to_np(kick_audio)
            if kick_np is not None:
                # Find trigger points (peaks above threshold)
                threshold = np.max(np.abs(kick_np)) * 0.5
                peaks = np.where(np.abs(kick_np) > threshold)[0]
                if len(peaks) > 0:
                    # Debounce: keep only first peak in each group
                    min_gap = int(0.1 * SR)
                    debounced = [peaks[0]]
                    for p in peaks[1:]:
                        if p - debounced[-1] > min_gap:
                            debounced.append(p)
                    kick_positions = debounced

    for track_def in layout.tracks:
        bus_name = track_def.bus
        if bus_name not in buses:
            buses[bus_name] = BusArrangement(
                name=bus_name,
                gain=layout.bus_gains.get(bus_name, 1.0),
            )

        audio = stem_map.get(track_def.name)

        # Apply per-track processing
        if audio is not None:
            audio = _apply_track_processing(audio, track_def, SR)

        # Apply sidechain if configured
        if track_def.sidechain_from and audio is not None and kick_positions:
            audio = _apply_sidechain(audio, kick_positions, SR)

        track_arr = TrackArrangement(
            name=track_def.name,
            bus=bus_name,
            samples=audio,
            gain=track_def.volume,
            pan=track_def.pan,
            mute=track_def.mute,
            sends=dict(track_def.sends),
        )
        buses[bus_name].tracks.append(track_arr)

    bus_summary = {name: len(bus.tracks) for name, bus in buses.items()}
    print(f"  Buses: {bus_summary}")

    # ── 7. Return tracks ──
    returns: dict[str, TrackArrangement] = {}
    for ret in layout.returns:
        returns[ret.name.lower()] = TrackArrangement(
            name=ret.name,
            bus="return",
            gain=ret.volume,
        )
    print(f"  Returns: {list(returns.keys())}")

    # ── 8. Energy curve ──
    energy_curve = build_energy_curve(mandate, total_samples, SR)

    elapsed = time.perf_counter() - t0
    print(f"  Phase 2 Setup complete: {elapsed:.2f}s")

    return SessionArrangement(
        buses=buses,
        returns=returns,
        layout=layout,
        bpm=bpm,
        total_bars=total_bars,
        total_samples=total_samples,
        section_map=scene_map,
        kick_positions=kick_positions,
        energy_curve=energy_curve,
        elapsed_s=elapsed,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  ALS EXPORT — Generate .als file from session arrangement
# ═══════════════════════════════════════════════════════════════════════════

def export_session_als(arrangement: SessionArrangement,
                       output_path: str | None = None) -> str | None:
    """Export the session arrangement as an Ableton .als file.

    Uses als_generator to build the project file with all tracks,
    buses, and scenes configured.
    """
    if arrangement.layout is None:
        _log.warning("Cannot export ALS without layout")
        return None

    try:
        from engine.als_generator import ALSProject, ALSTrack, write_als

        dna = None
        for bus in arrangement.buses.values():
            for t in bus.tracks:
                if t.samples is not None:
                    # We have at least some audio
                    break

        template = to_ableton_live_template(
            arrangement.layout,
            bpm=arrangement.bpm,
        )

        project = ALSProject(
            name=template.name,
            bpm=arrangement.bpm,
            tracks=[],
        )

        for track_config in template.tracks:
            project.tracks.append(ALSTrack(
                name=track_config.name,
                track_type=track_config.track_type,
                color=track_config.color,
                volume_db=_vol_to_db(track_config.volume),
                pan=track_config.pan,
                mute=track_config.mute,
                device_names=[d.class_name for d in track_config.devices],
            ))

        for ret_config in template.return_tracks:
            project.tracks.append(ALSTrack(
                name=ret_config.name,
                track_type="return",
                color=ret_config.color,
                volume_db=_vol_to_db(ret_config.volume),
                device_names=[d.class_name for d in ret_config.devices],
            ))

        if output_path:
            write_als(project, output_path)
            _log.info("ALS exported: %s", output_path)
            return output_path

        return None
    except Exception as exc:
        _log.warning("ALS export failed: %s", exc)
        return None


def _vol_to_db(vol: float) -> float:
    """Convert normalized volume to dB."""
    if vol <= 0:
        return -70.0
    import math
    return 20 * math.log10(vol)
