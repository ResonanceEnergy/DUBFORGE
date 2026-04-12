"""
DUBFORGE Engine — Ableton Live Set (.als) Generator

Generates valid Ableton Live 11/12 set files (.als) from DUBFORGE
session templates.  An .als file is a gzip-compressed XML document.

Outputs:
    output/ableton/*.als — Ableton Live set files
"""

from __future__ import annotations

import gzip
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engine.config_loader import PHI
from engine.log import get_logger

_log = get_logger("dubforge.als_generator")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

ALS_CREATOR = "Ableton Live 12.1d1"
ALS_SCHEMA_VERSION = "12.0_12117"  # Ableton Live 12 schema (MAJOR.MINOR_BUILD)
DEFAULT_BPM = 150.0
DEFAULT_TIME_SIG_NUM = 4
DEFAULT_TIME_SIG_DEN = 4


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
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
    clip_names: list[str] = field(default_factory=list)
    clip_paths: list[str] = field(default_factory=list)  # abs paths to WAV files
    send_levels: list[float] = field(default_factory=list)  # send amounts per return (0.0-1.0)
    arrangement_clips: list = field(default_factory=list)  # list[ALSClipInfo] for positioned clips
    automations: list = field(default_factory=list)  # list[ALSAutomation] envelopes


@dataclass
class ALSScene:
    """Represents a scene (row of clips)."""
    name: str
    tempo: float = DEFAULT_BPM
    time_sig: tuple[int, int] = (4, 4)


@dataclass
class ALSWarpMarker:
    """Warp marker for audio time-stretching."""
    sec_time: float   # position in source audio (seconds)
    beat_time: float  # position in arrangement (beats)


@dataclass
class ALSClipInfo:
    """Extended clip placement info for arrangement view."""
    path: str                    # absolute WAV file path
    start_beat: float = 0.0      # arrangement position (beats)
    length_beats: float = 0.0    # clip duration (0 = auto from project)
    warp_mode: int = 0           # 0=Beats,1=Tones,2=Texture,3=RePitch,4=Complex,6=ComplexPro
    warp_markers: list[ALSWarpMarker] = field(default_factory=list)
    loop: bool = False
    loop_start: float = 0.0
    loop_end: float = 0.0
    gain: float = 1.0            # 0.0-1.0
    name: str = ""


@dataclass
class ALSAutomationPoint:
    """A single automation breakpoint."""
    time: float   # beats
    value: float  # parameter value
    curve: float = 0.0  # -1.0 to 1.0 (0=linear, neg=log, pos=exp)


@dataclass
class ALSAutomation:
    """Automation envelope for a track parameter."""
    parameter_name: str   # e.g. "Volume", "Pan", "Send 0"
    points: list[ALSAutomationPoint] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATION SHAPE GENERATORS (insights 102, 116-121)
# ═══════════════════════════════════════════════════════════════════════════

import math as _math


def make_sine_automation(param: str, start_beat: float, end_beat: float,
                         min_val: float = 0.0, max_val: float = 1.0,
                         cycles: int = 1, resolution: int = 32) -> ALSAutomation:
    """Sine-shaped automation (insight 116 — tremolo/LFO)."""
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
    """Sawtooth automation (insight 117 — filter sweeps)."""
    pts = []
    beats_per_cycle = (end_beat - start_beat) / cycles
    for c in range(cycles):
        cycle_start = start_beat + c * beats_per_cycle
        for i in range(resolution // cycles):
            frac = i / (resolution // cycles)
            t = cycle_start + beats_per_cycle * frac
            v = min_val + (max_val - min_val) * frac
            pts.append(ALSAutomationPoint(time=t, value=v))
        pts.append(ALSAutomationPoint(time=cycle_start + beats_per_cycle, value=min_val))
    return ALSAutomation(parameter_name=param, points=pts)


def make_ramp_automation(param: str, start_beat: float, end_beat: float,
                         start_val: float = 0.0, end_val: float = 1.0,
                         curve: float = 0.0) -> ALSAutomation:
    """Linear or curved ramp (insight 123 — log/exp curves)."""
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
    """LP filter build sweep (insight 21 — LP automation in builds)."""
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


@dataclass
class ALSCuePoint:
    """Arrangement view cue point / locator."""
    name: str
    time: float   # beats


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
    cue_points: list = field(default_factory=list)  # list[ALSCuePoint]


# ═══════════════════════════════════════════════════════════════════════════
# XML BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _set_val(parent: ET.Element, tag: str, value: str) -> ET.Element:
    """Create element with Value attribute (Ableton's pattern)."""
    elem = ET.SubElement(parent, tag, Value=str(value))
    return elem


def _build_transport(root: ET.Element, project: ALSProject) -> None:
    """Set tempo, time signature, and transport settings."""
    transport = ET.SubElement(root, "Transport")
    tempo = ET.SubElement(transport, "Tempo")
    _set_val(tempo, "Manual", str(project.bpm))
    _set_val(tempo, "AutomationTarget", "0")

    time_sig = ET.SubElement(transport, "TimeSignature")
    ts_val = ET.SubElement(time_sig, "TimeSignatures")
    ts_event = ET.SubElement(ts_val, "RemoteableTimeSignature")
    _set_val(ts_event, "Numerator", str(project.time_sig_num))
    _set_val(ts_event, "Denominator", str(project.time_sig_den))


def _build_sends(mixer_elem: ET.Element, send_levels: list[float]) -> None:
    """Build send level XML elements in a mixer."""
    if not send_levels:
        return
    sends = ET.SubElement(mixer_elem, "Sends")
    for i, level in enumerate(send_levels):
        send = ET.SubElement(sends, "TrackSendHolder", Id=str(i))
        send_val = ET.SubElement(send, "Send")
        _set_val(send_val, "Manual", str(round(level, 4)))
        _set_val(send, "Active", "true")


def _build_automation_envelopes(parent: ET.Element,
                                automations: list) -> None:
    """Build automation envelope XML elements on a track."""
    if not automations:
        return
    envelopes_elem = ET.SubElement(parent, "AutomationEnvelopes")
    envs = ET.SubElement(envelopes_elem, "Envelopes")
    for auto_id, auto in enumerate(automations):
        env = ET.SubElement(envs, "AutomationEnvelope", Id=str(auto_id))
        _set_val(env, "ParameterName", auto.parameter_name)
        automation = ET.SubElement(env, "Automation")
        events = ET.SubElement(automation, "Events")
        for pt in auto.points:
            attrs = {
                "Id": str(int(pt.time * 100)),
                "Time": str(round(pt.time, 4)),
                "Value": str(round(pt.value, 6)),
            }
            if pt.curve != 0.0:
                attrs["CurveControl1X"] = str(round(0.5, 4))
                attrs["CurveControl1Y"] = str(round(pt.curve, 4))
                attrs["CurveControl2X"] = str(round(0.5, 4))
                attrs["CurveControl2Y"] = str(round(pt.curve, 4))
            ET.SubElement(events, "FloatEvent", **attrs)  # type: ignore[arg-type]


def _build_midi_track(parent: ET.Element, track: ALSTrack,
                      track_id: int) -> ET.Element:
    """Build a MIDI track XML element."""
    t = ET.SubElement(parent, "MidiTrack", Id=str(track_id))

    # Name
    name_elem = ET.SubElement(t, "Name")
    _set_val(name_elem, "EffectiveName", track.name)
    _set_val(name_elem, "UserName", track.name)

    # Color
    _set_val(t, "Color", str(track.color))

    # Mixer
    mixer = ET.SubElement(t, "DeviceChain")
    mixer_elem = ET.SubElement(mixer, "Mixer")

    volume = ET.SubElement(mixer_elem, "Volume")
    _set_val(volume, "Manual", str(track.volume_db))
    pan = ET.SubElement(mixer_elem, "Pan")
    _set_val(pan, "Manual", str(track.pan))
    _set_val(mixer_elem, "SoloSink", str(track.solo).lower())

    # Send routing
    _build_sends(mixer_elem, track.send_levels)

    # Armed
    _set_val(t, "TrackArmed", str(track.armed).lower())

    # Placeholder clip slots
    main_seq = ET.SubElement(t, "MainSequencer")
    clip_slots = ET.SubElement(main_seq, "ClipSlotList")
    for i, clip_name in enumerate(track.clip_names):
        slot = ET.SubElement(clip_slots, "ClipSlot", Id=str(i))
        clip_elem = ET.SubElement(slot, "ClipSlot")
        name_el = ET.SubElement(clip_elem, "Name")
        _set_val(name_el, "Value", clip_name)

    # Device references
    devices = ET.SubElement(mixer, "DeviceChainList")
    for dev_name in track.device_names:
        dev = ET.SubElement(devices, "PluginDevice")
        _set_val(dev, "ClassName", dev_name)

    # Automation envelopes
    _build_automation_envelopes(t, track.automations)

    return t


def _build_audio_track(parent: ET.Element, track: ALSTrack,
                       track_id: int,
                       total_beats: float = 0.0,
                       als_dir: str = "") -> ET.Element:
    """Build an audio track XML element with AudioClip references."""
    t = ET.SubElement(parent, "AudioTrack", Id=str(track_id))

    name_elem = ET.SubElement(t, "Name")
    _set_val(name_elem, "EffectiveName", track.name)
    _set_val(name_elem, "UserName", track.name)
    _set_val(t, "Color", str(track.color))

    mixer = ET.SubElement(t, "DeviceChain")
    mixer_elem = ET.SubElement(mixer, "Mixer")
    volume = ET.SubElement(mixer_elem, "Volume")
    _set_val(volume, "Manual", str(track.volume_db))
    pan = ET.SubElement(mixer_elem, "Pan")
    _set_val(pan, "Manual", str(track.pan))

    # Send routing
    _build_sends(mixer_elem, track.send_levels)

    # Device references
    if track.device_names:
        devices = ET.SubElement(mixer, "DeviceChainList")
        for dev_name in track.device_names:
            dev = ET.SubElement(devices, "PluginDevice")
            _set_val(dev, "ClassName", dev_name)

    # Arrangement clips — use ALSClipInfo if available, else legacy clip_paths
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
            })
    elif track.clip_paths:
        for clip_path in track.clip_paths:
            clip_sources.append({
                "path": clip_path,
                "start_beat": 0.0,
                "length_beats": total_beats if total_beats > 0 else 288.0,
                "warp_mode": 0,
                "warp_markers": [],
                "loop": False,
                "loop_start": 0.0,
                "loop_end": 0.0,
                "gain": 1.0,
                "name": Path(clip_path).stem,
            })

    if clip_sources:
        arranger = ET.SubElement(t, "ArrangerAutomation")
        events = ET.SubElement(arranger, "Events")
        for clip_id, cs in enumerate(clip_sources):
            abs_path = str(Path(cs["path"]).resolve())
            file_name = Path(cs["path"]).name

            # Compute relative path from ALS file location
            rel_path = abs_path
            if als_dir:
                try:
                    rel_path = str(Path(abs_path).relative_to(Path(als_dir)))
                except ValueError:
                    rel_path = abs_path

            end_beats = cs["start_beat"] + cs["length_beats"]
            clip = ET.SubElement(events, "AudioClip",
                                 Id=str(clip_id),
                                 Time=str(round(cs["start_beat"], 4)))
            _set_val(clip, "CurrentStart", str(round(cs["start_beat"], 4)))
            _set_val(clip, "CurrentEnd", str(round(end_beats, 4)))
            clip_name_el = ET.SubElement(clip, "Name")
            _set_val(clip_name_el, "Value", cs["name"])
            _set_val(clip, "Disabled", "false")

            # Warp mode
            _set_val(clip, "WarpMode", str(cs["warp_mode"]))
            _set_val(clip, "Warping", "true")

            # Gain
            _set_val(clip, "SampleVolume", str(round(cs["gain"], 4)))

            # Loop settings
            if cs["loop"]:
                loop_elem = ET.SubElement(clip, "Loop")
                _set_val(loop_elem, "LoopOn", "true")
                _set_val(loop_elem, "LoopStart",
                         str(round(cs["loop_start"], 4)))
                _set_val(loop_elem, "LoopEnd",
                         str(round(cs["loop_end"] or cs["length_beats"], 4)))

            # Warp markers
            if cs["warp_markers"]:
                warp_elem = ET.SubElement(clip, "WarpMarkers")
                for wm in cs["warp_markers"]:
                    ET.SubElement(warp_elem, "WarpMarker",
                                  SecTime=str(round(wm.sec_time, 6)),
                                  BeatTime=str(round(wm.beat_time, 4)))

            # Sample reference
            sample_ref = ET.SubElement(clip, "SampleRef")
            file_ref = ET.SubElement(sample_ref, "FileRef")
            _set_val(file_ref, "HasRelativePath", "true")
            _set_val(file_ref, "RelativePath", rel_path)
            _set_val(file_ref, "Path", abs_path)
            _set_val(file_ref, "Name", file_name)
            _set_val(file_ref, "Type", "1")

    # Automation envelopes
    _build_automation_envelopes(t, track.automations)

    return t


def _build_return_track(parent: ET.Element, track: ALSTrack,
                        track_id: int) -> ET.Element:
    """Build a return track XML element."""
    t = ET.SubElement(parent, "ReturnTrack", Id=str(track_id))

    name_elem = ET.SubElement(t, "Name")
    _set_val(name_elem, "EffectiveName", track.name)
    _set_val(name_elem, "UserName", track.name)
    _set_val(t, "Color", str(track.color))

    mixer = ET.SubElement(t, "DeviceChain")
    mixer_elem = ET.SubElement(mixer, "Mixer")
    volume = ET.SubElement(mixer_elem, "Volume")
    _set_val(volume, "Manual", str(track.volume_db))

    # Send routing (returns can send to other returns)
    _build_sends(mixer_elem, track.send_levels)

    # Device references
    if track.device_names:
        devices = ET.SubElement(mixer, "DeviceChainList")
        for dev_name in track.device_names:
            dev = ET.SubElement(devices, "PluginDevice")
            _set_val(dev, "ClassName", dev_name)

    # Automation envelopes
    _build_automation_envelopes(t, track.automations)

    return t


def build_als_xml(project: ALSProject,
                  als_path: str = "") -> ET.Element:
    """Build the complete Ableton Live set XML tree."""
    root = ET.Element("Ableton",
                      MajorVersion="5",
                      MinorVersion=ALS_SCHEMA_VERSION,
                      SchemaChangeCount="10",
                      Creator=ALS_CREATOR,
                      Revision="")

    live_set = ET.SubElement(root, "LiveSet")

    # Transport
    _build_transport(live_set, project)

    # Compute total beats for arrangement clip sizing
    total_beats = len(project.scenes) * project.time_sig_num * 8.0
    als_dir = str(Path(als_path).parent.resolve()) if als_path else ""

    # Tracks
    tracks_elem = ET.SubElement(live_set, "Tracks")
    track_id = 0
    for track in project.tracks:
        if track.track_type == "midi":
            _build_midi_track(tracks_elem, track, track_id)
        elif track.track_type == "audio":
            _build_audio_track(tracks_elem, track, track_id,
                               total_beats, als_dir)
        elif track.track_type == "return":
            _build_return_track(tracks_elem, track, track_id)
        track_id += 1

    # Scenes
    scenes_elem = ET.SubElement(live_set, "Scenes")
    for i, scene in enumerate(project.scenes):
        s = ET.SubElement(scenes_elem, "Scene", Id=str(i))
        name_el = ET.SubElement(s, "Name")
        _set_val(name_el, "Value", scene.name)

    # Master track
    master = ET.SubElement(live_set, "MasterTrack")
    master_mixer = ET.SubElement(master, "DeviceChain")
    mixer_elem = ET.SubElement(master_mixer, "Mixer")
    vol = ET.SubElement(mixer_elem, "Volume")
    _set_val(vol, "Manual", str(project.master_volume_db))

    # Annotation
    if project.notes:
        annotation = ET.SubElement(live_set, "Annotation")
        _set_val(annotation, "Value", project.notes)

    # Cue points / locators
    if project.cue_points:
        cues = ET.SubElement(live_set, "CuePoints")
        for i, cp in enumerate(project.cue_points):
            cue = ET.SubElement(cues, "CuePoint", Id=str(i))
            _set_val(cue, "Time", str(round(cp.time, 4)))
            name_el = ET.SubElement(cue, "Name")
            _set_val(name_el, "Value", cp.name)

    return root


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
            # Return tracks
            ALSTrack(name="REVERB", track_type="return", color=COLOR_BLUE, volume_db=-10),
            ALSTrack(name="DELAY", track_type="return", color=COLOR_GREEN, volume_db=-12),
            ALSTrack(name="SIDECHAIN", track_type="return", color=COLOR_RED, volume_db=-6),
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
        notes="Generated by DUBFORGE — Subtronics weapon template",
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
            ALSTrack(name="PERC", track_type="audio", color=COLOR_YELLOW, volume_db=-8),
            ALSTrack(name="REVERB", track_type="return", color=COLOR_BLUE, volume_db=-8),
            ALSTrack(name="DELAY", track_type="return", color=COLOR_GREEN, volume_db=-10),
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
        notes="Generated by DUBFORGE — Emotive melodic template",
    )


def hybrid_fractal_session() -> ALSProject:
    """Hybrid fractal dubstep session with phi-ratio track levels."""
    tracks = []
    # Main tracks with phi-ratio volume decay
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
        vol = -i * (1.0 / PHI)  # Phi-decay volume curve
        tracks.append(ALSTrack(name=name, track_type=ttype, color=color,
                               volume_db=round(vol, 1)))

    # Returns
    tracks.extend([
        ALSTrack(name="VERB_SHORT", track_type="return", color=COLOR_BLUE, volume_db=-8),
        ALSTrack(name="VERB_LONG", track_type="return", color=COLOR_BLUE, volume_db=-12),
        ALSTrack(name="DELAY_1_4", track_type="return", color=COLOR_GREEN, volume_db=-10),
        ALSTrack(name="DELAY_PHI", track_type="return", color=COLOR_GREEN, volume_db=-14),
        ALSTrack(name="SIDECHAIN", track_type="return", color=COLOR_RED, volume_db=-6),
    ])

    return ALSProject(
        name="DUBFORGE_HYBRID_FRACTAL",
        bpm=150.0,
        tracks=tracks,
        scenes=[
            ALSScene(name="INTRO"),
            ALSScene(name="BUILD_A"),
            ALSScene(name="DROP_A"),
            ALSScene(name="FILL_FIBONACCI"),
            ALSScene(name="DROP_B_HALFTIME"),
            ALSScene(name="BREAKDOWN"),
            ALSScene(name="BUILD_B"),
            ALSScene(name="DROP_C_WEAPON"),
            ALSScene(name="DROP_D_VIP"),
            ALSScene(name="OUTRO"),
        ],
        notes="Generated by DUBFORGE — Hybrid fractal template with phi-ratio levels",
    )


ALL_ALS_TEMPLATES = {
    "weapon":         dubstep_weapon_session,
    "emotive":        emotive_melodic_session,
    "hybrid_fractal": hybrid_fractal_session,
}


# ═══════════════════════════════════════════════════════════════════════════
# STEM AUTO-POPULATE
# ═══════════════════════════════════════════════════════════════════════════

def auto_populate_stems(project: ALSProject, stem_dir: str = "output/wavetables",
                        output_dir: str = "output/ableton") -> str:
    """Generate an ALS project auto-populated with rendered stem references.

    Scans *stem_dir* for .wav files and assigns them to matching audio tracks
    in the project template.  Returns the path to the written .als file.
    """
    stem_path = Path(stem_dir)
    wav_files = sorted(stem_path.rglob("*.wav")) if stem_path.exists() else []

    # Build a mapping from track name fragments to wav files
    stem_map: dict[str, list[str]] = {}
    for wav in wav_files:
        stem_name = wav.stem.lower()
        stem_map.setdefault(stem_name, []).append(str(wav))

    # Enrich audio tracks with discovered stems
    enriched_tracks: list[ALSTrack] = []
    for track in project.tracks:
        t = ALSTrack(
            name=track.name,
            track_type=track.track_type,
            color=track.color,
            volume_db=track.volume_db,
            pan=track.pan,
            mute=track.mute,
            solo=track.solo,
            armed=track.armed,
            midi_channel=track.midi_channel,
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
        name=project.name + "_STEMS",
        bpm=project.bpm,
        time_sig_num=project.time_sig_num,
        time_sig_den=project.time_sig_den,
        tracks=enriched_tracks,
        scenes=list(project.scenes),
        master_volume_db=project.master_volume_db,
        notes=project.notes + " | Stems auto-populated",
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    als_path = str(out / f"{enriched.name}.als")
    write_als(enriched, als_path)
    write_als_json(enriched, str(out / f"{enriched.name}_structure.json"))
    return als_path


def export_all_als(output_dir: str = "output") -> list[str]:
    """Generate all ALS templates + stem-populated variants."""
    paths: list[str] = []
    out_dir = Path(output_dir) / "ableton"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, gen_fn in ALL_ALS_TEMPLATES.items():
        project = gen_fn()
        als_path = str(out_dir / f"DUBFORGE_{name}.als")
        write_als(project, als_path)
        paths.append(als_path)

        json_path = str(out_dir / f"DUBFORGE_{name}_structure.json")
        write_als_json(project, json_path)

        # Stem-populated variant
        stem_path = auto_populate_stems(project, str(Path(output_dir) / "wavetables"),
                                        str(out_dir))
        paths.append(stem_path)

    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    paths = export_all_als()
    print(f"ALS Generator complete — {len(paths)} files ({len(ALL_ALS_TEMPLATES)} templates + stems).")


if __name__ == "__main__":
    main()
