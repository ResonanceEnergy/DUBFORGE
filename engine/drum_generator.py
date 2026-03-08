"""
DUBFORGE Engine — 4/4 Drum & Percussion Generator

Generates MIDI drum patterns using Fibonacci-timed fills,
phi-ratio velocity curves, and genre-specific dubstep patterns.

Outputs:
    output/midi/drums_*.mid — One per pattern preset
    output/midi/drums_FULL_KIT.mid — Multi-track combined drum arrangement

All patterns follow General MIDI drum mapping (channel 10).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import mido

from engine.config_loader import FIBONACCI, PHI
from engine.log import get_logger

_log = get_logger("dubforge.drum_generator")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

TICKS_PER_BEAT = 480
DEFAULT_BPM = 150
DRUM_CHANNEL = 9  # GM channel 10 (0-indexed)

# General MIDI Drum Map (key selections for dubstep)
GM_DRUMS = {
    "kick":         36,
    "kick_alt":     35,
    "snare":        38,
    "snare_rim":    37,
    "snare_alt":    40,
    "clap":         39,
    "hat_closed":   42,
    "hat_pedal":    44,
    "hat_open":     46,
    "crash":        49,
    "crash_alt":    57,
    "ride":         51,
    "ride_bell":    53,
    "tom_low":      45,
    "tom_mid":      47,
    "tom_high":     50,
    "perc_1":       56,  # cowbell
    "perc_2":       54,  # tambourine
    "shaker":       70,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DrumHit:
    """A single drum hit in a pattern."""
    note: int              # GM drum note number
    beat: float            # position in beats (0-indexed)
    velocity: int = 100    # 1-127
    duration: float = 0.1  # in beats


@dataclass
class DrumPattern:
    """A drum pattern spanning a fixed number of bars."""
    name: str
    bars: int = 4                           # pattern length in bars
    time_sig: tuple[int, int] = (4, 4)
    hits: list[DrumHit] = field(default_factory=list)

    @property
    def total_beats(self) -> float:
        return self.bars * self.time_sig[0]


# ═══════════════════════════════════════════════════════════════════════════
# VELOCITY CURVES
# ═══════════════════════════════════════════════════════════════════════════

def phi_velocity(base: int, position: float, swing: float = 0.0) -> int:
    """Compute velocity with phi-decay ghost notes."""
    # Downbeats hit harder, off-beats ghost
    beat_frac = position % 1.0
    if beat_frac < 0.01:  # on the beat
        v = base
    elif abs(beat_frac - 0.5) < 0.01:  # off-beat
        v = int(base * (1.0 / PHI))
    else:  # ghost notes
        v = int(base * (1.0 / (PHI ** 2)))
    # Swing offset
    if swing > 0:
        v = int(v * (1 + swing * 0.1))
    return max(1, min(127, v))


def fibonacci_accent_pattern(n_beats: int, base_vel: int = 100) -> list[int]:
    """Generate velocity pattern where Fibonacci-position beats get accents."""
    fib_set = set()
    a, b = 1, 1
    while a <= n_beats:
        fib_set.add(a - 1)  # 0-indexed
        a, b = b, a + b
    return [min(127, base_vel + 20) if i in fib_set else base_vel
            for i in range(n_beats)]


# ═══════════════════════════════════════════════════════════════════════════
# PATTERN GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def generate_dubstep_drop(bars: int = 4) -> DrumPattern:
    """
    Dubstep drop pattern: half-time feel.
    Kick on 1, snare on 3, hat 8ths, ghost snares.
    """
    pattern = DrumPattern(name="DUBSTEP_DROP", bars=bars)

    for bar in range(bars):
        base = bar * 4
        # Kick: beat 1
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=120))
        # Snare: beat 3 (half-time)
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 2.0, velocity=110))
        # Clap layered with snare
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], base + 2.0, velocity=90))
        # Closed hats: 8th notes
        for eighth in range(8):
            beat = base + eighth * 0.5
            vel = phi_velocity(80, beat)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], beat, velocity=vel, duration=0.05))
        # Ghost snare on "and of 4"
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 3.5, velocity=45))

    return pattern


def generate_dubstep_build(bars: int = 8) -> DrumPattern:
    """
    Build-up pattern: accelerating snare rolls with Fibonacci timing.
    """
    pattern = DrumPattern(name="DUBSTEP_BUILD", bars=bars)

    for bar in range(bars):
        base = bar * 4
        progress = bar / max(bars - 1, 1)
        # Kick on 1
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=110))
        # Hat pattern gets denser as build progresses
        divisions = 4 + int(progress * 12)  # 4 → 16 per bar
        for i in range(divisions):
            beat = base + i * (4.0 / divisions)
            vel = int(60 + progress * 60)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], beat, velocity=min(127, vel), duration=0.05))
        # Snare roll density increases with progress
        if progress < 0.25:
            # Quarter notes snare
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 2.0, velocity=100))
        elif progress < 0.5:
            # 8th note snares
            for i in range(0, 8, 2):
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + i * 0.5, velocity=90))
        elif progress < 0.75:
            # 8th notes full
            for i in range(8):
                vel = int(80 + (i / 8) * 40)
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + i * 0.5, velocity=min(127, vel)))
        else:
            # 16th note roll
            for i in range(16):
                vel = int(70 + (i / 16) * 57)
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + i * 0.25, velocity=min(127, vel)))

    return pattern


def generate_halftime_groove(bars: int = 4) -> DrumPattern:
    """
    Half-time groove: heavy kick, snare on 3, syncopated hats.
    Classic Subtronics feel.
    """
    pattern = DrumPattern(name="HALFTIME_GROOVE", bars=bars)

    for bar in range(bars):
        base = bar * 4
        # Kick pattern: 1, "and of 2"
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 1.5, velocity=90))
        # Snare on 3
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 2.0, velocity=115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], base + 2.0, velocity=85))
        # Syncopated hats with ghost notes
        hat_pattern = [0, 0.5, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.25, 3.5, 3.75]
        for h in hat_pattern:
            vel = phi_velocity(75, h)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], base + h, velocity=vel, duration=0.05))
        # Open hat on "and of 2"
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], base + 1.5, velocity=70, duration=0.25))

    return pattern


def generate_fibonacci_fill(bars: int = 1) -> DrumPattern:
    """
    Fill pattern using Fibonacci-timed tom hits.
    Descending toms: high → mid → low across Fibonacci subdivisions.
    """
    pattern = DrumPattern(name="FIBONACCI_FILL", bars=bars)
    total_beats = pattern.total_beats
    toms = [GM_DRUMS["tom_high"], GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]]

    # Generate hits at Fibonacci intervals within the bar
    fib_beats = []
    for f in FIBONACCI:
        if f > 0:
            beat = (f / 13.0) * total_beats  # normalize to pattern length
            if beat < total_beats:
                fib_beats.append(beat)

    fib_beats = sorted(set(round(b, 3) for b in fib_beats))

    for i, beat in enumerate(fib_beats):
        tom = toms[i % len(toms)]
        vel = int(127 - (i / max(len(fib_beats), 1)) * 40)
        pattern.hits.append(DrumHit(tom, beat, velocity=max(60, vel)))
        # Add a crash at the start
        if i == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], beat, velocity=110))

    # Snare flam on last 16th
    pattern.hits.append(DrumHit(GM_DRUMS["snare"], total_beats - 0.25, velocity=120))
    pattern.hits.append(DrumHit(GM_DRUMS["snare"], total_beats - 0.125, velocity=100))

    return pattern


def generate_breakbeat(bars: int = 4) -> DrumPattern:
    """
    Breakbeat-style pattern for hybrid dubstep sections.
    Syncopated kicks, broken beat feel.
    """
    pattern = DrumPattern(name="BREAKBEAT", bars=bars)

    for bar in range(bars):
        base = bar * 4
        # Syncopated kicks
        kicks = [0.0, 0.75, 1.5, 2.75, 3.0]
        for k in kicks:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + k, velocity=115))
        # Snare on 2 and 4 (full-time)
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 1.0, velocity=105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 3.0, velocity=110))
        # 16th note hats with ghost dynamics
        for i in range(16):
            beat = base + i * 0.25
            vel = phi_velocity(70, beat)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], beat, velocity=vel, duration=0.04))

    return pattern


def generate_intro_minimal(bars: int = 8) -> DrumPattern:
    """
    Minimal intro pattern: sparse kicks and low hats.
    Builds tension before the first build.
    """
    pattern = DrumPattern(name="INTRO_MINIMAL", bars=bars)

    for bar in range(bars):
        base = bar * 4
        progress = bar / max(bars - 1, 1)
        # Kick every 2 bars at first, every bar later
        if bar % max(1, 2 - int(progress)) == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=int(80 + progress * 40)))
        # Sparse hat (quarter notes, low velocity)
        for i in range(4):
            if (bar + i) % 2 == 0 or progress > 0.5:
                vel = int(40 + progress * 30)
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], base + i, velocity=vel, duration=0.05))
        # Ride bell on laters bars
        if progress > 0.5:
            pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"], base + 2.0, velocity=50))

    return pattern


def generate_snare_roll_32nd(bars: int = 2) -> DrumPattern:
    """
    32nd-note snare roll with phi-velocity crescendo.
    Classic Subtronics pre-drop build finisher.
    Velocity ramps from ghost (40) → full blast (127) using phi curve.
    """
    pattern = DrumPattern(name="SNARE_ROLL_32ND", bars=bars)
    total_beats = pattern.total_beats
    total_32nds = int(total_beats * 8)  # 8 thirty-second notes per beat

    for i in range(total_32nds):
        beat = i / 8.0
        progress = i / max(total_32nds - 1, 1)
        # Phi-curved velocity crescendo: slow start → explosive finish
        phi_progress = progress ** (1.0 / PHI)  # ~progress^0.618
        vel = int(40 + phi_progress * 87)
        vel = max(1, min(127, vel))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], beat, velocity=vel, duration=0.05))
        # Layer clap on every 4th hit for thickness
        if i % 4 == 0:
            clap_vel = int(vel * 0.7)
            pattern.hits.append(DrumHit(GM_DRUMS["clap"], beat, velocity=max(1, clap_vel), duration=0.05))

    # Crash on final beat
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], total_beats - 0.125, velocity=127))

    return pattern


def generate_tom_cascade_fill(bars: int = 1) -> DrumPattern:
    """
    Descending tom cascade fill: high → mid → low.
    16th note toms with velocity ramp, ending in a kick+crash.
    Classic Subtronics transition fill.
    """
    pattern = DrumPattern(name="TOM_CASCADE_FILL", bars=bars)
    total_beats = pattern.total_beats
    total_16ths = int(total_beats * 4)
    toms = [GM_DRUMS["tom_high"], GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]]

    for i in range(total_16ths):
        beat = i * 0.25
        progress = i / max(total_16ths - 1, 1)
        # Descend through toms: high (first third) → mid (second) → low (last)
        tom_idx = min(int(progress * 3), 2)
        tom = toms[tom_idx]
        # Velocity builds then drops for each tom group
        group_progress = (progress * 3) % 1.0
        vel = int(90 + group_progress * 37)
        vel = max(60, min(127, vel))
        pattern.hits.append(DrumHit(tom, beat, velocity=vel, duration=0.1))
        # Add a kick on beat boundaries
        if i % 4 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], beat, velocity=110))

    # Big crash + kick on final 16th
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], total_beats - 0.125, velocity=127))
    pattern.hits.append(DrumHit(GM_DRUMS["kick"], total_beats - 0.125, velocity=127))

    return pattern


def generate_riddim_minimal(bars: int = 4) -> DrumPattern:
    """
    Minimal riddim pattern: hypnotic, sparse, half-time.
    Kick on 1, snare on 3, barely-there hats, cowbell ghost.
    The space IS the groove — classic Subtronics riddim sections.
    """
    pattern = DrumPattern(name="RIDDIM_MINIMAL", bars=bars)

    for bar in range(bars):
        base = bar * 4
        # Kick: beat 1 only — heavy
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=127))
        # Snare: beat 3 — crisp
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 2.0, velocity=115))
        # Minimal hats: only on 1 and 3 (quarter notes, very low vel)
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], base + 0.0, velocity=40, duration=0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], base + 2.0, velocity=35, duration=0.04))
        # Ghost cowbell on "and of 4" — every other bar
        if bar % 2 == 1:
            pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], base + 3.5, velocity=30, duration=0.05))
        # Open hat on "and of 2" — subtle
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], base + 1.5, velocity=45, duration=0.15))

    return pattern


def generate_triplet_hat_groove(bars: int = 4) -> DrumPattern:
    """
    Triplet hi-hat groove with half-time kick/snare.
    Creates that bouncy, rolling feel Subtronics uses in
    breakdowns and build transitions. 12 hats per bar (triplet 8ths).
    """
    pattern = DrumPattern(name="TRIPLET_HAT_GROOVE", bars=bars)

    for bar in range(bars):
        base = bar * 4
        # Half-time foundation: kick on 1, snare on 3
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], base + 0.0, velocity=120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], base + 2.0, velocity=110))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], base + 2.0, velocity=80))
        # Triplet 8th note hats: 12 per bar (3 per beat)
        for i in range(12):
            beat = base + i * (4.0 / 12.0)  # evenly spaced triplets
            # Accent pattern: first of each triplet group louder
            if i % 3 == 0:
                vel = 90
                drum = GM_DRUMS["hat_closed"]
            elif i % 3 == 1:
                vel = 55
                drum = GM_DRUMS["hat_closed"]
            else:
                vel = 40
                drum = GM_DRUMS["hat_closed"]
            # Open hat on every 4th hit for movement
            if i % 6 == 3:
                drum = GM_DRUMS["hat_open"]
                vel = 65
            pattern.hits.append(DrumHit(drum, beat, velocity=vel, duration=0.04))

    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# BEAT-MAP FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def _build_from_beat_map(
    name: str, bars: int,
    beat_map: dict[str, list[tuple[float, int, float]]],
) -> DrumPattern:
    """Build repeating DrumPattern from per-bar beat positions.

    beat_map: {drum_key: [(beat_in_bar, velocity, duration), ...]}
    """
    pattern = DrumPattern(name=name, bars=bars)
    for bar in range(bars):
        base = bar * 4
        for drum_key, positions in beat_map.items():
            note = GM_DRUMS[drum_key]
            for pos, vel, dur in positions:
                pattern.hits.append(
                    DrumHit(note, base + pos, velocity=vel, duration=dur)
                )
    return pattern


# --- Beat-map patterns (static per-bar repeat) ---------------------------

def generate_double_time_hat(bars: int = 4) -> DrumPattern:
    """Double-time 16th hi-hats over half-time kick/snare."""
    return _build_from_beat_map("DOUBLE_TIME_HAT", bars, {
        "kick": [(0.0, 120, 0.1), (1.5, 85, 0.1)],
        "snare": [(2.0, 110, 0.1)],
        "clap": [(2.0, 85, 0.1)],
        "hat_closed": [(i * 0.25, 80 if i % 4 == 0 else 50 if i % 2 == 0 else 35, 0.04)
                       for i in range(16)],
    })


def generate_shuffle_groove(bars: int = 4) -> DrumPattern:
    """Swung shuffle feel with offset ghost notes."""
    return _build_from_beat_map("SHUFFLE_GROOVE", bars, {
        "kick": [(0.0, 120, 0.1), (1.67, 80, 0.1)],
        "snare": [(2.0, 110, 0.1)],
        "hat_closed": [(0.0, 75, 0.04), (0.67, 45, 0.04), (1.0, 70, 0.04),
                       (1.67, 45, 0.04), (2.0, 75, 0.04), (2.67, 45, 0.04),
                       (3.0, 70, 0.04), (3.67, 45, 0.04)],
    })


def generate_four_on_floor(bars: int = 4) -> DrumPattern:
    """Straight 4/4 kick with snare on 2+4 — festival energy."""
    return _build_from_beat_map("FOUR_ON_FLOOR", bars, {
        "kick": [(0.0, 127, 0.1), (1.0, 120, 0.1), (2.0, 120, 0.1), (3.0, 120, 0.1)],
        "snare": [(1.0, 105, 0.1), (3.0, 110, 0.1)],
        "hat_closed": [(i * 0.5, 70 if i % 2 == 0 else 45, 0.04) for i in range(8)],
        "hat_open": [(0.5, 55, 0.15)],
    })


def generate_syncopated_kick(bars: int = 4) -> DrumPattern:
    """Off-beat syncopated kick pattern for tension and groove."""
    return _build_from_beat_map("SYNCOPATED_KICK", bars, {
        "kick": [(0.0, 120, 0.1), (0.75, 95, 0.1), (1.5, 100, 0.1),
                 (2.75, 110, 0.1), (3.5, 90, 0.1)],
        "snare": [(2.0, 110, 0.1)],
        "clap": [(2.0, 80, 0.1)],
        "hat_closed": [(i * 0.5, 65, 0.04) for i in range(8)],
    })


def generate_ghost_snare_groove(bars: int = 4) -> DrumPattern:
    """Ghost-note heavy groove — snare weaves between every hit."""
    return _build_from_beat_map("GHOST_SNARE_GROOVE", bars, {
        "kick": [(0.0, 120, 0.1), (1.5, 90, 0.1)],
        "snare": [(2.0, 115, 0.1)],
        "snare_rim": [(0.75, 35, 0.05), (1.25, 30, 0.05), (2.5, 40, 0.05),
                      (3.0, 35, 0.05), (3.5, 30, 0.05), (3.75, 25, 0.05)],
        "hat_closed": [(i * 0.5, 60, 0.04) for i in range(8)],
    })


def generate_cymbal_accent(bars: int = 4) -> DrumPattern:
    """Crash and ride accent pattern for transitions."""
    return _build_from_beat_map("CYMBAL_ACCENT", bars, {
        "kick": [(0.0, 115, 0.1)],
        "snare": [(2.0, 105, 0.1)],
        "crash": [(0.0, 110, 0.3)],
        "ride": [(i, 70 if i % 2 == 0 else 50, 0.1) for i in range(4)],
        "ride_bell": [(0.0, 65, 0.1), (2.0, 60, 0.1)],
    })


def generate_open_hat_groove(bars: int = 4) -> DrumPattern:
    """Open hi-hat groove — airy and spacious."""
    return _build_from_beat_map("OPEN_HAT_GROOVE", bars, {
        "kick": [(0.0, 120, 0.1), (1.5, 85, 0.1)],
        "snare": [(2.0, 110, 0.1)],
        "hat_closed": [(0.0, 70, 0.04), (1.0, 65, 0.04), (2.0, 70, 0.04), (3.0, 65, 0.04)],
        "hat_open": [(0.5, 60, 0.2), (1.5, 55, 0.2), (2.5, 60, 0.2), (3.5, 55, 0.2)],
    })


def generate_ride_pattern(bars: int = 4) -> DrumPattern:
    """Ride cymbal-driven groove for breakdown sections."""
    return _build_from_beat_map("RIDE_PATTERN", bars, {
        "kick": [(0.0, 115, 0.1), (2.5, 85, 0.1)],
        "snare": [(2.0, 100, 0.1)],
        "ride": [(i * 0.5, 75 if i % 2 == 0 else 50, 0.1) for i in range(8)],
        "ride_bell": [(0.0, 80, 0.1)],
        "hat_pedal": [(1.0, 40, 0.05), (3.0, 40, 0.05)],
    })


def generate_half_shuffle(bars: int = 4) -> DrumPattern:
    """Shuffled half-time — swing feel at 150 BPM."""
    return _build_from_beat_map("HALF_SHUFFLE", bars, {
        "kick": [(0.0, 127, 0.1), (1.67, 80, 0.1)],
        "snare": [(2.0, 115, 0.1)],
        "clap": [(2.0, 85, 0.1)],
        "hat_closed": [(0.0, 75, 0.04), (0.67, 40, 0.04), (1.0, 70, 0.04),
                       (1.67, 40, 0.04), (2.0, 75, 0.04), (2.67, 40, 0.04),
                       (3.0, 70, 0.04), (3.67, 40, 0.04)],
        "hat_open": [(1.67, 50, 0.15)],
    })


def generate_perc_layer(bars: int = 4) -> DrumPattern:
    """Percussion-only layer: shaker, tambourine, cowbell."""
    return _build_from_beat_map("PERC_LAYER", bars, {
        "shaker": [(i * 0.25, 35 + (i % 4) * 5, 0.04) for i in range(16)],
        "perc_2": [(i * 0.5, 45 if i % 2 == 0 else 30, 0.05) for i in range(8)],
        "perc_1": [(1.5, 40, 0.05), (3.5, 35, 0.05)],
    })


# --- Dynamic patterns (per-bar variation) ---------------------------------

def generate_trap_hat_roll(bars: int = 4) -> DrumPattern:
    """Trap-style hi-hat rolls that accelerate within each bar."""
    pattern = DrumPattern(name="TRAP_HAT_ROLL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.0, 110))
        # First half: 8th hats, second half: 32nd rolls
        for i in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + i * 0.5, 70, 0.04))
        for i in range(16):
            beat = b + 2.0 + i * 0.125
            vel = int(50 + (i / 16) * 70)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], beat, min(127, vel), 0.03))
    return pattern


def generate_militaristic_snare(bars: int = 4) -> DrumPattern:
    """Military marching snare — steady 16th doubles with accents."""
    pattern = DrumPattern(name="MILITARISTIC_SNARE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for i in range(16):
            beat = b + i * 0.25
            vel = 110 if i % 8 == 0 else 85 if i % 4 == 0 else 60
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], beat, vel, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.0, 95))
    return pattern


def generate_polyrhythm_3v4(bars: int = 4) -> DrumPattern:
    """3-over-4 polyrhythm — tom triplets against kick quarters."""
    pattern = DrumPattern(name="POLYRHYTHM_3V4", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for i in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + i, 110, 0.1))
        toms = [GM_DRUMS["tom_high"], GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]]
        for i in range(3):
            beat = b + i * (4.0 / 3.0)
            pattern.hits.append(DrumHit(toms[i], beat, 95, 0.15))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 0.5, 55, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 2.5, 55, 0.04))
    return pattern


def generate_dnb_crossover(bars: int = 4) -> DrumPattern:
    """Drum & bass-style breakbeat at dubstep tempo."""
    pattern = DrumPattern(name="DNB_CROSSOVER", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for k in [0.0, 1.25, 2.5, 3.0]:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + k, 115, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.0, 110, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.0, 115, 0.1))
        for i in range(16):
            v = phi_velocity(65, i * 0.25)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + i * 0.25, v, 0.03))
    return pattern


def generate_flam_fill(bars: int = 1) -> DrumPattern:
    """Flam-based fill — double strikes on toms and snare."""
    pattern = DrumPattern(name="FLAM_FILL", bars=bars)
    total_beats = pattern.total_beats
    drums_seq = [GM_DRUMS["snare"], GM_DRUMS["tom_high"],
                 GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]]
    n_hits = int(total_beats * 4)
    for i in range(n_hits):
        beat = i * 0.25
        drum = drums_seq[i % len(drums_seq)]
        vel = int(100 + (i / max(n_hits, 1)) * 27)
        pattern.hits.append(DrumHit(drum, max(0, beat - 0.06), int(vel * 0.5), 0.05))
        pattern.hits.append(DrumHit(drum, beat, min(127, vel), 0.08))
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], total_beats - 0.125, 127))
    return pattern


def generate_tribal_toms(bars: int = 4) -> DrumPattern:
    """Tribal tom groove — world-music-influenced pattern."""
    pattern = DrumPattern(name="TRIBAL_TOMS", bars=bars)
    tom_hits = [
        ("tom_low", 0.0, 110), ("tom_mid", 0.75, 80),
        ("tom_high", 1.0, 95), ("tom_high", 1.5, 70),
        ("tom_mid", 2.0, 100), ("tom_low", 2.75, 85),
        ("tom_high", 3.0, 90), ("tom_mid", 3.5, 75),
    ]
    for bar in range(bars):
        b = bar * 4
        for drum, pos, vel in tom_hits:
            pattern.hits.append(DrumHit(GM_DRUMS[drum], b + pos, vel, 0.15))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.0, 95))
    return pattern


def generate_stutter_kick(bars: int = 2) -> DrumPattern:
    """Glitchy rapid-fire kick stutters with increasing density."""
    pattern = DrumPattern(name="STUTTER_KICK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        progress = bar / max(bars - 1, 1)
        n_kicks = 4 + int(progress * 12)
        for i in range(n_kicks):
            beat = b + i * (4.0 / n_kicks)
            vel = int(80 + (i / n_kicks) * 40)
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], beat, min(127, vel), 0.05))
        for i in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + i, 55, 0.04))
    return pattern


def generate_outro_decay(bars: int = 8) -> DrumPattern:
    """Gradually decaying pattern — elements drop out over time."""
    pattern = DrumPattern(name="OUTRO_DECAY", bars=bars)
    for bar in range(bars):
        b = bar * 4
        decay = 1.0 - bar / max(bars - 1, 1)
        if decay > 0.25:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, max(30, int(120 * decay))))
        if decay > 0.5:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.0, max(30, int(110 * decay))))
        for i in range(4):
            vel = int(60 * decay)
            if vel > 15:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + i, vel, 0.04))
        if 0 < decay < 0.3:
            pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"], b, int(40 * decay), 0.1))
    return pattern


def generate_micro_fill(bars: int = 1) -> DrumPattern:
    """Quick 1-bar micro-fill — 16th snare/tom combo."""
    pattern = DrumPattern(name="MICRO_FILL", bars=bars)
    drums = [GM_DRUMS["snare"], GM_DRUMS["snare"], GM_DRUMS["tom_high"],
             GM_DRUMS["tom_mid"], GM_DRUMS["snare"], GM_DRUMS["snare"],
             GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]] * 2
    total_16ths = int(pattern.total_beats * 4)
    for i in range(total_16ths):
        beat = i * 0.25
        drum = drums[i % len(drums)]
        vel = int(85 + (i / max(total_16ths, 1)) * 42)
        pattern.hits.append(DrumHit(drum, beat, min(127, vel), 0.06))
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], pattern.total_beats - 0.125, 127))
    return pattern


def generate_triplet_snare_build(bars: int = 4) -> DrumPattern:
    """Triplet snare build — 3-feel snare ramp with crescendo."""
    pattern = DrumPattern(name="TRIPLET_SNARE_BUILD", bars=bars)
    for bar in range(bars):
        b = bar * 4
        progress = bar / max(bars - 1, 1)
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        beats_active = 1 + int(progress * 3)
        for beat_idx in range(beats_active):
            for triplet in range(3):
                pos = b + beat_idx + triplet * (1.0 / 3.0)
                vel = int(60 + progress * 60 + triplet * 5)
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos, min(127, vel), 0.06))
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], pattern.total_beats - 0.125, 127))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v1.9 PATTERNS (20 more)
# ═══════════════════════════════════════════════════════════════════════════

def generate_breakcore_chop(bars: int = 4) -> DrumPattern:
    """Breakcore chop — rapid irregular hits with chaotic energy."""
    pattern = DrumPattern(name="BREAKCORE_CHOP", bars=bars)
    fib = [1, 1, 2, 3, 5, 8]
    for bar in range(bars):
        b = bar * 4
        for i, f in enumerate(fib):
            pos = b + (f % 4) + (i * 0.25) % 4
            if pos < b + 4:
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos, 110 + (i * 3) % 17, 0.04))
                pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos + 0.125, 100, 0.05))
        for s in range(16):
            if s % 3 == 0 or s % 5 == 0:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.25,
                                            70 + (s * 7) % 40, 0.03))
    return pattern


def generate_uk_garage(bars: int = 4) -> DrumPattern:
    """UK garage — 2-step swing with shuffled hats."""
    pattern = DrumPattern(name="UK_GARAGE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        for s in range(8):
            pos = b + s * 0.5
            swing = 0.08 if s % 2 == 1 else 0
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], pos + swing,
                                        75 + (s * 5) % 20, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 1.5, 80, 0.12))
    return pattern


def generate_wonky_groove(bars: int = 4) -> DrumPattern:
    """Wonky groove — off-grid kicks with micro-timed accents."""
    pattern = DrumPattern(name="WONKY_GROOVE", bars=bars)
    kick_positions = [0, 0.75, 1.5, 2.25, 3.125]
    for bar in range(bars):
        b = bar * 4
        for kp in kick_positions:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + kp, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 95))
        for s in range(16):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.25,
                                        60 + (s * 11) % 30, 0.04))
    return pattern


def generate_industrial_slam(bars: int = 4) -> DrumPattern:
    """Industrial slam — heavy distorted kick pattern with metal percussion."""
    pattern = DrumPattern(name="INDUSTRIAL_SLAM", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 127))
            pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b + beat + 0.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + 0.75, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + 2.75, 95))
    return pattern


def generate_reggaeton_dembow(bars: int = 4) -> DrumPattern:
    """Reggaeton dembow — classic tresillo kick + snare pattern."""
    pattern = DrumPattern(name="REGGAETON_DEMBOW", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 0.75, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.75, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.75, 90))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5,
                                        70, 0.05))
    return pattern


def generate_blast_beat(bars: int = 2) -> DrumPattern:
    """Blast beat — extreme speed alternating kick/snare for intensity."""
    pattern = DrumPattern(name="BLAST_BEAT", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for s in range(32):
            pos = b + s * 0.125
            if s % 2 == 0:
                pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, 110, 0.04))
            else:
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos, 105, 0.04))
            if s % 4 == 0:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], pos, 80, 0.03))
    return pattern


def generate_swing_shuffle(bars: int = 4) -> DrumPattern:
    """Swing shuffle — classic jazz-influenced shuffled groove."""
    pattern = DrumPattern(name="SWING_SHUFFLE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["ride"], b + beat, 85, 0.1))
            pattern.hits.append(DrumHit(GM_DRUMS["ride"], b + beat + 0.67, 65, 0.08))
    return pattern


def generate_phi_euclidean(bars: int = 4) -> DrumPattern:
    """Phi euclidean — golden-ratio-spaced kick placement."""
    pattern = DrumPattern(name="PHI_EUCLIDEAN", bars=bars)
    total_16ths = bars * 16
    num_kicks = int(total_16ths / PHI)
    for i in range(num_kicks):
        pos = (i * PHI * 0.25) % (bars * 4)
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, 105))
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5, 75, 0.05))
    return pattern


def generate_double_pedal(bars: int = 4) -> DrumPattern:
    """Double pedal — rapid kick doubles for heavy sections."""
    pattern = DrumPattern(name="DOUBLE_PEDAL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 110, 0.06))
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat + 0.125, 95, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5, 75, 0.05))
    return pattern


def generate_sparse_ambient(bars: int = 8) -> DrumPattern:
    """Sparse ambient — minimal scattered hits for atmospheric sections."""
    pattern = DrumPattern(name="SPARSE_AMBIENT", bars=bars)
    fib = [1, 2, 3, 5, 8, 13]
    for f in fib:
        pos = (f * PHI) % (bars * 4)
        pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"], pos, 60, 0.3))
    for bar in range(0, bars, 2):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3, 55, 0.1))
    return pattern


def generate_march_snare(bars: int = 4) -> DrumPattern:
    """March snare — military march rhythm with flams."""
    pattern = DrumPattern(name="MARCH_SNARE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        march_pos = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]
        for mp in march_pos:
            vel = 100 if mp % 1 == 0 else 70
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + mp, vel, 0.08))
            if mp % 2 == 0:
                flam_pos = max(0.0, b + mp - 0.03)
                pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], flam_pos,
                                            50, 0.03))
    return pattern


def generate_lo_fi_beat(bars: int = 4) -> DrumPattern:
    """Lo-fi beat — relaxed groove with ghost snare hits."""
    pattern = DrumPattern(name="LO_FI_BEAT", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.5, 40, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.5, 35, 0.05))
        for s in range(8):
            vel = 55 + (s * 3) % 20
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5, vel, 0.06))
    return pattern


def generate_cross_stick(bars: int = 4) -> DrumPattern:
    """Cross stick pattern — rimshot-driven minimal groove."""
    pattern = DrumPattern(name="CROSS_STICK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 1, 95, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3, 90, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3.75, 70, 0.06))
        for s in range(16):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.25,
                                        55 + (s * 5) % 25, 0.04))
    return pattern


def generate_tom_groove(bars: int = 4) -> DrumPattern:
    """Tom groove — melodic tom-driven pattern."""
    pattern = DrumPattern(name="TOM_GROOVE", bars=bars)
    toms = [GM_DRUMS["tom_low"], GM_DRUMS["tom_mid"], GM_DRUMS["tom_high"]]
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        tom_pattern = [0.5, 1, 1.75, 2.5, 3, 3.5]
        for i, tp in enumerate(tom_pattern):
            pattern.hits.append(DrumHit(toms[i % 3], b + tp, 90 - i * 3, 0.12))
    return pattern


def generate_kick_snare_only(bars: int = 4) -> DrumPattern:
    """Kick-snare only — stripped back foundation."""
    pattern = DrumPattern(name="KICK_SNARE_ONLY", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
    return pattern


def generate_clap_stack(bars: int = 4) -> DrumPattern:
    """Clap stack — layered clap/snare hits for thick backbeat."""
    pattern = DrumPattern(name="CLAP_STACK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        for beat in [1, 3]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + beat, 110))
            pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + beat, 105))
            pattern.hits.append(DrumHit(GM_DRUMS["snare_alt"], b + beat + 0.02, 85))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5,
                                        70, 0.05))
    return pattern


def generate_shaker_groove(bars: int = 4) -> DrumPattern:
    """Shaker groove — 16th note shaker with sparse kick/snare."""
    pattern = DrumPattern(name="SHAKER_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        for s in range(16):
            vel = 65 if s % 4 == 0 else 45
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"], b + s * 0.25, vel, 0.04))
    return pattern


def generate_crash_accent(bars: int = 4) -> DrumPattern:
    """Crash accent — crash cymbals on phi-spaced beats."""
    pattern = DrumPattern(name="CRASH_ACCENT", bars=bars)
    total_beats = bars * 4
    crash_positions = set()
    pos = 0.0
    while pos < total_beats:
        crash_positions.add(round(pos * 4) / 4)
        pos += PHI * 2
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
    for cp in crash_positions:
        if cp < total_beats:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], cp, 110, 0.2))
    return pattern


def generate_countdown_fill(bars: int = 2) -> DrumPattern:
    """Countdown fill — accelerating snare hits into crash."""
    pattern = DrumPattern(name="COUNTDOWN_FILL", bars=bars)
    total_beats = bars * 4
    # Subdivisions double each quarter: 1, 2, 4, 8, 16...
    pos = 0.0
    subdiv = 1.0
    while pos < total_beats - 0.125:
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos,
                                    int(70 + (pos / total_beats) * 57), 0.06))
        pos += subdiv
        subdiv = max(0.125, subdiv / PHI)
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], total_beats - 0.0625, 127))
    pattern.hits.append(DrumHit(GM_DRUMS["kick"], total_beats - 0.0625, 127))
    return pattern


def generate_reverse_buildup(bars: int = 4) -> DrumPattern:
    """Reverse buildup — starts dense and strips down to silence."""
    pattern = DrumPattern(name="REVERSE_BUILDUP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        density = 1 - bar / max(bars - 1, 1)
        num_16ths = max(1, int(16 * density))
        for s in range(num_16ths):
            pos = b + s * 0.25
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos,
                                        int(60 + density * 60), 0.06))
        if density > 0.5:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        elif density > 0.2:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 90))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v2.0 — 16 new drum patterns (→ 66 total)
# ═══════════════════════════════════════════════════════════════════════════

def generate_heavy_halftime(bars: int = 4) -> DrumPattern:
    """Heavy halftime — massive kick/snare with ghost notes."""
    pattern = DrumPattern(name="HEAVY_HALFTIME", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        # Ghost snares
        for g in [0.75, 1.5, 3.25, 3.75]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + g, 45, 0.06))
        # Hats on 8ths
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5,
                                        60 + (s % 2) * 15, 0.06))
    return pattern


def generate_rolling_16ths(bars: int = 4) -> DrumPattern:
    """Rolling 16ths — continuous 16th-note hats with kick/snare backbone."""
    pattern = DrumPattern(name="ROLLING_16THS", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 105))
        for s in range(16):
            vel = 90 if s % 4 == 0 else 55
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.25,
                                        vel, 0.06))
    return pattern


def generate_broken_beat(bars: int = 4) -> DrumPattern:
    """Broken beat — syncopated displaced kick/snare groove."""
    pattern = DrumPattern(name="BROKEN_BEAT", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for pos in [0, 0.75, 2.5]:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + pos, 110))
        for pos in [1.25, 3.0, 3.5]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + pos, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.5,
                                        65, 0.06))
    return pattern


def generate_jungle_break(bars: int = 4) -> DrumPattern:
    """Jungle break — chopped amen-style breakbeat pattern."""
    pattern = DrumPattern(name="JUNGLE_BREAK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # Kick pattern
        for pos in [0, 1.25, 2.5, 3.75]:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + pos, 110))
        # Snare pattern (displaced off-beats)
        for pos in [0.5, 1.75, 2.0, 3.25]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + pos, 100))
        # Fast hats
        for s in range(16):
            if s % 3 != 0:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                            b + s * 0.25, 70, 0.05))
    return pattern


def generate_garage_2step(bars: int = 4) -> DrumPattern:
    """Garage 2-step — skippy kick with shuffled hats."""
    pattern = DrumPattern(name="GARAGE_2STEP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        # Shuffled hats (swing)
        for s in range(8):
            offset = 0.08 if s % 2 == 1 else 0
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5 + offset, 60, 0.06))
    return pattern


def generate_riddim_heavy(bars: int = 4) -> DrumPattern:
    """Riddim heavy — minimal kick/snare with massive hits."""
    pattern = DrumPattern(name="RIDDIM_HEAVY", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 127))
        # Double snare accent
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.25, 100))
        # Sparse hat
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 1, 70, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 3, 70, 0.06))
    return pattern


def generate_footwork(bars: int = 4) -> DrumPattern:
    """Footwork — rapid 160bpm juke-style pattern."""
    pattern = DrumPattern(name="FOOTWORK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # Rapid kick bursts
        for pos in [0, 0.25, 0.5, 2.0, 2.25, 2.5]:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + pos, 105))
        # Clap on 2 and 4
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 100))
        # Fast hats
        for s in range(16):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s * 0.25,
                                        50 + (s % 2) * 20, 0.04))
    return pattern


def generate_drill_slide(bars: int = 4) -> DrumPattern:
    """Drill slide — UK drill sliding hi-hats with heavy kick."""
    pattern = DrumPattern(name="DRILL_SLIDE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.25, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        # Sliding triplet hats
        for trip in range(12):
            vel = 80 if trip % 3 == 0 else 45
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + trip * (4.0 / 12), vel, 0.04))
    return pattern


def generate_tape_stop_break(bars: int = 2) -> DrumPattern:
    """Tape stop break — decelerating hits simulating tape stop."""
    pattern = DrumPattern(name="TAPE_STOP_BREAK", bars=bars)
    total_beats = bars * 4
    pos = 0.0
    interval = 0.125
    while pos < total_beats:
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos,
                                    int(max(40, 120 - pos * 10)), 0.06))
        if int(pos * 4) % 2 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, 100))
        pos += interval
        interval *= 1.08  # gradually decelerate
    return pattern


def generate_glitch_stutter(bars: int = 4) -> DrumPattern:
    """Glitch stutter — random-feeling retriggered hits."""
    import random
    pattern = DrumPattern(name="GLITCH_STUTTER", bars=bars)
    rng = random.Random(42)
    for bar in range(bars):
        b = bar * 4
        # Base groove
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 100))
        # Stutter fills at 16th divisions
        num_stutters = rng.randint(3, 6)
        positions = sorted(rng.sample(range(16), num_stutters))
        for p in positions:
            pos = b + p * 0.25
            drum = rng.choice([GM_DRUMS["hat_closed"], GM_DRUMS["snare"],
                              GM_DRUMS["snare_rim"]])
            pattern.hits.append(DrumHit(drum, pos, rng.randint(50, 89), 0.04))
    return pattern


def generate_double_kick_roll(bars: int = 2) -> DrumPattern:
    """Double kick roll — rapid alternating kick pattern."""
    pattern = DrumPattern(name="DOUBLE_KICK_ROLL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # 32nd note kicks (double pedal style)
        for s in range(32):
            vel = 100 if s % 4 == 0 else 70
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + s * 0.125,
                                        vel, 0.04))
        # Crash accents
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 110, 0.2))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b + 2, 100, 0.2))
    return pattern


def generate_half_swing(bars: int = 4) -> DrumPattern:
    """Half swing — lazy behind-the-beat shuffled groove."""
    pattern = DrumPattern(name="HALF_SWING", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.05, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.1, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.08, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.08, 100))
        for s in range(8):
            swing = 0.1 if s % 2 == 1 else 0
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5 + swing, 55, 0.06))
    return pattern


def generate_crash_cascade(bars: int = 4) -> DrumPattern:
    """Crash cascade — escalating crash cymbal accent pattern."""
    pattern = DrumPattern(name="CRASH_CASCADE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 100))
        # Increasing crash density per bar
        num_crashes = min(bar + 1, 4)
        for c in range(num_crashes):
            pos = b + c * (4.0 / num_crashes)
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], pos, 90 + bar * 8, 0.2))
    return pattern


def generate_rim_click_groove(bars: int = 4) -> DrumPattern:
    """Rim click groove — stripped back pattern using rim clicks."""
    pattern = DrumPattern(name="RIM_CLICK_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 85))
        # Rim clicks on off-beats
        for pos in [0.75, 1.5, 2.25, 3.0, 3.75]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + pos, 80, 0.04))
        # Soft hat pulse
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s, 50, 0.06))
    return pattern


def generate_aggressive_fill(bars: int = 1) -> DrumPattern:
    """Aggressive fill — 32nd-note tom + snare cascade into crash."""
    pattern = DrumPattern(name="AGGRESSIVE_FILL", bars=bars)
    drums = [GM_DRUMS["snare"], GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"],
             GM_DRUMS["kick"]]
    for s in range(bars * 32):
        pos = s * 0.125
        drum_idx = min(s // 8, len(drums) - 1)
        vel = min(127, 70 + s * 2)
        pattern.hits.append(DrumHit(drums[drum_idx], pos, vel, 0.04))
    # Big crash at end
    end = bars * 4 - 0.0625
    pattern.hits.append(DrumHit(GM_DRUMS["crash"], end, 127, 0.3))
    pattern.hits.append(DrumHit(GM_DRUMS["kick"], end, 127))
    return pattern


def generate_lo_fi_shuffle(bars: int = 4) -> DrumPattern:
    """Lo-fi shuffle — swung dusty beat with ghost swipes."""
    pattern = DrumPattern(name="LO_FI_SHUFFLE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.33, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 85))
        # Ghost swipes
        for g in [0.66, 1.66, 2.66, 3.66]:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + g, 35, 0.04))
        # Shuffled hat
        for s in range(6):
            swing = 0.33 if s % 2 == 1 else 0
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.66 + swing, 50, 0.06))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v2.1 — Experimental patterns (8)
# ═══════════════════════════════════════════════════════════════════════════


def generate_soca_kick(bars: int = 4) -> DrumPattern:
    """Soca kick — Caribbean-influenced kick pattern with offbeats."""
    pattern = DrumPattern(name="SOCA_KICK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        for step in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + step * 0.5, 55, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5, 60, 0.1))
    return pattern


def generate_neuro_stutter(bars: int = 4) -> DrumPattern:
    """Neuro stutter — rapid kick stutters with snare accents."""
    import random
    pattern = DrumPattern(name="NEURO_STUTTER", bars=bars)
    rng = random.Random(42)
    for bar in range(bars):
        b = bar * 4
        # Stuttered kicks
        for s in range(16):
            pos = b + s * 0.25
            if rng.random() < 0.6:
                vel = rng.randint(70, 110)
                pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, vel, 0.04))
        # Snare accents on 2 and 4
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 105))
        # Hat wash
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.05))
    return pattern


def generate_afrobeats(bars: int = 4) -> DrumPattern:
    """Afrobeats — bouncy kick/snare with shaker groove."""
    pattern = DrumPattern(name="AFROBEATS", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        # Shaker groove
        for s in range(16):
            vel = 50 if s % 2 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"],
                                        b + s * 0.25, vel, 0.04))
        # Perc accent
        pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + 0.75, 60, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + 2.75, 55, 0.08))
    return pattern


def generate_speed_garage(bars: int = 4) -> DrumPattern:
    """Speed garage — 4/4 kick with choppy offbeat bass and hats."""
    pattern = DrumPattern(name="SPEED_GARAGE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 85))
        for s in range(8):
            vel = 60 if s % 2 == 0 else 45
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, vel, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 1.5, 55, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5, 55, 0.1))
    return pattern


def generate_electro_slam(bars: int = 4) -> DrumPattern:
    """Electro slam — distorted kick with clap stacks and ride."""
    pattern = DrumPattern(name="ELECTRO_SLAM", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.5, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 105))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["ride"],
                                        b + s * 0.5, 55, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 70, 0.3))
    return pattern


def generate_bass_music_groove(bars: int = 4) -> DrumPattern:
    """Bass music groove — minimal with deep kick placement."""
    pattern = DrumPattern(name="BASS_MUSIC_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 95))
        # Sparse hat
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 0.5, 50, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 1.5, 45, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 2.5, 50, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5, 55, 0.1))
        # Rim ghost
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.75, 35, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.25, 30, 0.04))
    return pattern


def generate_complextro(bars: int = 4) -> DrumPattern:
    """Complextro — rapidly switching patterns within a bar."""
    import random
    pattern = DrumPattern(name="COMPLEXTRO", bars=bars)
    rng = random.Random(42)
    for bar in range(bars):
        b = bar * 4
        # First half: 4/4 kick
        for beat in range(2):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 100))
        # Second half: breakbeat-style
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.25, 90))
        # Snares
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 95))
        # Rapid hats that switch pattern
        for s in range(16):
            pos = b + s * 0.25
            vel = rng.randint(40, 70)
            if s < 8:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                            pos, vel, 0.04))
            else:
                if s % 2 == 0:
                    pattern.hits.append(DrumHit(GM_DRUMS["hat_open"],
                                                pos, vel, 0.08))
    return pattern


def generate_moombahton(bars: int = 4) -> DrumPattern:
    """Moombahton — reggaeton-influenced with half-tempo feel."""
    pattern = DrumPattern(name="MOOMBAHTON", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        # Dembow-style hat pattern
        for s in [0, 0.75, 1, 1.75, 2, 2.75, 3, 3.75]:
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s, 50, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["perc_2"], b + 0.5, 55, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["perc_2"], b + 2.5, 50, 0.06))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v2.1 — Intensity patterns (8)
# ═══════════════════════════════════════════════════════════════════════════


def generate_wall_of_kick(bars: int = 4) -> DrumPattern:
    """Wall of kick — relentless 16th-note kicks with crash accents."""
    pattern = DrumPattern(name="WALL_OF_KICK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for s in range(16):
            vel = 100 if s % 4 == 0 else 80
            pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                        b + s * 0.25, vel, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 80, 0.3))
    return pattern


def generate_half_time_dnb(bars: int = 4) -> DrumPattern:
    """Half-time DnB — drum and bass at half speed, spacious."""
    pattern = DrumPattern(name="HALF_TIME_DNB", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 95))
        # Amen-style ghost notes
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.25, 45, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.25, 40, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.5, 75))
        # Fast hats
        for s in range(16):
            vel = 55 if s % 2 == 0 else 40
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["ride"], b + 1, 45, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["ride"], b + 3, 45, 0.1))
    return pattern


def generate_polymetric_5v4(bars: int = 4) -> DrumPattern:
    """Polymetric 5 over 4 — kick in 5, snare in 4."""
    pattern = DrumPattern(name="POLYMETRIC_5V4", bars=bars)
    total_beats = bars * 4
    # Kick in groups of 5/4 beat
    kick_interval = 4.0 / 5.0
    pos = 0.0
    while pos < total_beats:
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, 95))
        pos += kick_interval
    # Snare on beats 2 and 4 of each bar
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 50, 0.05))
    return pattern


def generate_trap_drop(bars: int = 4) -> DrumPattern:
    """Trap drop — heavy 808 kick with triple hat rolls."""
    import random
    pattern = DrumPattern(name="TRAP_DROP", bars=bars)
    rng = random.Random(42)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 85))
        # Triple hat rolls on beat 2-3
        for s in range(12):
            pos = b + 1.5 + s * (1.0 / 6.0)
            vel = rng.randint(40, 70)
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        pos, vel, 0.03))
        # 808 open hat
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 0.5, 55, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5, 55, 0.1))
    return pattern


def generate_bounce_groove(bars: int = 4) -> DrumPattern:
    """Bounce groove — New Orleans bounce-influenced pattern."""
    pattern = DrumPattern(name="BOUNCE_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.75, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 70))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 75))
        # Tambourine bounce
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["perc_2"],
                                        b + s * 0.5, 50, 0.05))
    return pattern


def generate_metalcore_blast(bars: int = 4) -> DrumPattern:
    """Metalcore blast — alternating kick/snare blast with china crash."""
    pattern = DrumPattern(name="METALCORE_BLAST", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for s in range(16):
            pos = b + s * 0.25
            if s % 2 == 0:
                pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, 110, 0.04))
            else:
                pattern.hits.append(DrumHit(GM_DRUMS["snare"], pos, 100, 0.04))
        # Crash accents
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 90, 0.2))
        pattern.hits.append(DrumHit(GM_DRUMS["crash_alt"], b + 2, 85, 0.2))
    return pattern


def generate_ambient_pulse(bars: int = 4) -> DrumPattern:
    """Ambient pulse — soft kick pulse with delicate percussion."""
    pattern = DrumPattern(name="AMBIENT_PULSE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # Soft kick pulse
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 60))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 55))
        # Gentle rim clicks
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 1, 40, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3, 35, 0.05))
        # Ride shimmer
        pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"], b + 0.5, 30, 0.15))
        pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"], b + 2.5, 25, 0.15))
        # Sparse shaker
        if bar % 2 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"], b + 1.5, 25, 0.04))
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"], b + 3.5, 20, 0.04))
    return pattern


def generate_dubstep_tearout(bars: int = 4) -> DrumPattern:
    """Dubstep tearout — aggressive halftime with fill accents."""
    pattern = DrumPattern(name="DUBSTEP_TEAROUT", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        # Sub hits
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.5, 85))
        # Fast hat
        for s in range(16):
            vel = 60 if s % 4 == 0 else 40
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.04))
        # Crash on bar 1 and 3
        if bar % 2 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 100, 0.3))
        # Tom fill on last bar
        if bar == bars - 1:
            for t_idx, t_pos in enumerate([3.0, 3.25, 3.5, 3.75]):
                drums = [GM_DRUMS["tom_high"], GM_DRUMS["tom_mid"],
                         GM_DRUMS["tom_mid"], GM_DRUMS["tom_low"]]
                pattern.hits.append(DrumHit(drums[t_idx], b + t_pos, 90, 0.06))
    return pattern


def generate_wubstep_drop(bars: int = 4) -> DrumPattern:
    """Wubstep drop — heavy kick/snare with wub-rhythm hats."""
    pattern = DrumPattern(name="WUBSTEP_DROP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.25, 90))
        # Wub-rhythm hats
        for s in [0.5, 1.0, 2.5, 3.0, 3.5]:
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + s, 55, 0.04))
        if bar % 2 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 90, 0.3))
    return pattern


def generate_liquid_dnb(bars: int = 4) -> DrumPattern:
    """Liquid DnB — smooth two-step with ghost notes."""
    pattern = DrumPattern(name="LIQUID_DNB", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 105))
        # Ghost snares
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.5, 30, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.0, 25, 0.06))
        # Ride
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["ride"], b + s * 0.5, 50, 0.1))
    return pattern


def generate_stuttered_halftime(bars: int = 4) -> DrumPattern:
    """Stuttered halftime — rapid kick stutters before snare."""
    pattern = DrumPattern(name="STUTTERED_HALFTIME", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        # Stutter kicks
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        # Hats
        for s in range(16):
            vel = 50 if s % 4 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.04))
    return pattern


def generate_garage_shuffle(bars: int = 4) -> DrumPattern:
    """Garage shuffle — swung hats with skippy kick."""
    pattern = DrumPattern(name="GARAGE_SHUFFLE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        # Swung hats (shuffle)
        for s in range(8):
            offset = 0.33 if s % 2 == 1 else 0.0
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5 + offset, 55, 0.04))
        # Open hat accents
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 1.5, 60, 0.1))
    return pattern


def generate_neuro_roll(bars: int = 4) -> DrumPattern:
    """Neuro roll — 32nd note snare/kick rolls in drop sections."""
    pattern = DrumPattern(name="NEURO_ROLL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        # 32nd rolls in last beat
        if bar % 2 == 1:
            for s in range(8):
                pattern.hits.append(DrumHit(GM_DRUMS["snare"],
                                            b + 3 + s * 0.125, 70 + s * 5, 0.03))
        # Hats
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 45, 0.04))
    return pattern


def generate_tribal_stomp(bars: int = 4) -> DrumPattern:
    """Tribal stomp — heavy toms with floor kick pattern."""
    pattern = DrumPattern(name="TRIBAL_STOMP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3, 90))
        # Tom melody
        pattern.hits.append(DrumHit(GM_DRUMS["tom_low"], b + 0.5, 90, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_mid"], b + 1.5, 85, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_high"], b + 2.5, 80, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_mid"], b + 3.5, 75, 0.08))
        # Shaker
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"],
                                        b + s * 0.5, 40, 0.04))
    return pattern


def generate_cinematic_build(bars: int = 4) -> DrumPattern:
    """Cinematic build — increasing density with cymbal swells."""
    pattern = DrumPattern(name="CINEMATIC_BUILD", bars=bars)
    for bar in range(bars):
        b = bar * 4
        density = bar + 1  # increases each bar
        # Kick grows denser
        for s in range(density):
            pos = b + s * (4.0 / density)
            vel = 80 + bar * 10
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], pos, min(vel, 127)))
        # Snare on 2 and 4 (starting from bar 2)
        if bar >= 1:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 100))
        if bar >= 2:
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 80))
            pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 90))
        # Crash swell on last bar
        if bar == bars - 1:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 110, 0.5))
            pattern.hits.append(DrumHit(GM_DRUMS["crash_alt"], b + 2, 100, 0.5))
    return pattern


def generate_glitchstep(bars: int = 4) -> DrumPattern:
    """Glitchstep — randomised hit positions via deterministic RNG."""
    import random
    rng = random.Random(42)
    pattern = DrumPattern(name="GLITCHSTEP", bars=bars)
    drum_keys = ["kick", "snare", "hat_closed", "clap", "snare_rim"]
    for bar in range(bars):
        b = bar * 4
        # Anchor beat
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        # Glitch hits
        for _ in range(8):
            pos = b + rng.random() * 4.0
            key = rng.choice(drum_keys)
            vel = rng.randint(40, 100)
            pattern.hits.append(DrumHit(GM_DRUMS[key], pos, vel, 0.05))
    return pattern


def generate_dubstep_melodic(bars: int = 4) -> DrumPattern:
    """Dubstep melodic — lighter halftime with ride work."""
    pattern = DrumPattern(name="DUBSTEP_MELODIC", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 100))
        # Ride pattern
        for s in range(16):
            vel = 50 if s % 4 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["ride"],
                                        b + s * 0.25, vel, 0.08))
        # Ghost
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 1.5, 25, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3.5, 20, 0.06))
    return pattern


def generate_hardstyle_kick(bars: int = 4) -> DrumPattern:
    """Hardstyle kick — pounding 4/4 kick with offbeat bass drum."""
    pattern = DrumPattern(name="HARDSTYLE_KICK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + s, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b + 0.5, 80))
        pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b + 2.5, 75))
        # Clap on 2/4
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 100))
        # Open hat on offbeats
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_open"],
                                        b + s + 0.5, 60, 0.08))
    return pattern


def generate_hybrid_trap(bars: int = 4) -> DrumPattern:
    """Hybrid trap — 808-style kick with trap hat rolls."""
    pattern = DrumPattern(name="HYBRID_TRAP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.25, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        # Hat rolls (accelerating)
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 50, 0.04))
        # 32nd hat roll in beat 4
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + 3 + s * 0.125, 40 + s * 4, 0.03))
    return pattern


def generate_minimal_techno(bars: int = 4) -> DrumPattern:
    """Minimal techno — stripped 4/4 with pedal hat and rim clicks."""
    pattern = DrumPattern(name="MINIMAL_TECHNO", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + s, 110))
        # Pedal hat on every 8th
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_pedal"],
                                        b + s * 0.5, 45, 0.04))
        # Rim on 2/4
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 1, 70, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 3, 65, 0.06))
    return pattern


def generate_breakstep(bars: int = 4) -> DrumPattern:
    """Breakstep — chopped breakbeat with heavy drops."""
    pattern = DrumPattern(name="BREAKSTEP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.5, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.5, 100))
        # Choppy hats
        for s in [0.25, 0.75, 1.25, 2.0, 2.75, 3.25]:
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s, 55, 0.04))
        # Crash on 1 every 2 bars
        if bar % 2 == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 90, 0.3))
    return pattern


def generate_drum_and_bass_roller(bars: int = 4) -> DrumPattern:
    """D&B roller — relentless rolling beat with offbeat kicks."""
    pattern = DrumPattern(name="DNB_ROLLER", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        # Rolling 16th hats
        for s in range(16):
            vel = 55 if s % 4 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.03))
    return pattern


def generate_phonk_groove(bars: int = 4) -> DrumPattern:
    """Phonk groove — cowbell pattern with heavy kick and clap."""
    pattern = DrumPattern(name="PHONK_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.25, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 105))
        # Cowbell melody
        for s in [0.5, 1.0, 1.5, 2.5, 3.0, 3.5]:
            pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + s, 60, 0.06))
        # Hi-hat
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 50, 0.04))
    return pattern


def generate_double_time_break(bars: int = 4) -> DrumPattern:
    """Double-time breakbeat — fast 2-step with syncopated snares."""
    pattern = DrumPattern(name="DOUBLE_TIME_BREAK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 0.5, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.25, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.25, 100))
        # 16th hats
        for s in range(16):
            vel = 55 if s % 2 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.03))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v2.3 — Hybrid-genre patterns (12)
# ═══════════════════════════════════════════════════════════════════════════


def generate_tearout_stomp(bars: int = 4) -> DrumPattern:
    """Tearout stomp — aggressive halftime with stacked kicks."""
    pattern = DrumPattern(name="TEAROUT_STOMP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.25, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 50, 0.04))
    return pattern


def generate_deep_dubstep(bars: int = 4) -> DrumPattern:
    """Deep dubstep — sparse kick/snare with sub emphasis."""
    pattern = DrumPattern(name="DEEP_DUBSTEP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 1, 40, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 3, 40, 0.04))
    return pattern


def generate_heavy_riddim(bars: int = 4) -> DrumPattern:
    """Heavy riddim — relentless halftime with snare rolls."""
    pattern = DrumPattern(name="HEAVY_RIDDIM", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 95))
        # Snare roll on beat 4
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["snare"],
                                        b + 3 + s * 0.25, 80 + s * 10, 0.05))
        for s in range(8):
            vel = 55 if s % 2 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, vel, 0.04))
    return pattern


def generate_future_bass(bars: int = 4) -> DrumPattern:
    """Future bass — syncopated with open hat emphasis."""
    pattern = DrumPattern(name="FUTURE_BASS", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 0.5, 70, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 2.5, 70, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 1.5, 50, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 3.5, 50, 0.04))
    return pattern


def generate_neurofunk(bars: int = 4) -> DrumPattern:
    """Neurofunk — fast DnB with ghost snares and complex hats."""
    pattern = DrumPattern(name="NEUROFUNK", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        # Ghost snares
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.75, 50, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.25, 45, 0.03))
        for s in range(16):
            vel = 60 if s % 4 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.03))
    return pattern


def generate_bass_house(bars: int = 4) -> DrumPattern:
    """Bass house — four-on-floor with offbeat bass groove."""
    pattern = DrumPattern(name="BASS_HOUSE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3, 105))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 55, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 0.5, 65, 0.08))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 2.5, 65, 0.08))
    return pattern


def generate_deathstep(bars: int = 4) -> DrumPattern:
    """Deathstep — extremely heavy halftime with layered hits."""
    pattern = DrumPattern(name="DEATHSTEP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_alt"], b + 2, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 90, 0.5))
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s, 45, 0.04))
    return pattern


def generate_colour_bass(bars: int = 4) -> DrumPattern:
    """Colour bass — minimal kick/snare with sparse percussion."""
    pattern = DrumPattern(name="COLOUR_BASS", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 1, 35, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 3, 35, 0.04))
        if bar % 2 == 1:
            pattern.hits.append(DrumHit(GM_DRUMS["perc_1"], b + 3.5, 55, 0.05))
    return pattern


def generate_wave_groove(bars: int = 4) -> DrumPattern:
    """Wave/grime — skippy 2-step with rim clicks."""
    pattern = DrumPattern(name="WAVE_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.75, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.5, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.75, 60, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.25, 55, 0.03))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.04))
    return pattern


def generate_midtempo(bars: int = 4) -> DrumPattern:
    """Midtempo — slow powerful groove at ~100 BPM feel."""
    pattern = DrumPattern(name="MIDTEMPO", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 90))
        for s in range(8):
            vel = 50 if s % 2 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, vel, 0.04))
    return pattern


def generate_brostep(bars: int = 4) -> DrumPattern:
    """Brostep — aggressive with rapid hat patterns."""
    pattern = DrumPattern(name="BROSTEP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        # Rapid hats
        for s in range(16):
            vel = 65 if s % 4 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 85, 0.5))
    return pattern


def generate_freeform_bass(bars: int = 4) -> DrumPattern:
    """Freeform bass — unpredictable syncopation."""
    import random
    rng = random.Random(42)
    pattern = DrumPattern(name="FREEFORM_BASS", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        # Random extra hits
        for _ in range(3):
            pos = rng.choice([0.5, 1.0, 1.5, 2.5, 3.0, 3.5])
            drum = rng.choice(["hat_closed", "snare_rim", "perc_1"])
            pattern.hits.append(DrumHit(GM_DRUMS[drum], b + pos,
                                        rng.randint(40, 80), 0.04))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# v2.3 — Fill & build patterns (12)
# ═══════════════════════════════════════════════════════════════════════════


def generate_snare_build_32(bars: int = 4) -> DrumPattern:
    """32nd-note snare build — accelerating intensity."""
    pattern = DrumPattern(name="SNARE_BUILD_32", bars=bars)
    for bar in range(bars):
        b = bar * 4
        density = 4 + bar * 4  # increasingly dense
        for s in range(density):
            pos = s * (4.0 / density)
            vel = 60 + int(40 * s / max(1, density - 1))
            pattern.hits.append(DrumHit(GM_DRUMS["snare"],
                                        b + pos, vel, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
    return pattern


def generate_kick_march(bars: int = 4) -> DrumPattern:
    """Kick march — steady march-tempo kicks with rim accents."""
    pattern = DrumPattern(name="KICK_MARCH", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                        b + beat, 100 + (beat % 2) * 20))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 0.5, 60, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2.5, 60, 0.03))
    return pattern


def generate_tom_fill_cascade(bars: int = 4) -> DrumPattern:
    """Tom cascade fill — toms descending through the bar."""
    pattern = DrumPattern(name="TOM_FILL_CASCADE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        toms = ["tom_high", "tom_mid", "tom_low"]
        for i, tom in enumerate(toms):
            for s in range(4):
                pattern.hits.append(DrumHit(GM_DRUMS[tom],
                                            b + i + s * 0.25,
                                            90 + s * 5, 0.06))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b + 3.5, 100, 0.3))
    return pattern


def generate_hat_barrage(bars: int = 4) -> DrumPattern:
    """Hat barrage — 32nd hi-hat rolls with velocity dynamics."""
    pattern = DrumPattern(name="HAT_BARRAGE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 115))
        for s in range(32):
            vel = 30 + int(40 * abs(math.sin(s * 0.3)))
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.125, vel, 0.02))
    return pattern


def generate_crash_wall(bars: int = 4) -> DrumPattern:
    """Crash wall — layered crash hits building intensity."""
    pattern = DrumPattern(name="CRASH_WALL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 100, 0.5))
        if bar >= 1:
            pattern.hits.append(DrumHit(GM_DRUMS["crash_alt"], b + 2, 90, 0.4))
        if bar >= 2:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b + 1, 85, 0.3))
            pattern.hits.append(DrumHit(GM_DRUMS["crash_alt"], b + 3, 85, 0.3))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
    return pattern


def generate_ride_groove(bars: int = 4) -> DrumPattern:
    """Ride groove — jazzy ride bell pattern with kick/snare."""
    pattern = DrumPattern(name="RIDE_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 105))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 100))
        for s in range(8):
            drum = "ride_bell" if s % 2 == 0 else "ride"
            pattern.hits.append(DrumHit(GM_DRUMS[drum],
                                        b + s * 0.5, 55, 0.06))
    return pattern


def generate_perc_polyrhythm(bars: int = 4) -> DrumPattern:
    """Percussion polyrhythm — 3 over 4 with perc instruments."""
    pattern = DrumPattern(name="PERC_POLYRHYTHM", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # 4 beats
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                        b + beat, 105))
        # 3 over 4 on perc
        for s in range(3):
            pattern.hits.append(DrumHit(GM_DRUMS["perc_1"],
                                        b + s * (4.0 / 3), 75, 0.05))
            pattern.hits.append(DrumHit(GM_DRUMS["perc_2"],
                                        b + s * (4.0 / 3) + 0.5, 60, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
    return pattern


def generate_shaker_roll(bars: int = 4) -> DrumPattern:
    """Shaker roll — continuous shaker with accent pattern."""
    pattern = DrumPattern(name="SHAKER_ROLL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 105))
        for s in range(16):
            vel = 60 if s % 4 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"],
                                        b + s * 0.25, vel, 0.03))
    return pattern


def generate_stuttered_snare(bars: int = 4) -> DrumPattern:
    """Stuttered snare — glitchy snare placement."""
    pattern = DrumPattern(name="STUTTERED_SNARE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 115))
        # Stutter hits
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.125, 80, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.25, 60, 0.03))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.375, 45, 0.03))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 45, 0.04))
    return pattern


def generate_trap_triplet(bars: int = 4) -> DrumPattern:
    """Trap triplet — triplet hi-hat with 808 kick pattern."""
    pattern = DrumPattern(name="TRAP_TRIPLET", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        # Triplet hats
        for s in range(12):
            vel = 55 if s % 3 == 0 else 30
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * (4.0 / 12), vel, 0.03))
    return pattern


def generate_industrial_march(bars: int = 4) -> DrumPattern:
    """Industrial march — mechanical repetitive pattern."""
    pattern = DrumPattern(name="INDUSTRIAL_MARCH", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + beat, 115))
            pattern.hits.append(DrumHit(GM_DRUMS["hat_pedal"],
                                        b + beat + 0.5, 55, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1, 90))
    return pattern


def generate_ambient_scatter(bars: int = 4) -> DrumPattern:
    """Ambient scatter — sparse randomized percussive textures."""
    import random
    rng = random.Random(77)
    pattern = DrumPattern(name="AMBIENT_SCATTER", bars=bars)
    drums = ["hat_closed", "ride", "ride_bell", "perc_1", "shaker"]
    for bar in range(bars):
        b = bar * 4
        n_hits = rng.randint(3, 6)
        for _ in range(n_hits):
            pos = rng.uniform(0, 4.0)
            drum = rng.choice(drums)
            pattern.hits.append(DrumHit(GM_DRUMS[drum],
                                        b + pos, rng.randint(25, 55), 0.05))
    return pattern


# --- v2.4 Weapon patterns (10) ---


def generate_dubstep_weapon(bars: int = 4) -> DrumPattern:
    """Dubstep weapon — aggressive kick-snare with percussive fills."""
    pattern = DrumPattern(name="DUBSTEP_WEAPON", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 50 + (s % 2) * 20, 0.04))
        if bar % 2 == 1:
            for f in range(4):
                pattern.hits.append(DrumHit(GM_DRUMS["snare"],
                                            b + 3 + f * 0.25, 70 + f * 10, 0.03))
    return pattern


def generate_riddim_bounce(bars: int = 4) -> DrumPattern:
    """Riddim bounce — syncopated bounce groove."""
    pattern = DrumPattern(name="RIDDIM_BOUNCE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 3.5, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        for s in range(16):
            vel = 55 if s % 2 == 0 else 35
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, vel, 0.03))
    return pattern


def generate_half_time_weapon(bars: int = 4) -> DrumPattern:
    """Half-time weapon — heavy half-time with crash accents."""
    pattern = DrumPattern(name="HALF_TIME_WEAPON", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 125))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 100))
        if bar == 0:
            pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 1.5, 65, 0.1))
    return pattern


def generate_stutter_bounce(bars: int = 4) -> DrumPattern:
    """Stutter bounce — glitchy kick stutter with bounce."""
    pattern = DrumPattern(name="STUTTER_BOUNCE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        # Stutter kicks
        for i in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                        b + i * 0.125, 120 - i * 10))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 45, 0.04))
    return pattern


def generate_breakstep_chop(bars: int = 4) -> DrumPattern:
    """Breakstep chop — chopped breakbeat dubstep hybrid."""
    import random
    rng = random.Random(42)
    pattern = DrumPattern(name="BREAKSTEP_CHOP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2.75, 110))
        for s in range(16):
            if rng.random() < 0.6:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                            b + s * 0.25, rng.randint(30, 60), 0.03))
    return pattern


def generate_tearout_slam(bars: int = 4) -> DrumPattern:
    """Tearout slam — maximum impact dubstep drop pattern."""
    pattern = DrumPattern(name="TEAROUT_SLAM", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 127))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_low"], b + 3, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_mid"], b + 3.25, 85))
        pattern.hits.append(DrumHit(GM_DRUMS["tom_high"], b + 3.5, 80))
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s, 50, 0.04))
    return pattern


def generate_experimental_grid(bars: int = 4) -> DrumPattern:
    """Experimental grid — mathematically-spaced odd grid."""
    pattern = DrumPattern(name="EXPERIMENTAL_GRID", bars=bars)
    for bar in range(bars):
        b = bar * 4
        for i in range(7):
            pos = i * (4.0 / 7.0)
            if i % 2 == 0:
                pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                            b + pos, 100))
            else:
                pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"],
                                            b + pos, 80, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5, 55, 0.1))
    return pattern


def generate_phi_grid(bars: int = 4) -> DrumPattern:
    """Phi grid — golden ratio-spaced rhythmic pattern."""
    pattern = DrumPattern(name="PHI_GRID", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pos = 0.0
        step = 4.0 / PHI
        while pos < 4.0:
            pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + pos, 110))
            pos += step
            step /= PHI
            if step < 0.125:
                break
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 115))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.04))
    return pattern


def generate_fibonacci_cascade(bars: int = 4) -> DrumPattern:
    """Fibonacci cascade — Fibonacci-sequence hit placements."""
    pattern = DrumPattern(name="FIBONACCI_CASCADE", bars=bars)
    fib_pos = [f / max(FIBONACCI[:8]) * 4.0 for f in FIBONACCI[:8] if f > 0]
    for bar in range(bars):
        b = bar * 4
        for i, fp in enumerate(fib_pos):
            if fp < 4.0:
                if i % 2 == 0:
                    pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                                b + fp, 105))
                else:
                    pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"],
                                                b + fp, 85, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 80))
    return pattern


def generate_cymbal_wash(bars: int = 4) -> DrumPattern:
    """Cymbal wash — ride and crash layered wash."""
    pattern = DrumPattern(name="CYMBAL_WASH", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 100))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["ride"],
                                        b + s * 0.5, 55, 0.1))
        pattern.hits.append(DrumHit(GM_DRUMS["crash"], b, 70))
        if bar % 2 == 1:
            pattern.hits.append(DrumHit(GM_DRUMS["crash_alt"], b + 2, 65))
    return pattern


# --- v2.4 Groove patterns (10) ---


def generate_syncopated_stomp(bars: int = 4) -> DrumPattern:
    """Syncopated stomp — off-beat stomping groove."""
    pattern = DrumPattern(name="SYNCOPATED_STOMP", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 0.75, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1.5, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3.5, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1.5, 80))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 45, 0.04))
    return pattern


def generate_tom_roll_fill(bars: int = 4) -> DrumPattern:
    """Tom roll fill — descending tom roll build."""
    pattern = DrumPattern(name="TOM_ROLL_FILL", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.04))
        if bar == bars - 1:
            toms = ["tom_high", "tom_mid", "tom_low"]
            for i in range(12):
                pattern.hits.append(DrumHit(GM_DRUMS[toms[i % 3]],
                                            b + 2 + i * (2.0 / 12), 85 + i * 3, 0.05))
    return pattern


def generate_ghost_kick_groove(bars: int = 4) -> DrumPattern:
    """Ghost kick groove — main kick with ghost kick notes."""
    pattern = DrumPattern(name="GHOST_KICK_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b + 0.75, 50))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick_alt"], b + 2.75, 45))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        for s in range(16):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.25, 35, 0.03))
    return pattern


def generate_percussion_ensemble(bars: int = 4) -> DrumPattern:
    """Percussion ensemble — layered perc voices."""
    pattern = DrumPattern(name="PERCUSSION_ENSEMBLE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 105))
        # Perc layer 1 — quarter notes
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["perc_1"],
                                        b + s, 70, 0.05))
        # Perc layer 2 — offbeats
        for s in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["perc_2"],
                                        b + s + 0.5, 55, 0.05))
        # Shaker continuous
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["shaker"],
                                        b + s * 0.5, 35, 0.03))
    return pattern


def generate_double_snare_groove(bars: int = 4) -> DrumPattern:
    """Double snare groove — doubled snare hits for width."""
    pattern = DrumPattern(name="DOUBLE_SNARE_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        # Double snare
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_alt"], b + 1 + 0.02, 90))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["snare_alt"], b + 3 + 0.02, 90))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 45, 0.04))
    return pattern


def generate_swing_bass(bars: int = 4) -> DrumPattern:
    """Swing bass — swung kick pattern with shuffle feel."""
    pattern = DrumPattern(name="SWING_BASS", bars=bars)
    swing = 0.17  # Swing amount
    for bar in range(bars):
        b = bar * 4
        for beat in range(4):
            pattern.hits.append(DrumHit(GM_DRUMS["kick"],
                                        b + beat, 110))
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + beat + 0.5 + swing, 50, 0.04))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_open"], b + 3.5 + swing, 60, 0.1))
    return pattern


def generate_minimal_pulse(bars: int = 4) -> DrumPattern:
    """Minimal pulse — ultra-sparse pulse groove."""
    pattern = DrumPattern(name="MINIMAL_PULSE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 100))
        if bar % 2 == 1:
            pattern.hits.append(DrumHit(GM_DRUMS["snare_rim"], b + 2, 70, 0.05))
        pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"], b + 2, 35, 0.04))
    return pattern


def generate_ride_bell_groove(bars: int = 4) -> DrumPattern:
    """Ride bell groove — ride bell-led pattern."""
    pattern = DrumPattern(name="RIDE_BELL_GROOVE", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 110))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 105))
        for s in range(8):
            vel = 70 if s % 2 == 0 else 45
            pattern.hits.append(DrumHit(GM_DRUMS["ride_bell"],
                                        b + s * 0.5, vel, 0.06))
    return pattern


def generate_clap_snare_layer(bars: int = 4) -> DrumPattern:
    """Clap snare layer — layered clap and snare backbeat."""
    pattern = DrumPattern(name="CLAP_SNARE_LAYER", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 120))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 1.75, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 1, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 1 + 0.01, 95))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 3, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["clap"], b + 3 + 0.01, 95))
        for s in range(8):
            pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                        b + s * 0.5, 40, 0.04))
    return pattern


def generate_open_hat_accent(bars: int = 4) -> DrumPattern:
    """Open hat accent — open hi-hat accented groove."""
    pattern = DrumPattern(name="OPEN_HAT_ACCENT", bars=bars)
    for bar in range(bars):
        b = bar * 4
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b, 115))
        pattern.hits.append(DrumHit(GM_DRUMS["kick"], b + 2.5, 100))
        pattern.hits.append(DrumHit(GM_DRUMS["snare"], b + 2, 110))
        for s in range(8):
            if s in (1, 5):
                pattern.hits.append(DrumHit(GM_DRUMS["hat_open"],
                                            b + s * 0.5, 70, 0.12))
            else:
                pattern.hits.append(DrumHit(GM_DRUMS["hat_closed"],
                                            b + s * 0.5, 40, 0.04))
    return pattern


# ═══════════════════════════════════════════════════════════════════════════
# ALL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

ALL_DRUM_PATTERNS = {
    # --- Original (6) ---
    "dubstep_drop":          generate_dubstep_drop,
    "dubstep_build":         generate_dubstep_build,
    "halftime_groove":       generate_halftime_groove,
    "fibonacci_fill":        generate_fibonacci_fill,
    "breakbeat":             generate_breakbeat,
    "intro_minimal":         generate_intro_minimal,
    # --- v1.7 (4) ---
    "snare_roll_32nd":       generate_snare_roll_32nd,
    "tom_cascade_fill":      generate_tom_cascade_fill,
    "riddim_minimal":        generate_riddim_minimal,
    "triplet_hat_groove":    generate_triplet_hat_groove,
    # --- v1.8 Beat-map patterns (10) ---
    "double_time_hat":       generate_double_time_hat,
    "shuffle_groove":        generate_shuffle_groove,
    "four_on_floor":         generate_four_on_floor,
    "syncopated_kick":       generate_syncopated_kick,
    "ghost_snare_groove":    generate_ghost_snare_groove,
    "cymbal_accent":         generate_cymbal_accent,
    "open_hat_groove":       generate_open_hat_groove,
    "ride_pattern":          generate_ride_pattern,
    "half_shuffle":          generate_half_shuffle,
    "perc_layer":            generate_perc_layer,
    # --- v1.8 Dynamic patterns (10) ---
    "trap_hat_roll":         generate_trap_hat_roll,
    "militaristic_snare":    generate_militaristic_snare,
    "polyrhythm_3v4":        generate_polyrhythm_3v4,
    "dnb_crossover":         generate_dnb_crossover,
    "flam_fill":             generate_flam_fill,
    "tribal_toms":           generate_tribal_toms,
    "stutter_kick":          generate_stutter_kick,
    "outro_decay":           generate_outro_decay,
    "micro_fill":            generate_micro_fill,
    "triplet_snare_build":   generate_triplet_snare_build,
    # --- v1.9 Genre patterns (10) ---
    "breakcore_chop":        generate_breakcore_chop,
    "uk_garage":             generate_uk_garage,
    "wonky_groove":          generate_wonky_groove,
    "industrial_slam":       generate_industrial_slam,
    "reggaeton_dembow":      generate_reggaeton_dembow,
    "blast_beat":            generate_blast_beat,
    "swing_shuffle":         generate_swing_shuffle,
    "phi_euclidean":         generate_phi_euclidean,
    "double_pedal":          generate_double_pedal,
    "sparse_ambient":        generate_sparse_ambient,
    # --- v1.9 Texture patterns (10) ---
    "march_snare":           generate_march_snare,
    "lo_fi_beat":            generate_lo_fi_beat,
    "cross_stick":           generate_cross_stick,
    "tom_groove":            generate_tom_groove,
    "kick_snare_only":       generate_kick_snare_only,
    "clap_stack":            generate_clap_stack,
    "shaker_groove":         generate_shaker_groove,
    "crash_accent":          generate_crash_accent,
    "countdown_fill":        generate_countdown_fill,
    "reverse_buildup":       generate_reverse_buildup,
    # --- v2.0 Hybrid patterns (8) ---
    "heavy_halftime":        generate_heavy_halftime,
    "rolling_16ths":         generate_rolling_16ths,
    "broken_beat":           generate_broken_beat,
    "jungle_break":          generate_jungle_break,
    "garage_2step":          generate_garage_2step,
    "riddim_heavy":          generate_riddim_heavy,
    "footwork":              generate_footwork,
    "drill_slide":           generate_drill_slide,
    # --- v2.0 Production patterns (8) ---
    "tape_stop_break":       generate_tape_stop_break,
    "glitch_stutter":        generate_glitch_stutter,
    "double_kick_roll":      generate_double_kick_roll,
    "half_swing":            generate_half_swing,
    "crash_cascade":         generate_crash_cascade,
    "rim_click_groove":      generate_rim_click_groove,
    "aggressive_fill":       generate_aggressive_fill,
    "lo_fi_shuffle":         generate_lo_fi_shuffle,
    # --- v2.1 Experimental patterns (8) ---
    "soca_kick":             generate_soca_kick,
    "neuro_stutter":         generate_neuro_stutter,
    "afrobeats":             generate_afrobeats,
    "speed_garage":          generate_speed_garage,
    "electro_slam":          generate_electro_slam,
    "bass_music_groove":     generate_bass_music_groove,
    "complextro":            generate_complextro,
    "moombahton":            generate_moombahton,
    # --- v2.1 Intensity patterns (8) ---
    "wall_of_kick":          generate_wall_of_kick,
    "half_time_dnb":         generate_half_time_dnb,
    "polymetric_5v4":        generate_polymetric_5v4,
    "trap_drop":             generate_trap_drop,
    "bounce_groove":         generate_bounce_groove,
    "metalcore_blast":       generate_metalcore_blast,
    "ambient_pulse":         generate_ambient_pulse,
    "dubstep_tearout":       generate_dubstep_tearout,
    # --- v2.2 Sub-genre patterns (8) ---
    "wubstep_drop":          generate_wubstep_drop,
    "liquid_dnb":            generate_liquid_dnb,
    "stuttered_halftime":    generate_stuttered_halftime,
    "garage_shuffle":        generate_garage_shuffle,
    "neuro_roll":            generate_neuro_roll,
    "tribal_stomp":          generate_tribal_stomp,
    "cinematic_build":       generate_cinematic_build,
    "glitchstep":            generate_glitchstep,
    # --- v2.2 Crossover patterns (8) ---
    "dubstep_melodic":       generate_dubstep_melodic,
    "hardstyle_kick":        generate_hardstyle_kick,
    "hybrid_trap":           generate_hybrid_trap,
    "minimal_techno":        generate_minimal_techno,
    "breakstep":             generate_breakstep,
    "dnb_roller":            generate_drum_and_bass_roller,
    "phonk_groove":          generate_phonk_groove,
    "double_time_break":     generate_double_time_break,
    # --- v2.3 Hybrid-genre patterns (12) ---
    "tearout_stomp":         generate_tearout_stomp,
    "deep_dubstep":          generate_deep_dubstep,
    "heavy_riddim":          generate_heavy_riddim,
    "future_bass":           generate_future_bass,
    "neurofunk":             generate_neurofunk,
    "bass_house":            generate_bass_house,
    "deathstep":             generate_deathstep,
    "colour_bass":           generate_colour_bass,
    "wave_groove":           generate_wave_groove,
    "midtempo":              generate_midtempo,
    "brostep":               generate_brostep,
    "freeform_bass":         generate_freeform_bass,
    # --- v2.3 Fill & build patterns (12) ---
    "snare_build_32":        generate_snare_build_32,
    "kick_march":            generate_kick_march,
    "tom_fill_cascade":      generate_tom_fill_cascade,
    "hat_barrage":           generate_hat_barrage,
    "crash_wall":            generate_crash_wall,
    "ride_groove":           generate_ride_groove,
    "perc_polyrhythm":       generate_perc_polyrhythm,
    "shaker_roll":           generate_shaker_roll,
    "stuttered_snare":       generate_stuttered_snare,
    "trap_triplet":          generate_trap_triplet,
    "industrial_march":      generate_industrial_march,
    "ambient_scatter":       generate_ambient_scatter,
    # --- v2.4 Weapon patterns (10) ---
    "dubstep_weapon":        generate_dubstep_weapon,
    "riddim_bounce":         generate_riddim_bounce,
    "half_time_weapon":      generate_half_time_weapon,
    "stutter_bounce":        generate_stutter_bounce,
    "breakstep_chop":        generate_breakstep_chop,
    "tearout_slam":          generate_tearout_slam,
    "experimental_grid":     generate_experimental_grid,
    "phi_grid":              generate_phi_grid,
    "fibonacci_cascade":     generate_fibonacci_cascade,
    "cymbal_wash":           generate_cymbal_wash,
    # --- v2.4 Groove patterns (10) ---
    "syncopated_stomp":      generate_syncopated_stomp,
    "tom_roll_fill":         generate_tom_roll_fill,
    "ghost_kick_groove":     generate_ghost_kick_groove,
    "percussion_ensemble":   generate_percussion_ensemble,
    "double_snare_groove":   generate_double_snare_groove,
    "swing_bass":            generate_swing_bass,
    "minimal_pulse":         generate_minimal_pulse,
    "ride_bell_groove":      generate_ride_bell_groove,
    "clap_snare_layer":      generate_clap_snare_layer,
    "open_hat_accent":       generate_open_hat_accent,
}


# ═══════════════════════════════════════════════════════════════════════════
# MIDI EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def pattern_to_midi_track(pattern: DrumPattern, bpm: float = DEFAULT_BPM) -> mido.MidiTrack:
    """Convert a DrumPattern to a mido MidiTrack."""
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=pattern.name, time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.MetaMessage("time_signature",
                                  numerator=pattern.time_sig[0],
                                  denominator=pattern.time_sig[1],
                                  time=0))

    # Build absolute-time event list
    events = []
    for hit in pattern.hits:
        start_tick = int(hit.beat * TICKS_PER_BEAT)
        dur_ticks = max(1, int(hit.duration * TICKS_PER_BEAT))
        events.append((start_tick, "note_on", hit.note, hit.velocity))
        events.append((start_tick + dur_ticks, "note_off", hit.note, 0))

    # Sort by time, then note_off before note_on at same tick
    events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))

    # Convert to delta time
    current_tick = 0
    for tick, msg_type, note, vel in events:
        delta = tick - current_tick
        track.append(mido.Message(msg_type, note=note, velocity=vel,
                                  channel=DRUM_CHANNEL, time=delta))
        current_tick = tick

    track.append(mido.MetaMessage("end_of_track", time=0))
    return track


def write_drum_midi(pattern: DrumPattern, path: str,
                    bpm: float = DEFAULT_BPM) -> str:
    """Write a single drum pattern to a MIDI file."""
    mid = mido.MidiFile(type=0, ticks_per_beat=TICKS_PER_BEAT)
    track = pattern_to_midi_track(pattern, bpm)
    mid.tracks.append(track)

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out_path))
    _log.info("Wrote drum MIDI: %s (%d hits)", out_path.name, len(pattern.hits))
    return str(out_path)


def write_full_drum_arrangement(patterns: dict[str, DrumPattern],
                                path: str,
                                bpm: float = DEFAULT_BPM) -> str:
    """
    Write a multi-track drum MIDI with one track per pattern.
    Creates a full arrangement: intro → build → drop → fill → breakbeat.
    """
    mid = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    # Tempo track
    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    tempo_track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    tempo_track.append(mido.MetaMessage("track_name", name="DUBFORGE_DRUMS", time=0))
    tempo_track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(tempo_track)

    # Arrangement order — full dubstep track structure
    arrangement = [
        ("intro_minimal",      0),           # bars 1-8:   sparse intro
        ("dubstep_build",      8 * 4),       # bars 9-16:  build w/ snare accel
        ("snare_roll_32nd",    14 * 4),       # bars 15-16: 32nd roll finisher
        ("dubstep_drop",       16 * 4),       # bars 17-20: main drop
        ("fibonacci_fill",     20 * 4),       # bar 21:     Fibonacci fill
        ("halftime_groove",    21 * 4),       # bars 22-25: half-time groove
        ("riddim_minimal",     25 * 4),       # bars 26-29: riddim breakdown
        ("triplet_hat_groove", 29 * 4),       # bars 30-33: triplet groove
        ("tom_cascade_fill",   33 * 4),       # bar 34:     tom cascade → drop 2
        ("breakbeat",          34 * 4),       # bars 35-38: breakbeat section
    ]

    for pattern_name, start_beat in arrangement:
        if pattern_name in patterns:
            pattern = patterns[pattern_name]
            track = mido.MidiTrack()
            track.append(mido.MetaMessage("track_name", name=pattern.name, time=0))

            events = []
            for hit in pattern.hits:
                abs_tick = int((start_beat + hit.beat) * TICKS_PER_BEAT)
                dur_ticks = max(1, int(hit.duration * TICKS_PER_BEAT))
                events.append((abs_tick, "note_on", hit.note, hit.velocity))
                events.append((abs_tick + dur_ticks, "note_off", hit.note, 0))

            events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))

            current_tick = 0
            for tick, msg_type, note, vel in events:
                delta = tick - current_tick
                track.append(mido.Message(msg_type, note=note, velocity=vel,
                                          channel=DRUM_CHANNEL, time=delta))
                current_tick = tick

            track.append(mido.MetaMessage("end_of_track", time=0))
            mid.tracks.append(track)

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out_path))
    _log.info("Wrote full drum arrangement: %s (%d tracks)", out_path.name, len(mid.tracks))
    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_drum_manifest(patterns: dict[str, DrumPattern],
                        midi_dir: str,
                        bpm: float = DEFAULT_BPM) -> str:
    """Write a JSON manifest of all generated drum MIDI files."""
    manifest = {
        "generator": "DUBFORGE Drum Generator",
        "bpm": bpm,
        "ticks_per_beat": TICKS_PER_BEAT,
        "patterns": {},
    }
    for name, pattern in patterns.items():
        manifest["patterns"][name] = {
            "name": pattern.name,
            "bars": pattern.bars,
            "time_signature": f"{pattern.time_sig[0]}/{pattern.time_sig[1]}",
            "total_hits": len(pattern.hits),
            "midi_file": f"drums_{name}.mid",
        }

    manifest_path = Path(midi_dir) / "drums_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return str(manifest_path)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    midi_dir = Path("output/midi")
    midi_dir.mkdir(parents=True, exist_ok=True)

    patterns = {}
    for name, gen_fn in ALL_DRUM_PATTERNS.items():
        pattern = gen_fn()
        patterns[name] = pattern
        path = str(midi_dir / f"drums_{name}.mid")
        write_drum_midi(pattern, path)
        print(f"  drums_{name}.mid  ({pattern.bars} bars, {len(pattern.hits)} hits)")

    # Full arrangement
    full_path = str(midi_dir / "drums_FULL_KIT.mid")
    write_full_drum_arrangement(patterns, full_path)
    print(f"  drums_FULL_KIT.mid  (full arrangement, {len(patterns)} patterns)")

    # Manifest
    write_drum_manifest(patterns, str(midi_dir))
    print("  drums_manifest.json")

    print(f"Drum Generator complete — {len(patterns) + 1} MIDI files.")


if __name__ == "__main__":
    main()
