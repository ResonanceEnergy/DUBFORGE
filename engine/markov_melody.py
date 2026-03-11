"""
DUBFORGE — Markov Melody Generator Engine  (Session 171)

Generates melodies using Markov chains trained on scale
patterns, with PHI-weighted transition probabilities.
"""

import math
import os
import random
import struct
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000

# Scale definitions (semitone intervals from root)
SCALES: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "chromatic": list(range(12)),
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
}

# Note names
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class MelodyNote:
    """A single note in a melody."""
    midi_note: int
    duration_beats: float
    velocity: float = 0.8
    rest: bool = False

    @property
    def freq(self) -> float:
        return A4_432 * (2.0 ** ((self.midi_note - 69) / 12.0))

    @property
    def name(self) -> str:
        return f"{NOTE_NAMES[self.midi_note % 12]}{self.midi_note // 12 - 1}"


@dataclass
class Melody:
    """A complete melody."""
    notes: list[MelodyNote] = field(default_factory=list)
    key: str = "C"
    scale: str = "minor"
    bpm: float = 140.0

    @property
    def total_beats(self) -> float:
        return sum(n.duration_beats for n in self.notes)

    @property
    def duration_s(self) -> float:
        return self.total_beats * 60.0 / self.bpm

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "scale": self.scale,
            "bpm": self.bpm,
            "total_beats": self.total_beats,
            "duration_s": round(self.duration_s, 2),
            "notes": [
                {
                    "name": n.name,
                    "midi": n.midi_note,
                    "duration": n.duration_beats,
                    "velocity": n.velocity,
                    "rest": n.rest,
                }
                for n in self.notes
            ],
        }


class MarkovMelody:
    """Markov chain melody generator."""

    def __init__(self, key: str = "C", scale: str = "minor",
                  octave: int = 4, seed: int = 42):
        self.key = key
        self.scale = scale
        self.octave = octave
        self.rng = random.Random(seed)
        self._build_chain()

    def _note_to_midi(self, note_name: str, octave: int) -> int:
        """Convert note name + octave to MIDI number."""
        idx = NOTE_NAMES.index(note_name) if note_name in NOTE_NAMES else 0
        return idx + (octave + 1) * 12

    def _get_scale_notes(self, n_octaves: int = 2) -> list[int]:
        """Get MIDI notes for the scale."""
        root = self._note_to_midi(self.key, self.octave)
        intervals = SCALES.get(self.scale, SCALES["minor"])
        notes = []
        for oct in range(n_octaves):
            for interval in intervals:
                note = root + oct * 12 + interval
                if 0 <= note <= 127:
                    notes.append(note)
        return notes

    def _build_chain(self) -> None:
        """Build Markov transition matrix with PHI weighting."""
        self.scale_notes = self._get_scale_notes(2)
        n = len(self.scale_notes)
        if n == 0:
            return

        # Transition probabilities (PHI-weighted)
        self.transitions: dict[int, list[tuple[int, float]]] = {}

        for i, note in enumerate(self.scale_notes):
            probs: list[tuple[int, float]] = []
            for j, target in enumerate(self.scale_notes):
                interval = abs(j - i)
                if interval == 0:
                    weight = 0.1  # Repeat (low)
                elif interval == 1:
                    weight = PHI  # Step (highest = golden)
                elif interval == 2:
                    weight = 1.0 / PHI  # Skip
                elif interval == 3:
                    weight = 0.3
                elif interval == 4:
                    weight = 0.2  # 4th/5th
                else:
                    weight = 0.05

                probs.append((target, weight))

            # Normalize
            total = sum(w for _, w in probs)
            self.transitions[note] = [
                (t, w / total) for t, w in probs
            ]

    def generate(self, n_notes: int = 16,
                  rhythm_complexity: float = 0.5) -> Melody:
        """Generate a melody."""
        if not self.scale_notes:
            return Melody(key=self.key, scale=self.scale)

        notes: list[MelodyNote] = []
        current = self.rng.choice(self.scale_notes)

        # Rhythm patterns
        durations = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        dur_weights = [0.3, 0.3, 0.1, 0.2, 0.05, 0.05]

        for _ in range(n_notes):
            # Choose duration
            if rhythm_complexity < 0.3:
                dur = 0.5  # Simple
            elif rhythm_complexity > 0.7:
                dur = self.rng.choices(durations, dur_weights)[0]
            else:
                dur = self.rng.choice([0.25, 0.5, 1.0])

            # Rest probability
            is_rest = self.rng.random() < 0.1

            # Velocity (PHI variation)
            vel = 0.5 + self.rng.random() * 0.5
            # Accent on beat
            beat_pos = sum(n.duration_beats for n in notes) % 4
            if beat_pos < 0.01:
                vel = min(1.0, vel * PHI)

            notes.append(MelodyNote(
                midi_note=current,
                duration_beats=dur,
                velocity=round(vel, 2),
                rest=is_rest,
            ))

            # Transition to next note
            if current in self.transitions:
                targets, weights = zip(*self.transitions[current])
                current = self.rng.choices(list(targets),
                                            list(weights))[0]
            else:
                current = self.rng.choice(self.scale_notes)

        return Melody(
            notes=notes,
            key=self.key,
            scale=self.scale,
            bpm=140.0,
        )


def render_melody(melody: Melody,
                   sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render melody to audio signal."""
    total_s = melody.duration_s
    n = int(total_s * sample_rate)
    signal = [0.0] * n
    dt = 1.0 / sample_rate

    pos_s = 0.0
    for note in melody.notes:
        dur_s = note.duration_beats * 60.0 / melody.bpm
        start_sample = int(pos_s * sample_rate)
        end_sample = min(int((pos_s + dur_s) * sample_rate), n)

        if not note.rest:
            freq = note.freq
            for i in range(start_sample, end_sample):
                t = (i - start_sample) * dt
                # Simple envelope
                env = 1.0
                attack = 0.005
                release = min(0.05, dur_s * 0.2)
                if t < attack:
                    env = t / attack
                elif t > dur_s - release:
                    env = (dur_s - t) / release

                signal[i] = (
                    note.velocity * env *
                    (math.sin(2 * math.pi * freq * t) * 0.7 +
                     math.sin(2 * math.pi * freq * 2 * t) * 0.2 +
                     math.sin(2 * math.pi * freq * 3 * t) * 0.1)
                )

        pos_s += dur_s

    return signal


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


def main() -> None:
    print("Markov Melody Generator Engine")
    for scale_name in ["minor", "pentatonic", "dorian", "blues"]:
        gen = MarkovMelody("C", scale_name, 4, 42)
        melody = gen.generate(16, 0.5)
        print(f"  {scale_name}: {melody.total_beats} beats, "
              f"{len(melody.notes)} notes, {melody.duration_s:.1f}s")
        note_names = [n.name for n in melody.notes if not n.rest]
        print(f"    Notes: {' '.join(note_names[:8])}...")

    # Render one
    gen = MarkovMelody("A", "minor", 4, 42)
    melody = gen.generate(32, 0.6)
    sig = render_melody(melody)
    path = _write_wav("output/midi/markov_melody.wav", sig)
    print(f"  Rendered: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
