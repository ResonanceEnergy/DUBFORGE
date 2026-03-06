"""
DUBFORGE Engine — Ableton Live Integration Engine

Comprehensive internal model of Ableton Live's architecture, Live Object Model
(LOM), session/arrangement generation, MIDI clip creation, device chain presets,
and ALS-compatible project templates — all governed by phi/Fibonacci doctrine.

== ABLETON LIVE ARCHITECTURE (Learned Inside-Out) ==

CORE CONCEPTS:
    Song (live_set): The root — tempo, time signature, tracks, scenes, transport
    Tracks: Audio, MIDI, Return (send/return bus), Master
    Clips: MIDI clips (note data) or Audio clips (sample references)
    ClipSlots: Session View grid cells (track × scene matrix)
    Scenes: Horizontal rows in Session View — fire all clips in a row
    Devices: Instruments, Audio Effects, MIDI Effects, Racks, Max4Live
    DeviceParameters: Automatable knobs/faders on each device
    Chains: Sub-chains inside Rack devices (Instrument/Audio/Drum Racks)
    MixerDevice: Volume, Pan, Sends per track
    CuePoints: Arrangement View markers/locators

SESSION VIEW:
    - Clip launch grid (tracks × scenes)
    - Each ClipSlot can hold one Clip or be empty
    - Scenes fire all clips in their row simultaneously
    - Clip launch quantization: None, 1/32 to 8 Bars
    - Launch modes: Trigger, Gate, Toggle, Repeat
    - Follow Actions for automatic clip sequencing

ARRANGEMENT VIEW:
    - Linear timeline (horizontal)
    - Clips placed at specific beat positions
    - Automation lanes per track/parameter
    - CuePoints (locators) for navigation
    - Loop region (start/length)

DEVICE CHAIN (per track):
    MIDI Track: [MIDI Effects] → [Instrument] → [Audio Effects] → Mixer
    Audio Track: [Audio Effects] → Mixer
    Rack Devices: Instrument Rack, Audio Effect Rack, Drum Rack
        - Chains inside racks, each chain has its own device chain
        - Macro controls (up to 16) mapped to inner parameters
        - Chain selector for key/velocity zones

ROUTING:
    - Input: External (audio/MIDI interface), other tracks, Resampling
    - Output: Master, other tracks, sends to Return tracks, external
    - Send/Return: parallel FX buses via return tracks
    - Pre/Post fader send modes

LIVE OBJECT MODEL (LOM) HIERARCHY:
    Application
    └── Song (live_set)
        ├── tracks[] → Track
        │   ├── clip_slots[] → ClipSlot → Clip
        │   ├── arrangement_clips[] → Clip
        │   ├── devices[] → Device / RackDevice / PluginDevice
        │   │   ├── parameters[] → DeviceParameter
        │   │   ├── chains[] → Chain → devices[]
        │   │   └── drum_pads[] → DrumPad → chains[]
        │   └── mixer_device → MixerDevice
        │       ├── volume, panning, sends[]
        │       └── crossfader (master only)
        ├── return_tracks[] → Track
        ├── master_track → Track
        ├── scenes[] → Scene → clip_slots[]
        ├── cue_points[] → CuePoint
        ├── groove_pool → GroovePool → grooves[]
        └── tuning_system → TuningSystem

KEY LIVE PROPERTIES:
    Song: tempo (20-999 BPM), signature, is_playing, loop, root_note, scale_name
    Track: arm, mute, solo, name, color, has_midi_input, devices, clip_slots
    Clip: name, color, length, loop_start/end, looping, notes, warp_mode
    Device: name, class_name, type (instrument/audio_fx/midi_fx), parameters
    DeviceParameter: value (min→max), name, automation_state, is_quantized

PYTHON API ACCESS (via Max for Live or MIDI Remote Scripts):
    - import Live
    - song = Live.Application.get_application().get_document()
    - song.tracks, song.scenes, song.tempo, etc.
    - Full read/write access to entire LOM
    - Observer pattern for real-time callbacks

ALS FILE FORMAT:
    - Gzipped XML (.als = gzip of .xml)
    - Contains complete project state: tracks, clips, devices, automation
    - Can be programmatically generated or parsed

ABLETON LINK:
    - Network tempo/beat sync protocol
    - is_ableton_link_enabled, force_link_beat_time
    - Start/Stop sync across devices

NATIVE DEVICES (key ones for DUBFORGE):
    Instruments: Wavetable, Drift, Meld, Simpler, Sampler, Operator, Analog
    Audio FX: EQ Eight, Compressor, Glue Compressor, Saturator, OTT (multiband),
              Corpus, Erosion, Frequency Shifter, Grain Delay, Spectral Resonator,
              Spectral Time, Hybrid Reverb, Echo, Chorus-Ensemble, Phaser-Flanger,
              Roar, Shifter, Utility, Limiter, Gate
    MIDI FX: Arpeggiator, Chord, Note Length, Pitch, Random, Scale, Velocity
    Racks: Instrument Rack, Audio Effect Rack, Drum Rack, MIDI Effect Rack

TUNING SYSTEM (Live 12):
    - Custom micro-tuning support
    - note_tunings (cents deviation per note)
    - reference_pitch, pseudo_octave
    - Perfect for DUBFORGE 432 Hz integration

Outputs:
    output/ableton/session_template_<name>.json
    output/ableton/arrangement_template_<name>.json
    output/ableton/device_chain_<name>.json
    output/ableton/midi_clips_<name>.json
"""

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from enum import IntEnum

# --- DUBFORGE Constants ---------------------------------------------------

PHI = 1.6180339887498948482
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
A4_432 = 432.0
A4_440 = 440.0

# Ableton color palette (subset — RGB as 0x00RRGGBB)
ABLETON_COLORS = {
    "red":         0x00FF0000,
    "orange":      0x00FF6600,
    "yellow":      0x00FFFF00,
    "green":       0x0000FF00,
    "cyan":        0x0000FFFF,
    "blue":        0x000000FF,
    "purple":      0x009900CC,
    "magenta":     0x00FF00FF,
    "pink":        0x00FF6699,
    "white":       0x00FFFFFF,
    "dark_grey":   0x00333333,
    "grey":        0x00888888,
    "dubforge_sub":    0x00120024,  # deep purple-black (sub layer)
    "dubforge_low":    0x003300AA,  # dark blue (low bass)
    "dubforge_mid":    0x00FF3300,  # aggressive orange (mid growl)
    "dubforge_high":   0x00FF6600,  # bright orange (high fizz)
    "dubforge_click":  0x00FFCC00,  # gold (click transient)
}


# --- Enums matching Ableton's internal values ----------------------------

class ClipTriggerQuantization(IntEnum):
    """Ableton clip trigger quantization values."""
    NONE = 0
    EIGHT_BARS = 1
    FOUR_BARS = 2
    TWO_BARS = 3
    ONE_BAR = 4
    HALF = 5
    HALF_TRIPLET = 6
    QUARTER = 7
    QUARTER_TRIPLET = 8
    EIGHTH = 9
    EIGHTH_TRIPLET = 10
    SIXTEENTH = 11
    SIXTEENTH_TRIPLET = 12
    THIRTYSECOND = 13


class LaunchMode(IntEnum):
    """Clip launch modes."""
    TRIGGER = 0
    GATE = 1
    TOGGLE = 2
    REPEAT = 3


class WarpMode(IntEnum):
    """Audio clip warp modes."""
    BEATS = 0
    TONES = 1
    TEXTURE = 2
    RE_PITCH = 3
    COMPLEX = 4
    REX = 5
    COMPLEX_PRO = 6


class DeviceType(IntEnum):
    """Device type identifiers."""
    UNDEFINED = 0
    INSTRUMENT = 1
    AUDIO_EFFECT = 2
    MIDI_EFFECT = 4


class RecordQuantization(IntEnum):
    """MIDI recording quantization values."""
    NONE = 0
    QUARTER = 1
    EIGHTH = 2
    EIGHTH_TRIPLET = 3
    EIGHTH_AND_TRIPLET = 4
    SIXTEENTH = 5
    SIXTEENTH_TRIPLET = 6
    SIXTEENTH_AND_TRIPLET = 7
    THIRTYSECOND = 8


# --- LOM Data Models -----------------------------------------------------

@dataclass
class MIDINote:
    """A single MIDI note in a clip."""
    pitch: int             # 0-127, 60 = C3
    start_time: float      # beats (absolute clip time)
    duration: float        # beats
    velocity: float = 100.0   # 0-127
    mute: bool = False
    probability: float = 1.0  # 0.0–1.0, Live 11+

    def to_dict(self):
        return {
            "pitch": self.pitch,
            "start_time": round(self.start_time, 4),
            "duration": round(self.duration, 4),
            "velocity": round(self.velocity, 1),
            "mute": self.mute,
            "probability": round(self.probability, 2),
        }


@dataclass
class MIDIClip:
    """A MIDI clip with note data, loop settings, and metadata."""
    name: str
    length: float              # beats
    notes: list = field(default_factory=list)  # list of MIDINote
    looping: bool = True
    loop_start: float = 0.0
    loop_end: float = 0.0      # if 0, auto-set to length
    color: int = 0x00FF3300    # dubforge orange
    launch_mode: int = LaunchMode.TRIGGER
    launch_quantization: int = 0   # 0 = Global
    time_signature_num: int = 4
    time_signature_den: int = 4

    def __post_init__(self):
        if self.loop_end == 0.0:
            self.loop_end = self.length

    def to_dict(self):
        return {
            "name": self.name,
            "length_beats": self.length,
            "looping": self.looping,
            "loop_start": self.loop_start,
            "loop_end": self.loop_end,
            "color": hex(self.color),
            "launch_mode": LaunchMode(self.launch_mode).name,
            "launch_quantization": self.launch_quantization,
            "time_signature": f"{self.time_signature_num}/{self.time_signature_den}",
            "note_count": len(self.notes),
            "notes": [n.to_dict() for n in self.notes],
        }


@dataclass
class DeviceParam:
    """A device parameter setting."""
    name: str
    value: float
    min_val: float = 0.0
    max_val: float = 1.0

    def to_dict(self):
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "range": [self.min_val, self.max_val],
        }


@dataclass
class DeviceConfig:
    """A device in a track's device chain."""
    class_name: str           # e.g. "Operator", "Compressor", "Eq8", "PluginDevice"
    display_name: str
    device_type: int = DeviceType.AUDIO_EFFECT
    is_active: bool = True
    parameters: list = field(default_factory=list)  # list of DeviceParam
    rack_chains: list = field(default_factory=list)  # for Rack devices

    def to_dict(self):
        d = {
            "class_name": self.class_name,
            "display_name": self.display_name,
            "type": DeviceType(self.device_type).name,
            "active": self.is_active,
            "parameters": [p.to_dict() for p in self.parameters],
        }
        if self.rack_chains:
            d["chains"] = self.rack_chains
        return d


@dataclass
class SendLevel:
    """Send level to a return track."""
    return_index: int
    level: float = 0.0    # 0.0–1.0


@dataclass
class TrackConfig:
    """Complete track configuration."""
    name: str
    track_type: str = "midi"   # "midi", "audio", "return", "master"
    color: int = 0x00888888
    arm: bool = False
    mute: bool = False
    solo: bool = False
    volume: float = 0.85       # 0.0–1.0 (Ableton normalized)
    pan: float = 0.0           # -1.0 (left) to 1.0 (right)
    devices: list = field(default_factory=list)   # list of DeviceConfig
    sends: list = field(default_factory=list)      # list of SendLevel
    input_routing: str = "All Ins"
    output_routing: str = "Master"
    monitoring: str = "auto"   # "in", "auto", "off"
    clips: list = field(default_factory=list)      # list of MIDIClip (for session view)

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.track_type,
            "color": hex(self.color),
            "arm": self.arm,
            "mute": self.mute,
            "solo": self.solo,
            "volume": round(self.volume, 3),
            "pan": round(self.pan, 3),
            "devices": [d.to_dict() for d in self.devices],
            "sends": [{"return": s.return_index, "level": s.level} for s in self.sends],
            "input_routing": self.input_routing,
            "output_routing": self.output_routing,
            "monitoring": self.monitoring,
            "clip_count": len(self.clips),
            "clips": [c.to_dict() for c in self.clips],
        }


@dataclass
class SceneConfig:
    """A scene (row) in Session View."""
    name: str
    index: int
    tempo: float = -1.0         # -1 = use song tempo
    tempo_enabled: bool = False
    time_sig_num: int = -1      # -1 = use song time sig
    time_sig_den: int = -1
    color: int = 0x00333333

    def to_dict(self):
        d = {
            "name": self.name,
            "index": self.index,
            "color": hex(self.color),
        }
        if self.tempo_enabled:
            d["tempo"] = self.tempo
        if self.time_sig_num > 0:
            d["time_signature"] = f"{self.time_sig_num}/{self.time_sig_den}"
        return d


@dataclass
class CuePointConfig:
    """An arrangement view locator/marker."""
    name: str
    time: float   # beats

    def to_dict(self):
        return {"name": self.name, "time_beats": round(self.time, 2)}


@dataclass
class SessionTemplate:
    """Complete Session View template for an Ableton Live set."""
    name: str
    bpm: float = 150.0
    time_signature_num: int = 4
    time_signature_den: int = 4
    root_note: int = 9           # 0=C, 9=A
    scale_name: str = "Minor"
    tracks: list = field(default_factory=list)   # list of TrackConfig
    return_tracks: list = field(default_factory=list)
    scenes: list = field(default_factory=list)   # list of SceneConfig
    clip_trigger_quant: int = ClipTriggerQuantization.ONE_BAR
    tuning_a4: float = 432.0
    dubforge_doctrine: str = "Planck x phi Fractal Basscraft v1.0"

    def to_dict(self):
        return {
            "dubforge_doctrine": self.dubforge_doctrine,
            "template_name": self.name,
            "bpm": self.bpm,
            "time_signature": f"{self.time_signature_num}/{self.time_signature_den}",
            "root_note": self.root_note,
            "scale_name": self.scale_name,
            "tuning_a4_hz": self.tuning_a4,
            "clip_trigger_quantization": ClipTriggerQuantization(self.clip_trigger_quant).name,
            "track_count": len(self.tracks),
            "return_track_count": len(self.return_tracks),
            "scene_count": len(self.scenes),
            "tracks": [t.to_dict() for t in self.tracks],
            "return_tracks": [t.to_dict() for t in self.return_tracks],
            "scenes": [s.to_dict() for s in self.scenes],
        }


@dataclass
class ArrangementTemplate:
    """Complete Arrangement View template."""
    name: str
    bpm: float = 150.0
    total_bars: int = 0
    total_beats: float = 0.0
    sections: list = field(default_factory=list)  # list of dicts
    cue_points: list = field(default_factory=list)  # list of CuePointConfig
    loop_start: float = 0.0
    loop_length: float = 0.0

    def to_dict(self):
        return {
            "template_name": self.name,
            "bpm": self.bpm,
            "total_bars": self.total_bars,
            "total_beats": self.total_beats,
            "total_duration_s": round(self.total_beats * 60.0 / self.bpm, 2),
            "loop_start_beats": self.loop_start,
            "loop_length_beats": self.loop_length,
            "section_count": len(self.sections),
            "sections": self.sections,
            "cue_points": [c.to_dict() for c in self.cue_points],
        }


# --- Utility Functions ----------------------------------------------------

def midi_to_freq(note: int, a4: float = A4_432) -> float:
    """Convert MIDI note number to frequency."""
    return a4 * (2.0 ** ((note - 69) / 12.0))


def freq_to_midi(freq: float, a4: float = A4_432) -> int:
    """Convert frequency to nearest MIDI note number."""
    return round(69 + 12.0 * math.log2(freq / a4))


def phi_velocity_curve(n_notes: int, base: float = 80.0, peak: float = 120.0) -> list:
    """Generate velocities using phi-ratio distribution."""
    vels = []
    for i in range(n_notes):
        t = i / max(n_notes - 1, 1)
        v = base + (peak - base) * (t ** PHI)
        vels.append(min(127.0, max(1.0, round(v, 1))))
    return vels


def fibonacci_duration_pattern(bars: int) -> list:
    """Generate bar-count patterns from Fibonacci numbers that sum to target bars."""
    if bars <= 0:
        return [1]
    pattern = []
    remaining = bars
    fib_idx = len(FIBONACCI) - 1
    while remaining > 0 and fib_idx >= 0:
        f = FIBONACCI[fib_idx]
        if f <= remaining:
            pattern.append(f)
            remaining -= f
        else:
            fib_idx -= 1
    if remaining > 0:
        pattern.append(remaining)
    return pattern


def phi_timing_grid(total_beats: float, subdivisions: int) -> list:
    """Create non-uniform timing grid based on phi ratios."""
    if subdivisions <= 1:
        return [0.0]
    raw = []
    for i in range(subdivisions):
        t = (i / (subdivisions - 1)) ** (1.0 / PHI)
        raw.append(t * total_beats)
    return [round(t, 4) for t in raw]


def golden_section_point(total: float) -> float:
    """Return the golden section point of a duration (the climax point)."""
    return total / PHI


# --- MIDI Clip Generators ------------------------------------------------

def generate_sub_bass_clip(root_note: int = 33, bars: int = 8, bpm: float = 150.0) -> MIDIClip:
    """
    Generate a sub-bass MIDI clip — sustained root notes with
    phi-ratio gate lengths. Root at MIDI 33 = A1 (55 Hz @ 432).
    """
    beats = bars * 4
    notes = []
    beat_pos = 0.0
    gate_ratio = 1.0 / PHI  # ~0.618 of the beat

    while beat_pos < beats:
        dur = 4.0 * gate_ratio  # whole note × phi
        notes.append(MIDINote(
            pitch=root_note,
            start_time=beat_pos,
            duration=min(dur, beats - beat_pos),
            velocity=110.0,
        ))
        beat_pos += 4.0  # advance one bar

    return MIDIClip(
        name=f"DUBFORGE_SUB_{root_note}",
        length=beats,
        notes=notes,
        color=ABLETON_COLORS["dubforge_sub"],
    )


def generate_mid_bass_clip(root_note: int = 45, bars: int = 8, bpm: float = 150.0) -> MIDIClip:
    """
    Generate a mid-bass growl pattern — Fibonacci-timed note triggers
    with phi-velocity dynamics for aggressive modulation movement.
    """
    beats = bars * 4
    notes = []
    # Fibonacci rhythm pattern within each bar: hit on 1, 1, 2, 3, 5...
    fib_hits = [0, 1, 2, 4, 7]  # sum of fib: 0, 0+1, 0+1+1, 0+1+1+2, 0+1+1+2+3
    velocities = phi_velocity_curve(len(fib_hits) * bars, base=90, peak=127)
    vel_idx = 0

    for bar in range(bars):
        bar_start = bar * 4.0
        for hit_eighth in fib_hits:
            start = bar_start + hit_eighth * 0.5  # eighth notes
            if start >= beats:
                break
            dur = 0.5 / PHI  # short staccato gate
            notes.append(MIDINote(
                pitch=root_note,
                start_time=start,
                duration=dur,
                velocity=velocities[vel_idx % len(velocities)],
            ))
            vel_idx += 1

    return MIDIClip(
        name=f"DUBFORGE_MID_{root_note}",
        length=beats,
        notes=notes,
        color=ABLETON_COLORS["dubforge_mid"],
    )


def generate_arp_clip(
    root_note: int = 57,
    scale: str = "minor",
    bars: int = 4,
    octave_range: int = 2,
) -> MIDIClip:
    """
    Generate a Fibonacci arpeggiator MIDI clip using phi-timed gates.
    Maps Fibonacci sequence indices onto scale degrees.
    """
    from engine.phi_core import FIBONACCI as FIB

    SCALES_MAP = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
    }
    intervals = SCALES_MAP.get(scale, SCALES_MAP["minor"])
    total_notes = len(intervals) * octave_range

    beats = bars * 4
    notes = []
    note_dur = (1.0 / PHI)  # ~0.618 beats per note
    step_dur = 0.5  # 8th notes
    pos = 0.0
    fib_idx = 0

    while pos < beats:
        degree = FIB[fib_idx % len(FIB)] % total_notes
        octave = degree // len(intervals)
        scale_idx = degree % len(intervals)
        pitch = root_note + intervals[scale_idx] + 12 * octave
        pitch = max(0, min(127, pitch))

        notes.append(MIDINote(
            pitch=pitch,
            start_time=pos,
            duration=note_dur,
            velocity=80.0 + 20.0 * ((fib_idx % 8) / 7.0),
        ))
        pos += step_dur
        fib_idx += 1

    return MIDIClip(
        name=f"DUBFORGE_ARP_{root_note}",
        length=beats,
        notes=notes,
        color=ABLETON_COLORS["cyan"],
    )


def generate_chord_stab_clip(
    chord_notes: list = None,
    bars: int = 8,
    rhythm_pattern: str = "fibonacci",
) -> MIDIClip:
    """
    Generate chord stab MIDI clip with Fibonacci rhythmic pattern.
    chord_notes: list of MIDI pitches forming the chord.
    """
    if chord_notes is None:
        chord_notes = [57, 60, 64]  # Am triad (A3, C4, E4)

    beats = bars * 4
    notes = []

    if rhythm_pattern == "fibonacci":
        # Fibonacci-spaced hits within each bar group
        fib_positions = [0, 1, 1, 2, 3, 5]  # cumulative: 0, 1, 2, 4, 7, 12
        cumulative = []
        total = 0
        for f in fib_positions:
            total += f
            cumulative.append(total)
        # Scale to fit within bars
        max_pos = max(cumulative) if cumulative else 1
        scaled = [c * beats / (max_pos + 2) for c in cumulative]
    elif rhythm_pattern == "phi_grid":
        scaled = phi_timing_grid(beats, 8)
    else:
        # straight quarter notes
        scaled = [i * 1.0 for i in range(int(beats))]

    for pos in scaled:
        if pos >= beats:
            break
        for pitch in chord_notes:
            notes.append(MIDINote(
                pitch=pitch,
                start_time=pos,
                duration=1.0 / PHI,
                velocity=95.0,
            ))

    return MIDIClip(
        name=f"DUBFORGE_CHORD_STAB",
        length=beats,
        notes=notes,
        color=ABLETON_COLORS["purple"],
    )


# --- Device Chain Presets (DUBFORGE-optimized) ----------------------------

def psbs_device_chain() -> list:
    """
    Phase-Separated Bass System device chain for Ableton Live.
    Mirrors DUBFORGE PSBS architecture: 5 frequency bands via Instrument Rack.

    Instrument Rack → 5 chains:
        SUB (20-89 Hz), LOW (89-144 Hz), MID (144-233 Hz),
        HIGH (233-377 Hz), CLICK (377-610 Hz)

    Each chain: [Serum 2 / Wavetable] → [EQ Eight] → [Saturator] → [Utility]
    Macro 1: PHI MORPH → Wavetable position
    Macro 2: FM DEPTH → FM amount
    Macro 3: SUB WEIGHT → Chain volume balance
    Macro 4: GRIT → Saturator drive
    """
    # Phi-ratio crossover frequencies
    crossovers = {
        "SUB":   {"low": 20, "high": 89},
        "LOW":   {"low": 89, "high": 144},
        "MID":   {"low": 144, "high": 233},
        "HIGH":  {"low": 233, "high": 377},
        "CLICK": {"low": 377, "high": 610},
    }

    chains = []
    for band_name, freqs in crossovers.items():
        chain = {
            "name": f"DUBFORGE_{band_name}",
            "color": ABLETON_COLORS.get(f"dubforge_{band_name.lower()}", 0x00888888),
            "devices": [
                DeviceConfig(
                    class_name="PluginDevice",
                    display_name=f"Serum [{band_name}]",
                    device_type=DeviceType.INSTRUMENT,
                    parameters=[
                        DeviceParam("Wavetable Position", 0.5),
                        DeviceParam("FM Amount", 0.0 if band_name == "SUB" else 0.3),
                    ],
                ).to_dict(),
                DeviceConfig(
                    class_name="Eq8",
                    display_name=f"EQ [{band_name} ISO]",
                    device_type=DeviceType.AUDIO_EFFECT,
                    parameters=[
                        DeviceParam(f"Band 1 Freq", float(freqs["low"]), 20, 20000),
                        DeviceParam(f"Band 1 Type", 6.0, 0, 8),  # High-pass
                        DeviceParam(f"Band 8 Freq", float(freqs["high"]), 20, 20000),
                        DeviceParam(f"Band 8 Type", 0.0, 0, 8),  # Low-pass
                    ],
                ).to_dict(),
                DeviceConfig(
                    class_name="Saturator",
                    display_name=f"Sat [{band_name}]",
                    device_type=DeviceType.AUDIO_EFFECT,
                    parameters=[
                        DeviceParam("Drive", 0.0 if band_name == "SUB" else 0.4 * PHI),
                        DeviceParam("Output", 0.8),
                    ],
                ).to_dict(),
                DeviceConfig(
                    class_name="StereoGain",
                    display_name=f"Util [{band_name}]",
                    device_type=DeviceType.AUDIO_EFFECT,
                    parameters=[
                        DeviceParam("Mono", 1.0 if band_name == "SUB" else 0.0),
                        DeviceParam("Gain", 0.0),
                    ],
                ).to_dict(),
            ],
        }
        chains.append(chain)

    return DeviceConfig(
        class_name="InstrumentGroupDevice",
        display_name="DUBFORGE PSBS Rack",
        device_type=DeviceType.INSTRUMENT,
        parameters=[
            DeviceParam("Macro 1 — PHI MORPH", 0.5),
            DeviceParam("Macro 2 — FM DEPTH", 0.0),
            DeviceParam("Macro 3 — SUB WEIGHT", 0.75),
            DeviceParam("Macro 4 — GRIT", 0.15),
        ],
        rack_chains=chains,
    )


def dubstep_master_chain() -> list:
    """
    Master track device chain optimized for dubstep/bass music.
    EQ Eight → Glue Compressor → OTT (Multiband) → Limiter
    """
    return [
        DeviceConfig(
            class_name="Eq8",
            display_name="Master EQ",
            device_type=DeviceType.AUDIO_EFFECT,
            parameters=[
                DeviceParam("Band 1 Freq", 30.0, 20, 20000),
                DeviceParam("Band 1 Gain", -0.5, -15, 15),
                DeviceParam("Band 1 Type", 6.0),  # High-pass at 30Hz
            ],
        ),
        DeviceConfig(
            class_name="GlueCompressor",
            display_name="Glue Comp",
            device_type=DeviceType.AUDIO_EFFECT,
            parameters=[
                DeviceParam("Threshold", -8.0, -30, 0),
                DeviceParam("Ratio", 4.0, 2, 10),
                DeviceParam("Attack", 0.1, 0.01, 30),
                DeviceParam("Release", 0.1, 0.0, 1.2),   # auto
                DeviceParam("Makeup", 3.0, 0, 15),
            ],
        ),
        DeviceConfig(
            class_name="MultibandDynamics",
            display_name="OTT",
            device_type=DeviceType.AUDIO_EFFECT,
            parameters=[
                DeviceParam("Amount", 0.3, 0, 1),     # ~30% OTT
                DeviceParam("Low Crossover", 144.0),   # phi crossover
                DeviceParam("High Crossover", 377.0),  # phi crossover
            ],
        ),
        DeviceConfig(
            class_name="Limiter",
            display_name="Ceiling",
            device_type=DeviceType.AUDIO_EFFECT,
            parameters=[
                DeviceParam("Ceiling", -0.3, -30, 0),
                DeviceParam("Gain", 0.0, 0, 16),
            ],
        ),
    ]


def return_track_reverb() -> TrackConfig:
    """Return track A: Hybrid Reverb with Fibonacci decay."""
    return TrackConfig(
        name="A — REVERB",
        track_type="return",
        color=ABLETON_COLORS["blue"],
        volume=0.7,
        devices=[
            DeviceConfig(
                class_name="Eq8",
                display_name="Pre-Verb EQ",
                device_type=DeviceType.AUDIO_EFFECT,
                parameters=[
                    DeviceParam("Band 1 Freq", 200.0),  # HP at 200
                    DeviceParam("Band 1 Type", 6.0),
                ],
            ),
            DeviceConfig(
                class_name="ProxyAudioEffectDevice",
                display_name="Hybrid Reverb",
                device_type=DeviceType.AUDIO_EFFECT,
                parameters=[
                    DeviceParam("Decay", 2.472),     # 1 + phi + (1/phi)
                    DeviceParam("Size", 0.618),      # 1/phi
                    DeviceParam("Dry/Wet", 1.0),
                ],
            ),
        ],
    )


def return_track_delay() -> TrackConfig:
    """Return track B: Echo with phi-ratio feedback timing."""
    return TrackConfig(
        name="B — DELAY",
        track_type="return",
        color=ABLETON_COLORS["cyan"],
        volume=0.6,
        devices=[
            DeviceConfig(
                class_name="Echo",
                display_name="Phi Delay",
                device_type=DeviceType.AUDIO_EFFECT,
                parameters=[
                    DeviceParam("Left Time", 3.0),     # 3/16 (Fibonacci)
                    DeviceParam("Right Time", 5.0),    # 5/16 (Fibonacci)
                    DeviceParam("Feedback", 0.382),    # 1/phi²
                    DeviceParam("Dry/Wet", 1.0),
                ],
            ),
        ],
    )


# --- Session View Template Presets ----------------------------------------

def build_dubstep_session_template(
    name: str = "DUBFORGE_DUBSTEP",
    bpm: float = 150.0,
    root_note: int = 9,    # A
    a4_hz: float = 432.0,
) -> SessionTemplate:
    """
    Build a complete dubstep Session View template following DUBFORGE doctrine.

    Track layout (mirrors PSBS architecture):
        1. SUB BASS        — Serum sub (mono, clean, 20-89 Hz)
        2. LOW BASS         — Serum low (warm, 89-144 Hz)
        3. MID BASS         — Serum growl engine (144-233 Hz)
        4. HIGH BASS        — Serum fizz/harmonics (233-377 Hz)
        5. CLICK            — Transient click layer (377-610 Hz)
        6. CHORDS/PADS      — Emotional content
        7. LEAD             — Top melody/lead
        8. ARP              — Fibonacci arpeggiator
        9. DRUMS            — Drum Rack
        10. FX/RISERS       — Transition FX

    Return tracks:
        A. REVERB           — Hybrid Reverb (phi decay)
        B. DELAY            — Echo (Fibonacci timing)

    Scenes (Fibonacci bar count arrangement):
        1. INTRO            — 8 bars
        2. BUILD 1          — 8 bars
        3. DROP 1           — 16 bars
        4. BREAK            — 8 bars
        5. BUILD 2          — 8 bars
        6. DROP 2           — 16 bars
        7. OUTRO            — 8 bars
    """

    root_midi = 33  # A1 for sub

    # --- Tracks ---
    tracks = [
        TrackConfig(
            name="1 — SUB",
            track_type="midi",
            color=ABLETON_COLORS["dubforge_sub"],
            volume=0.9,
            pan=0.0,
            devices=[],
            clips=[generate_sub_bass_clip(root_midi, bars=16, bpm=bpm)],
        ),
        TrackConfig(
            name="2 — LOW",
            track_type="midi",
            color=ABLETON_COLORS["dubforge_low"],
            volume=0.75,
            pan=0.0,
            devices=[],
            clips=[generate_mid_bass_clip(root_midi + 12, bars=16, bpm=bpm)],
        ),
        TrackConfig(
            name="3 — MID GROWL",
            track_type="midi",
            color=ABLETON_COLORS["dubforge_mid"],
            volume=0.7,
            pan=0.0,
            devices=[],
            clips=[generate_mid_bass_clip(root_midi + 24, bars=16, bpm=bpm)],
        ),
        TrackConfig(
            name="4 — HIGH",
            track_type="midi",
            color=ABLETON_COLORS["dubforge_high"],
            volume=0.6,
            pan=0.0,
            devices=[],
            clips=[generate_mid_bass_clip(root_midi + 36, bars=8, bpm=bpm)],
        ),
        TrackConfig(
            name="5 — CLICK",
            track_type="midi",
            color=ABLETON_COLORS["dubforge_click"],
            volume=0.5,
            pan=0.0,
            devices=[],
            clips=[],
        ),
        TrackConfig(
            name="6 — CHORDS",
            track_type="midi",
            color=ABLETON_COLORS["purple"],
            volume=0.65,
            pan=0.0,
            devices=[],
            clips=[generate_chord_stab_clip([57, 60, 64], bars=8)],  # Am
        ),
        TrackConfig(
            name="7 — LEAD",
            track_type="midi",
            color=ABLETON_COLORS["magenta"],
            volume=0.6,
            pan=0.0,
            devices=[],
            clips=[],
        ),
        TrackConfig(
            name="8 — ARP",
            track_type="midi",
            color=ABLETON_COLORS["cyan"],
            volume=0.55,
            pan=0.0,
            devices=[],
            clips=[generate_arp_clip(root_note=57, scale="minor", bars=4)],
        ),
        TrackConfig(
            name="9 — DRUMS",
            track_type="midi",
            color=ABLETON_COLORS["orange"],
            volume=0.85,
            pan=0.0,
            devices=[],
            clips=[],
        ),
        TrackConfig(
            name="10 — FX/RISERS",
            track_type="audio",
            color=ABLETON_COLORS["yellow"],
            volume=0.5,
            pan=0.0,
            devices=[],
            clips=[],
        ),
    ]

    # --- Return Tracks ---
    returns = [
        return_track_reverb(),
        return_track_delay(),
    ]

    # --- Scenes (Fibonacci-aligned bar counts) ---
    scene_layout = [
        ("INTRO", 8),
        ("BUILD 1", 8),
        ("DROP 1", 16),
        ("BREAK", 8),
        ("BUILD 2", 8),
        ("DROP 2", 16),
        ("OUTRO", 8),
    ]

    scenes = []
    for i, (sname, bars) in enumerate(scene_layout):
        scenes.append(SceneConfig(
            name=sname,
            index=i,
            color=ABLETON_COLORS["dark_grey"] if "DROP" not in sname else ABLETON_COLORS["red"],
        ))

    template = SessionTemplate(
        name=name,
        bpm=bpm,
        time_signature_num=4,
        time_signature_den=4,
        root_note=root_note,
        scale_name="Minor",
        tracks=tracks,
        return_tracks=returns,
        scenes=scenes,
        clip_trigger_quant=ClipTriggerQuantization.ONE_BAR,
        tuning_a4=a4_hz,
    )

    return template


def build_arrangement_template(
    name: str = "DUBFORGE_WEAPON",
    bpm: float = 150.0,
) -> ArrangementTemplate:
    """
    Build a complete Arrangement View template using DUBFORGE doctrine.
    Section lengths follow Fibonacci bar counts.
    Golden section point marks the main drop climax.

    Structure:
        INTRO       → 8 bars
        BUILD 1     → 8 bars
        DROP 1      → 16 bars
        BREAK       → 8 bars
        BUILD 2     → 13 bars (Fibonacci!)
        DROP 2      → 21 bars (Fibonacci!)
        BRIDGE      → 5 bars  (Fibonacci!)
        FINAL DROP  → 13 bars (Fibonacci!)
        OUTRO       → 8 bars
    """
    sections_spec = [
        {"name": "INTRO",       "bars": 8,  "energy": [0.1, 0.3]},
        {"name": "BUILD 1",     "bars": 8,  "energy": [0.3, 0.7]},
        {"name": "DROP 1",      "bars": 16, "energy": [1.0, 0.8]},
        {"name": "BREAK",       "bars": 8,  "energy": [0.3, 0.2]},
        {"name": "BUILD 2",     "bars": 13, "energy": [0.2, 0.85]},
        {"name": "DROP 2",      "bars": 21, "energy": [1.0, 0.9]},
        {"name": "BRIDGE",      "bars": 5,  "energy": [0.4, 0.5]},
        {"name": "FINAL DROP",  "bars": 13, "energy": [1.0, 1.0]},
        {"name": "OUTRO",       "bars": 8,  "energy": [0.5, 0.0]},
    ]

    total_bars = sum(s["bars"] for s in sections_spec)
    total_beats = total_bars * 4.0

    # Build sections and cue points
    sections = []
    cue_points = []
    beat_pos = 0.0

    for s in sections_spec:
        section_beats = s["bars"] * 4
        cue_points.append(CuePointConfig(name=s["name"], time=beat_pos))
        sections.append({
            "name": s["name"],
            "bars": s["bars"],
            "start_beat": round(beat_pos, 2),
            "end_beat": round(beat_pos + section_beats, 2),
            "energy_start": s["energy"][0],
            "energy_end": s["energy"][1],
            "is_fibonacci_bars": s["bars"] in FIBONACCI,
        })
        beat_pos += section_beats

    # Golden section point
    golden_beat = golden_section_point(total_beats)
    cue_points.append(CuePointConfig(name="★ GOLDEN SECTION", time=golden_beat))

    return ArrangementTemplate(
        name=name,
        bpm=bpm,
        total_bars=total_bars,
        total_beats=total_beats,
        sections=sections,
        cue_points=cue_points,
        loop_start=0.0,
        loop_length=total_beats,
    )


# --- Max for Live / Python Remote Script Generator -----------------------

def generate_m4l_control_script(template: SessionTemplate) -> str:
    """
    Generate a Max for Live compatible Python control script
    that can set up tracks, devices, and clips in a running Live set.

    This outputs a Python script that uses the Live API (import Live)
    to programmatically construct the DUBFORGE session.
    """
    lines = [
        '"""',
        f'DUBFORGE — Max for Live Control Script',
        f'Template: {template.name}',
        f'Doctrine: {template.dubforge_doctrine}',
        f'',
        f'Usage: Load this as a Max for Live device script.',
        f'       It will configure the Live set according to DUBFORGE specs.',
        '"""',
        '',
        'import Live',
        '',
        'PHI = 1.6180339887498948482',
        '',
        '',
        'def create_dubforge_set():',
        '    """Configure the current Live set for DUBFORGE."""',
        '    app = Live.Application.get_application()',
        '    song = app.get_document()',
        '',
        f'    # Set tempo',
        f'    song.tempo = {template.bpm}',
        '',
        f'    # Set time signature',
        f'    song.signature_numerator = {template.time_signature_num}',
        f'    song.signature_denominator = {template.time_signature_den}',
        '',
        f'    # Set scale (root_note: {template.root_note}, 0=C ... 11=B)',
        f'    song.root_note = {template.root_note}',
        f'    song.scale_name = "{template.scale_name}"',
        f'    song.scale_mode = True',
        '',
        f'    # Set clip trigger quantization',
        f'    song.clip_trigger_quantization = {template.clip_trigger_quant}',
        '',
        '    # --- Create Tracks ---',
    ]

    for i, track in enumerate(template.tracks):
        ttype = "midi" if track.track_type == "midi" else "audio"
        lines.append(f'')
        lines.append(f'    # Track {i + 1}: {track.name}')
        if ttype == "midi":
            lines.append(f'    song.create_midi_track({i})')
        else:
            lines.append(f'    song.create_audio_track({i})')
        lines.append(f'    t = song.tracks[{i}]')
        lines.append(f'    t.name = "{track.name}"')
        lines.append(f'    t.color = {hex(track.color)}')

    lines.extend([
        '',
        '    # --- Create Return Tracks ---',
    ])

    for i, rt in enumerate(template.return_tracks):
        lines.append(f'    song.create_return_track()  # {rt.name}')
        lines.append(f'    song.return_tracks[{i}].name = "{rt.name}"')
        lines.append(f'    song.return_tracks[{i}].color = {hex(rt.color)}')

    lines.extend([
        '',
        '    # --- Create Scenes ---',
    ])

    for sc in template.scenes:
        lines.append(f'    song.create_scene({sc.index})  # {sc.name}')
        lines.append(f'    song.scenes[{sc.index}].name = "{sc.name}"')
        lines.append(f'    song.scenes[{sc.index}].color = {hex(sc.color)}')

    lines.extend([
        '',
        '    # --- Insert MIDI clips ---',
    ])

    for i, track in enumerate(template.tracks):
        for j, clip in enumerate(track.clips):
            lines.append(f'')
            lines.append(f'    # Clip: {clip.name} on track {i}, slot {j}')
            lines.append(f'    cs = song.tracks[{i}].clip_slots[{j}]')
            lines.append(f'    cs.create_clip({clip.length})')
            lines.append(f'    c = cs.clip')
            lines.append(f'    c.name = "{clip.name}"')
            lines.append(f'    c.color = {hex(clip.color)}')
            lines.append(f'    c.looping = {clip.looping}')
            if clip.notes:
                lines.append(f'    c.add_new_notes({{')
                lines.append(f'        "notes": [')
                for note in clip.notes:
                    lines.append(
                        f'            {{"pitch": {note.pitch}, '
                        f'"start_time": {note.start_time:.4f}, '
                        f'"duration": {note.duration:.4f}, '
                        f'"velocity": {note.velocity:.1f}}},')
                lines.append(f'        ]')
                lines.append(f'    }})')

    lines.extend([
        '',
        '',
        '# Auto-run when loaded',
        'create_dubforge_set()',
        '',
    ])

    return '\n'.join(lines)


# --- LOM Reference Database ----------------------------------------------

LOM_REFERENCE = {
    "hierarchy": {
        "Application": {
            "path": "live_app",
            "children": ["view", "control_surfaces"],
            "key_properties": ["average_process_usage", "peak_process_usage"],
            "key_functions": ["get_document", "get_major_version"],
        },
        "Song": {
            "path": "live_set",
            "children": ["tracks", "return_tracks", "master_track", "scenes",
                          "cue_points", "groove_pool", "tuning_system", "view"],
            "key_properties": [
                "tempo", "signature_numerator", "signature_denominator",
                "is_playing", "current_song_time", "loop", "loop_start", "loop_length",
                "root_note", "scale_name", "scale_mode", "scale_intervals",
                "record_mode", "metronome", "is_ableton_link_enabled",
                "groove_amount", "swing_amount", "song_length",
            ],
            "key_functions": [
                "start_playing", "stop_playing", "continue_playing",
                "create_midi_track", "create_audio_track", "create_return_track",
                "create_scene", "delete_track", "delete_scene",
                "capture_midi", "undo", "redo",
                "stop_all_clips", "trigger_session_record",
            ],
        },
        "Track": {
            "path": "live_set tracks N",
            "children": ["clip_slots", "arrangement_clips", "devices",
                          "mixer_device", "group_track", "view"],
            "key_properties": [
                "name", "color", "arm", "mute", "solo",
                "has_midi_input", "has_audio_output",
                "input_routing_type", "output_routing_type",
                "is_foldable", "is_grouped", "is_frozen",
            ],
            "key_functions": [
                "stop_all_clips", "duplicate_clip_slot",
                "create_audio_clip", "delete_device",
            ],
        },
        "ClipSlot": {
            "path": "live_set tracks N clip_slots M",
            "children": ["clip"],
            "key_properties": [
                "has_clip", "is_playing", "is_recording", "is_triggered",
            ],
            "key_functions": [
                "fire", "stop", "create_clip", "create_audio_clip",
                "delete_clip", "duplicate_clip_to",
            ],
        },
        "Clip": {
            "path": "live_set tracks N clip_slots M clip",
            "children": ["view"],
            "key_properties": [
                "name", "color", "length", "looping",
                "loop_start", "loop_end", "start_marker", "end_marker",
                "is_midi_clip", "is_audio_clip", "is_playing",
                "launch_mode", "launch_quantization",
                "warp_mode", "warping", "pitch_coarse", "pitch_fine",
                "gain", "playing_position",
            ],
            "key_functions": [
                "fire", "stop",
                "add_new_notes", "get_notes_extended", "get_all_notes_extended",
                "apply_note_modifications", "remove_notes_extended",
                "select_all_notes", "deselect_all_notes",
                "duplicate_loop", "duplicate_region", "crop",
                "quantize", "quantize_pitch",
                "clear_all_envelopes", "clear_envelope",
            ],
        },
        "Device": {
            "path": "live_set tracks N devices M",
            "children": ["parameters", "view"],
            "key_properties": [
                "name", "class_name", "class_display_name",
                "type", "is_active", "can_have_chains",
            ],
            "key_functions": ["store_chosen_bank"],
        },
        "DeviceParameter": {
            "path": "live_set tracks N devices M parameters L",
            "key_properties": [
                "name", "value", "min", "max",
                "is_quantized", "is_enabled", "automation_state",
            ],
            "key_functions": ["re_enable_automation", "str_for_value"],
        },
        "Scene": {
            "path": "live_set scenes N",
            "children": ["clip_slots"],
            "key_properties": [
                "name", "color", "is_empty", "is_triggered",
                "tempo", "tempo_enabled",
                "time_signature_numerator", "time_signature_denominator",
            ],
            "key_functions": ["fire", "fire_as_selected"],
        },
        "RackDevice": {
            "inherits": "Device",
            "children": ["chains", "drum_pads", "return_chains", "chain_selector"],
            "key_properties": [
                "can_show_chains", "has_drum_pads", "has_macro_mappings",
                "visible_macro_count", "variation_count",
            ],
            "key_functions": [
                "copy_pad", "add_macro", "remove_macro",
                "randomize_macros", "store_variation", "recall_selected_variation",
            ],
        },
        "MixerDevice": {
            "path": "live_set tracks N mixer_device",
            "children": ["volume", "panning", "sends", "crossfader", "cue_volume"],
            "key_properties": ["crossfade_assign", "panning_mode"],
        },
        "WavetableDevice": {
            "inherits": "Device",
            "key_properties": [
                "filter_routing", "mono_poly", "poly_voices",
                "oscillator_1_effect_mode", "oscillator_2_effect_mode",
                "oscillator_1_wavetable_category", "oscillator_1_wavetable_index",
                "unison_mode", "unison_voice_count",
            ],
            "key_functions": [
                "add_parameter_to_modulation_matrix",
                "set_modulation_value", "get_modulation_value",
            ],
        },
        "TuningSystem": {
            "path": "live_set tuning_system",
            "key_properties": [
                "name", "note_tunings", "reference_pitch",
                "pseudo_octave_in_cents", "lowest_note", "highest_note",
            ],
        },
    },
    "native_devices": {
        "instruments": [
            "Wavetable", "Drift", "Meld", "Simpler", "Sampler",
            "Operator", "Analog", "Collision", "Electric", "Tension",
        ],
        "audio_effects": [
            "Eq8", "Compressor", "GlueCompressor", "Limiter", "Gate",
            "MultibandDynamics", "Saturator", "Overdrive", "Amp",
            "Corpus", "Erosion", "FrequencyShifter", "Shifter",
            "GrainDelay", "Echo", "Delay", "PingPongDelay",
            "Chorus", "Flanger", "Phaser", "Chorus-Ensemble", "Phaser-Flanger",
            "Reverb", "HybridReverb", "Convolution",
            "AutoFilter", "AutoPan", "Redux", "Vinyl",
            "SpectralResonator", "SpectralTime",
            "Roar", "Utility", "Tuner", "Spectrum",
        ],
        "midi_effects": [
            "Arpeggiator", "Chord", "NoteLength", "Pitch",
            "Random", "Scale", "Velocity",
        ],
        "rack_types": [
            "InstrumentGroupDevice",     # Instrument Rack
            "AudioEffectGroupDevice",    # Audio Effect Rack
            "DrumGroupDevice",           # Drum Rack
            "MidiEffectGroupDevice",     # MIDI Effect Rack
        ],
    },
    "warp_modes": {
        0: "Beats — preserves transients (drums, percussive material)",
        1: "Tones — preserves pitch (monophonic melodic material)",
        2: "Texture — granular (pads, ambience, noise)",
        3: "Re-Pitch — changes pitch with speed (vinyl/tape style)",
        4: "Complex — phase vocoder (full mixes, complex material)",
        5: "REX — slice-based (loop format)",
        6: "Complex Pro — highest quality time-stretch",
    },
    "launch_modes": {
        0: "Trigger — plays on press, ignores release",
        1: "Gate — plays while held, stops on release",
        2: "Toggle — press to start, press again to stop",
        3: "Repeat — retriggers at launch quantization rate",
    },
    "clip_quantizations": {
        0: "None",    1: "8 Bars",  2: "4 Bars",  3: "2 Bars",
        4: "1 Bar",   5: "1/2",     6: "1/2T",    7: "1/4",
        8: "1/4T",    9: "1/8",    10: "1/8T",   11: "1/16",
       12: "1/16T",  13: "1/32",
    },
}


# --- Template Presets (all following DUBFORGE Doctrine) -------------------

SESSION_PRESETS = {
    "DUBSTEP_WEAPON": {
        "description": "Aggressive weapon-style dubstep template. Am, 150 BPM, 432 Hz.",
        "bpm": 150.0,
        "root_note": 9,
        "a4_hz": 432.0,
    },
    "EMOTIVE_MELODIC": {
        "description": "Melodic/emotive dubstep template. Dm, 140 BPM, 432 Hz.",
        "bpm": 140.0,
        "root_note": 2,  # D
        "a4_hz": 432.0,
    },
    "HYBRID_FRACTAL": {
        "description": "Hybrid bass template — phi-timed sections. Em, 145 BPM.",
        "bpm": 145.0,
        "root_note": 4,  # E
        "a4_hz": 432.0,
    },
    "TESSERACT": {
        "description": "Cinematic/experimental template. Fm, 155 BPM.",
        "bpm": 155.0,
        "root_note": 5,  # F
        "a4_hz": 432.0,
    },
    "FIBONACCI_LIVE": {
        "description": "Live performance template with Fibonacci scene progression.",
        "bpm": 150.0,
        "root_note": 9,
        "a4_hz": 432.0,
    },
}


# --- Export Function ------------------------------------------------------

def export_template(template, output_dir: Path, prefix: str = ""):
    """Export a template to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    name_safe = template.name.lower().replace(" ", "_")
    filepath = output_dir / f"{prefix}{name_safe}.json"
    with open(filepath, "w") as f:
        json.dump(template.to_dict(), f, indent=2, default=str)
    print(f"    ✓ {filepath.name}")
    return filepath


# --- Main -----------------------------------------------------------------

def main():
    """Generate all Ableton Live templates and export them."""
    out_dir = Path(__file__).parent.parent / "output" / "ableton"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("  DUBFORGE Ableton Live Engine")
    print("  Doctrine: Planck x phi Fractal Basscraft v1.0")
    print()

    # --- Session Templates ---
    print("  Session View Templates:")
    for preset_name, cfg in SESSION_PRESETS.items():
        template = build_dubstep_session_template(
            name=f"DUBFORGE_{preset_name}",
            bpm=cfg["bpm"],
            root_note=cfg["root_note"],
            a4_hz=cfg["a4_hz"],
        )
        export_template(template, out_dir, prefix="session_")

    # --- Arrangement Template ---
    print()
    print("  Arrangement View Templates:")
    arr_weapon = build_arrangement_template("DUBFORGE_WEAPON_ARR", bpm=150.0)
    export_template(arr_weapon, out_dir, prefix="arrangement_")

    arr_emotive = build_arrangement_template("DUBFORGE_EMOTIVE_ARR", bpm=140.0)
    export_template(arr_emotive, out_dir, prefix="arrangement_")

    # --- Device Chain Presets ---
    print()
    print("  Device Chain Presets:")
    psbs = psbs_device_chain()
    psbs_path = out_dir / "device_chain_psbs_rack.json"
    with open(psbs_path, "w") as f:
        json.dump(psbs.to_dict(), f, indent=2, default=str)
    print(f"    ✓ {psbs_path.name}")

    master = dubstep_master_chain()
    master_path = out_dir / "device_chain_master.json"
    with open(master_path, "w") as f:
        json.dump([d.to_dict() for d in master], f, indent=2, default=str)
    print(f"    ✓ {master_path.name}")

    # --- Max for Live Script ---
    print()
    print("  Max for Live Control Script:")
    weapon_template = build_dubstep_session_template(
        name="DUBFORGE_WEAPON",
        bpm=150.0,
        root_note=9,
        a4_hz=432.0,
    )
    m4l_script = generate_m4l_control_script(weapon_template)
    m4l_path = out_dir / "dubforge_m4l_setup.py"
    with open(m4l_path, "w") as f:
        f.write(m4l_script)
    print(f"    ✓ {m4l_path.name}")

    # --- LOM Reference Export ---
    print()
    print("  LOM Reference Database:")
    lom_path = out_dir / "lom_reference.json"
    with open(lom_path, "w") as f:
        json.dump(LOM_REFERENCE, f, indent=2)
    print(f"    ✓ {lom_path.name}")

    # --- Summary ---
    print()
    total_files = len(SESSION_PRESETS) + 2 + 2 + 1 + 1  # sessions + arrangements + chains + m4l + lom
    print(f"  Total outputs: {total_files} files")
    print(f"  Output dir:    {out_dir}")
    print()

    # Print architecture summary
    print("  Ableton Live Architecture Knowledge:")
    print(f"    LOM Classes:       {len(LOM_REFERENCE['hierarchy'])} documented")
    print(f"    Native Instruments: {len(LOM_REFERENCE['native_devices']['instruments'])}")
    print(f"    Audio Effects:     {len(LOM_REFERENCE['native_devices']['audio_effects'])}")
    print(f"    MIDI Effects:      {len(LOM_REFERENCE['native_devices']['midi_effects'])}")
    print(f"    Warp Modes:        {len(LOM_REFERENCE['warp_modes'])}")
    print(f"    Launch Modes:      {len(LOM_REFERENCE['launch_modes'])}")
    print(f"    Rack Types:        {len(LOM_REFERENCE['native_devices']['rack_types'])}")


if __name__ == "__main__":
    main()
