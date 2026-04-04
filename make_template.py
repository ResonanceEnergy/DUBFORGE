#!/usr/bin/env python3
"""DUBFORGE — Base Template Generator

Reads `configs/base_template.yaml` (or a track-specific override) and produces
a fully-loaded Ableton Live 12 ALS with:
  - 15 MIDI tracks + 2 returns (all pre-wired to Serum 2)
  - Auto-generated MIDI per track role (bass/drums/lead/etc.)
  - Full automation (filter sweeps, LFOs, sends, sidechain)
  - Drum Rack with 11 pads and choke groups
  - Serum 2 VST3 state embedded (Ableton-native XferJson)
  - Fibonacci-structured arrangement with cue markers
  - Pre-mixed volumes, pans, and send routing

Workflow (ill.Gates Dojo + Subtronics):
  1. Load base_template.yaml or track-specific override
  2. Resolve arrangement sections with bar offsets
  3. Generate MIDI notes per track role + section type
  4. Build automation envelopes per track config
  5. Assemble ALSProject with Serum 2 state + Drum Rack
  6. Export .als + .mid

Usage:
    python make_template.py                        # base template
    python make_template.py --name "CYCLOPS FURY"  # custom name
    python make_template.py --config configs/my_track.yaml
    python make_template.py --bpm 145 --key E_minor
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import field
from pathlib import Path

import yaml

# ═══════════════════════════════════════════════════════════════════════════
# Engine imports
# ═══════════════════════════════════════════════════════════════════════════

from engine.als_generator import (
    ALSAutomation,
    ALSAutomationPoint,
    ALSCuePoint,
    ALSDrumPad,
    ALSMidiClip,
    ALSMidiNote,
    ALSProject,
    ALSScene,
    ALSTrack,
    make_lp_sweep_automation,
    make_ramp_automation,
    make_sawtooth_automation,
    make_section_send_automation,
    make_sine_automation,
    write_als,
)
from engine.config_loader import PHI
from engine.log import get_logger

_log = get_logger("dubforge.template")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "base_template.yaml"
OUTPUT_DIR = PROJECT_ROOT / "output"


# ═══════════════════════════════════════════════════════════════════════════
# NOTE / PITCH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

_NOTE_NAMES = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}
_ACCIDENTALS = {"b": -1, "#": 1, "s": 1}


def note_name_to_midi(name: str) -> int:
    """Convert e.g. 'D2', 'Bb3', 'F#4' to MIDI pitch."""
    i = 1
    base = _NOTE_NAMES.get(name[0].upper())
    if base is None:
        raise ValueError(f"Bad note name: {name}")
    acc = 0
    while i < len(name) and name[i] in _ACCIDENTALS:
        acc += _ACCIDENTALS[name[i]]
        i += 1
    octave = int(name[i:])
    return (octave + 2) * 12 + base + acc


def _humanize_vel(base_vel: int, beat_pos: float,
                  strength: float = 0.15) -> int:
    """PHI-based non-repeating velocity humanisation."""
    offset = math.sin(beat_pos * PHI * 2.0) * base_vel * strength
    return max(1, min(127, int(base_vel + offset)))


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG LOADER
# ═══════════════════════════════════════════════════════════════════════════

def load_config(path: Path, overrides: dict | None = None) -> dict:
    """Load YAML config with optional CLI overrides."""
    with open(path) as f:
        cfg = yaml.safe_load(f)

    if overrides:
        g = cfg.get("global", {})
        if "bpm" in overrides:
            g["bpm"] = overrides["bpm"]
        if "key" in overrides:
            g["key"] = overrides["key"]
        if "name" in overrides:
            cfg["template_name"] = overrides["name"]
        cfg["global"] = g

    return cfg


def resolve_arrangement(cfg: dict) -> list[dict]:
    """Add cumulative bar_start to each section."""
    sections = cfg["arrangement"]
    bar_offset = 0
    resolved = []
    for sec in sections:
        s = dict(sec)
        s["bar_start"] = bar_offset
        bar_offset += s["bars"]
        resolved.append(s)
    return resolved


# ═══════════════════════════════════════════════════════════════════════════
# CHORD PROGRESSION
# ═══════════════════════════════════════════════════════════════════════════

def build_chord_roots(cfg: dict) -> list[int]:
    """Resolve chord progression note names to MIDI pitches."""
    prog = cfg["global"]["chord_progression"]
    return [note_name_to_midi(n) for n in prog]


def build_chord_voicings(roots: list[int]) -> list[list[int]]:
    """Build minor triad voicings from roots, voiced at octave 3."""
    voicings = []
    for root in roots:
        # Raise root to octave 3 range for chords
        base = root + 24 if root < 48 else root + 12 if root < 60 else root
        # Minor triad: root, minor 3rd, perfect 5th
        voicings.append([base, base + 3, base + 7])
    return voicings


# ═══════════════════════════════════════════════════════════════════════════
# MIDI GENERATORS (per role)
# ═══════════════════════════════════════════════════════════════════════════

def _gen_drums(sections: list[dict], drum_patterns: dict,
               cfg: dict) -> list[ALSMidiNote]:
    """Generate drum patterns per section type."""
    KICK, SNARE, CLAP = 36, 38, 39
    HH_CL, HH_OP = 42, 46
    CRASH, RIDE = 49, 51
    PERC_1, PERC_2 = 56, 57

    notes: list[ALSMidiNote] = []

    for sec in sections:
        sec_type = sec["type"]
        pattern = drum_patterns.get(sec_type, drum_patterns.get("drop", {}))
        base_vel = pattern.get("base_velocity", 90)
        bar_start = sec["bar_start"]
        sec_bars = sec["bars"]

        for bar_off in range(sec_bars):
            bar = bar_start + bar_off
            beat_base = bar * 4.0

            # Kick
            for beat in pattern.get("kick", []):
                vel = _humanize_vel(base_vel, beat_base + beat)
                notes.append(ALSMidiNote(
                    pitch=KICK, time=beat_base + beat,
                    duration=0.5, velocity=vel))

            # Snare
            for beat in pattern.get("snare", []):
                vel = _humanize_vel(base_vel - 5, beat_base + beat)
                notes.append(ALSMidiNote(
                    pitch=SNARE, time=beat_base + beat,
                    duration=0.25, velocity=vel))

            # Closed hat
            for beat in pattern.get("hh_cl", []):
                vel = _humanize_vel(base_vel - 20, beat_base + beat)
                notes.append(ALSMidiNote(
                    pitch=HH_CL, time=beat_base + beat,
                    duration=0.25, velocity=vel))

            # Open hat
            for beat in pattern.get("hh_op", []):
                vel = _humanize_vel(base_vel - 15, beat_base + beat)
                notes.append(ALSMidiNote(
                    pitch=HH_OP, time=beat_base + beat,
                    duration=0.5, velocity=vel))

            # Perc
            for beat in pattern.get("perc_1", []):
                vel = _humanize_vel(base_vel - 25, beat_base + beat)
                notes.append(ALSMidiNote(
                    pitch=PERC_1, time=beat_base + beat,
                    duration=0.25, velocity=vel))

            # Snare roll in last bars (if specified)
            if pattern.get("snare_roll") and bar_off >= sec_bars - 2:
                for i in range(16):
                    t = beat_base + i * 0.25
                    vel = _humanize_vel(base_vel - 10 + i, t)
                    notes.append(ALSMidiNote(
                        pitch=SNARE, time=t, duration=0.125, velocity=vel))

        # Crash on first beat of drops
        if sec_type == "drop":
            notes.append(ALSMidiNote(
                pitch=CRASH, time=bar_start * 4.0,
                duration=2.0, velocity=110))

    return notes


def _gen_bass_role(sections: list[dict], roots: list[int],
                   role_cfg: dict, track_cfg: dict,
                   escalation_idx: int = 0) -> list[ALSMidiNote]:
    """Generic bass-layer MIDI: root per 2-bar chord cycle."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop"]))
    escalation = track_cfg.get("escalation", False)
    octave_off = (role_cfg.get("octave_offset", 0)) * 12
    vel = role_cfg.get("default_velocity", 100)
    dur = role_cfg.get("duration", 1.5)

    drop_count = 0
    for sec in sections:
        if sec["type"] == "drop":
            drop_count += 1
        if sec["type"] not in active:
            continue
        if escalation and sec["type"] == "drop" and drop_count <= 1:
            continue  # skip first drop for escalation tracks

        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(roots)
            root = roots[chord_idx] + octave_off
            beat = bar * 4.0
            notes.append(ALSMidiNote(
                pitch=root, time=beat,
                duration=dur, velocity=_humanize_vel(vel, beat)))

    return notes


def _gen_riddim(sections: list[dict], roots: list[int],
                cfg: dict, track_cfg: dict) -> list[ALSMidiNote]:
    """Riddim with 5 rhythmic variations cycled across drops."""
    variations = track_cfg.get("riddim_variations",
                               ["quarter", "stutter", "triplet", "bounce", "minimal"])
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop"]))
    vel = 100

    drop_idx = 0
    for sec in sections:
        if sec["type"] not in active:
            if sec["type"] == "drop":
                drop_idx += 1
            continue

        var = variations[drop_idx % len(variations)]
        drop_idx += 1

        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(roots)
            root = roots[chord_idx]
            beat_base = bar * 4.0

            if var == "quarter":
                hits = [0.0, 1.0, 2.0, 3.0]
            elif var == "stutter":
                hits = [0.0, 0.25, 1.0, 1.25, 2.0, 2.25, 3.0, 3.25]
            elif var == "triplet":
                hits = [0.0, 0.667, 1.333, 2.0, 2.667, 3.333]
            elif var == "bounce":
                hits = [0.0, 0.75, 1.5, 2.25, 3.0]
            else:  # minimal
                hits = [0.0, 2.0]

            for h in hits:
                notes.append(ALSMidiNote(
                    pitch=root, time=beat_base + h,
                    duration=0.25, velocity=_humanize_vel(vel, beat_base + h)))

    return notes


def _gen_lead(sections: list[dict], cfg: dict,
              track_cfg: dict) -> list[ALSMidiNote]:
    """Ascending 4-bar phrase repeated per active section."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop", "build"]))
    midi_rule = cfg.get("midi_rules", {}).get("lead", {})
    motif_names = midi_rule.get("notes", ["A3", "C4", "D4", "F4"])
    motif = [note_name_to_midi(n) for n in motif_names]
    vel = midi_rule.get("default_velocity", 95)

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            beat = bar * 4.0
            note_idx = bar_off % len(motif)
            notes.append(ALSMidiNote(
                pitch=motif[note_idx], time=beat,
                duration=3.0, velocity=_humanize_vel(vel, beat)))

    return notes


def _gen_counter(sections: list[dict], cfg: dict,
                 track_cfg: dict) -> list[ALSMidiNote]:
    """Descending 4-bar counterpoint phrase."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop", "build"]))
    midi_rule = cfg.get("midi_rules", {}).get("counter", {})
    motif_names = midi_rule.get("notes", ["F4", "D4", "C4", "A3"])
    motif = [note_name_to_midi(n) for n in motif_names]
    vel = midi_rule.get("default_velocity", 85)

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            beat = bar * 4.0
            note_idx = bar_off % len(motif)
            notes.append(ALSMidiNote(
                pitch=motif[note_idx], time=beat + 2.0,  # offset by 2 beats
                duration=2.5, velocity=_humanize_vel(vel, beat)))

    return notes


def _gen_chords(sections: list[dict], voicings: list[list[int]],
                track_cfg: dict) -> list[ALSMidiNote]:
    """Full harmonic voicings per chord cycle."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop", "verse", "bridge"]))
    vel = 80

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(voicings)
            beat = bar * 4.0
            for pitch in voicings[chord_idx]:
                notes.append(ALSMidiNote(
                    pitch=pitch, time=beat,
                    duration=7.5, velocity=_humanize_vel(vel, beat)))

    return notes


def _gen_pad(sections: list[dict], voicings: list[list[int]],
             track_cfg: dict) -> list[ALSMidiNote]:
    """Long sustained chord pads in atmospheric sections."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections",
                                ["intro", "verse", "break", "bridge", "outro"]))
    vel = 70

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(0, sec["bars"], 2):  # every 2 bars
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(voicings)
            beat = bar * 4.0
            for pitch in voicings[chord_idx]:
                notes.append(ALSMidiNote(
                    pitch=pitch, time=beat,
                    duration=8.0, velocity=_humanize_vel(vel, beat)))

    return notes


def _gen_arp(sections: list[dict], voicings: list[list[int]],
             track_cfg: dict) -> list[ALSMidiNote]:
    """16th note arpeggio through chord tones."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop", "bridge"]))
    vel = 85

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(voicings)
            chord = voicings[chord_idx]
            beat_base = bar * 4.0
            for i in range(16):  # 16 sixteenth notes per bar
                t = beat_base + i * 0.25
                pitch = chord[i % len(chord)]
                # Alternate octave every other cycle
                if (i // len(chord)) % 2 == 1:
                    pitch += 12
                notes.append(ALSMidiNote(
                    pitch=pitch, time=t,
                    duration=0.2, velocity=_humanize_vel(vel, t)))

    return notes


def _gen_vocal_chop(sections: list[dict], roots: list[int],
                    track_cfg: dict) -> list[ALSMidiNote]:
    """Syncopated vocal chop hits."""
    notes: list[ALSMidiNote] = []
    active = set(track_cfg.get("active_sections", ["drop", "vip"]))
    vel = 100
    # Syncopated rhythm: off-beats and dotted patterns
    hit_pattern = [0.5, 1.5, 2.0, 3.25]

    for sec in sections:
        if sec["type"] not in active:
            continue
        for bar_off in range(sec["bars"]):
            bar = sec["bar_start"] + bar_off
            chord_idx = (bar_off // 2) % len(roots)
            root = roots[chord_idx] + 24  # voice up 2 octaves
            beat_base = bar * 4.0
            for h in hit_pattern:
                notes.append(ALSMidiNote(
                    pitch=root, time=beat_base + h,
                    duration=0.25, velocity=_humanize_vel(vel, beat_base + h)))

    return notes


def _gen_fx(sections: list[dict], track_cfg: dict) -> list[ALSMidiNote]:
    """Impact one-shots at section transitions."""
    notes: list[ALSMidiNote] = []
    for i, sec in enumerate(sections):
        if sec["type"] in ("drop", "build"):
            beat = sec["bar_start"] * 4.0
            notes.append(ALSMidiNote(
                pitch=60, time=beat, duration=2.0, velocity=110))
            # Reverse riser before drops
            if sec["type"] == "drop" and i > 0:
                prev_end = sec["bar_start"] * 4.0
                notes.append(ALSMidiNote(
                    pitch=64, time=prev_end - 4.0, duration=4.0, velocity=100))
    return notes


def _gen_riser(sections: list[dict], track_cfg: dict) -> list[ALSMidiNote]:
    """Sustained rising note through build sections."""
    notes: list[ALSMidiNote] = []
    for sec in sections:
        if sec["type"] != "build":
            continue
        beat = sec["bar_start"] * 4.0
        length = sec["bars"] * 4.0
        notes.append(ALSMidiNote(
            pitch=60, time=beat, duration=length,
            velocity=90))
    return notes


# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATION BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _build_sidechain_auto(param: str, sec_start: int, sec_bars: int,
                          duck_depth: float = 0.3) -> ALSAutomation:
    """Beat-sync volume ducking."""
    pts: list[ALSAutomationPoint] = []
    for bar_off in range(sec_bars):
        bar = sec_start + bar_off
        for beat in range(4):
            t = float(bar * 4 + beat)
            pts.append(ALSAutomationPoint(time=t, value=1.0 - duck_depth))
            pts.append(ALSAutomationPoint(time=t + 0.1, value=1.0))
    return ALSAutomation(parameter_name=param, points=pts)


def build_track_automation(track_name: str, track_cfg: dict,
                           sections: list[dict],
                           total_bars: int) -> list[ALSAutomation]:
    """Build all automation envelopes for a track from config."""
    autos: list[ALSAutomation] = []

    # --- Configured automation rules ---
    for rule in track_cfg.get("automation", []):
        param = rule["param"]
        shape = rule["shape"]
        trigger = rule.get("trigger", "drop")

        for sec in sections:
            if not _section_matches_trigger(sec, trigger):
                continue

            start_b = sec["bar_start"] * 4.0
            end_b = (sec["bar_start"] + sec["bars"]) * 4.0

            if shape == "lp_sweep":
                # Only sweep first 4 bars of section
                sweep_end = min(start_b + 16.0, end_b)
                autos.append(make_lp_sweep_automation(
                    param, start_b, sweep_end,
                    closed_val=rule.get("closed", 0.08),
                    open_val=rule.get("open", 1.0),
                    curve=rule.get("curve", 0.4)))

            elif shape == "sine":
                cycles = int(rule.get("cycles_per_bar", 2) * sec["bars"])
                res = sec["bars"] * 8
                autos.append(make_sine_automation(
                    param, start_b, end_b,
                    min_val=rule.get("min", 0.0),
                    max_val=rule.get("max", 1.0),
                    cycles=cycles, resolution=res))

            elif shape == "sawtooth":
                cycles = int(rule.get("cycles_per_bar", 1) * sec["bars"])
                res = sec["bars"] * 8
                autos.append(make_sawtooth_automation(
                    param, start_b, end_b,
                    min_val=rule.get("min", 0.0),
                    max_val=rule.get("max", 1.0),
                    cycles=cycles, resolution=res))

            elif shape == "ramp":
                autos.append(make_ramp_automation(
                    param, start_b, end_b,
                    start_val=rule.get("start", 0.0),
                    end_val=rule.get("end", 1.0)))

            elif shape == "sidechain":
                autos.append(_build_sidechain_auto(
                    param, sec["bar_start"], sec["bars"],
                    duck_depth=rule.get("duck_depth", 0.3)))

    # --- Send automation from send_a / send_b config ---
    for send_key, send_param in [("send_a", "Send_A"), ("send_b", "Send_B")]:
        send_map = track_cfg.get(send_key, {})
        if not send_map:
            continue
        send_sections = []
        for sec in sections:
            send_val = send_map.get(sec["type"])
            if send_val is not None:
                send_sections.append((sec["bar_start"], sec["bars"], send_val))
        if send_sections:
            autos.append(make_section_send_automation(
                send_param, send_sections, total_bars))

    return autos


def _section_matches_trigger(sec: dict, trigger: str) -> bool:
    """Check if a section matches an automation trigger rule."""
    if trigger == "drop_start":
        return sec["type"] == "drop"
    return sec["type"] == trigger


# ═══════════════════════════════════════════════════════════════════════════
# ALS PROJECT ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def build_project(cfg: dict) -> ALSProject:
    """Build complete ALSProject from config."""
    g = cfg["global"]
    bpm = g["bpm"]
    total_bars = g["total_bars"]
    total_beats = total_bars * 4

    sections = resolve_arrangement(cfg)
    roots = build_chord_roots(cfg)
    voicings = build_chord_voicings(roots)
    drum_patterns = cfg.get("drum_patterns", {})
    tracks_cfg = cfg.get("tracks", {})
    midi_rules = cfg.get("midi_rules", {})

    # Try to load Serum 2 state
    proc_state = None
    ctrl_state = None
    try:
        from engine._captured_serum2_state import (
            CONTROLLER_STATE_SERUM_2,
            PROCESSOR_STATE_SERUM_2,
        )
        proc_state = PROCESSOR_STATE_SERUM_2
        ctrl_state = CONTROLLER_STATE_SERUM_2
    except ImportError:
        _log.warning("No captured Serum 2 state — ALS will have empty plugin state")

    # Track ordering (matches both Wild Ones and Apology)
    TRACK_ORDER = [
        "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
        "LEAD", "COUNTER", "VOCAL_CHOP", "CHORDS", "PAD", "ARP", "FX", "RISER",
    ]

    # Generate MIDI per track
    midi_data: dict[str, list[ALSMidiNote]] = {}

    for track_name in TRACK_ORDER:
        tcfg = tracks_cfg.get(track_name, {})
        role = tcfg.get("role", track_name.lower())
        rule = midi_rules.get(role, {})

        if role == "drums":
            midi_data[track_name] = _gen_drums(sections, drum_patterns, cfg)
        elif role in ("bass", "sub", "growl", "wobble", "formant"):
            midi_data[track_name] = _gen_bass_role(
                sections, roots, rule, tcfg)
        elif role == "riddim":
            midi_data[track_name] = _gen_riddim(sections, roots, cfg, tcfg)
        elif role == "lead":
            midi_data[track_name] = _gen_lead(sections, cfg, tcfg)
        elif role == "counter":
            midi_data[track_name] = _gen_counter(sections, cfg, tcfg)
        elif role == "chords":
            midi_data[track_name] = _gen_chords(sections, voicings, tcfg)
        elif role == "pad":
            midi_data[track_name] = _gen_pad(sections, voicings, tcfg)
        elif role == "arp":
            midi_data[track_name] = _gen_arp(sections, voicings, tcfg)
        elif role == "vocal_chop":
            midi_data[track_name] = _gen_vocal_chop(sections, roots, tcfg)
        elif role == "fx":
            midi_data[track_name] = _gen_fx(sections, tcfg)
        elif role == "riser":
            midi_data[track_name] = _gen_riser(sections, tcfg)

    # Build automation per track
    auto_data: dict[str, list[ALSAutomation]] = {}
    for track_name in TRACK_ORDER:
        tcfg = tracks_cfg.get(track_name, {})
        auto_data[track_name] = build_track_automation(
            track_name, tcfg, sections, total_bars)

    # Drum rack pads
    drum_pads = []
    drums_cfg = tracks_cfg.get("DRUMS", {})
    for pad in drums_cfg.get("pads", []):
        drum_pads.append(ALSDrumPad(
            note=pad["note"],
            name=pad["name"],
            color=drums_cfg.get("color", 69),
            choke_group=pad.get("choke", -1)))

    # Assemble ALSTrack objects
    als_tracks: list[ALSTrack] = []

    for track_name in TRACK_ORDER:
        tcfg = tracks_cfg.get(track_name, {})
        notes = midi_data.get(track_name, [])

        if not notes:
            continue

        midi_clip = ALSMidiClip(
            name=track_name,
            start_beat=0.0,
            length_beats=float(total_beats),
            notes=notes,
        )

        is_drums = tcfg.get("role") == "drums"
        synth = tcfg.get("synth")
        devices = [] if is_drums or not synth else [synth]

        # Embed Serum 2 state
        proc_states: dict[str, bytes] = {}
        ctrl_states: dict[str, bytes] = {}
        if devices and proc_state:
            proc_states[synth] = proc_state
        if devices and ctrl_state:
            ctrl_states[synth] = ctrl_state

        als_tracks.append(ALSTrack(
            name=track_name,
            track_type="midi",
            color=tcfg.get("color", 0),
            volume_db=tcfg.get("volume_db", -6.0),
            pan=tcfg.get("pan", 0.0),
            device_names=devices,
            preset_states=proc_states,
            controller_states=ctrl_states,
            midi_clips=[midi_clip],
            automations=auto_data.get(track_name, []),
            drum_rack_pads=drum_pads if is_drums else [],
        ))

    # Return tracks
    returns_cfg = cfg.get("returns", {})
    for ret_name, ret_cfg in returns_cfg.items():
        als_tracks.append(ALSTrack(
            name=ret_name,
            track_type="return",
            color=ret_cfg.get("color", 0),
            volume_db=ret_cfg.get("volume_db", -6.0),
        ))

    # Scenes / cue points from arrangement
    scenes = [ALSScene(name=sec["name"], tempo=bpm) for sec in sections]
    cue_points = [ALSCuePoint(name=sec["name"], time=sec["bar_start"] * 4.0)
                  for sec in sections]

    track_name = cfg.get("template_name", "DUBFORGE_BASE")

    # Note count stats
    total_notes = sum(len(midi_data.get(t, [])) for t in TRACK_ORDER)
    total_auto_pts = sum(
        sum(len(a.points) for a in auto_data.get(t, []))
        for t in TRACK_ORDER)

    project = ALSProject(
        name=track_name,
        bpm=bpm,
        time_sig_num=g.get("time_sig", [4, 4])[0],
        time_sig_den=g.get("time_sig", [4, 4])[1],
        tracks=als_tracks,
        scenes=scenes,
        master_volume_db=0.0,
        cue_points=cue_points,
    )

    print(f"  {total_notes} MIDI notes across {len(als_tracks) - len(returns_cfg)} tracks")
    print(f"  {total_auto_pts} automation points across {sum(1 for t in TRACK_ORDER if auto_data.get(t))} tracks")

    return project


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="DUBFORGE Base Template Generator")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="YAML config file (default: configs/base_template.yaml)")
    parser.add_argument("--name", type=str, default=None,
                        help="Track name override")
    parser.add_argument("--bpm", type=float, default=None,
                        help="BPM override")
    parser.add_argument("--key", type=str, default=None,
                        help="Key override (e.g. E_minor)")
    args = parser.parse_args()

    overrides = {}
    if args.name:
        overrides["name"] = args.name
    if args.bpm:
        overrides["bpm"] = args.bpm
    if args.key:
        overrides["key"] = args.key

    cfg = load_config(args.config, overrides if overrides else None)
    track_name = cfg.get("template_name", "DUBFORGE_BASE")
    safe_name = track_name.replace(" ", "_").upper()

    print("╔══════════════════════════════════════════════════════════════╗")
    print(f"║  DUBFORGE — Base Template Generator                         ║")
    print(f"║  Track: {track_name:52s}║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Show arrangement
    sections = resolve_arrangement(cfg)
    g = cfg["global"]
    print(f"  Arrangement: {g['key']} @ {g['bpm']} BPM, {g['total_bars']} bars")
    for sec in sections:
        golden = " <<< GOLDEN SECTION" if (
            sec["bar_start"] / g["total_bars"] > 0.6 and
            sec["bar_start"] / g["total_bars"] < 0.65 and
            sec["type"] == "drop"
        ) else ""
        print(f"    Bar {sec['bar_start']:>3d}-{sec['bar_start']+sec['bars']:>3d}: "
              f"{sec['name']} ({sec['bars']} bars){golden}")
    print()

    project = build_project(cfg)

    # Write ALS
    als_path = OUTPUT_DIR / "ableton" / f"{safe_name}.als"
    write_als(project, str(als_path))

    print(f"\n  Outputs:")
    print(f"    ALS:  {als_path}")
    print()
    print("  Workflow:")
    print("    1. Open ALS in Ableton Live")
    print("    2. Load Serum 2 presets on each track")
    print("    3. Set Serum 2 global tune to -32 cents (432 Hz)")
    print("    4. Press play — full arrangement ready")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
