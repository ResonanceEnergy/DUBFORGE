"""
DUBFORGE — MIDI Processor Engine  (Session 175)

Extended MIDI processing: input parsing, quantization,
humanization, chord detection, and velocity mapping.
"""

import math
import random
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

# Chord templates (intervals from root)
CHORD_TEMPLATES: dict[str, list[int]] = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dim7": [0, 3, 6, 9],
    "add9": [0, 4, 7, 14],
    "power": [0, 7],
    "power5": [0, 7, 12],
}


@dataclass
class MIDINote:
    """A MIDI note event."""
    note: int  # 0-127
    velocity: int  # 0-127
    start_tick: int
    duration_ticks: int
    channel: int = 0

    @property
    def name(self) -> str:
        return f"{NOTE_NAMES[self.note % 12]}{self.note // 12 - 1}"

    @property
    def freq(self) -> float:
        return 432.0 * (2.0 ** ((self.note - 69) / 12.0))

    def to_dict(self) -> dict:
        return {
            "note": self.note,
            "name": self.name,
            "velocity": self.velocity,
            "start": self.start_tick,
            "duration": self.duration_ticks,
            "channel": self.channel,
        }


@dataclass
class MIDITrack:
    """A collection of MIDI notes."""
    name: str = "Track"
    notes: list[MIDINote] = field(default_factory=list)
    ppq: int = 480  # Pulses per quarter note

    @property
    def total_ticks(self) -> int:
        if not self.notes:
            return 0
        return max(n.start_tick + n.duration_ticks for n in self.notes)

    def sort(self) -> None:
        self.notes.sort(key=lambda n: (n.start_tick, n.note))


@dataclass
class ChordEvent:
    """A detected chord."""
    root: int
    chord_type: str
    tick: int
    notes: list[int] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"{NOTE_NAMES[self.root % 12]}{self.chord_type}"


def quantize(track: MIDITrack, grid_ticks: int = 120,
             strength: float = 1.0) -> MIDITrack:
    """Quantize notes to grid. strength=1.0 is full quantize."""
    result = MIDITrack(name=track.name, ppq=track.ppq)
    for note in track.notes:
        nearest = round(note.start_tick / grid_ticks) * grid_ticks
        new_start = int(note.start_tick + (nearest - note.start_tick) * strength)
        result.notes.append(MIDINote(
            note=note.note,
            velocity=note.velocity,
            start_tick=max(0, new_start),
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))
    result.sort()
    return result


def humanize(track: MIDITrack, timing_range: int = 10,
             velocity_range: int = 10,
             seed: int = 42) -> MIDITrack:
    """Add human feel to quantized MIDI."""
    rng = random.Random(seed)
    result = MIDITrack(name=track.name, ppq=track.ppq)

    for note in track.notes:
        t_offset = rng.randint(-timing_range, timing_range)
        v_offset = rng.randint(-velocity_range, velocity_range)
        result.notes.append(MIDINote(
            note=note.note,
            velocity=max(1, min(127, note.velocity + v_offset)),
            start_tick=max(0, note.start_tick + t_offset),
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))

    result.sort()
    return result


def phi_humanize(track: MIDITrack, seed: int = 42) -> MIDITrack:
    """Humanize with PHI-weighted timing offsets."""
    rng = random.Random(seed)
    result = MIDITrack(name=track.name, ppq=track.ppq)

    for note in track.notes:
        phi_offset = int(rng.gauss(0, track.ppq / (PHI * 8)))
        # Velocity: PHI curve
        beat_pos = (note.start_tick % (track.ppq * 4)) / (track.ppq * 4)
        phi_vel = int(note.velocity * (0.9 + 0.1 * math.sin(
            2 * math.pi * beat_pos * PHI)))
        result.notes.append(MIDINote(
            note=note.note,
            velocity=max(1, min(127, phi_vel)),
            start_tick=max(0, note.start_tick + phi_offset),
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))

    result.sort()
    return result


def detect_chords(track: MIDITrack,
                   window_ticks: int = 120) -> list[ChordEvent]:
    """Detect chords from simultaneous notes."""
    if not track.notes:
        return []

    track.sort()
    chords: list[ChordEvent] = []

    # Group notes by time window
    groups: list[list[MIDINote]] = []
    current_group: list[MIDINote] = [track.notes[0]]

    for note in track.notes[1:]:
        if note.start_tick - current_group[0].start_tick <= window_ticks:
            current_group.append(note)
        else:
            if len(current_group) >= 2:
                groups.append(current_group)
            current_group = [note]
    if len(current_group) >= 2:
        groups.append(current_group)

    # Match groups against chord templates
    for group in groups:
        pitches = sorted(set(n.note % 12 for n in group))
        if len(pitches) < 2:
            continue

        best_match = ""
        best_root = 0
        best_score = 0

        for root in range(12):
            for name, template in CHORD_TEMPLATES.items():
                template_set = {(root + t) % 12 for t in template}
                pitch_set = set(pitches)
                overlap = len(template_set & pitch_set)
                total = len(template_set | pitch_set)
                score = overlap / total if total > 0 else 0.0

                if score > best_score:
                    best_score = score
                    best_match = name
                    best_root = root

        if best_score >= 0.5:
            chords.append(ChordEvent(
                root=best_root,
                chord_type=best_match,
                tick=group[0].start_tick,
                notes=[n.note for n in group],
            ))

    return chords


def velocity_curve(track: MIDITrack,
                    curve_type: str = "linear",
                    min_vel: int = 30,
                    max_vel: int = 127) -> MIDITrack:
    """Apply velocity curve mapping."""
    result = MIDITrack(name=track.name, ppq=track.ppq)

    for note in track.notes:
        normalized = note.velocity / 127.0

        if curve_type == "exponential":
            mapped = normalized ** 2
        elif curve_type == "logarithmic":
            mapped = math.sqrt(normalized)
        elif curve_type == "s_curve":
            mapped = 0.5 * (1.0 + math.tanh(3.0 * (normalized - 0.5)))
        elif curve_type == "phi":
            mapped = normalized ** (1.0 / PHI)
        else:  # linear
            mapped = normalized

        vel = int(min_vel + mapped * (max_vel - min_vel))
        vel = max(1, min(127, vel))

        result.notes.append(MIDINote(
            note=note.note,
            velocity=vel,
            start_tick=note.start_tick,
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))

    return result


def transpose(track: MIDITrack, semitones: int) -> MIDITrack:
    """Transpose all notes by semitones."""
    result = MIDITrack(name=track.name, ppq=track.ppq)
    for note in track.notes:
        new_note = max(0, min(127, note.note + semitones))
        result.notes.append(MIDINote(
            note=new_note,
            velocity=note.velocity,
            start_tick=note.start_tick,
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))
    return result


def reverse(track: MIDITrack) -> MIDITrack:
    """Reverse note order while keeping rhythm."""
    if not track.notes:
        return MIDITrack(name=track.name, ppq=track.ppq)

    result = MIDITrack(name=track.name, ppq=track.ppq)
    total = track.total_ticks
    for note in reversed(track.notes):
        new_start = total - (note.start_tick + note.duration_ticks)
        result.notes.append(MIDINote(
            note=note.note,
            velocity=note.velocity,
            start_tick=max(0, new_start),
            duration_ticks=note.duration_ticks,
            channel=note.channel,
        ))
    result.sort()
    return result


def create_arpeggio(notes: list[int], pattern: str = "up",
                     ppq: int = 480, step_ticks: int = 120,
                     n_steps: int = 16) -> MIDITrack:
    """Create an arpeggio pattern."""
    track = MIDITrack(name="Arpeggio", ppq=ppq)
    if not notes:
        return track

    if pattern == "down":
        cycle = list(reversed(notes))
    elif pattern == "updown":
        cycle = notes + list(reversed(notes[1:-1])) if len(notes) > 2 else notes
    elif pattern == "random":
        rng = random.Random(42)
        cycle = [rng.choice(notes) for _ in range(n_steps)]
    else:  # up
        cycle = list(notes)

    for i in range(n_steps):
        note = cycle[i % len(cycle)]
        track.notes.append(MIDINote(
            note=note,
            velocity=100,
            start_tick=i * step_ticks,
            duration_ticks=step_ticks - 10,
        ))

    return track


def main() -> None:
    print("MIDI Processor Engine")

    # Create test track
    track = MIDITrack(name="Test", ppq=480)
    notes = [60, 64, 67, 72]  # C major chord
    for i, n in enumerate(notes):
        track.notes.append(MIDINote(n, 100, i * 480, 480))

    # Quantize
    q = quantize(track, 240)
    print(f"  Quantized: {len(q.notes)} notes")

    # Humanize
    h = humanize(track, 15, 10)
    print(f"  Humanized: velocities = {[n.velocity for n in h.notes]}")

    # PHI humanize
    ph = phi_humanize(track)
    print(f"  PHI-humanized: {[n.velocity for n in ph.notes]}")

    # Chord detection
    chords = detect_chords(track, 480)
    print(f"  Chords: {[c.name for c in chords]}")

    # Velocity curve
    vc = velocity_curve(track, "phi")
    print(f"  PHI velocity: {[n.velocity for n in vc.notes]}")

    # Transpose
    t = transpose(track, 3)
    print(f"  Transposed +3: {[n.name for n in t.notes]}")

    # Arpeggio
    arp = create_arpeggio([60, 64, 67, 72], "updown", n_steps=16)
    print(f"  Arpeggio: {len(arp.notes)} steps")

    print("Done.")


if __name__ == "__main__":
    main()
