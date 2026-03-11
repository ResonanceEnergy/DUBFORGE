"""
DUBFORGE — Tuning System  (Session 201)

Tuning and temperament engine: 432 Hz base,
equal temperament, just intonation, Pythagorean,
PHI-based tuning, micro-tuning support.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
A4_432 = 432.0


@dataclass
class Note:
    """A musical note with frequency."""
    name: str
    octave: int
    frequency: float
    midi_number: int = 0
    cents_offset: float = 0.0

    def to_dict(self) -> dict:
        return {
            "note": f"{self.name}{self.octave}",
            "freq": round(self.frequency, 3),
            "midi": self.midi_number,
            "cents": round(self.cents_offset, 1),
        }


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

ENHARMONIC = {
    "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#",
    "Ab": "G#", "Bb": "A#", "Cb": "B",
    "B#": "C", "E#": "F",
}


class TuningSystem:
    """Musical tuning and temperament engine."""

    def __init__(self, reference_freq: float = A4_432,
                 reference_note: str = "A",
                 reference_octave: int = 4):
        self.reference_freq = reference_freq
        self.reference_note = reference_note
        self.reference_octave = reference_octave
        self.reference_midi = 69  # A4

    def _normalize_note(self, name: str) -> str:
        """Normalize enharmonic spellings."""
        return ENHARMONIC.get(name, name)

    def _note_to_semitone(self, name: str) -> int:
        """Get semitone index (C=0)."""
        name = self._normalize_note(name)
        if name in NOTE_NAMES:
            return NOTE_NAMES.index(name)
        return 0

    def _semitones_from_ref(self, name: str, octave: int) -> int:
        """Semitones from reference note."""
        ref_semi = self._note_to_semitone(self.reference_note)
        note_semi = self._note_to_semitone(name)
        return (note_semi - ref_semi) + (octave - self.reference_octave) * 12

    # --- Equal Temperament (12-TET) ---

    def equal_temperament(self, name: str, octave: int) -> float:
        """Standard 12-TET frequency."""
        semitones = self._semitones_from_ref(name, octave)
        return self.reference_freq * (2 ** (semitones / 12))

    def equal_temperament_midi(self, midi_number: int) -> float:
        """Frequency from MIDI number."""
        return self.reference_freq * (2 ** ((midi_number - self.reference_midi) / 12))

    # --- Just Intonation ---

    JUST_RATIOS = {
        0: 1/1,      # Unison
        1: 16/15,    # Minor second
        2: 9/8,      # Major second
        3: 6/5,      # Minor third
        4: 5/4,      # Major third
        5: 4/3,      # Perfect fourth
        6: 45/32,    # Tritone
        7: 3/2,      # Perfect fifth
        8: 8/5,      # Minor sixth
        9: 5/3,      # Major sixth
        10: 9/5,     # Minor seventh
        11: 15/8,    # Major seventh
    }

    def just_intonation(self, name: str, octave: int,
                        root: str = "C") -> float:
        """Just intonation frequency from root."""
        root_freq = self.equal_temperament(root, octave)
        root_semi = self._note_to_semitone(root)
        note_semi = self._note_to_semitone(name)
        interval = (note_semi - root_semi) % 12

        ratio = self.JUST_RATIOS.get(interval, 1.0)
        # Adjust octave
        octave_diff = (octave - octave) + (
            1 if note_semi < root_semi and octave == octave else 0
        )

        freq = root_freq * ratio * (2 ** octave_diff)

        # Correct for octave offset
        semitones_full = self._semitones_from_ref(name, octave)
        ref_semitones = self._semitones_from_ref(root, octave)
        if semitones_full < ref_semitones:
            freq *= 2

        return freq

    # --- Pythagorean ---

    PYTH_RATIOS = {
        0: 1/1,
        1: 256/243,
        2: 9/8,
        3: 32/27,
        4: 81/64,
        5: 4/3,
        6: 729/512,
        7: 3/2,
        8: 128/81,
        9: 27/16,
        10: 16/9,
        11: 243/128,
    }

    def pythagorean(self, name: str, octave: int,
                    root: str = "C") -> float:
        """Pythagorean tuning."""
        root_freq = self.equal_temperament(root, octave)
        root_semi = self._note_to_semitone(root)
        note_semi = self._note_to_semitone(name)
        interval = (note_semi - root_semi) % 12

        ratio = self.PYTH_RATIOS.get(interval, 1.0)
        return root_freq * ratio

    # --- PHI Tuning ---

    def phi_tuning(self, name: str, octave: int) -> float:
        """PHI-based tuning: intervals derived from golden ratio."""
        semitones = self._semitones_from_ref(name, octave)
        # Use PHI as the ratio base instead of 2
        # One "octave" = PHI ratio
        return self.reference_freq * (PHI ** (semitones / 12))

    def phi_harmonic_series(self, fundamental: float,
                            n_harmonics: int = 8) -> list[float]:
        """Generate PHI-spaced harmonic series."""
        harmonics: list[float] = []
        for i in range(n_harmonics):
            freq = fundamental * (PHI ** i)
            harmonics.append(round(freq, 3))
        return harmonics

    # --- Micro-tuning ---

    def detune_cents(self, freq: float, cents: float) -> float:
        """Detune frequency by cents."""
        return freq * (2 ** (cents / 1200))

    def cents_between(self, freq_a: float, freq_b: float) -> float:
        """Calculate cents difference between frequencies."""
        if freq_a <= 0 or freq_b <= 0:
            return 0.0
        return 1200 * math.log2(freq_b / freq_a)

    # --- Scale Generation ---

    def generate_scale(self, root: str, octave: int,
                       intervals: list[int] = None,
                       tuning: str = "equal") -> list[Note]:
        """Generate a scale."""
        if intervals is None:
            intervals = [0, 2, 4, 5, 7, 9, 11]  # major

        notes: list[Note] = []
        for interval in intervals:
            note_idx = (self._note_to_semitone(root) + interval) % 12
            note_name = NOTE_NAMES[note_idx]
            note_octave = octave + (
                (self._note_to_semitone(root) + interval) // 12
            )

            if tuning == "equal":
                freq = self.equal_temperament(note_name, note_octave)
            elif tuning == "just":
                freq = self.just_intonation(note_name, note_octave, root)
            elif tuning == "pythagorean":
                freq = self.pythagorean(note_name, note_octave, root)
            elif tuning == "phi":
                freq = self.phi_tuning(note_name, note_octave)
            else:
                freq = self.equal_temperament(note_name, note_octave)

            equal_freq = self.equal_temperament(note_name, note_octave)
            cents_off = self.cents_between(equal_freq, freq)

            notes.append(Note(
                name=note_name,
                octave=note_octave,
                frequency=freq,
                midi_number=self.reference_midi + self._semitones_from_ref(
                    note_name, note_octave
                ),
                cents_offset=cents_off,
            ))

        return notes

    def generate_chromatic(self, octave: int,
                           tuning: str = "equal") -> list[Note]:
        """Generate full chromatic scale."""
        return self.generate_scale(
            "C", octave,
            list(range(12)),
            tuning
        )

    def frequency_to_note(self, freq: float) -> Note:
        """Find nearest note for a frequency."""
        if freq <= 0:
            return Note("?", 0, 0)

        semitones = 12 * math.log2(freq / self.reference_freq)
        midi = round(self.reference_midi + semitones)
        note_idx = (midi - 12) % 12  # C=0
        octave = (midi - 12) // 12

        name = NOTE_NAMES[note_idx]
        exact_freq = self.equal_temperament_midi(midi)
        cents = self.cents_between(exact_freq, freq)

        return Note(
            name=name, octave=octave,
            frequency=freq, midi_number=midi,
            cents_offset=cents,
        )

    def get_tuning_table(self, root: str = "A",
                         octave: int = 4) -> dict:
        """Get comparison table of all tunings."""
        result: dict[str, dict] = {}
        for tuning in ["equal", "just", "pythagorean", "phi"]:
            scale = self.generate_chromatic(octave, tuning)
            result[tuning] = {
                n.name: round(n.frequency, 2) for n in scale
            }
        return result


def main() -> None:
    print("Tuning System")

    tuner = TuningSystem(A4_432)

    # A4 in different tunings
    a4_eq = tuner.equal_temperament("A", 4)
    a4_phi = tuner.phi_tuning("A", 4)
    print(f"  A4 Equal: {a4_eq:.3f} Hz")
    print(f"  A4 PHI:   {a4_phi:.3f} Hz")

    # Generate scales
    major = tuner.generate_scale("C", 4, tuning="equal")
    print("\n  C Major (Equal):")
    for n in major:
        print(f"    {n.name}{n.octave}: {n.frequency:.2f} Hz")

    # PHI harmonics
    harmonics = tuner.phi_harmonic_series(432.0, 5)
    print(f"\n  PHI harmonics from 432: {harmonics}")

    # Note detection
    note = tuner.frequency_to_note(440.0)
    print(f"\n  440 Hz → {note.name}{note.octave} "
          f"({note.cents_offset:+.1f} cents)")

    print("Done.")


if __name__ == "__main__":
    main()
