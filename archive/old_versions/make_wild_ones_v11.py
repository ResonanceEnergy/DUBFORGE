#!/usr/bin/env python3
"""Wild Ones V11 -- MIDI ALS Production.

MIDI + Serum 2 architecture. Key features:
  1. Full automation system (filter sweeps, macro movement, send levels)
  2. Ghost notes and drum fills at section transitions
  3. PHI-derived velocity humanization
  4. Halftime VIP drop with triplet hi-hats
  5. Counter-melody track (answering hook)
  6. Per-section send automation (reverb & delay)
  7. Sidechain-style volume ducking on SUB

Output:
  - Wild_Ones_V11.als -> MIDI tracks (load Serum 2 presets for production)
"""
from __future__ import annotations

import math
import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from pathlib import Path

from engine.als_generator import (
    ALSAutomation,
    ALSAutomationPoint,
    ALSCuePoint,
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
from engine.midi_export import NoteEvent, write_midi_file
from engine.fxp_writer import FXPPreset, FXPBank, VSTParam, write_fxp, write_fxb

# ======================================================================
# SONG CONSTANTS
# ======================================================================
PHI = 1.6180339887
TRACK_NAME = "Wild_Ones_V11"
BPM = 127.0
KEY_ROOT = "Ab"
TIME_SIG = (4, 4)
TOTAL_BARS = 144  # Fibonacci: 144
TOTAL_BEATS = TOTAL_BARS * 4  # 576

# -- Pitch Map (Ab minor / Cb major) ----------------------------------
MIDI = {
    "Ab0": 32, "Bb0": 34,
    "Ab1": 44, "Bb1": 46, "C2": 48, "Db2": 49,
    "Eb2": 51, "F2": 53, "G2": 55,
    "Ab2": 56, "Bb2": 58, "C3": 60, "Db3": 61,
    "Eb3": 63, "F3": 65, "G3": 67,
    "Ab3": 68, "Bb3": 70, "C4": 72, "Db4": 73,
    "Eb4": 75, "F4": 77, "G4": 79,
    "Ab4": 80, "Bb4": 82, "C5": 84, "Db5": 85,
    "Eb5": 87, "F5": 89,
}

# Chord voicings
CHORD_Ab = [MIDI["Ab3"], MIDI["C4"], MIDI["Eb4"]]   # [68, 72, 75]
CHORD_Cm = [MIDI["C3"], MIDI["Eb3"], MIDI["G3"]]    # [60, 63, 67]
CHORD_Fm = [MIDI["F3"], MIDI["Ab3"], MIDI["C4"]]    # [65, 68, 72]
CHORD_Db = [MIDI["Db3"], MIDI["F3"], MIDI["Ab3"]]   # [61, 65, 68]
CHORDS = [CHORD_Ab, CHORD_Cm, CHORD_Fm, CHORD_Db]
BASS_ROOTS = [MIDI["Ab1"], MIDI["C2"], MIDI["F2"], MIDI["Db2"]]
SUB_ROOTS = [MIDI["Ab0"], MIDI["C2"] - 12, MIDI["F2"] - 12, MIDI["Db2"] - 12]

# GM Drum Map
KICK = 36
SNARE = 38
CLOSED_HH = 42
OPEN_HH = 46
CLAP = 39
RIDE = 51
CRASH = 49
PERC1 = 37  # side stick
PERC2 = 56  # cowbell

# -- Section Map (bar_start, num_bars) ---------------------------------
SEC_INTRO = 0;        INTRO_BARS = 8
SEC_VERSE1 = 8;       VERSE1_BARS = 8
SEC_PRECHORUS1 = 16;  PRECHORUS1_BARS = 8
SEC_CHORUS1 = 24;     CHORUS1_BARS = 16
SEC_BREAK = 40;       BREAK_BARS = 8
SEC_VERSE2 = 48;      VERSE2_BARS = 8
SEC_PRECHORUS2 = 56;  PRECHORUS2_BARS = 8
SEC_CHORUS2 = 64;     CHORUS2_BARS = 16
SEC_BRIDGE = 80;      BRIDGE_BARS = 8     # Golden section (~bar 89)
SEC_VIP = 88;         VIP_DROP_BARS = 16
SEC_FINAL = 104;      FINAL_CHORUS_BARS = 16
SEC_OUTRO = 120;      OUTRO_BARS = 24

SECTIONS = [
    ("INTRO",         SEC_INTRO,      INTRO_BARS),
    ("VERSE1",        SEC_VERSE1,     VERSE1_BARS),
    ("PRE_CHORUS1",   SEC_PRECHORUS1, PRECHORUS1_BARS),
    ("CHORUS1",       SEC_CHORUS1,    CHORUS1_BARS),
    ("BREAK",         SEC_BREAK,      BREAK_BARS),
    ("VERSE2",        SEC_VERSE2,     VERSE2_BARS),
    ("PRE_CHORUS2",   SEC_PRECHORUS2, PRECHORUS2_BARS),
    ("CHORUS2",       SEC_CHORUS2,    CHORUS2_BARS),
    ("BRIDGE_GOLDEN", SEC_BRIDGE,     BRIDGE_BARS),
    ("VIP_DROP",      SEC_VIP,        VIP_DROP_BARS),
    ("FINAL_CHORUS",  SEC_FINAL,      FINAL_CHORUS_BARS),
    ("OUTRO",         SEC_OUTRO,      OUTRO_BARS),
]

# -- Hook Melody (30-note loop, 8 bars = 32 beats) --------------------
HOOK_MELODY = [
    (0.0, "Eb4", 1.0), (1.0, "F4", 0.5), (1.5, "Ab4", 1.5),
    (3.0, "Bb4", 1.0), (4.0, "Ab4", 0.5), (4.5, "F4", 1.0),
    (5.5, "Eb4", 0.5), (6.0, "C4", 1.5), (7.5, "Db4", 0.5),
    (8.0, "Eb4", 1.0), (9.0, "F4", 1.0), (10.0, "Ab4", 1.0),
    (11.0, "C5", 1.0), (12.0, "Bb4", 2.0), (14.0, "Ab4", 1.0),
    (15.0, "F4", 1.0), (16.0, "Eb4", 2.0), (18.0, "C4", 1.5),
    (19.5, "Db4", 0.5), (20.0, "Eb4", 2.0), (22.0, "F4", 1.0),
    (23.0, "Ab4", 1.0), (24.0, "Bb4", 1.5), (25.5, "Ab4", 0.5),
    (26.0, "F4", 1.0), (27.0, "Eb4", 1.0), (28.0, "Db4", 1.0),
    (29.0, "C4", 1.5), (30.5, "Db4", 0.5), (31.0, "Eb4", 1.0),
]

# -- Counter-Melody (fills gaps of hook, lower register) ---------------
COUNTER_MELODY = [
    (2.0, "Ab3", 0.75), (3.5, "G3", 0.5), (5.0, "F3", 0.75),
    (6.5, "Eb3", 0.5), (7.0, "C3", 0.75),
    (10.5, "Db3", 0.75), (11.5, "Eb3", 0.5), (13.0, "F3", 0.75),
    (14.5, "G3", 0.5), (15.5, "Ab3", 0.5),
    (17.0, "G3", 0.75), (19.0, "F3", 0.75), (21.0, "Eb3", 0.75),
    (22.5, "C3", 0.5), (23.5, "Db3", 0.5),
    (25.0, "Eb3", 0.75), (26.5, "F3", 0.5), (28.5, "G3", 0.75),
    (30.0, "Ab3", 0.75), (31.5, "Bb3", 0.5),
]

# -- Track Colors (Ableton color indices) ------------------------------
COLORS = {
    "DRUMS": 69, "BASS": 24, "SUB": 25, "GROWL": 60,
    "WOBBLE": 61, "RIDDIM": 62, "FORMANT": 63, "LEAD": 17,
    "COUNTER": 19, "CHORDS": 20, "PAD": 26, "ARP": 18,
    "FX": 14, "RISER": 15, "REVERB": 50, "DELAY": 52,
}

# Serum 2 preset mapping
SERUM2_PRESETS = {
    "BASS":    ("DUBFORGE_Fractal_Sub",            "Phi-harmonic sub bass"),
    "SUB":     ("DUBFORGE_Deep_Sub",               "Pure sine sub"),
    "GROWL":   ("DUBFORGE_Phi_Growl",              "Aggressive growl"),
    "WOBBLE":  ("DUBFORGE_Spectral_Tear",          "Classic wobble bass"),
    "RIDDIM":  ("DUBFORGE_Riddim_Minimal",         "Minimal riddim"),
    "FORMANT": ("DUBFORGE_Formant_Vowel",          "Vowel-shifting bass"),
    "LEAD":    ("DUBFORGE_Fibonacci_FM_Screech",   "FM screech lead"),
    "COUNTER": ("DUBFORGE_Counter_Pluck",          "Pluck counter-melody"),
    "CHORDS":  ("DUBFORGE_Golden_Reese",           "Supersaw reese chords"),
    "PAD":     ("DUBFORGE_Granular_Atmosphere",    "Lush atmospheric pad"),
    "ARP":     ("DUBFORGE_Phi_Arp",                "Fibonacci-timed arp"),
    "FX":      ("DUBFORGE_Weapon",                 "Impact & FX hits"),
    "RISER":   ("DUBFORGE_Riser_Sweep",            "Build-up riser"),
}


# ======================================================================
# VELOCITY HUMANIZATION
# ======================================================================

def _humanize_vel(base_vel: int, beat_pos: float,
                  strength: float = 0.15) -> int:
    """PHI-derived velocity variation. Non-repeating natural feel."""
    offset = math.sin(beat_pos * PHI * 2.0) * base_vel * strength
    return max(1, min(127, int(base_vel + offset)))


# ======================================================================
# MIDI NOTE GENERATORS
# ======================================================================

def _gen_drums() -> list[ALSMidiNote]:
    """Drums with ghost notes, fills, and halftime VIP."""
    notes: list[ALSMidiNote] = []

    def _add(pitch: int, bar: int, beat: float, dur: float = 0.25,
             vel: int = 100) -> None:
        notes.append(ALSMidiNote(
            pitch=pitch, time=bar * 4 + beat, duration=dur, velocity=vel))

    def _snare_roll(bar: int, start_beat: float = 2.0,
                    end_beat: float = 4.0,
                    vel_start: int = 60, vel_end: int = 120) -> None:
        """32nd note snare roll with velocity ramp."""
        steps = int((end_beat - start_beat) / 0.125)
        for i in range(steps):
            v = vel_start + int(
                (vel_end - vel_start) * i / max(steps - 1, 1))
            _add(SNARE, bar, start_beat + i * 0.125, 0.125, v)

    for sec_name, sec_start, sec_bars in SECTIONS:
        for bar_offset in range(sec_bars):
            bar = sec_start + bar_offset
            is_last_bar = (bar_offset == sec_bars - 1)

            # -- BREAK: sparse + building snare roll ----------------------
            if sec_name == "BREAK":
                _add(KICK, bar, 0.0, 0.5, 70)
                _add(CLOSED_HH, bar, 2.0, 0.25, 50)
                if bar_offset % 2 == 0:
                    _add(PERC1, bar, 1.5, 0.25, 40)
                if bar_offset >= sec_bars - 2:
                    _snare_roll(bar, 2.0, 4.0,
                                50 + bar_offset * 10, 100)
                continue

            # -- INTRO: building from hats to full kit --------------------
            if sec_name == "INTRO":
                if bar_offset < 4:
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                             _humanize_vel(60, eighth * 0.5))
                else:
                    _add(KICK, bar, 0.0, 0.5, 90)
                    _add(KICK, bar, 2.0, 0.5, 80)
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                             _humanize_vel(70, eighth * 0.5))
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 70, 110)
                    _add(CRASH, bar, 3.75, 0.25, 80)
                continue

            # -- OUTRO: dissolving ----------------------------------------
            if sec_name == "OUTRO":
                fade = max(0.3, 1.0 - bar_offset / sec_bars)
                vel = int(100 * fade)
                _add(KICK, bar, 0.0, 0.5, vel)
                if bar_offset < sec_bars // 2:
                    _add(SNARE, bar, 1.0, 0.5, vel)
                for eighth in range(8):
                    _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                         int(vel * 0.7))
                continue

            is_drop = sec_name in ("CHORUS1", "CHORUS2", "FINAL_CHORUS")
            is_vip = sec_name == "VIP_DROP"
            is_build = "PRE_CHORUS" in sec_name

            # -- HALFTIME VIP: snare on 3, triplet hats -------------------
            if is_vip:
                _add(KICK, bar, 0.0, 0.5, 115)
                _add(KICK, bar, 1.75, 0.25, 85)
                _add(KICK, bar, 3.5, 0.25, 90)
                # Snare on 3 only (halftime feel)
                _add(SNARE, bar, 2.0, 0.5, 115)
                _add(CLAP, bar, 2.0, 0.25, 100)
                # Triplet hi-hats
                for triplet in range(12):
                    t = triplet * (4.0 / 12.0)
                    is_accent = triplet % 3 == 0
                    _add(CLOSED_HH, bar, t, 0.2,
                         _humanize_vel(85 if is_accent else 65, t))
                # Ghost snares
                _add(SNARE, bar, 0.75, 0.125, 40)
                _add(SNARE, bar, 3.25, 0.125, 35)
                if bar_offset == 0:
                    _add(CRASH, bar, 0.0, 1.0, 110)
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 80, 127)
                continue

            # -- STANDARD DROP: four-on-floor + ghost notes ---------------
            if is_drop:
                for beat in range(4):
                    _add(KICK, bar, float(beat), 0.5,
                         _humanize_vel(110, float(beat)))
                _add(SNARE, bar, 1.0, 0.5, 110)
                _add(SNARE, bar, 3.0, 0.5, 110)
                _add(CLAP, bar, 1.0, 0.25, 90)
                _add(CLAP, bar, 3.0, 0.25, 90)
                for eighth in range(8):
                    t = eighth * 0.5
                    if eighth % 2 == 1:
                        _add(OPEN_HH, bar, t, 0.25,
                             _humanize_vel(80, t))
                    else:
                        _add(CLOSED_HH, bar, t, 0.25,
                             _humanize_vel(85, t))
                # Ghost notes between snares
                _add(SNARE, bar, 1.75, 0.125, 40)
                _add(SNARE, bar, 3.75, 0.125, 35)
                if bar_offset == 0:
                    _add(CRASH, bar, 0.0, 1.0, 100)
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 70, 120)
                    _add(CRASH, bar, 3.875, 0.125, 95)
                continue

            # -- PRE-CHORUS BUILD: accelerating density -------------------
            if is_build:
                _add(KICK, bar, 0.0, 0.5, 95)
                _add(KICK, bar, 1.5, 0.5, 85)
                _add(KICK, bar, 3.0, 0.5, 90)
                if bar_offset > sec_bars // 2:
                    _add(KICK, bar, 0.5, 0.25, 70)
                    _add(KICK, bar, 2.5, 0.25, 70)
                _add(SNARE, bar, 1.0, 0.5, 95)
                _add(SNARE, bar, 3.0, 0.5, 95)
                for eighth in range(8):
                    _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                         _humanize_vel(75, eighth * 0.5))
                if is_last_bar:
                    _snare_roll(bar, 2.0, 4.0, 60, 127)
                    _add(CRASH, bar, 3.875, 0.125, 100)
                continue

            # -- VERSE / BRIDGE: half-time + ghost notes ------------------
            _add(KICK, bar, 0.0, 0.5, _humanize_vel(100, 0.0))
            _add(KICK, bar, 2.0, 0.5, _humanize_vel(90, 2.0))
            _add(SNARE, bar, 1.0, 0.5, _humanize_vel(95, 1.0))
            _add(SNARE, bar, 3.0, 0.5, _humanize_vel(95, 3.0))
            # Ghost notes in verses
            if "VERSE" in sec_name:
                _add(SNARE, bar, 0.75, 0.125, 38)
                _add(SNARE, bar, 2.75, 0.125, 35)
                _add(KICK, bar, 1.75, 0.25, 50)
            for eighth in range(8):
                vel = 85 if eighth % 2 == 0 else 75
                _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                     _humanize_vel(vel, eighth * 0.5))
            if sec_name == "BRIDGE_GOLDEN":
                _add(RIDE, bar, 0.0, 0.5, 65)
                _add(RIDE, bar, 2.0, 0.5, 55)
            if bar_offset % 2 == 0:
                _add(PERC1, bar, 1.5, 0.25, 45)

    return notes


def _gen_bass() -> list[ALSMidiNote]:
    """Bass -- root notes following chord progression, all 144 bars."""
    notes: list[ALSMidiNote] = []
    for bar in range(TOTAL_BARS):
        chord_idx = (bar // 2) % 4
        root = BASS_ROOTS[chord_idx]
        vel = _humanize_vel(100, float(bar))
        notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                  duration=2.0, velocity=vel))
    return notes


def _gen_sub() -> list[ALSMidiNote]:
    """Sub bass -- octave below bass, drops only."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = SUB_ROOTS[chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=4.0, velocity=90))
    return notes


def _gen_growl() -> list[ALSMidiNote]:
    """Growl bass -- VIP and final chorus."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"],
                    MIDI["Db3"]][chord_idx]
            vel = _humanize_vel(100, float(bar_off))
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=vel))
    return notes


def _gen_wobble() -> list[ALSMidiNote]:
    """Wobble bass -- chorus/VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = BASS_ROOTS[chord_idx]
            vel = _humanize_vel(95, float(bar_off))
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=vel))
    return notes


def _gen_riddim() -> list[ALSMidiNote]:
    """Riddim -- short staccato hits in VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = BASS_ROOTS[chord_idx]
            for sub_beat in [0.0, 0.75, 1.5, 2.5]:
                vel = _humanize_vel(100, sub_beat + bar_off)
                notes.append(ALSMidiNote(
                    pitch=root, time=bar * 4 + sub_beat,
                    duration=0.5, velocity=vel))
    return notes


def _gen_formant() -> list[ALSMidiNote]:
    """Formant bass -- vowel-shifting, VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"],
                    MIDI["Db3"]][chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=3.0, velocity=95))
    return notes


def _gen_lead() -> list[ALSMidiNote]:
    """Hook/lead -- 30-note loop in chorus/VIP/final with humanization."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for rep in range(sec_bars // 8):
            base_beat = (sec_start + rep * 8) * 4
            for beat_off, note_name, dur in HOOK_MELODY:
                vel = _humanize_vel(90, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=base_beat + beat_off,
                    duration=dur,
                    velocity=vel,
                ))
    return notes


def _gen_counter() -> list[ALSMidiNote]:
    """Counter-melody -- answering phrases in chorus/VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for rep in range(sec_bars // 8):
            base_beat = (sec_start + rep * 8) * 4
            for beat_off, note_name, dur in COUNTER_MELODY:
                vel = _humanize_vel(75, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=base_beat + beat_off,
                    duration=dur,
                    velocity=vel,
                ))
    return notes


def _gen_chords() -> list[ALSMidiNote]:
    """Chord voicings -- chorus/VIP/final, 3-note triads."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            for pitch in CHORDS[chord_idx]:
                vel = _humanize_vel(82, float(bar_off))
                notes.append(ALSMidiNote(
                    pitch=pitch, time=bar * 4,
                    duration=2.0, velocity=vel))
    return notes


def _gen_pad() -> list[ALSMidiNote]:
    """Pad -- sustained chords in verse/bridge/intro/outro."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_INTRO, INTRO_BARS),
                                 (SEC_VERSE1, VERSE1_BARS),
                                 (SEC_BREAK, BREAK_BARS),
                                 (SEC_VERSE2, VERSE2_BARS),
                                 (SEC_BRIDGE, BRIDGE_BARS),
                                 (SEC_OUTRO, OUTRO_BARS)]:
        for bar_off in range(0, sec_bars, 2):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            for pitch in CHORDS[chord_idx]:
                vel = _humanize_vel(65, float(bar_off))
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,  # octave up for pad register
                    time=bar * 4,
                    duration=8.0,  # 2 bars sustained
                    velocity=vel))
    return notes


def _gen_arp() -> list[ALSMidiNote]:
    """Arp -- 16th-note chord arpeggiation in chorus/bridge/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_BRIDGE, BRIDGE_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            chord_notes = CHORDS[chord_idx]
            arp_notes = chord_notes + [chord_notes[0] + 12]
            for sixteenth in range(16):
                pitch = arp_notes[sixteenth % len(arp_notes)]
                t = sixteenth * 0.25
                vel = _humanize_vel(
                    70 + (sixteenth % 4 == 0) * 15, t)
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,
                    time=bar * 4 + t,
                    duration=0.25,
                    velocity=vel))
    return notes


def _gen_fx() -> list[ALSMidiNote]:
    """FX hits -- impacts on drops, stutter in builds, reverse cues."""
    notes: list[ALSMidiNote] = []
    # Impact hits on drop entries
    for sec_start in [SEC_CHORUS1, SEC_CHORUS2, SEC_VIP, SEC_FINAL]:
        notes.append(ALSMidiNote(pitch=MIDI["Ab3"],
                                  time=sec_start * 4,
                                  duration=2.0, velocity=120))
    # Stutter FX in pre-chorus (last 2 bars)
    for sec_start, sec_bars in [(SEC_PRECHORUS1, PRECHORUS1_BARS),
                                 (SEC_PRECHORUS2, PRECHORUS2_BARS)]:
        for bar_off in range(sec_bars - 2, sec_bars):
            bar = sec_start + bar_off
            for eighth in range(8):
                vel = _humanize_vel(80, eighth * 0.5)
                notes.append(ALSMidiNote(
                    pitch=MIDI["Eb4"],
                    time=bar * 4 + eighth * 0.5,
                    duration=0.25, velocity=vel))
    # Reverse crash cue before each drop (last bar of build section)
    for sec_start in [SEC_CHORUS1, SEC_CHORUS2, SEC_VIP, SEC_FINAL]:
        notes.append(ALSMidiNote(
            pitch=MIDI["C5"],
            time=(sec_start - 1) * 4 + 2.0,
            duration=2.0, velocity=100))
    return notes


def _gen_riser() -> list[ALSMidiNote]:
    """Riser -- ascending pitch sweep in pre-chorus sections."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_PRECHORUS1, PRECHORUS1_BARS),
                                 (SEC_PRECHORUS2, PRECHORUS2_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            pitch = MIDI["Ab3"] + bar_off * 2
            notes.append(ALSMidiNote(
                pitch=min(pitch, 96),
                time=bar * 4,
                duration=4.0,
                velocity=70 + bar_off * 4))
    return notes


# ======================================================================
# AUTOMATION SYSTEM (V11 -- THE BIG NEW FEATURE)
# ======================================================================

def _build_sidechain_auto(param: str, sec_start: int,
                          sec_bars: int,
                          duck_depth: float = 0.3) -> ALSAutomation:
    """Sidechain-style volume ducking -- quick dip on each beat."""
    pts: list[ALSAutomationPoint] = []
    for bar_off in range(sec_bars):
        bar = sec_start + bar_off
        for beat in range(4):
            t = bar * 4.0 + beat
            pts.append(ALSAutomationPoint(time=t, value=duck_depth))
            pts.append(ALSAutomationPoint(
                time=t + 0.125, value=duck_depth + 0.2))
            pts.append(ALSAutomationPoint(time=t + 0.5, value=1.0))
    return ALSAutomation(parameter_name=param, points=pts)


def _build_track_automations() -> dict[str, list[ALSAutomation]]:
    """Build automation envelopes for all synth tracks."""
    auto: dict[str, list[ALSAutomation]] = {}

    # -- BASS: filter cutoff per section -------------------------------
    bass_filter_pts: list[ALSAutomationPoint] = []
    for sec_name, sec_start, sec_bars in SECTIONS:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        if sec_name in ("VERSE1", "VERSE2"):
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.25))
            bass_filter_pts.append(
                ALSAutomationPoint(time=end_b - 0.01, value=0.30))
        elif "PRE_CHORUS" in sec_name:
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.30))
            bass_filter_pts.append(
                ALSAutomationPoint(
                    time=end_b - 0.01, value=0.85, curve=0.4))
        elif sec_name in ("CHORUS1", "CHORUS2", "FINAL_CHORUS"):
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.85))
            bass_filter_pts.append(
                ALSAutomationPoint(time=end_b - 0.01, value=0.80))
        elif sec_name == "VIP_DROP":
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.95))
            bass_filter_pts.append(
                ALSAutomationPoint(time=end_b - 0.01, value=0.90))
        elif sec_name == "BREAK":
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.20))
            bass_filter_pts.append(
                ALSAutomationPoint(time=end_b - 0.01, value=0.15))
        else:
            bass_filter_pts.append(
                ALSAutomationPoint(time=start_b, value=0.35))
            bass_filter_pts.append(
                ALSAutomationPoint(time=end_b - 0.01, value=0.35))
    auto["BASS"] = [
        ALSAutomation(
            parameter_name="Filter_Cutoff", points=bass_filter_pts),
    ]

    # -- SUB: sidechain ducking in drops -------------------------------
    sub_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        sub_autos.append(
            _build_sidechain_auto("Volume", sec_start, sec_bars, 0.3))
    auto["SUB"] = sub_autos

    # -- WOBBLE: sine LFO on filter cutoff during drops ----------------
    wobble_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        wobble_autos.append(make_sine_automation(
            "Filter_Cutoff", start_b, end_b,
            min_val=0.2, max_val=0.9,
            cycles=sec_bars * 2,
            resolution=sec_bars * 16))
    auto["WOBBLE"] = wobble_autos

    # -- GROWL: sawtooth filter + macro2 ramp in VIP/final -------------
    growl_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        growl_autos.append(make_sawtooth_automation(
            "Filter_Cutoff", start_b, end_b,
            min_val=0.3, max_val=0.95,
            cycles=sec_bars // 2,
            resolution=sec_bars * 8))
        growl_autos.append(make_ramp_automation(
            "Macro2", start_b, end_b, 0.2, 0.8, curve=0.3))
    auto["GROWL"] = growl_autos

    # -- FORMANT: macro1 vowel sweep -----------------------------------
    formant_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        formant_autos.append(make_sine_automation(
            "Macro1", start_b, end_b,
            min_val=0.1, max_val=0.9,
            cycles=sec_bars // 4,
            resolution=sec_bars * 4))
    auto["FORMANT"] = formant_autos

    # -- LEAD: reverb send per section ---------------------------------
    lead_send: list[tuple[int, int, float]] = [
        (SEC_CHORUS1, CHORUS1_BARS, 0.6),
        (SEC_CHORUS2, CHORUS2_BARS, 0.6),
        (SEC_VIP, VIP_DROP_BARS, 0.25),
        (SEC_FINAL, FINAL_CHORUS_BARS, 0.5),
    ]
    auto["LEAD"] = [
        make_section_send_automation("Send_A", lead_send, TOTAL_BARS),
    ]

    # -- COUNTER: reverb send per section ------------------------------
    counter_send: list[tuple[int, int, float]] = [
        (SEC_CHORUS1, CHORUS1_BARS, 0.5),
        (SEC_CHORUS2, CHORUS2_BARS, 0.5),
        (SEC_VIP, VIP_DROP_BARS, 0.3),
        (SEC_FINAL, FINAL_CHORUS_BARS, 0.45),
    ]
    auto["COUNTER"] = [
        make_section_send_automation("Send_A", counter_send, TOTAL_BARS),
    ]

    # -- CHORDS: LP filter sweep + reverb send -------------------------
    chord_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        chord_autos.append(make_lp_sweep_automation(
            "Filter_Cutoff",
            sec_start * 4.0, (sec_start + 4) * 4.0,
            closed_val=0.4, open_val=0.85))
    chord_send: list[tuple[int, int, float]] = [
        (SEC_CHORUS1, CHORUS1_BARS, 0.4),
        (SEC_CHORUS2, CHORUS2_BARS, 0.4),
        (SEC_VIP, VIP_DROP_BARS, 0.3),
        (SEC_FINAL, FINAL_CHORUS_BARS, 0.4),
    ]
    chord_autos.append(
        make_section_send_automation("Send_A", chord_send, TOTAL_BARS))
    auto["CHORDS"] = chord_autos

    # -- PAD: filter opening + heavy reverb send -----------------------
    pad_autos: list[ALSAutomation] = []
    pad_autos.append(make_lp_sweep_automation(
        "Filter_Cutoff",
        SEC_INTRO * 4.0, (SEC_INTRO + INTRO_BARS) * 4.0,
        closed_val=0.15, open_val=0.7))
    pad_send: list[tuple[int, int, float]] = [
        (SEC_INTRO, INTRO_BARS, 0.7),
        (SEC_VERSE1, VERSE1_BARS, 0.65),
        (SEC_BREAK, BREAK_BARS, 0.75),
        (SEC_VERSE2, VERSE2_BARS, 0.65),
        (SEC_BRIDGE, BRIDGE_BARS, 0.7),
        (SEC_OUTRO, OUTRO_BARS, 0.8),
    ]
    pad_autos.append(
        make_section_send_automation("Send_A", pad_send, TOTAL_BARS))
    auto["PAD"] = pad_autos

    # -- ARP: delay send for rhythmic interest -------------------------
    arp_send: list[tuple[int, int, float]] = [
        (SEC_CHORUS1, CHORUS1_BARS, 0.5),
        (SEC_CHORUS2, CHORUS2_BARS, 0.5),
        (SEC_BRIDGE, BRIDGE_BARS, 0.6),
        (SEC_FINAL, FINAL_CHORUS_BARS, 0.45),
    ]
    auto["ARP"] = [
        make_section_send_automation("Send_B", arp_send, TOTAL_BARS),
    ]

    # -- RISER: LP sweep + volume ramp during builds -------------------
    riser_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_PRECHORUS1, PRECHORUS1_BARS),
                                 (SEC_PRECHORUS2, PRECHORUS2_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        riser_autos.append(make_lp_sweep_automation(
            "Filter_Cutoff", start_b, end_b, 0.1, 1.0, curve=0.5))
        riser_autos.append(make_ramp_automation(
            "Volume", start_b, end_b, 0.2, 1.0))
    auto["RISER"] = riser_autos

    # -- RIDDIM: macro1 sawtooth modulation ----------------------------
    riddim_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        riddim_autos.append(make_sawtooth_automation(
            "Macro1",
            sec_start * 4.0, (sec_start + sec_bars) * 4.0,
            min_val=0.2, max_val=0.7,
            cycles=sec_bars,
            resolution=sec_bars * 4))
    auto["RIDDIM"] = riddim_autos

    return auto


# ======================================================================
# SERUM 2 PRESET GENERATION
# ======================================================================

def _build_serum2_presets() -> dict[str, FXPPreset]:
    """Generate Serum 2 .fxp presets for each synth track."""
    presets: dict[str, FXPPreset] = {}

    def _preset(name: str,
                params: list[tuple[int, str, float]]) -> FXPPreset:
        return FXPPreset(
            name=name,
            params=[VSTParam(index=i, name=n, value=v)
                    for i, n, v in params],
        )

    presets["BASS"] = _preset("DUBFORGE_Fractal_Sub", [
        (0, "OscA_WtPos", 0.0), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0625), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.0), (7, "SubOsc_Level", 0.8),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.35),
        (10, "Filter_Res", 0.15), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.3),
        (14, "Env1_Sustain", 0.7), (15, "Env1_Release", 0.2),
        (16, "Master_Volume", 0.85), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.35), (19, "Macro2", 0.15),
    ])

    presets["SUB"] = _preset("DUBFORGE_Deep_Sub", [
        (0, "OscA_WtPos", 0.0), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.0), (7, "SubOsc_Level", 1.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.15),
        (10, "Filter_Res", 0.0), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.2),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.9), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.0), (19, "Macro2", 0.0),
    ])

    presets["GROWL"] = _preset("DUBFORGE_Phi_Growl", [
        (0, "OscA_WtPos", 0.45), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.25), (3, "OscA_Detune", 0.3),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.7), (7, "SubOsc_Level", 0.4),
        (8, "SubOsc_Shape", 0.33), (9, "Filter_Cutoff", 0.55),
        (10, "Filter_Res", 0.4), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.25),
        (14, "Env1_Sustain", 0.6), (15, "Env1_Release", 0.1),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.6), (19, "Macro2", 0.4),
    ])

    presets["WOBBLE"] = _preset("DUBFORGE_Spectral_Tear", [
        (0, "OscA_WtPos", 0.3), (1, "OscA_Level", 0.85),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.2),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.5), (7, "SubOsc_Level", 0.3),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.6),
        (10, "Filter_Res", 0.5), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.3),
        (14, "Env1_Sustain", 0.5), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.5),
    ])

    presets["RIDDIM"] = _preset("DUBFORGE_Riddim_Minimal", [
        (0, "OscA_WtPos", 0.2), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.125), (3, "OscA_Detune", 0.15),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.6), (7, "SubOsc_Level", 0.5),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.5),
        (10, "Filter_Res", 0.35), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.15),
        (14, "Env1_Sustain", 0.3), (15, "Env1_Release", 0.05),
        (16, "Master_Volume", 0.85), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.4), (19, "Macro2", 0.3),
    ])

    presets["FORMANT"] = _preset("DUBFORGE_Formant_Vowel", [
        (0, "OscA_WtPos", 0.5), (1, "OscA_Level", 0.85),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.1),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.4), (7, "SubOsc_Level", 0.3),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.65),
        (10, "Filter_Res", 0.6), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.4),
        (14, "Env1_Sustain", 0.5), (15, "Env1_Release", 0.2),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.7), (19, "Macro2", 0.5),
    ])

    presets["LEAD"] = _preset("DUBFORGE_Fibonacci_FM_Screech", [
        (0, "OscA_WtPos", 0.6), (1, "OscA_Level", 0.75),
        (2, "OscA_Unison", 0.3125), (3, "OscA_Detune", 0.25),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.8), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.8),
        (10, "Filter_Res", 0.2), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.2),
        (14, "Env1_Sustain", 0.65), (15, "Env1_Release", 0.25),
        (16, "Master_Volume", 0.75), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.6),
    ])

    # NEW: Counter-melody pluck preset
    presets["COUNTER"] = _preset("DUBFORGE_Counter_Pluck", [
        (0, "OscA_WtPos", 0.25), (1, "OscA_Level", 0.7),
        (2, "OscA_Unison", 0.125), (3, "OscA_Detune", 0.1),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.4), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.65),
        (10, "Filter_Res", 0.25), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.002), (13, "Env1_Decay", 0.2),
        (14, "Env1_Sustain", 0.15), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.65), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.4), (19, "Macro2", 0.35),
    ])

    presets["CHORDS"] = _preset("DUBFORGE_Golden_Reese", [
        (0, "OscA_WtPos", 0.15), (1, "OscA_Level", 0.8),
        (2, "OscA_Unison", 0.4375), (3, "OscA_Detune", 0.35),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.4), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.7),
        (10, "Filter_Res", 0.1), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.02), (13, "Env1_Decay", 0.4),
        (14, "Env1_Sustain", 0.6), (15, "Env1_Release", 0.3),
        (16, "Master_Volume", 0.7), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.35), (19, "Macro2", 0.15),
    ])

    presets["PAD"] = _preset("DUBFORGE_Granular_Atmosphere", [
        (0, "OscA_WtPos", 0.35), (1, "OscA_Level", 0.6),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.4),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.5), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.6),
        (10, "Filter_Res", 0.15), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.3), (13, "Env1_Decay", 0.6),
        (14, "Env1_Sustain", 0.8), (15, "Env1_Release", 0.5),
        (16, "Master_Volume", 0.55), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.4), (19, "Macro2", 0.3),
    ])

    presets["ARP"] = _preset("DUBFORGE_Phi_Arp", [
        (0, "OscA_WtPos", 0.4), (1, "OscA_Level", 0.7),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.15),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.3), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.75),
        (10, "Filter_Res", 0.2), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.15),
        (14, "Env1_Sustain", 0.1), (15, "Env1_Release", 0.1),
        (16, "Master_Volume", 0.65), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.4),
    ])

    presets["FX"] = _preset("DUBFORGE_Weapon", [
        (0, "OscA_WtPos", 0.7), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.5),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.8), (7, "SubOsc_Level", 0.5),
        (8, "SubOsc_Shape", 0.5), (9, "Filter_Cutoff", 0.9),
        (10, "Filter_Res", 0.3), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.5),
        (14, "Env1_Sustain", 0.0), (15, "Env1_Release", 0.4),
        (16, "Master_Volume", 0.9), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.8), (19, "Macro2", 0.7),
    ])

    presets["RISER"] = _preset("DUBFORGE_Riser_Sweep", [
        (0, "OscA_WtPos", 0.5), (1, "OscA_Level", 0.7),
        (2, "OscA_Unison", 0.375), (3, "OscA_Detune", 0.3),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.6), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.3),
        (10, "Filter_Res", 0.4), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.5), (13, "Env1_Decay", 0.0),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.3),
        (16, "Master_Volume", 0.7), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.3), (19, "Macro2", 0.5),
    ])

    return presets


# ======================================================================
# ALS BUILDER
# ======================================================================

SYNTH_TRACK_ORDER = [
    "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
    "LEAD", "COUNTER", "CHORDS", "PAD", "ARP", "FX", "RISER",
]

TRACK_VOLUMES = {
    "DRUMS": 0.0, "BASS": -3.0, "SUB": -6.0, "GROWL": -4.0,
    "WOBBLE": -5.0, "RIDDIM": -5.0, "FORMANT": -5.0,
    "LEAD": -4.0, "COUNTER": -6.0, "CHORDS": -6.0, "PAD": -9.0,
    "ARP": -8.0, "FX": -6.0, "RISER": -8.0,
}

TRACK_PANS = {
    "DRUMS": 0.0, "BASS": 0.0, "SUB": 0.0, "GROWL": 0.0,
    "WOBBLE": 0.1, "RIDDIM": -0.1, "FORMANT": 0.15,
    "LEAD": 0.0, "COUNTER": -0.15, "CHORDS": 0.0, "PAD": 0.2,
    "ARP": -0.3, "FX": 0.25, "RISER": -0.2,
}


def _build_als_project(
    midi_data: dict[str, list[ALSMidiNote]],
    track_automations: dict[str, list[ALSAutomation]],
) -> ALSProject:
    """Build ALSProject with MIDI tracks, automation, and Serum 2."""
    als_tracks: list[ALSTrack] = []

    for track_name in SYNTH_TRACK_ORDER:
        notes = midi_data.get(track_name, [])
        if not notes:
            continue

        midi_clip = ALSMidiClip(
            name=track_name,
            start_beat=0.0,
            length_beats=float(TOTAL_BEATS),
            notes=notes,
        )

        preset_info = SERUM2_PRESETS.get(track_name)
        display_name = track_name
        if preset_info:
            display_name = f"{track_name} [Serum2: {preset_info[0]}]"

        automations = track_automations.get(track_name, [])

        als_tracks.append(ALSTrack(
            name=display_name,
            track_type="midi",
            color=COLORS.get(track_name, 0),
            volume_db=TRACK_VOLUMES.get(track_name, -6.0),
            pan=TRACK_PANS.get(track_name, 0.0),
            mute=False,
            armed=False,
            device_names=["Serum 2"],
            midi_clips=[midi_clip],
            automations=automations,
        ))

    # Return tracks
    als_tracks.append(ALSTrack(
        name="REVERB", track_type="return",
        color=COLORS["REVERB"], volume_db=-6.0))
    als_tracks.append(ALSTrack(
        name="DELAY", track_type="return",
        color=COLORS["DELAY"], volume_db=-9.0))

    # Scenes
    scenes = [ALSScene(name=s[0], tempo=BPM) for s in SECTIONS]

    # Cue points
    cue_points = [ALSCuePoint(name=s[0], time=s[1] * 4.0)
                  for s in SECTIONS]
    cue_points.append(
        ALSCuePoint(name="GOLDEN_SECTION", time=89 * 4.0))

    return ALSProject(
        name=TRACK_NAME,
        bpm=BPM,
        time_sig_num=TIME_SIG[0],
        time_sig_den=TIME_SIG[1],
        tracks=als_tracks,
        scenes=scenes,
        master_volume_db=0.0,
        notes=(f"DUBFORGE {TRACK_NAME} -- Automation Edition\n"
               f"Key: {KEY_ROOT} minor | BPM: {BPM} | "
               f"Bars: {TOTAL_BARS}\n"
               f"Load Serum 2 on each MIDI track and import "
               f"matching .fxp preset."),
        cue_points=cue_points,
    )


# ======================================================================
# MAIN
# ======================================================================

def main() -> None:
    print(f"\n{'=' * 60}")
    print(f"  DUBFORGE -- {TRACK_NAME} -- MIDI ALS Production")
    print(f"  Key: {KEY_ROOT} minor | BPM: {BPM} | Bars: {TOTAL_BARS}")
    print(f"{'=' * 60}\n")

    output_dir = Path("output")
    preset_dir = output_dir / "presets"
    midi_dir = output_dir / "midi"
    als_dir = output_dir / "ableton"
    for d in [preset_dir, midi_dir, als_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # -- Step 1: Generate MIDI note data ------------------------------
    print("[1/6] Generating MIDI note data...")
    generators = {
        "DRUMS":   _gen_drums,   "BASS":    _gen_bass,
        "SUB":     _gen_sub,     "GROWL":   _gen_growl,
        "WOBBLE":  _gen_wobble,  "RIDDIM":  _gen_riddim,
        "FORMANT": _gen_formant, "LEAD":    _gen_lead,
        "COUNTER": _gen_counter, "CHORDS":  _gen_chords,
        "PAD":     _gen_pad,     "ARP":     _gen_arp,
        "FX":      _gen_fx,      "RISER":   _gen_riser,
    }

    midi_data: dict[str, list[ALSMidiNote]] = {}
    total_notes = 0
    for name, gen_fn in generators.items():
        notes = gen_fn()
        midi_data[name] = notes
        total_notes += len(notes)
        print(f"    {name:12s}: {len(notes):5d} notes")
    print(f"    {'TOTAL':12s}: {total_notes:5d} notes")

    # -- Step 2: Build automation envelopes ---------------------------
    print("\n[2/6] Building automation envelopes...")
    track_automations = _build_track_automations()
    total_auto_pts = 0
    for track_name, autos in track_automations.items():
        pts = sum(len(a.points) for a in autos)
        total_auto_pts += pts
        print(f"    {track_name:12s}: {len(autos):2d} envelopes, "
              f"{pts:5d} points")
    total_envelopes = sum(len(v) for v in track_automations.values())
    print(f"    {'TOTAL':12s}: {total_envelopes:2d} envelopes, "
          f"{total_auto_pts:5d} points")

    # -- Step 3: Generate Serum 2 presets (.fxp) ----------------------
    print("\n[3/6] Generating Serum 2 presets (.fxp)...")
    presets = _build_serum2_presets()
    fxp_presets: list[FXPPreset] = []
    for track_name, fxp in presets.items():
        fxp_path = preset_dir / f"{fxp.name}.fxp"
        write_fxp(fxp, str(fxp_path))
        fxp_presets.append(fxp)
        print(f"    {fxp.name}.fxp ({len(fxp.params)} params)")

    bank = FXPBank(name=f"{TRACK_NAME}_BANK", presets=fxp_presets)
    bank_path = preset_dir / f"{TRACK_NAME}_BANK.fxb"
    write_fxb(bank, str(bank_path))
    print(f"    {bank_path.name} (bank of {len(fxp_presets)})")

    # -- Step 4: Export MIDI file -------------------------------------
    print("\n[4/6] Exporting MIDI file...")
    midi_tracks_for_export: list[tuple[str, list[NoteEvent]]] = []
    for name in SYNTH_TRACK_ORDER:
        als_notes = midi_data.get(name, [])
        if not als_notes:
            continue
        events = [
            NoteEvent(pitch=n.pitch, start_beat=n.time,
                      duration_beats=n.duration, velocity=n.velocity)
            for n in als_notes
        ]
        midi_tracks_for_export.append((name, events))

    midi_path = midi_dir / f"{TRACK_NAME.lower()}.mid"
    write_midi_file(midi_tracks_for_export, str(midi_path),
                    bpm=int(BPM))
    print(f"    {midi_path} ({total_notes} notes, "
          f"{len(midi_tracks_for_export)} tracks)")

    # -- Step 5: Build MIDI ALS file ----------------------------------
    print("\n[5/6] Building MIDI Ableton Live Set...")
    project = _build_als_project(midi_data, track_automations)
    als_path = als_dir / f"{TRACK_NAME}.als"
    write_als(project, str(als_path))

    midi_count = sum(1 for t in project.tracks
                     if t.track_type == "midi")
    return_count = sum(1 for t in project.tracks
                       if t.track_type == "return")
    auto_tracks = sum(1 for t in project.tracks if t.automations)
    print(f"    {als_path}")
    print(f"    {midi_count} MIDI tracks + {return_count} returns")
    print(f"    {auto_tracks} tracks with automation")
    print(f"    {len(project.scenes)} scenes, "
          f"{len(project.cue_points)} cue points")

    # -- Step 6: Open MIDI ALS in Ableton ----------------------------
    print("\n[6/6] Opening MIDI ALS in Ableton Live...")
    abs_als = str(als_path.resolve())
    if sys.platform == "win32":
        os.startfile(abs_als)
        print(f"    Launched: {abs_als}")
    else:
        import subprocess
        subprocess.Popen(["open", abs_als])
        print(f"    Launched: {abs_als}")

    # -- Summary ------------------------------------------------------
    print(f"\n{'=' * 60}")
    print(f"  DONE -- {TRACK_NAME} (MIDI ALS Production)")
    print(f"{'=' * 60}")
    print(f"\n  V11 Features:")
    print(f"    - {total_notes} MIDI notes across "
          f"{len(midi_tracks_for_export)} tracks")
    print(f"    - {total_auto_pts} automation points "
          f"across {auto_tracks} tracks")
    print(f"    - Ghost notes + snare rolls in drums")
    print(f"    - Halftime VIP drop with triplet hi-hats")
    print(f"    - Counter-melody track (answering hook)")
    print(f"    - PHI-derived velocity humanization")
    print(f"    - Per-section send automation (reverb + delay)")
    print(f"\n  Outputs:")
    print(f"    MIDI ALS:  {als_path}")
    print(f"    MIDI:      {midi_path}")
    print(f"    Presets:   {preset_dir}/")
    print(f"\n  Workflow:")
    print(f"    1. MIDI ALS auto-opened in Ableton Live")
    print(f"    2. Load Serum 2 on each MIDI track")
    print(f"    3. Import matching .fxp preset from presets/")
    print(f"    4. Press play -- produce in Ableton")
    print(f"\n  Track -> Preset Mapping:")
    for name in SYNTH_TRACK_ORDER:
        preset_info = SERUM2_PRESETS.get(name)
        if preset_info:
            print(f"    {name:12s} -> {preset_info[0]}.fxp")
        else:
            print(f"    {name:12s} -> (Drum Rack)")
    print()


if __name__ == "__main__":
    main()
