#!/usr/bin/env python3
"""Wild Ones V10 — Serum 2 MIDI Production.

Eliminates ALL Python DSP synthesis. Generates:
  1. Serum 2 presets (.fxp) for each synth track
  2. ALS file with MIDI tracks + embedded MIDI clips
  3. MIDI file (.mid) for external use

NO audio rendering. Open ALS in Ableton → load Serum 2 on each track → play.
"""
from __future__ import annotations

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
    write_als,
)
from engine.midi_export import NoteEvent, write_midi_file
from engine.fxp_writer import FXPPreset, FXPBank, VSTParam, write_fxp, write_fxb

# ═══════════════════════════════════════════════════════════════════════════
# SONG CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
TRACK_NAME = "Wild_Ones_V10"
BPM = 127.0
KEY_ROOT = "Ab"
TIME_SIG = (4, 4)
TOTAL_BARS = 144  # Fibonacci: 144
TOTAL_BEATS = TOTAL_BARS * 4  # 576

# ── Pitch Map (Ab minor / Cb major) ─────────────────────────────────────
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

# ── Section Map (bar_start, num_bars) ────────────────────────────────────
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

# ── Hook Melody (32-note loop, 8 bars = 32 beats) ───────────────────────
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

# ── Track Colors (Ableton color indices) ────────────────────────────────
COLORS = {
    "DRUMS": 69,   # red
    "BASS": 24,    # orange
    "SUB": 25,     # dark orange
    "GROWL": 60,   # dark red
    "WOBBLE": 61,  # magenta
    "RIDDIM": 62,  # purple
    "FORMANT": 63, # violet
    "LEAD": 17,    # cyan
    "CHORDS": 20,  # blue
    "PAD": 26,     # teal
    "ARP": 18,     # light blue
    "FX": 14,      # yellow
    "RISER": 15,   # gold
    "REVERB": 50,  # slate
    "DELAY": 52,   # grey
}

# Serum 2 preset mapping: track_name -> (preset_name, description)
SERUM2_PRESETS = {
    "BASS":    ("DUBFORGE_Fractal_Sub",            "Phi-harmonic sub bass"),
    "SUB":     ("DUBFORGE_Deep_Sub",               "Pure sine sub"),
    "GROWL":   ("DUBFORGE_Phi_Growl",              "Aggressive growl"),
    "WOBBLE":  ("DUBFORGE_Spectral_Tear",          "Classic wobble bass"),
    "RIDDIM":  ("DUBFORGE_Riddim_Minimal",         "Minimal riddim"),
    "FORMANT": ("DUBFORGE_Formant_Vowel",          "Vowel-shifting bass"),
    "LEAD":    ("DUBFORGE_Fibonacci_FM_Screech",   "FM screech lead"),
    "CHORDS":  ("DUBFORGE_Golden_Reese",           "Supersaw reese chords"),
    "PAD":     ("DUBFORGE_Granular_Atmosphere",    "Lush atmospheric pad"),
    "ARP":     ("DUBFORGE_Phi_Arp",                "Fibonacci-timed arp"),
    "FX":      ("DUBFORGE_Weapon",                 "Impact & FX hits"),
    "RISER":   ("DUBFORGE_Riser_Sweep",            "Build-up riser"),
}


# ═══════════════════════════════════════════════════════════════════════════
# MIDI NOTE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _gen_drums() -> list[ALSMidiNote]:
    """Generate drum MIDI patterns per section."""
    notes: list[ALSMidiNote] = []

    def _add(pitch: int, bar: int, beat: float, dur: float = 0.25,
             vel: int = 100) -> None:
        notes.append(ALSMidiNote(
            pitch=pitch, time=bar * 4 + beat, duration=dur, velocity=vel))

    for sec_name, sec_start, sec_bars in SECTIONS:
        for bar_offset in range(sec_bars):
            bar = sec_start + bar_offset

            if sec_name == "BREAK":
                # Sparse break — kick on 1, light hats
                _add(KICK, bar, 0.0, 0.5, 70)
                _add(CLOSED_HH, bar, 2.0, 0.25, 50)
                continue

            if sec_name == "INTRO":
                # Building intro — hats only first 4 bars, add kick
                if bar_offset < 4:
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25, 60)
                else:
                    _add(KICK, bar, 0.0, 0.5, 90)
                    _add(KICK, bar, 2.0, 0.5, 80)
                    for eighth in range(8):
                        _add(CLOSED_HH, bar, eighth * 0.5, 0.25, 70)
                continue

            if sec_name == "OUTRO":
                # Dissolving outro
                fade = max(0.3, 1.0 - bar_offset / sec_bars)
                vel = int(100 * fade)
                _add(KICK, bar, 0.0, 0.5, vel)
                if bar_offset < sec_bars // 2:
                    _add(SNARE, bar, 1.0, 0.5, vel)
                for eighth in range(8):
                    _add(CLOSED_HH, bar, eighth * 0.5, 0.25, int(vel * 0.7))
                continue

            # Standard patterns for VERSE, CHORUS, VIP, FINAL, PRECHORUS
            is_drop = sec_name in ("CHORUS1", "CHORUS2", "VIP_DROP",
                                    "FINAL_CHORUS")
            is_build = "PRE_CHORUS" in sec_name

            # Kick — four-on-the-floor in drops, half-time in verse
            if is_drop:
                for beat in range(4):
                    _add(KICK, bar, float(beat), 0.5, 110)
            elif is_build:
                _add(KICK, bar, 0.0, 0.5, 95)
                _add(KICK, bar, 1.5, 0.5, 85)
                _add(KICK, bar, 3.0, 0.5, 90)
                # Build density ramp
                if bar_offset > sec_bars // 2:
                    _add(KICK, bar, 0.5, 0.25, 70)
                    _add(KICK, bar, 2.5, 0.25, 70)
            else:
                _add(KICK, bar, 0.0, 0.5, 100)
                _add(KICK, bar, 2.0, 0.5, 90)

            # Snare — beat 2 and 4
            snare_vel = 110 if is_drop else 95
            _add(SNARE, bar, 1.0, 0.5, snare_vel)
            _add(SNARE, bar, 3.0, 0.5, snare_vel)

            # Clap layered with snare in drops
            if is_drop:
                _add(CLAP, bar, 1.0, 0.25, 90)
                _add(CLAP, bar, 3.0, 0.25, 90)

            # Hi-hats — 8th notes, open on offbeats in drops
            for eighth in range(8):
                t = eighth * 0.5
                is_offbeat = eighth % 2 == 1
                if is_drop and is_offbeat:
                    _add(OPEN_HH, bar, t, 0.25, 80)
                else:
                    _add(CLOSED_HH, bar, t, 0.25, 75 if is_offbeat else 85)

            # Crash on section downbeats
            if bar_offset == 0 and is_drop:
                _add(CRASH, bar, 0.0, 1.0, 100)

            # Ride in bridge
            if sec_name == "BRIDGE_GOLDEN":
                _add(RIDE, bar, 0.0, 0.5, 65)
                _add(RIDE, bar, 2.0, 0.5, 55)

    return notes


def _gen_bass() -> list[ALSMidiNote]:
    """Bass — root notes following chord progression, all 144 bars."""
    notes: list[ALSMidiNote] = []
    for bar in range(TOTAL_BARS):
        chord_idx = (bar // 2) % 4
        root = BASS_ROOTS[chord_idx]
        notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                  duration=2.0, velocity=100))
    return notes


def _gen_sub() -> list[ALSMidiNote]:
    """Sub bass — octave below bass, chorus/VIP/final only."""
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
    """Growl bass — VIP and final chorus."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"], MIDI["Db3"]][chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=100))
    return notes


def _gen_wobble() -> list[ALSMidiNote]:
    """Wobble bass — chorus/VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = BASS_ROOTS[chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=2.0, velocity=95))
    return notes


def _gen_riddim() -> list[ALSMidiNote]:
    """Riddim — short staccato gaps in VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = BASS_ROOTS[chord_idx]
            # 3-4 short hits per bar
            for sub_beat in [0.0, 0.75, 1.5, 2.5]:
                notes.append(ALSMidiNote(pitch=root, time=bar * 4 + sub_beat,
                                          duration=0.5, velocity=100))
    return notes


def _gen_formant() -> list[ALSMidiNote]:
    """Formant bass — vowel-shifting, VIP/final."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            root = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"], MIDI["Db3"]][chord_idx]
            notes.append(ALSMidiNote(pitch=root, time=bar * 4,
                                      duration=3.0, velocity=95))
    return notes


def _gen_lead() -> list[ALSMidiNote]:
    """Hook/lead melody — 32-note loop in chorus/VIP/final sections."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for rep in range(sec_bars // 8):
            base_beat = (sec_start + rep * 8) * 4
            for beat_off, note_name, dur in HOOK_MELODY:
                notes.append(ALSMidiNote(
                    pitch=MIDI[note_name],
                    time=base_beat + beat_off,
                    duration=dur,
                    velocity=90,
                ))
    return notes


def _gen_chords() -> list[ALSMidiNote]:
    """Chord voicings — chorus/VIP/final, 3-note triads."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_VIP, VIP_DROP_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            chord_notes = CHORDS[chord_idx]
            for pitch in chord_notes:
                notes.append(ALSMidiNote(
                    pitch=pitch, time=bar * 4,
                    duration=2.0, velocity=82))
    return notes


def _gen_pad() -> list[ALSMidiNote]:
    """Pad — sustained chords in verse/bridge/intro/outro."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_INTRO, INTRO_BARS),
                                 (SEC_VERSE1, VERSE1_BARS),
                                 (SEC_BREAK, BREAK_BARS),
                                 (SEC_VERSE2, VERSE2_BARS),
                                 (SEC_BRIDGE, BRIDGE_BARS),
                                 (SEC_OUTRO, OUTRO_BARS)]:
        # One long sustained chord every 2 bars
        for bar_off in range(0, sec_bars, 2):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            chord_notes = CHORDS[chord_idx]
            for pitch in chord_notes:
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,  # octave up for pad register
                    time=bar * 4,
                    duration=8.0,  # 2 bars sustained
                    velocity=65))
    return notes


def _gen_arp() -> list[ALSMidiNote]:
    """Arp — 16th-note arpeggiation of chords in chorus/bridge."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_CHORUS1, CHORUS1_BARS),
                                 (SEC_CHORUS2, CHORUS2_BARS),
                                 (SEC_BRIDGE, BRIDGE_BARS),
                                 (SEC_FINAL, FINAL_CHORUS_BARS)]:
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            chord_idx = (bar_off // 2) % 4
            chord_notes = CHORDS[chord_idx]
            # 16th note arpeggio cycling through chord tones + octave
            arp_notes = chord_notes + [chord_notes[0] + 12]
            for sixteenth in range(16):
                pitch = arp_notes[sixteenth % len(arp_notes)]
                notes.append(ALSMidiNote(
                    pitch=pitch + 12,  # up an octave
                    time=bar * 4 + sixteenth * 0.25,
                    duration=0.25,
                    velocity=70 + (sixteenth % 4 == 0) * 15))
    return notes


def _gen_fx() -> list[ALSMidiNote]:
    """FX hits — impacts on drop downbeats, fills in builds."""
    notes: list[ALSMidiNote] = []
    # Impact hits on drop entries
    for sec_start in [SEC_CHORUS1, SEC_CHORUS2, SEC_VIP, SEC_FINAL]:
        notes.append(ALSMidiNote(pitch=MIDI["Ab3"], time=sec_start * 4,
                                  duration=2.0, velocity=120))
    # Stutter FX in pre-chorus (last 2 bars)
    for sec_start, sec_bars in [(SEC_PRECHORUS1, PRECHORUS1_BARS),
                                 (SEC_PRECHORUS2, PRECHORUS2_BARS)]:
        for bar_off in range(sec_bars - 2, sec_bars):
            bar = sec_start + bar_off
            for eighth in range(8):
                notes.append(ALSMidiNote(
                    pitch=MIDI["Eb4"],
                    time=bar * 4 + eighth * 0.5,
                    duration=0.25, velocity=80))
    return notes


def _gen_riser() -> list[ALSMidiNote]:
    """Riser — ascending pitch sweep in pre-chorus sections."""
    notes: list[ALSMidiNote] = []
    for sec_start, sec_bars in [(SEC_PRECHORUS1, PRECHORUS1_BARS),
                                 (SEC_PRECHORUS2, PRECHORUS2_BARS)]:
        # Rising pitch over 8 bars
        for bar_off in range(sec_bars):
            bar = sec_start + bar_off
            # Chromatically ascending
            pitch = MIDI["Ab3"] + bar_off * 2
            notes.append(ALSMidiNote(
                pitch=min(pitch, 96),
                time=bar * 4,
                duration=4.0,
                velocity=70 + bar_off * 4))
    return notes


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 PRESET GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _build_serum2_presets() -> dict[str, FXPPreset]:
    """Generate Serum 2 .fxp presets for each synth track."""
    presets: dict[str, FXPPreset] = {}

    # Helper: normalized parameter list
    def _preset(name: str, params: list[tuple[int, str, float]]) -> FXPPreset:
        return FXPPreset(
            name=name,
            params=[VSTParam(index=i, name=n, value=v)
                    for i, n, v in params],
        )

    # BASS — deep sub with harmonic warmth
    presets["BASS"] = _preset("DUBFORGE_Fractal_Sub", [
        (0, "OscA_WtPos", 0.0), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0625), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.0), (7, "SubOsc_Level", 0.8),
        (8, "SubOsc_Shape", 0.0),  # sine
        (9, "Filter_Cutoff", 0.35), (10, "Filter_Res", 0.15),
        (11, "Filter_Type", 0.0),  # LP
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.3),
        (14, "Env1_Sustain", 0.7), (15, "Env1_Release", 0.2),
        (16, "Master_Volume", 0.85), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.35), (19, "Macro2", 0.15),
    ])

    # SUB — pure sine sub
    presets["SUB"] = _preset("DUBFORGE_Deep_Sub", [
        (0, "OscA_WtPos", 0.0), (1, "OscA_Level", 1.0),
        (2, "OscA_Unison", 0.0), (3, "OscA_Detune", 0.0),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.0), (7, "SubOsc_Level", 1.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.15), (10, "Filter_Res", 0.0),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.2),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.9), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.0), (19, "Macro2", 0.0),
    ])

    # GROWL — aggressive waveshaping
    presets["GROWL"] = _preset("DUBFORGE_Phi_Growl", [
        (0, "OscA_WtPos", 0.45), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.25), (3, "OscA_Detune", 0.3),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.7), (7, "SubOsc_Level", 0.4),
        (8, "SubOsc_Shape", 0.33),
        (9, "Filter_Cutoff", 0.55), (10, "Filter_Res", 0.4),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.25),
        (14, "Env1_Sustain", 0.6), (15, "Env1_Release", 0.1),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.6), (19, "Macro2", 0.4),
    ])

    # WOBBLE — LFO-modulated cutoff
    presets["WOBBLE"] = _preset("DUBFORGE_Spectral_Tear", [
        (0, "OscA_WtPos", 0.3), (1, "OscA_Level", 0.85),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.2),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.5), (7, "SubOsc_Level", 0.3),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.6), (10, "Filter_Res", 0.5),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.3),
        (14, "Env1_Sustain", 0.5), (15, "Env1_Release", 0.15),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.5),
    ])

    # RIDDIM — short staccato
    presets["RIDDIM"] = _preset("DUBFORGE_Riddim_Minimal", [
        (0, "OscA_WtPos", 0.2), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.125), (3, "OscA_Detune", 0.15),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.6), (7, "SubOsc_Level", 0.5),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.5), (10, "Filter_Res", 0.35),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.15),
        (14, "Env1_Sustain", 0.3), (15, "Env1_Release", 0.05),
        (16, "Master_Volume", 0.85), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.4), (19, "Macro2", 0.3),
    ])

    # FORMANT — vowel-shifting
    presets["FORMANT"] = _preset("DUBFORGE_Formant_Vowel", [
        (0, "OscA_WtPos", 0.5), (1, "OscA_Level", 0.85),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.1),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.4), (7, "SubOsc_Level", 0.3),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.65), (10, "Filter_Res", 0.6),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.01), (13, "Env1_Decay", 0.4),
        (14, "Env1_Sustain", 0.5), (15, "Env1_Release", 0.2),
        (16, "Master_Volume", 0.8), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.7), (19, "Macro2", 0.5),
    ])

    # LEAD — FM screech
    presets["LEAD"] = _preset("DUBFORGE_Fibonacci_FM_Screech", [
        (0, "OscA_WtPos", 0.6), (1, "OscA_Level", 0.75),
        (2, "OscA_Unison", 0.3125), (3, "OscA_Detune", 0.25),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.8), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.8), (10, "Filter_Res", 0.2),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.005), (13, "Env1_Decay", 0.2),
        (14, "Env1_Sustain", 0.65), (15, "Env1_Release", 0.25),
        (16, "Master_Volume", 0.75), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.6),
    ])

    # CHORDS — supersaw reese
    presets["CHORDS"] = _preset("DUBFORGE_Golden_Reese", [
        (0, "OscA_WtPos", 0.15), (1, "OscA_Level", 0.8),
        (2, "OscA_Unison", 0.4375), (3, "OscA_Detune", 0.35),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.4), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.7), (10, "Filter_Res", 0.1),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.02), (13, "Env1_Decay", 0.4),
        (14, "Env1_Sustain", 0.6), (15, "Env1_Release", 0.3),
        (16, "Master_Volume", 0.7), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.35), (19, "Macro2", 0.15),
    ])

    # PAD — atmospheric
    presets["PAD"] = _preset("DUBFORGE_Granular_Atmosphere", [
        (0, "OscA_WtPos", 0.35), (1, "OscA_Level", 0.6),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.4),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.5), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.6), (10, "Filter_Res", 0.15),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.3), (13, "Env1_Decay", 0.6),
        (14, "Env1_Sustain", 0.8), (15, "Env1_Release", 0.5),
        (16, "Master_Volume", 0.55), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.4), (19, "Macro2", 0.3),
    ])

    # ARP — bright pluck
    presets["ARP"] = _preset("DUBFORGE_Phi_Arp", [
        (0, "OscA_WtPos", 0.4), (1, "OscA_Level", 0.7),
        (2, "OscA_Unison", 0.1875), (3, "OscA_Detune", 0.15),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.3), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.75), (10, "Filter_Res", 0.2),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.15),
        (14, "Env1_Sustain", 0.1), (15, "Env1_Release", 0.1),
        (16, "Master_Volume", 0.65), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.5), (19, "Macro2", 0.4),
    ])

    # FX — weapon impact
    presets["FX"] = _preset("DUBFORGE_Weapon", [
        (0, "OscA_WtPos", 0.7), (1, "OscA_Level", 0.9),
        (2, "OscA_Unison", 0.5), (3, "OscA_Detune", 0.5),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.8), (7, "SubOsc_Level", 0.5),
        (8, "SubOsc_Shape", 0.5),
        (9, "Filter_Cutoff", 0.9), (10, "Filter_Res", 0.3),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.001), (13, "Env1_Decay", 0.5),
        (14, "Env1_Sustain", 0.0), (15, "Env1_Release", 0.4),
        (16, "Master_Volume", 0.9), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.8), (19, "Macro2", 0.7),
    ])

    # RISER — sweep
    presets["RISER"] = _preset("DUBFORGE_Riser_Sweep", [
        (0, "OscA_WtPos", 0.5), (1, "OscA_Level", 0.7),
        (2, "OscA_Unison", 0.375), (3, "OscA_Detune", 0.3),
        (4, "OscA_Pan", 0.5), (5, "OscA_Semi", 0.5),
        (6, "OscB_Level", 0.6), (7, "SubOsc_Level", 0.0),
        (8, "SubOsc_Shape", 0.0),
        (9, "Filter_Cutoff", 0.3), (10, "Filter_Res", 0.4),
        (11, "Filter_Type", 0.0),
        (12, "Env1_Attack", 0.5), (13, "Env1_Decay", 0.0),
        (14, "Env1_Sustain", 1.0), (15, "Env1_Release", 0.3),
        (16, "Master_Volume", 0.7), (17, "Master_Tune", 0.5),
        (18, "Macro1", 0.3), (19, "Macro2", 0.5),
    ])

    return presets


# ═══════════════════════════════════════════════════════════════════════════
# ALS BUILDER
# ═══════════════════════════════════════════════════════════════════════════

SYNTH_TRACK_ORDER = [
    "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
    "LEAD", "CHORDS", "PAD", "ARP", "FX", "RISER",
]

# Volume levels per track (dB)
TRACK_VOLUMES = {
    "DRUMS": 0.0, "BASS": -3.0, "SUB": -6.0, "GROWL": -4.0,
    "WOBBLE": -5.0, "RIDDIM": -5.0, "FORMANT": -5.0,
    "LEAD": -4.0, "CHORDS": -6.0, "PAD": -9.0,
    "ARP": -8.0, "FX": -6.0, "RISER": -8.0,
}

# Pan positions (-1.0 to 1.0)
TRACK_PANS = {
    "DRUMS": 0.0, "BASS": 0.0, "SUB": 0.0, "GROWL": 0.0,
    "WOBBLE": 0.1, "RIDDIM": -0.1, "FORMANT": 0.15,
    "LEAD": 0.0, "CHORDS": 0.0, "PAD": 0.2,
    "ARP": -0.3, "FX": 0.25, "RISER": -0.2,
}


def _build_als_project(
    midi_data: dict[str, list[ALSMidiNote]],
) -> ALSProject:
    """Build ALSProject with MIDI tracks for Serum 2."""
    als_tracks: list[ALSTrack] = []

    for track_name in SYNTH_TRACK_ORDER:
        notes = midi_data.get(track_name, [])
        if not notes:
            continue

        # Create a single MIDI clip spanning the full arrangement
        midi_clip = ALSMidiClip(
            name=track_name,
            start_beat=0.0,
            length_beats=float(TOTAL_BEATS),
            notes=notes,
        )

        # Track name shows the Serum 2 preset to load
        preset_info = SERUM2_PRESETS.get(track_name)
        display_name = track_name
        if preset_info:
            display_name = f"{track_name} [Serum2: {preset_info[0]}]"

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
    cue_points = [ALSCuePoint(name=s[0], time=s[1] * 4.0) for s in SECTIONS]
    # Golden section marker
    cue_points.append(ALSCuePoint(name="GOLDEN_SECTION", time=89 * 4.0))

    return ALSProject(
        name=TRACK_NAME,
        bpm=BPM,
        time_sig_num=TIME_SIG[0],
        time_sig_den=TIME_SIG[1],
        tracks=als_tracks,
        scenes=scenes,
        master_volume_db=0.0,
        notes=(f"DUBFORGE {TRACK_NAME} — Serum 2 MIDI Production\n"
               f"Key: {KEY_ROOT} minor | BPM: {BPM} | Bars: {TOTAL_BARS}\n"
               f"Load Serum 2 on each MIDI track and import matching .fxp preset."),
        cue_points=cue_points,
    )


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"\n{'=' * 60}")
    print(f"  DUBFORGE — {TRACK_NAME} — Serum 2 MIDI Production")
    print(f"  Key: {KEY_ROOT} minor | BPM: {BPM} | Bars: {TOTAL_BARS}")
    print(f"  NO Python DSP — Pure MIDI + Serum 2")
    print(f"{'=' * 60}\n")

    output_dir = Path("output")
    preset_dir = output_dir / "presets"
    midi_dir = output_dir / "midi"
    als_dir = output_dir / "ableton"
    for d in [preset_dir, midi_dir, als_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Generate MIDI note data ──────────────────────────────────
    print("[1/4] Generating MIDI note data...")
    generators = {
        "DRUMS":   _gen_drums,
        "BASS":    _gen_bass,
        "SUB":     _gen_sub,
        "GROWL":   _gen_growl,
        "WOBBLE":  _gen_wobble,
        "RIDDIM":  _gen_riddim,
        "FORMANT": _gen_formant,
        "LEAD":    _gen_lead,
        "CHORDS":  _gen_chords,
        "PAD":     _gen_pad,
        "ARP":     _gen_arp,
        "FX":      _gen_fx,
        "RISER":   _gen_riser,
    }

    midi_data: dict[str, list[ALSMidiNote]] = {}
    total_notes = 0
    for name, gen_fn in generators.items():
        notes = gen_fn()
        midi_data[name] = notes
        total_notes += len(notes)
        print(f"    {name:12s}: {len(notes):5d} notes")
    print(f"    {'TOTAL':12s}: {total_notes:5d} notes")

    # ── Step 2: Generate Serum 2 presets ─────────────────────────────────
    print("\n[2/4] Generating Serum 2 presets (.fxp)...")
    presets = _build_serum2_presets()
    fxp_presets: list[FXPPreset] = []
    for track_name, fxp in presets.items():
        fxp_path = preset_dir / f"{fxp.name}.fxp"
        write_fxp(fxp, str(fxp_path))
        fxp_presets.append(fxp)
        print(f"    {fxp.name}.fxp ({len(fxp.params)} params)")

    # Write bank file
    bank = FXPBank(name=f"{TRACK_NAME}_BANK", presets=fxp_presets)
    bank_path = preset_dir / f"{TRACK_NAME}_BANK.fxb"
    write_fxb(bank, str(bank_path))
    print(f"    {bank_path.name} (bank of {len(fxp_presets)})")

    # ── Step 3: Export MIDI file ─────────────────────────────────────────
    print("\n[3/4] Exporting MIDI file...")
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
    write_midi_file(midi_tracks_for_export, str(midi_path), bpm=int(BPM))
    print(f"    {midi_path} ({total_notes} notes, {len(midi_tracks_for_export)} tracks)")

    # ── Step 4: Build ALS file ───────────────────────────────────────────
    print("\n[4/4] Building Ableton Live Set...")
    project = _build_als_project(midi_data)
    als_path = als_dir / f"{TRACK_NAME}.als"
    write_als(project, str(als_path))

    midi_track_count = sum(1 for t in project.tracks
                           if t.track_type == "midi")
    return_count = sum(1 for t in project.tracks
                       if t.track_type == "return")
    print(f"    {als_path}")
    print(f"    {midi_track_count} MIDI tracks + {return_count} returns")
    print(f"    {len(project.scenes)} scenes, {len(project.cue_points)} cue points")

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  DONE — {TRACK_NAME}")
    print(f"{'=' * 60}")
    print(f"\n  Outputs:")
    print(f"    ALS:     {als_path}")
    print(f"    MIDI:    {midi_path}")
    print(f"    Presets: {preset_dir}/")
    print(f"\n  Instructions:")
    print(f"    1. Open {als_path.name} in Ableton Live")
    print(f"    2. For each MIDI track, drag Serum 2 from browser onto the track")
    print(f"    3. In Serum 2, File -> Import Preset -> load matching .fxp from:")
    print(f"       {preset_dir.resolve()}")
    print(f"    4. Press play — Serum 2 synthesizes everything")
    print(f"\n  Track -> Preset Mapping:")
    for name in SYNTH_TRACK_ORDER:
        preset_info = SERUM2_PRESETS.get(name)
        if preset_info:
            print(f"    {name:12s} -> {preset_info[0]}.fxp")
        else:
            print(f"    {name:12s} -> (Drum Rack / any drum plugin)")
    print()


if __name__ == "__main__":
    main()
