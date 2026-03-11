"""
DUBFORGE Engine — Production Pipeline

Master orchestrator: SongDNA → Ableton Live + Serum 2 → Mixed Track

This replaces the Python-synthesis path in forge.py with real DAW control.
Translates SongDNA into:
  - Ableton session with MIDI/audio tracks
  - Serum 2 instances with correct presets per track
  - MIDI clips programmed from DNA note data
  - Drum samples loaded from sample library
  - FX chains (reverb, delay, distortion, compression)
  - Routing (sends, groups, mastering chain)
  - Mix automation (volume, pan, filter sweeps)

Usage:
    from engine.production_pipeline import ProductionPipeline
    pipe = ProductionPipeline()
    pipe.connect()
    result = pipe.produce_from_dna(dna)  # SongDNA → full Ableton session

    # Or from scratch:
    result = pipe.produce_from_name("CYCLOPS FURY")  # name → DNA → session
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.log import get_logger
from engine.config_loader import PHI, FIBONACCI, A4_432
from engine.ableton_bridge import AbletonBridge, NoteData, COLORS, QUANT
from engine.serum2_controller import (
    Serum2Controller, DUBFORGE_PRESETS, SERUM_PARAMS
)
from engine.sample_library import SampleLibrary
from engine.midi_export import write_midi_file, NoteEvent, export_full_arrangement

_log = get_logger("dubforge.production_pipeline")

# ═══════════════════════════════════════════════════════════════════════════
# GOLDEN RATIO CONSTANTS — derived from PHI for music production
# ═══════════════════════════════════════════════════════════════════════════

PHI_INV = 1.0 / PHI          # 0.6180339887… — the golden conjugate
PHI_SQ = PHI * PHI            # 2.6180339887… — phi squared
FIB_BARS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]  # Fibonacci bar lengths
GOLDEN_VEL = int(127 * PHI_INV)  # ~78 — golden velocity

# Phi-derived mix levels (each track sits at a golden ratio distance)
PHI_MIX_LEVELS = {
    "SUB BASS":     round(PHI_INV ** 0.2, 4),   # ~0.896 (loudest)
    "MID BASS":     round(PHI_INV ** 0.4, 4),   # ~0.803
    "DRUMS":        round(PHI_INV ** 0.3, 4),   # ~0.858
    "LEAD":         round(PHI_INV ** 0.6, 4),   # ~0.720
    "PAD":          round(PHI_INV ** 1.0, 4),   # ~0.618
    "FX AUDIO":     round(PHI_INV ** 1.2, 4),   # ~0.554
    "DRUM SAMPLES": round(PHI_INV ** 0.5, 4),   # ~0.786
}

# Phi-derived send levels
PHI_SEND_REVERB = round(PHI_INV ** 2, 3)   # ~0.382
PHI_SEND_DELAY = round(PHI_INV ** 3, 3)    # ~0.236

# Lazy imports for DNA system (avoids circular)
_SongDNA = None
_VariationEngine = None
_SongBlueprint = None


def _ensure_dna_imports():
    global _SongDNA, _VariationEngine, _SongBlueprint
    if _SongDNA is None:
        from engine.variation_engine import SongDNA, VariationEngine, SongBlueprint
        _SongDNA = SongDNA
        _VariationEngine = VariationEngine
        _SongBlueprint = SongBlueprint


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SCALE_INTERVALS = {
    "minor":          [0, 2, 3, 5, 7, 8, 10],
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "dorian":         [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "locrian":        [0, 1, 3, 5, 6, 8, 10],
    "chromatic":      [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "whole_tone":     [0, 2, 4, 6, 8, 10],
    "pentatonic":     [0, 2, 4, 7, 9],
}

# MIDI note number for root notes
ROOT_MIDI = {
    "C": 24, "C#": 25, "Db": 25, "D": 26, "D#": 27, "Eb": 27,
    "E": 28, "F": 29, "F#": 30, "Gb": 30, "G": 31, "G#": 32,
    "Ab": 32, "A": 33, "A#": 34, "Bb": 34, "B": 35,
}

# Serum preset mapping based on bass/lead types from SongDNA
BASS_TYPE_TO_PRESET = {
    "dist_fm":    "DUBFORGE_FM_BASS",
    "sync":       "DUBFORGE_GROWL_BASS",
    "neuro":      "DUBFORGE_TEAROUT_BASS",
    "acid":       "DUBFORGE_RIDDIM_BASS",
    "growl":      "DUBFORGE_GROWL_BASS",
    "formant":    "DUBFORGE_RIDDIM_BASS",
    "fm_growl":   "DUBFORGE_FM_BASS",
    "reese":      "DUBFORGE_REESE_BASS",
    "sub":        "DUBFORGE_SUB_BASS",
}

LEAD_TYPE_TO_PRESET = {
    "screech":    "DUBFORGE_SCREECH_LEAD",
    "supersaw":   "DUBFORGE_SUPERSAW_LEAD",
    "additive":   "DUBFORGE_SCREECH_LEAD",
    "fm":         "DUBFORGE_SCREECH_LEAD",
}

PAD_TYPE_TO_PRESET = {
    "dark":       "DUBFORGE_DARK_PAD",
    "ambient":    "DUBFORGE_AMBIENT_PAD",
    "lush":       "DUBFORGE_AMBIENT_PAD",
}

# Track color scheme
TRACK_COLORS = {
    "SUB BASS":     "dubforge_1",
    "MID BASS":     "dubforge_2",
    "LEAD":         "dubforge_3",
    "PAD":          "purple",
    "DRUMS":        "orange",
    "FX":           "cyan",
    "VOX":          "pink",
    "MASTER":       "white",
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TrackSetup:
    """Configuration for an Ableton track."""
    name: str
    type: str = "midi"  # "midi" or "audio"
    color: str = "white"
    instrument: str = ""  # "serum2", "drum_rack", "simpler", ""
    preset: str = ""
    volume: float = 0.85
    pan: float = 0.0
    arm: bool = False
    sends: dict[int, float] = field(default_factory=dict)  # return_idx → level
    group: str = ""


@dataclass
class SessionSetup:
    """Complete session configuration."""
    name: str
    bpm: float
    key: str
    scale: str
    time_sig: tuple[int, int] = (4, 4)
    tracks: list[TrackSetup] = field(default_factory=list)
    return_tracks: list[str] = field(default_factory=list)  # ["REVERB", "DELAY"]
    scenes: list[str] = field(default_factory=list)
    total_bars: int = 64


@dataclass
class ProductionResult:
    """Result of a production run."""
    session_name: str
    bpm: float
    key: str
    track_count: int
    scene_count: int
    midi_files: list[str] = field(default_factory=list)
    sample_paths: list[str] = field(default_factory=list)
    status: str = "created"
    errors: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# NOTE / PATTERN GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

class PatternGenerator:
    """Generate MIDI patterns from SongDNA specification.

    Golden Ratio Integration:
      - Fibonacci bar lengths for clip structures (1,2,3,5,8,13,21)
      - Phi-weighted velocities: accents at golden positions within bar
      - Golden section note placement: strongest notes at beat × PHI_INV
      - Phi-harmonic melody intervals: scale degree jumps follow phi
      - Dojo 128 Rack note mapping for drum patterns
    """

    def __init__(self, root_note: int, scale: str, bpm: float):
        self.root = root_note
        self.intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["minor"])
        self.bpm = bpm

    def note(self, degree: int, octave: int = 2) -> int:
        """Scale degree → MIDI note. degree=0 → root, degree=2 → 3rd."""
        semi = self.intervals[degree % len(self.intervals)]
        oct_shift = degree // len(self.intervals)
        return self.root + (octave * 12) + semi + (oct_shift * 12)

    def phi_velocity(self, position: float, bar_length: float = 4.0,
                     base: int = 80, accent: int = 120) -> int:
        """Golden-ratio velocity curve within a bar.

        Notes at the golden section point (beat × 0.618) get maximum
        accent. Velocity falls off by PHI_INV from that peak.
        """
        golden_beat = bar_length * PHI_INV  # ~2.472 in 4/4
        distance = abs(position % bar_length - golden_beat) / bar_length
        weight = PHI_INV ** (distance * 3)  # Smooth falloff
        return int(base + (accent - base) * weight)

    def fibonacci_bars(self, total_bars: int) -> list[int]:
        """Decompose total bars into Fibonacci-number segments.

        E.g. 13 → [8, 5], 21 → [13, 8], 8 → [5, 3], 4 → [3, 1]
        Uses Zeckendorf's representation (every positive integer is
        a unique sum of non-consecutive Fibonacci numbers).
        """
        fibs = [f for f in FIB_BARS if f > 0]
        fibs.sort(reverse=True)
        segments = []
        remaining = total_bars
        for f in fibs:
            while remaining >= f:
                segments.append(f)
                remaining -= f
        if remaining > 0:
            segments.append(remaining)
        return segments

    # ── Bass Patterns ────────────────────────────────────────────────────

    def sub_bass_pattern(self, bars: int = 4, density: float = 0.5) -> list[NoteData]:
        """Generate sub bass pattern — steady root notes at phi-weighted timing.

        Golden ratio: note duration = PHI_INV × bar (≈2.472 beats for sustained),
        velocity peaks at golden-section position.
        """
        notes = []
        phi_dur = 4.0 * PHI_INV  # ~2.472 beats — golden note length
        for bar in range(bars):
            # Primary hit on beat 1
            t = bar * 4.0
            notes.append(NoteData(
                pitch=self.note(0, 1),
                start_time=t,
                duration=phi_dur if density < 0.7 else phi_dur * PHI_INV,
                velocity=self.phi_velocity(0.0),
            ))
            # Secondary hit at golden section of bar
            if density > 0.5:
                golden_t = bar * 4.0 + 4.0 * PHI_INV  # beat ~2.472
                notes.append(NoteData(
                    pitch=self.note(0, 1),
                    start_time=golden_t,
                    duration=4.0 - 4.0 * PHI_INV,  # fills rest of bar
                    velocity=int(self.phi_velocity(golden_t) * PHI_INV),
                ))
        return notes

    def mid_bass_pattern(self, bars: int = 4, bass_type: str = "growl",
                         density: float = 0.7) -> list[NoteData]:
        """Generate mid bass pattern — rhythmic, syncopated."""
        notes = []
        # Rhythmic grid — dubstep style
        rhythm = self._dubstep_rhythm(bars, density)
        for t, dur, vel in rhythm:
            # Rotate through scale degrees for movement
            degree = [0, 0, 5, 3, 0, 4, 0, 2][int(t * 2) % 8]
            notes.append(NoteData(
                pitch=self.note(degree, 2),
                start_time=t,
                duration=dur,
                velocity=vel,
            ))
        return notes

    def _dubstep_rhythm(self, bars: int, density: float) -> list[tuple]:
        """Generate dubstep-style rhythmic grid with phi-velocity accents.

        Golden ratio: syncopation points at phi-derived positions,
        velocities weighted by distance from golden section.
        Returns: [(time_beats, duration_beats, velocity)]
        """
        events = []
        for bar in range(bars):
            base = bar * 4.0
            # Core dubstep rhythm — golden section on the snare hit area
            # 4.0 × PHI_INV ≈ 2.472 — the golden beat in 4/4
            phi_beat = 4.0 * PHI_INV  # ~2.472
            grid = [
                (0.0,        0.75, 120),             # beat 1 — anchor
                (PHI_INV,    0.25, 90),               # ~0.618 — golden sync
                (1.5,        0.5,  100),              # and-of-2
                (phi_beat,   0.5,  127),              # ~2.472 — GOLDEN HIT
                (3.0,        0.5,  int(127*PHI_INV)), # beat 4 — phi velocity
                (3.0+PHI_INV, 0.25, 80),              # ~3.618 — golden sync
                (3.75,       0.25, 95),               # pickup
            ]
            for t, d, v in grid:
                if t / 4.0 < density or t == 0:
                    events.append((base + t, d, v))
        return events

    # ── Lead Pattern ─────────────────────────────────────────────────────

    def lead_pattern(self, bars: int = 4, style: str = "melodic") -> list[NoteData]:
        """Generate lead melody pattern using Fibonacci-interval contour.

        Golden ratio: melody jumps follow Fibonacci intervals (1,1,2,3,5),
        note durations alternate phi-long and phi-short.
        """
        notes = []
        # Fibonacci-interval melody: jumps of 1,1,2,3,5 scale degrees
        fib_jumps = [1, 1, 2, 3, 5, 3, 2, 1, 1, 2, 3, 5, 2, 1, 1, 0]
        degree = 0
        phi_short = PHI_INV  # ~0.618 beats
        phi_long = 1.0       # 1 beat (phi_short × PHI ≈ 1.0)
        for bar in range(bars):
            for i in range(4):
                idx = (bar * 4 + i) % len(fib_jumps)
                degree = (degree + fib_jumps[idx]) % len(self.intervals)
                t = bar * 4.0 + i
                # Alternate phi-long and phi-short durations
                dur = phi_long if i % 2 == 0 else phi_short
                notes.append(NoteData(
                    pitch=self.note(degree, 3),
                    start_time=t,
                    duration=dur,
                    velocity=self.phi_velocity(float(i), 4.0, 85, 115),
                ))
        return notes

    # ── Pad Pattern ──────────────────────────────────────────────────────

    def pad_pattern(self, bars: int = 4) -> list[NoteData]:
        """Generate pad chord pattern — phi-stacked voicings.

        Golden ratio: chord voicings separated by Fibonacci intervals,
        velocity layers follow PHI_INV cascade (root loudest, upper
        voices softer by phi).
        """
        notes = []
        # Progression: i - VI - III - VII (Fibonacci degrees: 0,5,2,6)
        chords = [
            [0, 2, 4],  # i (root triad)
            [5, 0, 2],  # VI
            [2, 4, 6],  # III
            [6, 1, 3],  # VII
        ]
        for bar in range(bars):
            chord = chords[bar % len(chords)]
            for j, degree in enumerate(chord):
                # Phi-cascade velocity: root=90, 3rd=~56, 5th=~34
                vel = int(90 * (PHI_INV ** j))
                vel = max(vel, 30)  # floor
                notes.append(NoteData(
                    pitch=self.note(degree, 3),
                    start_time=bar * 4.0,
                    duration=4.0 * PHI_INV if j == 0 else 4.0,  # root shorter (breath)
                    velocity=vel,
                ))
        return notes

    # ── Drum Patterns (MIDI) ────────────────────────────────────────────

    def kick_pattern(self, bars: int = 4, style: str = "standard") -> list[NoteData]:
        """Generate kick pattern. Uses GM MIDI note 36 (C1).

        Golden ratio: ghost kick at golden-section position (beat × PHI_INV).
        """
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            if style == "halftime":
                notes.append(NoteData(36, base, 0.5, 127))
                notes.append(NoteData(36, base + 3.0, 0.5, GOLDEN_VEL))
            elif style == "dubstep":
                notes.append(NoteData(36, base, 0.5, 127))
                if bar % 2 == 0:
                    # Ghost kick at golden position instead of fixed 2.5
                    notes.append(NoteData(36, base + 4.0 * PHI_INV, 0.25, GOLDEN_VEL))
            else:  # standard
                for beat in [0, 2]:
                    notes.append(NoteData(36, base + beat, 0.5, 120))
        return notes

    def snare_pattern(self, bars: int = 4, style: str = "halftime") -> list[NoteData]:
        """Generate snare pattern. MIDI note 38 (D1).

        Golden ratio: fills use Fibonacci subdivisions.
        """
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            if style == "halftime":
                notes.append(NoteData(38, base + 2.0, 0.5, 120))
            elif style == "dubstep":
                notes.append(NoteData(38, base + 2.0, 0.5, 127))
                if bar % 4 == 3:  # Fibonacci fill: 3 hits at Fib timing
                    notes.append(NoteData(38, base + 3.0, 0.25, GOLDEN_VEL))
                    notes.append(NoteData(38, base + 3.5, 0.25, 100))
                    notes.append(NoteData(38, base + 3.75, 0.25, 110))
            else:
                for beat in [1, 3]:
                    notes.append(NoteData(38, base + beat, 0.5, 115))
        return notes

    def hat_pattern(self, bars: int = 4, density: float = 0.6) -> list[NoteData]:
        """Generate hi-hat pattern. Closed=42, Open=46.

        Golden ratio: open hats at golden positions, velocity follows phi wave.
        """
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            for eighth in range(8):
                t = base + eighth * 0.5
                if eighth / 8.0 < density:
                    # Phi-velocity: accent follows golden curve
                    vel = self.phi_velocity(eighth * 0.5, 4.0, 55, 95)
                    # Open hat at golden position (~5th eighth ≈ beat 2.5)
                    golden_eighth = int(8 * PHI_INV)  # ~5
                    midi_note = 46 if eighth == golden_eighth else 42
                    notes.append(NoteData(midi_note, t, 0.25, vel))
        return notes

    def full_drum_pattern(self, bars: int = 4, style: str = "dubstep",
                          hat_density: float = 0.6) -> list[NoteData]:
        """Combined drum pattern — kick + snare + hats (phi-weighted)."""
        notes = []
        notes.extend(self.kick_pattern(bars, style))
        notes.extend(self.snare_pattern(bars, "halftime" if style == "dubstep" else style))
        notes.extend(self.hat_pattern(bars, hat_density))
        return notes

    # ── Fibonacci Arp (Dojo technique) ───────────────────────────────────

    def fibonacci_arp_pattern(self, bars: int = 4, octave: int = 3) -> list[NoteData]:
        """Generate a Fibonacci-interval arpeggio.

        Each note jumps by the next Fibonacci number of scale degrees:
        0, +1, +1, +2, +3, +5, +3, +2, +1, +1, 0 (arch shape).
        Duration of each note = Fibonacci-scaled 16ths.
        """
        notes = []
        fib_jumps = [0, 1, 1, 2, 3, 5, 3, 2, 1, 1, 0]
        degree = 0
        t = 0.0
        fib_durs = [0.25, 0.25, 0.5, 0.25, 0.5, 0.75, 0.5, 0.25, 0.5, 0.25, 0.25]
        for bar in range(bars):
            for i, jump in enumerate(fib_jumps):
                if t >= (bar + 1) * 4.0:
                    break
                degree = (degree + jump) % len(self.intervals)
                dur = fib_durs[i % len(fib_durs)]
                notes.append(NoteData(
                    pitch=self.note(degree, octave),
                    start_time=t,
                    duration=dur,
                    velocity=self.phi_velocity(t % 4.0),
                ))
                t += dur
            if t < (bar + 1) * 4.0:
                t = (bar + 1) * 4.0  # align to next bar
        return notes


# ═══════════════════════════════════════════════════════════════════════════
# MIDI FILE EXPORTER
# ═══════════════════════════════════════════════════════════════════════════

class MIDIExporter:
    """Export patterns as MIDI files for Ableton import."""

    def __init__(self, output_dir: str = "output/midi"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_pattern(self, name: str, notes: list[NoteData],
                       bpm: float = 140) -> str:
        """Export a pattern to a MIDI file. Returns file path."""
        events = []
        for n in notes:
            events.append(NoteEvent(
                pitch=n.pitch,
                start_beat=n.start_time,
                duration_beats=n.duration,
                velocity=n.velocity,
                channel=0,
            ))

        filepath = str(self.output_dir / f"{name}.mid")
        write_midi_file(
            tracks=[(name, events)],
            path=filepath,
            bpm=int(bpm),
            tpb=480,
        )
        _log.info(f"Exported MIDI: {filepath}")
        return filepath

    def export_all_patterns(self, patterns: dict[str, list[NoteData]],
                            bpm: float = 140) -> dict[str, str]:
        """Export multiple patterns. Returns {name: filepath}."""
        results = {}
        for name, notes in patterns.items():
            results[name] = self.export_pattern(name, notes, bpm)
        return results


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTION PIPELINE — THE MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class ProductionPipeline:
    """Master production pipeline: DNA → Ableton session → full track.

    Golden Ratio & Dojo Integration:
    - Fibonacci bar structures for clip/scene lengths (3,5,8,13,21)
    - PHI-weighted velocity curves across all patterns
    - Phi-proportioned mix levels (each track at PHI_INV^n)
    - Golden-section send amounts (reverb/delay at phi cascades)
    - Dojo PSBS track architecture (Sub → Mid Growl → Lead → Pad)
    - Fibonacci arp pattern generation (Dojo technique)
    - 128 Rack zone mapping for drum samples

    Complete workflow:
    1. Parse SongDNA or generate from track name
    2. Create Ableton session (Dojo template with PSBS tracks)
    3. Load Serum 2 on each synth track
    4. Configure Serum presets per track role (phi-tuned params)
    5. Program MIDI clips from DNA patterns (Fibonacci structures)
    6. Load drum samples into audio tracks
    7. Set up FX chains (returns with phi-proportioned sends)
    8. Configure sends & routing (golden ratio levels)
    9. Set up mix automation (phi mix curve)
    10. Export MIDI files as backups
    """

    def __init__(self, sample_dir: str = "output/samples",
                 midi_dir: str = "output/midi",
                 freesound_api_key: str = ""):
        self.bridge = AbletonBridge(verbose=True)
        self.samples = SampleLibrary(sample_dir, freesound_api_key)
        self.midi_exporter = MIDIExporter(midi_dir)
        self._serum_controllers: dict[int, Serum2Controller] = {}  # track → controller
        self._connected = False

    # ── CONNECTION ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to Ableton Live."""
        self._connected = self.bridge.connect()
        return self._connected

    def disconnect(self):
        self.bridge.disconnect()
        self._connected = False

    # ── MAIN ENTRY POINTS ────────────────────────────────────────────────

    def produce_from_name(self, name: str, style: str = "dubstep",
                           mood: str = "aggressive",
                           bpm: int = 140) -> ProductionResult:
        """Complete production from a track name.

        name → SongDNA → Ableton session → programmed clips → mix ready
        """
        _ensure_dna_imports()

        # Generate DNA from name
        blueprint = _SongBlueprint(
            name=name,
            theme=name.lower(),
            mood=mood,
            style=style,
            bpm=bpm,
        )
        engine = _VariationEngine()
        dna = engine.forge_dna(blueprint)

        print(f"\n  ◆ DUBFORGE Production Pipeline")
        print(f"    Track: {dna.name}")
        print(f"    Key: {dna.key} {dna.scale} @ {dna.bpm} BPM")
        print(f"    Bass: {dna.bass.primary_type} / {dna.bass.secondary_type}")
        print(f"    Style: {dna.style}")

        return self.produce_from_dna(dna)

    def produce_from_dna(self, dna) -> ProductionResult:
        """Full production from a SongDNA object.

        This is the core method that builds everything in Ableton.
        """
        result = ProductionResult(
            session_name=dna.name,
            bpm=dna.bpm,
            key=f"{dna.key} {dna.scale}",
            track_count=0,
            scene_count=0,
        )

        # Determine root MIDI note
        root_midi = ROOT_MIDI.get(dna.key, ROOT_MIDI.get("F", 29))

        # Pattern generator
        pg = PatternGenerator(root_midi, dna.scale, dna.bpm)

        # ── 1. SESSION SETUP ───────────────────────────────────────────
        session = self._build_session_setup(dna)

        if self._connected:
            self._setup_ableton_session(session, dna)
            result.track_count = self.bridge.get_track_count()
            result.scene_count = self.bridge.get_scene_count()
        else:
            print("  ⚠ Not connected to Ableton — generating MIDI files only")

        # ── 2. GENERATE PATTERNS ───────────────────────────────────────
        patterns = self._generate_all_patterns(dna, pg)

        # ── 3. PROGRAM CLIPS / EXPORT MIDI ─────────────────────────────
        if self._connected:
            self._program_clips(session, patterns, dna)
        midi_files = self.midi_exporter.export_all_patterns(patterns, dna.bpm)
        result.midi_files = list(midi_files.values())

        # ── 4. LOAD SAMPLES ───────────────────────────────────────────
        drum_kit = self.samples.build_drum_kit()
        if drum_kit:
            result.sample_paths = list(drum_kit.values())
            if self._connected:
                self._load_drum_samples(drum_kit, session)

        # ── 5. FX + ROUTING ───────────────────────────────────────────
        if self._connected:
            self._setup_fx_routing(session, dna)

        # ── 6. MIX SETTINGS ──────────────────────────────────────────
        if self._connected:
            self._apply_mix_settings(session, dna)

        result.status = "complete" if self._connected else "midi_only"
        print(f"\n  ✓ Production pipeline complete: {result.status}")
        print(f"    MIDI files: {len(result.midi_files)}")
        print(f"    Samples: {len(result.sample_paths)}")
        if self._connected:
            print(f"    Ableton tracks: {result.track_count}")
            print(f"    Scenes: {result.scene_count}")

        return result

    # ── OFFLINE MODE (MIDI export without Ableton) ────────────────────

    def produce_offline(self, dna) -> ProductionResult:
        """Generate MIDI files and session templates without Ableton.

        Use this when Ableton isn't running. Produces:
        - MIDI files for each track
        - Session template JSON
        - ALS project file
        """
        result = ProductionResult(
            session_name=dna.name,
            bpm=dna.bpm,
            key=f"{dna.key} {dna.scale}",
            track_count=0,
            scene_count=0,
        )

        root_midi = ROOT_MIDI.get(dna.key, ROOT_MIDI.get("F", 29))
        pg = PatternGenerator(root_midi, dna.scale, dna.bpm)

        # Generate patterns
        patterns = self._generate_all_patterns(dna, pg)

        # Export MIDI files
        midi_files = self.midi_exporter.export_all_patterns(patterns, dna.bpm)
        result.midi_files = list(midi_files.values())

        # Generate ALS project file
        from engine.als_generator import ALSProject, ALSTrack, ALSScene, write_als
        session = self._build_session_setup(dna)
        als = ALSProject(
            name=dna.name,
            bpm=dna.bpm,
            time_sig_num=4,
            time_sig_den=4,
        )
        for track_setup in session.tracks:
            als.tracks.append(ALSTrack(
                name=track_setup.name,
                track_type=track_setup.type,
                color=track_setup.color,
            ))
        for scene_name in session.scenes:
            als.scenes.append(ALSScene(name=scene_name))

        als_path = f"output/ableton/{dna.name.replace(' ', '_')}.als"
        Path("output/ableton").mkdir(parents=True, exist_ok=True)
        write_als(als, als_path)
        _log.info(f"Generated ALS project: {als_path}")

        result.status = "offline"
        result.track_count = len(session.tracks)
        result.scene_count = len(session.scenes)

        print(f"\n  ✓ Offline production complete")
        print(f"    MIDI files: {len(result.midi_files)}")
        print(f"    ALS project: {als_path}")

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Session Building
    # ═══════════════════════════════════════════════════════════════════════

    def _build_session_setup(self, dna) -> SessionSetup:
        """Build session setup from DNA — Dojo template with phi mix levels.

        Session architecture follows Producer Dojo PSBS methodology:
        - Track layout mirrors dojo session template (128 Rack, Sub, Mid, etc.)
        - Volume levels use phi-derived ratios (PHI_MIX_LEVELS)
        - Scenes follow Fibonacci bar counts from arrangement
        - Return sends at golden ratio amounts
        """
        session = SessionSetup(
            name=dna.name,
            bpm=dna.bpm,
            key=dna.key,
            scale=dna.scale,
            total_bars=dna.total_bars,
        )

        # ── Synth Tracks (Dojo: Sub → Mid Growl → Lead → Pad) ─────
        # Sub bass
        session.tracks.append(TrackSetup(
            name="SUB BASS",
            type="midi",
            color="dubforge_1",
            instrument="serum2",
            preset=BASS_TYPE_TO_PRESET.get("sub", "DUBFORGE_SUB_BASS"),
            volume=PHI_MIX_LEVELS.get("SUB BASS", 0.85),
            group="BASS",
        ))

        # Mid bass (primary — Dojo "MID GROWL")
        primary_bass = dna.bass.primary_type if hasattr(dna, 'bass') else "growl"
        session.tracks.append(TrackSetup(
            name="MID BASS",
            type="midi",
            color="dubforge_2",
            instrument="serum2",
            preset=BASS_TYPE_TO_PRESET.get(primary_bass, "DUBFORGE_GROWL_BASS"),
            volume=PHI_MIX_LEVELS.get("MID BASS", 0.80),
            group="BASS",
        ))

        # Lead
        session.tracks.append(TrackSetup(
            name="LEAD",
            type="midi",
            color="dubforge_3",
            instrument="serum2",
            preset=LEAD_TYPE_TO_PRESET.get("screech", "DUBFORGE_SCREECH_LEAD"),
            volume=PHI_MIX_LEVELS.get("LEAD", 0.70),
        ))

        # Pad
        pad_type = dna.atmosphere.pad_type if hasattr(dna, 'atmosphere') else "dark"
        session.tracks.append(TrackSetup(
            name="PAD",
            type="midi",
            color="purple",
            instrument="serum2",
            preset=PAD_TYPE_TO_PRESET.get(pad_type, "DUBFORGE_DARK_PAD"),
            volume=PHI_MIX_LEVELS.get("PAD", 0.55),
        ))

        # ── Drum Tracks ────────────────────────────────────────────
        session.tracks.append(TrackSetup(
            name="DRUMS",
            type="midi",
            color="orange",
            instrument="drum_rack",
            volume=PHI_MIX_LEVELS.get("DRUMS", 0.85),
        ))

        # ── Audio Tracks (for samples) ────────────────────────────
        session.tracks.append(TrackSetup(
            name="DRUM SAMPLES",
            type="audio",
            color="orange",
            volume=PHI_MIX_LEVELS.get("DRUM SAMPLES", 0.80),
        ))

        session.tracks.append(TrackSetup(
            name="FX AUDIO",
            type="audio",
            color="cyan",
            volume=PHI_MIX_LEVELS.get("FX AUDIO", 0.65),
        ))

        # ── Return Tracks ─────────────────────────────────────────
        session.return_tracks = ["REVERB", "DELAY", "DISTORTION"]

        # ── Scenes (Fibonacci bar structure from arrangement) ─────
        if hasattr(dna, 'arrangement') and dna.arrangement:
            session.scenes = [s.name for s in dna.arrangement]
        else:
            # Default scenes with Fibonacci bar counts
            # 3+5+8+5+3+8+2 = 34 bars (Fibonacci!)
            session.scenes = [
                "INTRO [3 bars]", "BUILD [5 bars]", "DROP 1 [8 bars]",
                "BREAK [5 bars]", "BUILD 2 [3 bars]", "DROP 2 [8 bars]",
                "OUTRO [2 bars]",
            ]

        return session

    def _setup_ableton_session(self, session: SessionSetup, dna):
        """Create the actual Ableton session via AbletonOSC."""
        print(f"\n  ◆ Setting up Ableton session: {session.name}")

        # Set tempo and time sig
        self.bridge.set_tempo(session.bpm)
        self.bridge.set_time_signature(*session.time_sig)
        self.bridge.set_metronome(False)

        # Display message in Ableton
        self.bridge.show_message(f"DUBFORGE: Creating {session.name}")

        # Create tracks
        track_indices = {}
        for i, track_setup in enumerate(session.tracks):
            if track_setup.type == "audio":
                idx = self.bridge.create_audio_track(-1, track_setup.name)
            else:
                idx = self.bridge.create_midi_track(-1, track_setup.name)

            track_indices[track_setup.name] = idx
            self.bridge.set_track_color(idx, track_setup.color)
            self.bridge.set_track_volume(idx, track_setup.volume)
            if track_setup.pan != 0:
                self.bridge.set_track_pan(idx, track_setup.pan)

            print(f"    Track {idx}: {track_setup.name} ({track_setup.type})")
            time.sleep(0.05)

        # Create return tracks
        for rt_name in session.return_tracks:
            rt_idx = self.bridge.create_return_track(rt_name)
            print(f"    Return {rt_idx}: {rt_name}")
            time.sleep(0.05)

        # Create scenes
        for scene_name in session.scenes:
            s_idx = self.bridge.create_scene(-1)
            self.bridge.set_scene_name(s_idx, scene_name)
            time.sleep(0.02)

        # Store track indices for later use
        self._track_indices = track_indices

        print(f"  ✓ Session created: {len(track_indices)} tracks, "
              f"{len(session.return_tracks)} returns, "
              f"{len(session.scenes)} scenes")

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Pattern Generation
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_all_patterns(self, dna, pg: PatternGenerator) -> dict[str, list[NoteData]]:
        """Generate all MIDI patterns from DNA — Fibonacci-structured.

        Golden ratio integration:
        - Clip lengths decomposed into Fibonacci bar segments
        - Patterns use phi-velocity and golden-section note placement
        - Fibonacci arp pattern generated as bonus clip
        """
        bars = dna.total_bars if hasattr(dna, 'total_bars') else 16
        # Use Fibonacci-number clip length (nearest Fib ≤ 8)
        fib_clip_bars = max(f for f in FIB_BARS if f <= min(bars, 8))
        _log.info(f"Fibonacci clip bars: {fib_clip_bars} (from {bars} total, "
                  f"Zeckendorf: {pg.fibonacci_bars(bars)})")

        patterns = {}

        # Sub bass (phi-timed)
        density = dna.bass.sub_weight if hasattr(dna, 'bass') else 0.6
        patterns["sub_bass"] = pg.sub_bass_pattern(fib_clip_bars, density)

        # Mid bass (phi-syncopated)
        bass_type = dna.bass.primary_type if hasattr(dna, 'bass') else "growl"
        patterns["mid_bass"] = pg.mid_bass_pattern(fib_clip_bars, bass_type, 0.7)

        # Lead (Fibonacci-interval melody)
        patterns["lead"] = pg.lead_pattern(fib_clip_bars, "melodic")

        # Pad (phi-velocity cascade)
        patterns["pad"] = pg.pad_pattern(fib_clip_bars)

        # Fibonacci arp (Dojo technique)
        patterns["fibonacci_arp"] = pg.fibonacci_arp_pattern(fib_clip_bars)

        # Drums (phi-weighted velocity curves)
        hat_subdiv = dna.drums.hat_density if hasattr(dna, 'drums') else 16
        hat_density = min(hat_subdiv / 32.0, 1.0)
        patterns["drums"] = pg.full_drum_pattern(fib_clip_bars, "dubstep", hat_density)

        # Individual drum parts
        patterns["kick"] = pg.kick_pattern(fib_clip_bars, "dubstep")
        patterns["snare"] = pg.snare_pattern(fib_clip_bars, "halftime")
        patterns["hats"] = pg.hat_pattern(fib_clip_bars, hat_density)

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Clip Programming
    # ═══════════════════════════════════════════════════════════════════════

    def _program_clips(self, session: SessionSetup, patterns: dict,
                       dna):
        """Program MIDI clips into Ableton tracks."""
        if not hasattr(self, '_track_indices'):
            return

        print(f"\n  ◆ Programming clips...")

        clip_bars = min(dna.total_bars, 8) if hasattr(dna, 'total_bars') else 8
        clip_length = clip_bars * 4.0  # in beats

        # Map pattern names to track names
        pattern_to_track = {
            "sub_bass": "SUB BASS",
            "mid_bass": "MID BASS",
            "lead":     "LEAD",
            "pad":      "PAD",
            "drums":    "DRUMS",
        }

        for pattern_name, track_name in pattern_to_track.items():
            if pattern_name not in patterns or track_name not in self._track_indices:
                continue

            track_idx = self._track_indices[track_name]
            notes = patterns[pattern_name]

            if not notes:
                continue

            # Create clip in slot 0
            self.bridge.program_clip_from_notes(
                track=track_idx,
                slot=0,
                length_beats=clip_length,
                notes=notes,
                name=f"{dna.name} - {track_name}",
                loop=True,
            )
            print(f"    Clip: {track_name} — {len(notes)} notes, {clip_length} beats")
            time.sleep(0.05)

        # Configure Serum 2 on synth tracks
        self._configure_serum_instances(session, dna)

    def _configure_serum_instances(self, session: SessionSetup, dna):
        """Discover and configure Serum 2 instances on synth tracks."""
        print(f"\n  ◆ Configuring Serum 2 instances...")

        for track_setup in session.tracks:
            if track_setup.instrument != "serum2":
                continue
            if track_setup.name not in self._track_indices:
                continue

            track_idx = self._track_indices[track_setup.name]

            # Check if Serum 2 is loaded on this track
            device_count = self.bridge.get_device_count(track_idx)
            if device_count == 0:
                print(f"    ⚠ {track_setup.name}: No device loaded. "
                      f"Load Serum 2 manually, then re-run.")
                continue

            # Create controller for this Serum instance
            ctrl = Serum2Controller(self.bridge, track_idx, 0)
            if ctrl.discover():
                self._serum_controllers[track_idx] = ctrl

                # Apply preset
                if track_setup.preset:
                    ctrl.apply_preset(track_setup.preset)
                    print(f"    ✓ {track_setup.name}: Applied {track_setup.preset} "
                          f"({ctrl.param_count} params)")

                # Apply DNA-specific tweaks
                self._apply_dna_tweaks(ctrl, track_setup, dna)
            else:
                print(f"    ⚠ {track_setup.name}: Could not discover Serum params")

    def _apply_dna_tweaks(self, ctrl: Serum2Controller, track: TrackSetup,
                          dna):
        """Apply DNA-specific parameter tweaks on top of preset.

        Golden ratio: filter cutoffs, drive amounts, and FX parameters
        use phi-derived values for harmonically natural results.
        """
        if not hasattr(dna, 'bass'):
            return

        if "BASS" in track.name.upper():
            # Apply DNA bass parameters — phi-scaled
            if hasattr(dna.bass, 'fm_depth'):
                ctrl.set_osc_b_level(dna.bass.fm_depth * PHI_INV)
            if hasattr(dna.bass, 'distortion'):
                ctrl.set_distortion(True, amount=dna.bass.distortion)
            if hasattr(dna.bass, 'filter_cutoff'):
                # Scale cutoff through phi for harmonic sweet spot
                cutoff = dna.bass.filter_cutoff * PHI_INV + (1 - PHI_INV) * 0.3
                ctrl.set_filter1_cutoff(cutoff)

        elif "LEAD" in track.name.upper():
            if hasattr(dna, 'lead') and hasattr(dna.lead, 'brightness'):
                # Phi-weighted brightness mapping
                cutoff = PHI_INV * dna.lead.brightness + (1 - PHI_INV) * 0.3
                ctrl.set_filter1_cutoff(cutoff)

        elif "PAD" in track.name.upper():
            if hasattr(dna, 'atmosphere') and hasattr(dna.atmosphere, 'reverb_decay'):
                # Golden reverb: decay scaled by phi
                decay = min(dna.atmosphere.reverb_decay * PHI_INV / 3.0, 1.0)
                ctrl.set_reverb(True, size=decay, mix=PHI_INV * 0.5)

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Sample Loading
    # ═══════════════════════════════════════════════════════════════════════

    def _load_drum_samples(self, drum_kit: dict[str, str], session: SessionSetup):
        """Load drum samples into Ableton audio tracks."""
        if "DRUM SAMPLES" not in self._track_indices:
            return

        track_idx = self._track_indices["DRUM SAMPLES"]
        print(f"\n  ◆ Loading drum samples to track {track_idx}...")

        for cat, path in drum_kit.items():
            if Path(path).exists():
                # Create audio clip from file
                slot = ["kick", "snare", "hat_closed", "hat_open",
                        "clap", "perc"].index(cat) if cat in [
                    "kick", "snare", "hat_closed", "hat_open",
                    "clap", "perc"] else 0
                self.bridge.create_audio_clip(track_idx, slot, str(Path(path).resolve()))
                self.bridge.set_clip_name(track_idx, slot, cat.upper())
                print(f"    Loaded: {cat} → slot {slot}")
                time.sleep(0.1)

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: FX & Routing
    # ═══════════════════════════════════════════════════════════════════════

    def _setup_fx_routing(self, session: SessionSetup, dna):
        """Set up return tracks and sends — phi-proportioned levels.

        Golden ratio: send levels follow PHI_INV cascade.
        Reverb sends at PHI_INV^2 ≈ 0.382, delay at PHI_INV^3 ≈ 0.236.
        Each track type gets phi-scaled amounts from the base levels.
        """
        print(f"\n  ◆ Setting up FX routing (phi-proportioned sends)...")

        reverb_send = 0  # First return = reverb
        delay_send = 1   # Second return = delay

        for track_setup in session.tracks:
            if track_setup.name not in self._track_indices:
                continue
            track_idx = self._track_indices[track_setup.name]

            # Phi-scaled send levels per track type
            if "PAD" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send,
                                           PHI_SEND_REVERB * PHI)   # ~0.618 (lush)
                self.bridge.set_track_send(track_idx, delay_send,
                                           PHI_SEND_DELAY)          # ~0.236
            elif "LEAD" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send,
                                           PHI_SEND_REVERB)         # ~0.382
                self.bridge.set_track_send(track_idx, delay_send,
                                           PHI_SEND_DELAY)          # ~0.236
            elif "MID BASS" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send,
                                           PHI_SEND_REVERB * PHI_INV)  # ~0.236 (tight)
            elif "SUB" in track_setup.name:
                pass  # No reverb on sub! (Dojo rule)
            elif "DRUM" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send,
                                           PHI_SEND_REVERB * PHI_INV)  # ~0.236

        print(f"  ✓ FX routing configured (phi sends: reverb={PHI_SEND_REVERB}, delay={PHI_SEND_DELAY})")

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Mix Settings
    # ═══════════════════════════════════════════════════════════════════════

    def _apply_mix_settings(self, session: SessionSetup, dna):
        """Apply DNA-driven mix settings — phi-proportioned levels.

        Golden ratio: master volume at PHI_INV, track panning follows
        golden angle (137.508°) for stereo field distribution.
        """
        print(f"\n  ◆ Applying phi-proportioned mix settings...")

        if hasattr(dna, 'mix'):
            # Master volume at golden ratio
            self.bridge.set_master_volume(PHI_INV)  # ~0.618

        # Apply phi-derived volumes and panning
        for track_setup in session.tracks:
            if track_setup.name not in self._track_indices:
                continue
            track_idx = self._track_indices[track_setup.name]

            # Apply phi mix level
            phi_vol = PHI_MIX_LEVELS.get(track_setup.name, track_setup.volume)
            self.bridge.set_track_volume(track_idx, phi_vol)

            # Center bass (Dojo rule: sub and mid always mono center)
            if "SUB" in track_setup.name or "MID BASS" in track_setup.name:
                self.bridge.set_track_pan(track_idx, 0.0)

        print(f"  ✓ Mix settings applied (phi levels, {len(PHI_MIX_LEVELS)} tracks)")

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def get_serum_controller(self, track_name: str) -> Serum2Controller | None:
        """Get the Serum2Controller for a named track."""
        if not hasattr(self, '_track_indices'):
            return None
        track_idx = self._track_indices.get(track_name)
        if track_idx is not None:
            return self._serum_controllers.get(track_idx)
        return None

    def preview_session(self):
        """Fire all clips in scene 0 for preview."""
        if self._connected:
            self.bridge.fire_scene(0)

    def stop_preview(self):
        if self._connected:
            self.bridge.stop()

    def list_presets(self) -> list[str]:
        """List available DUBFORGE Serum 2 presets."""
        return list(DUBFORGE_PRESETS.keys())

    # ── Context manager ──────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def quick_produce(name: str, bpm: int = 140, style: str = "dubstep",
                  mood: str = "aggressive") -> ProductionResult:
    """One-liner production: name → everything.

    Usage:
        from engine.production_pipeline import quick_produce
        result = quick_produce("CYCLOPS FURY", bpm=145)
    """
    pipe = ProductionPipeline()
    if pipe.connect():
        return pipe.produce_from_name(name, style, mood, bpm)
    else:
        # Offline mode — still generates MIDI files
        _ensure_dna_imports()
        blueprint = _SongBlueprint(name=name, theme=name.lower(),
                                   mood=mood, style=style, bpm=bpm)
        engine = _VariationEngine()
        dna = engine.forge_dna(blueprint)
        return pipe.produce_offline(dna)


def offline_produce(name: str, bpm: int = 140, style: str = "dubstep",
                    mood: str = "aggressive") -> ProductionResult:
    """Offline production: generates MIDI files + ALS without Ableton running."""
    _ensure_dna_imports()
    blueprint = _SongBlueprint(name=name, theme=name.lower(),
                               mood=mood, style=style, bpm=bpm)
    engine = _VariationEngine()
    dna = engine.forge_dna(blueprint)
    pipe = ProductionPipeline()
    return pipe.produce_offline(dna)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\nDUBFORGE Production Pipeline")
        print("=" * 50)
        print(f"Usage:")
        print(f"  python -m engine.production_pipeline 'TRACK NAME' [--bpm 145] [--offline]")
        print(f"  python -m engine.production_pipeline 'CYCLOPS FURY' --bpm 150")
        print(f"  python -m engine.production_pipeline 'DARK MATTER' --offline")
        print(f"\nFlags:")
        print(f"  --bpm N      Set tempo (default: 140)")
        print(f"  --offline    Generate MIDI files only (no Ableton required)")
        print(f"  --style S    Style: dubstep, riddim, tearout (default: dubstep)")
        print(f"  --mood M     Mood: aggressive, dark, chaotic (default: aggressive)")
        print(f"\nPresets available:")
        for name in DUBFORGE_PRESETS:
            print(f"  • {name}")
        sys.exit(0)

    name = sys.argv[1]
    bpm = 140
    style = "dubstep"
    mood = "aggressive"
    offline = False

    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--bpm" and i + 1 < len(args):
            bpm = int(args[i + 1])
        elif a == "--style" and i + 1 < len(args):
            style = args[i + 1]
        elif a == "--mood" and i + 1 < len(args):
            mood = args[i + 1]
        elif a == "--offline":
            offline = True

    if offline:
        result = offline_produce(name, bpm, style, mood)
    else:
        result = quick_produce(name, bpm, style, mood)

    print(f"\n  Result: {result.status}")
    print(f"  MIDI files: {result.midi_files}")
