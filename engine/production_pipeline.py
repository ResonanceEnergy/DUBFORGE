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
from engine.ableton_bridge import AbletonBridge, NoteData, COLORS, QUANT
from engine.serum2_controller import (
    Serum2Controller, DUBFORGE_PRESETS, SERUM_PARAMS
)
from engine.sample_library import SampleLibrary
from engine.midi_export import write_midi_file, NoteEvent, export_full_arrangement

_log = get_logger("dubforge.production_pipeline")

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
    """Generate MIDI patterns from SongDNA specification."""

    def __init__(self, root_note: int, scale: str, bpm: float):
        self.root = root_note
        self.intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["minor"])
        self.bpm = bpm

    def note(self, degree: int, octave: int = 2) -> int:
        """Scale degree → MIDI note. degree=0 → root, degree=2 → 3rd."""
        semi = self.intervals[degree % len(self.intervals)]
        oct_shift = degree // len(self.intervals)
        return self.root + (octave * 12) + semi + (oct_shift * 12)

    # ── Bass Patterns ────────────────────────────────────────────────────

    def sub_bass_pattern(self, bars: int = 4, density: float = 0.5) -> list[NoteData]:
        """Generate sub bass pattern — steady root notes."""
        notes = []
        for bar in range(bars):
            for beat in range(4):
                t = bar * 4.0 + beat
                if beat == 0 or (beat == 2 and density > 0.5):
                    dur = 2.0 if density < 0.7 else 1.0
                    notes.append(NoteData(
                        pitch=self.note(0, 1),  # low root
                        start_time=t,
                        duration=dur,
                        velocity=110,
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
        """Generate dubstep-style rhythmic grid.

        Returns: [(time_beats, duration_beats, velocity)]
        """
        events = []
        for bar in range(bars):
            base = bar * 4.0
            # Core dubstep rhythm — emphasize off-beats
            grid = [
                (0.0, 0.75, 120),   # beat 1
                (0.75, 0.25, 90),   # syncopation
                (1.5, 0.5, 100),    # and-of-2
                (2.0, 0.5, 115),    # beat 3
                (2.75, 0.25, 85),   # syncopation
                (3.0, 0.5, 105),    # beat 4
                (3.5, 0.25, 80),
                (3.75, 0.25, 95),   # pickup
            ]
            for t, d, v in grid:
                if t / 4.0 < density or t == 0:
                    events.append((base + t, d, v))
        return events

    # ── Lead Pattern ─────────────────────────────────────────────────────

    def lead_pattern(self, bars: int = 4, style: str = "melodic") -> list[NoteData]:
        """Generate lead melody pattern."""
        notes = []
        # Simple melodic contour using scale degrees
        melody = [0, 2, 4, 5, 4, 2, 3, 1, 0, 4, 5, 6, 4, 2, 0, 0]
        for bar in range(bars):
            for i in range(4):
                idx = (bar * 4 + i) % len(melody)
                degree = melody[idx]
                t = bar * 4.0 + i
                notes.append(NoteData(
                    pitch=self.note(degree, 3),
                    start_time=t,
                    duration=0.75,
                    velocity=90 + (10 if i == 0 else 0),
                ))
        return notes

    # ── Pad Pattern ──────────────────────────────────────────────────────

    def pad_pattern(self, bars: int = 4) -> list[NoteData]:
        """Generate pad chord pattern — long sustained notes."""
        notes = []
        # Simple chord progression: i - VI - III - VII
        chords = [
            [0, 2, 4],  # i (root triad)
            [5, 0, 2],  # VI
            [2, 4, 6],  # III
            [6, 1, 3],  # VII
        ]
        for bar in range(bars):
            chord = chords[bar % len(chords)]
            for degree in chord:
                notes.append(NoteData(
                    pitch=self.note(degree, 3),
                    start_time=bar * 4.0,
                    duration=4.0,
                    velocity=70,
                ))
        return notes

    # ── Drum Patterns (MIDI) ────────────────────────────────────────────

    def kick_pattern(self, bars: int = 4, style: str = "standard") -> list[NoteData]:
        """Generate kick pattern. Uses GM MIDI note 36 (C1) for kick."""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            if style == "halftime":
                notes.append(NoteData(36, base, 0.5, 127))
                notes.append(NoteData(36, base + 3.0, 0.5, 100))
            elif style == "dubstep":
                notes.append(NoteData(36, base, 0.5, 127))
                if bar % 2 == 0:
                    notes.append(NoteData(36, base + 2.5, 0.25, 95))
            else:  # standard
                for beat in [0, 2]:
                    notes.append(NoteData(36, base + beat, 0.5, 120))
        return notes

    def snare_pattern(self, bars: int = 4, style: str = "halftime") -> list[NoteData]:
        """Generate snare pattern. MIDI note 38 (D1)."""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            if style == "halftime":
                notes.append(NoteData(38, base + 2.0, 0.5, 120))
            elif style == "dubstep":
                notes.append(NoteData(38, base + 2.0, 0.5, 127))
                if bar % 4 == 3:  # fill on last bar
                    notes.append(NoteData(38, base + 3.5, 0.25, 100))
                    notes.append(NoteData(38, base + 3.75, 0.25, 110))
            else:
                for beat in [1, 3]:
                    notes.append(NoteData(38, base + beat, 0.5, 115))
        return notes

    def hat_pattern(self, bars: int = 4, density: float = 0.6) -> list[NoteData]:
        """Generate hi-hat pattern. Closed=42, Open=46."""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            for eighth in range(8):
                t = base + eighth * 0.5
                if eighth / 8.0 < density:
                    vel = 90 if eighth % 2 == 0 else 65
                    midi_note = 46 if (eighth == 4 and bar % 2 == 0) else 42
                    notes.append(NoteData(midi_note, t, 0.25, vel))
        return notes

    def full_drum_pattern(self, bars: int = 4, style: str = "dubstep",
                          hat_density: float = 0.6) -> list[NoteData]:
        """Combined drum pattern — kick + snare + hats."""
        notes = []
        notes.extend(self.kick_pattern(bars, style))
        notes.extend(self.snare_pattern(bars, "halftime" if style == "dubstep" else style))
        notes.extend(self.hat_pattern(bars, hat_density))
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

    Complete workflow:
    1. Parse SongDNA or generate from track name
    2. Create Ableton session (tracks, routing, tempo)
    3. Load Serum 2 on each synth track
    4. Configure Serum presets per track role
    5. Program MIDI clips from DNA patterns
    6. Load drum samples into audio tracks
    7. Set up FX chains (return tracks)
    8. Configure sends & routing
    9. Set up mix automation
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
        """Build session setup from DNA."""
        session = SessionSetup(
            name=dna.name,
            bpm=dna.bpm,
            key=dna.key,
            scale=dna.scale,
            total_bars=dna.total_bars,
        )

        # ── Synth Tracks ───────────────────────────────────────────
        # Sub bass
        session.tracks.append(TrackSetup(
            name="SUB BASS",
            type="midi",
            color="dubforge_1",
            instrument="serum2",
            preset=BASS_TYPE_TO_PRESET.get("sub", "DUBFORGE_SUB_BASS"),
            volume=0.85,
            group="BASS",
        ))

        # Mid bass (primary)
        primary_bass = dna.bass.primary_type if hasattr(dna, 'bass') else "growl"
        session.tracks.append(TrackSetup(
            name="MID BASS",
            type="midi",
            color="dubforge_2",
            instrument="serum2",
            preset=BASS_TYPE_TO_PRESET.get(primary_bass, "DUBFORGE_GROWL_BASS"),
            volume=0.80,
            group="BASS",
        ))

        # Lead
        session.tracks.append(TrackSetup(
            name="LEAD",
            type="midi",
            color="dubforge_3",
            instrument="serum2",
            preset=LEAD_TYPE_TO_PRESET.get("screech", "DUBFORGE_SCREECH_LEAD"),
            volume=0.70,
        ))

        # Pad
        pad_type = dna.atmosphere.pad_type if hasattr(dna, 'atmosphere') else "dark"
        session.tracks.append(TrackSetup(
            name="PAD",
            type="midi",
            color="purple",
            instrument="serum2",
            preset=PAD_TYPE_TO_PRESET.get(pad_type, "DUBFORGE_DARK_PAD"),
            volume=0.55,
        ))

        # ── Drum Tracks ────────────────────────────────────────────

        # Drums (MIDI for programming, could be Drum Rack in Ableton)
        session.tracks.append(TrackSetup(
            name="DRUMS",
            type="midi",
            color="orange",
            instrument="drum_rack",
            volume=0.85,
        ))

        # ── Audio Tracks (for samples) ────────────────────────────

        session.tracks.append(TrackSetup(
            name="DRUM SAMPLES",
            type="audio",
            color="orange",
            volume=0.80,
        ))

        session.tracks.append(TrackSetup(
            name="FX AUDIO",
            type="audio",
            color="cyan",
            volume=0.65,
        ))

        # ── Return Tracks ─────────────────────────────────────────
        session.return_tracks = ["REVERB", "DELAY", "DISTORTION"]

        # ── Scenes (from arrangement) ─────────────────────────────
        if hasattr(dna, 'arrangement') and dna.arrangement:
            session.scenes = [s.name for s in dna.arrangement]
        else:
            session.scenes = ["INTRO", "BUILD", "DROP 1", "BREAK",
                              "BUILD 2", "DROP 2", "OUTRO"]

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
        """Generate all MIDI patterns from DNA."""
        bars = dna.total_bars if hasattr(dna, 'total_bars') else 16
        clip_bars = min(bars, 8)  # Clip length (looped for longer sections)

        patterns = {}

        # Sub bass
        density = dna.bass.sub_weight if hasattr(dna, 'bass') else 0.6
        patterns["sub_bass"] = pg.sub_bass_pattern(clip_bars, density)

        # Mid bass
        bass_type = dna.bass.primary_type if hasattr(dna, 'bass') else "growl"
        patterns["mid_bass"] = pg.mid_bass_pattern(clip_bars, bass_type, 0.7)

        # Lead
        patterns["lead"] = pg.lead_pattern(clip_bars, "melodic")

        # Pad
        patterns["pad"] = pg.pad_pattern(clip_bars)

        # Drums
        hat_subdiv = dna.drums.hat_density if hasattr(dna, 'drums') else 16
        hat_density = min(hat_subdiv / 32.0, 1.0)  # Normalize subdivisions to 0-1
        patterns["drums"] = pg.full_drum_pattern(clip_bars, "dubstep", hat_density)

        # Individual drum parts
        patterns["kick"] = pg.kick_pattern(clip_bars, "dubstep")
        patterns["snare"] = pg.snare_pattern(clip_bars, "halftime")
        patterns["hats"] = pg.hat_pattern(clip_bars, hat_density)

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
        """Apply DNA-specific parameter tweaks on top of preset."""
        if not hasattr(dna, 'bass'):
            return

        if "BASS" in track.name.upper():
            # Apply DNA bass parameters
            if hasattr(dna.bass, 'fm_depth'):
                ctrl.set_osc_b_level(dna.bass.fm_depth * 0.8)
            if hasattr(dna.bass, 'distortion'):
                ctrl.set_distortion(True, amount=dna.bass.distortion)
            if hasattr(dna.bass, 'filter_cutoff'):
                ctrl.set_filter1_cutoff(dna.bass.filter_cutoff)

        elif "LEAD" in track.name.upper():
            if hasattr(dna, 'lead') and hasattr(dna.lead, 'brightness'):
                ctrl.set_filter1_cutoff(0.3 + dna.lead.brightness * 0.6)

        elif "PAD" in track.name.upper():
            if hasattr(dna, 'atmosphere') and hasattr(dna.atmosphere, 'reverb_decay'):
                decay = min(dna.atmosphere.reverb_decay / 5.0, 1.0)
                ctrl.set_reverb(True, size=decay * 0.8, mix=0.35)

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
        """Set up return tracks and sends."""
        print(f"\n  ◆ Setting up FX routing...")

        # Configure sends from synth tracks to returns
        reverb_send = 0  # First return = reverb
        delay_send = 1   # Second return = delay

        for track_setup in session.tracks:
            if track_setup.name not in self._track_indices:
                continue
            track_idx = self._track_indices[track_setup.name]

            # Different send levels per track type
            if "PAD" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send, 0.45)
                self.bridge.set_track_send(track_idx, delay_send, 0.15)
            elif "LEAD" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send, 0.25)
                self.bridge.set_track_send(track_idx, delay_send, 0.20)
            elif "MID BASS" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send, 0.10)
            elif "SUB" in track_setup.name:
                pass  # No reverb on sub!
            elif "DRUM" in track_setup.name:
                self.bridge.set_track_send(track_idx, reverb_send, 0.12)

        print(f"  ✓ FX routing configured")

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL: Mix Settings
    # ═══════════════════════════════════════════════════════════════════════

    def _apply_mix_settings(self, session: SessionSetup, dna):
        """Apply DNA-driven mix settings."""
        print(f"\n  ◆ Applying mix settings...")

        if hasattr(dna, 'mix'):
            # Master volume
            self.bridge.set_master_volume(0.85)

        # Set stereo width via panning
        for track_setup in session.tracks:
            if track_setup.name not in self._track_indices:
                continue
            track_idx = self._track_indices[track_setup.name]

            # Center bass
            if "SUB" in track_setup.name:
                self.bridge.set_track_pan(track_idx, 0.0)
            elif "MID BASS" in track_setup.name:
                self.bridge.set_track_pan(track_idx, 0.0)
            # Slight spread on lead
            elif "LEAD" in track_setup.name:
                pass  # Leave centered, Serum handles width

        print(f"  ✓ Mix settings applied")

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
