"""
DUBFORGE Engine — Session Template Builder

Defines the canonical Subtronics-aligned Ableton Live session layout.
This is the SINGLE SOURCE OF TRUTH for the track/bus/return structure
that ALL phases reference.

Phase 2 receives Phase 1 output and maps it into this template.
Phase 1 Stage 1A references this template to know WHAT to generate.

Track Layout (25 tracks + 3 returns):
    DRUMS Bus
    ├── Kick (layered: Sub + Body + Click)
    ├── Snare (layered: Head + Tail + Ghost)
    ├── Hi-Hats (velocity-varied, swing applied)
    ├── Percussion (rides, crashes, fills)
    └── [Sidechain trigger — muted]

    BASS Bus
    ├── SUB (sine/triangle — clean, mono, <120Hz)
    ├── MID BASS (Serum — the main growl/wobble/riddim layer)
    ├── GROWL (resampled audio — the texture layer)
    ├── RIDDIM (minimal wub pattern — halftime feel)
    └── FORMANT (vowel bass — the "talking" layer)

    MELODICS Bus
    ├── LEAD (Serum — clean or processed)
    ├── PAD (atmospheric — reverb-heavy)
    ├── ARP (rhythmic melodic content)
    ├── CHORDS (supersaws or plucks)
    └── VOCAL (processed vocals/chops)

    FX Bus
    ├── RISERS (white noise + pitch sweep)
    ├── IMPACTS (sub boom + reverse crash)
    ├── TRANSITIONS (tape stops, glitches)
    └── ATMOS (ambient textures, foley)

    RETURN Tracks
    ├── REVERB (shared space — hall or plate)
    ├── DELAY (tempo-synced — 1/4 or dotted 1/8)
    └── PARALLEL COMP (heavy ratio, blended back)

Arrangement Scenes (Session View):
    INTRO | BUILD 1 | DROP 1 | BREAKDOWN | BUILD 2 | DROP 2 | BRIDGE | FINAL DROP | OUTRO
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

from engine.config_loader import PHI
from engine.log import get_logger

if TYPE_CHECKING:
    from engine.ableton_live import SessionTemplate
    from engine.bus_router import BusRouter

_log = get_logger("dubforge.session_template")


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — Immutable template specification (backflows to Stage 1A)
# ═══════════════════════════════════════════════════════════════════════════

class BusGroup(IntEnum):
    """Bus index constants for routing."""
    DRUMS = 0
    BASS = 1
    MELODICS = 2
    FX = 3


# Color palette — Ableton RGB (0x00RRGGBB format)
COLORS = {
    # Bus groups
    "drums":      0x00FF3333,   # Red
    "bass":       0x00FF6600,   # Orange
    "melodics":   0x003399FF,   # Blue
    "fx":         0x009933FF,   # Purple
    "returns":    0x0066CC66,   # Green
    # Individual tracks
    "kick":       0x00CC2200,
    "snare":      0x00FF4444,
    "hihats":     0x00FF6666,
    "perc":       0x00FF8888,
    "sc_trigger": 0x00333333,   # Dark grey (muted)
    "sub":        0x00FF4400,
    "mid_bass":   0x00FF6600,
    "growl":      0x00FF8800,
    "riddim":     0x00FFAA00,
    "formant":    0x00FFCC00,
    "lead":       0x002266FF,
    "pad":        0x004488FF,
    "arp":        0x0066AAFF,
    "chords":     0x0088CCFF,
    "vocal":      0x00AADDFF,
    "risers":     0x007722CC,
    "impacts":    0x009944CC,
    "transitions":0x00BB66CC,
    "atmos":      0x00DD88CC,
    "reverb":     0x0044AA44,
    "delay":      0x0066CC66,
    "parallel":   0x0088EE88,
}

# Default gain staging — all tracks gain-staged to -6dB headroom
# Values are Ableton-normalized (0.0–1.0, where 0.85 ≈ 0dB, 0.707 ≈ -3dB)
DEFAULT_GAINS = {
    # DRUMS
    "kick":        0.85,
    "snare":       0.80,
    "hihats":      0.72,
    "perc":        0.68,
    "sc_trigger":  0.00,   # Muted (trigger only)
    # BASS
    "sub":         0.82,
    "mid_bass":    0.78,
    "growl":       0.72,
    "riddim":      0.72,
    "formant":     0.68,
    # MELODICS
    "lead":        0.72,
    "pad":         0.60,
    "arp":         0.55,
    "chords":      0.65,
    "vocal":       0.70,
    # FX
    "risers":      0.55,
    "impacts":     0.75,
    "transitions": 0.55,
    "atmos":       0.45,
}

# Send levels per track (to returns)
DEFAULT_SENDS = {
    # (track_name, return_name) → level
    ("kick",    "parallel"):  0.20,
    ("snare",   "reverb"):    0.25,
    ("snare",   "parallel"):  0.30,
    ("hihats",  "delay"):     0.15,
    ("perc",    "reverb"):    0.20,
    ("sub",     "parallel"):  0.00,    # Sub stays dry
    ("mid_bass","parallel"):  0.15,
    ("growl",   "reverb"):    0.10,
    ("lead",    "reverb"):    0.25,
    ("lead",    "delay"):     0.20,
    ("pad",     "reverb"):    0.40,
    ("arp",     "delay"):     0.30,
    ("chords",  "reverb"):    0.30,
    ("vocal",   "reverb"):    0.20,
    ("vocal",   "delay"):     0.15,
    ("risers",  "reverb"):    0.25,
    ("impacts", "reverb"):    0.15,
    ("atmos",   "reverb"):    0.35,
}

# Bus gain staging
BUS_GAINS = {
    "drums":    1.00,
    "bass":     0.90,
    "melodics": 0.75,
    "fx":       0.55,
}

RETURN_GAINS = {
    "reverb":   0.35,
    "delay":    0.30,
    "parallel": 0.25,
}


# ═══════════════════════════════════════════════════════════════════════════
# TRACK DEFINITIONS — Ordered list of all tracks
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TrackDef:
    """Definition of a single track in the session template."""
    name: str
    bus: str                    # "drums" | "bass" | "melodics" | "fx" | "return"
    track_type: str = "audio"   # "audio" | "midi" | "return"
    color: int = 0x00888888
    volume: float = 0.85
    pan: float = 0.0
    mute: bool = False
    mono: bool = False          # Force mono (sub, kick)
    # Routing
    output: str = ""            # Bus name or "Master"
    sends: dict[str, float] = field(default_factory=dict)
    # Device expectations (what devices Phase 1 should pre-load)
    expected_devices: list[str] = field(default_factory=list)
    # Content mapping — what Phase 1 output maps to this track
    mandate_source: str = ""    # Dotted path into SongMandate
    # Processing flags
    sidechain_from: str = ""    # Track name to sidechain from
    low_cut_hz: float = 0.0    # HPF frequency (0 = none)
    high_cut_hz: float = 0.0   # LPF frequency (0 = none)


@dataclass
class SceneDef:
    """Definition of a scene (song section)."""
    name: str
    bars: int
    energy: float = 0.5   # 0.0–1.0
    color: int = 0x00333333


@dataclass
class ReturnDef:
    """Definition of a return track."""
    name: str
    color: int = 0x0066CC66
    volume: float = 0.35
    devices: list[str] = field(default_factory=list)


@dataclass
class SessionLayout:
    """Complete session template layout — THE canonical track list."""
    tracks: list[TrackDef]
    returns: list[ReturnDef]
    scenes: list[SceneDef]
    bus_gains: dict[str, float]


# ═══════════════════════════════════════════════════════════════════════════
# BUILDER — Constructs the canonical session layout
# ═══════════════════════════════════════════════════════════════════════════

def build_dubstep_session(bpm: float = 150.0) -> SessionLayout:
    """
    Build THE canonical Subtronics-aligned dubstep session template.

    This is the single source of truth. Phase 1 generates content to fill
    these tracks. Phase 2 maps Phase 1 output into these tracks.
    Phase 3 mixes through these buses. Phase 4 masters the result.

    Returns SessionLayout with all tracks, returns, scenes, and bus gains.
    """

    tracks = [
        # ══════════════════════════════════════════════
        # DRUMS BUS
        # ══════════════════════════════════════════════
        TrackDef(
            name="Kick", bus="drums", track_type="audio",
            color=COLORS["kick"], volume=DEFAULT_GAINS["kick"],
            mono=True, output="drums",
            mandate_source="drums.kick",
            expected_devices=["EQ Eight", "Compressor", "Saturator"],
            sends={"parallel": DEFAULT_SENDS.get(("kick", "parallel"), 0)},
            low_cut_hz=30.0,
        ),
        TrackDef(
            name="Snare", bus="drums", track_type="audio",
            color=COLORS["snare"], volume=DEFAULT_GAINS["snare"],
            output="drums",
            mandate_source="drums.snare",
            expected_devices=["EQ Eight", "Compressor", "Saturator"],
            sends={
                "reverb": DEFAULT_SENDS.get(("snare", "reverb"), 0),
                "parallel": DEFAULT_SENDS.get(("snare", "parallel"), 0),
            },
            low_cut_hz=100.0,
        ),
        TrackDef(
            name="Hi-Hats", bus="drums", track_type="audio",
            color=COLORS["hihats"], volume=DEFAULT_GAINS["hihats"],
            output="drums",
            mandate_source="drums.hat_closed",
            expected_devices=["EQ Eight", "Compressor"],
            sends={"delay": DEFAULT_SENDS.get(("hihats", "delay"), 0)},
            low_cut_hz=200.0,
        ),
        TrackDef(
            name="Percussion", bus="drums", track_type="audio",
            color=COLORS["perc"], volume=DEFAULT_GAINS["perc"],
            output="drums",
            mandate_source="drums.clap",
            expected_devices=["EQ Eight"],
            sends={"reverb": DEFAULT_SENDS.get(("perc", "reverb"), 0)},
            low_cut_hz=150.0,
        ),
        TrackDef(
            name="SC Trigger", bus="drums", track_type="midi",
            color=COLORS["sc_trigger"], volume=0.0,
            mute=True, output="drums",
            mandate_source="",
            expected_devices=["Operator"],
        ),

        # ══════════════════════════════════════════════
        # BASS BUS
        # ══════════════════════════════════════════════
        TrackDef(
            name="Sub", bus="bass", track_type="audio",
            color=COLORS["sub"], volume=DEFAULT_GAINS["sub"],
            mono=True, output="bass",
            mandate_source="bass.sub",
            expected_devices=["EQ Eight", "Utility"],
            sidechain_from="SC Trigger",
            low_cut_hz=20.0, high_cut_hz=120.0,
        ),
        TrackDef(
            name="Mid Bass", bus="bass", track_type="midi",
            color=COLORS["mid_bass"], volume=DEFAULT_GAINS["mid_bass"],
            output="bass",
            mandate_source="bass.sounds",
            expected_devices=["Serum 2", "OTT", "EQ Eight", "Saturator"],
            sidechain_from="SC Trigger",
            sends={"parallel": DEFAULT_SENDS.get(("mid_bass", "parallel"), 0)},
            low_cut_hz=80.0,
        ),
        TrackDef(
            name="Growl", bus="bass", track_type="audio",
            color=COLORS["growl"], volume=DEFAULT_GAINS["growl"],
            output="bass",
            mandate_source="growl",
            expected_devices=["EQ Eight", "Saturator", "Auto Filter"],
            sidechain_from="SC Trigger",
            sends={"reverb": DEFAULT_SENDS.get(("growl", "reverb"), 0)},
            low_cut_hz=100.0,
        ),
        TrackDef(
            name="Riddim", bus="bass", track_type="midi",
            color=COLORS["riddim"], volume=DEFAULT_GAINS["riddim"],
            output="bass",
            mandate_source="riddim",
            expected_devices=["Serum 2", "OTT", "EQ Eight"],
            sidechain_from="SC Trigger",
            low_cut_hz=80.0,
        ),
        TrackDef(
            name="Formant", bus="bass", track_type="audio",
            color=COLORS["formant"], volume=DEFAULT_GAINS["formant"],
            output="bass",
            mandate_source="vocals.chops",
            expected_devices=["EQ Eight", "Auto Filter", "Corpus"],
            sidechain_from="SC Trigger",
            low_cut_hz=80.0,
        ),

        # ══════════════════════════════════════════════
        # MELODICS BUS
        # ══════════════════════════════════════════════
        TrackDef(
            name="Lead", bus="melodics", track_type="midi",
            color=COLORS["lead"], volume=DEFAULT_GAINS["lead"],
            output="melodics",
            mandate_source="leads.screech",
            expected_devices=["Serum 2", "EQ Eight", "Compressor", "Chorus-Ensemble"],
            sends={
                "reverb": DEFAULT_SENDS.get(("lead", "reverb"), 0),
                "delay": DEFAULT_SENDS.get(("lead", "delay"), 0),
            },
            low_cut_hz=200.0,
        ),
        TrackDef(
            name="Pad", bus="melodics", track_type="midi",
            color=COLORS["pad"], volume=DEFAULT_GAINS["pad"],
            output="melodics",
            mandate_source="atmosphere.dark_pad",
            expected_devices=["Serum 2", "EQ Eight", "Reverb"],
            sends={"reverb": DEFAULT_SENDS.get(("pad", "reverb"), 0)},
            low_cut_hz=100.0,
        ),
        TrackDef(
            name="Arp", bus="melodics", track_type="midi",
            color=COLORS["arp"], volume=DEFAULT_GAINS["arp"],
            output="melodics",
            mandate_source="melody.arp_patterns",
            expected_devices=["Serum 2", "EQ Eight", "Ping Pong Delay"],
            sends={"delay": DEFAULT_SENDS.get(("arp", "delay"), 0)},
            low_cut_hz=200.0,
        ),
        TrackDef(
            name="Chords", bus="melodics", track_type="midi",
            color=COLORS["chords"], volume=DEFAULT_GAINS["chords"],
            output="melodics",
            mandate_source="leads.chord_l",
            expected_devices=["Serum 2", "EQ Eight", "Chorus-Ensemble"],
            sends={"reverb": DEFAULT_SENDS.get(("chords", "reverb"), 0)},
            low_cut_hz=150.0,
        ),
        TrackDef(
            name="Vocal", bus="melodics", track_type="audio",
            color=COLORS["vocal"], volume=DEFAULT_GAINS["vocal"],
            output="melodics",
            mandate_source="vocals.chops",
            expected_devices=["EQ Eight", "Compressor", "Auto Filter"],
            sends={
                "reverb": DEFAULT_SENDS.get(("vocal", "reverb"), 0),
                "delay": DEFAULT_SENDS.get(("vocal", "delay"), 0),
            },
            low_cut_hz=150.0,
        ),

        # ══════════════════════════════════════════════
        # FX BUS
        # ══════════════════════════════════════════════
        TrackDef(
            name="Risers", bus="fx", track_type="audio",
            color=COLORS["risers"], volume=DEFAULT_GAINS["risers"],
            output="fx",
            mandate_source="fx.riser",
            expected_devices=["Auto Filter", "Reverb"],
            sends={"reverb": DEFAULT_SENDS.get(("risers", "reverb"), 0)},
        ),
        TrackDef(
            name="Impacts", bus="fx", track_type="audio",
            color=COLORS["impacts"], volume=DEFAULT_GAINS["impacts"],
            output="fx",
            mandate_source="fx.boom",
            expected_devices=["EQ Eight", "Compressor"],
            sends={"reverb": DEFAULT_SENDS.get(("impacts", "reverb"), 0)},
            low_cut_hz=30.0,
        ),
        TrackDef(
            name="Transitions", bus="fx", track_type="audio",
            color=COLORS["transitions"], volume=DEFAULT_GAINS["transitions"],
            output="fx",
            mandate_source="fx.tape_stop",
            expected_devices=["Auto Filter", "Beat Repeat"],
        ),
        TrackDef(
            name="Atmos", bus="fx", track_type="audio",
            color=COLORS["atmos"], volume=DEFAULT_GAINS["atmos"],
            output="fx",
            mandate_source="atmosphere.noise_bed",
            expected_devices=["EQ Eight", "Reverb", "Utility"],
            sends={"reverb": DEFAULT_SENDS.get(("atmos", "reverb"), 0)},
            low_cut_hz=80.0,
        ),
    ]

    returns = [
        ReturnDef(
            name="Reverb", color=COLORS["reverb"],
            volume=RETURN_GAINS["reverb"],
            devices=["Reverb", "EQ Eight"],
        ),
        ReturnDef(
            name="Delay", color=COLORS["delay"],
            volume=RETURN_GAINS["delay"],
            devices=["Delay", "EQ Eight"],
        ),
        ReturnDef(
            name="Parallel Comp", color=COLORS["parallel"],
            volume=RETURN_GAINS["parallel"],
            devices=["Glue Compressor", "Utility"],
        ),
    ]

    # Standard Subtronics arrangement scenes
    scenes = [
        SceneDef("INTRO",       bars=8,   energy=0.2,  color=0x00334455),
        SceneDef("BUILD 1",     bars=16,  energy=0.5,  color=0x00445566),
        SceneDef("DROP 1",      bars=16,  energy=1.0,  color=0x00FF3300),
        SceneDef("BREAKDOWN",   bars=8,   energy=0.3,  color=0x00336655),
        SceneDef("BUILD 2",     bars=16,  energy=0.6,  color=0x00556677),
        SceneDef("DROP 2",      bars=16,  energy=1.0,  color=0x00FF4400),
        SceneDef("BRIDGE",      bars=8,   energy=0.4,  color=0x00445588),
        SceneDef("FINAL DROP",  bars=16,  energy=1.0,  color=0x00FF0000),
        SceneDef("OUTRO",       bars=8,   energy=0.1,  color=0x00223344),
    ]

    return SessionLayout(
        tracks=tracks,
        returns=returns,
        scenes=scenes,
        bus_gains=dict(BUS_GAINS),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1A BACKFLOW — What Phase 1 must generate to fill this template
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TemplateRequirements:
    """What Phase 1 must generate to satisfy the session template.

    Backflows to Stage 1A so the oracle knows WHAT content to produce.
    """
    # Required audio stems (track_name → mandate dotted path)
    required_stems: dict[str, str]
    # Required MIDI instruments (track_name → expected VST)
    required_instruments: dict[str, str]
    # Bus routing expectations
    bus_names: list[str]
    return_names: list[str]
    # Scene structure (section_name → bars)
    scene_bars: dict[str, int]
    # Total expected bar count
    total_bars: int
    # Sidechain sources
    sidechain_pairs: dict[str, str]   # target → source


def get_template_requirements(layout: SessionLayout | None = None) -> TemplateRequirements:
    """
    Extract what Phase 1 must generate to fill the session template.

    Called by Stage 1A to inform the oracle what content is needed.
    """
    if layout is None:
        layout = build_dubstep_session()

    required_stems: dict[str, str] = {}
    required_instruments: dict[str, str] = {}
    sidechain_pairs: dict[str, str] = {}

    for track in layout.tracks:
        if track.mandate_source:
            if track.track_type == "audio":
                required_stems[track.name] = track.mandate_source
            elif track.track_type == "midi":
                required_instruments[track.name] = track.mandate_source
        if track.sidechain_from:
            sidechain_pairs[track.name] = track.sidechain_from

    bus_names = sorted(set(t.bus for t in layout.tracks))
    return_names = [r.name for r in layout.returns]

    scene_bars: dict[str, int] = {}
    total = 0
    for scene in layout.scenes:
        scene_bars[scene.name] = scene.bars
        total += scene.bars

    return TemplateRequirements(
        required_stems=required_stems,
        required_instruments=required_instruments,
        bus_names=bus_names,
        return_names=return_names,
        scene_bars=scene_bars,
        total_bars=total,
        sidechain_pairs=sidechain_pairs,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CONVERTERS — Template → existing data models
# ═══════════════════════════════════════════════════════════════════════════

def to_ableton_live_template(layout: SessionLayout,
                             bpm: float = 150.0,
                             root_note: int = 5,
                             scale_name: str = "Minor") -> "SessionTemplate":
    """
    Convert SessionLayout to ableton_live.SessionTemplate-compatible dict.

    This bridges our canonical layout to the existing SessionTemplate dataclass
    so als_generator.py and ableton_bridge.py can consume it.
    """
    from engine.ableton_live import (
        TrackConfig, DeviceConfig, SendLevel,
        SessionTemplate, SceneConfig, DeviceType,
    )

    tracks = []
    for i, t in enumerate(layout.tracks):
        sends = []
        for j, ret in enumerate(layout.returns):
            level = t.sends.get(ret.name.lower(), 0.0)
            sends.append(SendLevel(return_index=j, level=level))

        devices = [
            DeviceConfig(
                class_name=d, display_name=d,
                device_type=(DeviceType.INSTRUMENT
                             if d in ("Serum 2", "Operator")
                             else DeviceType.AUDIO_EFFECT),
            )
            for d in t.expected_devices
        ]

        tracks.append(TrackConfig(
            name=t.name,
            track_type=t.track_type,
            color=t.color,
            volume=t.volume,
            pan=t.pan,
            mute=t.mute,
            devices=devices,
            sends=sends,
            output_routing=t.output or "Master",
        ))

    return_tracks = []
    for ret in layout.returns:
        devices = [
            DeviceConfig(class_name=d, display_name=d)
            for d in ret.devices
        ]
        return_tracks.append(TrackConfig(
            name=ret.name,
            track_type="return",
            color=ret.color,
            volume=ret.volume,
            devices=devices,
        ))

    scenes = [
        SceneConfig(name=s.name, index=i, color=s.color)
        for i, s in enumerate(layout.scenes)
    ]

    return SessionTemplate(
        name="DUBFORGE Subtronics Template",
        bpm=bpm,
        root_note=root_note,
        scale_name=scale_name,
        tracks=tracks,
        return_tracks=return_tracks,
        scenes=scenes,
    )


def to_bus_router(layout: SessionLayout) -> "BusRouter":  # engine.bus_router.BusRouter
    """
    Convert SessionLayout to a BusRouter with proper hierarchy.

    Upgrades the existing create_dubstep_template() with the
    full track-level routing from our canonical layout.
    """
    from engine.bus_router import BusRouter

    router = BusRouter()

    # Create bus hierarchy
    for bus_name, gain in layout.bus_gains.items():
        router.add_bus(bus_name, gain=gain)

    # Return buses
    for ret in layout.returns:
        router.add_bus(ret.name.lower(), gain=ret.volume)

    return router


def to_als_tracks(layout: SessionLayout) -> list:  # list[ALSTrack]
    """
    Convert SessionLayout to ALSTrack-compatible dicts for als_generator.
    Phase 1 uses this to build the .als file with the correct track structure.
    """
    from engine.als_generator import ALSTrack

    als_tracks = []
    for t in layout.tracks:
        als_tracks.append(ALSTrack(
            name=t.name,
            track_type=t.track_type,
            color=t.color,
            volume_db=_vol_to_db(t.volume),
            pan=t.pan,
            mute=t.mute,
            device_names=list(t.expected_devices),
        ))

    for ret in layout.returns:
        als_tracks.append(ALSTrack(
            name=ret.name,
            track_type="return",
            color=ret.color,
            volume_db=_vol_to_db(ret.volume),
            device_names=list(ret.devices),
        ))

    return als_tracks


def _vol_to_db(vol: float) -> float:
    """Convert Ableton normalized volume (0–1) to dB."""
    if vol <= 0:
        return -70.0
    import math
    return 20 * math.log10(vol)


# ═══════════════════════════════════════════════════════════════════════════
# STEM MAPPING — Phase 1 output → template track assignment
# ═══════════════════════════════════════════════════════════════════════════

# Map from SongMandate field paths to track names
MANDATE_TO_TRACK: dict[str, str] = {
    # Drums
    "drums.kick":       "Kick",
    "drums.snare":      "Snare",
    "drums.hat_closed": "Hi-Hats",
    "drums.hat_open":   "Hi-Hats",     # Layered onto same track
    "drums.clap":       "Percussion",
    "drums.crash":      "Percussion",
    "drums.ride":       "Percussion",
    "drums.perc":       "Percussion",
    # Bass
    "bass.sub":         "Sub",
    "bass.sounds":      "Mid Bass",     # Primary bass rotation
    "bass.reese":       "Growl",        # Reese → growl texture
    "growl":            "Growl",
    "riddim":           "Riddim",
    "formant":          "Formant",
    # Melodics
    "leads.screech":    "Lead",
    "leads.fm_lead":    "Lead",
    "leads.pluck":      "Chords",
    "leads.chord_l":    "Chords",
    "leads.chord_r":    "Chords",
    "atmosphere.dark_pad":  "Pad",
    "atmosphere.lush_pad":  "Pad",
    "atmosphere.drone":     "Pad",
    "melody.arp_patterns":  "Arp",
    "melody.lead_melody":   "Lead",
    "vocals.chops":     "Vocal",
    # FX
    "fx.riser":         "Risers",
    "fx.boom":          "Impacts",
    "fx.hit":           "Impacts",
    "fx.rev_crash":     "Impacts",
    "fx.tape_stop":     "Transitions",
    "fx.pitch_dive":    "Transitions",
    "fx.stutter":       "Transitions",
    "fx.gate_chop":     "Transitions",
    "atmosphere.noise_bed": "Atmos",
}

# Reverse: track name → list of mandate paths
TRACK_TO_MANDATE: dict[str, list[str]] = {}
for path, track in MANDATE_TO_TRACK.items():
    TRACK_TO_MANDATE.setdefault(track, []).append(path)


# ═══════════════════════════════════════════════════════════════════════════
# MODULE WIRING — Which engine modules serve each track
# ═══════════════════════════════════════════════════════════════════════════

# Maps track names to the engine modules that generate their content
TRACK_MODULES: dict[str, list[str]] = {
    # DRUMS
    "Kick":        ["drum_generator", "perc_synth", "drum_pipeline"],
    "Snare":       ["drum_generator", "perc_synth", "drum_pipeline"],
    "Hi-Hats":     ["drum_generator", "perc_synth", "groove"],
    "Percussion":  ["drum_generator", "perc_synth", "beat_repeat"],
    "SC Trigger":  ["sidechain"],
    # BASS
    "Sub":         ["bass_oneshot", "sub_bass", "sidechain"],
    "Mid Bass":    ["bass_oneshot", "fm_synth", "growl_resampler", "wobble_bass",
                    "riddim_engine", "wave_folder", "resample_feedback", "serum2"],
    "Growl":       ["growl_resampler", "resample_feedback", "granular_depth"],
    "Riddim":      ["riddim_engine", "serum2"],
    "Formant":     ["formant_synth", "vocal_chop", "vocal_mangle"],
    # MELODICS
    "Lead":        ["lead_synth", "additive_synth", "arp_synth", "serum2"],
    "Pad":         ["pad_synth", "drone_synth", "ambient_texture", "granular_synth"],
    "Arp":         ["arp_synth", "serum2"],
    "Chords":      ["chord_pad", "supersaw", "karplus_strong", "guitar_synth"],
    "Vocal":       ["vocal_chop", "vocal_mangle", "vocal_processor"],
    # FX
    "Risers":      ["riser_synth", "noise_generator", "fx_generator"],
    "Impacts":     ["impact_hit", "fx_generator"],
    "Transitions": ["transition_fx", "glitch_engine", "beat_repeat"],
    "Atmos":       ["ambient_texture", "granular_synth", "granular_depth", "noise_generator"],
    # RETURNS
    "Reverb":      ["reverb_delay", "convolution"],
    "Delay":       ["reverb_delay"],
    "Parallel Comp": ["dynamics", "dynamics_processor"],
}

# Which new Session 13 gap modules integrate at which tracks
GAP_MODULE_TRACKS: dict[str, list[str]] = {
    "resample_feedback": ["Mid Bass", "Growl"],
    "wavetable_export":  ["Mid Bass", "Riddim", "Lead"],
    "granular_depth":    ["Growl", "Pad", "Atmos"],
    "guitar_synth":      ["Chords", "Lead"],
    "vocal_mangle":      ["Vocal", "Formant"],
    "serum_lfo_shapes":  ["Mid Bass", "Lead", "Arp", "Riddim"],
    "ab_workflow":       ["Mid Bass", "Lead"],   # Used for sound selection
    "vip_generator":     ["Mid Bass", "Lead"],   # VIP variant generation
}
