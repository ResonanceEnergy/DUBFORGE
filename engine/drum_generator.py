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
