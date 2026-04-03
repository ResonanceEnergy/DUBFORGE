"""
DUBFORGE Engine — Ableton Live Set (.als) Generator  (V7 — Schema-Compliant)

Generates valid Ableton Live 12 set files (.als) that match the XML schema
used by Ableton's own factory templates.  Reverse-engineered from
C:\\ProgramData\\Ableton\\Live 12 Standard\\Resources\\Builtin\\Templates\\DefaultLiveSet.als

An .als file is a gzip-compressed XML document.

Outputs:
    output/ableton/*.als — Ableton Live set files
"""

from __future__ import annotations

import gzip
import json
import math as _math
import os
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engine.config_loader import PHI
from engine.log import get_logger
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)

_log = get_logger("dubforge.als_generator")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

ALS_CREATOR = "Ableton Live 12.1d1"
ALS_SCHEMA_VERSION = "12.0_12117"  # Ableton Live 12 schema (MAJOR.MINOR_BUILD)
DEFAULT_BPM = 150.0
DEFAULT_TIME_SIG_NUM = 4
DEFAULT_TIME_SIG_DEN = 4

# Search paths for Ableton's factory default template (tried in order)
_DEFAULT_TEMPLATE_PATHS = [
    Path(r"C:\ProgramData\Ableton\Live 12 Suite\Resources\Builtin\Templates\DefaultLiveSet.als"),
    Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"),
    Path(r"C:\ProgramData\Ableton\Live 12 Lite\Resources\Builtin\Templates\DefaultLiveSet.als"),
    Path(r"C:\ProgramData\Ableton\Live 12 Intro\Resources\Builtin\Templates\DefaultLiveSet.als"),
]

# Ableton volume fader range (linear amplitude)
_VOL_MIN = 0.0003162277571   # ≈ -70 dB
_VOL_MAX = 1.99526238        # ≈ +6 dB


def _db_to_linear(db: float) -> float:
    """Convert dB to Ableton's linear fader value.  0 dB -> 1.0."""
    if db <= -70.0:
        return _VOL_MIN
    return max(_VOL_MIN, min(_VOL_MAX, 10.0 ** (db / 20.0)))


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL  (unchanged public API)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ALSTrack:
    """Represents a track in an Ableton Live set."""
    name: str
    track_type: str = "midi"        # "midi" | "audio" | "return"
    color: int = 0                  # Track color index (0-69)
    volume_db: float = 0.0
    pan: float = 0.0                # -1.0 to 1.0
    mute: bool = False
    solo: bool = False
    armed: bool = False
    midi_channel: int = 0           # 0-15
    device_names: list[str] = field(default_factory=list)
    preset_states: dict[str, bytes] = field(default_factory=dict)  # device_name -> raw state bytes
    clip_names: list[str] = field(default_factory=list)
    clip_paths: list[str] = field(default_factory=list)
    send_levels: list[float] = field(default_factory=list)
    arrangement_clips: list = field(default_factory=list)   # list[ALSClipInfo]
    automations: list = field(default_factory=list)         # list[ALSAutomation]
    midi_clips: list = field(default_factory=list)          # list[ALSMidiClip]


@dataclass
class ALSScene:
    """Represents a scene (row of clips)."""
    name: str
    tempo: float = DEFAULT_BPM
    time_sig: tuple[int, int] = (4, 4)


@dataclass
class ALSWarpMarker:
    """Warp marker for audio time-stretching."""
    sec_time: float
    beat_time: float


@dataclass
class ALSClipInfo:
    """Extended clip placement info for arrangement view."""
    path: str
    start_beat: float = 0.0
    length_beats: float = 0.0
    warp_mode: int = 0
    warp_markers: list[ALSWarpMarker] = field(default_factory=list)
    loop: bool = False
    loop_start: float = 0.0
    loop_end: float = 0.0
    gain: float = 1.0
    name: str = ""
    sample_rate: int = 0
    duration_frames: int = 0
    file_size: int = 0


@dataclass
class ALSAutomationPoint:
    """A single automation breakpoint."""
    time: float
    value: float
    curve: float = 0.0


@dataclass
class ALSAutomation:
    """Automation envelope for a track parameter."""
    parameter_name: str
    points: list[ALSAutomationPoint] = field(default_factory=list)

    def to_compressed(self) -> CompressedAudioBuffer:
        """TQ-compress automation point values."""
        values = [p.value for p in self.points]
        if not values:
            values = [0.0]
        tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(values)))
        return compress_audio_buffer(
            values, f"als_auto_{self.parameter_name}", tq_cfg,
            sample_rate=1, label=self.parameter_name,
        )


@dataclass
class ALSCuePoint:
    """Arrangement view cue point / locator."""
    name: str
    time: float


@dataclass
class ALSMidiNote:
    """A single MIDI note event."""
    pitch: int              # MIDI pitch 0-127
    time: float             # Start time in beats (relative to clip start)
    duration: float         # Duration in beats
    velocity: int = 100     # 0-127


@dataclass
class ALSMidiClip:
    """A MIDI clip for arrangement view."""
    name: str
    start_beat: float           # Position in arrangement (beats)
    length_beats: float         # Clip length in beats
    notes: list[ALSMidiNote] = field(default_factory=list)


@dataclass
class ALSProject:
    """Complete Ableton Live set project."""
    name: str
    bpm: float = DEFAULT_BPM
    time_sig_num: int = DEFAULT_TIME_SIG_NUM
    time_sig_den: int = DEFAULT_TIME_SIG_DEN
    tracks: list[ALSTrack] = field(default_factory=list)
    scenes: list[ALSScene] = field(default_factory=list)
    master_volume_db: float = 0.0
    notes: str = ""
    cue_points: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATION SHAPE GENERATORS  (insights 102, 116-121)
# ═══════════════════════════════════════════════════════════════════════════

def make_sine_automation(param: str, start_beat: float, end_beat: float,
                         min_val: float = 0.0, max_val: float = 1.0,
                         cycles: int = 1, resolution: int = 32) -> ALSAutomation:
    """Sine-shaped automation (insight 116 -- tremolo/LFO)."""
    pts = []
    for i in range(resolution + 1):
        t = start_beat + (end_beat - start_beat) * i / resolution
        phase = 2.0 * _math.pi * cycles * i / resolution
        v = min_val + (max_val - min_val) * (0.5 + 0.5 * _math.sin(phase))
        pts.append(ALSAutomationPoint(time=t, value=v))
    return ALSAutomation(parameter_name=param, points=pts)


def make_sawtooth_automation(param: str, start_beat: float, end_beat: float,
                             min_val: float = 0.0, max_val: float = 1.0,
                             cycles: int = 1, resolution: int = 32) -> ALSAutomation:
    """Sawtooth automation (insight 117 -- filter sweeps)."""
    pts = []
    beats_per_cycle = (end_beat - start_beat) / cycles
    pts_per_cycle = max(resolution // cycles, 2)
    for c in range(cycles):
        cycle_start = start_beat + c * beats_per_cycle
        for i in range(pts_per_cycle):
            frac = i / pts_per_cycle
            t = cycle_start + beats_per_cycle * frac
            v = min_val + (max_val - min_val) * frac
            pts.append(ALSAutomationPoint(time=t, value=v))
        # Reset at end of last cycle only (intermediate resets are at
        # next cycle_start with value=min_val already)
        if c == cycles - 1:
            pts.append(ALSAutomationPoint(time=cycle_start + beats_per_cycle,
                                          value=min_val))
    return ALSAutomation(parameter_name=param, points=pts)


def make_ramp_automation(param: str, start_beat: float, end_beat: float,
                         start_val: float = 0.0, end_val: float = 1.0,
                         curve: float = 0.0) -> ALSAutomation:
    """Linear or curved ramp (insight 123)."""
    return ALSAutomation(
        parameter_name=param,
        points=[
            ALSAutomationPoint(time=start_beat, value=start_val, curve=curve),
            ALSAutomationPoint(time=end_beat, value=end_val),
        ],
    )


def make_lp_sweep_automation(param: str, start_beat: float, end_beat: float,
                             closed_val: float = 0.08, open_val: float = 1.0,
                             curve: float = 0.4) -> ALSAutomation:
    """LP filter build sweep (insight 21)."""
    return make_ramp_automation(param, start_beat, end_beat,
                                start_val=closed_val, end_val=open_val,
                                curve=curve)


def make_section_send_automation(param: str, sections: list,
                                 total_bars: int) -> ALSAutomation:
    """Dynamic send automation per section (insight 129)."""
    pts = []
    for bar_start, bar_len, send_val in sections:
        beat_start = bar_start * 4.0
        beat_end = (bar_start + bar_len) * 4.0
        pts.append(ALSAutomationPoint(time=beat_start, value=send_val))
        pts.append(ALSAutomationPoint(time=beat_end - 0.01, value=send_val))
    return ALSAutomation(parameter_name=param, points=pts)


# ═══════════════════════════════════════════════════════════════════════════
# POINTEE-ID COUNTER  (insight 110, 134)
# ═══════════════════════════════════════════════════════════════════════════

class _IdCounter:
    """Manages unique incremental IDs for AutomationTarget / ModulationTarget /
    Pointee elements across the entire LiveSet."""

    def __init__(self, start: int = 10000):
        self._next = start

    def next(self) -> int:
        val = self._next
        self._next += 1
        return val

    @property
    def value(self) -> int:
        return self._next


# ═══════════════════════════════════════════════════════════════════════════
# XML HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _v(parent: ET.Element, tag: str, value) -> ET.Element:
    """Create <Tag Value="..."/> (Ableton's ubiquitous pattern)."""
    return ET.SubElement(parent, tag, Value=str(value))


def _automation_target(parent: ET.Element, tag: str, ids: _IdCounter) -> ET.Element:
    """<AutomationTarget Id="N"><LockEnvelope Value="0"/></AutomationTarget>"""
    at = ET.SubElement(parent, tag, Id=str(ids.next()))
    _v(at, "LockEnvelope", "0")
    return at


_modulation_target = _automation_target


def _on_switch(parent: ET.Element, ids: _IdCounter, value: str = "true") -> None:
    """Standard On element with AutomationTarget + MidiCCOnOffThresholds."""
    on = ET.SubElement(parent, "On")
    _v(on, "LomId", "0")
    _v(on, "Manual", value)
    _automation_target(on, "AutomationTarget", ids)
    thresholds = ET.SubElement(on, "MidiCCOnOffThresholds")
    _v(thresholds, "Min", "64")
    _v(thresholds, "Max", "127")


def _device_header(parent: ET.Element, ids: _IdCounter) -> None:
    """Common device header: LomId, IsExpanded, On, Pointee, etc."""
    _v(parent, "LomId", "0")
    _v(parent, "LomIdView", "0")
    _v(parent, "IsExpanded", "true")
    _v(parent, "BreakoutIsExpanded", "false")
    _on_switch(parent, ids)
    _v(parent, "ModulationSourceCount", "0")
    ET.SubElement(parent, "ParametersListWrapper", LomId="0")
    ET.SubElement(parent, "Pointee", Id=str(ids.next()))
    _v(parent, "LastSelectedTimeableIndex", "0")
    _v(parent, "LastSelectedClipEnvelopeIndex", "0")
    lpr = ET.SubElement(parent, "LastPresetRef")
    ET.SubElement(lpr, "Value")
    ET.SubElement(parent, "LockedScripts")
    _v(parent, "IsFolded", "false")
    _v(parent, "ShouldShowPresetName", "false")
    _v(parent, "UserName", "")
    _v(parent, "Annotation", "")
    sc = ET.SubElement(parent, "SourceContext")
    ET.SubElement(sc, "Value")


def _mpe_settings(parent: ET.Element) -> None:
    """Standard MpeSettings sub-element for routing."""
    mpe = ET.SubElement(parent, "MpeSettings")
    _v(mpe, "ZoneType", "0")
    _v(mpe, "FirstNoteChannel", "1")
    _v(mpe, "LastNoteChannel", "15")


def _routing(parent: ET.Element, tag: str, target: str,
             upper: str, lower: str = "") -> None:
    """Build a routing element (AudioInputRouting, MidiOutputRouting, etc.)."""
    r = ET.SubElement(parent, tag)
    _v(r, "Target", target)
    _v(r, "UpperDisplayString", upper)
    _v(r, "LowerDisplayString", lower)
    _mpe_settings(r)


def _fmt_float(v) -> str:
    """Format a float for ALS XML: drop trailing .0 for integer values."""
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


def _float_param(parent: ET.Element, tag: str, value, ids: _IdCounter,
                 min_val=None, max_val=None) -> ET.Element:
    """Standard float parameter with AutomationTarget + ModulationTarget."""
    elem = ET.SubElement(parent, tag)
    _v(elem, "LomId", "0")
    _v(elem, "Manual", _fmt_float(value))
    if min_val is not None and max_val is not None:
        mcr = ET.SubElement(elem, "MidiControllerRange")
        _v(mcr, "Min", str(min_val))
        _v(mcr, "Max", str(max_val))
    _automation_target(elem, "AutomationTarget", ids)
    _automation_target(elem, "ModulationTarget", ids)
    return elem


def _bool_param(parent: ET.Element, tag: str, value: str,
                ids: _IdCounter) -> ET.Element:
    """Boolean parameter with AutomationTarget + MidiCC thresholds."""
    elem = ET.SubElement(parent, tag)
    _v(elem, "LomId", "0")
    _v(elem, "Manual", value)
    _automation_target(elem, "AutomationTarget", ids)
    thresholds = ET.SubElement(elem, "MidiCCOnOffThresholds")
    _v(thresholds, "Min", "64")
    _v(thresholds, "Max", "127")
    return elem


# ═══════════════════════════════════════════════════════════════════════════
# MIXER BUILDER  (matches real Ableton mixer structure)
# ═══════════════════════════════════════════════════════════════════════════

def _build_mixer(dc: ET.Element, track: ALSTrack, ids: _IdCounter,
                 num_returns: int) -> None:
    """Build a complete Mixer element inside a DeviceChain."""
    mixer = ET.SubElement(dc, "Mixer")
    _device_header(mixer, ids)

    # Sends
    sends = ET.SubElement(mixer, "Sends")
    for i in range(num_returns):
        holder = ET.SubElement(sends, "TrackSendHolder", Id=str(i))
        send = ET.SubElement(holder, "Send")
        send_val = track.send_levels[i] if i < len(track.send_levels) else _VOL_MIN
        _v(send, "LomId", "0")
        _v(send, "Manual", str(round(send_val, 10)))
        mcr = ET.SubElement(send, "MidiControllerRange")
        _v(mcr, "Min", str(_VOL_MIN))
        _v(mcr, "Max", "1")
        _automation_target(send, "AutomationTarget", ids)
        _automation_target(send, "ModulationTarget", ids)
        _v(holder, "EnabledByUser", "true")

    # Speaker
    _bool_param(mixer, "Speaker", "true", ids)

    _v(mixer, "SoloSink", "false")
    _v(mixer, "PanMode", "0")

    _float_param(mixer, "Pan", str(round(track.pan, 6)), ids,
                 min_val="-1", max_val="1")
    _float_param(mixer, "SplitStereoPanL", "-1", ids,
                 min_val="-1", max_val="1")
    _float_param(mixer, "SplitStereoPanR", "1", ids,
                 min_val="-1", max_val="1")

    # Volume (dB to linear)
    vol_linear = _db_to_linear(track.volume_db)
    _float_param(mixer, "Volume", str(round(vol_linear, 10)), ids,
                 min_val=str(_VOL_MIN), max_val=str(_VOL_MAX))

    _v(mixer, "ViewStateSessionTrackWidth", "93")
    xf = ET.SubElement(mixer, "CrossFadeState")
    _v(xf, "LomId", "0")
    _v(xf, "Manual", "1")
    _automation_target(xf, "AutomationTarget", ids)

    ET.SubElement(mixer, "SendsListWrapper", LomId="0")


# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATION ENVELOPES
# ═══════════════════════════════════════════════════════════════════════════

def _build_automation_envelopes(parent: ET.Element,
                                automations: list) -> ET.Element:
    """Build AutomationEnvelopes container (always present, even if empty).

    Returns the Envelopes sub-element so it can be populated later
    via _populate_automation_envelopes once the Mixer exists.
    """
    envelopes_elem = ET.SubElement(parent, "AutomationEnvelopes")
    envs = ET.SubElement(envelopes_elem, "Envelopes")
    return envs


def _mixer_param_map(mixer: ET.Element) -> dict[str, str]:
    """Build parameter_name → AutomationTarget Id mapping from a Mixer."""
    pmap: dict[str, str] = {}
    for tag in ("Volume", "Pan", "Speaker", "SplitStereoPanL",
                "SplitStereoPanR"):
        el = mixer.find(tag)
        if el is not None:
            at = el.find("AutomationTarget")
            if at is not None:
                pmap[tag] = at.get("Id")
    sends = mixer.find("Sends")
    if sends is not None:
        for holder in sends.findall("TrackSendHolder"):
            send = holder.find("Send")
            if send is not None:
                at = send.find("AutomationTarget")
                if at is not None:
                    pmap[f"Send {holder.get('Id', '0')}"] = at.get("Id")
    return pmap


def _populate_automation_envelopes(envs: ET.Element, automations: list,
                                   mixer: ET.Element) -> None:
    """Fill in automation envelopes with correct EnvelopeTarget/PointeeId.

    Only emits envelopes for parameters that have a matching
    AutomationTarget in the Mixer.  Skips unknown parameter names.
    Multiple automations targeting the same parameter are merged into
    a single envelope (Ableton crashes on duplicate envelopes per target).
    """
    if not automations:
        return
    pmap = _mixer_param_map(mixer)

    # Merge automations by parameter so each target gets ONE envelope
    merged: dict[str, list] = {}
    for auto in automations:
        target_id = pmap.get(auto.parameter_name)
        if target_id is None:
            continue  # skip parameters with no matching mixer target
        merged.setdefault(auto.parameter_name, []).extend(auto.points)

    auto_idx = 0
    for param_name, points in merged.items():
        target_id = pmap[param_name]
        points.sort(key=lambda p: p.time)

        # Ableton crashes (EXCEPTION_ACCESS_VIOLATION) if the first
        # automation event doesn't start at or before Time 0.  Prepend
        # a sentinel anchor at -63072000 (Ableton's "beginning of
        # time") using the first point's value so the parameter holds
        # constant until the actual automation begins.
        if points and points[0].time > 0:
            from types import SimpleNamespace
            anchor = SimpleNamespace(time=-63072000, value=points[0].value,
                                     curve=0.0)
            points.insert(0, anchor)

        env = ET.SubElement(envs, "AutomationEnvelope", Id=str(auto_idx))
        env_target = ET.SubElement(env, "EnvelopeTarget")
        _v(env_target, "PointeeId", target_id)
        automation = ET.SubElement(env, "Automation")
        events = ET.SubElement(automation, "Events")
        for pt_idx, pt in enumerate(points):
            attrs = {
                "Id": str(pt_idx),
                "Time": str(round(pt.time, 4)),
                "Value": str(round(pt.value, 6)),
            }
            if pt.curve != 0.0:
                attrs["CurveControl1X"] = str(round(0.5, 4))
                attrs["CurveControl1Y"] = str(round(pt.curve, 4))
                attrs["CurveControl2X"] = str(round(0.5, 4))
                attrs["CurveControl2Y"] = str(round(pt.curve, 4))
            ET.SubElement(events, "FloatEvent", **attrs)
        atvs = ET.SubElement(automation, "AutomationTransformViewState")
        _v(atvs, "IsTransformPending", "false")
        ET.SubElement(atvs, "TimeAndValueTransforms")
        auto_idx += 1


# ═══════════════════════════════════════════════════════════════════════════
# TRACK-LEVEL STRUCTURAL ELEMENTS
# ═══════════════════════════════════════════════════════════════════════════

def _track_preamble(t: ET.Element, track: ALSTrack) -> None:
    """Elements at the top of every track type."""
    _v(t, "LomId", "0")
    _v(t, "LomIdView", "0")
    _v(t, "IsContentSelectedInDocument", "false")
    _v(t, "PreferredContentViewMode", "0")

    td = ET.SubElement(t, "TrackDelay")
    _v(td, "Value", "0")
    _v(td, "IsValueSampleBased", "false")

    name_elem = ET.SubElement(t, "Name")
    _v(name_elem, "EffectiveName", track.name)
    _v(name_elem, "UserName", track.name)
    _v(name_elem, "Annotation", "")
    _v(name_elem, "MemorizedFirstClipName", "")

    _v(t, "Color", str(track.color))


def _track_postamble(t: ET.Element, track_type: str = "audio") -> None:
    """Elements after AutomationEnvelopes on every track type.

    Element set varies by track type (matches Ableton 12 factory template):
      - AudioTrack: full set including Freeze elements
      - MidiTrack: full set + ReWireDeviceMidiTargetId etc.
      - ReturnTrack / MainTrack / PreHearTrack: stops at LinkedTrackGroupId
    """
    _v(t, "TrackGroupId", "-1")
    _v(t, "TrackUnfolded", "true")
    ET.SubElement(t, "DevicesListWrapper", LomId="0")
    ET.SubElement(t, "ClipSlotsListWrapper", LomId="0")
    _v(t, "ViewData", "{}")

    tl = ET.SubElement(t, "TakeLanes")
    ET.SubElement(tl, "TakeLanes")
    _v(tl, "AreTakeLanesFolded", "true")

    _v(t, "LinkedTrackGroupId", "-1")

    # Return / master / pre-hear tracks stop here
    if track_type in ("return", "master", "prehear"):
        return

    # Audio + MIDI tracks continue with play/freeze state
    _v(t, "SavedPlayingSlot", "-1")
    _v(t, "SavedPlayingOffset", "0")
    _v(t, "Freeze", "false")
    _v(t, "NeedArrangerRefreeze", "true")
    _v(t, "PostProcessFreezeClips", "0")


def _build_clip_slots(parent: ET.Element, num_scenes: int) -> None:
    """Build empty ClipSlotList for MainSequencer / FreezeSequencer."""
    csl = ET.SubElement(parent, "ClipSlotList")
    for si in range(num_scenes):
        cs = ET.SubElement(csl, "ClipSlot", Id=str(si))
        _v(cs, "LomId", "0")
        cs_inner = ET.SubElement(cs, "ClipSlot")
        ET.SubElement(cs_inner, "Value")
        _v(cs, "HasStop", "true")
        _v(cs, "NeedRefreeze", "true")


def _build_arranger_automation_empty(parent: ET.Element, tag: str = "Sample") -> ET.Element:
    """Build empty Sample > ArrangerAutomation structure (or ClipTimeable for MIDI)."""
    container = ET.SubElement(parent, tag)
    aa = ET.SubElement(container, "ArrangerAutomation")
    events = ET.SubElement(aa, "Events")
    atv = ET.SubElement(aa, "AutomationTransformViewState")
    _v(atv, "IsTransformPending", "false")
    ET.SubElement(atv, "TimeAndValueTransforms")
    return events


_MODULATION_TARGET_NAMES = [
    "VolumeModulationTarget",
    "TranspositionModulationTarget",
    "TransientEnvelopeModulationTarget",
    "GrainSizeModulationTarget",
    "FluxModulationTarget",
    "SampleOffsetModulationTarget",
    "ComplexProFormantsModulationTarget",
    "ComplexProEnvelopeModulationTarget",
]


def _build_sequencer(dc: ET.Element, tag: str, track: ALSTrack,
                     ids: _IdCounter, num_scenes: int,
                     is_midi: bool = False, is_main: bool = True) -> ET.Element:
    """Build MainSequencer or FreezeSequencer.

    MainSequencer for MIDI tracks uses ClipTimeable (no modulation targets).
    All other sequencers (audio MainSequencer, all FreezeSequencers) use
    Sample + 8 modulation targets + 2 scroll positions.
    """
    seq = ET.SubElement(dc, tag)
    _device_header(seq, ids)
    _build_clip_slots(seq, num_scenes)
    _v(seq, "MonitoringEnum", "1")
    _v(seq, "KeepRecordMonitoringLatency", "true")

    use_clip_timeable = is_midi and is_main
    container_tag = "ClipTimeable" if use_clip_timeable else "Sample"
    events_elem = _build_arranger_automation_empty(seq, container_tag)

    # Audio-type sequencers need modulation targets + scroll positions
    if not use_clip_timeable:
        for mt_name in _MODULATION_TARGET_NAMES:
            _modulation_target(seq, mt_name, ids)
        _v(seq, "PitchViewScrollPosition", "-1073741824")
        _v(seq, "SampleOffsetModulationScrollPosition", "-1073741824")

    rec = ET.SubElement(seq, "Recorder")
    _v(rec, "IsArmed", str(track.armed).lower() if is_main else "false")
    _v(rec, "TakeCounter", "0")

    if is_midi and is_main:
        controllers = ET.SubElement(seq, "MidiControllers")
        for ci in range(131):
            ct_elem = ET.SubElement(controllers,
                                    f"ControllerTargets.{ci}",
                                    Id=str(ids.next()))
            _v(ct_elem, "LockEnvelope", "0")

    return events_elem


# ═══════════════════════════════════════════════════════════════════════════
# VST3 PLUGIN DEVICE BUILDER
# ═══════════════════════════════════════════════════════════════════════════

# Known VST3 plugins — CID (hex), vendor, category, device type
# device_type: 1 = instrument, 2 = effect
_VST3_REGISTRY: dict[str, dict] = {
    "Serum 2": {
        "cid": "56534558667350736572756D20320000",
        "vendor": "Xfer Records",
        "category": "Instrument|Synth",
        "device_type": 1,
    },
    "Serum 2 FX": {
        "cid": "56534558667351736572756D20322066",
        "vendor": "Xfer Records",
        "category": "Fx",
        "device_type": 2,
    },
}


def _cid_to_fields(cid_hex: str) -> tuple[int, int, int, int]:
    """Convert 32-char hex CID to 4 big-endian signed int32 values."""
    import struct
    return struct.unpack(">iiii", bytes.fromhex(cid_hex))


def _build_vst3_uid(parent: ET.Element, cid_fields: tuple[int, int, int, int]) -> None:
    """Append a <Uid> element with Fields.0 .. Fields.3 children."""
    uid = ET.SubElement(parent, "Uid")
    for i, val in enumerate(cid_fields):
        _v(uid, f"Fields.{i}", str(val))


def _build_vst3_plugin_device(
    devices_elem: ET.Element,
    device_name: str,
    ids: _IdCounter,
    device_id: int = 0,
    processor_state: bytes | None = None,
) -> None:
    """Build a VST3 PluginDevice element inside <Devices>.

    Creates a PluginDevice matching the structure Ableton Live 12 expects:
    standard device header, Vst3PluginInfo with correct Uid Fields.N naming,
    and a Vst3Preset.  When *processor_state* is provided the raw bytes are
    base64-encoded into <ProcessorState> so Ableton restores the plugin with
    a specific preset already loaded.
    """
    info = _VST3_REGISTRY.get(device_name)
    if info is None:
        _log.warning("No VST3 registry entry for %r -- skipping", device_name)
        return

    pd = ET.SubElement(devices_elem, "PluginDevice", Id=str(device_id))

    # Standard device header (LomId through SourceContext)
    _device_header(pd, ids)

    # PluginDevice-specific: MpePitchBendUsesTuning before PluginDesc
    _v(pd, "MpePitchBendUsesTuning", "true")

    # ── PluginDesc / Vst3PluginInfo ──────────────────────────────────────
    desc = ET.SubElement(pd, "PluginDesc")
    vst3 = ET.SubElement(desc, "Vst3PluginInfo", Id="0")
    _v(vst3, "WinPosX", "0")
    _v(vst3, "WinPosY", "0")
    num_inputs = "0" if info["device_type"] == 1 else "1"
    _v(vst3, "NumAudioInputs", num_inputs)
    _v(vst3, "NumAudioOutputs", "1")
    _v(vst3, "IsPlaceholderDevice", "false")

    # Preset > Vst3Preset (empty state -- Ableton loads defaults from plugin)
    cid_fields = _cid_to_fields(info["cid"])
    preset_wrap = ET.SubElement(vst3, "Preset")
    vp = ET.SubElement(preset_wrap, "Vst3Preset", Id=str(ids.next()))
    _v(vp, "OverwriteProtectionNumber", "3074")
    _v(vp, "MpeEnabled", "0")
    mpe_p = ET.SubElement(vp, "MpeSettings")
    _v(mpe_p, "ZoneType", "0")
    _v(mpe_p, "FirstNoteChannel", "1")
    _v(mpe_p, "LastNoteChannel", "15")
    ET.SubElement(vp, "ParameterSettings")
    _v(vp, "IsOn", "true")
    _v(vp, "PowerMacroControlIndex", "-1")
    pmr = ET.SubElement(vp, "PowerMacroMappingRange")
    _v(pmr, "Min", "64")
    _v(pmr, "Max", "127")
    _v(vp, "IsFolded", "false")
    _v(vp, "StoredAllParameters", "true")
    _v(vp, "DeviceLomId", "0")
    _v(vp, "DeviceViewLomId", "0")
    _v(vp, "IsOnLomId", "0")
    _v(vp, "ParametersListWrapperLomId", "0")
    _build_vst3_uid(vp, cid_fields)
    _v(vp, "DeviceType", str(info["device_type"]))
    ps_elem = ET.SubElement(vp, "ProcessorState")
    cs_elem = ET.SubElement(vp, "ControllerState")
    if processor_state:
        import base64
        ps_elem.text = base64.b64encode(processor_state).decode("ascii")
        cs_elem.text = ps_elem.text
    _v(vp, "Name", "")
    ET.SubElement(vp, "PresetRef")

    # Outer Name & Uid on Vst3PluginInfo
    _v(vst3, "Name", device_name)
    _build_vst3_uid(vst3, cid_fields)
    _v(vst3, "DeviceType", str(info["device_type"]))

    # ── Post-PluginDesc elements ─────────────────────────────────────────
    _v(pd, "MpeEnabled", "false")
    _mpe_settings(pd)

    # Empty ParameterList (Ableton populates from plugin on load)
    ET.SubElement(pd, "ParameterList")


def _build_device_chain(dc: ET.Element, track: ALSTrack, ids: _IdCounter,
                        num_returns: int, num_scenes: int,
                        is_midi: bool = False,
                        track_role: str = "audio") -> ET.Element | None:
    """Build complete DeviceChain.  Returns the MainSequencer events element
    so audio clips can be injected into it.

    track_role: "audio" | "midi" | "return"
        - audio/midi: MainSequencer + FreezeSequencer + inner DeviceChain
        - return: FreezeSequencer + inner DeviceChain (no MainSequencer)
    """
    # AutomationLanes
    al_wrap = ET.SubElement(dc, "AutomationLanes")
    al_inner = ET.SubElement(al_wrap, "AutomationLanes")
    lane = ET.SubElement(al_inner, "AutomationLane", Id="0")
    _v(lane, "SelectedDevice", "0")
    _v(lane, "SelectedEnvelope", "0")
    _v(lane, "IsContentSelectedInDocument", "false")
    _v(lane, "LaneHeight", "68")
    _v(al_wrap, "AreAdditionalAutomationLanesFolded", "true")

    # ClipEnvelopeChooserViewState
    cevs = ET.SubElement(dc, "ClipEnvelopeChooserViewState")
    _v(cevs, "SelectedDevice", "0")
    _v(cevs, "SelectedEnvelope", "0")
    _v(cevs, "PreferModulationVisible", "false")

    # Routing
    _routing(dc, "AudioInputRouting", "AudioIn/External/S0", "Ext. In", "1/2")
    _routing(dc, "MidiInputRouting", "MidiIn/External.All/-1", "Ext: All Ins")
    _routing(dc, "AudioOutputRouting", "AudioOut/Main", "Master")
    _routing(dc, "MidiOutputRouting", "MidiOut/None", "None")

    # Mixer
    _build_mixer(dc, track, ids, num_returns)

    # MainSequencer (not present on return/master/prehear tracks)
    events_elem = None
    if track_role in ("audio", "midi"):
        events_elem = _build_sequencer(dc, "MainSequencer", track, ids,
                                       num_scenes, is_midi=(track_role == "midi"),
                                       is_main=True)

    if track_role == "return":
        # Return tracks: inner DeviceChain BEFORE FreezeSequencer
        # (matches factory template element ordering)
        inner_dc = ET.SubElement(dc, "DeviceChain")
        devices_elem = ET.SubElement(inner_dc, "Devices")
        ET.SubElement(inner_dc, "SignalModulations")
        _build_sequencer(dc, "FreezeSequencer", track, ids,
                         0, is_midi=False, is_main=False)
    else:
        # Audio/MIDI tracks: FreezeSequencer BEFORE inner DeviceChain
        freeze_scenes = num_scenes
        _build_sequencer(dc, "FreezeSequencer", track, ids,
                         freeze_scenes, is_midi=False, is_main=False)
        inner_dc = ET.SubElement(dc, "DeviceChain")
        devices_elem = ET.SubElement(inner_dc, "Devices")

    # VST3 PluginDevice auto-loading — embed plugin references so
    # Ableton instantiates instruments when the .als is opened.
    if track_role != "return":
        for dev_idx, dev_name in enumerate(track.device_names):
            state = track.preset_states.get(dev_name)
            _build_vst3_plugin_device(devices_elem, dev_name, ids,
                                      device_id=dev_idx,
                                      processor_state=state)
        ET.SubElement(inner_dc, "SignalModulations")

    return events_elem


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO CLIP BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _inject_audio_clips(events_elem: ET.Element, track: ALSTrack,
                        total_beats: float, als_dir: str,
                        project_bpm: float) -> None:
    """Inject AudioClip elements into an ArrangerAutomation Events element.

    Produces the full 48-element AudioClip structure matching Ableton Live 12's
    schema (reverse-engineered from Sample Reference.als in Core Library).
    """
    clip_sources = []
    if track.arrangement_clips:
        for ci in track.arrangement_clips:
            clip_sources.append({
                "path": ci.path,
                "start_beat": ci.start_beat,
                "length_beats": ci.length_beats or total_beats or 288.0,
                "warp_mode": ci.warp_mode,
                "warp_markers": ci.warp_markers,
                "loop": ci.loop,
                "loop_start": ci.loop_start,
                "loop_end": ci.loop_end,
                "gain": ci.gain,
                "name": ci.name or Path(ci.path).stem,
                "sample_rate": ci.sample_rate,
                "duration_frames": ci.duration_frames,
                "file_size": ci.file_size,
            })
    elif track.clip_paths:
        for clip_path in track.clip_paths:
            clip_sources.append({
                "path": clip_path,
                "start_beat": 0.0,
                "length_beats": total_beats if total_beats > 0 else 288.0,
                "warp_mode": 0, "warp_markers": [],
                "loop": False, "loop_start": 0.0, "loop_end": 0.0,
                "gain": 1.0, "name": Path(clip_path).stem,
                "sample_rate": 0, "duration_frames": 0, "file_size": 0,
            })

    for clip_id, cs in enumerate(clip_sources):
        abs_path = str(Path(cs["path"]).resolve())
        file_name = Path(cs["path"]).name
        rel_path = abs_path
        if als_dir:
            rel_path = os.path.relpath(abs_path, als_dir).replace("\\", "/")

        end_beats = cs["start_beat"] + cs["length_beats"]
        clip = ET.SubElement(events_elem, "AudioClip",
                             Id=str(clip_id),
                             Time=str(round(cs["start_beat"], 4)))

        # --- Full 48-element AudioClip (matches Ableton 12 schema) ---
        _v(clip, "LomId", "0")
        _v(clip, "LomIdView", "0")
        _v(clip, "CurrentStart", str(round(cs["start_beat"], 4)))
        _v(clip, "CurrentEnd", str(round(end_beats, 4)))

        # Loop (7 children)
        loop_elem = ET.SubElement(clip, "Loop")
        loop_start = cs["loop_start"] if cs["loop"] else cs["start_beat"]
        loop_end = (cs["loop_end"] if cs["loop"] and cs["loop_end"]
                    else end_beats)
        _v(loop_elem, "LoopStart", str(round(loop_start, 4)))
        _v(loop_elem, "LoopEnd", str(round(loop_end, 4)))
        _v(loop_elem, "StartRelative", "0")
        _v(loop_elem, "LoopOn", str(cs["loop"]).lower())
        _v(loop_elem, "OutMarker", str(round(end_beats, 4)))
        _v(loop_elem, "HiddenLoopStart", "0")
        _v(loop_elem, "HiddenLoopEnd", str(round(end_beats, 4)))

        # Name (direct Value attribute, NOT nested)
        _v(clip, "Name", cs["name"])
        _v(clip, "Annotation", "")
        _v(clip, "Color", "-1")
        _v(clip, "LaunchMode", "0")
        _v(clip, "LaunchQuantisation", "0")

        # TimeSignature
        time_sig = ET.SubElement(clip, "TimeSignature")
        ts_changes = ET.SubElement(time_sig, "TimeSignatures")
        rts = ET.SubElement(ts_changes, "RemoteableTimeSignature", Id="0")
        _v(rts, "Numerator", "4")
        _v(rts, "Denominator", "4")
        _v(rts, "Time", "0")

        # Envelopes (empty)
        envs_outer = ET.SubElement(clip, "Envelopes")
        ET.SubElement(envs_outer, "Envelopes")

        # ScrollerTimePreserver
        stp = ET.SubElement(clip, "ScrollerTimePreserver")
        _v(stp, "LeftTime", "0")
        _v(stp, "RightTime", "0")

        # TimeSelection
        tsel = ET.SubElement(clip, "TimeSelection")
        _v(tsel, "AnchorTime", "0")
        _v(tsel, "OtherTime", "0")

        _v(clip, "Legato", "false")
        _v(clip, "Ram", "false")

        # GrooveSettings
        gs = ET.SubElement(clip, "GrooveSettings")
        _v(gs, "GrooveId", "-1")

        _v(clip, "Disabled", "false")
        _v(clip, "VelocityAmount", "0")

        # FollowAction (10 children)
        fa = ET.SubElement(clip, "FollowAction")
        _v(fa, "FollowTime", "4")
        _v(fa, "IsLinked", "true")
        _v(fa, "LoopIterations", "1")
        _v(fa, "FollowActionA", "4")
        _v(fa, "FollowActionB", "0")
        _v(fa, "FollowChanceA", "100")
        _v(fa, "FollowChanceB", "0")
        _v(fa, "JumpIndexA", "1")
        _v(fa, "JumpIndexB", "1")
        _v(fa, "FollowActionEnabled", "false")

        # Grid (6 children)
        grid = ET.SubElement(clip, "Grid")
        _v(grid, "FixedNumerator", "1")
        _v(grid, "FixedDenominator", "16")
        _v(grid, "GridIntervalPixel", "20")
        _v(grid, "Ntoles", "2")
        _v(grid, "SnapToGrid", "true")
        _v(grid, "Fixed", "false")

        _v(clip, "FreezeStart", "0")
        _v(clip, "FreezeEnd", "0")
        _v(clip, "IsWarped", "true")
        _v(clip, "TakeId", "0")
        _v(clip, "IsInKey", "false")

        # ScaleInformation
        si = ET.SubElement(clip, "ScaleInformation")
        _v(si, "Root", "0")
        _v(si, "Name", "0")

        # SampleRef (matches Ableton 12 FileRef schema)
        sample_ref = ET.SubElement(clip, "SampleRef")
        file_ref = ET.SubElement(sample_ref, "FileRef")
        _v(file_ref, "RelativePathType", "3")
        _v(file_ref, "RelativePath", rel_path)
        _v(file_ref, "Path", abs_path)
        _v(file_ref, "Type", "1")
        _v(file_ref, "LivePackName", "")
        _v(file_ref, "LivePackId", "")
        _v(file_ref, "OriginalFileSize", str(cs.get("file_size") or 0))
        _v(file_ref, "OriginalCrc", "0")
        _v(file_ref, "SourceHint", "")
        _v(sample_ref, "LastModDate", "0")
        ET.SubElement(sample_ref, "SourceContext")
        _v(sample_ref, "SampleUsageHint", "0")
        _v(sample_ref, "DefaultDuration", str(cs.get("duration_frames") or 0))
        _v(sample_ref, "DefaultSampleRate", str(cs.get("sample_rate") or 44100))
        _v(sample_ref, "SamplesToAutoWarp", "0")

        # Onsets
        onsets = ET.SubElement(clip, "Onsets")
        ET.SubElement(onsets, "UserOnsets")
        _v(onsets, "HasUserOnsets", "false")

        _v(clip, "WarpMode", str(cs["warp_mode"]))
        _v(clip, "GranularityTones", "30")
        _v(clip, "GranularityTexture", "65")
        _v(clip, "FluctuationTexture", "25")
        _v(clip, "TransientResolution", "6")
        _v(clip, "TransientLoopMode", "2")
        _v(clip, "TransientEnvelope", "100")
        _v(clip, "ComplexProFormants", "100")
        _v(clip, "ComplexProEnvelope", "128")
        _v(clip, "Sync", "true")
        _v(clip, "HiQ", "true")
        _v(clip, "Fade", "true")

        # Fades (10 children)
        fades = ET.SubElement(clip, "Fades")
        _v(fades, "FadeInLength", "0")
        _v(fades, "FadeOutLength", "0")
        _v(fades, "ClipFadesAreInitialized", "true")
        _v(fades, "CrossfadeInState", "0")
        _v(fades, "FadeInCurveSkew", "0")
        _v(fades, "FadeInCurveSlope", "0")
        _v(fades, "FadeOutCurveSkew", "0")
        _v(fades, "FadeOutCurveSlope", "0")
        _v(fades, "IsDefaultFadeIn", "true")
        _v(fades, "IsDefaultFadeOut", "true")

        _v(clip, "PitchCoarse", "0")
        _v(clip, "PitchFine", "0")
        _v(clip, "SampleVolume", str(round(cs["gain"], 4)))

        # Warp markers
        warp_elem = ET.SubElement(clip, "WarpMarkers")
        if cs["warp_markers"]:
            for wi, wm in enumerate(cs["warp_markers"]):
                ET.SubElement(warp_elem, "WarpMarker",
                              Id=str(wi),
                              SecTime=str(round(wm.sec_time, 6)),
                              BeatTime=str(round(wm.beat_time, 4)))
        else:
            ET.SubElement(warp_elem, "WarpMarker",
                          Id="0", SecTime="0", BeatTime="0")
            sec_end = cs["length_beats"] / (project_bpm / 60.0)
            ET.SubElement(warp_elem, "WarpMarker",
                          Id="1",
                          SecTime=str(round(sec_end, 6)),
                          BeatTime=str(round(cs["length_beats"], 4)))

        ET.SubElement(clip, "SavedWarpMarkersForStretched")
        _v(clip, "MarkersGenerated", "false")
        _v(clip, "IsSongTempoLeader", "false")


def _inject_midi_clips(events_elem: ET.Element, track: ALSTrack) -> None:
    """Inject MidiClip elements into a MainSequencer's ArrangerAutomation Events.

    Creates the full MidiClip XML structure matching Ableton Live 12's schema,
    including KeyTrack-based note storage.
    """
    if not track.midi_clips:
        return

    for clip_id, mc in enumerate(track.midi_clips):
        end_beat = mc.start_beat + mc.length_beats
        clip = ET.SubElement(events_elem, "MidiClip",
                             Id=str(clip_id),
                             Time=str(round(mc.start_beat, 4)))

        _v(clip, "LomId", "0")
        _v(clip, "LomIdView", "0")
        _v(clip, "CurrentStart", str(round(mc.start_beat, 4)))
        _v(clip, "CurrentEnd", str(round(end_beat, 4)))

        # Loop
        loop_elem = ET.SubElement(clip, "Loop")
        _v(loop_elem, "LoopStart", str(round(mc.start_beat, 4)))
        _v(loop_elem, "LoopEnd", str(round(end_beat, 4)))
        _v(loop_elem, "StartRelative", "0")
        _v(loop_elem, "LoopOn", "false")
        _v(loop_elem, "OutMarker", str(round(end_beat, 4)))
        _v(loop_elem, "HiddenLoopStart", "0")
        _v(loop_elem, "HiddenLoopEnd", str(round(end_beat, 4)))

        _v(clip, "Name", mc.name)
        _v(clip, "Annotation", "")
        _v(clip, "Color", "-1")
        _v(clip, "LaunchMode", "0")
        _v(clip, "LaunchQuantisation", "0")

        # TimeSignature
        time_sig = ET.SubElement(clip, "TimeSignature")
        ts_changes = ET.SubElement(time_sig, "TimeSignatures")
        rts = ET.SubElement(ts_changes, "RemoteableTimeSignature", Id="0")
        _v(rts, "Numerator", "4")
        _v(rts, "Denominator", "4")
        _v(rts, "Time", "0")

        # Envelopes (empty)
        envs_outer = ET.SubElement(clip, "Envelopes")
        ET.SubElement(envs_outer, "Envelopes")

        # ScrollerTimePreserver
        stp = ET.SubElement(clip, "ScrollerTimePreserver")
        _v(stp, "LeftTime", "0")
        _v(stp, "RightTime", "8")

        # TimeSelection
        tsel = ET.SubElement(clip, "TimeSelection")
        _v(tsel, "AnchorTime", "0")
        _v(tsel, "OtherTime", "0")

        _v(clip, "Legato", "false")
        _v(clip, "Ram", "false")

        # GrooveSettings
        gs = ET.SubElement(clip, "GrooveSettings")
        _v(gs, "GrooveId", "-1")

        _v(clip, "Disabled", "false")
        _v(clip, "VelocityAmount", "0")

        # FollowAction
        fa = ET.SubElement(clip, "FollowAction")
        _v(fa, "FollowTime", "4")
        _v(fa, "IsLinked", "true")
        _v(fa, "LoopIterations", "1")
        _v(fa, "FollowActionA", "4")
        _v(fa, "FollowActionB", "0")
        _v(fa, "FollowChanceA", "100")
        _v(fa, "FollowChanceB", "0")
        _v(fa, "JumpIndexA", "1")
        _v(fa, "JumpIndexB", "1")
        _v(fa, "FollowActionEnabled", "false")

        # Grid
        grid = ET.SubElement(clip, "Grid")
        _v(grid, "FixedNumerator", "1")
        _v(grid, "FixedDenominator", "16")
        _v(grid, "GridIntervalPixel", "20")
        _v(grid, "Ntoles", "2")
        _v(grid, "SnapToGrid", "true")
        _v(grid, "Fixed", "false")

        _v(clip, "FreezeStart", "0")
        _v(clip, "FreezeEnd", "0")
        _v(clip, "IsWarped", "true")
        _v(clip, "TakeId", "-1")

        # Notes — group notes by pitch into KeyTracks
        notes_elem = ET.SubElement(clip, "Notes")
        key_tracks = ET.SubElement(notes_elem, "KeyTracks")

        global_note_id = 0
        if mc.notes:
            # Group notes by pitch
            by_pitch: dict[int, list[ALSMidiNote]] = {}
            for n in mc.notes:
                by_pitch.setdefault(n.pitch, []).append(n)

            kt_id = 0
            for pitch in sorted(by_pitch.keys()):
                kt = ET.SubElement(key_tracks, "KeyTrack", Id=str(kt_id))
                _v(kt, "MidiKey", str(pitch))
                notes_container = ET.SubElement(kt, "Notes")
                for note in sorted(by_pitch[pitch],
                                   key=lambda n: n.time):
                    # Note time is relative to clip start
                    note_time = note.time - mc.start_beat
                    ET.SubElement(
                        notes_container, "MidiNoteEvent",
                        Time=str(round(note_time, 4)),
                        Duration=str(round(note.duration, 4)),
                        Velocity=str(note.velocity),
                        VelocityDeviation="0",
                        OffVelocity="64",
                        Probability="1",
                        IsEnabled="true",
                        NoteId=str(global_note_id),
                    )
                    global_note_id += 1
                kt_id += 1

        # PerNoteEventStore (empty)
        pnes = ET.SubElement(notes_elem, "PerNoteEventStore")
        ET.SubElement(pnes, "EventLists")

        # NoteProbabilityGroups (required by Ableton 12)
        ET.SubElement(notes_elem, "NoteProbabilityGroups")
        pig = ET.SubElement(notes_elem, "ProbabilityGroupIdGenerator")
        _v(pig, "NextId", "1")
        nig = ET.SubElement(notes_elem, "NoteIdGenerator")
        _v(nig, "NextId", str(global_note_id))

        _v(clip, "BankSelectCoarse", "-1")
        _v(clip, "BankSelectFine", "-1")
        _v(clip, "ProgramChange", "-1")
        _v(clip, "NoteEditorFoldInZoom", "-1")
        _v(clip, "NoteEditorFoldInScroll", "0")
        _v(clip, "NoteEditorFoldOutZoom", "-1")
        _v(clip, "NoteEditorFoldOutScroll", "1024")
        _v(clip, "NoteEditorFoldScaleZoom", "-1")
        _v(clip, "NoteEditorFoldScaleScroll", "0")
        scale_info = ET.SubElement(clip, "ScaleInformation")
        _v(scale_info, "RootNote", "0")
        _v(scale_info, "Name", "0")
        _v(clip, "IsInKey", "false")
        _v(clip, "NoteSpellingPreference", "3")
        _v(clip, "AccidentalSpellingPreference", "3")
        _v(clip, "PreferFlatRootNote", "false")

        # ExpressionGrid
        egrid = ET.SubElement(clip, "ExpressionGrid")
        _v(egrid, "FixedNumerator", "1")
        _v(egrid, "FixedDenominator", "16")
        _v(egrid, "GridIntervalPixel", "20")
        _v(egrid, "Ntoles", "2")
        _v(egrid, "SnapToGrid", "false")
        _v(egrid, "Fixed", "false")


# ═══════════════════════════════════════════════════════════════════════════
# TRACK BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_midi_track(parent: ET.Element, track: ALSTrack, track_id: int,
                      ids: _IdCounter, num_returns: int,
                      num_scenes: int) -> ET.Element:
    """Build a complete MidiTrack matching Ableton's schema."""
    t = ET.SubElement(parent, "MidiTrack", Id=str(track_id),
                      SelectedToolPanel="7",
                      SelectedTransformationName="",
                      SelectedGeneratorName="")
    _track_preamble(t, track)
    envs = _build_automation_envelopes(t, track.automations)
    _track_postamble(t, track_type="midi")

    dc = ET.SubElement(t, "DeviceChain")
    events_elem = _build_device_chain(dc, track, ids, num_returns, num_scenes,
                                      track_role="midi")
    _populate_automation_envelopes(envs, track.automations, dc.find('Mixer'))

    # Inject MIDI clips into MainSequencer's ArrangerAutomation
    if events_elem is not None:
        _inject_midi_clips(events_elem, track)

    # MIDI-specific elements (after DeviceChain)
    _v(t, "ReWireDeviceMidiTargetId", "0")
    _v(t, "PitchbendRange", "96")
    _v(t, "IsTuned", "false")
    _v(t, "ControllerLayoutRemoteable", "0")
    clc = ET.SubElement(t, "ControllerLayoutCustomization")
    _v(clc, "PitchClassSource", "0")
    _v(clc, "OctaveSource", "2")
    _v(clc, "KeyNoteTarget", "60")
    _v(clc, "StepSize", "1")
    _v(clc, "OctaveEvery", "12")
    _v(clc, "AllowedKeys", "0")
    _v(clc, "FillerKeysMapTo", "0")

    return t


def _build_audio_track(parent: ET.Element, track: ALSTrack, track_id: int,
                       ids: _IdCounter, num_returns: int, num_scenes: int,
                       total_beats: float = 0.0, als_dir: str = "",
                       project_bpm: float = DEFAULT_BPM) -> ET.Element:
    """Build a complete AudioTrack with arrangement clips."""
    t = ET.SubElement(parent, "AudioTrack", Id=str(track_id),
                      SelectedToolPanel="7",
                      SelectedTransformationName="",
                      SelectedGeneratorName="")
    _track_preamble(t, track)
    envs = _build_automation_envelopes(t, track.automations)
    _track_postamble(t, track_type="audio")

    dc = ET.SubElement(t, "DeviceChain")
    events_elem = _build_device_chain(dc, track, ids, num_returns, num_scenes,
                                      track_role="audio")
    _populate_automation_envelopes(envs, track.automations, dc.find('Mixer'))

    # Inject arrangement clips into MainSequencer's ArrangerAutomation
    _inject_audio_clips(events_elem, track, total_beats, als_dir, project_bpm)

    return t


def _build_return_track(parent: ET.Element, track: ALSTrack, track_id: int,
                        ids: _IdCounter, num_returns: int,
                        num_scenes: int) -> ET.Element:
    """Build a complete ReturnTrack matching Ableton's schema."""
    t = ET.SubElement(parent, "ReturnTrack", Id=str(track_id),
                      SelectedToolPanel="7",
                      SelectedTransformationName="",
                      SelectedGeneratorName="")
    _track_preamble(t, track)
    envs = _build_automation_envelopes(t, track.automations)
    _track_postamble(t, track_type="return")

    dc = ET.SubElement(t, "DeviceChain")
    _build_device_chain(dc, track, ids, num_returns, num_scenes,
                        track_role="return")
    _populate_automation_envelopes(envs, track.automations, dc.find('Mixer'))

    return t


# ═══════════════════════════════════════════════════════════════════════════
# TRANSPORT
# ═══════════════════════════════════════════════════════════════════════════

def _build_transport(live_set: ET.Element, project: ALSProject,
                     ids: _IdCounter) -> None:
    """Build the Transport element."""
    transport = ET.SubElement(live_set, "Transport")

    tempo = ET.SubElement(transport, "Tempo")
    _v(tempo, "LomId", "0")
    _v(tempo, "Manual", str(project.bpm))
    mcr = ET.SubElement(tempo, "MidiControllerRange")
    _v(mcr, "Min", "60")
    _v(mcr, "Max", "999")
    _automation_target(tempo, "AutomationTarget", ids)
    _automation_target(tempo, "ModulationTarget", ids)

    time_sig = ET.SubElement(transport, "TimeSignature")
    ts_val = ET.SubElement(time_sig, "TimeSignatures")
    ts_event = ET.SubElement(ts_val, "RemoteableTimeSignature", Id="0")
    _v(ts_event, "Numerator", str(project.time_sig_num))
    _v(ts_event, "Denominator", str(project.time_sig_den))
    _v(ts_event, "Time", "0")

    _v(transport, "LoopOn", "false")
    _v(transport, "LoopStart", "0")
    _v(transport, "LoopLength", "16")
    _v(transport, "CurrentTime", "0")
    _v(transport, "PunchIn", "false")
    _v(transport, "PunchOut", "false")
    _v(transport, "MetronomeOn", "false")
    _v(transport, "DrawMode", "false")


# ═══════════════════════════════════════════════════════════════════════════
# MASTER TRACK
# ═══════════════════════════════════════════════════════════════════════════

def _build_master_track(live_set: ET.Element, project: ALSProject,
                        ids: _IdCounter, num_returns: int,
                        num_scenes: int) -> None:
    """Build the MasterTrack element (matches factory template structure)."""
    mt = ET.SubElement(live_set, "MasterTrack")

    # Use track preamble/postamble for consistency
    master_info = ALSTrack(name="Master", track_type="audio",
                           color=-1, volume_db=project.master_volume_db)
    _track_preamble(mt, master_info)
    _build_automation_envelopes(mt, [])
    _track_postamble(mt, track_type="master")

    dc = ET.SubElement(mt, "DeviceChain")

    # AutomationLanes
    al_wrap = ET.SubElement(dc, "AutomationLanes")
    al_inner = ET.SubElement(al_wrap, "AutomationLanes")
    lane = ET.SubElement(al_inner, "AutomationLane", Id="0")
    _v(lane, "SelectedDevice", "0")
    _v(lane, "SelectedEnvelope", "0")
    _v(lane, "IsContentSelectedInDocument", "false")
    _v(lane, "LaneHeight", "68")
    _v(al_wrap, "AreAdditionalAutomationLanesFolded", "true")

    cevs = ET.SubElement(dc, "ClipEnvelopeChooserViewState")
    _v(cevs, "SelectedDevice", "0")
    _v(cevs, "SelectedEnvelope", "0")
    _v(cevs, "PreferModulationVisible", "false")

    _routing(dc, "AudioInputRouting", "AudioIn/External/S0", "Ext. In", "1/2")
    _routing(dc, "MidiInputRouting", "MidiIn/External.All/-1", "Ext: All Ins")
    _routing(dc, "AudioOutputRouting", "AudioOut/External/S0", "Ext. Out", "1/2")
    _routing(dc, "MidiOutputRouting", "MidiOut/None", "None")

    master_track = ALSTrack(
        name="Master", track_type="audio",
        volume_db=project.master_volume_db, pan=0.0)
    _build_mixer(dc, master_track, ids, num_returns)

    # FreezeSequencer (MainTrack uses minimal AudioSequencer)
    freeze_seq = ET.SubElement(dc, "FreezeSequencer")
    ET.SubElement(freeze_seq, "AudioSequencer", Id="0")

    # Inner DeviceChain (Devices + SignalModulations)
    inner_dc = ET.SubElement(dc, "DeviceChain")
    ET.SubElement(inner_dc, "Devices")
    ET.SubElement(inner_dc, "SignalModulations")


# ═══════════════════════════════════════════════════════════════════════════
# SCENES
# ═══════════════════════════════════════════════════════════════════════════

def _build_scene_element(parent: ET.Element, scene_id: int,
                         name: str, tempo: float) -> ET.Element:
    """Build a single Scene element matching Ableton 12 factory template.

    Key differences from Track Name elements:
      - Scene Name is simple: <Name Value="text"/>
      - Scene has FollowAction block
      - Scene has ClipSlotsListWrapper
    """
    s = ET.SubElement(parent, "Scene", Id=str(scene_id))

    # FollowAction (required by Ableton, even if disabled)
    fa = ET.SubElement(s, "FollowAction")
    _v(fa, "FollowTime", "4")
    _v(fa, "IsLinked", "true")
    _v(fa, "LoopIterations", "1")
    _v(fa, "FollowActionA", "4")
    _v(fa, "FollowActionB", "0")
    _v(fa, "FollowChanceA", "100")
    _v(fa, "FollowChanceB", "0")
    _v(fa, "JumpIndexA", "0")
    _v(fa, "JumpIndexB", "0")
    _v(fa, "FollowActionEnabled", "false")

    _v(s, "Name", name)
    _v(s, "Annotation", "")
    _v(s, "Color", "-1")
    _v(s, "Tempo", str(round(tempo, 2)))
    _v(s, "IsTempoEnabled", "false")
    _v(s, "TimeSignatureId", "201")
    _v(s, "IsTimeSignatureEnabled", "false")
    _v(s, "LomId", "0")
    ET.SubElement(s, "ClipSlotsListWrapper", LomId="0")
    return s


def _build_scenes(live_set: ET.Element, scenes: list[ALSScene]) -> None:
    """Build the Scenes element."""
    scenes_elem = ET.SubElement(live_set, "Scenes")
    for i, scene in enumerate(scenes):
        _build_scene_element(scenes_elem, i, scene.name, scene.tempo)


# ═══════════════════════════════════════════════════════════════════════════
# CUE POINTS / LOCATORS
# ═══════════════════════════════════════════════════════════════════════════

def _build_cue_points(live_set: ET.Element,
                      cue_points: list[ALSCuePoint]) -> None:
    """Build Locators element (Ableton's name for cue points)."""
    if not cue_points:
        return
    locators = ET.SubElement(live_set, "Locators")
    locat_inner = ET.SubElement(locators, "Locators")
    for i, cp in enumerate(cue_points):
        loc = ET.SubElement(locat_inner, "Locator", Id=str(i))
        _v(loc, "LomId", "0")
        _v(loc, "Time", str(round(cp.time, 4)))
        _v(loc, "Name", cp.name)
        _v(loc, "Annotation", "")
        _v(loc, "IsSongStart", "false")


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _load_default_template() -> ET.Element | None:
    """Load and decompress Ableton's default template as XML skeleton."""
    for p in _DEFAULT_TEMPLATE_PATHS:
        if p.is_file():
            try:
                with gzip.open(str(p), "rb") as f:
                    return ET.fromstring(f.read())
            except Exception as exc:
                _log.warning("Failed to load template %s: %s", p, exc)
    return None


def _update_track_sends(track_elem: ET.Element, num_returns: int,
                        ids: _IdCounter) -> None:
    """Rebuild a track's Sends to match the project's return count."""
    mixer = track_elem.find("DeviceChain/Mixer")
    if mixer is None:
        return
    sends = mixer.find("Sends")
    if sends is None:
        return
    for child in list(sends):
        sends.remove(child)
    for i in range(num_returns):
        holder = ET.SubElement(sends, "TrackSendHolder", Id=str(i))
        send = ET.SubElement(holder, "Send")
        _v(send, "LomId", "0")
        _v(send, "Manual", str(_VOL_MIN))
        mcr = ET.SubElement(send, "MidiControllerRange")
        _v(mcr, "Min", str(_VOL_MIN))
        _v(mcr, "Max", "1")
        _automation_target(send, "AutomationTarget", ids)
        _automation_target(send, "ModulationTarget", ids)
        _v(holder, "EnabledByUser", "true")


# ═══════════════════════════════════════════════════════════════════════════
# FALLBACK BUILDER  (used when no template is available)
# ═══════════════════════════════════════════════════════════════════════════

def _build_als_from_scratch(project: ALSProject,
                            als_path: str = "") -> ET.Element:
    """Build ALS from scratch (fallback when template is unavailable)."""
    ids = _IdCounter(10000)

    root = ET.Element("Ableton",
                      MajorVersion="5",
                      MinorVersion=ALS_SCHEMA_VERSION,
                      SchemaChangeCount="10",
                      Creator=ALS_CREATOR,
                      Revision="")

    live_set = ET.SubElement(root, "LiveSet")

    # Header counters (NextPointeeId updated at the end)
    next_pid_elem = _v(live_set, "NextPointeeId", "0")
    _v(live_set, "OverwriteProtectionNumber", "2816")
    _v(live_set, "LomId", "0")
    _v(live_set, "LomIdView", "0")

    # Transport
    _build_transport(live_set, project, ids)

    num_returns = sum(1 for t in project.tracks if t.track_type == "return")
    num_scenes = max(len(project.scenes), 1)
    total_beats = num_scenes * project.time_sig_num * 8.0
    als_dir = str(Path(als_path).parent.resolve()) if als_path else ""

    # Tracks
    tracks_elem = ET.SubElement(live_set, "Tracks")
    track_id = 0
    for track in project.tracks:
        if track.track_type == "midi":
            _build_midi_track(tracks_elem, track, track_id, ids,
                              num_returns, num_scenes)
        elif track.track_type == "audio":
            _build_audio_track(tracks_elem, track, track_id, ids,
                               num_returns, num_scenes,
                               total_beats, als_dir, project.bpm)
        elif track.track_type == "return":
            _build_return_track(tracks_elem, track, track_id, ids,
                                num_returns, num_scenes)
        track_id += 1

    # Master Track
    _build_master_track(live_set, project, ids, num_returns, num_scenes)

    # Scenes
    _build_scenes(live_set, project.scenes)

    # Annotation
    if project.notes:
        annotation = ET.SubElement(live_set, "Annotation", Value=project.notes)

    # Cue Points / Locators
    _build_cue_points(live_set, project.cue_points)

    # Finalize NextPointeeId
    next_pid_elem.set("Value", str(ids.value))

    return root


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL BUILDER  (template skeleton approach)
# ═══════════════════════════════════════════════════════════════════════════

def build_als_xml(project: ALSProject,
                  als_path: str = "") -> ET.Element:
    """Build the complete Ableton Live set XML tree.

    Uses Ableton's own default template as the structural skeleton so that
    all 75+ required LiveSet children are present.  Only the dynamic parts
    (Tracks, Scenes, Locators, Transport tempo, master volume) are replaced.
    Falls back to building from scratch when no template is available.
    """
    # --- try to load the factory template --------------------------------
    template = _load_default_template()
    if template is None:
        _log.warning("Ableton default template not found -- "
                     "building ALS from scratch (may not open correctly)")
        return _build_als_from_scratch(project, als_path)

    live_set = template.find("LiveSet")
    if live_set is None:
        return _build_als_from_scratch(project, als_path)

    # Start IDs after the template's reserved range to avoid clashes
    next_pid_elem = live_set.find("NextPointeeId")
    start_id = (int(next_pid_elem.get("Value", "10000"))
                if next_pid_elem is not None else 10000)
    ids = _IdCounter(start_id)

    # Update root attributes
    template.set("Creator", ALS_CREATOR)
    template.set("MinorVersion", ALS_SCHEMA_VERSION)
    template.set("Revision", "")

    num_returns = sum(1 for t in project.tracks if t.track_type == "return")
    num_scenes = max(len(project.scenes), 1)
    total_beats = num_scenes * project.time_sig_num * 8.0
    als_dir = str(Path(als_path).parent.resolve()) if als_path else ""

    # -- Tracks -----------------------------------------------------------
    tracks_elem = live_set.find("Tracks")
    if tracks_elem is not None:
        for child in list(tracks_elem):
            tracks_elem.remove(child)
    else:
        tracks_elem = ET.SubElement(live_set, "Tracks")

    track_id = 0
    for track in project.tracks:
        if track.track_type == "midi":
            _build_midi_track(tracks_elem, track, track_id, ids,
                              num_returns, num_scenes)
        elif track.track_type == "audio":
            _build_audio_track(tracks_elem, track, track_id, ids,
                               num_returns, num_scenes,
                               total_beats, als_dir, project.bpm)
        elif track.track_type == "return":
            _build_return_track(tracks_elem, track, track_id, ids,
                                num_returns, num_scenes)
        track_id += 1

    # -- MainTrack (master volume + sends + tempo) -----------------------
    main_track = live_set.find("MainTrack")
    if main_track is not None:
        vol_manual = main_track.find("DeviceChain/Mixer/Volume/Manual")
        if vol_manual is not None:
            vol_linear = _db_to_linear(project.master_volume_db)
            vol_manual.set("Value", str(round(vol_linear, 10)))
        tempo_manual = main_track.find("DeviceChain/Mixer/Tempo/Manual")
        if tempo_manual is not None:
            tempo_manual.set("Value", str(project.bpm))
        # MainTrack Sends is empty in Ableton's template — do NOT populate it

    # -- SendsPre (one bool per return track) -----------------------------
    sends_pre = live_set.find("SendsPre")
    if sends_pre is not None:
        for child in list(sends_pre):
            sends_pre.remove(child)
        for i in range(num_returns):
            ET.SubElement(sends_pre, "SendPreBool",
                          Id=str(i), Value="false")

    # -- Transport (tempo + time signature) -------------------------------
    transport = live_set.find("Transport")
    if transport is not None:
        tempo_manual = transport.find("Tempo/Manual")
        if tempo_manual is not None:
            tempo_manual.set("Value", str(project.bpm))
        ts_container = transport.find("TimeSignature/TimeSignatures")
        if ts_container is not None:
            for rts in ts_container:
                num_el = rts.find("Numerator")
                den_el = rts.find("Denominator")
                if num_el is not None:
                    num_el.set("Value", str(project.time_sig_num))
                if den_el is not None:
                    den_el.set("Value", str(project.time_sig_den))

    # -- Scenes -----------------------------------------------------------
    scenes_elem = live_set.find("Scenes")
    if scenes_elem is not None:
        for child in list(scenes_elem):
            scenes_elem.remove(child)
    else:
        scenes_elem = ET.SubElement(live_set, "Scenes")

    if project.scenes:
        for i, scene in enumerate(project.scenes):
            _build_scene_element(scenes_elem, i, scene.name, scene.tempo)
    else:
        # Ableton crashes (EXCEPTION_ACCESS_VIOLATION) if Scenes is empty
        # but tracks have clip slots — always emit at least one scene.
        _build_scene_element(scenes_elem, 0, "", project.bpm)

    # -- Annotation -------------------------------------------------------
    annotation = live_set.find("Annotation")
    if annotation is not None and project.notes:
        annotation.set("Value", project.notes)

    # -- Locators (cue points) --------------------------------------------
    locators = live_set.find("Locators")
    if locators is not None:
        inner = locators.find("Locators")
        if inner is not None:
            for child in list(inner):
                inner.remove(child)
        else:
            inner = ET.SubElement(locators, "Locators")
    else:
        locators = ET.SubElement(live_set, "Locators")
        inner = ET.SubElement(locators, "Locators")

    for i, cp in enumerate(project.cue_points):
        loc = ET.SubElement(inner, "Locator", Id=str(i))
        _v(loc, "LomId", "0")
        _v(loc, "Time", str(round(cp.time, 4)))
        _v(loc, "Name", cp.name)
        _v(loc, "Annotation", "")
        _v(loc, "IsSongStart", "false")

    # -- Finalize NextPointeeId -------------------------------------------
    if next_pid_elem is not None:
        next_pid_elem.set("Value", str(ids.value))

    _log.info("Built ALS from template skeleton (%d tracks, %d scenes, "
              "%d locators)", len(project.tracks), len(project.scenes),
              len(project.cue_points))

    return template


# ═══════════════════════════════════════════════════════════════════════════
# FILE I/O
# ═══════════════════════════════════════════════════════════════════════════

def write_als(project: ALSProject, path: str) -> str:
    """Write an Ableton .als file (gzip-compressed XML)."""
    root = build_als_xml(project, als_path=path)
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(str(out_path), "wb") as f:
        f.write(xml_str.encode("utf-8"))

    _log.info("Wrote ALS: %s (%d tracks, %d scenes)",
              out_path.name, len(project.tracks), len(project.scenes))
    return str(out_path)


def write_als_json(project: ALSProject, path: str) -> str:
    """Write the project structure to JSON (for debugging)."""
    data = asdict(project)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
# DUBSTEP SESSION TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

# Track color indices (Ableton's palette)
COLOR_RED = 0
COLOR_ORANGE = 5
COLOR_YELLOW = 10
COLOR_GREEN = 18
COLOR_CYAN = 25
COLOR_BLUE = 30
COLOR_PURPLE = 40
COLOR_PINK = 50
COLOR_WHITE = 69


def dubstep_weapon_session() -> ALSProject:
    """Subtronics-style dubstep weapon session template."""
    return ALSProject(
        name="DUBFORGE_WEAPON",
        bpm=150.0,
        tracks=[
            ALSTrack(name="SUB", track_type="midi", color=COLOR_RED,
                     volume_db=0, device_names=["PSBS_Sub"],
                     clip_names=["Sub_Drop", "Sub_Build"]),
            ALSTrack(name="MID_BASS", track_type="midi", color=COLOR_ORANGE,
                     volume_db=-2, device_names=["Serum2_MidBass"],
                     clip_names=["MB_Drop", "MB_Build", "MB_Fill"]),
            ALSTrack(name="GROWL", track_type="midi", color=COLOR_YELLOW,
                     volume_db=-3, device_names=["Serum2_Growl"],
                     clip_names=["Growl_A", "Growl_B", "Growl_Fill"]),
            ALSTrack(name="LEAD", track_type="midi", color=COLOR_CYAN,
                     volume_db=-4, device_names=["Serum2_Lead"],
                     clip_names=["Lead_Melody", "Lead_Stab"]),
            ALSTrack(name="PAD", track_type="midi", color=COLOR_BLUE,
                     volume_db=-6, device_names=["Serum2_Pad"],
                     clip_names=["Pad_Intro", "Pad_Breakdown"]),
            ALSTrack(name="ARP", track_type="midi", color=COLOR_GREEN,
                     volume_db=-5, device_names=["Serum2_Arp"],
                     clip_names=["Arp_Rise", "Arp_Drop"]),
            ALSTrack(name="DRUMS", track_type="midi", color=COLOR_WHITE,
                     volume_db=-1, midi_channel=9,
                     clip_names=["Drums_Drop", "Drums_Build", "Drums_Fill"]),
            ALSTrack(name="FX", track_type="audio", color=COLOR_PURPLE,
                     volume_db=-8,
                     clip_names=["Riser", "Impact", "Downlifter"]),
            ALSTrack(name="REVERB", track_type="return", color=COLOR_BLUE,
                     volume_db=-10),
            ALSTrack(name="DELAY", track_type="return", color=COLOR_GREEN,
                     volume_db=-12),
            ALSTrack(name="SIDECHAIN", track_type="return", color=COLOR_RED,
                     volume_db=-6),
        ],
        scenes=[
            ALSScene(name="INTRO", tempo=150.0),
            ALSScene(name="BUILD_1", tempo=150.0),
            ALSScene(name="DROP_1", tempo=150.0),
            ALSScene(name="BREAKDOWN", tempo=150.0),
            ALSScene(name="BUILD_2", tempo=150.0),
            ALSScene(name="DROP_2", tempo=150.0),
            ALSScene(name="BRIDGE", tempo=150.0),
            ALSScene(name="DROP_3_VIP", tempo=150.0),
            ALSScene(name="OUTRO", tempo=150.0),
        ],
        notes="Generated by DUBFORGE -- Subtronics weapon template",
    )


def emotive_melodic_session() -> ALSProject:
    """Emotive melodic dubstep session template."""
    return ALSProject(
        name="DUBFORGE_EMOTIVE",
        bpm=140.0,
        tracks=[
            ALSTrack(name="SUB", track_type="midi", color=COLOR_RED,
                     volume_db=0, device_names=["PSBS_Sub"]),
            ALSTrack(name="BASS", track_type="midi", color=COLOR_ORANGE,
                     volume_db=-2, device_names=["Serum2_Bass"]),
            ALSTrack(name="CHORDS", track_type="midi", color=COLOR_CYAN,
                     volume_db=-4, device_names=["Serum2_Chords"]),
            ALSTrack(name="MELODY", track_type="midi", color=COLOR_GREEN,
                     volume_db=-3, device_names=["Serum2_Lead"]),
            ALSTrack(name="VOCAL_CHOP", track_type="audio", color=COLOR_PINK,
                     volume_db=-5),
            ALSTrack(name="PADS", track_type="midi", color=COLOR_BLUE,
                     volume_db=-6, device_names=["Serum2_Pad"]),
            ALSTrack(name="DRUMS", track_type="midi", color=COLOR_WHITE,
                     volume_db=-1, midi_channel=9),
            ALSTrack(name="PERC", track_type="audio", color=COLOR_YELLOW,
                     volume_db=-8),
            ALSTrack(name="REVERB", track_type="return", color=COLOR_BLUE,
                     volume_db=-8),
            ALSTrack(name="DELAY", track_type="return", color=COLOR_GREEN,
                     volume_db=-10),
        ],
        scenes=[
            ALSScene(name="INTRO", tempo=140.0),
            ALSScene(name="VERSE", tempo=140.0),
            ALSScene(name="BUILD", tempo=140.0),
            ALSScene(name="DROP", tempo=140.0),
            ALSScene(name="BREAKDOWN", tempo=140.0),
            ALSScene(name="BUILD_2", tempo=140.0),
            ALSScene(name="DROP_2", tempo=140.0),
            ALSScene(name="OUTRO", tempo=140.0),
        ],
        notes="Generated by DUBFORGE -- Emotive melodic template",
    )


ALL_ALS_TEMPLATES: dict[str, Callable[[], ALSProject]] = {}


def hybrid_fractal_session() -> ALSProject:
    """Hybrid fractal dubstep session with phi-ratio track levels."""
    tracks = []
    track_defs = [
        ("SUB", "midi", COLOR_RED),
        ("MID_BASS_L", "midi", COLOR_ORANGE),
        ("MID_BASS_R", "midi", COLOR_ORANGE),
        ("GROWL_1", "midi", COLOR_YELLOW),
        ("GROWL_2", "midi", COLOR_YELLOW),
        ("REESE", "midi", COLOR_RED),
        ("LEAD", "midi", COLOR_CYAN),
        ("CHORDS", "midi", COLOR_BLUE),
        ("ARP", "midi", COLOR_GREEN),
        ("PAD", "midi", COLOR_BLUE),
        ("DRUMS", "midi", COLOR_WHITE),
        ("PERC", "audio", COLOR_PURPLE),
        ("FX", "audio", COLOR_PINK),
    ]

    for i, (name, ttype, color) in enumerate(track_defs):
        vol = -i * (1.0 / PHI)
        tracks.append(ALSTrack(name=name, track_type=ttype, color=color,
                               volume_db=round(vol, 1)))

    tracks.extend([
        ALSTrack(name="VERB_SHORT", track_type="return", color=COLOR_BLUE,
                 volume_db=-8),
        ALSTrack(name="VERB_LONG", track_type="return", color=COLOR_BLUE,
                 volume_db=-12),
        ALSTrack(name="DELAY_1_4", track_type="return", color=COLOR_GREEN,
                 volume_db=-10),
        ALSTrack(name="DELAY_PHI", track_type="return", color=COLOR_GREEN,
                 volume_db=-14),
        ALSTrack(name="SIDECHAIN", track_type="return", color=COLOR_RED,
                 volume_db=-6),
    ])

    return ALSProject(
        name="DUBFORGE_HYBRID_FRACTAL",
        bpm=150.0,
        tracks=tracks,
        scenes=[
            ALSScene(name="INTRO"),
            ALSScene(name="BUILD_A"),
            ALSScene(name="DROP_A"),
            ALSScene(name="BREAKDOWN"),
            ALSScene(name="BUILD_B"),
            ALSScene(name="DROP_B"),
            ALSScene(name="BRIDGE"),
            ALSScene(name="DROP_VIP"),
            ALSScene(name="BUILD_C"),
            ALSScene(name="DROP_FINAL"),
            ALSScene(name="OUTRO"),
        ],
        notes="Generated by DUBFORGE -- Hybrid fractal phi-ratio template",
    )


def phase3_mixing_session() -> ALSProject:
    """Audio-only Phase 3 mix session for importing arrangement stems."""
    tracks = [
        ALSTrack(name="DRUMS", track_type="audio", color=COLOR_WHITE,
                 volume_db=-2.0, pan=0.0),
        ALSTrack(name="SUB", track_type="audio", color=COLOR_RED,
                 volume_db=-4.0, pan=0.0),
        ALSTrack(name="BASS", track_type="audio", color=COLOR_ORANGE,
                 volume_db=-3.0, pan=0.0),
        ALSTrack(name="MUSIC", track_type="audio", color=COLOR_CYAN,
                 volume_db=-5.0, pan=0.0),
        ALSTrack(name="LEADS", track_type="audio", color=COLOR_GREEN,
                 volume_db=-5.5, pan=0.12),
        ALSTrack(name="VOCALS", track_type="audio", color=COLOR_PINK,
                 volume_db=-6.0, pan=-0.12),
        ALSTrack(name="FX", track_type="audio", color=COLOR_YELLOW,
                 volume_db=-7.0, pan=0.0),
        ALSTrack(name="PARALLEL_DRUMS", track_type="audio", color=COLOR_PURPLE,
                 volume_db=-10.0, pan=0.0),
        ALSTrack(name="REVERB", track_type="return", color=COLOR_BLUE,
                 volume_db=-10.0),
        ALSTrack(name="DELAY", track_type="return", color=COLOR_GREEN,
                 volume_db=-12.0),
        ALSTrack(name="PARALLEL_COMP", track_type="return", color=COLOR_ORANGE,
                 volume_db=-9.0),
    ]
    return ALSProject(
        name="DUBFORGE_PHASE3_MIXING",
        bpm=150.0,
        tracks=tracks,
        scenes=[
            ALSScene(name="IMPORT"),
            ALSScene(name="ANALYZE"),
            ALSScene(name="BALANCE"),
            ALSScene(name="GLUE"),
            ALSScene(name="PRINT"),
        ],
        notes=(
            "Generated by DUBFORGE -- Phase 3 mixing session with audio-only "
            "stem tracks, ready for gain staging, EQ, dynamics, and spatial work"
        ),
    )


def phase4_mastering_session() -> ALSProject:
    """Audio-focused Phase 4 mastering session for premaster import."""
    tracks = [
        ALSTrack(name="PREMASTER", track_type="audio", color=COLOR_WHITE,
                 volume_db=-6.0, pan=0.0),
        ALSTrack(name="REFERENCE_A", track_type="audio", color=COLOR_CYAN,
                 volume_db=-8.0, pan=-0.1),
        ALSTrack(name="REFERENCE_B", track_type="audio", color=COLOR_GREEN,
                 volume_db=-8.0, pan=0.1),
        ALSTrack(name="MASTER_PRINT", track_type="audio", color=COLOR_YELLOW,
                 volume_db=-3.0, pan=0.0),
        ALSTrack(name="MASTER_FX", track_type="return", color=COLOR_PURPLE,
                 volume_db=-12.0),
    ]
    return ALSProject(
        name="DUBFORGE_PHASE4_MASTERING",
        bpm=150.0,
        tracks=tracks,
        scenes=[
            ALSScene(name="IMPORT"),
            ALSScene(name="EQ"),
            ALSScene(name="COMP"),
            ALSScene(name="LIMIT"),
            ALSScene(name="PRINT"),
        ],
        notes=(
            "Generated by DUBFORGE -- Phase 4 mastering session for premaster "
            "import, reference comparison, and final print"
        ),
    )


# Populate template registry
ALL_ALS_TEMPLATES = {
    "weapon":         dubstep_weapon_session,
    "emotive":        emotive_melodic_session,
    "hybrid_fractal": hybrid_fractal_session,
}

ADDITIONAL_ALS_TEMPLATES: dict[str, Callable[[], ALSProject]] = {
    "phase3_mixing":  phase3_mixing_session,
    "phase4_mastering": phase4_mastering_session,
}


# ═══════════════════════════════════════════════════════════════════════════
# STEM AUTO-POPULATE
# ═══════════════════════════════════════════════════════════════════════════

def auto_populate_stems(project: ALSProject, stem_dir: str = "output/wavetables",
                        output_dir: str = "output/ableton") -> str:
    """Generate an ALS project auto-populated with rendered stem references."""
    stem_path = Path(stem_dir)
    wav_files = sorted(stem_path.rglob("*.wav")) if stem_path.exists() else []

    stem_map: dict[str, list[str]] = {}
    for wav in wav_files:
        stem_name = wav.stem.lower()
        stem_map.setdefault(stem_name, []).append(str(wav))

    enriched_tracks: list[ALSTrack] = []
    for track in project.tracks:
        t = ALSTrack(
            name=track.name, track_type=track.track_type, color=track.color,
            volume_db=track.volume_db, pan=track.pan, mute=track.mute,
            solo=track.solo, armed=track.armed, midi_channel=track.midi_channel,
            device_names=list(track.device_names),
            clip_names=list(track.clip_names),
            clip_paths=list(track.clip_paths),
        )
        if track.track_type == "audio":
            key_lower = track.name.lower()
            for sname, spaths in stem_map.items():
                if key_lower in sname or sname in key_lower:
                    t.clip_names.extend(Path(p).stem for p in spaths[:4])
                    t.clip_paths.extend(spaths[:4])
                    break
        enriched_tracks.append(t)

    enriched = ALSProject(
        name=project.name + "_STEMS", bpm=project.bpm,
        time_sig_num=project.time_sig_num, time_sig_den=project.time_sig_den,
        tracks=enriched_tracks, scenes=list(project.scenes),
        master_volume_db=project.master_volume_db,
        notes=project.notes + " | Stems auto-populated",
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    als_path = str(out / f"{enriched.name}.als")
    write_als(enriched, als_path)
    write_als_json(enriched, str(out / f"{enriched.name}_structure.json"))
    return als_path


def _stem_dir_for_template(output_dir: str, template_name: str) -> str:
    """Choose the phase-appropriate source directory for stem auto-population."""
    root = Path(output_dir)
    if template_name == "phase3_mixing":
        return str(root / "stems" / "phase2")
    if template_name == "phase4_mastering":
        return str(root / "stems" / "phase3")
    return str(root / "wavetables")


def export_all_als(output_dir: str = "output") -> list[str]:
    """Generate all ALS templates + stem-populated variants."""
    paths: list[str] = []
    out_dir = Path(output_dir) / "ableton"
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = {**ALL_ALS_TEMPLATES, **ADDITIONAL_ALS_TEMPLATES}

    for name, gen_fn in templates.items():
        project = gen_fn()
        als_path = str(out_dir / f"{project.name}.als")
        write_als(project, als_path)
        paths.append(als_path)
        json_path = str(out_dir / f"{project.name}_structure.json")
        write_als_json(project, json_path)
        stem_path = auto_populate_stems(project,
                                        _stem_dir_for_template(output_dir, name),
                                        str(out_dir))
        paths.append(stem_path)

    return paths


def main() -> None:
    paths = export_all_als()
    print(f"ALS Generator complete -- {len(paths)} files "
          f"({len(ALL_ALS_TEMPLATES) + len(ADDITIONAL_ALS_TEMPLATES)} templates + stems).")


if __name__ == "__main__":
    main()
