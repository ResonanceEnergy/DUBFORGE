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


# ═══════════════════════════════════════════════════════════════════════════
# ALL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

ALL_DRUM_PATTERNS = {
    "dubstep_drop":     generate_dubstep_drop,
    "dubstep_build":    generate_dubstep_build,
    "halftime_groove":  generate_halftime_groove,
    "fibonacci_fill":   generate_fibonacci_fill,
    "breakbeat":        generate_breakbeat,
    "intro_minimal":    generate_intro_minimal,
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

    # Arrangement order
    arrangement = [
        ("intro_minimal", 0),
        ("dubstep_build", 8 * 4),     # starts at bar 9
        ("dubstep_drop",  16 * 4),    # starts at bar 17
        ("fibonacci_fill", 20 * 4),   # starts at bar 21
        ("halftime_groove", 21 * 4),  # starts at bar 22
        ("breakbeat",      25 * 4),   # starts at bar 26
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
