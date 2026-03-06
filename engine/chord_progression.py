"""
DUBFORGE Engine — Chord Progression Engine

Generates chord progressions using music theory, phi-ratio voicings,
and Fibonacci-timed harmonic rhythm. Includes dubstep/bass music presets
inspired by Subtronics' emotive vs weapon approach.

Supports:
    - Roman numeral analysis (I, ii, iii, IV, V, vi, viio)
    - Major, minor, diminished, augmented, sus, 7th, 9th chords
    - Key transposition with 432 Hz / 440 Hz tuning
    - Phi-ratio voicing spread & Fibonacci harmonic rhythm
    - EDM/dubstep-specific progression presets
    - MIDI note number output + frequency output
    - JSON export

Outputs:
    output/analysis/chord_progressions_<preset>.json
"""

import json
import math
import numpy as np
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# --- Constants -----------------------------------------------------------

PHI = 1.6180339887498948482
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
A4_432 = 432.0
A4_440 = 440.0

# Chromatic note names
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Semitone intervals for scale degrees in major scale
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
# Natural minor (Aeolian)
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
# Harmonic minor
HARMONIC_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 11]
# Phrygian dominant (common in dubstep/metal)
PHRYGIAN_DOMINANT_SCALE = [0, 1, 4, 5, 7, 8, 10]
# Dorian (common in EDM)
DORIAN_SCALE = [0, 2, 3, 5, 7, 9, 10]

SCALES = {
    "major": MAJOR_SCALE,
    "minor": MINOR_SCALE,
    "harmonic_minor": HARMONIC_MINOR_SCALE,
    "phrygian_dominant": PHRYGIAN_DOMINANT_SCALE,
    "dorian": DORIAN_SCALE,
}


# --- Chord Quality Definitions -------------------------------------------

# Intervals from root for each chord quality (in semitones)
CHORD_QUALITIES = {
    "major":       [0, 4, 7],
    "minor":       [0, 3, 7],
    "diminished":  [0, 3, 6],
    "augmented":   [0, 4, 8],
    "sus2":        [0, 2, 7],
    "sus4":        [0, 5, 7],
    "power":       [0, 7],           # Power chord (no 3rd)
    "maj7":        [0, 4, 7, 11],
    "min7":        [0, 3, 7, 10],
    "dom7":        [0, 4, 7, 10],
    "dim7":        [0, 3, 6, 9],
    "min7b5":      [0, 3, 6, 10],    # Half-diminished
    "add9":        [0, 4, 7, 14],
    "madd9":       [0, 3, 7, 14],
    "maj9":        [0, 4, 7, 11, 14],
    "min9":        [0, 3, 7, 10, 14],
    "dom9":        [0, 4, 7, 10, 14],
    "min11":       [0, 3, 7, 10, 14, 17],
    "7sus4":       [0, 5, 7, 10],
    # Dubstep specials
    "5th_stack":   [0, 7, 14],       # Stacked 5ths — hollow aggressive
    "tritone":     [0, 6],           # Pure tension
    "phi_triad":   [0, 5, 8],        # ~phi-ratio intervals (5 & 8 are Fibonacci)
}

# Roman numeral → scale degree (1-indexed)
ROMAN_NUMERALS = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
    "bII": 2, "bIII": 3, "bVI": 6, "bVII": 7,
    "bii": 2, "biii": 3, "bvi": 6, "bvii": 7,
}

# Default chord quality for diatonic degrees in major key
MAJOR_DIATONIC_QUALITIES = {
    1: "major", 2: "minor", 3: "minor", 4: "major",
    5: "major", 6: "minor", 7: "diminished",
}

# Default chord quality for diatonic degrees in minor key
MINOR_DIATONIC_QUALITIES = {
    1: "minor", 2: "diminished", 3: "major", 4: "minor",
    5: "minor", 6: "major", 7: "major",
}


# --- Data Classes ---------------------------------------------------------

@dataclass
class Note:
    """Single MIDI note with frequency."""
    name: str
    midi: int
    frequency: float
    octave: int


@dataclass
class Chord:
    """A chord with root, quality, voicing, and note data."""
    symbol: str              # e.g., "Am", "F#m7", "Bb"
    roman: str               # e.g., "vi", "IV", "bVII"
    root_name: str           # e.g., "A"
    quality: str             # e.g., "minor"
    notes: list              # list of Note dicts
    midi_notes: list         # list of MIDI numbers
    frequencies: list        # list of Hz values
    duration_beats: float = 4.0
    inversion: int = 0       # 0=root, 1=first, 2=second


@dataclass
class ChordProgression:
    """Complete chord progression with metadata."""
    name: str
    key: str                 # e.g., "Am", "F"
    scale_type: str          # e.g., "minor", "major"
    bpm: int = 150           # Dubstep standard
    tuning_hz: float = 440.0
    time_signature: str = "4/4"
    total_bars: int = 4
    chords: list = field(default_factory=list)
    harmonic_rhythm: list = field(default_factory=list)  # beats per chord
    phi_voicing: bool = False
    tags: list = field(default_factory=list)
    notes: str = ""


# --- Core Functions -------------------------------------------------------

def note_to_midi(note_name: str, octave: int) -> int:
    """Convert note name + octave to MIDI number. C4 = 60."""
    idx = NOTE_NAMES.index(note_name.replace("b", "#").replace("Db", "C#")
                           .replace("Eb", "D#").replace("Gb", "F#")
                           .replace("Ab", "G#").replace("Bb", "A#"))
    return 12 * (octave + 1) + idx


def midi_to_note(midi: int) -> tuple[str, int]:
    """Convert MIDI number to (note_name, octave)."""
    octave = (midi // 12) - 1
    note_idx = midi % 12
    return NOTE_NAMES[note_idx], octave


def midi_to_freq(midi: int, a4: float = A4_440) -> float:
    """Convert MIDI note to frequency. Supports 432 Hz tuning."""
    return a4 * (2 ** ((midi - 69) / 12))


def freq_to_nearest_midi(freq: float, a4: float = A4_440) -> int:
    """Find nearest MIDI note for a given frequency."""
    if freq <= 0:
        return 0
    return round(69 + 12 * math.log2(freq / a4))


def get_scale_notes(root_name: str, scale_type: str = "minor") -> list[int]:
    """Get semitone offsets for a scale rooted on root_name."""
    root_idx = NOTE_NAMES.index(root_name)
    intervals = SCALES.get(scale_type, MINOR_SCALE)
    return [(root_idx + i) % 12 for i in intervals]


def build_chord(root_midi: int, quality: str = "minor",
                inversion: int = 0, a4: float = A4_440) -> list[Note]:
    """Build a chord from a root MIDI note and quality."""
    intervals = CHORD_QUALITIES.get(quality, CHORD_QUALITIES["minor"])
    midi_notes = [root_midi + i for i in intervals]

    # Apply inversion — move lowest N notes up an octave
    for i in range(min(inversion, len(midi_notes) - 1)):
        midi_notes[i] += 12

    midi_notes.sort()

    notes = []
    for m in midi_notes:
        name, octave = midi_to_note(m)
        notes.append(Note(
            name=name,
            midi=m,
            frequency=round(midi_to_freq(m, a4), 2),
            octave=octave,
        ))
    return notes


def phi_voice_spread(chord_notes: list[Note], spread: float = PHI) -> list[Note]:
    """
    Apply phi-ratio voicing spread to a chord.
    Redistributes chord tones across octaves using phi spacing.
    The lowest note stays; upper notes are placed at phi-ratio
    intervals above the bass.
    """
    if len(chord_notes) < 2:
        return chord_notes

    bass = chord_notes[0]
    voiced = [bass]
    for i, note in enumerate(chord_notes[1:], 1):
        # Spread each upper voice by phi^i semitones from bass
        phi_offset = round(spread * i)
        new_midi = bass.midi + (note.midi - chord_notes[0].midi) + phi_offset
        name, octave = midi_to_note(new_midi)
        voiced.append(Note(
            name=name,
            midi=new_midi,
            frequency=round(midi_to_freq(new_midi, A4_440), 2),
            octave=octave,
        ))
    return voiced


def fibonacci_harmonic_rhythm(total_beats: int = 16) -> list[float]:
    """
    Generate a harmonic rhythm (chord durations) using Fibonacci numbers.
    Distributes beats across chords in Fibonacci proportions.
    """
    # Use small Fibonacci numbers that sum to total_beats
    fib_options = [f for f in FIBONACCI if f > 0 and f <= total_beats]

    # Find a combination that sums to total_beats
    # Simple greedy approach using Fibonacci proportions
    rhythm = []
    remaining = total_beats
    fib_idx = min(5, len(fib_options) - 1)  # Start from fib[5] = 8

    while remaining > 0 and fib_idx >= 0:
        val = fib_options[fib_idx]
        if val <= remaining:
            rhythm.append(float(val))
            remaining -= val
        fib_idx -= 1

    # If remaining, fill with 1s
    while remaining > 0:
        rhythm.append(1.0)
        remaining -= 1

    return rhythm


def resolve_roman(roman: str, key_root: str, scale_type: str = "minor",
                  octave: int = 3, quality_override: str = None) -> tuple[int, str]:
    """
    Resolve a Roman numeral chord symbol to a MIDI root note and quality.

    Resolves degrees from the key's OWN scale (pop/EDM convention).
    In Am minor: VI = F (natural 6th), III = C (natural 3rd), VII = G.
    Accidentals (b/#) chromatically alter FROM the current scale.
    Uppercase = major quality, lowercase = minor quality (default).

    Returns: (root_midi, quality)
    """
    # Determine if flat degree
    flat = roman.startswith("b") or roman.startswith("♭")
    sharp = roman.startswith("#")
    clean_roman = roman.lstrip("b♭#")

    # Determine quality from case
    is_upper = clean_roman[0].isupper() if clean_roman else True

    # Parse any quality suffix
    suffix = ""
    base_numeral = clean_roman
    for q in ["maj9", "min9", "dom9", "maj7", "min7", "dom7", "dim7",
              "min7b5", "7sus4", "add9", "madd9", "min11",
              "sus2", "sus4", "dim", "aug", "7", "9", "5"]:
        if clean_roman.lower().endswith(q):
            suffix = q
            base_numeral = clean_roman[:-len(q)]
            break

    # Get scale degree
    degree = ROMAN_NUMERALS.get(base_numeral,
                                ROMAN_NUMERALS.get(base_numeral.upper(), 1))

    # Resolve from the KEY'S OWN scale (pop/EDM convention)
    scale = SCALES.get(scale_type, MINOR_SCALE)
    root_idx = NOTE_NAMES.index(key_root)
    deg_semitone = scale[degree - 1] if degree <= len(scale) else 0

    # Accidentals chromatically alter from the scale degree
    if flat:
        deg_semitone -= 1
    elif sharp:
        deg_semitone += 1

    root_midi = 12 * (octave + 1) + (root_idx + deg_semitone) % 12

    # Determine quality
    if quality_override:
        quality = quality_override
    elif suffix:
        suffix_map = {
            "7": "dom7", "9": "dom9", "5": "power",
            "dim": "diminished", "aug": "augmented",
        }
        quality = suffix_map.get(suffix, suffix)
    else:
        # Uppercase = major, lowercase = minor
        # Special: viio = diminished
        if not is_upper and degree == 7:
            quality = "diminished"
        elif degree == 2 and not is_upper and scale_type in ("minor", "harmonic_minor"):
            quality = "diminished"  # iio in minor
        elif is_upper:
            quality = "major"
        else:
            quality = "minor"

    return root_midi, quality


def build_progression(name: str, key: str, scale_type: str,
                      roman_sequence: list[str],
                      bpm: int = 150, tuning_hz: float = 440.0,
                      beats_per_chord: list[float] = None,
                      phi_voicing: bool = False,
                      inversions: list[int] = None,
                      qualities: list[str] = None,
                      tags: list[str] = None,
                      notes_text: str = "",
                      octave: int = 3) -> ChordProgression:
    """
    Build a complete chord progression from Roman numeral symbols.

    Args:
        name: Preset name
        key: Root note name (e.g., "A", "F#")
        scale_type: Scale type (e.g., "minor", "major")
        roman_sequence: List of Roman numerals (e.g., ["i", "VI", "III", "VII"])
        bpm: Tempo in BPM
        tuning_hz: A4 reference (432 or 440)
        beats_per_chord: Duration of each chord in beats
        phi_voicing: Apply phi-ratio voicing spread
        inversions: List of inversion numbers per chord
        qualities: List of quality overrides per chord (None = auto)
        tags: Descriptive tags
        notes_text: Free-form notes/description
        octave: Base octave for chord roots
    """
    n_chords = len(roman_sequence)

    if beats_per_chord is None:
        beats_per_chord = [4.0] * n_chords
    if inversions is None:
        inversions = [0] * n_chords
    if qualities is None:
        qualities = [None] * n_chords
    if tags is None:
        tags = []

    chords = []
    for i, roman in enumerate(roman_sequence):
        root_midi, quality = resolve_roman(
            roman, key, scale_type, octave,
            quality_override=qualities[i] if i < len(qualities) else None,
        )

        chord_notes = build_chord(
            root_midi, quality,
            inversion=inversions[i] if i < len(inversions) else 0,
            a4=tuning_hz,
        )

        if phi_voicing:
            chord_notes = phi_voice_spread(chord_notes)

        root_name, _ = midi_to_note(root_midi)
        quality_symbol = _quality_to_symbol(quality)

        chords.append(Chord(
            symbol=f"{root_name}{quality_symbol}",
            roman=roman,
            root_name=root_name,
            quality=quality,
            notes=[asdict(n) for n in chord_notes],
            midi_notes=[n.midi for n in chord_notes],
            frequencies=[n.frequency for n in chord_notes],
            duration_beats=beats_per_chord[i] if i < len(beats_per_chord) else 4.0,
            inversion=inversions[i] if i < len(inversions) else 0,
        ))

    total_beats = sum(c.duration_beats for c in chords)
    total_bars = int(total_beats / 4)

    return ChordProgression(
        name=name,
        key=f"{key}{'m' if scale_type != 'major' else ''}",
        scale_type=scale_type,
        bpm=bpm,
        tuning_hz=tuning_hz,
        total_bars=max(total_bars, 1),
        chords=[asdict(c) for c in chords],
        harmonic_rhythm=beats_per_chord,
        phi_voicing=phi_voicing,
        tags=tags,
        notes=notes_text,
    )


def _quality_to_symbol(quality: str) -> str:
    """Convert quality name to chord symbol suffix."""
    return {
        "major": "",
        "minor": "m",
        "diminished": "dim",
        "augmented": "aug",
        "sus2": "sus2",
        "sus4": "sus4",
        "power": "5",
        "maj7": "maj7",
        "min7": "m7",
        "dom7": "7",
        "dim7": "dim7",
        "min7b5": "m7b5",
        "add9": "add9",
        "madd9": "madd9",
        "maj9": "maj9",
        "min9": "m9",
        "dom9": "9",
        "min11": "m11",
        "7sus4": "7sus4",
        "5th_stack": "5stack",
        "tritone": "tt",
        "phi_triad": "φ",
    }.get(quality, quality)


# =========================================================================
#  PRESETS — Dubstep / Bass Music Progressions
# =========================================================================

def preset_weapon_dark() -> ChordProgression:
    """
    WEAPON_DARK: The classic dark dubstep progression.
    i - bVI - bVII - i  (Am: Am - F - G - Am)
    Heavy, aggressive, forward momentum. Used in Subtronics weapon drops.
    """
    return build_progression(
        name="WEAPON_DARK",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "VI", "VII", "i"],
        bpm=150,
        beats_per_chord=[4.0, 4.0, 4.0, 4.0],
        tags=["weapon", "dark", "aggressive", "drop"],
        notes_text="Classic dark dubstep. bVI-bVII creates the 'epic' lift back to i. "
                   "Subtronics uses this in weapon-style drops. Root position for maximum weight.",
    )


def preset_emotive_rise() -> ChordProgression:
    """
    EMOTIVE_RISE: Melodic dubstep/future bass with emotional pull.
    i - VI - III - VII  (Am: Am - F - C - G)
    The dubstep version of I-V-vi-IV, reversed for minor key.
    """
    return build_progression(
        name="EMOTIVE_RISE",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "VI", "III", "VII"],
        bpm=150,
        beats_per_chord=[4.0, 4.0, 4.0, 4.0],
        phi_voicing=True,
        tags=["emotive", "melodic", "rise", "future_bass"],
        notes_text="Melodic dubstep staple. III-VII creates uplift. "
                   "Phi voicing spreads chords wide for cinematic feel. "
                   "Think Subtronics 'Spacetime' emotive sections.",
    )


def preset_fractal_spiral() -> ChordProgression:
    """
    FRACTAL_SPIRAL: Phi-doctrine progression using Fibonacci harmonic rhythm.
    i - iv - bVII - III - bVI - i
    6 chords with Fibonacci-proportioned durations (3+5+2+3+2+1 = 16 beats).
    """
    return build_progression(
        name="FRACTAL_SPIRAL",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "iv", "VII", "III", "VI", "i"],
        bpm=150,
        beats_per_chord=[3.0, 5.0, 2.0, 3.0, 2.0, 1.0],  # Fibonacci rhythm!
        phi_voicing=True,
        tags=["fractal", "phi", "fibonacci", "spiral", "doctrine"],
        notes_text="DUBFORGE doctrine progression. 6 chords in Fibonacci-timed rhythm "
                   "(3+5+2+3+2+1=16 beats). Phi voicing creates fractal self-similar "
                   "harmonic structure. Spiral through the circle of minor relationships.",
    )


def preset_andalusian_weapon() -> ChordProgression:
    """
    ANDALUSIAN_WEAPON: Phrygian-flavored descending bass line.
    i - bVII - bVI - V  (Am: Am - G - F - E)
    Andalusian cadence — dark, exotic, heavy. Perfect for riddim/dubstep.
    """
    return build_progression(
        name="ANDALUSIAN_WEAPON",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "VII", "VI", "V"],
        bpm=150,
        beats_per_chord=[4.0, 4.0, 4.0, 4.0],
        qualities=[None, "major", "major", "major"],  # V is major in harmonic minor
        tags=["andalusian", "weapon", "phrygian", "descending", "dark"],
        notes_text="Andalusian cadence adapted for dubstep. Descending bass line "
                   "(A-G-F-E) creates relentless downward pull. The major V chord "
                   "provides the leading tone tension. Used in riddim and heavy drops.",
    )


def preset_golden_ratio() -> ChordProgression:
    """
    GOLDEN_RATIO: Pure phi-doctrine chord choices.
    Uses Fibonacci scale degrees: 1, 2, 3, 5, 8(=1).
    Progression through degrees 1-3-5-8(1)-3-1 with phi timing.
    """
    return build_progression(
        name="GOLDEN_RATIO",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "III", "v", "i", "III"],
        bpm=150,
        beats_per_chord=[5.0, 3.0, 3.0, 3.0, 2.0],  # Fibonacci: 5+3+3+3+2=16
        phi_voicing=True,
        tags=["phi", "golden_ratio", "fibonacci", "doctrine", "sacred"],
        notes_text="Pure Fibonacci degree selection (1,3,5 = Fibonacci numbers). "
                   "Timing in Fibonacci ratios. Phi-voiced for maximum fractal coherence. "
                   "Dan Winter's 'embedding' principle in harmonic form.",
    )


def preset_tesseract() -> ChordProgression:
    """
    TESSERACT: Named after Subtronics' album. 4D harmonic folding.
    i - bVI - iv - bVII - V - i
    6 chords, 8-bar form, descending then resolving upward.
    """
    return build_progression(
        name="TESSERACT",
        key="D",
        scale_type="minor",
        roman_sequence=["i", "VI", "iv", "VII", "V", "i"],
        bpm=150,
        beats_per_chord=[8.0, 4.0, 4.0, 4.0, 4.0, 8.0],
        inversions=[0, 1, 0, 0, 0, 0],
        tags=["tesseract", "subtronics", "cinematic", "long_form"],
        notes_text="8-bar cinematic progression. Named for Subtronics' TESSERACT album. "
                   "Opens and closes on i with extended 8-beat holds. "
                   "bVI in first inversion for smooth bass motion. "
                   "V creates harmonic-minor tension before final resolution.",
        qualities=[None, None, None, None, "major", None],
    )


def preset_wook_trip() -> ChordProgression:
    """
    WOOK_TRIP: Psychedelic, dissonant, unpredictable.
    Uses add9, sus4, tritone — deliberately unstable voicings.
    """
    return build_progression(
        name="WOOK_TRIP",
        key="E",
        scale_type="minor",
        roman_sequence=["i", "bII", "iv", "VII", "i"],
        bpm=140,
        beats_per_chord=[5.0, 3.0, 3.0, 3.0, 2.0],
        qualities=["madd9", "major", "7sus4", "dom9", "sus2"],
        phi_voicing=True,
        tags=["wook", "psychedelic", "weird", "experimental"],
        notes_text="Psychedelic wook bass trip. madd9 and 7sus4 voicings create "
                   "an unsettled, floating quality. bII (Phrygian color) adds darkness. "
                   "Fibonacci timing keeps it organically uneven.",
    )


def preset_fibonacci_drop() -> ChordProgression:
    """
    FIBONACCI_DROP: 8-chord Fibonacci-structured drop.
    13 Fibonacci notes mapped across 8 bars.
    """
    return build_progression(
        name="FIBONACCI_DROP",
        key="F",
        scale_type="minor",
        roman_sequence=["i", "i", "VI", "VII", "iv", "VI", "VII", "i"],
        bpm=150,
        beats_per_chord=[1.0, 2.0, 3.0, 2.0, 3.0, 2.0, 2.0, 1.0],  # Fibonacci palindrome
        tags=["fibonacci", "drop", "weapon", "palindrome"],
        notes_text="Fibonacci palindrome rhythm (1+2+3+2+3+2+2+1 = 16 beats). "
                   "Mirror structure creates tension-release symmetry. "
                   "Doubled i bookends for maximum impact on drop hit and resolve.",
    )


def preset_stepwise_grind() -> ChordProgression:
    """
    STEPWISE_GRIND: Chromatic stepwise bassline for riddim/tearout.
    Uses power chords for maximum aggression.
    """
    return build_progression(
        name="STEPWISE_GRIND",
        key="E",
        scale_type="minor",
        roman_sequence=["i", "bII", "i", "VII"],
        bpm=150,
        beats_per_chord=[4.0, 2.0, 6.0, 4.0],
        qualities=["power", "power", "power", "power"],
        tags=["riddim", "tearout", "aggressive", "chromatic", "power_chords"],
        notes_text="Riddim/tearout progression. Power chords only — no 3rd, "
                   "pure aggression. bII creates half-step crunch. "
                   "Extended i (6 beats) for bass design showcase space.",
    )


def preset_432_sacred() -> ChordProgression:
    """
    432_SACRED: A=432 Hz tuned progression for coherent resonance.
    Uses the 'healing frequency' tuning per Dan Winter's doctrine.
    """
    return build_progression(
        name="432_SACRED",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "iv", "VI", "VII", "III", "i"],
        bpm=144,  # Fibonacci BPM!
        tuning_hz=432.0,
        beats_per_chord=[3.0, 2.0, 3.0, 3.0, 2.0, 3.0],
        phi_voicing=True,
        tags=["432hz", "sacred", "tuning", "coherence", "doctrine", "healing"],
        notes_text="432 Hz tuned progression at 144 BPM (Fibonacci!). "
                   "All frequencies derived from A=432 Hz for maximum "
                   "bio-coherent resonance per Dan Winter's research. "
                   "Phi voicing creates self-similar harmonic nesting.",
    )


def preset_antifractal() -> ChordProgression:
    """
    ANTIFRACTAL: Deliberately breaks phi patterns — chaotic energy.
    Non-Fibonacci rhythms, tritone relationships, augmented chords.
    Named for Subtronics' Antifractals album — VIP chaos energy.
    """
    return build_progression(
        name="ANTIFRACTAL",
        key="A",
        scale_type="minor",
        roman_sequence=["i", "bV", "bII", "VI", "IV", "i"],
        bpm=155,
        beats_per_chord=[3.5, 2.5, 3.0, 2.0, 2.5, 2.5],  # Deliberately non-Fibonacci
        qualities=["minor", "augmented", "major", "augmented", "major", "power"],
        tags=["antifractal", "chaos", "vip", "tritone", "augmented"],
        notes_text="ANTIFRACTAL: deliberate violation of phi doctrine. "
                   "Tritone root motion (bV), augmented chords, non-Fibonacci rhythm. "
                   "Chaos as compositional principle. Named for Subtronics' "
                   "Antifractals album — the VIP destroys the original's structure.",
    )


# --- All Presets ----------------------------------------------------------

ALL_PRESETS = {
    "WEAPON_DARK": preset_weapon_dark,
    "EMOTIVE_RISE": preset_emotive_rise,
    "FRACTAL_SPIRAL": preset_fractal_spiral,
    "ANDALUSIAN_WEAPON": preset_andalusian_weapon,
    "GOLDEN_RATIO": preset_golden_ratio,
    "TESSERACT": preset_tesseract,
    "WOOK_TRIP": preset_wook_trip,
    "FIBONACCI_DROP": preset_fibonacci_drop,
    "STEPWISE_GRIND": preset_stepwise_grind,
    "432_SACRED": preset_432_sacred,
    "ANTIFRACTAL": preset_antifractal,
}


# --- Utility: Analyze interval relationships ------------------------------

def analyze_intervals(prog: ChordProgression) -> dict:
    """Analyze the intervallic relationships in a progression."""
    chords = prog.chords
    if not chords:
        return {}

    root_midis = [c["midi_notes"][0] for c in chords if c["midi_notes"]]
    intervals = []
    for i in range(1, len(root_midis)):
        interval = (root_midis[i] - root_midis[i - 1]) % 12
        intervals.append(interval)

    # Check for phi/Fibonacci presence
    fib_set = set(FIBONACCI[:10])
    fib_intervals = [iv for iv in intervals if iv in fib_set]
    fib_ratio = len(fib_intervals) / max(len(intervals), 1)

    return {
        "root_motion_semitones": intervals,
        "fibonacci_interval_ratio": round(fib_ratio, 3),
        "contains_tritone": 6 in intervals,
        "total_root_movement": sum(intervals),
        "avg_interval": round(sum(intervals) / max(len(intervals), 1), 2),
    }


def progression_to_midi_sequence(prog: ChordProgression, velocity: int = 100) -> list[dict]:
    """
    Convert a progression to a flat MIDI-like note sequence for export.
    Each event has: tick, midi, velocity, duration_ticks.
    Assumes 480 ticks per beat.
    """
    tpb = 480  # ticks per beat
    events = []
    tick = 0

    for chord in prog.chords:
        dur_ticks = int(chord["duration_beats"] * tpb)
        for midi_note in chord["midi_notes"]:
            events.append({
                "tick": tick,
                "midi": midi_note,
                "velocity": velocity,
                "duration_ticks": dur_ticks,
                "chord_symbol": chord["symbol"],
            })
        tick += dur_ticks

    return events


# --- Export ---------------------------------------------------------------

def export_progression(prog: ChordProgression, out_dir: Path) -> Path:
    """Export a progression to JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"chord_progression_{prog.name}.json"

    analysis = analyze_intervals(prog)
    midi_seq = progression_to_midi_sequence(prog)

    data = {
        "dubforge_module": "CHORD_PROGRESSION_ENGINE",
        "version": "1.0",
        "doctrine": "Planck x phi Fractal Basscraft",
        "progression": asdict(prog),
        "analysis": analysis,
        "midi_sequence_length": len(midi_seq),
        "midi_sequence_preview": midi_seq[:20],  # First 20 events
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    return filename


# --- Main -----------------------------------------------------------------

def main():
    """Generate all chord progression presets."""
    out_dir = Path(__file__).parent.parent / "output" / "analysis"

    print(f"  Generating {len(ALL_PRESETS)} chord progression presets...")
    print()

    for name, preset_fn in ALL_PRESETS.items():
        prog = preset_fn()
        filepath = export_progression(prog, out_dir)

        # Print summary
        chord_syms = " → ".join(c["symbol"] for c in prog.chords)
        romans = " → ".join(c["roman"] for c in prog.chords)
        rhythm = " + ".join(str(b) for b in prog.harmonic_rhythm)
        analysis = analyze_intervals(prog)

        print(f"  [{name}]")
        print(f"    Key: {prog.key} | BPM: {prog.bpm} | Tuning: {prog.tuning_hz} Hz")
        print(f"    Roman: {romans}")
        print(f"    Chords: {chord_syms}")
        print(f"    Rhythm: {rhythm} = {sum(prog.harmonic_rhythm)} beats")
        print(f"    Fibonacci interval ratio: {analysis.get('fibonacci_interval_ratio', 0)}")
        print(f"    Tags: {', '.join(prog.tags)}")
        print(f"    → {filepath}")
        print()

    print(f"  ✓ {len(ALL_PRESETS)} progressions exported")


if __name__ == "__main__":
    main()
