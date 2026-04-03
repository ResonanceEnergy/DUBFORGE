#!/usr/bin/env python3
"""Can You See The Apology That Never Came -- V4 MIDI ALS.

MIDI ALS rewrite of the V3 Dojo Mastery track. Strips all Python DSP;
pure MIDI + Serum 2 preset + automation pipeline for Ableton Live.

Song DNA (from V3):
  - D minor, 150 BPM, 432 Hz tuning reference
  - 144 bars (Fibonacci) -- PACK_ALPHA structure
  - 4 drops: FRACTURE (13), MARATHON (34), CLIMAX (21), TRANSCENDENCE (21)
  - Golden section at bar ~89 (middle of Drop 3 CLIMAX)
  - Ascending lead motif: A3 -> C4 -> D4 -> F4
  - Counter-melody: descending answer D4 -> Bb3 -> A3 -> G3
  - 5 riddim types encoded as rhythmic MIDI variations
  - Vocal chop palette: ah/oh/eh/ee/oo as pitched MIDI
  - KS arp whispers in intro/breaks/outro

Mood arc: Defiance x Fracture x Evolution x Transcendence

Lyrics (configs/apology_lyrics.md):
  V1: "In the hollow of midnight, I claw at our fractured screams..."
  CH: "The apology that never came, Sliced open my soul..."
  V2: "Phantoms of us whisper through the ashes of deceit..."
  BR: "Perhaps the agony lingers, a thorn in my core..."
  FC: "The apology that never came, Forged my defiance..."

Output:
  - Apology_V4.als -> MIDI tracks (load Serum 2 presets)
  - apology_v4.mid -> Standard MIDI file
  - presets/*.fxp -> Individual Serum 2 presets
  - presets/Apology_V4_BANK.fxb -> Preset bank
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
TRACK_NAME = "Apology_V4"
BPM = 150.0
KEY_ROOT = "D"
TIME_SIG = (4, 4)
TOTAL_BARS = 144  # Fibonacci: 144
TOTAL_BEATS = TOTAL_BARS * 4  # 576

# -- D minor Pitch Map (432 Hz tuning reference) ----------------------
# 432 Hz tuning: A4 = 432 Hz (vs 440 Hz standard)
# Serum 2 global tune should be set -0.318 semitones (~-32 cents)
MIDI = {
    "D1": 26, "E1": 28, "F1": 29, "G1": 31, "A1": 33,
    "Bb1": 34, "C2": 36,
    "D2": 38, "E2": 40, "F2": 41, "G2": 43, "A2": 45,
    "Bb2": 46, "C3": 48,
    "D3": 50, "E3": 52, "F3": 53, "G3": 55, "A3": 57,
    "Bb3": 58, "C4": 60,
    "D4": 62, "E4": 64, "F4": 65, "G4": 67, "A4": 69,
    "Bb4": 70, "C5": 72,
    "D5": 74, "F5": 77,
}

# Chord voicings (D minor)
CHORD_Dm = [MIDI["D3"], MIDI["F3"], MIDI["A3"]]     # i
CHORD_Gm = [MIDI["G3"], MIDI["Bb3"], MIDI["D4"]]    # iv
CHORD_Am = [MIDI["A3"], MIDI["C4"], MIDI["E4"]]      # v
CHORD_Bb = [MIDI["Bb3"], MIDI["D4"], MIDI["F4"]]     # VI
CHORD_F = [MIDI["F3"], MIDI["A3"], MIDI["C4"]]       # III
CHORD_C = [MIDI["C3"], MIDI["E3"], MIDI["G3"]]       # VII
CHORDS = [CHORD_Dm, CHORD_Gm, CHORD_Bb, CHORD_Am]
CHORDS_DROP = [CHORD_Dm, CHORD_Bb, CHORD_Gm, CHORD_F]  # darker drops
BASS_ROOTS = [MIDI["D2"], MIDI["G2"], MIDI["Bb2"], MIDI["A2"]]
SUB_ROOTS = [MIDI["D1"], MIDI["G1"], MIDI["Bb1"], MIDI["A1"]]

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
TOM_LOW = 45
TOM_HIGH = 50

# -- PACK_ALPHA Section Map -------------------------------------------
# 13 sections, 4 drops, golden section at bar ~89
SEC_INTRO = 0;       INTRO_BARS = 8
SEC_BUILD1 = 8;      BUILD1_BARS = 5        # Fibonacci 5
SEC_DROP1 = 13;      DROP1_BARS = 13        # FRACTURE (Fibonacci 13)
SEC_BREAK1 = 26;     BREAK1_BARS = 5        # Fibonacci 5
SEC_BUILD2 = 31;     BUILD2_BARS = 8        # Fibonacci 8
SEC_DROP2 = 39;      DROP2_BARS = 34        # MARATHON (Fibonacci 34)
SEC_BREAK2 = 73;     BREAK2_BARS = 3        # Fibonacci 3
SEC_BUILD3 = 76;     BUILD3_BARS = 5        # Fibonacci 5
SEC_DROP3 = 81;      DROP3_BARS = 21        # CLIMAX (Fibonacci 21, golden @ bar 89)
SEC_BREAK3 = 102;    BREAK3_BARS = 5        # Fibonacci 5
SEC_BUILD4 = 107;    BUILD4_BARS = 8        # Fibonacci 8
SEC_DROP4 = 115;     DROP4_BARS = 21        # TRANSCENDENCE (Fibonacci 21)
SEC_OUTRO = 136;     OUTRO_BARS = 8

SECTIONS = [
    ("INTRO",               SEC_INTRO,    INTRO_BARS),
    ("BUILD1_DEFIANCE",     SEC_BUILD1,   BUILD1_BARS),
    ("DROP1_FRACTURE",      SEC_DROP1,    DROP1_BARS),
    ("BREAK1_SHATTER",      SEC_BREAK1,   BREAK1_BARS),
    ("BUILD2_EVOLUTION",    SEC_BUILD2,   BUILD2_BARS),
    ("DROP2_MARATHON",      SEC_DROP2,    DROP2_BARS),
    ("BREAK2_BREATH",       SEC_BREAK2,   BREAK2_BARS),
    ("BUILD3_ASCENSION",    SEC_BUILD3,   BUILD3_BARS),
    ("DROP3_CLIMAX",        SEC_DROP3,    DROP3_BARS),
    ("BREAK3_REVELATION",   SEC_BREAK3,   BREAK3_BARS),
    ("BUILD4_TRANSCEND",    SEC_BUILD4,   BUILD4_BARS),
    ("DROP4_TRANSCENDENCE", SEC_DROP4,    DROP4_BARS),
    ("OUTRO_VOID",          SEC_OUTRO,    OUTRO_BARS),
]

# Drop / Build section lists for easy iteration
DROP_SECTIONS = [
    (SEC_DROP1, DROP1_BARS), (SEC_DROP2, DROP2_BARS),
    (SEC_DROP3, DROP3_BARS), (SEC_DROP4, DROP4_BARS),
]
BUILD_SECTIONS = [
    (SEC_BUILD1, BUILD1_BARS), (SEC_BUILD2, BUILD2_BARS),
    (SEC_BUILD3, BUILD3_BARS), (SEC_BUILD4, BUILD4_BARS),
]
BREAK_SECTIONS = [
    (SEC_BREAK1, BREAK1_BARS), (SEC_BREAK2, BREAK2_BARS),
    (SEC_BREAK3, BREAK3_BARS),
]

# -- Lead Motif: ascending A3 -> C4 -> D4 -> F4 ----------------------
LEAD_MOTIF = [
    # 4-bar ascending phrase
    (0.0, "A3", 1.5), (1.5, "C4", 1.0), (2.5, "D4", 1.5),
    (4.0, "F4", 2.0), (6.0, "D4", 1.0), (7.0, "C4", 1.0),
    # 4-bar development
    (8.0, "A3", 1.0), (9.0, "D4", 1.5), (10.5, "F4", 1.5),
    (12.0, "A4", 2.0), (14.0, "F4", 1.0), (15.0, "D4", 1.0),
]

# -- Counter-Melody: descending answer D4 -> Bb3 -> A3 -> G3 ---------
COUNTER_MELODY = [
    (1.0, "D4", 0.75), (2.5, "Bb3", 0.75), (4.0, "A3", 1.0),
    (5.5, "G3", 0.75), (6.5, "F3", 0.5),
    (9.0, "Bb3", 0.75), (10.0, "A3", 0.75), (11.5, "G3", 1.0),
    (13.0, "F3", 0.75), (14.0, "E3", 0.5), (15.0, "D3", 1.0),
]

# -- Vocal Chop Pattern -----------------------------------------------
VOCAL_CHOP_PATTERN = [
    (0.0, "D4", 0.25), (0.5, "F4", 0.25), (1.0, "A3", 0.5),
    (2.0, "C4", 0.25), (2.5, "D4", 0.25), (3.0, "F4", 0.5),
    (4.0, "A4", 0.25), (4.5, "G4", 0.25), (5.0, "F4", 0.5),
    (6.0, "D4", 0.25), (6.5, "A3", 0.25), (7.0, "D4", 0.5),
]

# -- KS Arp Pattern (whispers in intro/breaks/outro) ------------------
KS_ARP_PATTERN = [
    (0.0, "D3", 0.5), (0.75, "F3", 0.5), (1.5, "A3", 0.5),
    (2.25, "D4", 0.5), (3.0, "A3", 0.5), (3.75, "F3", 0.5),
    (4.5, "D3", 0.5), (5.25, "Bb3", 0.5), (6.0, "G3", 0.5),
    (6.75, "D3", 0.5), (7.5, "A3", 0.5),
]

# -- Track Colors (Ableton color indices) ------------------------------
COLORS = {
    "DRUMS": 69, "BASS": 24, "SUB": 25, "GROWL": 60,
    "WOBBLE": 61, "RIDDIM": 62, "FORMANT": 63, "LEAD": 17,
    "COUNTER": 19, "VOCAL_CHOP": 16, "CHORDS": 20, "PAD": 26,
    "ARP": 18, "FX": 14, "RISER": 15, "REVERB": 50, "DELAY": 52,
}

# Serum 2 preset mapping
SERUM2_PRESETS = {
    "BASS":       ("APOLOGY_Defiant_Sub",            "Aggressive sub bass"),
    "SUB":        ("APOLOGY_Void_Sub",               "Pure 432Hz sine sub"),
    "GROWL":      ("APOLOGY_Fracture_Growl",         "Growl resample bass"),
    "WOBBLE":     ("APOLOGY_Agony_Wobble",           "Deep wobble bass"),
    "RIDDIM":     ("APOLOGY_Riddim_Rage",            "5-type riddim bass"),
    "FORMANT":    ("APOLOGY_Phantom_Vowel",          "Vowel morph bass"),
    "LEAD":       ("APOLOGY_Screech_Ascend",         "Ascending screech"),
    "COUNTER":    ("APOLOGY_KS_Whisper",             "Karplus-Strong pluck"),
    "VOCAL_CHOP": ("APOLOGY_Cry_Chop",              "Pitched vocal chop"),
    "CHORDS":     ("APOLOGY_Dark_Reese",             "Dark minor reese"),
    "PAD":        ("APOLOGY_Void_Atmosphere",        "Dark evolving pad"),
    "ARP":        ("APOLOGY_Ghost_Arp",              "Ethereal arp"),
    "FX":         ("APOLOGY_Impact_Boom",            "Sub boom impact"),
    "RISER":      ("APOLOGY_Harmonic_Rise",          "Harmonic build riser"),
}


# ======================================================================
# VELOCITY HUMANIZATION
# ======================================================================

def _humanize_vel(base_vel: int, beat_pos: float,
                  strength: float = 0.15) -> int:
    """PHI-derived velocity variation."""
    offset = math.sin(beat_pos * PHI * 2.0) * base_vel * strength
    return max(1, min(127, int(base_vel + offset)))


# ======================================================================
# MIDI NOTE GENERATORS
# ======================================================================

def _gen_drums() -> list[ALSMidiNote]:
    """Drums -- PACK_ALPHA: 4 drops with escalating intensity."""
    notes: list[ALSMidiNote] = []

    def _add(pitch: int, bar: int, beat: float, dur: float = 0.25,
             vel: int = 100) -> None:
        notes.append(ALSMidiNote(
            pitch=pitch, time=bar * 4 + beat, duration=dur, velocity=vel))

    def _snare_roll(bar: int, start_beat: float = 2.0,
                    end_beat: float = 4.0,
                    vel_start: int = 60, vel_end: int = 120) -> None:
        steps = int((end_beat - start_beat) / 0.125)
        for i in range(steps):
            v = vel_start + int(
                (vel_end - vel_start) * i / max(steps - 1, 1))
            _add(SNARE, bar, start_beat + i * 0.125, 0.125, v)

    def _tom_fill(bar: int) -> None:
        _add(TOM_HIGH, bar, 2.0, 0.25, 95)
        _add(TOM_HIGH, bar, 2.5, 0.25, 90)
        _add(TOM_LOW, bar, 3.0, 0.25, 100)
        _add(TOM_LOW, bar, 3.5, 0.25, 95)

    for sec_name, sec_start, sec_bars in SECTIONS:
        for bar_offset in range(sec_bars):
            bar = sec_start + bar_offset
            is_last_bar = (bar_offset == sec_bars - 1)

            # -- INTRO: sparse -- building hi-hats -----------------------
            if sec_name == "INTRO":
                if bar_offset < 4:
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                             _humanize_vel(55, eighth * 0.5))
                else:
                    _add(KICK, bar, 0.0, 0.5, 85)
                    _add(KICK, bar, 2.0, 0.5, 75)
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                             _humanize_vel(65, eighth * 0.5))
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 70, 110)
                continue

            # -- BREAKS: minimal + snare build ---------------------------
            if "BREAK" in sec_name:
                _add(KICK, bar, 0.0, 0.5, 65)
                _add(CLOSED_HH, bar, 2.0, 0.25, 45)
                if bar_offset % 2 == 0:
                    _add(PERC1, bar, 1.5, 0.25, 40)
                if is_last_bar:
                    _snare_roll(bar, 2.0, 4.0, 50, 110)
                continue

            # -- BUILDS: accelerating density ----------------------------
            if "BUILD" in sec_name:
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

            # -- OUTRO: dissolving ----------------------------------------
            if sec_name == "OUTRO_VOID":
                fade = max(0.2, 1.0 - bar_offset / sec_bars)
                vel = int(100 * fade)
                _add(KICK, bar, 0.0, 0.5, vel)
                if bar_offset < sec_bars // 2:
                    _add(SNARE, bar, 1.0, 0.5, vel)
                for eighth in range(8):
                    _add(CLOSED_HH, bar, eighth * 0.5, 0.25,
                         int(vel * 0.6))
                continue

            # -- DROPS: escalating intensity across 4 drops ---------------
            is_drop1 = sec_name == "DROP1_FRACTURE"
            is_drop2 = sec_name == "DROP2_MARATHON"
            is_drop3 = sec_name == "DROP3_CLIMAX"
            is_drop4 = sec_name == "DROP4_TRANSCENDENCE"

            # Drop 3 CLIMAX: halftime feel at golden section
            if is_drop3 and bar_offset >= 8:
                _add(KICK, bar, 0.0, 0.5, 120)
                _add(KICK, bar, 1.75, 0.25, 85)
                _add(KICK, bar, 3.5, 0.25, 90)
                _add(SNARE, bar, 2.0, 0.5, 120)
                _add(CLAP, bar, 2.0, 0.25, 105)
                for triplet in range(12):
                    t = triplet * (4.0 / 12.0)
                    is_accent = triplet % 3 == 0
                    _add(CLOSED_HH, bar, t, 0.2,
                         _humanize_vel(85 if is_accent else 60, t))
                _add(SNARE, bar, 0.75, 0.125, 42)
                _add(SNARE, bar, 3.25, 0.125, 38)
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 80, 127)
                continue

            # Drop 4 TRANSCENDENCE: double-time kick
            if is_drop4:
                for eighth in range(8):
                    t = eighth * 0.5
                    _add(KICK, bar, t, 0.25,
                         _humanize_vel(115, t))
                _add(SNARE, bar, 1.0, 0.5, 120)
                _add(SNARE, bar, 3.0, 0.5, 120)
                _add(CLAP, bar, 1.0, 0.25, 105)
                _add(CLAP, bar, 3.0, 0.25, 105)
                for sixteenth in range(16):
                    t = sixteenth * 0.25
                    _add(CLOSED_HH, bar, t, 0.125,
                         _humanize_vel(85, t))
                _add(SNARE, bar, 0.75, 0.125, 45)
                _add(SNARE, bar, 2.75, 0.125, 40)
                if bar_offset == 0:
                    _add(CRASH, bar, 0.0, 1.0, 120)
                if is_last_bar:
                    _tom_fill(bar)
                continue

            # Drop 2 MARATHON: four-on-floor + ghost notes, added perc
            if is_drop2:
                for beat in range(4):
                    _add(KICK, bar, float(beat), 0.5,
                         _humanize_vel(112, float(beat)))
                _add(SNARE, bar, 1.0, 0.5, 112)
                _add(SNARE, bar, 3.0, 0.5, 112)
                _add(CLAP, bar, 1.0, 0.25, 95)
                _add(CLAP, bar, 3.0, 0.25, 95)
                for eighth in range(8):
                    t = eighth * 0.5
                    if eighth % 2 == 1:
                        _add(OPEN_HH, bar, t, 0.25,
                             _humanize_vel(80, t))
                    else:
                        _add(CLOSED_HH, bar, t, 0.25,
                             _humanize_vel(85, t))
                _add(SNARE, bar, 1.75, 0.125, 42)
                _add(SNARE, bar, 3.75, 0.125, 38)
                # Extra percussion every 4 bars in marathon
                if bar_offset % 4 == 0:
                    _add(PERC2, bar, 0.5, 0.25, 55)
                    _add(PERC2, bar, 2.5, 0.25, 50)
                if bar_offset == 0:
                    _add(CRASH, bar, 0.0, 1.0, 105)
                if is_last_bar:
                    _snare_roll(bar, 3.0, 4.0, 70, 120)
                continue

            # Drop 1 FRACTURE & Drop 3 first half: standard drop
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
            _add(SNARE, bar, 1.75, 0.125, 40)
            _add(SNARE, bar, 3.75, 0.125, 35)
            if bar_offset == 0:
                _add(CRASH, bar, 0.0, 1.0, 100)
            if is_last_bar:
                _tom_fill(bar)
                _add(CRASH, bar, 3.875, 0.125, 95)

    return notes


def _gen_bass() -> list[ALSMidiNote]:
    """Bass -- root notes following Dm progression, all 144 bars."""
    notes: list[ALSMidiNote] = []
    for bar in range(TOTAL_BARS):
        chord_idx = (bar // 2) % 4
        root = BASS_ROOTS[chord_idx]
        vel = _humanize_vel(100, float(bar))
        notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                  duration=2.0, velocity=vel))
    return notes


def _gen_sub() -> list[ALSMidiNote]:
    """Sub bass -- drops only, pure D1 weight."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = SUB_ROOTS[chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=4.0, velocity=90))
    return notes


def _gen_growl() -> list[ALSMidiNote]:
    """Growl bass -- Drop 2 marathon + Drop 3/4 intensity."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_DROP2, DROP2_BARS),
                                 (SEC_DROP3, DROP3_BARS),
                                 (SEC_DROP4, DROP4_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["D2"], MIDI["G2"], MIDI["Bb2"],
                    MIDI["A2"]][chord_idx]
            vel = _humanize_vel(105, float(bar_off))
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=vel))
    return notes


def _gen_wobble() -> list[ALSMidiNote]:
    """Wobble bass -- all drops."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = BASS_ROOTS[chord_idx]
            vel = _humanize_vel(95, float(bar_off))
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=vel))
    return notes


def _gen_riddim() -> list[ALSMidiNote]:
    """Riddim -- 5 rhythmic variations across the 4 drops.

    Drop 1: heavy (quarter notes)
    Drop 2: stutter (16ths), triplet overlay
    Drop 3: bounce (dotted 8ths)
    Drop 4: minimal (half notes, wide)
    """
    notes: list[ALSMidiNote] = []

    # Drop 1 FRACTURE: heavy quarter-note riddim
    for bar_off in range(DROP1_BARS):
        bar = SEC_DROP1 + bar_off
        chord_idx = (bar_off // 2) % 4
        root = BASS_ROOTS[chord_idx]
        for beat in [0.0, 1.0, 2.0, 3.0]:
            vel = _humanize_vel(100, beat + bar_off)
            notes.append(ALSMidiNote(
                pitch=root, time=bar * 4 + beat,
                duration=0.75, velocity=vel))

    # Drop 2 MARATHON: stutter 16ths (first half), triplet (second half)
    for bar_off in range(DROP2_BARS):
        bar = SEC_DROP2 + bar_off
        chord_idx = (bar_off // 2) % 4
        root = BASS_ROOTS[chord_idx]
        if bar_off < DROP2_BARS // 2:
            # Stutter 16ths
            for sixteenth in range(0, 16, 2):
                t = sixteenth * 0.25
                vel = _humanize_vel(95, t + bar_off)
                notes.append(ALSMidiNote(
                    pitch=root, time=bar * 4 + t,
                    duration=0.25, velocity=vel))
        else:
            # Triplet riddim
            for triplet in range(6):
                t = triplet * (4.0 / 6.0)
                vel = _humanize_vel(100, t + bar_off)
                notes.append(ALSMidiNote(
                    pitch=root, time=bar * 4 + t,
                    duration=0.5, velocity=vel))

    # Drop 3 CLIMAX: bounce (dotted 8th spacing)
    for bar_off in range(DROP3_BARS):
        bar = SEC_DROP3 + bar_off
        chord_idx = (bar_off // 2) % 4
        root = BASS_ROOTS[chord_idx]
        for sub_beat in [0.0, 0.75, 1.5, 2.25, 3.0]:
            vel = _humanize_vel(105, sub_beat + bar_off)
            notes.append(ALSMidiNote(
                pitch=root, time=bar * 4 + sub_beat,
                duration=0.5, velocity=vel))

    # Drop 4 TRANSCENDENCE: minimal half-note riddim
    for bar_off in range(DROP4_BARS):
        bar = SEC_DROP4 + bar_off
        chord_idx = (bar_off // 2) % 4
        root = BASS_ROOTS[chord_idx]
        for beat in [0.0, 2.0]:
            vel = _humanize_vel(95, beat + bar_off)
            notes.append(ALSMidiNote(
                pitch=root, time=bar * 4 + beat,
                duration=1.5, velocity=vel))

    return notes


def _gen_formant() -> list[ALSMidiNote]:
    """Formant bass -- vowel morphing in Drop 2/3/4."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_DROP2, DROP2_BARS),
                                 (SEC_DROP3, DROP3_BARS),
                                 (SEC_DROP4, DROP4_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["D2"], MIDI["G2"], MIDI["Bb2"],
                    MIDI["A2"]][chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=3.0, velocity=95))
    return notes


def _gen_lead() -> list[ALSMidiNote]:
    """Lead -- ascending motif A3->C4->D4->F4 in all drops."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for rep in range(max(1, sec_bars // 4)):
            base_beat = (sec_start + rep * 4) * 4
            for beat_off, note_name, dur in LEAD_MOTIF:
                abs_time = base_beat + beat_off
                if abs_time >= (sec_start + sec_bars) * 4:
                    break
                vel = _humanize_vel(95, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=abs_time,
                    duration=dur,
                    velocity=vel,
                ))
    return notes


def _gen_counter() -> list[ALSMidiNote]:
    """Counter-melody -- descending answer in drops."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for rep in range(max(1, sec_bars // 4)):
            base_beat = (sec_start + rep * 4) * 4
            for beat_off, note_name, dur in COUNTER_MELODY:
                abs_time = base_beat + beat_off
                if abs_time >= (sec_start + sec_bars) * 4:
                    break
                vel = _humanize_vel(75, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=abs_time,
                    duration=dur,
                    velocity=vel,
                ))
    return notes


def _gen_vocal_chop() -> list[ALSMidiNote]:
    """Vocal chop -- pitched rhythmic hits in drops."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for bar_off in range(0, sec_bars, 2):
            bar = sec_start + bar_off
            base_beat = bar * 4
            for beat_off, note_name, dur in VOCAL_CHOP_PATTERN:
                abs_time = base_beat + beat_off
                if abs_time >= (sec_start + sec_bars) * 4:
                    break
                vel = _humanize_vel(85, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=abs_time,
                    duration=dur,
                    velocity=vel,
                ))
    return notes


def _gen_chords() -> list[ALSMidiNote]:
    """Chords -- dark minor voicings in drops."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            for pitch in CHORDS_DROP[chord_idx]:
                vel = _humanize_vel(85, float(bar_off))
                notes.append(ALSMidiNote(
                    pitch=pitch, time=bar * 4,
                    duration=2.0, velocity=vel))
    return notes


def _gen_pad() -> list[ALSMidiNote]:
    """Pad -- sustained dark chords in intro/breaks/builds/outro."""
    notes: list[ALSMidiNote] = []
    pad_sections = (
        [(SEC_INTRO, INTRO_BARS)]
        + BREAK_SECTIONS
        + BUILD_SECTIONS
        + [(SEC_OUTRO, OUTRO_BARS)]
    )
    for sec_start, sec_bars in pad_sections:
        for bar_off in range(0, sec_bars, 2):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            dur = min(8.0, float((sec_bars - bar_off) * 4))
            for pitch in CHORDS[chord_idx]:
                vel = _humanize_vel(60, float(bar_off))
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,
                    time=bar * 4,
                    duration=dur,
                    velocity=vel))
    return notes


def _gen_arp() -> list[ALSMidiNote]:
    """Arp -- KS whispers in intro/breaks/outro + 16th runs in drops."""
    notes: list[ALSMidiNote] = []

    # KS whispers in atmospheric sections
    whisper_sections = (
        [(SEC_INTRO, INTRO_BARS)]
        + BREAK_SECTIONS
        + [(SEC_OUTRO, OUTRO_BARS)]
    )
    for sec_start, sec_bars in whisper_sections:
        for bar_off in range(0, sec_bars, 2):
            bar = sec_start + bar_off
            base_beat = bar * 4
            for beat_off, note_name, dur in KS_ARP_PATTERN:
                abs_time = base_beat + beat_off
                if abs_time >= (sec_start + sec_bars) * 4:
                    break
                vel = _humanize_vel(50, beat_off)
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=abs_time,
                    duration=dur,
                    velocity=vel,
                ))

    # 16th-note arpeggiation in drops
    for sec_start, sec_bars in DROP_SECTIONS:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            chord_notes = CHORDS[chord_idx]
            arp_notes = chord_notes + [chord_notes[0] + 12]
            for sixteenth in range(16):
                pitch = arp_notes[sixteenth % len(arp_notes)]
                t = sixteenth * 0.25
                vel = _humanize_vel(
                    65 + (sixteenth % 4 == 0) * 15, t)
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,
                    time=bar * 4 + t,
                    duration=0.25,
                    velocity=vel))
    return notes


def _gen_fx() -> list[ALSMidiNote]:
    """FX -- impacts on drops, stutter in builds, reverse cues."""
    notes: list[ALSMidiNote] = []
    # Impact hits at each drop entry
    for sec_start, _ in DROP_SECTIONS:
        notes.append(ALSMidiNote(pitch=MIDI["D3"],
                                  time=sec_start * 4,
                                  duration=2.0, velocity=120))
    # Stutter FX in builds (last 2 bars)
    for sec_start, sec_bars in BUILD_SECTIONS:
        for bar_off in range(max(0, sec_bars - 2), sec_bars):
            bar = sec_start + bar_off
            for eighth in range(8):
                vel = _humanize_vel(80, eighth * 0.5)
                notes.append(ALSMidiNote(
                    pitch=MIDI["A3"],
                    time=bar * 4 + eighth * 0.5,
                    duration=0.25, velocity=vel))
    # Reverse crash cue before each drop
    for sec_start, _ in DROP_SECTIONS:
        if sec_start > 0:
            notes.append(ALSMidiNote(
                pitch=MIDI["D5"],
                time=(sec_start - 1) * 4 + 2.0,
                duration=2.0, velocity=100))
    return notes


def _gen_riser() -> list[ALSMidiNote]:
    """Riser -- ascending pitch sweep in build sections."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in BUILD_SECTIONS:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            pitch = MIDI["D3"] + bar_off * 3
            notes.append(ALSMidiNote(
                pitch=min(pitch, 96),
                time=bar * 4,
                duration=4.0,
                velocity=70 + bar_off * 5))
    return notes


# ======================================================================
# AUTOMATION SYSTEM
# ======================================================================

def _build_sidechain_auto(param: str, sec_start: int,
                          sec_bars: int,
                          duck_depth: float = 0.3) -> ALSAutomation:
    """Sidechain-style volume ducking."""
    pts: list[ALSAutomationPoint] = []
    for bar_off in range(sec_bars):
        bar = sec_start + bar_off
        for beat in range(4):
            t = bar * 4 + beat
            pts.append(ALSAutomationPoint(
                time=float(t), value=1.0 - duck_depth))
            pts.append(ALSAutomationPoint(
                time=float(t) + 0.1, value=1.0))
    return ALSAutomation(parameter_name=param, points=pts)


def _build_track_automations() -> dict[str, list[ALSAutomation]]:
    """Per-track automation envelopes for PACK_ALPHA."""
    auto: dict[str, list[ALSAutomation]] = {}

    # -- BASS: filter cutoff per drop ----------------------------------
    bass_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        bass_autos.append(make_lp_sweep_automation(
            "Filter_Cutoff",
            sec_start * 4.0, (sec_start + min(4, sec_bars)) * 4.0,
            closed_val=0.2, open_val=0.75))
    auto["BASS"] = bass_autos

    # -- SUB: sidechain ducking ----------------------------------------
    sub_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        sub_autos.append(
            _build_sidechain_auto("Volume", sec_start, sec_bars))
    auto["SUB"] = sub_autos

    # -- WOBBLE: sine LFO on filter cutoff -----------------------------
    wobble_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        wobble_autos.append(make_sine_automation(
            "Filter_Cutoff",
            sec_start * 4.0, (sec_start + sec_bars) * 4.0,
            min_val=0.2, max_val=0.85,
            cycles=sec_bars * 2,
            resolution=sec_bars * 8))
    auto["WOBBLE"] = wobble_autos

    # -- GROWL: sawtooth filter + macro ramp ---------------------------
    growl_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_DROP2, DROP2_BARS),
                                 (SEC_DROP3, DROP3_BARS),
                                 (SEC_DROP4, DROP4_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        growl_autos.append(make_sawtooth_automation(
            "Filter_Cutoff", start_b, end_b,
            min_val=0.15, max_val=0.8,
            cycles=sec_bars * 2,
            resolution=sec_bars * 8))
        growl_autos.append(make_ramp_automation(
            "Macro1", start_b, end_b, 0.2, 0.9))
    auto["GROWL"] = growl_autos

    # -- FORMANT: sine Macro1 modulation -------------------------------
    formant_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in [(SEC_DROP2, DROP2_BARS),
                                 (SEC_DROP3, DROP3_BARS),
                                 (SEC_DROP4, DROP4_BARS)]:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        formant_autos.append(make_sine_automation(
            "Macro1", start_b, end_b,
            min_val=0.1, max_val=0.9,
            cycles=max(1, sec_bars // 4),
            resolution=sec_bars * 4))
    auto["FORMANT"] = formant_autos

    # -- LEAD: reverb send per drop ------------------------------------
    lead_send: list[tuple[int, int, float]] = [
        (SEC_DROP1, DROP1_BARS, 0.5),
        (SEC_DROP2, DROP2_BARS, 0.55),
        (SEC_DROP3, DROP3_BARS, 0.3),
        (SEC_DROP4, DROP4_BARS, 0.45),
    ]
    auto["LEAD"] = [
        make_section_send_automation("Send_A", lead_send, TOTAL_BARS),
    ]

    # -- COUNTER: reverb send ------------------------------------------
    counter_send: list[tuple[int, int, float]] = [
        (SEC_DROP1, DROP1_BARS, 0.45),
        (SEC_DROP2, DROP2_BARS, 0.5),
        (SEC_DROP3, DROP3_BARS, 0.35),
        (SEC_DROP4, DROP4_BARS, 0.4),
    ]
    auto["COUNTER"] = [
        make_section_send_automation("Send_A", counter_send, TOTAL_BARS),
    ]

    # -- VOCAL_CHOP: delay send ----------------------------------------
    chop_send: list[tuple[int, int, float]] = [
        (SEC_DROP1, DROP1_BARS, 0.35),
        (SEC_DROP2, DROP2_BARS, 0.4),
        (SEC_DROP3, DROP3_BARS, 0.5),
        (SEC_DROP4, DROP4_BARS, 0.55),
    ]
    auto["VOCAL_CHOP"] = [
        make_section_send_automation("Send_B", chop_send, TOTAL_BARS),
    ]

    # -- CHORDS: LP filter sweep + reverb send -------------------------
    chord_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in DROP_SECTIONS:
        chord_autos.append(make_lp_sweep_automation(
            "Filter_Cutoff",
            sec_start * 4.0, (sec_start + min(4, sec_bars)) * 4.0,
            closed_val=0.4, open_val=0.85))
    chord_send: list[tuple[int, int, float]] = [
        (SEC_DROP1, DROP1_BARS, 0.4),
        (SEC_DROP2, DROP2_BARS, 0.35),
        (SEC_DROP3, DROP3_BARS, 0.3),
        (SEC_DROP4, DROP4_BARS, 0.4),
    ]
    chord_autos.append(
        make_section_send_automation("Send_A", chord_send, TOTAL_BARS))
    auto["CHORDS"] = chord_autos

    # -- PAD: filter opening + heavy reverb send -----------------------
    pad_autos: list[ALSAutomation] = []
    pad_autos.append(make_lp_sweep_automation(
        "Filter_Cutoff",
        SEC_INTRO * 4.0, (SEC_INTRO + INTRO_BARS) * 4.0,
        closed_val=0.1, open_val=0.65))
    pad_send_sections: list[tuple[int, int, float]] = [
        (SEC_INTRO, INTRO_BARS, 0.75),
        (SEC_BREAK1, BREAK1_BARS, 0.7),
        (SEC_BREAK2, BREAK2_BARS, 0.7),
        (SEC_BREAK3, BREAK3_BARS, 0.7),
        (SEC_OUTRO, OUTRO_BARS, 0.8),
    ]
    pad_autos.append(
        make_section_send_automation(
            "Send_A", pad_send_sections, TOTAL_BARS))
    auto["PAD"] = pad_autos

    # -- ARP: delay send -----------------------------------------------
    arp_send: list[tuple[int, int, float]] = [
        (SEC_INTRO, INTRO_BARS, 0.6),
        (SEC_BREAK1, BREAK1_BARS, 0.55),
        (SEC_BREAK2, BREAK2_BARS, 0.55),
        (SEC_BREAK3, BREAK3_BARS, 0.6),
        (SEC_DROP1, DROP1_BARS, 0.4),
        (SEC_DROP2, DROP2_BARS, 0.4),
        (SEC_DROP3, DROP3_BARS, 0.35),
        (SEC_DROP4, DROP4_BARS, 0.4),
        (SEC_OUTRO, OUTRO_BARS, 0.65),
    ]
    auto["ARP"] = [
        make_section_send_automation("Send_B", arp_send, TOTAL_BARS),
    ]

    # -- RISER: LP sweep + volume ramp during builds -------------------
    riser_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in BUILD_SECTIONS:
        start_b = sec_start * 4.0
        end_b = (sec_start + sec_bars) * 4.0
        riser_autos.append(make_lp_sweep_automation(
            "Filter_Cutoff", start_b, end_b, 0.1, 1.0, curve=0.5))
        riser_autos.append(make_ramp_automation(
            "Volume", start_b, end_b, 0.2, 1.0))
    auto["RISER"] = riser_autos

    # -- RIDDIM: macro1 sawtooth modulation ----------------------------
    riddim_autos: list[ALSAutomation] = []
    for sec_start, sec_bars in DROP_SECTIONS:
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
    """Generate Serum 2 .fxp presets -- 432 Hz tuning reference."""
    presets: dict[str, FXPPreset] = {}

    # Master_Tune 0.4841 = -32 cents offset for 432Hz tuning
    TUNE_432 = 0.4841

    def _preset(name: str,
                params: list[tuple[int, str, float]]) -> FXPPreset:
        return FXPPreset(
            name=name,
            params=[VSTParam(index=i, name=n, value=v)
                    for i, n, v in params],
        )

    presets["BASS"] = _preset("APOLOGY_Defiant_Sub", [
        (0, "OscA_WtPos", 0.05), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0625), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.15), (7, "SubOsc_Level", 0.85),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.38),
        (10, "Filter_Res", 0.18), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.008), (13, "Env1_Decay", 0.28),
        (14, "Env1_Sustain", 0.72), (15, "Env1_Release", 0.18),
        (16, "Master_Volume", 0.88), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.38), (19, "Macro2", 0.18),
    ])

    presets["SUB"] = _preset("APOLOGY_Void_Sub", [
        (0, "OscA_WtPos", 0.0), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.0), (7, "SubOsc_Level", 1.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.12),
        (10, "Filter_Res", 0.0), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.25),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.92), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.0), (19, "Macro2", 0.0),
    ])

    presets["GROWL"] = _preset("APOLOGY_Fracture_Growl", [
        (0, "OscA_WtPos", 0.52), (1, "OscA_Level", 0.92),
        (2, "OscA_Unison", 0.3125), (3, "OscA_Detune", 0.35),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.75), (7, "SubOsc_Level", 0.35),
        (8, "SubOsc_Shape", 0.33), (9, "Filter_Cutoff", 0.52),
        (10, "Filter_Res", 0.45), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.003), (13, "Env1_Decay", 0.22),
        (14, "Env1_Sustain", 0.55), (15, "Env1_Release", 0.08),
        (16, "Master_Volume", 0.82), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.65), (19, "Macro2", 0.45),
    ])

    presets["WOBBLE"] = _preset("APOLOGY_Agony_Wobble", [
        (0, "OscA_WtPos", 0.35), (1, "OscA_Level", 0.88),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.22),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.52), (7, "SubOsc_Level", 0.28),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.58),
        (10, "Filter_Res", 0.52), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.012), (13, "Env1_Decay", 0.32),
        (14, "Env1_Sustain", 0.48), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.82), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.52), (19, "Macro2", 0.48),
    ])

    presets["RIDDIM"] = _preset("APOLOGY_Riddim_Rage", [
        (0, "OscA_WtPos", 0.22), (1, "OscA_Level", 0.92),
        (2, "OscA_Unison", 0.125), (3, "OscA_Detune", 0.18),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.62), (7, "SubOsc_Level", 0.45),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.48),
        (10, "Filter_Res", 0.38), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.12),
        (14, "Env1_Sustain", 0.28), (15, "Env1_Release", 0.05),
        (16, "Master_Volume", 0.88), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.42), (19, "Macro2", 0.32),
    ])

    presets["FORMANT"] = _preset("APOLOGY_Phantom_Vowel", [
        (0, "OscA_WtPos", 0.55), (1, "OscA_Level", 0.88),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.12),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.42), (7, "SubOsc_Level", 0.28),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.62),
        (10, "Filter_Res", 0.58), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.012), (13, "Env1_Decay", 0.38),
        (14, "Env1_Sustain", 0.48), (15, "Env1_Release", 0.22),
        (16, "Master_Volume", 0.82), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.72), (19, "Macro2", 0.52),
    ])

    presets["LEAD"] = _preset("APOLOGY_Screech_Ascend", [
        (0, "OscA_WtPos", 0.62), (1, "OscA_Level", 0.78),
        (2, "OscA_Unison", 0.3125), (3, "OscA_Detune", 0.28),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.82), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.82),
        (10, "Filter_Res", 0.22), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.003), (13, "Env1_Decay", 0.18),
        (14, "Env1_Sustain", 0.62), (15, "Env1_Release", 0.22),
        (16, "Master_Volume", 0.78), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.52), (19, "Macro2", 0.62),
    ])

    presets["COUNTER"] = _preset("APOLOGY_KS_Whisper", [
        (0, "OscA_WtPos", 0.28), (1, "OscA_Level", 0.68),
        (2, "OscA_Unison", 0.0625), (3, "OscA_Detune", 0.08),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.35), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.62),
        (10, "Filter_Res", 0.22), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.18),
        (14, "Env1_Sustain", 0.12), (15, "Env1_Release", 0.12),
        (16, "Master_Volume", 0.65), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.38), (19, "Macro2", 0.32),
    ])

    presets["VOCAL_CHOP"] = _preset("APOLOGY_Cry_Chop", [
        (0, "OscA_WtPos", 0.68), (1, "OscA_Level", 0.82),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.05),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.32), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.72),
        (10, "Filter_Res", 0.38), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.08),
        (14, "Env1_Sustain", 0.18), (15, "Env1_Release", 0.06),
        (16, "Master_Volume", 0.72), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.58), (19, "Macro2", 0.48),
    ])

    presets["CHORDS"] = _preset("APOLOGY_Dark_Reese", [
        (0, "OscA_WtPos", 0.18), (1, "OscA_Level", 0.82),
        (2, "OscA_Unison", 0.4375), (3, "OscA_Detune", 0.38),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.42), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.65),
        (10, "Filter_Res", 0.12), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.018), (13, "Env1_Decay", 0.42),
        (14, "Env1_Sustain", 0.58), (15, "Env1_Release", 0.28),
        (16, "Master_Volume", 0.72), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.38), (19, "Macro2", 0.18),
    ])

    presets["PAD"] = _preset("APOLOGY_Void_Atmosphere", [
        (0, "OscA_WtPos", 0.42), (1, "OscA_Level", 0.58),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.42),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.52), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.52),
        (10, "Filter_Res", 0.12), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.4), (13, "Env1_Decay", 0.65),
        (14, "Env1_Sustain", 0.78), (15, "Env1_Release", 0.55),
        (16, "Master_Volume", 0.52), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.42), (19, "Macro2", 0.32),
    ])

    presets["ARP"] = _preset("APOLOGY_Ghost_Arp", [
        (0, "OscA_WtPos", 0.38), (1, "OscA_Level", 0.68),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.12),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.28), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.7),
        (10, "Filter_Res", 0.18), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.12),
        (14, "Env1_Sustain", 0.08), (15, "Env1_Release", 0.08),
        (16, "Master_Volume", 0.62), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.48), (19, "Macro2", 0.38),
    ])

    presets["FX"] = _preset("APOLOGY_Impact_Boom", [
        (0, "OscA_WtPos", 0.72), (1, "OscA_Level", 0.92),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.48),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.82), (7, "SubOsc_Level", 0.55),
        (8, "SubOsc_Shape", 0.5), (9, "Filter_Cutoff", 0.88),
        (10, "Filter_Res", 0.28), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.52),
        (14, "Env1_Sustain", 0.0), (15, "Env1_Release", 0.42),
        (16, "Master_Volume", 0.92), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.82), (19, "Macro2", 0.72),
    ])

    presets["RISER"] = _preset("APOLOGY_Harmonic_Rise", [
        (0, "OscA_WtPos", 0.48), (1, "OscA_Level", 0.72),
        (2, "OscA_Unison", 0.375), (3, "OscA_Detune", 0.28),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.58), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0), (9, "Filter_Cutoff", 0.28),
        (10, "Filter_Res", 0.42), (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.52), (13, "Env1_Decay", 0.0),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.28),
        (16, "Master_Volume", 0.72), (17, "Master_Tune", TUNE_432),
        (18, "Macro1", 0.32), (19, "Macro2", 0.48),
    ])

    return presets


# ======================================================================
# ALS BUILDER
# ======================================================================

SYNTH_TRACK_ORDER = [
    "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
    "LEAD", "COUNTER", "VOCAL_CHOP", "CHORDS", "PAD", "ARP",
    "FX", "RISER",
]

TRACK_VOLUMES = {
    "DRUMS": 0.0, "BASS": -3.0, "SUB": -6.0, "GROWL": -3.5,
    "WOBBLE": -5.0, "RIDDIM": -4.5, "FORMANT": -5.0,
    "LEAD": -3.5, "COUNTER": -6.0, "VOCAL_CHOP": -5.0,
    "CHORDS": -6.0, "PAD": -9.0, "ARP": -8.0,
    "FX": -5.0, "RISER": -8.0,
}

TRACK_PANS = {
    "DRUMS": 0.0, "BASS": 0.0, "SUB": 0.0, "GROWL": 0.0,
    "WOBBLE": 0.1, "RIDDIM": -0.1, "FORMANT": 0.15,
    "LEAD": 0.0, "COUNTER": -0.15, "VOCAL_CHOP": 0.2,
    "CHORDS": 0.0, "PAD": -0.2, "ARP": 0.3,
    "FX": -0.25, "RISER": 0.2,
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
        notes=(f"DUBFORGE {TRACK_NAME} -- "
               f"Can You See The Apology That Never Came\n"
               f"Key: {KEY_ROOT} minor (432 Hz) | BPM: {BPM} | "
               f"Bars: {TOTAL_BARS}\n"
               f"PACK_ALPHA: 4 drops (Fracture/Marathon/Climax/"
               f"Transcendence)\n"
               f"Golden section at bar 89 (middle of Drop 3 CLIMAX)\n"
               f"Load Serum 2 on each MIDI track, import matching "
               f".fxp preset.\n"
               f"Set Serum 2 global tune to -32 cents (432 Hz)."),
        cue_points=cue_points,
    )


# ======================================================================
# MAIN
# ======================================================================

def main() -> None:
    print(f"\n{'=' * 60}")
    print(f"  DUBFORGE -- {TRACK_NAME}")
    print(f"  Can You See The Apology That Never Came")
    print(f"  Key: {KEY_ROOT} minor (432 Hz) | BPM: {BPM} | "
          f"Bars: {TOTAL_BARS}")
    print(f"  PACK_ALPHA: 4 Drops -- Fracture / Marathon / "
          f"Climax / Transcendence")
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
        "DRUMS":      _gen_drums,      "BASS":       _gen_bass,
        "SUB":        _gen_sub,        "GROWL":      _gen_growl,
        "WOBBLE":     _gen_wobble,     "RIDDIM":     _gen_riddim,
        "FORMANT":    _gen_formant,    "LEAD":       _gen_lead,
        "COUNTER":    _gen_counter,    "VOCAL_CHOP": _gen_vocal_chop,
        "CHORDS":     _gen_chords,     "PAD":        _gen_pad,
        "ARP":        _gen_arp,        "FX":         _gen_fx,
        "RISER":      _gen_riser,
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
    print(f"  DONE -- {TRACK_NAME}")
    print(f"  Can You See The Apology That Never Came")
    print(f"{'=' * 60}")
    print(f"\n  PACK_ALPHA Structure:")
    for sec_name, sec_start, sec_bars in SECTIONS:
        marker = " <<< GOLDEN SECTION" if sec_start <= 89 < sec_start + sec_bars else ""
        print(f"    Bar {sec_start:3d}-{sec_start + sec_bars:3d}: "
              f"{sec_name} ({sec_bars} bars){marker}")
    print(f"\n  Song DNA:")
    print(f"    - D minor, 150 BPM, 432 Hz tuning")
    print(f"    - 4 drops: Fracture({DROP1_BARS}) -> "
          f"Marathon({DROP2_BARS}) -> Climax({DROP3_BARS}) -> "
          f"Transcendence({DROP4_BARS})")
    print(f"    - Golden section at bar 89")
    print(f"    - Ascending lead motif: A3->C4->D4->F4")
    print(f"    - 5 riddim variations across drops")
    print(f"    - KS arp whispers in intro/breaks/outro")
    print(f"\n  Stats:")
    print(f"    - {total_notes} MIDI notes across "
          f"{len(midi_tracks_for_export)} tracks")
    print(f"    - {total_auto_pts} automation points "
          f"across {auto_tracks} tracks")
    print(f"\n  Outputs:")
    print(f"    MIDI ALS:  {als_path}")
    print(f"    MIDI:      {midi_path}")
    print(f"    Presets:   {preset_dir}/")
    print(f"\n  Workflow:")
    print(f"    1. MIDI ALS auto-opened in Ableton Live")
    print(f"    2. Load Serum 2 on each MIDI track")
    print(f"    3. Import matching .fxp preset from presets/")
    print(f"    4. Set Serum 2 global tune to -32 cents (432 Hz)")
    print(f"    5. Press play -- produce in Ableton")
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
