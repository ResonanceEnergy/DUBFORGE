# pyright: basic
"""DUBFORGE — Phase 1: IDEA → MANDATE

4-stage pipeline that produces a complete SongMandate
with all sounds, presets, and production plan for Phase 2 (ARRANGE).

    Stage 1: THE TOTAL RECIPE (compounding: each step feeds the next)
             1A Constants — PHI, FIBONACCI, A4_432
             1B DNA — variation_engine → SongDNA (153 fields)
             1C Harmony — chord progression (harmonic roadmap)
             1D Freq table — key/scale → 5-octave lookup
             1E Palette intent — DNA sub-DNAs → timbral goals
             1F Template config — genre profile + Serum 2 spec
             1G Production recipe — quality targets + Fibonacci checkpoints
             1H Arrangement — section structure + energy from DNA
    Stage 2: MIDI SEQUENCES
             2A MIDI — section-aware MIDI for all stems + ghost kick
             2B Galactia FX — pre-load FX samples
    Stage 3: SYNTH FACTORY — design + render all synth audio
             3A WT intake (Galactia + phi_core)
             3B WT generation (DNA-driven FM/harmonic/growl)
             3C Modulation routes (Serum 2 mod matrix per stem)
             3D FX chains (Ableton FX rack per stem)
             3E WT morphing (mood-driven)
             3F Serum 2 presets (build + DNA mutation)
             3G Synthesis (9× numpy render)
             3H Stem config + preset mutation
             3I ALS build (ghost kick + 10 Serum 2 tracks)
             3I+ Audio manifest (4E stem entries)
             3J Live bounce (optional Ableton export)
             3K Collect + production skeleton
    Stage 4: DRUM FACTORY — samples, rack, loops (NO synth content)
             4A Drum selection (DNA-guided from Galactia)
             4B Galactia zone mapping
             4C Drum processing (dynamics/saturation/EQ)
             4D 128 Rack build (drums + FX only)
             4E Drum loop MIDI (all section types)
             4F Pattern factory (drum patterns per section + 5E manifest)
             4G ALS build + bounce + collect

Output: SongMandate — every ingredient Phase 2 needs to place in the timeline.

Dojo methodology (ill.Gates / Producer Dojo):
    - 128 Rack: organized sample slots with Fibonacci zone distribution
    - The Approach: Collect → Design → Sketch → Finish
    - PSBS: Phase-Separated Bass System for mixing
    - Drums from Galactia catalog (real samples only — no synthesis)
    - Collect samples before sound design so presets target real material
    - Sound design before synthesis so renders use designed patches/FX
    - Serum 2 integration: preset design, modulation, automation
    - Ableton FX: saturation, sidechain, stereo, reverb/delay, wave folding
"""

from __future__ import annotations

import logging
import os
import random
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.ableton_bridge import AbletonBridge

import numpy as np
import yaml

from engine.config_loader import PHI, FIBONACCI
from engine.variation_engine import (
    ArrangementSection,
    BassDNA,
    DrumDNA,
    FxDNA,
    LeadDNA,
    MixDNA,
    SongBlueprint,
    SongDNA,
    VariationEngine,
    AtmosphereDNA,
    SCALE_INTERVALS,
    NOTES,
)

# ── Stage 1 modules (arrangement + recipe + template) ──
from engine.arrangement_sequencer import ArrangementTemplate, SectionDef

# RCO removed — energy derived directly from arrangement section.intensity

try:
    from engine.recipe_book import RecipeBook, select_recipe as rb_select_recipe
    _HAS_RECIPE_BOOK = True
except Exception:
    _HAS_RECIPE_BOOK = False

# template_generator — removed (dead import, never called in pipeline)

# ── Stage 3 modules (wavetable generation + morphing + Serum 2 presets) ──
try:
    from engine.wavetable_pack import (
        generate_fm_ratio_sweep,
        generate_harmonic_sweep,
        generate_growl_vowel_pack,
        generate_morph_pack,
    )
    _HAS_WT_PACK = True
except Exception:
    _HAS_WT_PACK = False

try:
    from engine.wavetable_morph import (
        morph_wavetable,
        MorphPreset,
    )
    _HAS_WT_MORPH = True
except Exception:
    _HAS_WT_MORPH = False

try:
    from engine.growl_resampler import growl_resample_pipeline
    _HAS_GROWL_RESAMPLE = True
except Exception:
    _HAS_GROWL_RESAMPLE = False

try:
    from engine.phi_core import (
        phi_harmonic_series,
        generate_frame as phi_generate_frame,
        phi_amplitude_curve,
        morph_frames as phi_morph_frames,
    )
    _HAS_PHI_CORE = True
except Exception:
    _HAS_PHI_CORE = False

try:
    from engine.serum2_preset import (
        build_all_presets as s2_build_all_presets,
        get_preset_state_map as s2_get_preset_state_map,
        SerumPreset,
    )
    _HAS_SERUM2_PRESET = True
except Exception:
    _HAS_SERUM2_PRESET = False

try:
    from engine.als_generator import (
        ALSMidiNote,
        ALSMidiClip,
        ALSTrack as _ALSTrack,
        ALSProject as _ALSProject,
        ALSClipInfo as _ALSClipInfo,
        ALSDrumPad as _ALSDrumPad,
        ALSAutomation as _ALSAutomation,
        ALSAutomationPoint as _ALSAutomationPoint,
        ALSScene as _ALSScene,
        ALSCuePoint as _ALSCuePoint,
        write_als as _write_als,
    )
    _HAS_ALS_GEN = True
except Exception:
    _HAS_ALS_GEN = False

try:
    from engine.midi_pattern_db import pick_pattern as _pick_pattern, pattern_to_notes as _pattern_to_notes
    _HAS_PATTERN_DB = True
except Exception:
    _HAS_PATTERN_DB = False

log = logging.getLogger("dubforge.phase_one")

SR = 48000
BEATS_PER_BAR = 4  # 4/4 time — all DUBFORGE output is strictly 4/4


# ═══════════════════════════════════════════════════════════════════════════
#  DATA MODEL — SongMandate
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DrumKit:
    """Selected drum samples — from Galactia or synth fallback."""
    kick: np.ndarray | None = None
    snare: np.ndarray | None = None
    hat_closed: np.ndarray | None = None
    hat_open: np.ndarray | None = None
    clap: np.ndarray | None = None
    crash: np.ndarray | None = None
    ride: np.ndarray | None = None
    perc: np.ndarray | None = None
    # Source tracking
    kick_source: str = ""
    snare_source: str = ""
    hat_closed_source: str = ""
    hat_open_source: str = ""
    clap_source: str = ""
    crash_source: str = ""
    ride_source: str = ""
    perc_source: str = ""


@dataclass
class BassArsenal:
    """Pre-rendered bass one-shots keyed by type and frequency."""
    # sounds[bass_type] = np.ndarray (rendered at root freq)
    sounds: dict[str, np.ndarray] = field(default_factory=dict)
    sub: np.ndarray | None = None
    reese: np.ndarray | None = None
    rotation_order: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class LeadPalette:
    """Pre-rendered lead notes at multiple pitches."""
    # notes[freq_hz] = np.ndarray
    screech: dict[float, np.ndarray] = field(default_factory=dict)
    pluck: dict[float, np.ndarray] = field(default_factory=dict)
    fm_lead: dict[float, np.ndarray] = field(default_factory=dict)
    # Chord stabs at root
    chord_l: np.ndarray | None = None
    chord_r: np.ndarray | None = None
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class AtmosphereKit:
    """Pre-rendered pads, drones, and noise beds."""
    dark_pad: np.ndarray | None = None
    lush_pad: np.ndarray | None = None
    drone: np.ndarray | None = None
    noise_bed: np.ndarray | None = None
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class FxKit:
    """Pre-rendered transition FX — from Galactia or synthesized."""
    riser: np.ndarray | None = None
    boom: np.ndarray | None = None
    hit: np.ndarray | None = None
    tape_stop: np.ndarray | None = None
    pitch_dive: np.ndarray | None = None
    rev_crash: np.ndarray | None = None
    stutter: np.ndarray | None = None
    gate_chop: np.ndarray | None = None
    # Galactia FX samples (falling, rising, shepard tones)
    fx_falling: list[np.ndarray] = field(default_factory=list)
    fx_rising: list[np.ndarray] = field(default_factory=list)
    shepard_tones: list[np.ndarray] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class VocalKit:
    """Pre-rendered vocal chops per vowel."""
    # chops[vowel] = np.ndarray
    chops: dict[str, np.ndarray] = field(default_factory=dict)
    vowels: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class WavetableKit:
    """Selected wavetables from Galactia neuro collection."""
    # frames[name] = list of np.ndarray (wavetable frames)
    frames: dict[str, list[np.ndarray]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class GalactiaFxSamples:
    """Raw FX samples from Galactia before processing."""
    risers: list[np.ndarray] = field(default_factory=list)
    impacts: list[np.ndarray] = field(default_factory=list)
    reverses: list[np.ndarray] = field(default_factory=list)
    falling: list[np.ndarray] = field(default_factory=list)
    rising: list[np.ndarray] = field(default_factory=list)
    shepard: list[np.ndarray] = field(default_factory=list)
    buildups: list[np.ndarray] = field(default_factory=list)
    sources: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class MelodyKit:
    """Pre-rendered melody lines — lead melody + arp patterns."""
    lead_melody: np.ndarray | None = None       # rendered lead melody audio
    lead_melody_notes: list[Any] = field(default_factory=list)  # MelodyNote list for MIDI
    arp_patterns: dict[str, np.ndarray] = field(default_factory=dict)  # type → audio
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class WobbleBassKit:
    """Pre-rendered wobble bass patterns for drop sections."""
    patterns: dict[str, np.ndarray] = field(default_factory=dict)  # type → audio
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class RiddimBassKit:
    """Pre-rendered riddim patterns for rhythmic bass sections."""
    patterns: dict[str, np.ndarray] = field(default_factory=dict)  # type → audio
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class GrowlKit:
    """Growl-resampled wavetable frames for mid-bass textures."""
    frames: list[np.ndarray] = field(default_factory=list)  # single-cycle frames
    source_type: str = ""
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class DrumLoopKit:
    """Audio loops built from DrumKit samples — one per section type."""
    patterns: dict[str, np.ndarray] = field(default_factory=dict)  # section_type → audio
    pattern_bars: dict[str, int] = field(default_factory=dict)     # section_type → bar count
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class RackMidiMap:
    """MIDI note assignments for every populated 128 Rack zone.

    Each entry: zone_num → {note: int, name: str, zone: str}
    Standard Drum Rack mapping: MIDI note == zone number (C-2 = 0).
    """
    note_map: dict[int, dict[str, Any]] = field(default_factory=dict)
    zone_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)  # zone → (start, end)


@dataclass
class LoopMidiMap:
    """A MIDI pattern that triggers drum rack pads to play a loop.

    hits: list of {beat: float, note: int, velocity: float, duration: float}
    """
    name: str = ""
    section_type: str = ""
    n_bars: int = 4
    hits: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Rack128:
    """The 128 Rack — organized sample/sound slots (Dojo methodology).

    Fibonacci zone distribution (matches dojo.py build_128_rack):
        Zones  0-7   (8 slots):  Sub bass
        Zones  8-15  (8 slots):  Low bass
        Zones 16-28  (13 slots): Mid bass (growls, wobbles, riddim)
        Zones 29-36  (8 slots):  High bass (fizz, harmonics)
        Zones 37-49  (13 slots): Kicks
        Zones 50-62  (13 slots): Snares / claps
        Zones 63-70  (8 slots):  Hi-hats
        Zones 71-83  (13 slots): Percussion
        Zones 84-96  (13 slots): FX / risers
        Zones 97-104 (8 slots):  Melodic (melody, arps, chords)
        Zones 105-112 (8 slots): Atmosphere (pads, drones)
        Zones 113-117 (5 slots): Vocal
        Zones 118-122 (5 slots): Transitions
        Zones 123-127 (5 slots): Utility (wavetables, growl frames)
    """
    slots: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_manifest: list[dict[str, Any]] = field(default_factory=list)
    zone_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class StemSynthConfig:
    """Per-stem synthesis configuration — compiled from S1–S3 data.

    This is the 4A output: everything needed to build a Serum 2 preset,
    write MIDI, and configure the FX chain for one stem.
    """
    stem_name: str                                   # "sub_bass", "lead", etc.
    stem_group: str                                  # "bass" | "lead" | "pad"
    # S3C: modulation
    mod_matrix: list = field(default_factory=list)    # list[ModulationRoute]
    lfos: list = field(default_factory=list)          # list[LFOPreset]
    # S3D: FX chain components
    saturation: Any = None                           # SatConfig
    sidechain: Any = None                            # SidechainPreset
    stereo: Any = None                               # StereoPreset
    reverb: Any = None                               # ReverbDelayPreset
    wave_folder: Any = None                          # WaveFolderPatch
    pitch_auto: Any = None                           # PitchAutoPreset
    # S3B/S3E: wavetable data
    wavetable_frames: list = field(default_factory=list)
    morph_frames: list | None = None
    # S3F: base Serum 2 preset
    base_preset_name: str = ""
    base_preset: Any = None                          # SerumPreset
    # S1: DNA identity
    root_midi: int = 36
    bpm: float = 150.0
    key: str = "F"
    scale: str = "minor"
    mood: str = "dark"
    style: str = "dubstep"
    energy: float = 0.7


# ── Audio Manifest: planned vs delivered audio file tracking ──

@dataclass
class AudioFileSpec:
    """Single expected audio file in the manifest."""
    name: str             # e.g. "sub_bass", "drop_sub_bass"
    stem_type: str        # "stem_4e" | "pattern_5e" | "drum" | "loop" | "fx"
    function: str         # human description: "Sub bass Serum 2 wet bounce"
    stage: str            # "4E" | "5E" | "2A" etc
    path: Path | None = None       # expected output path (set when known)
    delivered: bool = False        # True once file exists + validated
    file_size: int = 0             # bytes, filled after delivery
    sample_rate: int = 48000
    bit_depth: int = 24
    format: str = "WAV"


@dataclass
class AudioManifest:
    """Complete inventory of expected audio outputs from Phase 1.

    Built at end of Stage 1 (planning).  Validated after 4E/5E (delivery).
    """
    files: list[AudioFileSpec] = field(default_factory=list)

    # ── Convenience accessors ──
    @property
    def total(self) -> int:
        return len(self.files)

    @property
    def delivered_count(self) -> int:
        return sum(1 for f in self.files if f.delivered)

    @property
    def pending(self) -> list[AudioFileSpec]:
        return [f for f in self.files if not f.delivered]

    @property
    def by_stage(self) -> dict[str, list[AudioFileSpec]]:
        result: dict[str, list[AudioFileSpec]] = {}
        for f in self.files:
            result.setdefault(f.stage, []).append(f)
        return result

    def mark_delivered(self, name: str, path: Path, file_size: int = 0) -> bool:
        """Mark a file as delivered after validating it exists on disk.

        Returns True if found in manifest AND file exists.
        """
        for f in self.files:
            if f.name == name:
                if path and Path(path).exists():
                    f.delivered = True
                    f.path = path
                    f.file_size = file_size or Path(path).stat().st_size
                else:
                    log.warning("MANIFEST: %s not found on disk at %s", name, path)
                    f.delivered = False
                return True
        return False

    def summary(self) -> str:
        lines = [f"Audio Manifest: {self.delivered_count}/{self.total} delivered"]
        for stage, specs in sorted(self.by_stage.items()):
            done = sum(1 for s in specs if s.delivered)
            lines.append(f"  {stage}: {done}/{len(specs)}")
            for s in specs:
                mark = "✓" if s.delivered else "✗"
                size = f" ({s.file_size / 1024 / 1024:.1f} MB)" if s.file_size else ""
                lines.append(f"    {mark} {s.name} — {s.function}{size}")
        return "\n".join(lines)


@dataclass
class SongMandate:
    """Complete output of Phase 1 — everything Phase 2 (ARRANGE) needs."""

    # ── Identity ──
    dna: SongDNA = field(default_factory=lambda: SongDNA(
        name="untitled", style="dubstep", theme="", mood_name="dark",
        tags=[], seed=0, key="F", scale="minor", bpm=140, root_freq=43.65,
    ))

    # ── Timing constants ──
    beat_s: float = 0.0
    bar_s: float = 0.0
    freq_table: dict[str, float] = field(default_factory=dict)

    # ── Section map ──
    sections: dict[str, int] = field(default_factory=dict)
    total_bars: int = 0
    total_samples: int = 0

    # ── Arrangement + energy (Stage 2) ──
    arrangement_template: Any = None       # ArrangementTemplate from arrangement_sequencer

    # ── Production recipe (Stage 1D) ──
    production_recipe: Any = None          # Recipe selection from recipe_book

    # ── Sound palette (all rendered audio) ──
    drums: DrumKit = field(default_factory=DrumKit)
    drum_loops: DrumLoopKit = field(default_factory=DrumLoopKit)
    bass: BassArsenal = field(default_factory=BassArsenal)
    leads: LeadPalette = field(default_factory=LeadPalette)
    atmosphere: AtmosphereKit = field(default_factory=AtmosphereKit)
    fx: FxKit = field(default_factory=FxKit)
    vocals: VocalKit = field(default_factory=VocalKit)
    wavetables: WavetableKit = field(default_factory=WavetableKit)
    galactia_fx: GalactiaFxSamples = field(default_factory=GalactiaFxSamples)

    # ── Galactia zone map (raw audio mapped to Rack128 zones) ──
    galactia_zone_map: Any = None          # GalactiaZoneMap from galatcia.py

    # ── Harmonic + melodic content ──
    chord_progression: Any = None          # ChordProgression from chord_progression.py
    melody: MelodyKit = field(default_factory=MelodyKit)
    wobble_bass: WobbleBassKit = field(default_factory=WobbleBassKit)
    riddim_bass: RiddimBassKit = field(default_factory=RiddimBassKit)
    growl_textures: GrowlKit = field(default_factory=GrowlKit)

    # ── Infrastructure ──
    rack_128: Rack128 = field(default_factory=Rack128)
    rack_midi_map: RackMidiMap = field(default_factory=RackMidiMap)
    loop_midi_maps: list[LoopMidiMap] = field(default_factory=list)
    groove_template: str = "dubstep_halftime"
    design_intent: dict[str, Any] = field(default_factory=dict)

    # ── Task list for Phase 2 ──
    arrange_tasks: list[str] = field(default_factory=list)
    quality_targets: dict[str, Any] = field(default_factory=dict)

    # ── Config source ──
    yaml_config: dict[str, Any] | None = None

    # ── Sound design output (Stage 3) ──
    modulation_routes: dict[str, Any] = field(default_factory=dict)
    fx_chains: dict[str, Any] = field(default_factory=dict)
    wavetable_packs: list[tuple[str, list[Any]]] = field(default_factory=list)
    morph_wavetables: dict[str, list[Any]] = field(default_factory=dict)
    serum2_presets: dict[str, Any] = field(default_factory=dict)
    serum2_state_map: dict[str, tuple[bytes, bytes]] = field(default_factory=dict)

    # ── Stage 4: Serum 2 Sound Factory outputs ──
    stem_configs: dict[str, Any] = field(default_factory=dict)
    midi_sequences: dict[str, list] = field(default_factory=dict)
    render_als_path: Any = None
    audio_clips: dict[str, Any] = field(default_factory=dict)
    production_als_path: Any = None

    # ── Stage 5: Render Factory outputs ──
    render_patterns: dict[str, Any] = field(default_factory=dict)   # section→zone→MIDI
    stage5_als_path: Any = None
    stage5_renders: dict[str, Any] = field(default_factory=dict)    # WAV stems catalog

    # ── Audio manifest (Stage 3 planning → Stage 4E/5E delivery) ──
    audio_manifest: AudioManifest = field(default_factory=AudioManifest)

    # ── Audit trail ──
    phase_log: list[dict[str, Any]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
#  YAML CONFIG INGESTION
# ═══════════════════════════════════════════════════════════════════════════

def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a DUBFORGE YAML track config."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def yaml_to_blueprint(cfg: dict[str, Any]) -> SongBlueprint:
    """Convert YAML config → SongBlueprint for the VariationEngine."""
    gl = cfg.get("global", {})

    # Parse key from YAML format "Ab_minor" → key="Ab", scale="minor"
    key_str = gl.get("key", "F_minor")
    parts = key_str.split("_", 1)
    key = parts[0] if parts else "F"
    scale = parts[1] if len(parts) > 1 else "minor"

    # Parse arrangement from YAML
    arrangement_raw = cfg.get("arrangement", [])
    arrangement = []
    for sec in arrangement_raw:
        arrangement.append(ArrangementSection(
            name=sec.get("name", "section").lower(),
            bars=sec.get("bars", 8),
            energy={"intro": 0.3, "verse": 0.4, "build": 0.6, "drop": 1.0,
                     "break": 0.3, "bridge": 0.5, "vip": 1.0, "outro": 0.2
                     }.get(sec.get("type", "intro"), 0.5),
            elements=[],
        ))

    name = cfg.get("template_name", gl.get("name", "untitled"))

    bp = SongBlueprint(
        name=name,
        style=gl.get("style", "dubstep"),
        theme=gl.get("theme", ""),
        mood=gl.get("mood", "dark"),
        sound_style=gl.get("sound_style", ""),
        key=key,
        scale=scale,
        bpm=gl.get("bpm", 150),
        arrangement=arrangement if arrangement else None,  # type: ignore[arg-type]
    )
    return bp


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1a: ORACLE — DNA Generation
# ═══════════════════════════════════════════════════════════════════════════

def _oracle(
    blueprint: SongBlueprint | None,
    dna: SongDNA | None,
    yaml_config: dict[str, Any] | None,
) -> SongDNA:
    """Generate SongDNA from blueprint, YAML config, or existing DNA."""
    if dna is not None:
        return dna

    if yaml_config is not None and blueprint is None:
        blueprint = yaml_to_blueprint(yaml_config)

    if blueprint is None:
        blueprint = SongBlueprint(name="untitled")

    engine = VariationEngine()
    result = engine.forge_dna(blueprint)
    log.info("ORACLE: DNA forged — %s %s @ %d BPM", result.key, result.scale, result.bpm)
    return result


def _build_freq_table(dna: SongDNA) -> dict[str, float]:
    """Build frequency lookup table from DNA key and scale.

    Includes:
      - Standard scale degree × octave grid (5 octaves)
      - Phi-ratio harmony series: root × phi^n for fractal overtones
      - Planck × phi^n sub-bass ladder for sub-harmonic precision
      - Named shortcuts for quick access
    """
    intervals = SCALE_INTERVALS.get(dna.scale, [0, 2, 3, 5, 7, 8, 10])
    root = dna.root_freq

    def n(degree: int, octave: int) -> float:
        semi = intervals[degree % len(intervals)]
        return root * (2.0 ** (octave - 1)) * (2.0 ** (semi / 12.0))

    table: dict[str, float] = {}

    # ── Standard scale degree grid (5 octaves) ──
    for oct in range(1, 6):
        for deg in range(min(7, len(intervals))):
            label = f"d{deg}o{oct}"
            table[label] = n(deg, oct)

    # ── Phi-ratio harmony series: root × phi^n (fractal overtones) ──
    # These give the self-similar harmonic relationships from DOCTRINE
    for i in range(8):
        table[f"phi_{i}"] = root * (PHI ** i)

    # ── Planck × phi^n sub-bass ladder ──
    # Sub-harmonic precision targets from DOCTRINE's Planck-floor principle
    # Start from root and descend by phi ratios into sub territory
    for i in range(1, 5):
        table[f"planck_sub_{i}"] = root / (PHI ** i)

    # ── Fibonacci harmonic nodes ──
    # Frequencies at Fibonacci partial ratios (1, 1, 2, 3, 5, 8, 13...)
    for fib in FIBONACCI[:8]:
        if fib > 0:
            table[f"fib_{fib}"] = root * fib

    # ── Named shortcuts ──
    table["root"] = root
    table["sub"] = root
    table["bass"] = root * 2
    table["mid"] = root * 4
    table["high"] = root * 8
    table["phi_fifth"] = root * PHI          # ~golden interval
    table["phi_octave"] = root * PHI * PHI   # ~phi double

    return table


def _extract_sections(dna: SongDNA) -> dict[str, int]:
    """Extract section bar counts from DNA arrangement."""
    type_map: dict[str, list[ArrangementSection]] = {}
    for s in dna.arrangement:
        name_lower = s.name.lower()
        if any(w in name_lower for w in ("intro", "dawn")):
            sec_type = "intro"
        elif any(w in name_lower for w in ("build", "ascent")):
            sec_type = "build"
        elif any(w in name_lower for w in ("drop", "revelation", "transcendence")):
            sec_type = "drop"
        elif any(w in name_lower for w in ("break", "reflection", "stillness", "memory")):
            sec_type = "break"
        elif any(w in name_lower for w in ("bridge", "reverie")):
            sec_type = "bridge"
        elif any(w in name_lower for w in ("outro", "dusk")):
            sec_type = "outro"
        else:
            sec_type = name_lower
        type_map.setdefault(sec_type, []).append(s)

    result = {}
    for sec_type, sections in type_map.items():
        result[sec_type] = sum(s.bars for s in sections)

    for key in ("intro", "build", "drop", "break", "outro"):
        result.setdefault(key, 0)

    return result


def _build_arrangement_from_dna(dna: SongDNA) -> ArrangementTemplate:
    """Build ArrangementTemplate directly from DNA arrangement sections.

    Translates DNA element vocabulary into the _ELEMENT_STEMS vocabulary
    that Stage 4C uses to decide which synth stems are active per section.
    Each song gets a unique arrangement structure derived from its DNA —
    no hardcoded templates.
    """
    # Map DNA element names → _ELEMENT_STEMS-compatible names
    _DNA_TO_ELEMENTS: dict[str, list[str]] = {
        # Drums — no stem mapping, but kept for sidechain/pattern decisions
        "kick": ["drums_full", "sidechain"],
        "kick_lite": ["drums_light"],
        "kick_fade": ["drums_light"],
        "snare": ["drums_full", "sidechain"],
        "snare_roll": ["drums_building"],
        "hats": ["drums_full"],
        "hats_sparse": ["drums_light"],
        # Bass
        "sub": ["bass_sub", "sidechain"],
        "sub_long": ["bass_sub"],
        "sub_fade": ["bass_sub"],
        "bass": ["bass_heavy", "sidechain"],
        "bass_alt": ["bass_heavy"],
        "extra_bass": ["bass_weapon"],
        # Melodic
        "lead": ["lead"],
        "chords": ["chord"],
        "pad": ["pad"],
        "pad_fade": ["pad"],
        "plucks": ["pluck"],
        "pluck": ["pluck"],
        "arp": ["arp"],
        # Texture
        "drone": ["drone"],
        "noise_bed": ["noise"],
        "texture": ["ambient"],
        "ambient": ["ambient"],
        # FX / transitions
        "riser": ["riser"],
        "swell": ["riser"],
        "chops": ["vocal"],
        "vocal": ["vocal"],
        "noise": ["noise"],
        "reverb_fx": ["fx"],
        "fx": ["fx"],
        "fx_tail": ["fx_subtle"],
    }

    sections: list[SectionDef] = []
    for dna_sec in dna.arrangement:
        # Translate element vocabulary
        translated: list[str] = []
        seen: set[str] = set()
        for elem in dna_sec.elements:
            mapped = _DNA_TO_ELEMENTS.get(elem, [elem])
            for m in mapped:
                if m not in seen:
                    translated.append(m)
                    seen.add(m)

        sections.append(SectionDef(
            name=dna_sec.name,
            bars=dna_sec.bars,
            elements=translated,
            intensity=dna_sec.energy,
            bpm=dna.bpm,
        ))

    # Determine template type from style
    _type_map = {
        "dubstep": "weapon", "riddim": "weapon",
        "melodic": "emotive", "hybrid": "hybrid",
    }
    t_type = _type_map.get(dna.style, "weapon")

    return ArrangementTemplate(
        name=f"{dna.name}_ARRANGEMENT",
        template_type=t_type,
        bpm=dna.bpm,
        sections=sections,
        key=f"{dna.key}{dna.scale[0]}",
    )


def _sections_from_arrangement(template: ArrangementTemplate) -> dict[str, int]:
    """Build sections dict from arrangement_template — single source of truth.

    Collapses numbered sections (drop1, drop2 → drop) to match the
    simplified key format downstream code expects.
    """
    type_map: dict[str, int] = {}
    for s in template.sections:
        name_lower = s.name.lower()
        if any(w in name_lower for w in ("intro", "dawn")):
            sec_type = "intro"
        elif any(w in name_lower for w in ("build", "ascent")):
            sec_type = "build"
        elif any(w in name_lower for w in ("drop", "revelation", "transcendence")):
            sec_type = "drop"
        elif any(w in name_lower for w in ("break", "reflection", "stillness",
                                            "memory", "interlude", "breakdown")):
            sec_type = "break"
        elif any(w in name_lower for w in ("bridge", "reverie")):
            sec_type = "bridge"
        elif any(w in name_lower for w in ("outro", "dusk")):
            sec_type = "outro"
        elif any(w in name_lower for w in ("verse",)):
            sec_type = "verse"
        elif any(w in name_lower for w in ("expand", "transcend")):
            sec_type = "drop"
        else:
            sec_type = name_lower
        type_map[sec_type] = type_map.get(sec_type, 0) + s.bars

    for key in ("intro", "build", "drop", "break", "outro"):
        type_map.setdefault(key, 0)

    return type_map


# ─── Audio manifest builder (called end of Stage 1) ──────────────────────

# Human-readable function description per stem
_STEM_FUNCTIONS: dict[str, str] = {
    "sub_bass": "Sub bass — Serum 2 wet bounce (20-80 Hz foundation)",
    "mid_bass": "Mid bass — Serum 2 wet bounce (80-300 Hz body)",
    "neuro": "Neuro bass — Serum 2 wet bounce (growl/FM texture)",
    "wobble": "Wobble bass — Serum 2 wet bounce (LFO-modulated)",
    "riddim": "Riddim bass — Serum 2 wet bounce (minimal stab)",
    "lead": "Lead synth — Serum 2 wet bounce (FM screech melody)",
    "chords": "Chord synth — Serum 2 wet bounce (harmonic stabs)",
    "arps": "Arp synth — Serum 2 wet bounce (rhythmic sequence)",
    "pad": "Pad/atmosphere — Serum 2 wet bounce (evolving texture)",
    "supersaw": "Supersaw — Serum 2 wet bounce (stacked detuned)",
}


def _build_audio_manifest(safe_name: str = "dubforge") -> AudioManifest:
    """Build audio manifest with 4E stem entries.

    Only enumerates the 10 Serum 2 stem WAVs (3J bounce).
    5E pattern entries are added at Stage 4F when actual
    zone groups are known — no guessing.
    """
    manifest = AudioManifest()
    bounce_dir = Path("output") / safe_name / "bounces"

    for stem in ALL_SYNTH_STEMS:
        manifest.files.append(AudioFileSpec(
            name=stem,
            stem_type="stem_4e",
            function=_STEM_FUNCTIONS.get(stem, f"{stem} Serum 2 wet bounce"),
            stage="4E",
            path=bounce_dir / f"{stem}.wav",
        ))

    return manifest


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1b: DESIGN — Sound Palette Intent
# ═══════════════════════════════════════════════════════════════════════════

def _design_palette_intent(dna: SongDNA) -> dict[str, Any]:
    """Decide what the sound palette should contain based on DNA."""
    dd = dna.drums
    bd = dna.bass
    ld = dna.lead
    ad = dna.atmosphere
    fd = dna.fx
    energy = getattr(dna, "energy", 0.7)

    return {
        "drums": {
            "source": "galactia",
            "fallback": "synth",
            "kick_character": dd.kick_sample_category,
            "snare_character": dd.snare_sample_category,
            "hat_character": "bright" if dd.hat_brightness > 0.8 else "dark",
            "hat_density": dd.hat_density,
        },
        "bass": {
            "types_needed": [bd.primary_type, bd.secondary_type, bd.tertiary_type],
            "rotation": dna.bass_rotation[:7],
            "sub_weight": bd.sub_weight,
            "fm_depth": bd.fm_depth,
            "distortion": bd.distortion,
            "filter_cutoff": bd.filter_cutoff,
            "processing": {
                "unison_voices": 5 if energy < 0.9 else 7,
                "distortion_stages": 3,
                "ott": bd.ott_amount,
            },
        },
        "leads": {
            "use_screech": True,
            "use_fm": ld.use_fm,
            "use_additive": ld.use_additive,
            "brightness": ld.brightness,
            "chord_style": "supersaw",
            "filter_cutoff": getattr(ld, "supersaw_cutoff", 5500.0) / 10000.0,
            "resonance": 0.3,
        },
        "atmosphere": {
            "pad_type": ad.pad_type,
            "use_drone": True,
            "use_karplus_drone": ad.use_karplus_drone,
            "noise_bed": ad.noise_bed_type,
            "reverb_amount": ad.reverb_decay / 10.0,
        },
        "fx": {
            "riser_start_freq": fd.riser_start_freq,
            "riser_end_freq": fd.riser_end_freq,
            "riser_intensity": fd.riser_intensity,
            "impact_intensity": fd.impact_intensity,
            "stutter_rate": fd.stutter_rate,
            "vocal_chop_distortion": fd.vocal_chop_distortion,
            "source": "galactia",
        },
        "vocals": {
            "vowels": dna.chop_vowels or ["ah", "oh", "ee", "oo"],
            "distortion": fd.vocal_chop_distortion,
        },
        "wavetables": {
            "source": "galactia",
            "morph_type": "phi_spline",
        },
    }


def _build_chord_progression(dna: SongDNA) -> Any:
    """Select and build a chord progression matching the DNA mood/style.

    Runs during DESIGN because it's structural — melody, arps, and bass
    patterns all derive from this harmonic roadmap.

    Priority: dna.lead.chord_progression (from audio analysis) > mood/style preset
    """
    try:
        from engine.chord_progression import build_progression, ALL_PRESETS

        # ── Audio-extracted chord progression takes priority ──
        # If reference intake already extracted real chord degrees from the track,
        # build the progression directly from those — no preset matching.
        audio_degrees = getattr(dna.lead, "chord_progression", [])
        if audio_degrees and len(audio_degrees) >= 2:
            # Build a custom progression from the actual detected degrees
            _DEGREE_TO_ROMAN = {0: "I", 1: "II", 2: "III", 3: "IV",
                                4: "V", 5: "VI", 6: "VII"}
            roman_seq = [_DEGREE_TO_ROMAN.get(d % 7, "I") for d in audio_degrees[:8]]
            try:
                prog = build_progression(
                    name="audio_extracted",
                    key=dna.key,
                    scale_type=dna.scale,
                    roman_sequence=roman_seq,
                    bpm=dna.bpm,
                )
                log.info("DESIGN CHORDS (audio-direct): degrees=%s → %s (%s %s @ %d BPM)",
                         audio_degrees, roman_seq, dna.key, dna.scale, dna.bpm)
                return prog
            except Exception as exc:
                log.warning("DESIGN CHORDS: direct build failed (%s), trying preset match", exc)

            # Fallback: find closest preset if direct build fails
            best_preset = None
            best_score = -1
            for pname, pfactory in ALL_PRESETS.items():
                try:
                    p = pfactory()
                    p_degrees = []
                    for c in p.chords:
                        rdeg = c.get("root_degree", 0) if isinstance(c, dict) else getattr(c, "root_degree", 0)
                        p_degrees.append(rdeg)
                    overlap = len(set(audio_degrees[:4]) & set(p_degrees[:4]))
                    if overlap > best_score:
                        best_score = overlap
                        best_preset = pname
                except Exception:
                    continue
            if best_preset is None:
                best_preset = "WEAPON_DARK"
            prog = ALL_PRESETS[best_preset]()
            prog.key = dna.key
            prog.scale_type = dna.scale
            prog.bpm = dna.bpm
            log.info("DESIGN CHORDS (audio-preset): %s → degrees=%s (%s %s @ %d BPM)",
                     best_preset, audio_degrees, dna.key, dna.scale, dna.bpm)
            return prog

        # ── Fallback: mood/style preset selection ──
        mood = getattr(dna, "mood_name", "dark").lower()
        style = dna.style.lower()

        # Mood/style → preset priority
        MOOD_PRESET_MAP = {
            "dark": ["WEAPON_DARK", "ANDALUSIAN_WEAPON", "STEPWISE_GRIND"],
            "aggressive": ["WEAPON_DARK", "FIBONACCI_DROP", "ANTIFRACTAL"],
            "dreamy": ["EMOTIVE_RISE", "WOOK_TRIP", "GOLDEN_RATIO"],
            "ethereal": ["FRACTAL_SPIRAL", "GOLDEN_RATIO", "432_SACRED"],
            "intense": ["WEAPON_DARK", "FIBONACCI_DROP", "ANTIFRACTAL"],
            "mystic": ["FRACTAL_SPIRAL", "TESSERACT", "432_SACRED"],
            "sacred": ["432_SACRED", "GOLDEN_RATIO", "FRACTAL_SPIRAL"],
            "euphoric": ["EMOTIVE_RISE", "GOLDEN_RATIO", "WOOK_TRIP"],
        }
        STYLE_PRESET_MAP = {
            "riddim": ["STEPWISE_GRIND", "WEAPON_DARK", "ANTIFRACTAL"],
            "melodic": ["EMOTIVE_RISE", "GOLDEN_RATIO", "FRACTAL_SPIRAL"],
            "tearout": ["WEAPON_DARK", "ANTIFRACTAL", "FIBONACCI_DROP"],
            "hybrid": ["TESSERACT", "FIBONACCI_DROP", "WEAPON_DARK"],
        }

        candidates = MOOD_PRESET_MAP.get(mood, []) + STYLE_PRESET_MAP.get(style, [])
        if not candidates:
            candidates = ["WEAPON_DARK"]

        # Pick the first available preset
        preset_name = "WEAPON_DARK"
        for name in candidates:
            if name in ALL_PRESETS:
                preset_name = name
                break

        prog = ALL_PRESETS[preset_name]()

        # Override key/BPM to match DNA
        prog.key = dna.key
        prog.scale_type = dna.scale
        prog.bpm = dna.bpm

        log.info("DESIGN CHORDS: %s → %s (%s %s @ %d BPM)",
                 preset_name, [c["symbol"] if isinstance(c, dict) else c.symbol for c in prog.chords],
                 dna.key, dna.scale, dna.bpm)
        return prog

    except Exception as exc:
        log.warning("DESIGN CHORDS: chord_progression module unavailable (%s)", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1c: COLLECT — Source ALL materials from Galactia + SampleLibrary
# ═══════════════════════════════════════════════════════════════════════════

def _load_wav_as_array(path: str) -> np.ndarray | None:
    """Load a WAV file as a mono float64 numpy array, normalized to [-1, 1]."""
    try:
        with wave.open(path, "rb") as wf:
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(n_frames)
        if sample_width == 2:
            dtype = np.int16
            max_val = 32768.0
        elif sample_width == 3:
            raw_bytes = np.frombuffer(raw, dtype=np.uint8)
            samples_24 = (raw_bytes[0::3].astype(np.int32) |
                          (raw_bytes[1::3].astype(np.int32) << 8) |
                          (raw_bytes[2::3].astype(np.int32) << 16))
            samples_24[samples_24 >= 0x800000] -= 0x1000000
            audio = samples_24.astype(np.float64) / 8388608.0
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels).mean(axis=1)
            return audio
        elif sample_width == 4:
            dtype = np.int32
            max_val = 2147483648.0
        else:
            return None
        audio = np.frombuffer(raw, dtype=dtype).astype(np.float64) / max_val
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)
        return audio
    except Exception as exc:
        log.debug("Failed to load WAV %s: %s", path, exc)
        return None


def _pick_sample(samples: list, keywords: tuple[str, ...] = ()) -> Any | None:
    """Score and pick best sample from a list based on character keywords."""
    if not samples:
        return None
    scored = []
    for s in samples:
        score = 0
        fname = getattr(s, "filename", str(s)).lower()
        if keywords:
            for kw in keywords:
                if kw in fname:
                    score += 2
        scored.append((score, random.random(), s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


def _collect_drums(dna: SongDNA, intent: dict[str, Any]) -> DrumKit:
    """Select drum samples from Galactia/SampleLibrary based on DNA intent.

    Pure selection — no synthesis. If a sample isn't available in the library,
    the slot stays None. Fill your Galactia library, don't synthesize workarounds.
    """
    kit = DrumKit()
    drum_intent = intent.get("drums", {})

    try:
        from engine.sample_library import SampleLibrary
        lib = SampleLibrary()

        # ── DNA-guided keyword maps ──
        _KICK_KW = {
            "heavy": ("hard", "heavy", "brutal", "808", "punch"),
            "clean": ("clean", "soft", "lite", "tight"),
            "deep": ("deep", "sub", "low", "boom"),
        }
        _SNARE_KW = {
            "metallic": ("metal", "ring", "clang", "bright"),
            "organic": ("snare", "snap", "crack", "wood"),
            "layered": ("layer", "fat", "stack", "thick"),
        }
        _HAT_KW = {
            "bright": ("bright", "crisp", "shimmer", "open"),
            "dark": ("dark", "muted", "lo-fi", "tape"),
        }

        # ── Kick (DNA-guided) ──
        kicks = lib.list_category("kick")
        kick_char = drum_intent.get("kick_character", "heavy")
        kw = _KICK_KW.get(kick_char, _KICK_KW["heavy"])
        sel = _pick_sample(kicks, kw)
        if sel:
            audio = _load_wav_as_array(sel.path)
            if audio is not None:
                kit.kick = audio
                kit.kick_source = f"galactia:{sel.filename}"

        # ── Snare (DNA-guided) ──
        snares = lib.list_category("snare")
        snare_char = drum_intent.get("snare_character", "organic")
        kw = _SNARE_KW.get(snare_char, _SNARE_KW["organic"])
        sel = _pick_sample(snares, kw)
        if sel:
            audio = _load_wav_as_array(sel.path)
            if audio is not None:
                kit.snare = audio
                kit.snare_source = f"galactia:{sel.filename}"

        # ── Hats (DNA-guided by character) ──
        hat_char = drum_intent.get("hat_character", "bright")
        hat_kw = _HAT_KW.get(hat_char, _HAT_KW["bright"])
        for cat, attr, src_attr in [
            ("hat_closed", "hat_closed", "hat_closed_source"),
            ("hat_open", "hat_open", "hat_open_source"),
        ]:
            items = lib.list_category(cat)
            sel = _pick_sample(items, hat_kw) if items else None
            if sel:
                audio = _load_wav_as_array(sel.path)
                if audio is not None:
                    setattr(kit, attr, audio)
                    setattr(kit, src_attr, f"galactia:{sel.filename}")

        # ── Clap, crash, ride, perc (best-match from library) ──
        for cat, attr, src_attr in [
            ("clap", "clap", "clap_source"),
            ("crash", "crash", "crash_source"),
            ("ride", "ride", "ride_source"),
            ("perc", "perc", "perc_source"),
        ]:
            items = lib.list_category(cat)
            if items:
                sel = random.choice(items)
                audio = _load_wav_as_array(sel.path)
                if audio is not None:
                    setattr(kit, attr, audio)
                    setattr(kit, src_attr, f"galactia:{sel.filename}")

    except Exception as exc:
        log.warning("COLLECT DRUMS: SampleLibrary unavailable (%s) — drum slots empty", exc)

    # Log what we got
    filled = [s for s in ["kick", "snare", "hat_closed", "hat_open", "clap",
                          "crash", "ride", "perc"]
              if getattr(kit, s) is not None]
    empty = [s for s in ["kick", "snare", "hat_closed", "hat_open", "clap",
                         "crash", "ride", "perc"]
             if getattr(kit, s) is None]
    if empty:
        log.warning("COLLECT DRUMS: empty slots (add to Galactia): %s", empty)

    return kit


def _collect_fx_samples(intent: dict[str, Any]) -> GalactiaFxSamples:
    """Source FX samples from Galactia — risers, impacts, reverses, falling, rising, shepards.

    Uses intent['fx']['impact_intensity'] and kick_character to tilt
    category proportions toward the reference track's energy profile.
    """
    gfx = GalactiaFxSamples()

    try:
        from engine.sample_library import SampleLibrary
        lib = SampleLibrary()

        # Scale sample counts from analyzer-derived intensity fields
        _fx = intent.get("fx", {})
        _impact_intensity = float(_fx.get("impact_intensity", 0.85))
        _riser_intensity = float(_fx.get("riser_intensity", 0.85))
        _kick_heavy = intent.get("drums", {}).get("kick_character", "") == "heavy"
        # impact count 1–5; risers/sweeps 1–4; heavy kick → +1 impact
        _n_impacts = max(1, round(1 + _impact_intensity * 3) + (1 if _kick_heavy else 0))
        _n_risers = max(1, round(1 + _riser_intensity * 2))

        cat_map = {
            "fx_riser":      ("risers",  _n_risers),
            "fx_impact":     ("impacts", _n_impacts),
            "fx_downlifter": ("falling", _n_risers),
            "fx_sweep":      ("rising",  max(1, _n_risers - 1)),
            "fx_shepard":    ("shepard", 2),
        }

        for cat, (attr, max_count) in cat_map.items():
            items = lib.list_category(cat)
            if items:
                selected = random.sample(items, min(max_count, len(items)))
                loaded = []
                src_names = []
                for s in selected:
                    audio = _load_wav_as_array(s.path)
                    if audio is not None:
                        loaded.append(audio)
                        src_names.append(s.filename)
                setattr(gfx, attr, loaded)
                gfx.sources[attr] = src_names
                log.info("COLLECT FX: %d %s samples", len(loaded), attr)

        # Buildups
        buildups = lib.list_category("loop_buildup")
        if buildups:
            selected = random.sample(buildups, min(2, len(buildups)))
            for s in selected:
                audio = _load_wav_as_array(s.path)
                if audio is not None:
                    gfx.buildups.append(audio)
            gfx.sources["buildups"] = [s.filename for s in selected]

        # Reverse/transition samples
        revs = lib.list_category("fx_transition")
        if revs:
            selected = random.sample(revs, min(2, len(revs)))
            for s in selected:
                audio = _load_wav_as_array(s.path)
                if audio is not None:
                    gfx.reverses.append(audio)
            gfx.sources["reverses"] = [s.filename for s in selected]

    except Exception as exc:
        log.warning("COLLECT FX: SampleLibrary unavailable (%s)", exc)

    return gfx


def _collect_wavetables() -> WavetableKit:
    """Source wavetables from Galactia neuro collection + phi_core fallback."""
    wt_kit = WavetableKit()

    try:
        from engine.galatcia import catalog_galatcia, read_wavetable_frames
        catalog = catalog_galatcia()

        for wt in catalog.wavetables:
            try:
                frames = read_wavetable_frames(wt.source_path)
                if frames:
                    wt_kit.frames[wt.name] = frames
                    wt_kit.sources[wt.name] = f"galactia:{wt.filename}"
                    log.info("COLLECT WT: loaded %s (%d frames)", wt.name, len(frames))
            except Exception as exc:
                log.debug("COLLECT WT: failed to load %s: %s", wt.name, exc)

    except Exception as exc:
        log.warning("COLLECT WT: Galactia catalog unavailable (%s)", exc)

    # Fallback: generate phi-core wavetable
    if not wt_kit.frames:
        try:
            from engine.phi_core import generate_phi_core_v1
            frames = generate_phi_core_v1(n_frames=16)
            wt_kit.frames["phi_core_v1"] = frames
            wt_kit.sources["phi_core_v1"] = "synth:phi_core"
            log.info("COLLECT WT: generated phi_core_v1 fallback (%d frames)", len(frames))
        except Exception as exc:
            log.debug("COLLECT WT: phi_core fallback failed: %s", exc)

    return wt_kit


# ── DNA-to-morph-type mapping ──
_MOOD_MORPH_MAP: dict[str, str] = {
    "dark": "fractal",
    "aggressive": "granular",
    "dreamy": "spectral",
    "ethereal": "spectral",
    "intense": "fractal",
    "mystic": "phi_spline",
    "sacred": "phi_spline",
    "euphoric": "formant",
}

_STYLE_MORPH_OVERRIDE: dict[str, str] = {
    "riddim": "granular",
    "tearout": "fractal",
    "melodic": "spectral",
    "hybrid": "fractal",
}


def _generate_dna_wavetables(
    dna: SongDNA,
    intent: dict[str, Any],
    wt_kit: WavetableKit,
) -> tuple[list[tuple[str, list[Any]]], int]:
    """DNA-driven wavetable generation — tunes FM/harmonic/growl packs to the song.

    Uses ``dna.bass.fm_depth`` to scale FM ratio range, ``dna.bass.distortion``
    to drive growl intensity, ``dna.root_freq`` for harmonic fundamental, and
    ``dna.mood_name`` to weight pack selection.

    Returns (all_packs, count_generated).
    """
    all_packs: list[tuple[str, list[Any]]] = []
    generated = 0

    if not _HAS_WT_PACK:
        return all_packs, generated

    # ── DNA-scaled parameters ──
    fm_depth = dna.bass.fm_depth        # 0-10, drives FM ratio range
    distortion = dna.bass.distortion    # 0-1, drives growl drive levels
    mood = getattr(dna, "mood_name", "dark").lower()
    style = dna.style.lower()

    # Scale FM tables by depth — more FM depth → more tables
    fm_n_tables = max(4, min(16, int(4 + fm_depth * 1.2)))
    try:
        fm_pack = generate_fm_ratio_sweep(n_tables=fm_n_tables, n_frames=16)
        all_packs.extend(fm_pack)
        generated += len(fm_pack)
    except Exception as exc:
        log.warning("STAGE 3B: FM sweep failed: %s", exc)

    # Harmonic sweep — always useful, scale by brightness
    harm_n_tables = max(4, min(16, int(6 + dna.lead.brightness * 10)))
    try:
        harm_pack = generate_harmonic_sweep(n_tables=harm_n_tables, n_frames=16)
        all_packs.extend(harm_pack)
        generated += len(harm_pack)
    except Exception as exc:
        log.warning("STAGE 3B: harmonic sweep failed: %s", exc)

    # Growl pack — scale by distortion and bass aggressiveness
    if distortion > 0.1 or style in ("riddim", "tearout", "dubstep"):
        try:
            growl_pack = generate_growl_vowel_pack(n_frames=16)
            all_packs.extend(growl_pack)
            generated += len(growl_pack)
        except Exception as exc:
            log.warning("STAGE 3B: growl pack failed: %s", exc)

    # Morph pack — fractal interpolation for variation
    if mood in ("mystic", "sacred", "dreamy", "ethereal") or style == "melodic":
        try:
            morph_p = generate_morph_pack(n_tables=8, n_frames=16)
            all_packs.extend(morph_p)
            generated += len(morph_p)
        except Exception as exc:
            log.warning("STAGE 3B: morph pack failed: %s", exc)

    # ── Phi-core generation tuned to song root ──
    if _HAS_PHI_CORE:
        try:
            root = dna.root_freq
            partials = phi_harmonic_series(root, n_partials=24)
            amps = phi_amplitude_curve(24, decay=1.0 + distortion)
            base_frame = phi_generate_frame(partials, amps, size=2048)
            bright_amps = phi_amplitude_curve(24, decay=0.5)
            bright_frame = phi_generate_frame(partials, bright_amps, size=2048)
            phi_frames = phi_morph_frames(base_frame, bright_frame, steps=16)
            pack_name = f"phi_root_{dna.key}_{dna.scale}"
            all_packs.append((pack_name, phi_frames))
            generated += 1
        except Exception as exc:
            log.warning("STAGE 3B: phi_core root WT failed: %s", exc)

    # ── Growl resampler on existing frames if style demands ──
    if _HAS_GROWL_RESAMPLE and distortion > 0.25:
        try:
            # Pick first available frame as seed
            seed_frame = None
            for _name, frames in wt_kit.frames.items():
                if frames and hasattr(frames[0], "__len__") and len(frames[0]) >= 2048:
                    seed_frame = frames[0]
                    break
            if seed_frame is None and all_packs:
                _, first_pack_frames = all_packs[0]
                if first_pack_frames:
                    seed_frame = first_pack_frames[0]
            if seed_frame is not None:
                growl_frames = growl_resample_pipeline(seed_frame, n_output_frames=16)
                all_packs.append(("growl_resample", growl_frames))
                generated += 1
        except Exception as exc:
            log.warning("STAGE 3B: growl resampler failed: %s", exc)

    # Merge all packs into wavetable kit
    for pack_name, frames in all_packs:
        if frames:
            wt_kit.frames[pack_name] = frames
            wt_kit.sources[pack_name] = "gen:dna_wavetable_pack"

    return all_packs, generated


def _select_morph_type(dna: SongDNA) -> str:
    """Pick the best morph algorithm for this song's DNA."""
    mood = getattr(dna, "mood_name", "dark").lower()
    style = dna.style.lower()
    # Style override takes priority
    if style in _STYLE_MORPH_OVERRIDE:
        return _STYLE_MORPH_OVERRIDE[style]
    return _MOOD_MORPH_MAP.get(mood, "phi_spline")


def _morph_all_wavetables(
    dna: SongDNA,
    wt_kit: WavetableKit,
    mod_routes: dict[str, Any],
) -> dict[str, list[Any]]:
    """DNA-informed morphing of all wavetable frames.

    Selects morph type from mood/style, uses modulation route info to
    set morph parameters (e.g. higher LFO rate → more morph frames,
    sidechain shape → morph curve).
    """
    morphed: dict[str, list[Any]] = {}
    if not _HAS_WT_MORPH or not wt_kit.frames:
        return morphed

    morph_type = _select_morph_type(dna)

    # Derive morph parameters from mod routes
    bass_routes = mod_routes.get("bass", {})
    bass_lfos = bass_routes.get("lfos", [])
    # More LFOs / higher rates → more morph frames for movement
    n_frames = 16
    if bass_lfos:
        avg_rate = sum(getattr(l, "rate", 2.0) for l in bass_lfos) / len(bass_lfos)
        n_frames = max(8, min(32, int(avg_rate * 4)))

    # Morph curve from mood profile
    morph_curve = 1.618  # PHI default
    mood = getattr(dna, "mood_name", "dark").lower()
    if mood in ("aggressive", "intense"):
        morph_curve = 2.0  # sharper transitions
    elif mood in ("dreamy", "ethereal"):
        morph_curve = 1.2  # smoother transitions

    for wt_name, frames in list(wt_kit.frames.items()):
        if len(frames) < 2:
            continue
        try:
            preset = MorphPreset(
                name=f"morph_{wt_name}",
                morph_type=morph_type,
                num_frames=min(n_frames, len(frames)),
                morph_curve=morph_curve,
            )
            result = morph_wavetable(frames[:preset.num_frames], preset)
            morph_key = f"{wt_name}_{morph_type}"
            morphed[morph_key] = result
            wt_kit.frames[morph_key] = result
            wt_kit.sources[morph_key] = f"morph:{morph_type}:{wt_name}"
        except Exception as exc:
            log.debug("MORPH: failed %s: %s", wt_name, exc)

    return morphed


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1d: RECIPES
# ═══════════════════════════════════════════════════════════════════════════

def _build_recipes(dna: SongDNA, intent: dict[str, Any],
                    sections: dict[str, int]) -> dict[str, Any]:
    """Build production recipes consumed by downstream phases.

    All quality targets derived from DNA or FIBONACCI/PHI constants.
    """
    beat_s = 60.0 / dna.bpm
    bar_s = beat_s * BEATS_PER_BAR
    total_bars = sum(sections.values())

    return {
        "groove_template": _select_groove_template(dna),
        "quality_targets": {
            "target_lufs": dna.mix.target_lufs,
            "ceiling_db": dna.mix.ceiling_db,
            "dr_target": PHI ** 5,                             # ~11.09 dB dynamic range
            "stereo_width": dna.mix.stereo_width,
            "min_sections": FIBONACCI[4],                      # 5 sections minimum
            "min_duration_s": bar_s * FIBONACCI[9],            # 55 bars worth
            "max_duration_s": bar_s * FIBONACCI[11],           # 233 bars worth
        },
        "arrange_tasks": _build_arrange_tasks(dna, intent, sections),
    }


def _select_groove_template(dna: SongDNA) -> str:
    style_map = {
        "dubstep": "dubstep_halftime",
        "riddim": "riddim_bounce",
        "melodic": "dubstep_halftime",
        "tearout": "dubstep_halftime",
        "dnb": "dnb_full",
        "hybrid": "dubstep_halftime",
    }
    return style_map.get(dna.style, "dubstep_halftime")


def _build_arrange_tasks(dna: SongDNA, intent: dict[str, Any],
                          sections: dict[str, int]) -> list[str]:
    """Generate concrete task list for ARRANGE phase."""
    tasks = []
    bass_types = intent.get("bass", {}).get("types_needed", ["dist_fm"])

    if sections.get("intro", 0) > 0:
        tasks.append(f"INTRO ({sections['intro']} bars): drone + filtered pad + noise bed + sparse drums")
    if sections.get("build", 0) > 0:
        tasks.append(f"BUILD ({sections['build']} bars): riser + gate chop + full pad + snare roll")
    if sections.get("drop", 0) > 0:
        tasks.append(f"DROP ({sections['drop']} bars): full drums + sub + bass rotation"
                     f" ({'/'.join(bass_types)}) + leads + chords + vocal chops")
    if sections.get("break", 0) > 0:
        tasks.append(f"BREAK ({sections['break']} bars): lush pad + pluck arps + sparse drums (NO sub)")
    if sections.get("bridge", 0) > 0:
        tasks.append(f"BRIDGE ({sections['bridge']} bars): atmos + filtered elements + reverse FX")
    if sections.get("outro", 0) > 0:
        tasks.append(f"OUTRO ({sections['outro']} bars): pad fadeout + sparse drums + drone tail")

    return tasks


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1e: SKETCH — Synthesize + Process ALL ingredients
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Normalize audio to target peak level."""
    peak = np.max(np.abs(audio))
    if peak > 0:
        return audio * (target_peak / peak)
    return audio


def _process_drum(audio: np.ndarray, drive: float = 0.5,
                   eq_low_db: float = 0.0, eq_high_db: float = 0.0) -> np.ndarray:
    """Drum processing — compression + saturation + EQ shaping."""
    from engine.dynamics import compress, CompressorSettings
    from engine.saturation import SaturationEngine, SatConfig

    processed = compress(audio.tolist(), CompressorSettings(
        threshold_db=-6.0, ratio=4.0, attack_ms=0.5, release_ms=40.0, makeup_db=2.0
    ))

    if drive > 0.1:
        sat = SaturationEngine(sample_rate=SR)
        processed = sat.saturate(processed, SatConfig(
            sat_type="tape", drive=drive, mix=0.4
        ))

    if abs(eq_low_db) > 0.5 or abs(eq_high_db) > 0.5:
        from engine.intelligent_eq import apply_eq_band
        if eq_low_db != 0:
            processed = apply_eq_band(processed, center_hz=100.0, gain_db=eq_low_db, q=0.5)
        if eq_high_db != 0:
            processed = apply_eq_band(processed, center_hz=8000.0, gain_db=eq_high_db, q=0.5)

    return np.asarray(processed, dtype=np.float64)


def _sketch_drums(kit: DrumKit, dna: SongDNA) -> DrumKit:
    """Process collected drum samples with DNA-driven shaping."""
    dd = dna.drums

    # ── DNA-driven norm gains (phi-scaled from velocity targets) ──
    kick_gain = 1.0 - 1.0 / (PHI ** 5)              # ~0.909
    snare_gain = 1.0 - 1.0 / (PHI ** 3)             # ~0.764
    hat_gain = 1.0 / PHI                              # ~0.618
    clap_gain = 1.0 - 1.0 / (PHI ** 2)              # ~0.618
    crash_gain = 1.0 / PHI - 0.1                     # ~0.518
    ride_gain = 1.0 / PHI - 0.15                     # ~0.468
    perc_gain = 1.0 / PHI                             # ~0.618

    if kit.kick is not None:
        kit.kick = _normalize(_process_drum(
            kit.kick, drive=dd.kick_drive,
            eq_low_db=dd.kick_sub_weight * PHI ** 2,
            eq_high_db=dd.kick_sub_weight * PHI
        ), kick_gain)

    if kit.snare is not None:
        kit.snare = _normalize(_process_drum(
            kit.snare, drive=dd.snare_metallic + (1.0 / PHI ** 3),
            eq_low_db=dd.snare_noise_mix * PHI,
            eq_high_db=dd.snare_metallic * PHI ** 2
        ), snare_gain)

    if kit.hat_closed is not None:
        from engine.intelligent_eq import apply_eq_band
        hat_center = dna.root_freq * PHI ** 8         # DNA-driven hat EQ center
        hat_q = 1.0 / PHI                             # phi-derived Q
        hc = apply_eq_band(kit.hat_closed.tolist(),
                           center_hz=hat_center,
                           gain_db=dd.hat_brightness * PHI ** 2,
                           q=hat_q)
        kit.hat_closed = _normalize(np.asarray(hc, dtype=np.float64), hat_gain + dd.hat_brightness * 0.1)

    if kit.hat_open is not None:
        from engine.intelligent_eq import apply_eq_band
        ho_center = dna.root_freq * PHI ** 7          # slightly below closed hat
        ho = apply_eq_band(kit.hat_open.tolist(),
                           center_hz=ho_center,
                           gain_db=dd.hat_brightness * PHI,
                           q=1.0 / PHI)
        kit.hat_open = _normalize(np.asarray(ho, dtype=np.float64), hat_gain)

    if kit.clap is not None:
        kit.clap = _normalize(_process_drum(
            kit.clap, drive=dd.snare_metallic / PHI,
            eq_high_db=dd.snare_metallic * PHI
        ), clap_gain)

    if kit.crash is not None:
        kit.crash = _normalize(kit.crash, crash_gain)

    if kit.ride is not None:
        kit.ride = _normalize(kit.ride, ride_gain)

    if kit.perc is not None:
        kit.perc = _normalize(kit.perc, perc_gain)

    log.info("SKETCH DRUMS: kick=%s snare=%s hat=%s clap=%s",
             kit.kick_source, kit.snare_source,
             kit.hat_closed_source, kit.clap_source)
    return kit


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2B: BUILD DRUM LOOPS — sequence samples into per-section patterns
# ═══════════════════════════════════════════════════════════════════════════

_SR = 48_000


def _build_drum_loops(kit: DrumKit, dna: SongDNA,
                      sections: dict[str, int]) -> DrumLoopKit:
    """Build audio loops from DrumKit samples for each section type.

    DNA-driven dubstep halftime conventions:
      - drop:  kick on 1, snare on 3, hats driven by hat_density
      - build: accelerating snare rolls (energy-scaled)
      - intro/outro: sparse hats + soft kick
      - bridge: minimal kick + ride
    """
    loops = DrumLoopKit()
    bpm = dna.bpm
    beat_samples = int(60.0 / bpm * _SR)
    dd = dna.drums
    style = getattr(dna, "style", "dubstep").lower()
    energy = getattr(dna, "energy", 0.7)

    # ── DNA-driven velocities (phi-scaled from drum DNA fields) ──
    kick_vel = 1.0 - 1.0 / (PHI ** (1 + dd.kick_drive * 2))  # phi-scaled 0.38–0.85
    snare_vel = 1.0 - 1.0 / (PHI ** (1 + dd.snare_noise_mix * 2))
    hat_vel = dd.hat_brightness / PHI                          # phi-scaled brightness

    # Hat subdivisions from DrumDNA hat_density (16 = 8ths, 32 = 16ths)
    hat_subdivisions = dd.hat_density  # 16 or 32
    hat_steps_per_bar = hat_subdivisions // 2  # 8 or 16 steps per bar
    hat_step_beats = float(BEATS_PER_BAR) / hat_steps_per_bar   # 0.5 or 0.25 beats

    def _bar_samples() -> int:
        return beat_samples * BEATS_PER_BAR

    def _mix(buf: np.ndarray, sample: np.ndarray | None,
             offset: int, gain: float = 1.0) -> None:
        if sample is None:
            return
        end = min(offset + len(sample), len(buf))
        if offset < 0 or offset >= len(buf):
            return
        n = end - offset
        buf[offset:end] += sample[:n] * gain

    # ── Drop pattern: bar count from sections, DNA velocities ──
    drop_bars = sections.get("drop", FIBONACCI[5])     # from arrangement, fallback 8
    drop_buf = np.zeros(drop_bars * _bar_samples(), dtype=np.float64)
    for bar_i in range(drop_bars):
        bo = bar_i * _bar_samples()
        _mix(drop_buf, kit.kick, bo, kick_vel)
        if style in ("tearout", "brostep") and bar_i % 2 == 1:
            _mix(drop_buf, kit.kick, bo + beat_samples, kick_vel / PHI)
        _mix(drop_buf, kit.snare, bo + beat_samples * 2, snare_vel)
        _swing_offset = int(dd.pattern_swing * beat_samples * 0.5)
        for step in range(hat_steps_per_bar):
            vel = hat_vel if step % 2 == 0 else hat_vel / PHI
            _mix(drop_buf, kit.hat_closed,
                 bo + int(step * hat_step_beats * beat_samples) + (_swing_offset if step % 2 == 1 else 0), vel)
        _mix(drop_buf, kit.hat_open, bo + int(beat_samples * 1.5), hat_vel * (1.0 / PHI + 0.2))
        _mix(drop_buf, kit.hat_open, bo + int(beat_samples * 3.5), hat_vel * (1.0 / PHI + 0.2))
        if bar_i % 2 == 1 and kit.crash is not None:
            _mix(drop_buf, kit.crash, bo, 1.0 / PHI ** 2)
        if style not in ("riddim", "deep_dubstep") and kit.perc is not None:
            if bar_i % 2 == 0:
                _mix(drop_buf, kit.perc, bo + int(beat_samples * (PHI - 0.1)), 1.0 / PHI ** 3)
    loops.patterns["drop"] = drop_buf
    loops.pattern_bars["drop"] = drop_bars
    loops.sources["drop"] = f"drum_loop:halftime_drop_{style}_hd{hat_subdivisions}"

    # ── Build pattern: Fibonacci-derived accelerating roll ──
    build_bars = sections.get("build", FIBONACCI[5])   # from arrangement, fallback 8
    build_buf = np.zeros(build_bars * _bar_samples(), dtype=np.float64)
    fib_divisions = [FIBONACCI[3], FIBONACCI[5], FIBONACCI[7], FIBONACCI[8]]  # 3, 8, 21, 34
    for bar_i in range(build_bars):
        bo = bar_i * _bar_samples()
        _mix(build_buf, kit.kick, bo, kick_vel / PHI)
        _mix(build_buf, kit.kick, bo + beat_samples * 2, kick_vel / PHI)
        div_idx = min(int(bar_i * len(fib_divisions) / max(build_bars, 1)), len(fib_divisions) - 1)
        divisions = fib_divisions[div_idx]
        step = _bar_samples() // max(divisions, 1)
        for hit in range(divisions):
            vel = (1.0 / PHI ** 2 + snare_vel / PHI) * (bar_i / max(build_bars, 1)) * (hit / max(divisions, 1))
            vel = max(1.0 / PHI ** 4, vel)
            _mix(build_buf, kit.snare, bo + hit * step, vel)
    loops.patterns["build"] = build_buf
    loops.pattern_bars["build"] = build_bars
    loops.sources["build"] = "drum_loop:build_roll"

    # ── Intro pattern: section-driven, DNA velocities ──
    intro_bars = sections.get("intro", FIBONACCI[5])   # from arrangement, fallback 8
    intro_buf = np.zeros(intro_bars * _bar_samples(), dtype=np.float64)
    for bar_i in range(intro_bars):
        bo = bar_i * _bar_samples()
        _mix(intro_buf, kit.kick, bo, kick_vel / (PHI ** 2))
        for q in range(BEATS_PER_BAR):
            _mix(intro_buf, kit.hat_closed, bo + q * beat_samples, hat_vel / PHI)
    loops.patterns["intro"] = intro_buf
    loops.pattern_bars["intro"] = intro_bars
    loops.sources["intro"] = "drum_loop:sparse_intro"

    # ── Bridge pattern: section-driven, DNA velocities ──
    bridge_bars = sections.get("bridge", FIBONACCI[4]) # from arrangement, fallback 5
    bridge_buf = np.zeros(bridge_bars * _bar_samples(), dtype=np.float64)
    for bar_i in range(bridge_bars):
        bo = bar_i * _bar_samples()
        _mix(bridge_buf, kit.kick, bo, kick_vel / (PHI ** 3))
        for q in range(BEATS_PER_BAR):
            _mix(bridge_buf, kit.ride, bo + q * beat_samples, 1.0 / PHI ** 2)
        _mix(bridge_buf, kit.hat_closed, bo + int(beat_samples * 0.5), hat_vel / (PHI ** 2))
        _mix(bridge_buf, kit.hat_closed, bo + int(beat_samples * 2.5), hat_vel / (PHI ** 2))
    loops.patterns["bridge"] = bridge_buf
    loops.pattern_bars["bridge"] = bridge_bars
    loops.sources["bridge"] = "drum_loop:bridge_ride"

    # ── Outro pattern (reuse intro) ──
    loops.patterns["outro"] = intro_buf.copy()
    loops.pattern_bars["outro"] = intro_bars
    loops.sources["outro"] = "drum_loop:sparse_outro"

    log.info("DRUM LOOPS: built %d patterns (%s)",
             len(loops.patterns), list(loops.patterns.keys()))
    return loops


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2F: RACK MIDI MAP — map populated rack slots to MIDI notes
# ═══════════════════════════════════════════════════════════════════════════

# Zone layout (matches _build_128_rack)
_ZONE_RANGES: dict[str, tuple[int, int]] = {
    "sub_bass": (0, 7), "low_bass": (8, 15), "mid_bass": (16, 28),
    "high_bass": (29, 36), "kicks": (37, 49), "snares": (50, 62),
    "hats": (63, 70), "perc": (71, 83), "fx": (84, 96),
    "melodic": (97, 104), "atmos": (105, 112), "vocal": (113, 117),
    "transitions": (118, 122), "utility": (123, 127),
}

# Derived from _ZONE_RANGES — start index and capacity per zone
_ZONE_IDX: dict[str, int] = {z: r[0] for z, r in _ZONE_RANGES.items()}
_ZONE_MAX: dict[str, int] = {z: r[1] - r[0] + 1 for z, r in _ZONE_RANGES.items()}


def _rack_add(rack: Rack128, counts: dict[str, int],
              zone: str, name: str, audio: np.ndarray | None, source: str,
              *, dedup: bool = False) -> None:
    """Add a single slot to the rack."""
    if audio is None or counts.get(zone, 0) >= _ZONE_MAX.get(zone, 0):
        return
    if dedup and name in rack.slots:
        return
    slot_num = _ZONE_IDX[zone] + counts[zone]
    rack.slots[name] = {"audio": audio, "source": source, "zone_num": slot_num, "zone": zone}
    rack.source_manifest.append({"slot": name, "source": source, "zone": slot_num})
    counts[zone] += 1


def _fill_synth_zones(rack: Rack128, counts: dict[str, int], *,
                      bass: BassArsenal | None = None,
                      leads: LeadPalette | None = None,
                      atmosphere: AtmosphereKit | None = None,
                      fx: FxKit | None = None,
                      vocals: VocalKit | None = None,
                      wavetables: WavetableKit | None = None,
                      galactia_fx: GalactiaFxSamples | None = None,
                      melody: MelodyKit | None = None,
                      wobble: WobbleBassKit | None = None,
                      riddim: RiddimBassKit | None = None,
                      growl: GrowlKit | None = None,
                      dedup: bool = False) -> None:
    """Fill non-drum synth zones into *rack*.  Used by both build and augment."""
    add = lambda z, n, a, s: _rack_add(rack, counts, z, n, a, s, dedup=dedup)

    # ── Sub bass ──
    if bass:
        if bass.sub is not None:
            add("sub_bass", "sub_sine", np.asarray(bass.sub, dtype=np.float64), bass.sources.get("sub", ""))
        for btype, audio in bass.sounds.items():
            if "sub" in btype.lower():
                add("sub_bass", f"sub_{btype}", audio, bass.sources.get(btype, ""))

    # ── Low bass ──
    if bass:
        if bass.reese is not None:
            add("low_bass", "bass_reese", np.asarray(bass.reese, dtype=np.float64), bass.sources.get("reese", ""))
        for btype, audio in bass.sounds.items():
            if "sub" not in btype.lower():
                add("low_bass", f"bass_{btype}", audio, bass.sources.get(btype, ""))

    # ── Mid bass: wobble + riddim ──
    if wobble:
        for wname, audio in wobble.patterns.items():
            add("mid_bass", f"wobble_{wname}", audio, wobble.sources.get(wname, ""))
    if riddim:
        for rname, audio in riddim.patterns.items():
            add("mid_bass", f"riddim_{rname}", audio, riddim.sources.get(rname, ""))

    # ── High bass: growl frames ──
    if growl and growl.frames:
        for i, frame in enumerate(growl.frames[:_ZONE_MAX["high_bass"]]):
            add("high_bass", f"growl_frame_{i}", frame, growl.sources.get("growl_frames", ""))

    # ── FX / Risers ──
    if fx:
        for attr in ("riser", "boom", "rev_crash", "hit"):
            audio = getattr(fx, attr, None)
            if audio is not None:
                add("fx", f"fx_{attr}", audio, fx.sources.get(attr, ""))
        for i, audio in enumerate(fx.fx_falling):
            add("fx", f"falling_{i}", audio, f"galactia:falling_{i}")
        for i, audio in enumerate(fx.fx_rising):
            add("fx", f"rising_{i}", audio, f"galactia:rising_{i}")
        for i, audio in enumerate(fx.shepard_tones):
            add("fx", f"shepard_{i}", audio, f"galactia:shepard_{i}")

    # ── Melodic ──
    if leads:
        for freq, audio in list(leads.screech.items())[:2]:
            add("melodic", f"screech_{freq:.0f}hz", audio, leads.sources.get("screech", ""))
        for freq, audio in list(leads.pluck.items())[:2]:
            add("melodic", f"pluck_{freq:.0f}hz", audio, leads.sources.get("pluck", ""))
        if leads.chord_l is not None:
            add("melodic", "chord_L", leads.chord_l, leads.sources.get("chords", ""))
    if melody and melody.lead_melody is not None:
        add("melodic", "lead_melody", melody.lead_melody, melody.sources.get("lead_melody", ""))
    if melody:
        for aname, audio in list(melody.arp_patterns.items())[:2]:
            add("melodic", f"arp_{aname}", audio, melody.sources.get(aname, ""))

    # ── Atmosphere ──
    if atmosphere:
        if atmosphere.dark_pad is not None:
            add("atmos", "pad_dark", atmosphere.dark_pad, atmosphere.sources.get("dark_pad", ""))
        if atmosphere.lush_pad is not None:
            add("atmos", "pad_lush", atmosphere.lush_pad, atmosphere.sources.get("lush_pad", ""))
        if atmosphere.drone is not None:
            add("atmos", "drone", atmosphere.drone, atmosphere.sources.get("drone", ""))
        if atmosphere.noise_bed is not None:
            add("atmos", "noise_bed", atmosphere.noise_bed, atmosphere.sources.get("noise_bed", ""))

    # ── Vocal ──
    if vocals:
        for vowel, audio in list(vocals.chops.items())[:5]:
            add("vocal", f"vox_{vowel}", audio, vocals.sources.get(vowel, ""))

    # ── Transitions ──
    if fx:
        for attr in ("tape_stop", "pitch_dive", "gate_chop", "stutter"):
            audio = getattr(fx, attr, None)
            if audio is not None:
                add("transitions", f"trans_{attr}", audio, fx.sources.get(attr, ""))
    if galactia_fx:
        for i, audio in enumerate(galactia_fx.buildups[:1]):
            add("transitions", f"buildup_{i}", audio, f"galactia:buildup_{i}")

    # ── Utility: wavetables ──
    if wavetables:
        for wt_name in list(wavetables.frames.keys())[:5]:
            frames = wavetables.frames[wt_name]
            if frames:
                add("utility", f"wt_{wt_name}", frames[0], wavetables.sources.get(wt_name, ""))


def _build_rack_midi_map(rack: Rack128) -> RackMidiMap:
    """Create MIDI note assignments for every populated 128 Rack slot.

    Standard Ableton Drum Rack: MIDI note N triggers pad N (C-2 = note 0).
    """
    midi_map = RackMidiMap(zone_ranges=dict(_ZONE_RANGES))

    for name, slot_info in rack.slots.items():
        zone_num = slot_info.get("zone_num", -1)
        zone_name = slot_info.get("zone", "unknown")
        if 0 <= zone_num <= 127:
            midi_map.note_map[zone_num] = {
                "note": zone_num,
                "name": name,
                "zone": zone_name,
                "source": slot_info.get("source", ""),
            }

    log.info("RACK MIDI MAP: %d notes mapped across %d zones",
             len(midi_map.note_map),
             len({v["zone"] for v in midi_map.note_map.values()}))
    return midi_map


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2G: LOOP MIDI MAPS — MIDI patterns that trigger drum rack pads
# ═══════════════════════════════════════════════════════════════════════════

def _build_loop_midi_maps(loops: DrumLoopKit, rack: Rack128,
                           dna: SongDNA) -> list[LoopMidiMap]:
    """Create MIDI trigger patterns matching each drum loop.

    All velocities and timing derived from DNA fields and PHI/FIBONACCI.
    Each hit references the MIDI note (zone_num) of the corresponding
    drum sample in the 128 rack.
    """
    dd = dna.drums
    beat_s = 60.0 / dna.bpm

    # ── DNA-driven MIDI velocities (phi-scaled from drum DNA) ──
    kick_midi_vel = 1.0 - 1.0 / (PHI ** (1 + dd.kick_drive * 2))
    snare_midi_vel = 1.0 - 1.0 / (PHI ** (1 + dd.snare_noise_mix * 2))
    hat_midi_vel = dd.hat_brightness / PHI
    oh_midi_vel = hat_midi_vel / PHI
    crash_midi_vel = 1.0 / PHI ** 2
    ride_midi_vel = 1.0 / PHI ** 2

    # ── Phi-derived note durations (in beats) ──
    dur_long = 1.0 / PHI                              # ~0.618 beats
    dur_med  = 1.0 / PHI ** 2                          # ~0.382 beats
    dur_short = 1.0 / PHI ** 3                         # ~0.236 beats

    # Resolve drum names → zone_num in rack
    _drum_notes: dict[str, int] = {}
    for name, slot in rack.slots.items():
        if slot.get("zone", "").startswith(("kicks", "snares", "hats", "perc")):
            _drum_notes[name] = slot["zone_num"]

    # Shorthand lookups
    kick_note = _drum_notes.get("drum_kick", 37)
    snare_note = _drum_notes.get("drum_snare", 50)
    clap_note = _drum_notes.get("drum_clap", 51)
    hc_note = _drum_notes.get("drum_hat_closed", 63)
    ho_note = _drum_notes.get("drum_hat_open", 64)
    crash_note = _drum_notes.get("drum_crash", 71)
    ride_note = _drum_notes.get("drum_ride", 72)

    midi_maps: list[LoopMidiMap] = []
    fib_divisions = [FIBONACCI[3], FIBONACCI[5], FIBONACCI[7], FIBONACCI[8]]  # 3, 8, 21, 34

    for section_type, n_bars in loops.pattern_bars.items():
        lm = LoopMidiMap(name=f"loop_{section_type}", section_type=section_type,
                         n_bars=n_bars)
        hits: list[dict[str, Any]] = []

        if section_type == "drop":
            for bar in range(n_bars):
                b = bar * float(BEATS_PER_BAR)
                hits.append({"beat": b, "note": kick_note, "velocity": kick_midi_vel, "duration": dur_long})
                hits.append({"beat": b + 2.0, "note": snare_note, "velocity": snare_midi_vel, "duration": dur_long})
                for eighth in range(FIBONACCI[5]):  # 8 hat hits per bar
                    hits.append({"beat": b + eighth * 0.5, "note": hc_note, "velocity": hat_midi_vel, "duration": dur_short})
                hits.append({"beat": b + 1.5, "note": ho_note, "velocity": oh_midi_vel, "duration": dur_med})
                hits.append({"beat": b + 3.5, "note": ho_note, "velocity": oh_midi_vel, "duration": dur_med})
                if bar % 2 == 1:
                    hits.append({"beat": b, "note": crash_note, "velocity": crash_midi_vel, "duration": dur_long})

        elif section_type == "build":
            for bar in range(n_bars):
                b = bar * float(BEATS_PER_BAR)
                hits.append({"beat": b, "note": kick_note, "velocity": kick_midi_vel / PHI, "duration": dur_long})
                hits.append({"beat": b + 2.0, "note": kick_note, "velocity": kick_midi_vel / PHI, "duration": dur_long})
                div_idx = min(int(bar * len(fib_divisions) / max(n_bars, 1)), len(fib_divisions) - 1)
                divisions = fib_divisions[div_idx]
                step = float(BEATS_PER_BAR) / divisions
                for hit_i in range(divisions):
                    vel = (1.0 / PHI + snare_midi_vel / PHI) * (bar / max(n_bars, 1)) * (hit_i / max(divisions, 1))
                    vel = max(1.0 / PHI ** 4, vel)
                    hits.append({"beat": b + hit_i * step, "note": snare_note,
                                 "velocity": round(vel, 3), "duration": dur_short})

        elif section_type in ("intro", "outro"):
            for bar in range(n_bars):
                b = bar * float(BEATS_PER_BAR)
                hits.append({"beat": b, "note": kick_note, "velocity": kick_midi_vel / (PHI ** 2), "duration": dur_long})
                for q in range(BEATS_PER_BAR):
                    hits.append({"beat": b + q, "note": hc_note, "velocity": hat_midi_vel / PHI, "duration": dur_short})

        elif section_type == "bridge":
            for bar in range(n_bars):
                b = bar * float(BEATS_PER_BAR)
                hits.append({"beat": b, "note": kick_note, "velocity": kick_midi_vel / (PHI ** 3), "duration": dur_long})
                for q in range(BEATS_PER_BAR):
                    hits.append({"beat": b + q, "note": ride_note, "velocity": ride_midi_vel, "duration": dur_med})
                hits.append({"beat": b + 0.5, "note": hc_note, "velocity": hat_midi_vel / (PHI ** 2), "duration": dur_short})
                hits.append({"beat": b + 2.5, "note": hc_note, "velocity": hat_midi_vel / (PHI ** 2), "duration": dur_short})

        lm.hits = hits
        midi_maps.append(lm)

    log.info("LOOP MIDI MAPS: %d patterns (%s)",
             len(midi_maps), [m.section_type for m in midi_maps])
    return midi_maps


def _sketch_bass(dna: SongDNA, intent: dict[str, Any]) -> BassArsenal:
    """Synthesize bass one-shots for each type in the rotation.

    All envelope timing derived from phi ratios of the beat duration:
      beat_s = 60/bpm  →  attack = beat_s / phi^5, release = beat_s / phi^2
    FM ratios use phi and Fibonacci partials per DOCTRINE.
    """
    from engine.bass_oneshot import synthesize_sub_sine, synthesize_reese, BassPreset

    arsenal = BassArsenal()
    bd = dna.bass
    root = dna.root_freq
    beat_s = 60.0 / dna.bpm
    bass_intent = intent.get("bass", {})
    types_needed = bass_intent.get("types_needed", [bd.primary_type, bd.secondary_type])

    # ── Phi-derived envelope timing from beat duration ──
    phi_attack = beat_s / (PHI ** 5)     # ~0.005s at 150 BPM (fast transient)
    phi_release = beat_s / (PHI ** 2)    # ~0.153s at 150 BPM (tight release)
    phi_duration = beat_s * PHI          # ~0.647s at 150 BPM (one golden beat)
    sub_duration = beat_s * (PHI ** 2)   # ~1.047s at 150 BPM (sustained sub)
    reese_duration = beat_s * PHI        # ~0.647s at 150 BPM

    # ── Sub bass (always needed) ──
    sub_preset = BassPreset(
        name="sub", bass_type="sub_sine", frequency=root,
        duration_s=sub_duration, attack_s=phi_attack, release_s=phi_release * PHI,
        filter_cutoff=1.0 / (PHI ** 2)   # ~0.382 — warm sub cutoff
    )
    arsenal.sub = synthesize_sub_sine(sub_preset)
    arsenal.sources["sub"] = "synth:bass_oneshot:sub_sine"

    # ── Reese bass ──
    reese_preset = BassPreset(
        name="reese", bass_type="reese", frequency=root * 2,
        duration_s=reese_duration, detune_cents=PHI * 9.0,  # ~14.6 cents
        distortion=bd.distortion * 0.5,
        filter_cutoff=bd.filter_cutoff,
        attack_s=phi_attack, release_s=phi_release,
    )
    arsenal.reese = synthesize_reese(reese_preset)
    arsenal.sources["reese"] = "synth:bass_oneshot:reese"

    # ── Bass rotation sounds ──
    # FM ratios use phi and Fibonacci partials per DOCTRINE
    BASS_SYNTH_MAP = {
        "sub_sine": ("sub_sine", {"filter_cutoff": 1.0 / (PHI ** 2)}),
        "reese": ("reese", {"detune_cents": PHI * 9.0}),
        "dist_fm": ("fm", {"fm_ratio": PHI, "fm_depth": bd.fm_depth, "distortion": bd.distortion}),
        "fm": ("fm", {"fm_ratio": PHI, "fm_depth": bd.fm_depth}),
        "neuro": ("fm", {"fm_ratio": FIBONACCI[6] / FIBONACCI[5], "fm_depth": bd.fm_depth * PHI, "distortion": bd.distortion * 0.8}),
        "growl": ("fm", {"fm_ratio": PHI / 1.0, "fm_depth": bd.fm_depth * (PHI ** 2), "distortion": bd.distortion}),
        "sync": ("fm", {"fm_ratio": FIBONACCI[5] / FIBONACCI[4], "fm_depth": bd.fm_depth, "distortion": bd.distortion * (1.0 / PHI)}),
        "acid": ("fm", {"fm_ratio": 1.0, "fm_depth": 1.0 / PHI, "filter_cutoff": 1.0 / PHI + 0.3}),
        "formant": ("fm", {"fm_ratio": PHI, "fm_depth": bd.fm_depth * (1.0 / PHI)}),
        "fm_growl": ("fm", {"fm_ratio": PHI * 2, "fm_depth": bd.fm_depth * (PHI ** 2), "distortion": bd.distortion * PHI}),
    }

    for bass_type in types_needed:
        if bass_type in arsenal.sounds:
            continue
        synth_type, params = BASS_SYNTH_MAP.get(bass_type, ("fm", {"fm_depth": bd.fm_depth}))

        preset = BassPreset(
            name=bass_type, bass_type=synth_type,
            frequency=root * 2, duration_s=phi_duration,
            attack_s=phi_attack, release_s=phi_release,
            **params
        )

        if synth_type == "sub_sine":
            audio = synthesize_sub_sine(preset)
        elif synth_type == "reese":
            audio = synthesize_reese(preset)
        else:
            try:
                from engine.bass_oneshot import synthesize_fm_bass
                audio = synthesize_fm_bass(preset)
            except (ImportError, AttributeError):
                from engine.fm_synth import render_fm as render_fm_patch, FMPatch  # type: ignore[attr-defined]
                patch = FMPatch(name=bass_type)
                audio = render_fm_patch(patch, freq=root * 2, duration=0.8)

        if audio is not None:
            arr = np.asarray(audio, dtype=np.float64)
            dist_amount = params.get("distortion", 0.0)
            if dist_amount > 0.1:
                from engine.saturation import SaturationEngine, SatConfig
                sat = SaturationEngine(sample_rate=SR)
                arr = np.asarray(sat.saturate(arr.tolist(), SatConfig(
                    sat_type="aggressive" if dist_amount > 0.5 else "tape",
                    drive=dist_amount, mix=0.6
                )), dtype=np.float64)

            arsenal.sounds[bass_type] = _normalize(arr, 0.90)
            arsenal.sources[bass_type] = f"synth:bass_oneshot:{synth_type}"

    arsenal.rotation_order = list(types_needed)
    log.info("SKETCH BASS: %d types — %s",
             len(arsenal.sounds), "/".join(arsenal.sounds.keys()))
    return arsenal


def _sketch_leads(dna: SongDNA, intent: dict[str, Any]) -> LeadPalette:
    """Synthesize lead sounds at multiple pitches for arrangement.

    Phi-derived timing: duration = beat_s / phi (short stab), pluck = beat_s / phi^2.
    Filter cutoffs and resonance driven by LeadDNA brightness + intent overrides.
    FM ratio = phi per DOCTRINE.
    """
    from engine.lead_synth import (
        synthesize_screech_lead, synthesize_pluck_lead,
        synthesize_fm_lead, LeadPreset,
    )

    leads = LeadPalette()
    ld = dna.lead
    root = dna.root_freq
    beat_s = 60.0 / dna.bpm
    lead_intent = intent.get("leads", {})
    intervals = SCALE_INTERVALS.get(dna.scale, [0, 2, 3, 5, 7, 8, 10])

    # ── Phi-derived timing ──
    screech_dur = beat_s / PHI                    # ~0.247s at 150 BPM — snappy
    pluck_dur = beat_s / (PHI ** 2)               # ~0.153s at 150 BPM — tight pluck
    chord_dur = beat_s * PHI                      # ~0.647s at 150 BPM — sustained stab

    # ── DNA-driven filter from LeadDNA brightness ──
    lead_cutoff = lead_intent.get("filter_cutoff", _clamp(ld.brightness * 0.7 + 0.2))
    lead_resonance = lead_intent.get("resonance", _clamp(ld.brightness * 0.4 + 0.1))

    # Screech + FM leads at scale degrees (octave 3 and 4)
    for oct in (3, 4):
        for deg_idx, semi in enumerate(intervals[:5]):
            freq = root * (2.0 ** (oct - 1)) * (2.0 ** (semi / 12.0))

            if lead_intent.get("use_screech", True):
                preset = LeadPreset(
                    name=f"screech_d{deg_idx}_o{oct}", lead_type="screech",
                    frequency=freq, duration_s=screech_dur,
                    filter_cutoff=lead_cutoff,
                    resonance=lead_resonance,
                    distortion=0.0,
                )
                audio = synthesize_screech_lead(preset)
                leads.screech[freq] = _normalize(np.asarray(audio, dtype=np.float64), 0.85)

            if lead_intent.get("use_fm", ld.use_fm):
                preset = LeadPreset(
                    name=f"fm_d{deg_idx}_o{oct}", lead_type="fm_lead",
                    frequency=freq, duration_s=screech_dur,
                    fm_ratio=PHI, fm_depth=ld.fm_depth,
                    filter_cutoff=lead_cutoff,
                )
                audio = synthesize_fm_lead(preset)
                leads.fm_lead[freq] = _normalize(np.asarray(audio, dtype=np.float64), 0.80)

    # Pluck leads at root octaves (for arps)
    for oct in (3, 4, 5):
        freq = root * (2.0 ** (oct - 1))
        preset = LeadPreset(
            name=f"pluck_o{oct}", lead_type="pluck",
            frequency=freq, duration_s=pluck_dur,
            filter_cutoff=_clamp(ld.brightness * 0.5 + 0.4),
            resonance=_clamp(ld.brightness * 0.3 + 0.2),
        )
        audio = synthesize_pluck_lead(preset)
        leads.pluck[freq] = _normalize(np.asarray(audio, dtype=np.float64), 0.82)

    # Chord stabs (supersaw at root × 4) — phi-spaced detune
    try:
        chord_freq = root * 4
        preset_l = LeadPreset(
            name="chord_L", lead_type="screech",
            frequency=chord_freq, duration_s=chord_dur,
            detune_cents=PHI * 7.0,  # ~11.3 cents
            filter_cutoff=_clamp(ld.brightness * 0.4 + 0.3),
        )
        preset_r = LeadPreset(
            name="chord_R", lead_type="screech",
            frequency=chord_freq * (2.0 ** (7 / 12.0)),
            duration_s=chord_dur,
            detune_cents=PHI * 9.0,  # ~14.6 cents
            filter_cutoff=_clamp(ld.brightness * 0.4 + 0.3),
        )
        leads.chord_l = _normalize(np.asarray(synthesize_screech_lead(preset_l), dtype=np.float64), 0.75)
        leads.chord_r = _normalize(np.asarray(synthesize_screech_lead(preset_r), dtype=np.float64), 0.75)
        leads.sources["chords"] = "synth:lead_synth:screech"
    except Exception as exc:
        log.debug("SKETCH LEADS: chord stab failed: %s", exc)

    leads.sources["screech"] = "synth:lead_synth:screech"
    leads.sources["pluck"] = "synth:lead_synth:pluck"
    leads.sources["fm"] = "synth:lead_synth:fm_lead"

    log.info("SKETCH LEADS: %d screech, %d pluck, %d fm",
             len(leads.screech), len(leads.pluck), len(leads.fm_lead))
    return leads


def _sketch_atmosphere(dna: SongDNA, intent: dict[str, Any]) -> AtmosphereKit:
    """Synthesize pads, drones, and noise beds.

    Phi-derived timing: pad = Fibonacci[7] beats (13 beats ≈ 2 bars),
    drone = Fibonacci[8] beats (21 beats ≈ 5+ bars).
    Attack/release use phi ratios of bar duration.
    Brightness and reverb driven by AtmosphereDNA.
    """
    from engine.pad_synth import synthesize_dark_pad, synthesize_lush_pad, PadPreset
    from engine.noise_generator import synthesize_noise, NoisePreset

    atmos = AtmosphereKit()
    ad = dna.atmosphere
    root = dna.root_freq
    beat_s = 60.0 / dna.bpm
    bar_s = beat_s * BEATS_PER_BAR
    atmos_intent = intent.get("atmosphere", {})

    # ── Phi-derived timing ──
    pad_duration = bar_s * FIBONACCI[5]         # 8 bars — sustained texture
    drone_duration = bar_s * FIBONACCI[6]       # 13 bars — evolving drone
    noise_duration = bar_s * FIBONACCI[5]       # 8 bars — background bed
    phi_attack = bar_s / PHI                    # ~golden fraction of a bar
    phi_release = bar_s / (PHI ** 2) * PHI      # release proportional to bar

    # ── Dark pad — DNA-driven brightness ──
    dark_preset = PadPreset(
        name="dark_pad", pad_type="dark",
        frequency=root * 2, duration_s=pad_duration,
        filter_cutoff=_clamp(ad.pad_brightness * 0.5),
        brightness=_clamp(ad.pad_brightness * 0.4 + 0.1),
        reverb_amount=atmos_intent.get("reverb_amount", ad.reverb_decay / 10.0),
        attack_s=phi_attack, release_s=phi_release,
    )
    audio = synthesize_dark_pad(dark_preset)
    atmos.dark_pad = _normalize(np.asarray(audio, dtype=np.float64), 0.70)
    atmos.sources["dark_pad"] = "synth:pad_synth:dark"

    # ── Lush pad — DNA-driven brightness ──
    lush_preset = PadPreset(
        name="lush_pad", pad_type="lush",
        frequency=root * 4, duration_s=pad_duration,
        filter_cutoff=_clamp(ad.pad_brightness * 0.6 + 0.2),
        brightness=_clamp(ad.pad_brightness * 0.7 + 0.2),
        detune_cents=PHI * 7.0,  # ~11.3 cents — phi-spaced unison
        reverb_amount=atmos_intent.get("reverb_amount", ad.reverb_decay / 10.0),
        attack_s=phi_attack * (1.0 / PHI),  # slightly faster attack for lush
        release_s=phi_release,
    )
    audio = synthesize_lush_pad(lush_preset)
    atmos.lush_pad = _normalize(np.asarray(audio, dtype=np.float64), 0.65)
    atmos.sources["lush_pad"] = "synth:pad_synth:lush"

    # ── Drone — phi LFO rate for evolving movement ──
    try:
        from engine.drone_synth import synthesize_drone, DronePreset
        drone_preset = DronePreset(
            name="drone", drone_type="evolving", frequency=root,
            duration_s=drone_duration,
            brightness=_clamp(ad.pad_brightness * 0.3),
        )
        audio = synthesize_drone(drone_preset)
        atmos.drone = _normalize(np.asarray(audio, dtype=np.float64), 0.50)
        atmos.sources["drone"] = "synth:drone_synth"
    except Exception:
        t = np.linspace(0, drone_duration, int(drone_duration * SR), endpoint=False)
        drone = np.sin(2 * np.pi * root * t) * 0.3
        # Phi-rate LFO modulation on drone amplitude
        lfo_rate = (dna.bpm / 60.0) / (PHI ** 3)  # very slow phi-scaled LFO
        drone *= 0.5 + 0.5 * np.sin(2 * np.pi * lfo_rate * t)
        atmos.drone = _normalize(drone, 0.50)
        atmos.sources["drone"] = "synth:sine_fallback"

    # ── Noise bed — DNA-driven type and brightness ──
    noise_type = atmos_intent.get("noise_bed", ad.noise_bed_type)
    valid_types = ("white", "pink", "brown", "vinyl", "tape")
    noise_preset = NoisePreset(
        name="noise_bed", noise_type=noise_type if noise_type in valid_types else "pink",
        duration_s=noise_duration,
        brightness=_clamp(ad.pad_brightness * 0.4),
        gain=_clamp(0.2 + (1.0 - ad.pad_brightness) * 0.3),
        attack_s=phi_attack, release_s=phi_release,
    )
    audio = synthesize_noise(noise_preset)
    atmos.noise_bed = _normalize(np.asarray(audio, dtype=np.float64), 0.40)
    atmos.sources["noise_bed"] = f"synth:noise_generator:{noise_type}"

    log.info("SKETCH ATMOS: dark_pad + lush_pad + drone + %s noise (pad=%.1fs, drone=%.1fs)",
             noise_type, pad_duration, drone_duration)
    return atmos


def _sketch_fx(dna: SongDNA, intent: dict[str, Any],
                galactia_fx: GalactiaFxSamples) -> FxKit:
    """Build FX kit from Galactia samples + synthesized transitions."""
    from engine.riser_synth import synthesize_noise_sweep, synthesize_pitch_rise, RiserPreset
    from engine.impact_hit import synthesize_sub_boom, synthesize_reverse_hit, ImpactPreset
    from engine.transition_fx import (
        synthesize_tape_stop, synthesize_gate_chop,
        synthesize_pitch_dive, TransitionPreset,
    )
    from engine.glitch_engine import synthesize_stutter, GlitchPreset

    fx = FxKit()
    fd = dna.fx
    fx_intent = intent.get("fx", {})
    beat_s = 60.0 / dna.bpm
    bar_s = beat_s * BEATS_PER_BAR

    # ── DNA/phi-derived timing ──
    riser_dur = bar_s * PHI                 # ~1 bar × phi
    boom_dur = bar_s / PHI                  # sub-bar impact
    rev_dur = beat_s * PHI                  # reverse hit: beat × phi
    rise_dur = bar_s / PHI                  # pitch rise
    tape_dur = beat_s                       # 1 beat tape stop
    dive_dur = beat_s / PHI                 # quick pitch dive
    chop_dur = bar_s / PHI                  # gate chop
    stutter_dur = beat_s                    # 1 beat stutter

    # DNA-driven gains (defaults from fx_intent or phi-scaled)
    riser_gain = fx_intent.get("riser_gain", 1.0 / PHI)
    boom_gain = fx_intent.get("boom_gain", 1.0 / PHI + 0.1)
    rev_gain = fx_intent.get("reverse_gain", 1.0 / PHI)
    hit_gain = fx_intent.get("hit_gain", 1.0 / PHI)
    tape_gain = fx_intent.get("tape_gain", 1.0 / PHI)
    dive_gain = fx_intent.get("dive_gain", 1.0 / PHI)
    chop_gain = fx_intent.get("chop_gain", 1.0 / PHI)
    stutter_gain = fx_intent.get("stutter_gain", 1.0 / PHI)
    galactia_gain = fx_intent.get("galactia_gain", 1.0 / (PHI ** 2) + 0.3)

    # ── Riser: prefer Galactia ──
    if galactia_fx.risers:
        fx.riser = _normalize(galactia_fx.risers[0], riser_gain)
        fx.sources["riser"] = f"galactia:{galactia_fx.sources.get('risers', ['?'])[0]}"
    else:
        riser_preset = RiserPreset(
            name="riser", riser_type="noise_sweep",
            duration_s=riser_dur,
            start_freq=fx_intent.get("riser_start_freq", fd.riser_start_freq),
            end_freq=fx_intent.get("riser_end_freq", fd.riser_end_freq),
            intensity=fd.riser_intensity if hasattr(fd, "riser_intensity") else 0.8,
        )
        audio = synthesize_noise_sweep(riser_preset)
        fx.riser = _normalize(np.asarray(audio, dtype=np.float64), riser_gain)
        fx.sources["riser"] = "synth:riser_synth:noise_sweep"

    # ── Boom/impact: prefer Galactia ──
    if galactia_fx.impacts:
        fx.boom = _normalize(galactia_fx.impacts[0], boom_gain)
        fx.sources["boom"] = f"galactia:{galactia_fx.sources.get('impacts', ['?'])[0]}"
    else:
        boom_preset = ImpactPreset(
            name="boom", impact_type="sub_boom",
            duration_s=boom_dur, frequency=dna.root_freq,
            intensity=fx_intent.get("impact_intensity", fd.impact_intensity),
        )
        audio = synthesize_sub_boom(boom_preset)
        fx.boom = _normalize(np.asarray(audio, dtype=np.float64), boom_gain)
        fx.sources["boom"] = "synth:impact_hit:sub_boom"

    # ── Reverse hit: prefer Galactia ──
    if galactia_fx.reverses:
        fx.rev_crash = _normalize(galactia_fx.reverses[0], rev_gain)
        fx.sources["rev_crash"] = f"galactia:{galactia_fx.sources.get('reverses', ['?'])[0]}"
    else:
        rev_preset = ImpactPreset(
            name="rev", impact_type="reverse_hit",
            duration_s=rev_dur, frequency=dna.root_freq * PHI,
        )
        audio = synthesize_reverse_hit(rev_preset)
        fx.rev_crash = _normalize(np.asarray(audio, dtype=np.float64), rev_gain)
        fx.sources["rev_crash"] = "synth:impact_hit:reverse_hit"

    # ── Pitch rise (Galactia rising samples) ──
    if galactia_fx.rising:
        fx.hit = _normalize(galactia_fx.rising[0], hit_gain)
        fx.sources["hit"] = f"galactia:{galactia_fx.sources.get('rising', ['?'])[0]}"
    else:
        rise_preset = RiserPreset(
            name="pitch_rise", riser_type="pitch_rise",
            duration_s=rise_dur,
            start_freq=fd.riser_start_freq,
            end_freq=fd.riser_end_freq,
        )
        audio = synthesize_pitch_rise(rise_preset)
        fx.hit = _normalize(np.asarray(audio, dtype=np.float64), hit_gain)
        fx.sources["hit"] = "synth:riser_synth:pitch_rise"

    # ── Tape stop ──
    ts_preset = TransitionPreset(
        name="tape_stop", fx_type="tape_stop",
        duration_s=tape_dur, start_freq=dna.root_freq * PHI,
    )
    audio = synthesize_tape_stop(ts_preset)
    fx.tape_stop = _normalize(np.asarray(audio, dtype=np.float64), tape_gain)
    fx.sources["tape_stop"] = "synth:transition_fx:tape_stop"

    # ── Pitch dive ──
    pd_preset = TransitionPreset(
        name="pitch_dive", fx_type="pitch_dive",
        duration_s=dive_dur,
        start_freq=dna.root_freq * (PHI ** 3), end_freq=dna.root_freq,
    )
    audio = synthesize_pitch_dive(pd_preset)
    fx.pitch_dive = _normalize(np.asarray(audio, dtype=np.float64), dive_gain)
    fx.sources["pitch_dive"] = "synth:transition_fx:pitch_dive"

    # ── Gate chop ──
    gc_preset = TransitionPreset(
        name="gate_chop", fx_type="gate_chop",
        duration_s=chop_dur, gate_divisions=int(fd.stutter_rate),
    )
    audio = synthesize_gate_chop(gc_preset)
    fx.gate_chop = _normalize(np.asarray(audio, dtype=np.float64), chop_gain)
    fx.sources["gate_chop"] = "synth:transition_fx:gate_chop"

    # ── Stutter ──
    st_preset = GlitchPreset(
        name="stutter", glitch_type="stutter",
        duration_s=stutter_dur, rate=fd.stutter_rate, depth=fd.riser_intensity if hasattr(fd, "riser_intensity") else 0.8,
    )
    audio = synthesize_stutter(st_preset)
    fx.stutter = _normalize(np.asarray(audio, dtype=np.float64), stutter_gain)
    fx.sources["stutter"] = "synth:glitch_engine:stutter"

    # ── Pass through Galactia falling/rising/shepard samples ──
    fx.fx_falling = [_normalize(s, galactia_gain) for s in galactia_fx.falling]
    fx.fx_rising = [_normalize(s, galactia_gain) for s in galactia_fx.rising]
    fx.shepard_tones = [_normalize(s, galactia_gain * 0.9) for s in galactia_fx.shepard]

    log.info("SKETCH FX: riser=%s boom=%s + %d falling, %d rising, %d shepard",
             fx.sources.get("riser", "?"), fx.sources.get("boom", "?"),
             len(fx.fx_falling), len(fx.fx_rising), len(fx.shepard_tones))
    return fx


def _sketch_vocals(dna: SongDNA, intent: dict[str, Any]) -> VocalKit:
    """Synthesize vocal chops for each vowel in the DNA."""
    from engine.vocal_chop import synthesize_chop, VocalChop

    vox = VocalKit()
    vocal_intent = intent.get("vocals", {})
    vowels = vocal_intent.get("vowels", ["ah", "oh", "ee", "oo"])
    distortion = vocal_intent.get("distortion", 0.0)
    beat_s = 60.0 / dna.bpm

    # ── Phi-derived vocal timing ──
    chop_dur = beat_s / (PHI ** 2)          # quick chop: beat / phi^2
    chop_attack = beat_s / (PHI ** 5)       # sub-ms click avoidance
    chop_release = beat_s / (PHI ** 3)      # smooth tail
    chop_gain = vocal_intent.get("chop_gain", 1.0 / PHI)

    for vowel in vowels:
        chop = VocalChop(
            name=f"chop_{vowel}", vowel=vowel, note="C4",
            duration_s=chop_dur, attack_s=chop_attack, release_s=chop_release,
            distortion=distortion,
        )
        audio = synthesize_chop(chop)
        vox.chops[vowel] = _normalize(np.asarray(audio, dtype=np.float64), chop_gain)
        vox.sources[vowel] = f"synth:vocal_chop:{vowel}"

    vox.vowels = vowels
    log.info("SKETCH VOCALS: %d vowels — %s", len(vox.chops), "/".join(vowels))
    return vox


def _sketch_melody(dna: SongDNA, chord_prog: Any) -> MelodyKit:
    """Generate lead melody and arp patterns from the chord progression.

    Order dependency: requires chord_progression from DESIGN step.
    The melody follows the chord tones, arps follow the root notes.
    """
    kit = MelodyKit()

    # ── DNA-driven melody parameters ──
    melody_notes = FIBONACCI[5]             # 8 notes per phrase (Fibonacci)
    melody_complexity = getattr(dna.lead, "complexity", 0.5)
    melody_octave = getattr(dna.lead, "octave", 4)
    melody_gain = 1.0 / PHI                # phi-scaled gain

    # ── Lead melody via Markov chain ──
    try:
        from engine.markov_melody import MarkovMelody, render_melody

        mm = MarkovMelody(key=dna.key, scale=dna.scale, octave=melody_octave, seed=dna.seed)
        melody = mm.generate(n_notes=melody_notes, rhythm_complexity=melody_complexity)
        melody.bpm = float(dna.bpm)

        audio = render_melody(melody, sample_rate=SR)
        kit.lead_melody = _normalize(np.asarray(audio, dtype=np.float64), melody_gain)
        kit.lead_melody_notes = melody.notes
        kit.sources["lead_melody"] = "synth:markov_melody"
        log.info("SKETCH MELODY: %d notes, %.1fs",
                 len(melody.notes), len(kit.lead_melody) / SR)
    except Exception as exc:
        log.warning("SKETCH MELODY: markov_melody unavailable (%s)", exc)

    # ── Arp patterns ──
    try:
        from engine.arp_synth import synthesize_arp, ArpSynthPreset

        root = dna.root_freq
        beat_s = 60.0 / dna.bpm
        bar_duration = beat_s * BEATS_PER_BAR

        # DNA-driven arp parameters
        arp_cutoff = getattr(dna.lead, "filter_cutoff", 0.5)
        arp_res = getattr(dna.lead, "resonance", 0.3)
        arp_gain = 1.0 / PHI - 0.1
        arp_steps_a = FIBONACCI[4]          # 5 steps
        arp_steps_b = FIBONACCI[5]          # 8 steps

        arp_configs = [
            ("pulse_arp", "pulse", root * PHI, arp_cutoff, arp_res, arp_steps_b),
            ("saw_arp", "saw", root * PHI, arp_cutoff * 0.9, arp_res + 0.1, arp_steps_b),
            ("pluck_arp", "pluck", root * PHI, arp_cutoff + 0.1, arp_res * 0.7, arp_steps_b * 2),
        ]
        if getattr(dna.lead, "use_fm", False):
            arp_configs.append(("fm_arp", "fm", root * PHI, arp_cutoff, arp_res, arp_steps_b))

        for name, atype, freq, cutoff, res, steps in arp_configs:
            preset = ArpSynthPreset(
                name=name, arp_type=atype, base_freq=freq,
                duration_s=bar_duration * PHI,
                step_count=steps, filter_cutoff=cutoff,
                resonance=res, octave_range=2,
            )
            audio = synthesize_arp(preset, sample_rate=SR)
            kit.arp_patterns[name] = _normalize(np.asarray(audio, dtype=np.float64), arp_gain)
            kit.sources[name] = f"synth:arp_synth:{atype}"

        log.info("SKETCH ARPS: %d patterns — %s",
                 len(kit.arp_patterns), "/".join(kit.arp_patterns.keys()))
    except Exception as exc:
        log.warning("SKETCH ARPS: arp_synth unavailable (%s)", exc)

    return kit


def _sketch_wobble_bass(dna: SongDNA) -> WobbleBassKit:
    """Synthesize wobble bass patterns — LFO-modulated bass for drops.

    Order dependency: uses root_freq and BPM from DNA.
    """
    kit = WobbleBassKit()

    try:
        from engine.wobble_bass import synthesize_wobble, WobblePreset

        root = dna.root_freq
        bd = dna.bass
        beat_s = 60.0 / dna.bpm
        bar_duration = beat_s * BEATS_PER_BAR

        # ── LFO rates: center from bd.lfo_rate (measured wobble_rate_hz), phi-scaled variants ──
        bps = dna.bpm / 60.0                       # beats per second
        _wobble_lfo_rate = bd.lfo_rate if bd.lfo_rate > 0 else bps * PHI
        lfo_classic = _wobble_lfo_rate              # center rate from analyzer
        lfo_slow = _wobble_lfo_rate / PHI           # slower variant
        lfo_fast = _wobble_lfo_rate * PHI           # faster variant
        lfo_vowel = _wobble_lfo_rate / (PHI ** 2)   # slowest variant

        # ── DNA-driven resonance and gain ──
        wobble_res = getattr(bd, "resonance", 1.0 / PHI)
        wobble_gain = 1.0 - 1.0 / (PHI ** 3)       # ~0.764

        wobble_configs = [
            ("classic", "classic", lfo_classic, 0.8, bd.filter_cutoff, bd.distortion * (1.0 / PHI)),
            ("slow", "slow",       lfo_slow,    0.9, bd.filter_cutoff * 0.9, bd.distortion / (PHI ** 2)),
            ("fast", "fast",       lfo_fast,    0.7, bd.filter_cutoff * 1.1, bd.distortion * (1.0 / PHI + 0.1)),
            ("vowel", "vowel",     lfo_vowel,   0.85, bd.filter_cutoff * 0.8, bd.distortion / PHI),
        ]

        for name, wtype, rate, depth, cutoff, dist in wobble_configs:
            preset = WobblePreset(
                name=f"wobble_{name}", wobble_type=wtype,
                frequency=root * PHI, duration_s=bar_duration * FIBONACCI[5],
                lfo_rate=rate, lfo_depth=depth,
                filter_cutoff=cutoff, resonance=wobble_res,
                distortion=dist, sub_mix=bd.sub_weight,
            )
            audio = synthesize_wobble(preset, sample_rate=SR)
            kit.patterns[name] = _normalize(np.asarray(audio, dtype=np.float64), wobble_gain)
            kit.sources[name] = f"synth:wobble_bass:{wtype}"

        log.info("SKETCH WOBBLE: %d patterns — %s",
                 len(kit.patterns), "/".join(kit.patterns.keys()))
    except Exception as exc:
        log.warning("SKETCH WOBBLE: wobble_bass unavailable (%s)", exc)

    return kit


def _sketch_riddim_bass(dna: SongDNA) -> RiddimBassKit:
    """Synthesize riddim bass patterns — rhythmic gaps for drop sections.

    Order dependency: uses root_freq and BPM from DNA.
    """
    kit = RiddimBassKit()

    try:
        from engine.riddim_engine import generate_riddim, RiddimPreset

        root = dna.root_freq
        bd = dna.bass
        beat_s = 60.0 / dna.bpm
        bar_duration = beat_s * BEATS_PER_BAR

        # ── DNA-driven gap ratio from bd.riddim_gap_ratio (style density + onset_rate) ──
        base_gap = bd.riddim_gap_ratio if bd.riddim_gap_ratio > 0 else 1.0 / PHI
        riddim_gain = 1.0 - 1.0 / (PHI ** 3)          # ~0.764

        riddim_configs = [
            ("minimal", "minimal", base_gap,              FIBONACCI[3], bd.distortion / PHI),
            ("heavy",   "heavy",   base_gap / PHI,        FIBONACCI[3], bd.distortion),
            ("bounce",  "bounce",  base_gap * (1.0/PHI),  FIBONACCI[3], bd.distortion * (1.0/PHI)),
            ("stutter", "stutter", base_gap - 0.05,       FIBONACCI[5], bd.distortion / PHI + 0.1),
        ]

        for name, rtype, gap, subs, dist in riddim_configs:
            preset = RiddimPreset(
                name=f"riddim_{name}", riddim_type=rtype,
                frequency=root * PHI, duration_s=bar_duration * FIBONACCI[5],
                gap_ratio=gap, distortion=dist,
                subdivisions=subs, bpm=float(dna.bpm),
            )
            audio = generate_riddim(preset, sample_rate=SR)
            kit.patterns[name] = _normalize(np.asarray(audio, dtype=np.float64), riddim_gain)
            kit.sources[name] = f"synth:riddim_engine:{rtype}"

        log.info("SKETCH RIDDIM: %d patterns — %s",
                 len(kit.patterns), "/".join(kit.patterns.keys()))
    except Exception as exc:
        log.warning("SKETCH RIDDIM: riddim_engine unavailable (%s)", exc)

    return kit


def _sketch_growl_textures(dna: SongDNA) -> GrowlKit:
    """Generate growl-resampled wavetable frames for mid-bass textures.

    Order dependency: uses root_freq from DNA. These are single-cycle frames
    that Phase 2 can pitch and sequence across the arrangement.
    """
    kit = GrowlKit()

    try:
        from engine.growl_resampler import (
            growl_resample_pipeline, generate_saw_source, generate_fm_source,
        )

        # Generate from FM source (phi ratio = classic dubstep growl)
        source = generate_fm_source(
            fm_ratio=PHI, fm_depth=dna.bass.fm_depth * PHI,
        )
        frames = growl_resample_pipeline(source, n_output_frames=64)
        kit.frames = frames
        kit.source_type = "fm_phi"
        kit.sources["growl_frames"] = "synth:growl_resampler:fm_phi"
        log.info("SKETCH GROWL: %d wavetable frames from FM source", len(frames))

    except Exception as exc:
        log.warning("SKETCH GROWL: growl_resampler unavailable (%s)", exc)

    return kit


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1f: RACK — Pack everything into the 128 Rack
# ═══════════════════════════════════════════════════════════════════════════

def _build_128_rack(drums: DrumKit,
                     galactia_fx: GalactiaFxSamples) -> Rack128:
    """Pack drums + FX samples into the 128 Rack.  Synth stems are separate
    WAV tracks from Stage 4 — they do NOT belong in the rack.

    Zone layout matches dojo.py build_128_rack() — 14 Fibonacci-sized categories.
    """
    rack = Rack128()
    counts: dict[str, int] = {z: 0 for z in _ZONE_IDX}
    add = lambda z, n, a, s: _rack_add(rack, counts, z, n, a, s)

    # ── Drums ──
    if drums.kick is not None:
        add("kicks", "drum_kick", drums.kick, drums.kick_source)
    if drums.snare is not None:
        add("snares", "drum_snare", drums.snare, drums.snare_source)
    if drums.clap is not None:
        add("snares", "drum_clap", drums.clap, drums.clap_source)
    if drums.hat_closed is not None:
        add("hats", "drum_hat_closed", drums.hat_closed, drums.hat_closed_source)
    if drums.hat_open is not None:
        add("hats", "drum_hat_open", drums.hat_open, drums.hat_open_source)
    if drums.crash is not None:
        add("perc", "drum_crash", drums.crash, drums.crash_source)
    if drums.ride is not None:
        add("perc", "drum_ride", drums.ride, drums.ride_source)
    if drums.perc is not None:
        add("perc", "drum_perc", drums.perc, drums.perc_source)

    # ── FX samples from Galactia ──
    if galactia_fx:
        for i, audio in enumerate(galactia_fx.risers[:5]):
            add("fx", f"riser_{i}", audio, galactia_fx.sources.get("risers", ["galactia"])[min(i, len(galactia_fx.sources.get("risers", []))-1)] if galactia_fx.sources.get("risers") else "galactia")
        for i, audio in enumerate(galactia_fx.impacts[:5]):
            add("fx", f"impact_{i}", audio, "galactia:impact")
        for i, audio in enumerate(galactia_fx.falling[:3]):
            add("fx", f"falling_{i}", audio, "galactia:falling")
        for i, audio in enumerate(galactia_fx.rising[:3]):
            add("fx", f"rising_{i}", audio, "galactia:rising")
        for i, audio in enumerate(galactia_fx.shepard[:2]):
            add("fx", f"shepard_{i}", audio, "galactia:shepard")
        for i, audio in enumerate(galactia_fx.buildups[:3]):
            add("transitions", f"buildup_{i}", audio, "galactia:buildup")

    rack.zone_counts = counts
    filled = sum(counts.values())
    zone_str = " | ".join(f"{z}={c}" for z, c in counts.items() if c > 0)
    log.info("RACK 128: %d/128 filled — %s", filled, zone_str)
    return rack


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 4 — SYNTH FACTORY: DNA-driven modulation + FX chain design
# ═══════════════════════════════════════════════════════════════════════════

# ── Mood / style → profile tables ──

_MOOD_MODULATION_PROFILES: dict[str, dict[str, Any]] = {
    "dark": {
        "lfo_type": "sine",
        "lfo_rate_scale": 0.7,
        "sidechain_shape": "pump",
        "saturation_type": "tube",
        "reverb_type": "hall",
        "stereo_type": "mid_side",
        "wave_fold_algo": "tanh",
        "pitch_auto_type": "dive",
        "chaos": 0.3,
    },
    "aggressive": {
        "lfo_type": "saw",
        "lfo_rate_scale": 1.2,
        "sidechain_shape": "hard_cut",
        "saturation_type": "hard",
        "reverb_type": "plate",
        "stereo_type": "haas",
        "wave_fold_algo": "multi",
        "pitch_auto_type": "dive",
        "chaos": 0.6,
    },
    "dreamy": {
        "lfo_type": "triangle",
        "lfo_rate_scale": 0.5,
        "sidechain_shape": "smooth",
        "saturation_type": "tape",
        "reverb_type": "shimmer",
        "stereo_type": "psychoacoustic",
        "wave_fold_algo": "sinusoidal",
        "pitch_auto_type": "glide",
        "chaos": 0.2,
    },
    "ethereal": {
        "lfo_type": "triangle",
        "lfo_rate_scale": 0.4,
        "sidechain_shape": "smooth",
        "saturation_type": "soft",
        "reverb_type": "shimmer",
        "stereo_type": "psychoacoustic",
        "wave_fold_algo": "sinusoidal",
        "pitch_auto_type": "glide",
        "chaos": 0.15,
    },
    "intense": {
        "lfo_type": "saw",
        "lfo_rate_scale": 1.0,
        "sidechain_shape": "hard_cut",
        "saturation_type": "transistor",
        "reverb_type": "room",
        "stereo_type": "frequency_split",
        "wave_fold_algo": "multi",
        "pitch_auto_type": "dive",
        "chaos": 0.5,
    },
    "mystic": {
        "lfo_type": "sine",
        "lfo_rate_scale": 0.6,
        "sidechain_shape": "phi_curve",
        "saturation_type": "phi",
        "reverb_type": "hall",
        "stereo_type": "phase",
        "wave_fold_algo": "phi",
        "pitch_auto_type": "wobble",
        "chaos": 0.35,
    },
    "sacred": {
        "lfo_type": "sine",
        "lfo_rate_scale": 0.5,
        "sidechain_shape": "phi_curve",
        "saturation_type": "console",
        "reverb_type": "hall",
        "stereo_type": "mid_side",
        "wave_fold_algo": "phi",
        "pitch_auto_type": "glide",
        "chaos": 0.2,
    },
    "euphoric": {
        "lfo_type": "triangle",
        "lfo_rate_scale": 0.8,
        "sidechain_shape": "pump",
        "saturation_type": "tape",
        "reverb_type": "plate",
        "stereo_type": "haas",
        "wave_fold_algo": "standard",
        "pitch_auto_type": "rise",
        "chaos": 0.25,
    },
}

_STYLE_MODULATION_OVERRIDES: dict[str, dict[str, Any]] = {
    "riddim": {
        "sidechain_shape": "hard_cut",
        "lfo_rate_scale": 1.5,
        "saturation_type": "hard",
        "wave_fold_algo": "multi",
    },
    "melodic": {
        "reverb_type": "shimmer",
        "stereo_type": "psychoacoustic",
        "lfo_rate_scale": 0.6,
    },
    "tearout": {
        "saturation_type": "hard",
        "sidechain_shape": "hard_cut",
        "wave_fold_algo": "multi",
        "chaos": 0.7,
    },
    "hybrid": {
        "lfo_type": "sample_hold",
        "wave_fold_algo": "multi",
        "chaos": 0.5,
    },
}


def _resolve_profile(dna: SongDNA) -> dict[str, Any]:
    """Merge mood profile + style overrides → resolved modulation profile."""
    mood = getattr(dna, "mood_name", "dark").lower()
    style = dna.style.lower()
    profile = dict(_MOOD_MODULATION_PROFILES.get(mood, _MOOD_MODULATION_PROFILES["dark"]))
    overrides = _STYLE_MODULATION_OVERRIDES.get(style, {})
    profile.update(overrides)
    return profile


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _design_modulation_routes(
    dna: SongDNA,
    intent: dict[str, Any],
) -> dict[str, Any]:
    """DNA-driven Serum 2 modulation routing per stem type.

    Returns a dict keyed by stem ("bass", "lead", "pad", "fx") where each
    value contains Serum 2 mod-matrix routes + LFO configs derived from
    the track's SongDNA rather than static/generic defaults.
    """
    from engine.serum2 import ModulationRoute
    from engine.lfo_matrix import LFOPreset

    profile = _resolve_profile(dna)
    bd = dna.bass
    ld = dna.lead
    ad = dna.atmosphere
    fd = dna.fx
    energy = getattr(dna, "energy", 0.7)
    bpm = dna.bpm

    # ── Derive per-stem LFO rates from BPM + profile scale ──
    beat_hz = bpm / 60.0
    base_rate = beat_hz * profile["lfo_rate_scale"]

    # ── Bass LFO: prefer analyzer-measured wobble rate over BPM-derived default ──
    _bass_lfo_rate = bd.lfo_rate if bd.lfo_rate > 0 else base_rate * 0.5
    _bass_lfo_depth = bd.lfo_depth if bd.lfo_depth > 0 else None  # None = use computed depth

    routes: dict[str, Any] = {}

    # ──────────────────────────────────────────────────────────────────
    # BASS modulation — driven by BassDNA
    # ──────────────────────────────────────────────────────────────────
    bass_filter_mod = _clamp(bd.filter_cutoff * 0.8 + energy * 0.2)
    bass_wt_mod = _clamp(bd.distortion * 0.6 + bd.fm_depth * 0.4)
    bass_growl_depth = _clamp(bd.mid_drive * 0.5 + bd.ott_amount * 0.3 + profile["chaos"] * 0.2)

    routes["bass"] = {
        "mod_matrix": [
            ModulationRoute(
                source="LFO 1",
                destination="Filter 1 Cutoff",
                amount=bass_filter_mod,
                curve=_clamp(bd.distortion * 0.5),
                polarity_bipolar=True,
                aux_source="Velocity",
                output_scale=_clamp(energy),
            ),
            ModulationRoute(
                source="LFO 2",
                destination="Osc A WT Pos",
                amount=bass_wt_mod,
                curve=0.0,
                polarity_bipolar=True,
                aux_source="Macro 1",
                output_scale=1.0,
            ),
            ModulationRoute(
                source="ENV 2",
                destination="Filter 1 Cutoff",
                amount=_clamp(0.5 + bd.filter_cutoff * 0.5),
                curve=_clamp(bd.distortion * 0.3),
                polarity_bipolar=False,
            ),
            ModulationRoute(
                source="Macro 4",
                destination="Osc A WT Pos",
                amount=bass_growl_depth,
                curve=0.0,
                polarity_bipolar=True,
                aux_source="LFO 3",
                output_scale=_clamp(energy * 0.8),
            ),
            ModulationRoute(
                source="Velocity",
                destination="Filter 1 Cutoff",
                amount=_clamp(0.2 + bd.distortion * 0.3),
                curve=0.0,
                polarity_bipolar=False,
            ),
        ],
        "lfos": [
            LFOPreset(
                name="Bass Filter LFO",
                lfo_type=profile["lfo_type"],
                rate_hz=_bass_lfo_rate,
                depth=_bass_lfo_depth if _bass_lfo_depth is not None else bass_filter_mod,
                sync_bpm=float(bpm),
                sync_division=2.0,
                polarity="bipolar",
            ),
            LFOPreset(
                name="Bass WT Morph",
                lfo_type=profile["lfo_type"],
                rate_hz=_bass_lfo_rate * 0.5,
                depth=bass_wt_mod,
                sync_bpm=float(bpm),
                sync_division=4.0,
                polarity="unipolar",
            ),
            LFOPreset(
                name="Bass Growl",
                lfo_type="saw" if bd.mid_drive > 0.5 else profile["lfo_type"],
                rate_hz=_bass_lfo_rate * 2.0,
                depth=bass_growl_depth,
                sync_bpm=float(bpm),
                sync_division=1.0,
                polarity="bipolar",
            ),
        ],
    }

    # ──────────────────────────────────────────────────────────────────
    # LEAD modulation — driven by LeadDNA
    # ──────────────────────────────────────────────────────────────────
    lead_brightness_mod = _clamp(ld.brightness * 0.7 + energy * 0.3)
    lead_fm_mod = _clamp(ld.fm_depth * 0.8) if ld.use_fm else 0.0
    lead_reverb_send = _clamp(ld.reverb_decay / 8.0)

    routes["lead"] = {
        "mod_matrix": [
            ModulationRoute(
                source="LFO 1",
                destination="Filter 1 Cutoff",
                amount=lead_brightness_mod,
                curve=0.0,
                polarity_bipolar=True,
                aux_source="Mod Wheel",
                output_scale=_clamp(ld.brightness),
            ),
            ModulationRoute(
                source="ENV 2",
                destination="Filter 1 Cutoff",
                amount=_clamp(ld.brightness * 0.6),
                curve=0.2,
                polarity_bipolar=False,
            ),
            ModulationRoute(
                source="LFO 2",
                destination="Osc A WT Pos",
                amount=_clamp(ld.brightness * 0.4 + energy * 0.2),
                curve=0.0,
                polarity_bipolar=True,
                aux_source="Macro 1",
                output_scale=1.0,
            ),
            ModulationRoute(
                source="Macro 2",
                destination="Osc B FM Depth",
                amount=lead_fm_mod,
                curve=0.0,
                polarity_bipolar=False,
            ),
            ModulationRoute(
                source="Velocity",
                destination="Filter 1 Cutoff",
                amount=_clamp(0.15 + ld.brightness * 0.25),
                curve=0.0,
                polarity_bipolar=False,
            ),
        ],
        "lfos": [
            LFOPreset(
                name="Lead Filter Sweep",
                lfo_type="triangle",
                rate_hz=base_rate * 0.25,
                depth=lead_brightness_mod * 0.7,
                sync_bpm=float(bpm),
                sync_division=4.0,
                polarity="bipolar",
            ),
            LFOPreset(
                name="Lead Vibrato",
                lfo_type="sine",
                rate_hz=5.5,
                depth=0.15,
                polarity="bipolar",
            ),
        ],
    }

    # ──────────────────────────────────────────────────────────────────
    # PAD modulation — driven by AtmosphereDNA
    # ──────────────────────────────────────────────────────────────────
    pad_stereo_mod = _clamp(ad.stereo_width)
    pad_reverb_mod = _clamp(ad.reverb_decay / 8.0)
    pad_brightness_mod = _clamp(ad.pad_brightness * 0.6 + energy * 0.15)

    routes["pad"] = {
        "mod_matrix": [
            ModulationRoute(
                source="LFO 1",
                destination="Osc A WT Pos",
                amount=pad_brightness_mod,
                curve=0.0,
                polarity_bipolar=True,
                aux_source="Macro 1",
                output_scale=1.0,
            ),
            ModulationRoute(
                source="LFO 2",
                destination="Filter 1 Cutoff",
                amount=_clamp(ad.pad_brightness * 0.5),
                curve=0.0,
                polarity_bipolar=True,
                aux_source="Mod Wheel",
                output_scale=0.8,
            ),
            ModulationRoute(
                source="ENV 2",
                destination="Filter 1 Cutoff",
                amount=_clamp(0.3 + ad.pad_brightness * 0.4),
                curve=0.1,
                polarity_bipolar=False,
            ),
        ],
        "lfos": [
            LFOPreset(
                name="Pad Drift",
                lfo_type="sine",
                rate_hz=base_rate * 0.125,
                depth=pad_brightness_mod * 0.5,
                sync_bpm=float(bpm),
                sync_division=8.0,
                polarity="bipolar",
            ),
        ],
    }

    # ──────────────────────────────────────────────────────────────────
    # FX modulation — driven by FxDNA
    # ──────────────────────────────────────────────────────────────────
    fx_intensity = _clamp(fd.riser_intensity * 0.5 + fd.impact_intensity * 0.5)
    fx_glitch = _clamp(fd.glitch_amount)

    routes["fx"] = {
        "mod_matrix": [
            ModulationRoute(
                source="LFO 1",
                destination="Filter 1 Cutoff",
                amount=_clamp(fx_intensity * 0.8),
                curve=_clamp(fx_glitch * 0.5),
                polarity_bipolar=True,
            ),
            ModulationRoute(
                source="ENV 2",
                destination="Osc A WT Pos",
                amount=_clamp(fx_intensity * 0.6),
                curve=0.0,
                polarity_bipolar=False,
            ),
        ],
        "lfos": [
            LFOPreset(
                name="FX Sweep",
                lfo_type="saw",
                rate_hz=base_rate * 2.0,
                depth=fx_intensity,
                sync_bpm=float(bpm),
                sync_division=0.5,
                polarity="unipolar",
            ),
        ],
    }

    log.info(
        "DESIGN MOD ROUTES: profile=%s/%s, bass_filter=%.2f, bass_wt=%.2f, "
        "lead_bright=%.2f, pad_stereo=%.2f, fx_intensity=%.2f",
        getattr(dna, "mood_name", "dark"),
        dna.style,
        bass_filter_mod,
        bass_wt_mod,
        lead_brightness_mod,
        pad_stereo_mod,
        fx_intensity,
    )

    return routes


def _design_fx_chains(
    dna: SongDNA,
    intent: dict[str, Any],
) -> dict[str, Any]:
    """DNA-driven Ableton FX chain configs per stem type.

    Returns a dict keyed by stem ("bass", "lead", "pad", "drums", "fx")
    where each value contains saturation, sidechain, stereo, reverb/delay,
    wave folder, and pitch automation configs — all derived from SongDNA.
    """
    from engine.saturation import SatConfig
    from engine.sidechain import SidechainPreset
    from engine.stereo_imager import StereoPreset
    from engine.reverb_delay import ReverbDelayPreset
    from engine.wave_folder import WaveFolderPatch
    from engine.pitch_automation import PitchAutoPreset

    profile = _resolve_profile(dna)
    bd = dna.bass
    ld = dna.lead
    ad = dna.atmosphere
    fd = dna.fx
    dd = dna.drums
    md = dna.mix
    energy = getattr(dna, "energy", 0.7)
    bpm = dna.bpm

    chains: dict[str, Any] = {}

    # ──────────────────────────────────────────────────────────────────
    # BASS FX chain
    # ──────────────────────────────────────────────────────────────────
    chains["bass"] = {
        "saturation": SatConfig(
            sat_type=profile["saturation_type"],
            drive=_clamp(bd.distortion * 0.7 + bd.mid_drive * 0.3),
            mix=_clamp(0.4 + bd.distortion * 0.4),
            tone=_clamp(0.3 + bd.filter_cutoff * 0.4),
        ),
        "sidechain": SidechainPreset(
            name=f"Bass SC {profile['sidechain_shape']}",
            shape=profile["sidechain_shape"],
            attack_ms=0.5 + (1.0 - energy) * 2.0,
            release_ms=100.0 + (1.0 - energy) * 100.0,
            # Higher compression_ratio → deeper sidechain (heavily compressed ref needs more pumping)
            depth=_clamp(0.5 + energy * 0.3 + _clamp(md.compression_ratio / 20.0) * 0.2),
            curve_exp=2.0 + bd.distortion,
            bpm=float(bpm),
        ),
        "wave_folder": WaveFolderPatch(
            name=f"Bass Fold {profile['wave_fold_algo']}",
            fold_amount=1.0 + bd.distortion * 4.0,
            symmetry=0.5,
            bias=0.0,
            pre_gain=_clamp(0.8 + bd.mid_drive * 0.4, hi=2.0),
            post_gain=0.8,
            mix=_clamp(bd.distortion * 0.5),
        ),
        "pitch_auto": PitchAutoPreset(
            name="Bass Pitch Dive",
            auto_type=profile["pitch_auto_type"],
            start_semitones=0.0,
            end_semitones=-12.0 * _clamp(bd.distortion),
            duration_s=60.0 / bpm * 0.25,
            curve_exp=2.0,
        ),
    }

    # ──────────────────────────────────────────────────────────────────
    # LEAD FX chain
    # ──────────────────────────────────────────────────────────────────
    chains["lead"] = {
        "saturation": SatConfig(
            sat_type="tape" if ld.brightness < 0.6 else "transistor",
            drive=_clamp(ld.brightness * 0.4 + energy * 0.2),
            mix=_clamp(0.3 + ld.brightness * 0.3),
            tone=_clamp(ld.brightness * 0.8),
        ),
        "sidechain": SidechainPreset(
            name=f"Lead SC {profile['sidechain_shape']}",
            shape=profile["sidechain_shape"],
            attack_ms=0.5,
            release_ms=120.0,
            depth=_clamp(0.4 + energy * 0.2),
            bpm=float(bpm),
        ),
        "stereo": StereoPreset(
            name=f"Lead Stereo {profile['stereo_type']}",
            image_type=profile["stereo_type"],
            width=_clamp(0.8 + ld.brightness * 0.4, hi=2.0),
            delay_ms=8.0 + ld.brightness * 8.0,
            crossover_hz=250.0,
            mix=0.8,
        ),
        "reverb": ReverbDelayPreset(
            name=f"Lead Reverb {profile['reverb_type']}",
            effect_type=profile["reverb_type"],
            decay_time=_clamp(ld.reverb_decay * 0.5, lo=0.3, hi=5.0),
            pre_delay_ms=15.0 + ld.brightness * 15.0,
            diffusion=0.7,
            damping=_clamp(1.0 - ld.brightness * 0.6),
            room_size=_clamp(0.3 + ld.reverb_decay / 10.0),
            mix=_clamp(0.15 + ld.reverb_decay / 20.0),
            stereo_width=0.8,
            bpm=float(bpm),
        ),
    }

    # ──────────────────────────────────────────────────────────────────
    # PAD / ATMOSPHERE FX chain
    # ──────────────────────────────────────────────────────────────────
    chains["pad"] = {
        "saturation": SatConfig(
            sat_type="tape",
            drive=_clamp(0.2 + energy * 0.15),
            mix=0.3,
            tone=_clamp(ad.pad_brightness * 0.6),
        ),
        "sidechain": SidechainPreset(
            name="Pad SC Pump",
            shape="pump",
            attack_ms=1.0,
            release_ms=120.0 + (1.0 - energy) * 80.0,
            depth=_clamp(0.4 + energy * 0.2),
            bpm=float(bpm),
        ),
        "stereo": StereoPreset(
            name="Pad Stereo Wide",
            image_type=profile["stereo_type"],
            width=_clamp(ad.stereo_width * 1.5, hi=2.0),
            delay_ms=12.0 + ad.stereo_width * 10.0,
            crossover_hz=200.0,
            mix=1.0,
        ),
        "reverb": ReverbDelayPreset(
            name=f"Pad Reverb {profile['reverb_type']}",
            effect_type=profile["reverb_type"],
            decay_time=_clamp(ad.reverb_decay * 0.8, lo=0.5, hi=8.0),
            pre_delay_ms=30.0,
            diffusion=0.9,
            damping=_clamp(0.3 + (1.0 - ad.pad_brightness) * 0.4),
            room_size=_clamp(0.5 + ad.reverb_decay / 12.0),
            shimmer_pitch=12.0 if profile["reverb_type"] == "shimmer" else 0.0,
            shimmer_feedback=0.5 if profile["reverb_type"] == "shimmer" else 0.0,
            mix=_clamp(0.3 + ad.reverb_decay / 15.0),
            stereo_width=_clamp(ad.stereo_width),
            bpm=float(bpm),
        ),
    }

    # ──────────────────────────────────────────────────────────────────
    # DRUMS FX chain
    # ──────────────────────────────────────────────────────────────────
    chains["drums"] = {
        "saturation": SatConfig(
            sat_type="transistor" if dd.kick_drive > 0.5 else "tape",
            drive=_clamp(dd.kick_drive * 0.6),
            mix=_clamp(0.3 + dd.kick_drive * 0.3),
            tone=_clamp(0.4 + dd.hat_brightness * 0.3),
        ),
        "sidechain": SidechainPreset(
            name=f"Drum Bus SC {profile['sidechain_shape']}",
            shape=profile["sidechain_shape"],
            attack_ms=0.3,
            release_ms=80.0,
            depth=0.3,
            bpm=float(bpm),
        ),
        "stereo": StereoPreset(
            name="Drum Stereo",
            image_type="mid_side",
            width=_clamp(0.6 + dd.hat_brightness * 0.3),
            crossover_hz=300.0,
            mix=0.7,
        ),
        "reverb": ReverbDelayPreset(
            name="Drum Room",
            effect_type="room",
            decay_time=_clamp(0.2 + energy * 0.15, lo=0.1, hi=0.8),
            pre_delay_ms=5.0,
            diffusion=0.5,
            damping=0.6,
            room_size=0.3,
            mix=_clamp(0.1 + (1.0 - energy) * 0.1),
            bpm=float(bpm),
        ),
    }

    # ──────────────────────────────────────────────────────────────────
    # FX / TRANSITIONS FX chain
    # ──────────────────────────────────────────────────────────────────
    chains["fx"] = {
        "saturation": SatConfig(
            sat_type=profile["saturation_type"],
            drive=_clamp(fd.impact_intensity * 0.5),
            mix=_clamp(0.3 + fd.impact_intensity * 0.3),
            tone=0.6,
        ),
        "sidechain": SidechainPreset(
            name="FX SC Light",
            shape="pump",
            attack_ms=1.5,
            release_ms=100.0,
            depth=_clamp(0.3 + energy * 0.15),
            bpm=float(bpm),
        ),
        "reverb": ReverbDelayPreset(
            name="FX Reverb",
            effect_type=profile["reverb_type"],
            decay_time=_clamp(fd.boom_decay * 0.8, lo=0.5, hi=4.0),
            pre_delay_ms=10.0,
            diffusion=0.8,
            damping=0.4,
            room_size=0.6,
            mix=0.4,
            stereo_width=0.9,
            bpm=float(bpm),
        ),
        "pitch_auto": PitchAutoPreset(
            name="FX Pitch",
            auto_type=profile["pitch_auto_type"],
            start_semitones=0.0,
            end_semitones=-24.0 * _clamp(fd.pitch_dive_range / 48.0),
            duration_s=60.0 / bpm,
            curve_exp=2.5,
            depth_semitones=fd.pitch_dive_range,
        ),
        "stereo": StereoPreset(
            name="FX Stereo Wide",
            image_type="haas",
            width=1.6,
            delay_ms=15.0,
            mix=0.9,
        ),
    }

    log.info(
        "DESIGN FX CHAINS: profile=%s/%s, bass_drive=%.2f, lead_reverb=%.1fs, "
        "pad_width=%.2f, drum_sat=%s",
        getattr(dna, "mood_name", "dark"),
        dna.style,
        chains["bass"]["saturation"].drive,
        chains["lead"]["reverb"].decay_time,
        chains["pad"]["stereo"].width,
        chains["drums"]["saturation"].sat_type,
    )

    return chains


# ═══════════════════════════════════════════════════════════════════════════
#  STAGE 4: SERUM 2 SOUND FACTORY — 4A through 4G
#
#  Every function consumes S1–S3 outputs from the mandate:
#    arrangement_template.sections → section-aware MIDI/activation
#    section.intensity              → energy level → velocity/intensity
#    chord_progression             → harmonic content for leads/pads/chords
#    modulation_routes             → LFO rates, mod depths for wobble/arp
#    fx_chains                     → sidechain, saturation, reverb per stem
#    wavetable_packs + morphs      → Serum 2 oscillator content
#    serum2_presets                → base presets for DNA mutation
#    freq_table                   → pitch reference
#    design_intent                → timbral character
# ═══════════════════════════════════════════════════════════════════════════

import math as _math_s4

# ── Element → stem mapping (which arrangement elements activate which stems) ──
_ELEMENT_STEMS: dict[str, list[str]] = {
    # ── arrangement_sequencer vocabulary (hardcoded templates) ──
    "bass_sub": ["sub_bass"],
    "bass_heavy": ["sub_bass", "mid_bass", "neuro"],
    "bass_weapon": ["sub_bass", "mid_bass", "neuro", "wobble", "riddim"],
    "bass_melodic": ["sub_bass", "mid_bass"],
    "riddim": ["riddim"],
    "wobble": ["wobble"],
    "lead": ["lead", "supersaw"],
    "chord": ["chords"],
    "arp": ["arps"],
    "pad": ["pad"],
    "ambient": ["pad"],
    "drone": ["pad"],
    "noise": ["pad"],
    "pluck": ["chords"],
    "vocal": [],
    "sidechain": [],  # ghost kick trigger — not a stem
    "glitch": ["neuro"],
    "fx": [],
    "fx_subtle": [],
    "riser": [],
    "impact": [],
    "drums_full": [],
    "drums_light": [],
    "drums_building": [],
    # ── DNA vocabulary (from ARRANGEMENT_ARCHETYPES in variation_engine) ──
    "kick": [],
    "kick_lite": [],
    "kick_fade": [],
    "snare": [],
    "snare_roll": [],
    "hats": [],
    "hats_sparse": [],
    "sub": ["sub_bass"],
    "sub_long": ["sub_bass"],
    "sub_fade": ["sub_bass"],
    "bass": ["mid_bass", "neuro"],
    "bass_alt": ["mid_bass", "wobble"],
    "extra_bass": ["mid_bass", "neuro", "riddim"],
    "chops": [],
    "noise_bed": ["pad"],
    "pad_fade": ["pad"],
    "texture": ["pad"],
    "plucks": ["chords"],
    "swell": [],
    "reverb_fx": [],
    "perc_light": [],
    "fx_tail": [],
}

# ── Stem → S3F base preset mapping ──
_STEM_PRESET_MAP: dict[str, str | None] = {
    "sub_bass": "DUBFORGE_Fractal_Sub",
    "mid_bass": "DUBFORGE_Golden_Reese",
    "neuro": "DUBFORGE_Phi_Growl",
    "wobble": "DUBFORGE_Spectral_Tear",
    "riddim": "DUBFORGE_Riddim_Minimal",
    "lead": "DUBFORGE_Fibonacci_FM_Screech",
    "pad": "DUBFORGE_Granular_Atmosphere",
    "chords": "DUBFORGE_Counter_Pluck",
    "arps": "DUBFORGE_Phi_Arp",
    "supersaw": None,
}

# ── Stem → S3 stem group (modulation_routes + fx_chains key) ──
_STEM_GROUP_MAP: dict[str, str] = {
    "sub_bass": "bass", "mid_bass": "bass", "neuro": "bass",
    "wobble": "bass", "riddim": "bass",
    "lead": "lead", "chords": "lead", "arps": "lead", "supersaw": "lead",
    "pad": "pad",
}

ALL_SYNTH_STEMS = list(_STEM_GROUP_MAP.keys())

# ── Sidechain ducking tiers per stem ──
_SC_TIERS: dict[str, tuple[str, float, float]] = {
    "sub_bass": ("Full", -30.0, 8.0),
    "mid_bass": ("Full", -30.0, 8.0),
    "neuro": ("Medium", -24.0, 4.0),
    "wobble": ("Medium", -24.0, 4.0),
    "riddim": ("Light", -18.0, 2.0),
    "lead": ("Light", -18.0, 2.0),
    "pad": ("Medium", -24.0, 4.0),
    "chords": ("Light", -18.0, 2.0),
    "arps": ("Light", -18.0, 2.0),
    "supersaw": ("Medium", -24.0, 4.0),
}

# ── Wavetable preference per stem (for 4A frame selection) ──
_STEM_WT_PREFS: dict[str, list[str]] = {
    "sub_bass": ["phi_root", "sine"],
    "mid_bass": ["fm_ratio_sweep", "fm"],
    "neuro": ["growl_vowel", "growl"],
    "wobble": ["fm_ratio_sweep", "fm"],
    "riddim": ["growl_vowel", "fm_ratio_sweep"],
    "lead": ["harmonic_sweep", "harmonic"],
    "pad": ["harmonic_sweep", "morph"],
    "chords": ["harmonic_sweep", "harmonic"],
    "arps": ["harmonic_sweep", "harmonic"],
    "supersaw": [],
}


def _freq_to_midi(freq: float, tuning_hz: float = 440.0) -> int:
    """Convert frequency (Hz) to nearest MIDI note number."""
    if freq <= 0:
        return 36
    return max(0, min(127, round(69 + 12 * _math_s4.log2(freq / tuning_hz))))


def _get_scale_midi_notes(key: str, scale: str, octave: int = 3) -> list[int]:
    """Get MIDI note numbers for a scale at the given octave."""
    note_names = list(NOTES)
    key_idx = note_names.index(key) if key in note_names else 0
    intervals = SCALE_INTERVALS.get(
        scale, SCALE_INTERVALS.get("minor", [0, 2, 3, 5, 7, 8, 10]),
    )
    base_midi = 12 * (octave + 1) + key_idx
    return [base_midi + iv for iv in intervals]


# _section_energy removed — use section.intensity directly from arrangement


def _stems_active_in_section(elements: list[str]) -> set[str]:
    """Which synth stems are active based on section element keywords."""
    active: set[str] = set()
    for elem in elements:
        active.update(_ELEMENT_STEMS.get(elem, []))
    return active


# ──────────────────────────────────────────────────────────────────────────
# 4A: CONFIGURE — Compile per-stem synthesis spec from S1–S3
# ──────────────────────────────────────────────────────────────────────────

def _configure_stem_specs(mandate: SongMandate) -> dict[str, StemSynthConfig]:
    """4A: For each of 10 stems, pull together ALL S1–S3 data into a
    single StemSynthConfig — the recipe card for that stem."""
    dna = mandate.dna
    tuning = getattr(dna, "tuning_hz", 440.0)
    root_midi = _freq_to_midi(dna.root_freq, tuning)
    energy = getattr(dna, "energy", 0.7)
    configs: dict[str, StemSynthConfig] = {}

    for stem_name in ALL_SYNTH_STEMS:
        group = _STEM_GROUP_MAP[stem_name]

        # S3C modulation routes for this group
        group_routes = mandate.modulation_routes.get(group, {})
        mod_matrix = group_routes.get("mod_matrix", [])
        lfos = group_routes.get("lfos", [])

        # S3D FX chain for this group
        group_fx = mandate.fx_chains.get(group, {})

        # S3B + S3E wavetable frames
        wt_frames = _select_wavetable_frames(
            stem_name, mandate.wavetable_packs, mandate.wavetables,
        )
        morph_frames = _select_morph_frames(stem_name, mandate.morph_wavetables)

        # S3F base preset
        preset_name = _STEM_PRESET_MAP.get(stem_name)
        base_preset = mandate.serum2_presets.get(preset_name) if preset_name else None

        configs[stem_name] = StemSynthConfig(
            stem_name=stem_name,
            stem_group=group,
            mod_matrix=mod_matrix,
            lfos=lfos,
            saturation=group_fx.get("saturation"),
            sidechain=group_fx.get("sidechain"),
            stereo=group_fx.get("stereo"),
            reverb=group_fx.get("reverb"),
            wave_folder=group_fx.get("wave_folder"),
            pitch_auto=group_fx.get("pitch_auto"),
            wavetable_frames=wt_frames,
            morph_frames=morph_frames,
            base_preset_name=preset_name or "",
            base_preset=base_preset,
            root_midi=root_midi,
            bpm=dna.bpm,
            key=dna.key,
            scale=dna.scale,
            mood=getattr(dna, "mood_name", "dark"),
            style=dna.style,
            energy=energy,
        )

    log.info(
        "4A CONFIGURE: %d stems, root=%d (%s%s), energy=%.2f",
        len(configs), root_midi, dna.key, dna.scale, energy,
    )
    return configs


def _select_wavetable_frames(
    stem_name: str,
    wt_packs: list[tuple[str, list[Any]]],
    wavetables: WavetableKit,
) -> list:
    """Select appropriate wavetable frames for a stem from S3B packs."""
    prefs = _STEM_WT_PREFS.get(stem_name, [])

    # Search generated wavetable packs first
    for pack_name, frames in wt_packs:
        for pref in prefs:
            if pref in pack_name.lower():
                return frames if isinstance(frames, list) else [frames]

    # Fallback: search wavetable kit (S3A intake)
    for pref in prefs:
        for wt_name, frames in wavetables.frames.items():
            if pref in wt_name.lower():
                return frames

    return []


def _select_morph_frames(
    stem_name: str, morph_wts: dict[str, list[Any]],
) -> list | None:
    """Select morph frames for a stem from S3E morphs."""
    if not morph_wts:
        return None

    group = _STEM_GROUP_MAP.get(stem_name, "lead")
    prefs = (
        ["fractal", "spectral_crush", "phi_spline"]
        if group == "bass"
        else ["spectral_blend", "formant", "phi_spline"]
    )

    for pref in prefs:
        for morph_name, frames in morph_wts.items():
            if pref in morph_name.lower():
                return frames

    # Fallback: first available
    for frames in morph_wts.values():
        return frames
    return None


# ──────────────────────────────────────────────────────────────────────────
# 4B: PRESETS — DNA-mutate Serum 2 presets per stem
# ──────────────────────────────────────────────────────────────────────────

def _mutate_presets_dna(
    mandate: SongMandate,
    stem_configs: dict[str, StemSynthConfig],
) -> dict[str, tuple[bytes, bytes]]:
    """4B: For each stem, clone the base Serum 2 preset and apply
    DNA-derived parameter mutations + mod matrix baking.

    Consumes: S3F presets (base), S3C modulation (mod_matrix), S1 DNA.
    """
    if not _HAS_SERUM2_PRESET:
        log.warning("4B skipped: serum2_preset not available")
        return {}

    state_map: dict[str, tuple[bytes, bytes]] = {}

    for stem_name, config in stem_configs.items():
        preset = config.base_preset
        if preset is None:
            try:
                preset = SerumPreset(name=f"DUBFORGE_{stem_name}")
            except Exception:
                continue
        else:
            try:
                preset = SerumPreset(
                    name=preset.name,
                    cbor_data=dict(preset.cbor_data),
                )
            except Exception:
                try:
                    preset = SerumPreset(name=f"DUBFORGE_{stem_name}")
                except Exception:
                    continue

        # Apply per-stem DNA mutations
        _apply_stem_mutations(preset, config)

        # Bake S3C modulation matrix into preset (up to 64 slots)
        for idx, route in enumerate(config.mod_matrix[:64]):
            try:
                preset.set_mod_slot(
                    idx,
                    source=getattr(route, "source", "LFO 1"),
                    amount=getattr(route, "amount", 0.5) * 100.0,
                    bipolar=getattr(route, "polarity_bipolar", False),
                )
            except Exception:
                pass

        # Serialize to VST3 state bytes
        try:
            proc = preset.get_processor_state()
            ctrl = preset.get_controller_state()
            state_map[stem_name] = (proc, ctrl)  # type: ignore[assignment]
        except Exception as exc:
            log.warning("4B: serialize failed for %s: %s", stem_name, exc)

    log.info("4B PRESETS: %d/%d stem states generated", len(state_map), len(stem_configs))
    return state_map


def _apply_stem_mutations(preset: Any, config: StemSynthConfig) -> None:
    """Apply per-stem DNA mutations to a SerumPreset.

    Consumes: config.energy, config.mood, config.style, config.lfos.
    """
    try:
        if config.stem_name == "sub_bass":
            preset.set_param("Filter0", "cutoff", 120.0)
            preset.set_param("Filter0", "resonance", 0.1)
            preset.set_param("Oscillator0", "unison_voices", 1)

        elif config.stem_name == "neuro":
            preset.set_param("Filter0", "cutoff", 800.0 + config.energy * 4000.0)
            preset.set_param("Filter0", "resonance", 0.3 + config.energy * 0.3)

        elif config.stem_name == "lead":
            preset.set_param("Filter0", "cutoff", 2000.0 + config.energy * 8000.0)

        elif config.stem_name == "pad":
            preset.set_param("Oscillator0", "unison_detune", 30.0 + config.energy * 20.0)
            preset.set_param("Oscillator0", "unison_voices", 4)

        elif config.stem_name == "supersaw":
            preset.set_param("Oscillator0", "unison_voices", 7)
            preset.set_param("Oscillator0", "unison_detune", 50.0)

        # Bake DNA-driven LFO rates + depths into Serum 2 for all bass stems
        if config.stem_group == "bass" and config.lfos:
            for _lfo_idx, _lfo in enumerate(config.lfos[:3]):
                preset.set_param(f"LFO{_lfo_idx}", "rate", getattr(_lfo, "rate_hz", 2.0))
                preset.set_param(f"LFO{_lfo_idx}", "depth", getattr(_lfo, "depth", 0.5))
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────
# 4C: MIDI — Section-aware MIDI for all 10 stems + ghost kick
#
# EVERY note is driven by:
#   arrangement_template.sections → which stems are active per section
#   section.intensity             → velocity, intensity, density
#   chord_progression             → harmonic content (lead, pad, chords)
#   modulation_routes             → LFO rates (wobble, arp timing)
#   dna                          → key, scale, bpm, root_freq, style
# ──────────────────────────────────────────────────────────────────────────

def _generate_midi_sequences(
    mandate: SongMandate,
    stem_configs: dict[str, StemSynthConfig],
) -> dict[str, list]:
    """4C: Generate section-aware MIDI for all stems + ghost kick.

    Walks through arrangement_template.sections, and for each section:
    - Determines which stems are active (from section.elements)
    - Gets energy level (from section.intensity)
    - Gets harmonic context (from chord_progression)
    - Generates MIDI notes with section-appropriate patterns
    """
    dna = mandate.dna
    arrangement = mandate.arrangement_template
    chords = mandate.chord_progression

    sections = getattr(arrangement, "sections", []) if arrangement else []
    if not sections:
        # Fallback: minimal arrangement
        from types import SimpleNamespace
        sections = [
            SimpleNamespace(name="intro", bars=8,
                            elements=["pad", "ambient"], intensity=0.3, bpm=dna.bpm),
            SimpleNamespace(name="build_1", bars=8,
                            elements=["bass_melodic", "lead", "drums_building"],
                            intensity=0.6, bpm=dna.bpm),
            SimpleNamespace(name="drop_1", bars=16,
                            elements=["bass_heavy", "lead", "sidechain", "chord", "pad"],
                            intensity=1.0, bpm=dna.bpm),
            SimpleNamespace(name="outro", bars=8,
                            elements=["pad", "ambient"], intensity=0.2, bpm=dna.bpm),
        ]

    midi: dict[str, list] = {stem: [] for stem in ALL_SYNTH_STEMS}
    midi["ghost_kick"] = []

    beat_offset = 0.0

    for sec_idx, section in enumerate(sections):
        sec_bars = section.bars
        sec_beats = sec_bars * BEATS_PER_BAR
        energy = section.intensity
        active_stems = _stems_active_in_section(section.elements)
        has_sidechain = "sidechain" in section.elements

        # Chord data for this section (from S1C chord_progression)
        sec_chords = _get_section_chords(chords, sec_idx, sec_bars)

        # Generate per-stem MIDI for this section
        for stem_name in ALL_SYNTH_STEMS:
            if stem_name not in active_stems:
                continue
            config = stem_configs.get(stem_name)
            if config is None:
                continue

            notes = _generate_stem_midi(
                stem_name, config, dna,
                beat_offset, sec_bars, sec_beats, energy,
                section.name, sec_chords,
                sec_idx=sec_idx,
            )
            midi[stem_name].extend(notes)

        # Ghost kick — quarter notes on C1, velocity from energy curve
        # Only in sections with "sidechain" element (drops, expands)
        if has_sidechain:
            for beat in range(sec_beats):
                vel = int(80 + 47 * energy)
                midi["ghost_kick"].append(ALSMidiNote(
                    pitch=36, time=beat_offset + beat,
                    duration=0.25, velocity=vel,
                ))

        beat_offset += sec_beats

    log.info(
        "4C MIDI: %d sections, %d total notes, ghost_kick=%d triggers",
        len(sections),
        sum(len(v) for v in midi.values()),
        len(midi["ghost_kick"]),
    )
    return midi


def _get_section_chords(chord_prog: Any, sec_idx: int, sec_bars: int) -> list:
    """Extract chord data for a section from the chord progression."""
    if chord_prog is None:
        return []
    raw_chords = getattr(chord_prog, "chords", [])
    if not raw_chords:
        return []
    return [raw_chords[i % len(raw_chords)] for i in range(sec_bars)]


def _chord_midi_notes(chord: Any, octave: int = 4) -> list[int]:
    """Extract MIDI note numbers from a chord (dict or object format)."""
    if chord is None:
        return []

    if isinstance(chord, dict):
        midi = chord.get("midi_notes") or chord.get("midi") or chord.get("notes")
        if midi:
            return [n + (octave - 3) * 12 if n < 24 else n for n in midi]
        root = chord.get("root_midi", chord.get("root", None))
        if root is not None:
            return [root + octave * 12]
        return []

    midi = getattr(chord, "midi_notes", None) or getattr(chord, "midi", None)
    if midi:
        return [n + (octave - 3) * 12 if n < 24 else n for n in midi]
    root = getattr(chord, "root_midi", getattr(chord, "root", None))
    if root is not None:
        return [root + octave * 12]
    return []


def _generate_stem_midi(
    stem_name: str, config: StemSynthConfig, dna: SongDNA,
    offset: float, bars: int, beats: int, energy: float,
    section_name: str, chords: list,
    sec_idx: int = 0,
) -> list:
    """Generate MIDI for one stem in one section.

    Uses arrangement context (section_name, energy), harmonic context
    (chords), and DNA identity (key, scale, root, style) for every decision.
    """
    root = config.root_midi
    vel_base = int(60 + 67 * energy)
    notes: list = []

    # ── SUB BASS: follow chord roots, sustained per bar ──
    if stem_name == "sub_bass":
        # Try pattern DB for rhythmic sub patterns in high-energy sections
        _sub_pattern = None
        if _HAS_PATTERN_DB and energy > 0.7:
            _sub_pattern = _pick_pattern(
                "sub_bass", style=dna.style, section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_sub"),
            )
        if _sub_pattern:
            sub_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=2)
            for pitch, t, dur, vel in _pattern_to_notes(
                _sub_pattern, sub_scale, offset, bars, root, vel_base,
            ):
                notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
        else:
            # Sustained sub — follow chord root movement
            # Production techniques applied:
            # - Phrase-level velocity contour (accent bar 1 of every 4)
            # - Drop sections: rhythmic half-bar re-triggers on alternating bars
            # - Clean transitions: shorten note before chord root changes
            is_drop = "drop" in section_name or "expand" in section_name
            for bar in range(bars):
                chord_notes = _chord_midi_notes(
                    chords[bar] if bar < len(chords) else None, octave=2,
                )
                sub_pitch = chord_notes[0] if chord_notes else root
                # Phrase-level dynamics: accent first bar of each 4-bar phrase
                phrase_accent = 1.0 if bar % 4 == 0 else 0.93
                vel = min(127, int(vel_base * phrase_accent))

                if is_drop and energy > 0.7 and bar % 2 == 1:
                    # Rhythmic drive: split bar into 2-beat + 2-beat
                    notes.append(ALSMidiNote(
                        pitch=sub_pitch, time=offset + bar * BEATS_PER_BAR,
                        duration=2.0, velocity=vel,
                    ))
                    notes.append(ALSMidiNote(
                        pitch=sub_pitch, time=offset + bar * BEATS_PER_BAR + 2.0,
                        duration=1.75, velocity=min(127, int(vel * 0.9)),
                    ))
                else:
                    # Clean transition: shorten note if next bar changes pitch
                    next_chord = _chord_midi_notes(
                        chords[bar + 1] if bar + 1 < len(chords) else None,
                        octave=2,
                    )
                    next_pitch = next_chord[0] if next_chord else sub_pitch
                    dur = 3.75 if next_pitch != sub_pitch else float(BEATS_PER_BAR)
                    notes.append(ALSMidiNote(
                        pitch=sub_pitch, time=offset + bar * BEATS_PER_BAR,
                        duration=dur, velocity=vel,
                    ))

    # ── MID BASS: use bass_riff from analysis → pattern DB → fallback ──
    elif stem_name == "mid_bass":
        _bass_riff = getattr(dna.bass, "bass_riff", None)
        if _bass_riff and isinstance(_bass_riff, list) and len(_bass_riff) > 0:
            # Use extracted bass rhythm from reference analysis
            bass_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            for bar in range(bars):
                riff = _bass_riff[bar % len(_bass_riff)]
                if not isinstance(riff, (list, tuple)):
                    continue
                for entry in riff:
                    try:
                        if len(entry) == 3:
                            degree, beat_pos, dur = entry
                            vel_norm = 1.0
                        else:
                            degree, beat_pos, dur, vel_norm = entry
                    except (ValueError, TypeError):
                        continue
                    if degree < 0:
                        continue
                    pitch = bass_scale[int(degree) % len(bass_scale)]
                    abs_time = offset + bar * BEATS_PER_BAR + float(beat_pos)
                    velocity = min(127, max(1, int(vel_norm * vel_base)))
                    notes.append(ALSMidiNote(
                        pitch=pitch, time=abs_time, duration=float(dur), velocity=velocity,
                    ))
        elif _HAS_PATTERN_DB:
            # Use curated pattern DB for mid bass
            _bass_pat = _pick_pattern(
                "mid_bass", style=dna.style, section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_midbass"),
            )
            if _bass_pat:
                bass_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
                for pitch, t, dur, vel in _pattern_to_notes(
                    _bass_pat, bass_scale, offset, bars, root + 12, vel_base,
                ):
                    notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
            else:
                # Improved fallback: rotation patterns + ghost notes + pitch variety
                bass_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
                _mb_rng = random.Random(hash(f"{dna.name}_{section_name}_midbass_fb"))
                for bar in range(bars):
                    pattern = _bass_rotation_pattern(bar, dna.style, energy)
                    for step_8th, vel_scale in pattern:
                        # Occasional pitch variation: use 5th or 3rd for interest
                        if _mb_rng.random() < 0.12 and len(bass_scale) > 4:
                            pitch = _mb_rng.choice(bass_scale[2:5])
                        else:
                            pitch = root + 12
                        vel_human = vel_scale * _mb_rng.uniform(0.9, 1.1)
                        vel = min(127, max(1, int(vel_base * vel_human)))
                        dur = 0.5 if step_8th % 2 == 0 else 0.375
                        notes.append(ALSMidiNote(
                            pitch=pitch,
                            time=offset + bar * BEATS_PER_BAR + step_8th * 0.5,
                            duration=dur, velocity=vel,
                        ))
                    # Ghost notes for groove in energetic sections
                    if energy > 0.5:
                        for ghost_pos in [1.5, 3.5]:
                            if _mb_rng.random() < 0.35:
                                notes.append(ALSMidiNote(
                                    pitch=root + 12,
                                    time=offset + bar * BEATS_PER_BAR + ghost_pos,
                                    duration=0.125,
                                    velocity=min(127, int(vel_base * 0.35)),
                                ))
        else:
            # No pattern DB: rotation patterns + ghost notes + pitch variety
            bass_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            _mb_rng = random.Random(hash(f"{dna.name}_{section_name}_midbass_np"))
            for bar in range(bars):
                pattern = _bass_rotation_pattern(bar, dna.style, energy)
                for step_8th, vel_scale in pattern:
                    if _mb_rng.random() < 0.12 and len(bass_scale) > 4:
                        pitch = _mb_rng.choice(bass_scale[2:5])
                    else:
                        pitch = root + 12
                    vel_human = vel_scale * _mb_rng.uniform(0.9, 1.1)
                    vel = min(127, max(1, int(vel_base * vel_human)))
                    dur = 0.5 if step_8th % 2 == 0 else 0.375
                    notes.append(ALSMidiNote(
                        pitch=pitch,
                        time=offset + bar * BEATS_PER_BAR + step_8th * 0.5,
                        duration=dur, velocity=vel,
                    ))
                if energy > 0.5:
                    for ghost_pos in [1.5, 3.5]:
                        if _mb_rng.random() < 0.35:
                            notes.append(ALSMidiNote(
                                pitch=root + 12,
                                time=offset + bar * BEATS_PER_BAR + ghost_pos,
                                duration=0.125,
                                velocity=min(127, int(vel_base * 0.35)),
                            ))

    # ── NEURO: pattern DB for rhythmic hits, RNG fallback ──
    elif stem_name == "neuro":
        _neuro_pat = None
        if _HAS_PATTERN_DB:
            _neuro_pat = _pick_pattern(
                "neuro", style=dna.style, section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_neuro"),
            )
        if _neuro_pat:
            neuro_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            for pitch, t, dur, vel in _pattern_to_notes(
                _neuro_pat, neuro_scale, offset, bars, root + 12, vel_base,
            ):
                notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
        else:
            # Composed neuro patterns with rhythmic cells
            # Production techniques: Reese-bass inspired choppy patterns,
            # triplet and dotted-8th cells, chromatic tension, pitch variation
            rng = random.Random(hash(f"{dna.name}_{section_name}_neuro"))
            neuro_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            # Rhythmic cells: (beat_offset, duration, velocity_scale, pitch_mode)
            # pitch_mode: 0=root, 1=scale_tone, 2=chromatic_neighbor
            _neuro_cells = [
                # Syncopated stab pattern (choppy dubstep feel)
                [(0.0, 0.25, 1.0, 0), (0.75, 0.25, 0.85, 0),
                 (1.5, 0.25, 0.9, 1), (2.0, 0.25, 1.0, 0),
                 (3.0, 0.25, 0.9, 0), (3.5, 0.125, 0.7, 2)],
                # Dotted-8th groove (creates forward momentum)
                [(0.0, 0.375, 1.0, 0), (0.75, 0.375, 0.85, 0),
                 (1.5, 0.375, 0.9, 1), (2.25, 0.375, 0.85, 0),
                 (3.0, 0.375, 0.95, 0)],
                # Triplet burst pattern (aggressive neuro feel)
                [(0.0, 0.167, 1.0, 0), (0.333, 0.167, 0.8, 0),
                 (0.667, 0.167, 0.7, 2), (1.0, 0.5, 0.95, 0),
                 (2.0, 0.167, 1.0, 0), (2.333, 0.167, 0.8, 1),
                 (2.667, 0.167, 0.7, 0), (3.0, 0.5, 0.95, 0)],
                # Stuttered 16ths (machine-gun neuro)
                [(0.0, 0.125, 1.0, 0), (0.25, 0.125, 0.75, 0),
                 (0.5, 0.125, 0.9, 0), (1.0, 0.125, 1.0, 0),
                 (1.25, 0.125, 0.7, 2), (2.0, 0.125, 1.0, 0),
                 (2.25, 0.125, 0.75, 0), (2.5, 0.125, 0.85, 1),
                 (3.0, 0.25, 0.95, 0), (3.5, 0.125, 0.8, 0)],
                # Sparse + accent (minimal neuro, lets kicks breathe)
                [(0.0, 0.5, 1.0, 0), (1.5, 0.25, 0.85, 1),
                 (2.0, 0.5, 0.95, 0), (3.5, 0.25, 0.8, 0)],
                # Call-response (2 beats on, syncopated answer)
                [(0.0, 0.25, 1.0, 0), (0.5, 0.25, 0.85, 0),
                 (1.0, 0.25, 0.9, 1), (2.5, 0.25, 0.95, 0),
                 (3.0, 0.125, 0.8, 2), (3.25, 0.125, 0.7, 0),
                 (3.5, 0.25, 0.9, 0)],
            ]
            # Pick 2-3 patterns and alternate per bar
            n_cells = len(_neuro_cells)
            cell_order = rng.sample(range(n_cells), min(3, n_cells))

            for bar in range(bars):
                cell = _neuro_cells[cell_order[bar % len(cell_order)]]
                for beat_off, dur, vel_sc, p_mode in cell:
                    # Determine pitch based on mode
                    if p_mode == 1 and len(neuro_scale) > 2:
                        pitch = rng.choice(neuro_scale[1:4])
                    elif p_mode == 2:
                        pitch = root + 12 + rng.choice([-1, 1])
                    else:
                        pitch = root + 12
                    vel = min(127, max(1, int(vel_base * vel_sc * rng.uniform(0.92, 1.08))))
                    notes.append(ALSMidiNote(
                        pitch=pitch,
                        time=offset + bar * BEATS_PER_BAR + beat_off,
                        duration=dur, velocity=vel,
                    ))

    # ── WOBBLE: sustained root — LFO modulation creates the wobble ──
    elif stem_name == "wobble":
        notes.append(ALSMidiNote(
            pitch=root, time=offset,
            duration=float(beats), velocity=vel_base,
        ))

    # ── RIDDIM: pattern DB for authentic gap patterns, fallback to gap ratio ──
    elif stem_name == "riddim":
        _riddim_pat = None
        if _HAS_PATTERN_DB:
            _riddim_pat = _pick_pattern(
                "riddim", style="riddim", section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_riddim"),
            )
        if _riddim_pat:
            riddim_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            for pitch, t, dur, vel in _pattern_to_notes(
                _riddim_pat, riddim_scale, offset, bars, root, vel_base,
            ):
                notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
        else:
            # Authentic riddim patterns: syncopated gaps, velocity "whack" accents
            # Riddim is defined by repetitive basslines with strategic silences
            # that let the kick/clap punch through. Patterns cycle every 2-4 bars.
            rng = random.Random(hash(f"{dna.name}_{section_name}_riddim"))
            riddim_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=3)
            gap_ratio = getattr(dna.bass, 'riddim_gap_ratio',
                                 0.3 + getattr(dna.bass, 'distortion', 0.5) * 0.4)
            note_dur = max(0.0625, 0.25 * (1.0 - gap_ratio))

            # Riddim rhythmic cells: (beat_offset, dur_mult, vel_scale)
            # Gaps on beats 2 and 4 let kick/clap cut through
            _riddim_cells = [
                # Classic riddim: hits between kicks, gap on snare
                [(0.0, 1.0, 1.0), (0.5, 1.0, 0.85),
                 (1.5, 1.0, 0.9), (2.0, 1.0, 1.0), (2.5, 1.0, 0.85),
                 (3.5, 0.5, 0.8)],
                # Choppy riddim: short stabs with breathing room
                [(0.0, 0.8, 1.0), (0.5, 0.6, 0.75),
                 (1.5, 0.8, 0.9), (2.0, 0.8, 1.0),
                 (3.0, 0.6, 0.85), (3.5, 0.6, 0.75)],
                # Driving riddim: more notes, relentless feel
                [(0.0, 1.0, 1.0), (0.5, 0.8, 0.8),
                 (1.0, 0.6, 0.7), (1.5, 1.0, 0.9),
                 (2.0, 1.0, 1.0), (2.5, 0.8, 0.8),
                 (3.0, 0.6, 0.7), (3.5, 1.0, 0.85)],
                # Minimal riddim: sparse, lets the sound design breathe
                [(0.0, 1.5, 1.0), (1.5, 1.0, 0.85),
                 (2.5, 1.5, 0.9)],
                # Syncopated riddim: offbeat emphasis
                [(0.5, 1.0, 0.95), (1.0, 0.8, 0.85),
                 (2.0, 1.0, 1.0), (2.5, 0.8, 0.9),
                 (3.5, 1.0, 0.85)],
            ]
            cell_order = rng.sample(range(len(_riddim_cells)),
                                     min(3, len(_riddim_cells)))

            for bar in range(bars):
                cell = _riddim_cells[cell_order[bar % len(cell_order)]]
                for beat_off, dur_mult, vel_sc in cell:
                    # Occasional pitch variation: 5th or octave for fills
                    if rng.random() < 0.08 and len(riddim_scale) > 4:
                        pitch = riddim_scale[4]  # 5th degree
                    else:
                        pitch = root
                    dur = note_dur * dur_mult
                    vel = min(127, max(1, int(vel_base * vel_sc * rng.uniform(0.93, 1.07))))
                    notes.append(ALSMidiNote(
                        pitch=pitch,
                        time=offset + bar * BEATS_PER_BAR + beat_off,
                        duration=dur, velocity=vel,
                    ))

    # ── LEAD: scale-guided melody from chord tones (S1C) ──
    elif stem_name == "lead":
        # ── Priority: use melody_patterns extracted from reference audio ──
        _melody_patterns = getattr(dna.lead, "melody_patterns", [])
        if _melody_patterns and section_name not in ("intro", "outro", "breakdown"):
            # Translate scale-degree patterns to MIDI notes
            lead_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=4)
            pattern = _melody_patterns[sec_idx % len(_melody_patterns)]
            for bar in range(bars):
                for entry in pattern:
                    try:
                        degree, beat_pos, dur, vel_norm = entry
                    except (ValueError, TypeError):
                        continue
                    if degree < 0:  # rest
                        continue
                    scale_note = lead_scale[int(degree) % len(lead_scale)]
                    abs_time = offset + bar * BEATS_PER_BAR + float(beat_pos)
                    velocity = min(127, max(1, int(vel_norm * vel_base)))
                    notes.append(ALSMidiNote(
                        pitch=scale_note,
                        time=abs_time,
                        duration=float(dur),
                        velocity=velocity,
                    ))
        else:
            # Generative lead with proper melodic techniques:
            # - Step-wise motion (scale degrees move by 1-2 steps mostly)
            # - Chord tones targeted on strong beats (1, 3)
            # - Call-and-response phrasing (2-bar phrases)
            # - Arch-shaped melodic contour (rise then fall)
            # - Varied note durations mixing 8ths, 16ths, quarters
            # - Velocity dynamics: accent phrase starts, softer passing tones
            rng = random.Random(hash(f"{dna.name}_{section_name}_lead"))
            lead_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=4)
            n_scale = len(lead_scale)
            current_degree = 0  # Start on root

            for bar in range(bars):
                chord_notes = _chord_midi_notes(
                    chords[bar] if bar < len(chords) else None, octave=4,
                )
                is_phrase_start = bar % 2 == 0
                # Determine note density based on energy and phrase position
                if is_phrase_start:
                    n_notes = 3 + int(energy * 3)  # "call": more notes
                else:
                    n_notes = 2 + int(energy * 2)  # "response": fewer notes

                # Build positions with varied rhythmic grid
                if is_phrase_start:
                    # Call phrase: start on beat 1, fill beats 1-3
                    positions = [0.0]
                    for _ in range(n_notes - 1):
                        last = positions[-1]
                        step = rng.choice([0.25, 0.5, 0.75, 1.0])
                        nxt = last + step
                        if nxt < 4.0:
                            positions.append(nxt)
                else:
                    # Response phrase: start on offbeat, leave space at end
                    positions = [rng.choice([0.5, 1.0])]
                    for _ in range(n_notes - 1):
                        last = positions[-1]
                        step = rng.choice([0.25, 0.5, 0.75])
                        nxt = last + step
                        if nxt < 3.5:
                            positions.append(nxt)

                for i, pos in enumerate(positions):
                    on_strong_beat = pos % 2.0 < 0.01
                    if on_strong_beat and chord_notes:
                        # Target chord tones on strong beats
                        pitch = rng.choice(chord_notes)
                        # Update current_degree to match
                        dists = [abs(p - pitch) for p in lead_scale]
                        current_degree = dists.index(min(dists))
                    else:
                        # Step-wise motion: move 1-2 degrees, bias toward small intervals
                        step = rng.choice([-2, -1, -1, 1, 1, 2])
                        current_degree = max(0, min(n_scale - 1, current_degree + step))
                        pitch = lead_scale[current_degree]

                    # Durations: longer on strong beats, shorter on passing tones
                    if on_strong_beat:
                        dur = rng.choice([0.5, 1.0, 0.75])
                    else:
                        dur = rng.choice([0.25, 0.375, 0.5])

                    # Velocity dynamics: accent phrase starts, softer inner notes
                    if i == 0:
                        vel_mult = rng.uniform(0.92, 1.0)
                    elif on_strong_beat:
                        vel_mult = rng.uniform(0.85, 0.95)
                    else:
                        vel_mult = rng.uniform(0.7, 0.85)

                    notes.append(ALSMidiNote(
                        pitch=pitch,
                        time=offset + bar * BEATS_PER_BAR + pos,
                        duration=dur,
                        velocity=min(127, max(1, int(vel_base * vel_mult))),
                    ))

    # ── PAD: chord tones sustained across whole section ──
    elif stem_name == "pad":
        chord_notes = _chord_midi_notes(
            chords[0] if chords else None, octave=3,
        )
        if not chord_notes:
            chord_notes = [root + 36]
        for note in chord_notes:
            notes.append(ALSMidiNote(
                pitch=note, time=offset,
                duration=float(beats), velocity=int(vel_base * 0.7),
            ))

    # ── CHORDS: chord voicing stabs at bar boundaries ──
    elif stem_name == "chords":
        for bar in range(bars):
            chord_notes = _chord_midi_notes(
                chords[bar] if bar < len(chords) else None, octave=4,
            )
            if not chord_notes:
                chord_notes = _get_scale_midi_notes(dna.key, dna.scale, octave=4)[:3]
            for note in chord_notes:
                notes.append(ALSMidiNote(
                    pitch=note, time=offset + bar * BEATS_PER_BAR,
                    duration=0.5, velocity=vel_base,
                ))

    # ── ARPS: pattern DB for styled arps, fallback to step-sequenced ──
    elif stem_name == "arps":
        _arp_pat = None
        if _HAS_PATTERN_DB:
            _arp_pat = _pick_pattern(
                "arps", style=dna.style, section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_arps"),
            )
        if _arp_pat:
            arp_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=5)
            for pitch, t, dur, vel in _pattern_to_notes(
                _arp_pat, arp_scale, offset, bars, root + 60, vel_base,
            ):
                notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
        else:
            # Improved arp sequencer with production techniques:
            # - Octave jumping: extend range by adding octave-up notes
            # - Velocity groove: accent patterns (4-on-floor, offbeat, etc.)
            # - Gate-length variation: shorter at higher energy for tighter feel
            # - Section-aware: ascending in builds, rhythmic in drops
            # - Note skipping for interest (skip every Nth step)
            arp_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=5)
            # Extend with octave-up versions for range
            arp_scale_ext = arp_scale + [n + 12 for n in arp_scale]
            _subdiv = getattr(dna.lead, 'arp_subdivision', '1/16')
            _subdiv_map = {"1/4": 1.0, "1/8": 0.5, "1/16": 0.25, "1/32": 0.125}
            step_dur = _subdiv_map.get(_subdiv, 0.25)
            total_steps = max(1, int(round(beats / step_dur)))
            _arp_style = getattr(dna.lead, 'arp_style', 'up')
            _arp_rng = random.Random(hash(f"{dna.name}_{section_name}_arps"))
            _n = len(arp_scale)
            _n_ext = len(arp_scale_ext)
            is_build = "build" in section_name
            is_drop = "drop" in section_name or "expand" in section_name

            # Build sequence pattern based on style
            if _arp_style == "down":
                seq = list(range(_n_ext - 1, -1, -1))
            elif _arp_style == "updown":
                seq = list(range(_n_ext)) + list(range(_n_ext - 2, 0, -1))
            elif _arp_style == "random":
                seq = list(range(_n_ext))
                _arp_rng.shuffle(seq)
            else:  # "up" or default
                seq = list(range(_n_ext))

            # Velocity accent pattern: changes per section for variety
            if is_build:
                # Build: crescendo with accent on every 4th
                _vel_patterns = [1.0, 0.6, 0.75, 0.65]
            elif is_drop:
                # Drop: punchy accents on 1 and offbeat
                _vel_patterns = [1.0, 0.65, 0.85, 0.6]
            else:
                # Intro/break: gentle, wavering dynamics
                _vel_patterns = [0.9, 0.7, 0.8, 0.7]

            # Gate length: tighter at higher energy
            gate_mult = max(0.4, 0.9 - energy * 0.4)

            for i in range(total_steps):
                # Note skipping for rhythmic interest (skip ~15% of notes in drops)
                if is_drop and _arp_rng.random() < 0.15:
                    continue

                note = arp_scale_ext[seq[i % len(seq)]]

                # In builds, progressively use higher octave notes
                if is_build and total_steps > 1:
                    progress = i / total_steps
                    if progress > 0.6 and i % len(seq) < _n:
                        # Shift to upper octave in second half of build
                        note = arp_scale_ext[min(seq[i % len(seq)] + _n, _n_ext - 1)]

                # Velocity from accent pattern + humanization
                vel_acc = _vel_patterns[i % len(_vel_patterns)]
                # Build crescendo
                if is_build and total_steps > 1:
                    vel_acc *= 0.6 + 0.4 * (i / total_steps)
                vel = min(127, max(1, int(vel_base * vel_acc * _arp_rng.uniform(0.93, 1.07))))

                # Gate length with slight variation
                gate = step_dur * gate_mult * _arp_rng.uniform(0.85, 1.15)
                notes.append(ALSMidiNote(
                    pitch=note, time=offset + i * step_dur,
                    duration=gate, velocity=vel,
                ))

    # ── SUPERSAW: pattern DB for stabs/swells, hardcoded power chord fallback ──
    elif stem_name == "supersaw":
        _saw_pat = None
        if _HAS_PATTERN_DB:
            _saw_pat = _pick_pattern(
                "supersaw", style=dna.style, section=section_name,
                energy=energy, seed=hash(f"{dna.name}_{sec_idx}_supersaw"),
            )
        if _saw_pat:
            saw_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=4)
            for pitch, t, dur, vel in _pattern_to_notes(
                _saw_pat, saw_scale, offset, bars, root + 24, vel_base,
            ):
                notes.append(ALSMidiNote(pitch=pitch, time=t, duration=dur, velocity=vel))
        else:
            # Improved supersaw with production techniques:
            # - Builds: velocity crescendo, sustained chords that swell
            # - Drops: rhythmic half-note stabs with gaps (pumping feel)
            # - Breaks: wide voicing pads
            # - Chord inversions for variety across bars
            # - Add 7ths for harmonic richness
            saw_scale = _get_scale_midi_notes(dna.key, dna.scale, octave=4)
            _saw_rng = random.Random(hash(f"{dna.name}_{section_name}_supersaw"))

            if "build" in section_name:
                # Crescendo swell: velocity ramps up across the section
                # Use full chord voicing, sustained
                for bar in range(bars):
                    chord_notes = _chord_midi_notes(
                        chords[bar] if bar < len(chords) else None, octave=4,
                    )
                    if not chord_notes:
                        chord_notes = [root + 24, root + 31, root + 36]
                    # Progressive velocity crescendo
                    progress = (bar + 1) / max(1, bars)
                    vel = min(127, int(50 + progress * 77))
                    for p in chord_notes[:3]:
                        notes.append(ALSMidiNote(
                            pitch=p, time=offset + bar * BEATS_PER_BAR,
                            duration=float(BEATS_PER_BAR), velocity=vel,
                        ))
                    # Add root an octave down for weight in second half
                    if progress > 0.5 and chord_notes:
                        notes.append(ALSMidiNote(
                            pitch=chord_notes[0] - 12,
                            time=offset + bar * BEATS_PER_BAR,
                            duration=float(BEATS_PER_BAR),
                            velocity=min(127, int(vel * 0.7)),
                        ))

            elif "drop" in section_name or "expand" in section_name:
                # Rhythmic stab patterns: pumping feel with gaps
                # Stab patterns: (beat_offset, duration) per bar
                _stab_patterns = [
                    [(0.0, 1.75), (2.0, 1.75)],              # half-note stabs
                    [(0.0, 1.0), (1.5, 1.0), (3.0, 0.75)],   # syncopated stabs
                    [(0.0, 2.75)],                             # long sustain w/ gap
                    [(0.0, 0.75), (1.0, 0.75), (2.0, 0.75), (3.0, 0.75)],  # quarter stabs
                ]
                pat_order = _saw_rng.sample(range(len(_stab_patterns)), 2)

                for bar in range(bars):
                    chord_notes = _chord_midi_notes(
                        chords[bar] if bar < len(chords) else None, octave=4,
                    )
                    if not chord_notes:
                        chord_notes = [root + 24, root + 31, root + 36]
                    # Apply inversion every other bar for movement
                    if bar % 2 == 1 and len(chord_notes) >= 3:
                        # First inversion: move root up an octave
                        chord_notes = chord_notes[1:] + [chord_notes[0] + 12]
                    # Add 7th for richness on some bars
                    if bar % 4 == 3 and len(saw_scale) > 6:
                        chord_notes = chord_notes[:3] + [saw_scale[6]]

                    stab_pat = _stab_patterns[pat_order[bar % len(pat_order)]]
                    for beat_off, dur in stab_pat:
                        vel = min(127, int(vel_base * _saw_rng.uniform(0.9, 1.0)))
                        for p in chord_notes[:4]:
                            notes.append(ALSMidiNote(
                                pitch=p,
                                time=offset + bar * BEATS_PER_BAR + beat_off,
                                duration=dur, velocity=vel,
                            ))
            else:
                # Break/intro: wide sustained pad-like chords
                for bar in range(bars):
                    chord_notes = _chord_midi_notes(
                        chords[bar] if bar < len(chords) else None, octave=4,
                    )
                    if not chord_notes:
                        chord_notes = [root + 24, root + 31, root + 36]
                    vel = min(127, int(vel_base * 0.65))
                    for p in chord_notes[:3]:
                        notes.append(ALSMidiNote(
                            pitch=p, time=offset + bar * BEATS_PER_BAR,
                            duration=float(BEATS_PER_BAR), velocity=vel,
                        ))

    return notes


def _bass_rotation_pattern(
    bar: int, style: str, energy: float,
) -> list[tuple[int, float]]:
    """Return 8th-note pattern for mid-bass rotation.

    10 pattern types with musically-informed rhythms, reordered by style.
    Patterns draw from dubstep production techniques:
    - Syncopated offbeat hits for groove
    - Accented downbeats for weight
    - Sparse patterns for breathing room
    - Dotted/triplet feels for rhythmic interest
    Returns [(8th_note_index, velocity_scale), ...].
    """
    patterns = [
        [(0, 1.0), (2, 0.9), (4, 1.0), (6, 0.9)],          # quarter-note pulse
        [(1, 0.9), (3, 0.85), (5, 0.9), (7, 0.85)],         # offbeat 8ths
        [(0, 1.0), (3, 0.95), (4, 0.85), (6, 0.9)],         # syncopated A
        [(0, 1.0), (1, 0.6), (3, 0.9), (4, 1.0), (7, 0.7)], # syncopated B (choppier)
        [(i, 1.0 if i % 2 == 0 else 0.65) for i in range(8)],# full 8ths (driving)
        [(0, 1.0), (2, 0.5), (3, 0.95), (5, 0.5), (6, 0.95)],# dotted-8th feel
        [(0, 1.0), (4, 0.9)],                                 # sparse downbeats
        [(0, 1.0), (3, 0.8), (6, 0.9)],                       # dotted-quarter pulse
        [(0, 1.0), (2, 0.7), (3, 0.9), (5, 0.75), (7, 0.85)],# shuffled 8ths
        [(0, 1.0), (1, 0.5), (4, 1.0), (5, 0.5)],            # 2-step bounce
    ]
    if style == "riddim":
        order = [4, 3, 4, 0, 3, 9, 4, 3]
    elif style == "melodic":
        order = [0, 7, 0, 6, 5, 7, 0, 6]
    elif style == "aggressive":
        order = [4, 3, 8, 4, 3, 9, 4, 8]
    else:
        order = [0, 1, 2, 5, 3, 7, 8, 9]
    return patterns[order[bar % len(order)]]


# ──────────────────────────────────────────────────────────────────────────
# 4D: ALS — Build render session with ghost kick sidechain
# ──────────────────────────────────────────────────────────────────────────

def _build_render_als(
    mandate: SongMandate,
    stem_configs: dict[str, StemSynthConfig],
    serum2_state_map: dict[str, tuple[bytes, bytes]],
    midi_sequences: dict[str, list],
) -> Path | None:
    """4D: Build .als with GHOST_KICK (Track 0) + 10 Serum 2 tracks.

    Each track carries:
    - Serum 2 VST3 state (from 4B)             → preset_states
    - MIDI clip (from 4C)                       → midi_clips
    - FX chain (from stem_config / S3D)         → device_names
    - Compressor sidechain from GHOST_KICK      → sidechain routing
    - Modulation automation (from S3C)          → automations

    All bounces come out WET — FX chain + sidechain baked in.
    """
    if not _HAS_ALS_GEN:
        log.warning("4D skipped: als_generator not available")
        return None

    dna = mandate.dna
    sections = (
        mandate.arrangement_template.sections
        if mandate.arrangement_template else []
    )
    total_beats = float(sum(s.bars * BEATS_PER_BAR for s in sections)) if sections else 256.0

    project = _ALSProject(name=f"{dna.name}_render", bpm=dna.bpm)

    # ── Track 0: GHOST_KICK (silent sidechain trigger) ──
    ghost_notes = midi_sequences.get("ghost_kick", [])
    ghost_track = _ALSTrack(
        name="GHOST_KICK",
        track_type="midi",
        volume_db=-70.0,
        color=1,
        drum_rack_pads=[_ALSDrumPad(note=36, name="Kick SC")],
        midi_clips=[ALSMidiClip(
            name="GhostKick",
            start_beat=0.0,
            length_beats=total_beats,
            notes=ghost_notes,
        )],
    )
    project.tracks.append(ghost_track)

    # ── Tracks 1–10: Serum 2 stems ──
    for stem_name in ALL_SYNTH_STEMS:
        config = stem_configs.get(stem_name)
        stem_notes = midi_sequences.get(stem_name, [])
        proc_bytes, ctrl_bytes = serum2_state_map.get(stem_name, (b"", b""))

        # Device chain: Serum 2 → FX → Compressor (SC)
        # Full dubstep chain per §AUDIT: OTT, formant, phaser, parallel distortion
        device_names = ["Serum 2"]
        if config:
            # OTT (Multiband Dynamics) — on all bass stems, lighter on others
            if config.stem_group == "bass":
                device_names.append("Multiband Dynamics")   # OTT preset
            # Saturator (parallel distortion via dry/wet)
            if config.saturation:
                device_names.append("Saturator")
            # Wave folder rack for bass
            if config.wave_folder and config.stem_group == "bass":
                device_names.append("Audio Effect Rack")    # parallel chain
            # Auto Filter (formant resonance — bass stems)
            if config.stem_group == "bass":
                device_names.append("Auto Filter")          # formant sweep
            # Phaser (metallic / comb textures — bass & lead)
            if config.stem_group in ("bass", "lead"):
                device_names.append("Phaser")
            # Compressor with sidechain from ghost kick
            device_names.append("Compressor")
            # Reverb (leads, pads)
            if config.reverb:
                device_names.append("Reverb")
            # Utility (stereo width — leads, pads)
            if config.stereo:
                device_names.append("Utility")

        preset_states = {"Serum 2": proc_bytes} if proc_bytes else {}
        controller_states = {"Serum 2": ctrl_bytes} if ctrl_bytes else {}

        # Build modulation automation from S3C
        automations = _build_stem_automations(config, mandate)

        track = _ALSTrack(
            name=stem_name.upper().replace("_", " "),
            track_type="midi",
            volume_db=0.0,
            device_names=device_names,
            preset_states=preset_states,
            controller_states=controller_states,
            automations=automations,
            midi_clips=[ALSMidiClip(
                name=stem_name,
                start_beat=0.0,
                length_beats=total_beats,
                notes=stem_notes,
            )],
        )
        project.tracks.append(track)

    # ── Return Tracks: Reverb, Delay, Parallel Compression ──
    _return_names = [
        ("REVERB", ["Reverb"], 13),
        ("DELAY", ["Delay"], 14),
        ("PAR COMP", ["Compressor"], 15),
    ]
    for ret_name, ret_devs, ret_color in _return_names:
        ret_track = _ALSTrack(
            name=ret_name,
            track_type="return",
            volume_db=0.0,
            color=ret_color,
            device_names=ret_devs,
        )
        project.tracks.append(ret_track)

    # ── Scenes from arrangement sections ──
    if sections:
        for sec in sections:
            project.scenes.append(_ALSScene(
                name=sec.name,
                tempo=dna.bpm,
            ))
        # Cue points at section boundaries
        beat_cursor = 0.0
        for sec in sections:
            project.cue_points.append(_ALSCuePoint(
                name=sec.name,
                time=beat_cursor,
            ))
            beat_cursor += sec.bars * BEATS_PER_BAR

    # Write .als
    _sn_render = "".join(c if c.isalnum() or c in "-_ " else "" for c in dna.name).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn_render / "als"
    output_dir.mkdir(parents=True, exist_ok=True)
    als_path = output_dir / f"{dna.name}_render.als"

    try:
        _write_als(project, str(als_path))
        log.info("4D ALS: %s (%d tracks)", als_path, len(project.tracks))
        return als_path
    except Exception as exc:
        log.warning("4D: write failed: %s", exc)
        return None


def _build_stem_automations(
    config: StemSynthConfig | None, mandate: SongMandate,
) -> list:
    """Build automation envelopes for Serum 2 Macros 1-4 + FX parameters.

    Macro mapping (driven by 3C modulation_routes):
      Macro 1 — Filter cutoff (section energy → open in drops, closed in intros)
      Macro 2 — Wavetable position (section energy × WT morph depth)
      Macro 3 — FM depth / growl (section energy × distortion/fm_depth)
      Macro 4 — Formant shift (section-based vowel sweep for bass stems)

    Also writes:
      Pitch bend automation (octave drops on drop transitions)
      LFO rate automation (tempo sync → faster in drops)
    """
    if not _HAS_ALS_GEN or config is None:
        return []

    automations: list = []
    arrangement = mandate.arrangement_template
    if arrangement is None:
        return []

    sections = getattr(arrangement, "sections", [])
    if not sections:
        return []

    # ── Derive automation depths from 3C modulation data ──
    mod_matrix = config.mod_matrix or []
    lfos = config.lfos or []
    group = config.stem_group
    energy_scale = config.energy

    # Find modulation amounts for each Macro source
    filter_mod_depth = 0.7  # default
    wt_mod_depth = 0.5
    fm_mod_depth = 0.3
    formant_depth = 0.0

    for route in mod_matrix:
        src = getattr(route, "source", "")
        dest = getattr(route, "destination", "")
        amt = getattr(route, "amount", 0.5)
        if "Filter" in dest and "Cutoff" in dest:
            filter_mod_depth = max(filter_mod_depth, amt)
        if "WT Pos" in dest or "Osc A WT" in dest:
            wt_mod_depth = max(wt_mod_depth, amt)
        if "FM" in dest:
            fm_mod_depth = max(fm_mod_depth, amt)
        if "Macro 4" in src:
            formant_depth = max(formant_depth, amt)

    # Bass stems get deeper modulation
    is_bass = group == "bass"
    if is_bass:
        wt_mod_depth = min(1.0, wt_mod_depth * 1.3)
        fm_mod_depth = min(1.0, fm_mod_depth * 1.5)
        formant_depth = max(formant_depth, 0.4)  # bass always gets formant

    # ── Build section-by-section automation points ──
    m1_pts: list = []  # Filter cutoff
    m2_pts: list = []  # WT position
    m3_pts: list = []  # FM depth / growl
    m4_pts: list = []  # Formant shift
    pitch_pts: list = []  # Pitch bend

    beat_offset = 0.0
    prev_energy = 0.0

    for sec_idx, section in enumerate(sections):
        e = section.intensity
        sec_beats = section.bars * BEATS_PER_BAR
        sec_end = beat_offset + sec_beats - 0.1
        role = getattr(section, "name", "").lower()
        is_drop = "drop" in role
        is_build = "build" in role
        is_intro = "intro" in role or "outro" in role
        is_break = "break" in role or "bridge" in role

        # ── Macro 1: Filter cutoff (energy → filter open) ──
        filter_val = e * filter_mod_depth
        if is_intro:
            filter_val *= 0.4  # mostly closed
        elif is_build:
            # Ramp from closed to open over the build section
            m1_pts.append(_ALSAutomationPoint(
                time=beat_offset, value=0.2 * filter_mod_depth, curve=0.4))
            m1_pts.append(_ALSAutomationPoint(
                time=sec_end, value=filter_mod_depth, curve=0.0))
            beat_offset += sec_beats
            prev_energy = e
            continue  # skip the standard pair for builds
        m1_pts.append(_ALSAutomationPoint(time=beat_offset, value=filter_val))
        m1_pts.append(_ALSAutomationPoint(time=sec_end, value=filter_val))

        # ── Macro 2: WT position (evolves with energy) ──
        wt_val = e * wt_mod_depth
        if is_drop:
            # Sweep WT position across the drop for movement
            m2_pts.append(_ALSAutomationPoint(
                time=beat_offset, value=wt_val * 0.3, curve=0.3))
            m2_pts.append(_ALSAutomationPoint(
                time=sec_end, value=wt_val))
        else:
            m2_pts.append(_ALSAutomationPoint(time=beat_offset, value=wt_val * 0.5))
            m2_pts.append(_ALSAutomationPoint(time=sec_end, value=wt_val * 0.5))

        # ── Macro 3: FM depth / growl (aggressive in drops) ──
        fm_val = e * fm_mod_depth
        if is_drop and is_bass:
            fm_val = min(1.0, fm_val * 1.4)  # extra grit in drops
        elif is_break:
            fm_val *= 0.3  # subdued in breaks
        m3_pts.append(_ALSAutomationPoint(time=beat_offset, value=fm_val))
        m3_pts.append(_ALSAutomationPoint(time=sec_end, value=fm_val))

        # ── Macro 4: Formant shift (bass only — cyclic sweep in drops) ──
        if formant_depth > 0.0:
            if is_drop:
                # Formant sweep across drop (low → high → low) for "yoi"
                mid_beat = beat_offset + sec_beats * 0.5
                m4_pts.append(_ALSAutomationPoint(
                    time=beat_offset, value=0.1 * formant_depth))
                m4_pts.append(_ALSAutomationPoint(
                    time=mid_beat, value=formant_depth))
                m4_pts.append(_ALSAutomationPoint(
                    time=sec_end, value=0.2 * formant_depth))
            else:
                m4_pts.append(_ALSAutomationPoint(
                    time=beat_offset, value=0.1 * formant_depth))
                m4_pts.append(_ALSAutomationPoint(
                    time=sec_end, value=0.1 * formant_depth))

        # ── Pitch automation: octave drop on drop transitions ──
        if is_drop and prev_energy < 0.6 and is_bass:
            # Octave dive on first beat of drop (pitch bend 0→-12→0 semitones)
            # Represented as normalized: 0.5 = center, 0.0 = -24st, 1.0 = +24st
            pitch_pts.append(_ALSAutomationPoint(
                time=beat_offset, value=0.25, curve=0.5))  # -12 semitones
            pitch_pts.append(_ALSAutomationPoint(
                time=beat_offset + 1.0, value=0.5))  # back to center

        prev_energy = e
        beat_offset += sec_beats

    # ── Assemble automation lanes ──
    if m1_pts:
        automations.append(_ALSAutomation(parameter_name="Macro 1", points=m1_pts))
    if m2_pts:
        automations.append(_ALSAutomation(parameter_name="Macro 2", points=m2_pts))
    if m3_pts:
        automations.append(_ALSAutomation(parameter_name="Macro 3", points=m3_pts))
    if m4_pts:
        automations.append(_ALSAutomation(parameter_name="Macro 4", points=m4_pts))
    if pitch_pts:
        automations.append(_ALSAutomation(parameter_name="Pitch Bend", points=pitch_pts))

    # ── LFO rate: faster in builds (via Macro 5 if available) ──
    if lfos and is_bass:
        lfo_pts: list = []
        beat_offset = 0.0
        for section in sections:
            sec_beats = section.bars * BEATS_PER_BAR
            role = getattr(section, "name", "").lower()
            rate_norm = 0.5 if "drop" in role else (0.8 if "build" in role else 0.3)
            lfo_pts.append(_ALSAutomationPoint(time=beat_offset, value=rate_norm))
            lfo_pts.append(_ALSAutomationPoint(
                time=beat_offset + sec_beats - 0.1, value=rate_norm))
            beat_offset += sec_beats
        if lfo_pts:
            automations.append(_ALSAutomation(
                parameter_name="Macro 5", points=lfo_pts))

    return automations


# ──────────────────────────────────────────────────────────────────────────
# 4E: BOUNCE — Export WAVs from Ableton Live 12
# ──────────────────────────────────────────────────────────────────────────

# ── Ableton app detection ────────────────────────────────────────────────

_ABLETON_APP_NAME: str | None = None  # cached after first detection
_ABLETON_PROCESS_NAME: str | None = None  # System Events process name


def _detect_ableton_process() -> str:
    """Detect Ableton's System Events process name (e.g. 'Live').

    macOS System Events uses the executable name, not the .app bundle name.
    """
    global _ABLETON_PROCESS_NAME
    if _ABLETON_PROCESS_NAME is not None:
        return _ABLETON_PROCESS_NAME

    import subprocess
    # Ask System Events for the actual process name
    for keyword in ("Live", "Ableton"):
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to get name of first process '
                 f'whose name contains "{keyword}"'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                _ABLETON_PROCESS_NAME = result.stdout.strip()
                log.info("Detected Ableton process name: %s", _ABLETON_PROCESS_NAME)
                return _ABLETON_PROCESS_NAME
        except Exception:
            pass

    _ABLETON_PROCESS_NAME = "Live"
    log.info("Ableton process detection fell through — defaulting to: %s",
             _ABLETON_PROCESS_NAME)
    return _ABLETON_PROCESS_NAME


def _detect_ableton_app() -> str:
    """Detect the installed Ableton Live application name.

    Scans /Applications for Ableton Live *.app and returns the exact name
    (e.g. "Ableton Live 12 Suite", "Ableton Live 12 Standard").
    Falls back to checking the running process list.
    Caches the result for subsequent calls.
    """
    global _ABLETON_APP_NAME
    if _ABLETON_APP_NAME is not None:
        return _ABLETON_APP_NAME

    import subprocess

    # 1. Check /Applications for installed Ableton editions
    apps_dir = Path("/Applications")
    candidates = sorted(apps_dir.glob("Ableton Live*.app"), reverse=True)
    if candidates:
        _ABLETON_APP_NAME = candidates[0].stem  # e.g. "Ableton Live 12 Suite"
        log.info("Detected Ableton: %s", _ABLETON_APP_NAME)
        return _ABLETON_APP_NAME

    # 2. Fallback — check running processes
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every process '
             'whose name contains "Ableton"'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            name = result.stdout.strip().split(",")[0].strip()
            if name:
                _ABLETON_APP_NAME = name
                log.info("Detected running Ableton: %s", _ABLETON_APP_NAME)
                return _ABLETON_APP_NAME
    except Exception:
        pass

    # 3. Last resort
    _ABLETON_APP_NAME = "Ableton Live 12 Standard"
    log.info("Ableton detection fell through — defaulting to: %s",
             _ABLETON_APP_NAME)
    return _ABLETON_APP_NAME


# ── AppleScript helpers ──────────────────────────────────────────────────

def _dismiss_save_dialog(app_name: str, max_attempts: int = 10) -> bool:
    """Dismiss any "Save changes?" dialog that Ableton shows on set load.

    Polls up to *max_attempts* times (1 s apart) because the dialog can
    appear several seconds after the ``open`` call returns.  Handles both
    sheet-style dialogs and standalone modal windows.

    Returns True if a dialog was dismissed, False if none appeared.
    """
    import subprocess
    import time as _time

    proc_name = _detect_ableton_process()
    # AppleScript that checks for both sheet and standalone dialog variants,
    # clicks "Don't Save", and returns "dismissed" on success.
    script = f'''\
tell application "System Events"
    tell process "{proc_name}"
        -- Try sheet first (most common)
        try
            if exists sheet 1 of window 1 then
                try
                    click button "Don't Save" of sheet 1 of window 1
                    return "dismissed"
                end try
                try
                    -- macOS localized: Cmd+D = Don't Save accelerator
                    keystroke "d" using {{command down}}
                    return "dismissed"
                end try
            end if
        end try
        -- Try standalone dialog / group variant
        try
            set w1 to window 1
            try
                click button "Don't Save" of w1
                return "dismissed"
            end try
            try
                set grp to group 1 of w1
                set btn_count to count of buttons of grp
                if btn_count >= 2 then
                    -- "Don't Save" is typically button 1 or 3
                    repeat with b in buttons of grp
                        if description of b contains "Don" then
                            click b
                            return "dismissed"
                        end if
                    end repeat
                    -- last resort: Cmd+D
                    keystroke "d" using {{command down}}
                    return "dismissed"
                end if
            end try
        end try
    end tell
end tell
return "none"
'''
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                timeout=5, capture_output=True, text=True,
            )
            if "dismissed" in (result.stdout or ""):
                log.info("Save-changes dialog dismissed (attempt %d)", attempt + 1)
                return True
        except Exception:
            pass
        _time.sleep(1.0)
    return False


def _run_export_applescript(
    app_name: str,
    filename: str,
    export_dir: str,
    timeout: float = 60.0,
) -> tuple[bool, str]:
    """Drive Ableton Live 12's Export Audio/Video workflow via AppleScript.

    Ableton 12 flow:
      1. Cmd+Shift+R triggers either a "stop audio" confirmation or the
         Export Audio/Video dialog directly.
      2. If "This action will stop audio. Proceed?" appears, click Proceed.
      3. Configure WAV / 48 kHz / 24-bit via keyboard type-ahead on popups
         (Ableton custom popups have no AX menus).
      4. Click Export (button 10 of group 1).
      5. macOS NSSavePanel: Cmd+Shift+G to navigate to dir, type filename.

    Returns (success, error_message).
    """
    import subprocess

    safe_filename = filename.replace('"', '').replace("\\", "").replace("'", "")
    safe_dir = export_dir.replace('"', '').replace("\\", "").replace("'", "")

    proc_name = _detect_ableton_process()

    script = f'''\
tell application "{app_name}" to activate
delay 0.5

tell application "System Events"
    tell process "{proc_name}"
        set frontmost to true
        delay 0.3

        -- Step 1: Trigger Export Audio/Video (Cmd+Shift+R)
        keystroke "r" using {{command down, shift down}}
        delay 1.0

        -- Step 2: Handle "stop audio" confirmation if it appears
        -- Ableton shows "This action will stop audio. Proceed?" with 2 buttons.
        -- Button 2 is Proceed/OK.
        try
            if (count of windows) > 1 then
                set dlg to window 1
                try
                    set grp to group 1 of dlg
                    set stVal to value of static text 1 of grp
                    if stVal contains "stop audio" then
                        click button 2 of grp
                        delay 1.5
                    end if
                end try
            end if
        end try

        -- Step 3: Wait for the Export Audio/Video window
        set dialogReady to false
        repeat 40 times
            delay 0.3
            try
                if exists window "Export Audio/Video" then
                    set dialogReady to true
                    exit repeat
                end if
            end try
            -- Also check for unnamed dialog with popups (Ableton sometimes
            -- gives the window an empty name on first appearance)
            try
                if (count of windows) > 1 then
                    set w1 to window 1
                    if (subrole of w1) is "AXDialog" then
                        set grpCount to count of groups of w1
                        if grpCount > 0 then
                            set popCount to count of pop up buttons of group 1 of w1
                            if popCount >= 4 then
                                set dialogReady to true
                                exit repeat
                            end if
                        end if
                    end if
                end if
            end try
        end repeat

        if not dialogReady then
            error "Export Audio/Video window did not appear within 12 seconds"
        end if

        delay 0.5

        -- Locate the export dialog (prefer named, fall back to window 1)
        set exportWin to missing value
        try
            set exportWin to window "Export Audio/Video"
        end try
        if exportWin is missing value then
            set exportWin to window 1
        end if
        set mainGroup to group 1 of exportWin

        -- Step 4: Configure export settings via keyboard type-ahead
        -- Ableton custom popups: click to open, type first chars to select,
        -- press Return to confirm.

        -- File Type (popup 3) -> WAV
        try
            set ftp to pop up button 3 of mainGroup
            if (value of ftp) is not "WAV" then
                click ftp
                delay 0.3
                keystroke "W"
                delay 0.1
                keystroke return
                delay 0.5
            end if
        end try

        -- Sample Rate (popup 2) -> 48000
        try
            set srp to pop up button 2 of mainGroup
            if (value of srp) is not "48000" then
                click srp
                delay 0.3
                keystroke "4"
                delay 0.1
                keystroke "8"
                delay 0.1
                keystroke return
                delay 0.5
            end if
        end try

        -- Bit Depth (popup 4) -> 24
        try
            set bdp to pop up button 4 of mainGroup
            if (value of bdp) is not "24" then
                click bdp
                delay 0.3
                keystroke "2"
                delay 0.1
                keystroke "4"
                delay 0.1
                keystroke return
                delay 0.5
            end if
        end try

        -- Step 5: Click Export — find by accessibility description or name,
        --  fall back to button 10 for older Live layouts.
        set exportBtn to missing value
        try
            set exportBtn to (first button of mainGroup whose description contains "Export")
        end try
        if exportBtn is missing value then
            try
                set exportBtn to (first button of mainGroup whose name contains "Export")
            end try
        end if
        if exportBtn is missing value then
            try
                -- Last resort: iterate all buttons looking for "Export" label
                repeat with b in buttons of mainGroup
                    if (title of b) contains "Export" then
                        set exportBtn to b
                        exit repeat
                    end if
                end repeat
            end try
        end if
        if exportBtn is missing value then
            set exportBtn to button 10 of mainGroup
        end if
        click exportBtn
        delay 1.5

        -- Step 6: Save Panel — navigate to output dir and set filename
        keystroke "g" using {{command down, shift down}}
        delay 1.0

        keystroke "{safe_dir}"
        delay 0.3
        keystroke return
        delay 1.0

        -- Set filename (select all, type new name)
        keystroke "a" using {{command down}}
        delay 0.1
        keystroke "{safe_filename}"
        delay 0.3

        -- Save
        keystroke return
        delay 0.5

    end tell
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "AppleScript timed out"
    except Exception as exc:
        return False, str(exc)


# ── File and process polling ─────────────────────────────────────────────

def _wait_for_ableton_ready(
    bridge: "AbletonBridge",
    timeout: float = 60.0,
    expected_bpm: float | None = None,
    expected_tracks: int | None = None,
) -> bool:
    """Poll AbletonOSC until the *new* ALS is loaded.

    When *expected_bpm* is supplied, waits for the reported tempo to match
    (±1 BPM tolerance) — this prevents false-positives from the previous
    session still being active while Ableton loads the new set.

    When *expected_tracks* is supplied, also confirms the track count
    matches the generated ALS (ghost kick + 10 stems = 11).
    """
    import time as _time
    _bpm_corrected = False
    deadline = _time.time() + timeout
    attempts = 0
    while _time.time() < deadline:
        attempts += 1
        try:
            tempo = bridge.get_tempo()
            if tempo is None or tempo <= 0:
                if attempts % 5 == 1:
                    log.debug("_wait_for_ableton_ready: OSC no response yet (attempt %d, %.0fs left)",
                              attempts, deadline - _time.time())
                _time.sleep(2.0)
                continue

            # If we have an expected BPM, wait for Ableton to report it.
            # Tolerance ±5 BPM (accounts for rounding / slow ALS load).
            # After the first half of the timeout, force-set via OSC once
            # so a stale old session at wrong BPM doesn't block forever.
            if expected_bpm is not None and abs(tempo - expected_bpm) > 5.0:
                if not _bpm_corrected and _time.time() > deadline - (timeout / 2):
                    log.info("_wait_for_ableton_ready: forcing BPM %.0f → %.0f via OSC",
                             tempo, expected_bpm)
                    try:
                        bridge.set_tempo(expected_bpm)
                        _bpm_corrected = True
                    except Exception:
                        pass
                else:
                    log.debug("_wait_for_ableton_ready: BPM=%.0f waiting for %.0f (attempt %d)",
                              tempo, expected_bpm, attempts)
                _time.sleep(2.0)
                continue

            # If we have an expected track count, verify it
            if expected_tracks is not None and expected_tracks > 0:
                try:
                    tc = bridge.get_track_count()
                    if tc != expected_tracks:
                        log.debug("_wait_for_ableton_ready: track count=%d waiting for %d (attempt %d)",
                                  tc, expected_tracks, attempts)
                        _time.sleep(2.0)
                        continue
                except Exception:
                    _time.sleep(2.0)
                    continue

            log.info("_wait_for_ableton_ready: READY — BPM=%.0f tracks=%s (attempt %d)",
                     tempo, bridge.get_track_count(), attempts)
            return True
        except Exception as _exc:
            log.debug("_wait_for_ableton_ready: exception attempt %d: %s", attempts, _exc)
        _time.sleep(2.0)
    log.warning("_wait_for_ableton_ready: timed out after %d attempts (%.0fs)", attempts, timeout)
    return False


def _wait_for_file(path: Path, timeout: float = 120.0, poll: float = 1.0) -> bool:
    """Poll until a file appears and stops growing (export complete)."""
    import time as _time
    deadline = _time.time() + timeout
    last_size = -1
    stable_count = 0
    while _time.time() < deadline:
        if path.exists():
            size = path.stat().st_size
            if size > 0 and size == last_size:
                stable_count += 1
                if stable_count >= 3:
                    return True
            else:
                stable_count = 0
            last_size = size
        _time.sleep(poll)
    return path.exists()


def _wait_for_export_idle(bridge: "AbletonBridge", timeout: float = 10.0) -> None:
    """Wait for Ableton to return to idle after an export completes.

    Polls tempo to confirm the OSC connection is still responsive,
    which indicates Ableton is no longer busy rendering.
    """
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        try:
            if bridge.get_tempo() is not None:
                return
        except Exception:
            pass
        _time.sleep(0.5)


# ── 4E: Main bounce function ────────────────────────────────────────────

_BOUNCE_MAX_RETRIES = 2  # retry failed exports up to N times


def _bounce_render_tracks(
    als_path: Path | None,
    mandate: "SongMandate | None" = None,
    auto: bool = True,
) -> dict[str, Path]:
    """4E: Open render session in Live and bounce stems — fully automated.

    Requires Ableton Live running with AbletonOSC.
    Raises RuntimeError if Ableton is not reachable — NO manual fallback.
    """
    if als_path is None:
        return {}

    _sn = "".join(c if c.isalnum() or c in "-_ " else "" for c in (mandate.dna.name if mandate else "dubforge")).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn / "bounces"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Check for pre-existing bounces first ──
    existing = _scan_existing_bounces(output_dir)
    if len(existing) >= len(ALL_SYNTH_STEMS):
        print("       4E: All stem bounces found on disk — skipping export")
        return existing

    # ── Calculate arrangement length in beats ──
    total_beats = 0.0
    if mandate and mandate.arrangement_template:
        for sec in getattr(mandate.arrangement_template, "sections", []):
            total_beats += sec.bars * BEATS_PER_BAR
    if total_beats == 0:
        total_beats = 128.0  # safe default (32 bars)

    # ── Connect to Ableton via AbletonBridge ──
    try:
        from engine.ableton_bridge import AbletonBridge
    except ImportError:
        raise RuntimeError("ableton_bridge not available")

    bridge = AbletonBridge(verbose=False)
    if not bridge.connect():
        raise RuntimeError("Ableton Live not running (AbletonOSC port 11000)")

    try:
        return _bounce_auto(bridge, als_path, output_dir, total_beats, mandate)
    finally:
        bridge.disconnect()


def _bounce_auto(
    bridge: "AbletonBridge",
    als_path: Path,
    output_dir: Path,
    total_beats: float,
    mandate: "SongMandate | None" = None,
) -> dict[str, Path]:
    """Fully automated bounce: AbletonBridge (OSC) + AppleScript (UI).

    Steps per MANDATE §4E:
      1. Detect Ableton app name dynamically
      2. Open .als in detected Ableton edition
      3. Dismiss any save-changes dialog from the previous set
      4. Poll AbletonOSC until the set is loaded and responding
      5. For each stem track (1–10) with retry on failure:
         a. Solo the track via OSC
         b. Set loop to full arrangement via OSC
         c. Drive Export Audio/Video dialog via AppleScript
         d. Wait for the WAV to appear on disk (file polling)
         e. Unsolo via OSC
      6. Return all bounced WAV paths

    Requirements:
      - AbletonOSC remote script selected in Ableton > Preferences > Link/MIDI
      - macOS Accessibility permission granted to Terminal / VS Code
    """
    import subprocess
    import time as _time

    app_name = _detect_ableton_app()
    stem_tracks = list(enumerate(ALL_SYNTH_STEMS, start=1))
    abs_output = output_dir.resolve()

    # ── 1. Open .als in Ableton ──
    print(f"       4E: Opening render session in {app_name}…")
    subprocess.Popen(["open", "-a", app_name, str(als_path)])

    # ── 2. Dismiss any save-changes dialog (polls up to 10s) ──
    _time.sleep(2.0)
    if _dismiss_save_dialog(app_name):
        print("       4E: Save dialog dismissed")

    # ── 3. Poll until the NEW ALS is loaded ──
    # Wait for both the expected BPM and track count to appear via OSC,
    # which proves Ableton has finished loading the new project file.
    expected_bpm = mandate.dna.bpm if mandate else None
    expected_tracks = len(ALL_SYNTH_STEMS) + 1 if mandate else None  # +1 ghost kick
    print(f"       4E: Waiting for ALS to load (expecting {expected_bpm} BPM, "
          f"{expected_tracks} tracks)…")
    if not _wait_for_ableton_ready(
        bridge, timeout=90.0,
        expected_bpm=expected_bpm, expected_tracks=expected_tracks,
    ):
        log.warning("4E: Ableton did not load project within 90s — manual fallback")
        _bounce_print_instructions(als_path, output_dir)
        return _scan_existing_bounces(output_dir)

    tempo = bridge.get_tempo() or 150.0
    print(f"       4E: ALS loaded — tempo={tempo} BPM, "
          f"arrangement={total_beats} beats")

    # Grace period for Serum 2 plugin instances to fully initialize.
    # 10 Serum 2 tracks need time to load wavetables and presets.
    print("       4E: Waiting for plugins to initialize (15s)…")
    _time.sleep(15.0)

    # ── 4. Configure loop + enforce BPM ──
    if expected_bpm:
        bridge.set_tempo(expected_bpm)
        tempo = expected_bpm
    else:
        tempo = bridge.get_tempo() or 150.0
    bridge.set_loop(True, 0.0, total_beats)

    # Unsolo everything first
    for track_idx, _ in stem_tracks:
        bridge.set_track_solo(track_idx, False)
    _time.sleep(0.3)

    # ── 5. Solo → Export → Unsolo for each stem (with retry) ──
    bounces: dict[str, Path] = {}
    export_timeout = max((total_beats / tempo) * 60 + 20, 45.0)

    for track_idx, stem_name in stem_tracks:
        wav_path = output_dir / f"{stem_name}.wav"
        success = False

        for attempt in range(_BOUNCE_MAX_RETRIES + 1):
            # Remove stale file so we can detect fresh export
            if wav_path.exists():
                wav_path.unlink()

            # Solo this track
            bridge.set_track_solo(track_idx, True)
            _time.sleep(0.3)

            # ── PREVIEW: play 8s so you can hear the stem before export ──
            bridge.jump_to(0.0)
            bridge.play()
            _time.sleep(8.0)
            bridge.stop()
            bridge.jump_to(0.0)
            _time.sleep(0.3)

            # Drive the Export dialog via AppleScript
            label = (f"       4E: Bouncing {stem_name} "
                     f"(track {track_idx}/10)"
                     f"{f' retry {attempt}' if attempt > 0 else ''}…")
            print(label)

            ok, err = _run_export_applescript(
                app_name, stem_name, str(abs_output),
            )
            if not ok:
                log.warning("4E: AppleScript failed for %s: %s",
                            stem_name, err)
                # Dismiss any stuck dialogs (Escape x5)
                _proc = _detect_ableton_process()
                try:
                    subprocess.run(
                        ["osascript", "-e",
                         f'tell application "System Events" to tell process '
                         f'"{_proc}"\n'
                         f'repeat 5 times\nkey code 53\ndelay 0.3\n'
                         f'end repeat\nend tell'],
                        timeout=10, capture_output=True,
                    )
                except Exception:
                    pass
                _time.sleep(1.0)
                bridge.set_track_solo(track_idx, False)
                _time.sleep(0.3)
                if attempt < _BOUNCE_MAX_RETRIES:
                    continue
                break

            # Wait for the WAV to appear and finish writing
            if _wait_for_file(wav_path, timeout=export_timeout):
                bounces[stem_name] = wav_path
                size_mb = wav_path.stat().st_size / (1024 * 1024)
                print(f"           ✓ {stem_name}.wav ({size_mb:.1f} MB)")
                success = True
            else:
                log.warning("4E: export timeout for %s (attempt %d/%d)",
                            stem_name, attempt + 1, _BOUNCE_MAX_RETRIES + 1)
                if attempt < _BOUNCE_MAX_RETRIES:
                    bridge.set_track_solo(track_idx, False)
                    _time.sleep(0.3)
                    continue
                log.warning("4E: giving up on %s after %d attempts",
                            stem_name, _BOUNCE_MAX_RETRIES + 1)

            break

        # Unsolo and wait for Ableton to settle
        bridge.set_track_solo(track_idx, False)
        if success:
            _wait_for_export_idle(bridge, timeout=5.0)
        _time.sleep(0.3)

    # ── 6. Summary ──
    print(f"       4E: Bounced {len(bounces)}/{len(ALL_SYNTH_STEMS)} stems")
    if len(bounces) < len(ALL_SYNTH_STEMS):
        missing = [s for s in ALL_SYNTH_STEMS if s not in bounces]
        log.warning("4E: Missing bounces: %s", ", ".join(missing))
        print(f"       4E: Manual export needed for: {', '.join(missing)}")

    return bounces


def _bounce_print_instructions(als_path: Path, output_dir: Path) -> None:
    """Manual fallback — prints step-by-step bounce instructions."""
    print(f"\n{'=' * 60}")
    print("  ACTION REQUIRED: Bounce Serum 2 stems from Ableton")
    print(f"{'=' * 60}")
    print(f"  1. Open: {als_path}")
    print("  2. For each track (1–10):")
    print("     Solo → Cmd+Shift+R → Export to output/bounces/{stem}.wav")
    print("  3. Expected files:")
    for stem in ALL_SYNTH_STEMS:
        print(f"       → {output_dir / f'{stem}.wav'}")
    print(f"{'=' * 60}\n")


def _scan_existing_bounces(output_dir: Path) -> dict[str, Path]:
    """Scan output_dir for pre-existing stem WAVs."""
    bounces: dict[str, Path] = {}
    for stem in ALL_SYNTH_STEMS:
        wav_path = output_dir / f"{stem}.wav"
        if wav_path.exists():
            bounces[stem] = wav_path
    return bounces


# ──────────────────────────────────────────────────────────────────────────
# 4F: COLLECT — Validate bounced audio
# ──────────────────────────────────────────────────────────────────────────
# 3J+: RESAMPLE — multi-pass resampling loop (Subtronics technique)
# ──────────────────────────────────────────────────────────────────────────

# Stems that get resampled — sub_bass stays clean for club playback
_RESAMPLE_STEMS = ["neuro", "wobble", "riddim", "mid_bass"]

# Per-pass device chains — each pass adds different character
_RESAMPLE_PASSES: list[dict[str, str | list[str]]] = [
    {   # Pass 1: Body & Grit — heavy saturation + OTT
        "label": "grit",
        "devices": ["Saturator", "Multiband Dynamics", "Utility"],
    },
    {   # Pass 2: Texture & Movement — formant sweep + comb filtering
        "label": "texture",
        "devices": ["Auto Filter", "Phaser", "Saturator", "Utility"],
    },
    {   # Pass 3: Final Character — frequency shift + OTT polish
        "label": "character",
        "devices": ["Frequency Shifter", "Multiband Dynamics", "Saturator", "Utility"],
    },
]


def _build_resample_als(
    bounces: dict[str, Path],
    pass_num: int,
    mandate: SongMandate,
) -> Path | None:
    """Build an ALS with audio tracks + resample processing for one pass.

    Each bass stem gets an audio track loaded with the previous bounce
    plus a processing chain that varies by pass number.
    """
    if not _HAS_ALS_GEN:
        return None

    dna = mandate.dna
    sections = (
        mandate.arrangement_template.sections
        if mandate.arrangement_template else []
    )
    total_beats = float(
        sum(s.bars * BEATS_PER_BAR for s in sections)
    ) if sections else 256.0

    pass_cfg = _RESAMPLE_PASSES[pass_num % len(_RESAMPLE_PASSES)]
    devices = pass_cfg["devices"]
    label = pass_cfg["label"]

    project = _ALSProject(
        name=f"{dna.name}_resample_p{pass_num + 1}_{label}",
        bpm=dna.bpm,
    )

    for stem_name in _RESAMPLE_STEMS:
        wav_path = bounces.get(stem_name)
        if not wav_path or not wav_path.exists():
            continue

        track = _ALSTrack(
            name=f"RS{pass_num + 1} {stem_name.upper().replace('_', ' ')}",
            track_type="audio",
            volume_db=0.0,
            device_names=list(devices),
            arrangement_clips=[_ALSClipInfo(
                path=str(wav_path.resolve()),
                start_beat=0.0,
                length_beats=total_beats,
                name=f"{stem_name}_p{pass_num}",
            )],
        )
        project.tracks.append(track)

    if not project.tracks:
        return None

    _sn_rs = "".join(c if c.isalnum() or c in "-_ " else "" for c in project.name.split("_resample")[0]).strip().replace(" ", "_") or "dubforge"
    als_dir = Path("output") / _sn_rs / "als"
    als_dir.mkdir(parents=True, exist_ok=True)
    als_path = als_dir / f"{project.name}.als"
    _write_als(project, str(als_path))
    return als_path


def _bounce_resample_tracks(
    als_path: Path,
    pass_num: int,
    mandate: SongMandate,
) -> dict[str, Path]:
    """Bounce resampled stems from an audio-only ALS session.

    Same AbletonOSC + AppleScript mechanism as _bounce_render_tracks,
    but faster: no Serum 2 plugin initialization needed.
    """
    if als_path is None:
        return {}

    _sn = "".join(c if c.isalnum() or c in "-_ " else "" for c in mandate.dna.name).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn / "bounces" / f"resample_p{pass_num + 1}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for pre-existing bounces
    existing: dict[str, Path] = {}
    for stem in _RESAMPLE_STEMS:
        wav = output_dir / f"{stem}.wav"
        if wav.exists():
            existing[stem] = wav
    if len(existing) >= len(_RESAMPLE_STEMS):
        print(f"       RS{pass_num + 1}: All resample bounces cached — skip")
        return existing

    sections = (
        mandate.arrangement_template.sections
        if mandate.arrangement_template else []
    )
    total_beats = float(
        sum(s.bars * BEATS_PER_BAR for s in sections)
    ) if sections else 256.0

    try:
        from engine.ableton_bridge import AbletonBridge
    except ImportError:
        raise RuntimeError("ableton_bridge not available")

    bridge = AbletonBridge(verbose=False)
    if not bridge.connect():
        raise RuntimeError("Ableton not running for resample bounce")

    try:
        return _bounce_resample_auto(
            bridge, als_path, output_dir, total_beats, pass_num, mandate,
        )
    finally:
        bridge.disconnect()


def _bounce_resample_auto(
    bridge: "AbletonBridge",
    als_path: Path,
    output_dir: Path,
    total_beats: float,
    pass_num: int,
    mandate: SongMandate,
) -> dict[str, Path]:
    """Drive the resample bounce — audio tracks only, no plugin load wait."""
    import subprocess
    import time as _time

    app_name = _detect_ableton_app()
    _sn = "".join(c if c.isalnum() or c in "-_ " else "" for c in mandate.dna.name).strip().replace(" ", "_") or "dubforge"
    # Tracks are indexed 0..N-1, one per resample stem
    stem_tracks = [
        (idx, stem) for idx, stem in enumerate(_RESAMPLE_STEMS)
        if (Path("output") / _sn / "bounces" / f"{stem}.wav").exists()
         or any((Path("output") / _sn / "bounces" / f"resample_p{p}" / f"{stem}.wav").exists()
                for p in range(1, pass_num + 1))
    ]
    abs_output = output_dir.resolve()

    # No source WAVs to resample — skip entirely
    if not stem_tracks:
        log.warning("RS%d: no source bounces to resample — skipping", pass_num + 1)
        return {}

    print(f"       RS{pass_num + 1}: Opening resample session…")
    subprocess.Popen(["open", "-a", app_name, str(als_path)])
    _time.sleep(2.0)
    if _dismiss_save_dialog(app_name):
        print(f"       RS{pass_num + 1}: Save dialog dismissed")

    expected_bpm = mandate.dna.bpm if mandate else None
    # Use track count only when it's non-trivially non-zero
    expected_tracks = len(stem_tracks) if stem_tracks else None
    if not _wait_for_ableton_ready(
        bridge, timeout=90.0,
        expected_bpm=expected_bpm, expected_tracks=expected_tracks,
    ):
        log.warning("RS%d: Ableton did not load resample ALS within 90s", pass_num + 1)
        return {}

    # No Serum 2 → much shorter plugin init wait
    _time.sleep(3.0)

    tempo = bridge.get_tempo() or 150.0
    bridge.set_loop(True, 0.0, total_beats)

    # Unsolo all
    for track_idx, _ in stem_tracks:
        bridge.set_track_solo(track_idx, False)
    _time.sleep(0.3)

    bounces: dict[str, Path] = {}
    export_timeout = max((total_beats / tempo) * 60 + 20, 45.0)

    for track_idx, stem_name in stem_tracks:
        wav_path = output_dir / f"{stem_name}.wav"
        if wav_path.exists():
            wav_path.unlink()

        bridge.set_track_solo(track_idx, True)
        _time.sleep(0.3)

        # ── PREVIEW: play 6s so you can hear the resample stem ──
        bridge.jump_to(0.0)
        bridge.play()
        _time.sleep(6.0)
        bridge.stop()
        bridge.jump_to(0.0)
        _time.sleep(0.3)

        print(f"       RS{pass_num + 1}: Bouncing {stem_name} "
              f"(track {track_idx + 1}/{len(stem_tracks)})…")

        ok, err = _run_export_applescript(
            app_name, stem_name, str(abs_output),
        )
        if not ok:
            log.warning("RS%d: export failed for %s: %s",
                        pass_num + 1, stem_name, err)
            bridge.set_track_solo(track_idx, False)
            continue

        if _wait_for_file(wav_path, timeout=export_timeout):
            bounces[stem_name] = wav_path
            size_mb = wav_path.stat().st_size / (1024 * 1024)
            print(f"           ✓ {stem_name}_p{pass_num + 1}.wav "
                  f"({size_mb:.1f} MB)")
        else:
            log.warning("RS%d: export timeout for %s", pass_num + 1, stem_name)

        bridge.set_track_solo(track_idx, False)
        _wait_for_export_idle(bridge, timeout=5.0)
        _time.sleep(0.3)

    print(f"       RS{pass_num + 1}: {len(bounces)}/{len(stem_tracks)} "
          f"stems resampled")
    return bounces


def _resample_passes(
    bounces: dict[str, Path],
    mandate: SongMandate,
    num_passes: int = 3,
) -> dict[str, Path]:
    """3J+: Multi-pass resampling loop — Subtronics-style sound design.

    For each pass:
      1. Build an ALS with audio tracks + processing chain
      2. Bounce through Ableton (same OSC + AppleScript mechanism)
      3. Feed resampled WAVs into the next pass

    Only bass stems (neuro, wobble, riddim, mid_bass) are resampled.
    sub_bass stays clean for club compatibility.

    Returns updated bounce dict with resampled versions replacing originals.
    """
    current = dict(bounces)  # copy — don't mutate caller's dict

    # Only proceed if we have bass stems to resample
    resample_ready = [s for s in _RESAMPLE_STEMS if s in current]
    if not resample_ready:
        print("       3J+: No bass stems to resample — skip")
        return current

    print(f"       3J+: Resampling {len(resample_ready)} bass stems "
          f"× {num_passes} passes")

    for pass_num in range(num_passes):
        pass_cfg = _RESAMPLE_PASSES[pass_num % len(_RESAMPLE_PASSES)]
        print(f"       3J+ Pass {pass_num + 1}/{num_passes}: "
              f"{pass_cfg['label']}…")

        # Build resample ALS
        als_path = _build_resample_als(current, pass_num, mandate)
        if als_path is None:
            log.warning("3J+ pass %d: could not build resample ALS", pass_num + 1)
            break

        # Bounce
        try:
            pass_bounces = _bounce_resample_tracks(als_path, pass_num, mandate)
        except RuntimeError as exc:
            log.warning("3J+ pass %d skipped: %s", pass_num + 1, exc)
            break

        # Update current bounces with resampled versions
        for stem, wav in pass_bounces.items():
            current[stem] = wav

        if not pass_bounces:
            log.warning("3J+ pass %d: no bounces — stopping resample loop",
                        pass_num + 1)
            break

    resampled = [s for s in _RESAMPLE_STEMS if current.get(s) != bounces.get(s)]
    print(f"       3J+: Resampling complete — "
          f"{len(resampled)} stems updated across {num_passes} passes")
    return current


# ──────────────────────────────────────────────────────────────────────────

def _collect_bounced_audio(
    bounces: dict[str, Path],
    manifest: AudioManifest | None = None,
) -> dict[str, Path]:
    """4F: Validate all bounced WAVs exist and have audio content.

    If a manifest is provided, marks each delivered file in it.
    """
    validated: dict[str, Path] = {}

    for stem, path in bounces.items():
        if not path.exists():
            log.warning("4F: bounce missing: %s", path)
            continue
        try:
            with wave.open(str(path)) as wf:
                if wf.getnframes() == 0:
                    log.warning("4F: empty bounce: %s", path)
                    continue
            validated[stem] = path
            if manifest:
                manifest.mark_delivered(
                    stem, path, file_size=path.stat().st_size)
        except Exception as exc:
            log.warning("4F: invalid WAV %s: %s", path, exc)

    return validated


# ──────────────────────────────────────────────────────────────────────────
# 4G: TRACKS — Build production session skeleton for Phase 2
# ──────────────────────────────────────────────────────────────────────────

def _build_production_skeleton(
    mandate: SongMandate,
    audio_clips: dict[str, Path],
    serum2_state_map: dict[str, tuple[bytes, bytes]],
    midi_sequences: dict[str, list],
    stem_configs: dict[str, StemSynthConfig],
) -> Path | None:
    """4G: Build production .als with bounced audio + muted Serum 2 tracks.

    Audio tracks (1–10) play the wet bounces for arrangement.
    Muted MIDI tracks (11+) carry the original Serum 2 presets + MIDI
    so the producer can unmute, tweak, and re-bounce any stem.
    """
    if not _HAS_ALS_GEN:
        return None

    dna = mandate.dna
    sections = (
        mandate.arrangement_template.sections
        if mandate.arrangement_template else []
    )
    total_beats = float(sum(s.bars * BEATS_PER_BAR for s in sections)) if sections else 256.0

    project = _ALSProject(name=f"{dna.name}_production", bpm=dna.bpm)

    # Audio tracks — bounced wet stems
    for stem_name in ALL_SYNTH_STEMS:
        clip_path = audio_clips.get(stem_name)
        track = _ALSTrack(
            name=stem_name.upper().replace("_", " "),
            track_type="audio",
            volume_db=0.0,
            clip_paths=[str(clip_path)] if clip_path else [],
            arrangement_clips=[_ALSClipInfo(
                path=str(clip_path),
                start_beat=0.0,
                length_beats=total_beats,
                name=stem_name,
            )] if clip_path else [],
        )
        project.tracks.append(track)

    # Muted MIDI + Serum 2 editing tracks
    for stem_name in ALL_SYNTH_STEMS:
        stem_notes = midi_sequences.get(stem_name, [])
        proc, ctrl = serum2_state_map.get(stem_name, (b"", b""))

        preset_states = {"Serum 2": proc} if proc else {}
        controller_states = {"Serum 2": ctrl} if ctrl else {}

        track = _ALSTrack(
            name=f"SERUM {stem_name.upper().replace('_', ' ')}",
            track_type="midi",
            mute=True,
            device_names=["Serum 2"],
            preset_states=preset_states,
            controller_states=controller_states,
            midi_clips=[ALSMidiClip(
                name=f"serum_{stem_name}",
                start_beat=0.0,
                length_beats=total_beats,
                notes=stem_notes,
            )],
        )
        project.tracks.append(track)

    # ── Return Tracks: Reverb, Delay, Parallel Compression ──
    _return_names = [
        ("REVERB", ["Reverb"], 13),
        ("DELAY", ["Delay"], 14),
        ("PAR COMP", ["Compressor"], 15),
    ]
    for ret_name, ret_devs, ret_color in _return_names:
        ret_track = _ALSTrack(
            name=ret_name,
            track_type="return",
            volume_db=0.0,
            color=ret_color,
            device_names=ret_devs,
        )
        project.tracks.append(ret_track)

    # ── Scenes from arrangement sections ──
    if sections:
        for sec in sections:
            project.scenes.append(_ALSScene(
                name=sec.name,
                tempo=dna.bpm,
            ))
        # Cue points at section boundaries
        beat_cursor = 0.0
        for sec in sections:
            project.cue_points.append(_ALSCuePoint(
                name=sec.name,
                time=beat_cursor,
            ))
            beat_cursor += sec.bars * BEATS_PER_BAR

    _sn_prod = "".join(c if c.isalnum() or c in "-_ " else "" for c in dna.name).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn_prod / "als"
    output_dir.mkdir(parents=True, exist_ok=True)
    prod_path = output_dir / f"{dna.name}_production.als"

    try:
        _write_als(project, str(prod_path))
        log.info("4G TRACKS: %s (%d tracks)", prod_path, len(project.tracks))
        return prod_path
    except Exception as exc:
        log.warning("4G: write failed: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────
# 5D: ALS BUILD — Write render session for 128-rack pattern bouncing
# ──────────────────────────────────────────────────────────────────────────

# Default silence gap — overridden by dna.drums.silence_gap_beats when available
_SILENCE_GAP_BEATS = 4


def _build_stage5_als(
    mandate: SongMandate,
) -> Path | None:
    """5D: Build a dedicated render .als with the 128 Rack + MIDI patterns.

    Session structure per MANDATE §5D:
      Track 0: GHOST_KICK (MIDI) — sidechain trigger, volume=-inf
      Track 1: 128 RACK (MIDI)   — Drum Rack with all 128 pads + FX chains
               MIDI clips: one per (section × zone_group) laid out sequentially

    Each pattern clip is separated by silence so bounces don't bleed.
    Returns the .als path or None if als_generator unavailable.
    """
    if not _HAS_ALS_GEN:
        log.warning("5D skipped: als_generator not available")
        return None

    dna = mandate.dna
    render_patterns = mandate.render_patterns
    if not render_patterns:
        log.warning("5D skipped: no render patterns from 5B")
        return None

    project = _ALSProject(name=f"{dna.name}_stage5_render", bpm=dna.bpm)

    # ── Track 0: GHOST_KICK (silent sidechain trigger) ──
    # Calculate total arrangement length from all pattern clips + gaps
    silence_gap = getattr(dna.drums, "silence_gap_beats", _SILENCE_GAP_BEATS)
    clip_layout: list[tuple[str, str, float, float, list[dict]]] = []
    beat_cursor = 0.0
    for sec_name, zone_patterns in render_patterns.items():
        sec_bars = mandate.sections.get(sec_name, 8)
        sec_beats = float(sec_bars * BEATS_PER_BAR)
        for zone_group, hits in zone_patterns.items():
            clip_name = f"{sec_name}_{zone_group}"
            clip_layout.append(
                (clip_name, sec_name, beat_cursor, sec_beats, hits),
            )
            beat_cursor += sec_beats + silence_gap

    total_beats = beat_cursor if beat_cursor > 0 else 256.0

    # Ghost kick track — quarter-note trigger spanning entire arrangement
    ghost_notes: list[ALSMidiNote] = []
    for beat in range(int(total_beats)):
        ghost_notes.append(ALSMidiNote(
            pitch=36, time=float(beat), duration=0.25, velocity=100,
        ))

    ghost_track = _ALSTrack(
        name="GHOST_KICK",
        track_type="midi",
        volume_db=-70.0,
        color=1,
        drum_rack_pads=[_ALSDrumPad(note=36, name="Kick SC")],
        midi_clips=[ALSMidiClip(
            name="GhostKick",
            start_beat=0.0,
            length_beats=total_beats,
            notes=ghost_notes,
        )],
    )
    project.tracks.append(ghost_track)

    # ── Track 1: 128 RACK — Drum Rack with all pads + FX chains ──
    # Build drum pads from rack_128 slot data
    drum_pads: list[_ALSDrumPad] = []
    for slot_name, slot_data in mandate.rack_128.slots.items():
        zone_num = slot_data.get("zone_num", 0)
        drum_pads.append(_ALSDrumPad(
            note=zone_num,
            name=slot_name[:32],
        ))

    # Build per-clip MIDI events placed sequentially along the arrangement
    midi_clips: list[ALSMidiClip] = []
    for clip_name, _sec, start, length, hits in clip_layout:
        notes: list[ALSMidiNote] = []
        for h in hits:
            notes.append(ALSMidiNote(
                pitch=h["note"],
                time=h["time"],
                duration=h.get("duration", 0.5),
                velocity=h.get("velocity", 100),
            ))
        midi_clips.append(ALSMidiClip(
            name=clip_name,
            start_beat=start,
            length_beats=length,
            notes=notes,
        ))

    # FX chain device names from 5C fx_chains
    device_names: list[str] = ["Drum Rack"]
    s5_fx = mandate.fx_chains.get("stage5", {})
    # Flatten unique device types across all zones for the rack chain
    seen: set[str] = set()
    for chain in s5_fx.values():
        for fx in chain:
            fx_type = fx.get("type", "")
            if fx_type and fx_type not in seen:
                device_names.append(fx_type)
                seen.add(fx_type)

    rack_track = _ALSTrack(
        name="128 RACK",
        track_type="midi",
        volume_db=0.0,
        device_names=device_names,
        drum_rack_pads=drum_pads,
        midi_clips=midi_clips,
    )
    project.tracks.append(rack_track)

    # Write .als
    _sn_s5 = "".join(c if c.isalnum() or c in "-_ " else "" for c in dna.name).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn_s5 / "als"
    output_dir.mkdir(parents=True, exist_ok=True)
    als_path = output_dir / f"{dna.name}_stage5_render.als"

    try:
        _write_als(project, str(als_path))
        log.info("5D ALS: %s (%d clips, %.0f beats)",
                 als_path, len(midi_clips), total_beats)
        return als_path
    except Exception as exc:
        log.warning("5D: write failed: %s", exc)
        return None


def _get_stage5_clip_layout(
    mandate: SongMandate,
) -> list[tuple[str, float, float]]:
    """Return [(clip_name, start_beat, length_beats), ...] for 5E bounce."""
    silence_gap = getattr(mandate.dna.drums, "silence_gap_beats", _SILENCE_GAP_BEATS)
    layout: list[tuple[str, float, float]] = []
    beat_cursor = 0.0
    for sec_name, zone_patterns in mandate.render_patterns.items():
        sec_bars = mandate.sections.get(sec_name, 8)
        sec_beats = float(sec_bars * 4)
        for zone_group in zone_patterns:
            clip_name = f"{sec_name}_{zone_group}"
            layout.append((clip_name, beat_cursor, sec_beats))
            beat_cursor += sec_beats + silence_gap
    return layout


# ──────────────────────────────────────────────────────────────────────────
# 5E: BOUNCE — Render each pattern region to WAV
# ──────────────────────────────────────────────────────────────────────────

# AppleScript template for Stage 5 bounce — same pattern as 4E
def _bounce_stage5_patterns(
    als_path: Path | None,
    mandate: SongMandate,
    auto: bool = True,
) -> dict[str, Path]:
    """5E: Open render session in Live and bounce each pattern region to WAV.

    Requires Ableton Live running with AbletonOSC.
    Raises RuntimeError if Ableton is not reachable — NO manual fallback.
    """
    if als_path is None:
        return {}

    _sn = "".join(c if c.isalnum() or c in "-_ " else "" for c in mandate.dna.name).strip().replace(" ", "_") or "dubforge"
    output_dir = Path("output") / _sn / "stage5_renders"
    output_dir.mkdir(parents=True, exist_ok=True)

    clip_layout = _get_stage5_clip_layout(mandate)
    if not clip_layout:
        log.warning("5E: no clip layout — nothing to bounce")
        return {}

    # ── Check for pre-existing bounces first ──
    existing = _scan_stage5_bounces(output_dir, clip_layout)
    if len(existing) >= len(clip_layout):
        print("       5E: All pattern bounces found on disk — skipping export")
        return existing

    # ── Connect to Ableton via AbletonBridge ──
    try:
        from engine.ableton_bridge import AbletonBridge
    except ImportError:
        raise RuntimeError("ableton_bridge not available")

    bridge = AbletonBridge(verbose=False)
    if not bridge.connect():
        raise RuntimeError("Ableton Live not running (AbletonOSC port 11000)")

    try:
        return _bounce_stage5_auto(bridge, als_path, output_dir, clip_layout)
    finally:
        bridge.disconnect()


def _bounce_stage5_auto(
    bridge: "AbletonBridge",
    als_path: Path,
    output_dir: Path,
    clip_layout: list[tuple[str, float, float]],
) -> dict[str, Path]:
    """Fully automated Stage 5 bounce using AbletonOSC + AppleScript.

    For each pattern clip (with retry on failure):
      1. Detect Ableton app name dynamically
      2. Set loop region to clip boundaries
      3. Solo Track 1 (128 RACK)
      4. Export via shared _run_export_applescript()
      5. Wait for WAV to appear
    """
    import subprocess
    import time as _time

    app_name = _detect_ableton_app()
    abs_output = output_dir.resolve()

    # ── 1. Open .als in Ableton ──
    print(f"       5E: Opening Stage 5 render session in {app_name}…")
    subprocess.Popen(["open", "-a", app_name, str(als_path)])

    # ── 2. Dismiss any save-changes dialog (polls up to 10s) ──
    _time.sleep(2.0)
    if _dismiss_save_dialog(app_name):
        print("       5E: Save dialog dismissed")

    # ── 3. Poll until Ableton is ready ──
    print("       5E: Waiting for AbletonOSC to respond…")
    if not _wait_for_ableton_ready(bridge, timeout=90.0):
        log.warning("5E: Ableton did not respond within 90s — manual fallback")
        _bounce_stage5_print_instructions(als_path, output_dir, clip_layout)
        return _scan_stage5_bounces(output_dir, clip_layout)

    tempo = bridge.get_tempo() or 150.0
    print(f"       5E: Ableton ready — tempo={tempo} BPM, "
          f"{len(clip_layout)} patterns to bounce")

    # ── 4. Unsolo everything first ──
    for track_idx in range(3):
        bridge.set_track_solo(track_idx, False)
    _time.sleep(0.3)

    # ── 5. Bounce each pattern region (with retry) ──
    bounces: dict[str, Path] = {}
    rack_track_idx = 1  # Track 1 = 128 RACK

    for i, (clip_name, start_beat, length_beats) in enumerate(clip_layout):
        wav_path = output_dir / f"{clip_name}.wav"
        export_timeout = max((length_beats / tempo) * 60 + 20, 45.0)
        success = False

        for attempt in range(_BOUNCE_MAX_RETRIES + 1):
            # Remove stale file
            if wav_path.exists():
                wav_path.unlink()

            # Set loop to this clip's region
            bridge.set_loop(True, start_beat, length_beats)
            _time.sleep(0.2)

            # Solo the 128 RACK track
            bridge.set_track_solo(rack_track_idx, True)
            _time.sleep(0.3)

            # ── PREVIEW: play 6s of this drum pattern so you can hear it ──
            bridge.jump_to(start_beat)
            bridge.play()
            _time.sleep(6.0)
            bridge.stop()
            bridge.jump_to(start_beat)
            _time.sleep(0.3)

            label = (f"       5E: Bouncing {clip_name} "
                     f"({i + 1}/{len(clip_layout)})"
                     f"{f' retry {attempt}' if attempt > 0 else ''}…")
            print(label)

            ok, err = _run_export_applescript(
                app_name, clip_name, str(abs_output),
            )
            if not ok:
                log.warning("5E: AppleScript failed for %s: %s",
                            clip_name, err)
                # Press Escape to dismiss any stuck dialog
                _proc = _detect_ableton_process()
                try:
                    subprocess.run(
                        ["osascript", "-e",
                         f'tell application "System Events" to tell process '
                         f'"{_proc}" to keystroke (ASCII character 27)'],
                        timeout=5, capture_output=True,
                    )
                except Exception:
                    pass
                _time.sleep(1.0)
                bridge.set_track_solo(rack_track_idx, False)
                _time.sleep(0.3)
                if attempt < _BOUNCE_MAX_RETRIES:
                    continue
                break

            # Wait for the WAV to appear
            if _wait_for_file(wav_path, timeout=export_timeout):
                bounces[clip_name] = wav_path
                size_mb = wav_path.stat().st_size / (1024 * 1024)
                print(f"           ✓ {clip_name}.wav ({size_mb:.1f} MB)")
                success = True
            else:
                log.warning("5E: export timeout for %s (attempt %d/%d)",
                            clip_name, attempt + 1, _BOUNCE_MAX_RETRIES + 1)
                if attempt < _BOUNCE_MAX_RETRIES:
                    bridge.set_track_solo(rack_track_idx, False)
                    _time.sleep(0.3)
                    continue
                log.warning("5E: giving up on %s after %d attempts",
                            clip_name, _BOUNCE_MAX_RETRIES + 1)

            break

        # Unsolo and wait for Ableton to settle
        bridge.set_track_solo(rack_track_idx, False)
        if success:
            _wait_for_export_idle(bridge, timeout=5.0)
        _time.sleep(0.3)

    # ── 6. Summary ──
    print(f"       5E: Bounced {len(bounces)}/{len(clip_layout)} patterns")
    if len(bounces) < len(clip_layout):
        missing = [c for c, _, _ in clip_layout if c not in bounces]
        log.warning("5E: Missing bounces: %s", ", ".join(missing[:10]))

    return bounces


def _bounce_stage5_print_instructions(
    als_path: Path, output_dir: Path,
    clip_layout: list[tuple[str, float, float]],
) -> None:
    """Manual fallback — prints step-by-step Stage 5 bounce instructions."""
    print(f"\n{'=' * 60}")
    print("  ACTION REQUIRED: Bounce 128-rack pattern regions")
    print(f"{'=' * 60}")
    print(f"  1. Open: {als_path}")
    print("  2. For each clip region on Track 1 (128 RACK):")
    print("     Set loop → Solo Track 1 → Cmd+Shift+R → Export to:")
    print(f"     {output_dir}/{{clip_name}}.wav")
    print(f"  3. {len(clip_layout)} clips to bounce:")
    for clip_name, start, length in clip_layout[:20]:
        print(f"       → {clip_name}.wav  (beat {start:.0f}, "
              f"{length:.0f} beats)")
    if len(clip_layout) > 20:
        print(f"       … and {len(clip_layout) - 20} more")
    print(f"{'=' * 60}\n")


def _scan_stage5_bounces(
    output_dir: Path,
    clip_layout: list[tuple[str, float, float]],
) -> dict[str, Path]:
    """Scan output_dir for pre-existing Stage 5 bounced WAVs."""
    bounces: dict[str, Path] = {}
    for clip_name, _, _ in clip_layout:
        wav_path = output_dir / f"{clip_name}.wav"
        if wav_path.exists():
            bounces[clip_name] = wav_path
    return bounces


# ──────────────────────────────────────────────────────────────────────────
# 5F: COLLECT — Validate + catalog all rendered WAVs
# ──────────────────────────────────────────────────────────────────────────

def _collect_stage5_renders(
    bounces: dict[str, Path],
    manifest: AudioManifest | None = None,
) -> dict[str, dict[str, Path]]:
    """5F: Validate bounced WAVs and organize into section→group catalog.

    If a manifest is provided, marks each delivered file in it.

    Returns:
        dict[section_name, dict[zone_group, Path]] — ready for Phase 2.
        e.g. {"drop_1": {"drums": Path(...), "bass": Path(...)}, ...}
    """
    catalog: dict[str, dict[str, Path]] = {}

    for clip_name, path in bounces.items():
        if not path.exists():
            log.warning("5F: bounce missing: %s", path)
            continue
        try:
            with wave.open(str(path)) as wf:
                if wf.getnframes() == 0:
                    log.warning("5F: empty bounce: %s", path)
                    continue
                sr = wf.getframerate()
                if sr != SR:
                    log.warning("5F: unexpected sample rate %d in %s "
                                "(expected %d)", sr, path, SR)
        except Exception as exc:
            log.warning("5F: invalid WAV %s: %s", path, exc)
            continue

        # Parse clip_name into section + zone_group
        # Format: "{section_name}_{zone_group}" — split on first underscore
        # that separates known section names from zone groups.
        parts = clip_name.split("_")
        if len(parts) >= 2:
            # Try to find the split point: section names can contain
            # underscores (e.g. "drop_1", "build_2"), so we look for
            # known zone groups from the end.
            _ZONE_GROUPS = {
                "kicks", "snares", "hats", "perc", "sub", "low", "mid",
                "high", "fx", "melodic", "atmos", "vocal", "transitions",
                "bass",
            }
            split_idx = len(parts) - 1
            for i in range(len(parts) - 1, 0, -1):
                if parts[i] in _ZONE_GROUPS:
                    split_idx = i
                    break
            section = "_".join(parts[:split_idx])
            group = "_".join(parts[split_idx:])
        else:
            section = "global"
            group = clip_name

        if section not in catalog:
            catalog[section] = {}
        catalog[section][group] = path
        if manifest:
            manifest.mark_delivered(
                clip_name, path, file_size=path.stat().st_size)

    return catalog


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def run_phase_one(
    *,
    blueprint: SongBlueprint | None = None,
    dna: SongDNA | None = None,
    yaml_path: str | Path | None = None,
) -> SongMandate:
    """Execute Phase 1: IDEA → MANDATE.

    Accepts one of:
        - SongBlueprint (name + creative intent)
        - Pre-built SongDNA
        - YAML config path (e.g. configs/crystal_theorem.yaml)

    Returns a SongMandate with ALL ingredients Phase 2 (ARRANGE) needs.

    4-Stage execution order (compounding — each step feeds the next).
    Time signature: 4/4 always (BEATS_PER_BAR = 4).

        Stage 1: THE TOTAL RECIPE — compounding the full blueprint
                 1A Constants (PHI, FIBONACCI, A4_432)
                 1B DNA (variation_engine → SongDNA)
                 1C Harmony (chord progression)
                 1D Freq table (key/scale → 5-octave + phi lookup)
                 1E Palette intent (DNA sub-DNAs → timbral goals)
                 1F Template config (section structure)
                 1G Production recipe (quality targets + checkpoints)
                 1H Arrangement + RCO + sections + total_bars
                 1I Audio manifest (expected output catalog)

        Stage 2: MIDI SEQUENCES — what notes play?
                 2A Stem configs + MIDI for all stems + ghost kick
                 2B Galactia FX pre-load (risers, impacts)

        Stage 3: SYNTH FACTORY — design + render all synth audio
                 3A–3I: WT pipeline → presets → ALS build
                 3I+ Audio manifest (4E stem entries)
                 3J Live bounce (optional Ableton export)
                 3K Collect + production skeleton

        Stage 4: DRUM FACTORY — samples, rack, loops (NO synth content)
                 4A–4E: Drum selection → rack → loop MIDI
                 4F Pattern factory (drum patterns + 5E manifest entries)
                 4G ALS build + bounce + collect
    """
    mandate = SongMandate()

    # ── Load YAML config if provided ──
    yaml_config = None
    if yaml_path is not None:
        yaml_config = load_yaml_config(yaml_path)
        mandate.yaml_config = yaml_config

    # ══════════════════════════════════════════════════════════════════════
    print("\n═══ PHASE 1: IDEA → MANDATE ═══")

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║ STAGE 1: THE TOTAL RECIPE — compounding the full blueprint      ║
    # ║   DNA → Harmony → Freq → Palette → Config → Recipe →           ║
    # ║   Arrangement                                                    ║
    # ╚════════════════════════════════════════════════════════════════════╝
    print("  [Stage 1] THE TOTAL RECIPE — compounding the full blueprint...")

    # ── 1A: Constants (PHI, FIBONACCI, A4_432) — via config_loader ──

    # ── 1B: DNA — everything downstream depends on this ──
    print("    → 1B DNA...")
    mandate.dna = _oracle(blueprint, dna, yaml_config)
    beat_s = 60.0 / mandate.dna.bpm
    bar_s = beat_s * BEATS_PER_BAR
    mandate.beat_s = beat_s
    mandate.bar_s = bar_s
    _safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in mandate.dna.name).strip().replace(" ", "_") or "dubforge"
    print(f"       {mandate.dna.name} | {mandate.dna.key} {mandate.dna.scale} @ {mandate.dna.bpm} BPM")

    # ── 1C: Harmony — chord progression from DNA ──
    print("    → 1C harmony...")
    mandate.chord_progression = _build_chord_progression(mandate.dna)
    if mandate.chord_progression is not None:
        chords_str = " → ".join(
            c["symbol"] if isinstance(c, dict) else c.symbol
            for c in mandate.chord_progression.chords)
        print(f"       Chords: {chords_str}")
    else:
        print("       Chords: (fallback — no chord_progression module)")

    # ── 1D: Freq table — 5-octave lookup for key/scale ──
    print("    → 1D freq table...")
    mandate.freq_table = _build_freq_table(mandate.dna)

    # ── 1E: Palette intent — DNA sub-DNAs → timbral goals ──
    print("    → 1E palette intent...")
    intent = _design_palette_intent(mandate.dna)
    mandate.design_intent = intent

    # ── 1F: Template config — section structure from DNA ──
    print("    → 1F template config...")
    sections_raw = _extract_sections(mandate.dna)
    print(f"       Sections template: {' | '.join(f'{k}={v}bars' for k, v in sections_raw.items())}")

    # ── 1G: Production recipe — quality targets + Fibonacci checkpoints ──
    print("    → 1G production recipe...")
    if _HAS_RECIPE_BOOK:
        _mood = getattr(mandate.dna, "mood_name", "dark")
        _style = getattr(mandate.dna, "style", "dubstep")
        mandate.production_recipe = rb_select_recipe(_style, _mood, mandate.dna)
        print(f"       Recipe: {len(mandate.production_recipe.get('recipe_names', []))} recipes for {_style}/{_mood}")
    else:
        print("       Recipe: (fallback — using inline recipe builder)")

    recipes = _build_recipes(mandate.dna, intent, sections_raw)
    mandate.groove_template = recipes["groove_template"]
    mandate.quality_targets = recipes["quality_targets"]
    mandate.arrange_tasks = recipes["arrange_tasks"]

    if mandate.production_recipe and "targets" in mandate.production_recipe:
        for tgt in mandate.production_recipe["targets"]:
            mandate.quality_targets[tgt["name"]] = {
                "min": tgt.get("target_min"), "max": tgt.get("target_max"),
                "metric": tgt.get("metric"), "unit": tgt.get("unit"),
            }
    print(f"       Groove: {mandate.groove_template}")
    print(f"       Quality targets: {len(mandate.quality_targets)} specs")

    # ── 1H: Arrangement — DNA-driven layout + sections ──
    print("    → 1H arrangement...")
    mandate.arrangement_template = _build_arrangement_from_dna(mandate.dna)
    _arr_bars = sum(s.bars for s in mandate.arrangement_template.sections)
    print(f"       Arrangement: {mandate.arrangement_template.name} "
          f"({_arr_bars} bars, {len(mandate.arrangement_template.sections)} sections)")

    mandate.sections = _sections_from_arrangement(mandate.arrangement_template)
    mandate.total_bars = sum(mandate.sections.values())
    mandate.total_samples = int(mandate.total_bars * BEATS_PER_BAR * beat_s * SR)
    print(f"       Sections: {' → '.join(f'{k}({v})' for k, v in mandate.sections.items())}")
    print(f"       Total: {mandate.total_bars} bars, {mandate.total_samples / SR:.1f}s")

    # ── 1I: Template backflow — session template informs generation ──
    #    The canonical session template defines WHAT tracks exist.
    #    Stage 1I validates the SongMandate will produce content for
    #    every track slot so Phase 2 Setup finds no empty tracks.
    print("    → 1I template backflow (session template requirements)...")
    try:
        from engine.session_template import (
            get_template_requirements,
            build_dubstep_session,
            TRACK_TO_MANDATE,
        )
        _session_layout = build_dubstep_session(bpm=mandate.dna.bpm)
        _reqs = get_template_requirements(_session_layout)
        mandate.design_intent["session_template"] = {
            "required_stems": _reqs.required_stems,
            "required_instruments": _reqs.required_instruments,
            "bus_names": _reqs.bus_names,
            "return_names": _reqs.return_names,
            "scene_bars": _reqs.scene_bars,
            "total_bars": _reqs.total_bars,
            "sidechain_pairs": _reqs.sidechain_pairs,
            "track_to_mandate": dict(TRACK_TO_MANDATE),
        }
        print(f"       Session template: {len(_reqs.required_stems)} audio stems + "
              f"{len(_reqs.required_instruments)} MIDI instruments required")
        print(f"       Buses: {', '.join(_reqs.bus_names)} + "
              f"returns: {', '.join(_reqs.return_names)}")
        print(f"       Sidechain pairs: {len(_reqs.sidechain_pairs)}")
    except Exception as exc:
        log.warning("STAGE 1I: template backflow skipped: %s", exc)
        print(f"       Template backflow: skipped ({exc})")

    mandate.phase_log.append({"step": "total_recipe", "status": "complete"})

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║ STAGE 2: MIDI SEQUENCES — what notes play?                      ║
    # ║   Stem configs → MIDI for all stems → Galactia FX               ║
    # ╚════════════════════════════════════════════════════════════════════╝
    print("  [Stage 2] MIDI SEQUENCES — configuring stems and generating MIDI...")

    # ── 2A: MIDI — section-aware MIDI for all stems + ghost kick ──
    #    NOTE: stem_configs not built yet (that's Stage 3G). We pass a
    #    minimal config so MIDI generation can access arrangement + energy.
    #    The actual Serum 2 synthesis spec is NOT needed for note selection.
    print("    → 2A generate MIDI sequences...")
    # Build a lightweight stem config for MIDI generation (no WT/preset data needed)
    _midi_stem_configs = _configure_stem_specs(mandate)
    mandate.midi_sequences = _generate_midi_sequences(mandate, _midi_stem_configs)
    total_notes = sum(len(v) for v in mandate.midi_sequences.values())
    active_stems = sum(1 for v in mandate.midi_sequences.values() if v)
    ghost_count = len(mandate.midi_sequences.get("ghost_kick", []))
    print(f"       {total_notes} notes across {active_stems} stems, "
          f"ghost_kick={ghost_count} triggers")

    mandate.phase_log.append({"step": "midi_sequences", "status": "complete",
                              "total_notes": total_notes, "active_stems": active_stems})

    # ── 2B: Collect Galactia FX samples early ──
    #    _sketch_fx in 3G prefers Galactia samples over synthesis fallback.
    #    Collect now so they're available when Stage 3 runs.
    mandate.galactia_fx = _collect_fx_samples(intent)
    fx_count = sum(len(v) for v in [mandate.galactia_fx.risers, mandate.galactia_fx.impacts,
                                     mandate.galactia_fx.reverses, mandate.galactia_fx.falling,
                                     mandate.galactia_fx.rising, mandate.galactia_fx.shepard,
                                     mandate.galactia_fx.buildups])
    print(f"    → 2B Galactia FX pre-loaded: {fx_count} samples")

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║ STAGE 3: SYNTH FACTORY — design + render all synth audio        ║
    # ║   WT intake → Generate → Mod → FX → Morph → Presets →          ║
    # ║   Configure → ALS → Bounce → Collect                           ║
    # ╚════════════════════════════════════════════════════════════════════╝
    print("  [Stage 3] SYNTH FACTORY — wavetable design, presets, bounce...")

    # ── 3A: Intake — collect existing wavetables from Galactia ──
    mandate.wavetables = _collect_wavetables()
    wt_count_intake = len(mandate.wavetables.frames)
    print(f"       3A Intake: {wt_count_intake} wavetables collected")

    # ── 3B: Generate — DNA-driven WT packs tuned to this song ──
    mandate.wavetable_packs, gen_count = _generate_dna_wavetables(
        mandate.dna, intent, mandate.wavetables,
    )
    wt_count = len(mandate.wavetables.frames)
    print(f"       3B Generate: {gen_count} DNA-driven packs "
          f"(FM:{int(4 + mandate.dna.bass.fm_depth * 1.2)} "
          f"harm:{int(6 + mandate.dna.lead.brightness * 10)} "
          f"root:{mandate.dna.key}) — {wt_count} total WTs")

    # ── 3C: Modulation — DNA-driven Serum 2 mod matrix per stem ──
    mandate.modulation_routes = _design_modulation_routes(mandate.dna, intent)
    mod_stems = list(mandate.modulation_routes.keys())
    mod_route_count = sum(
        len(v.get("mod_matrix", [])) for v in mandate.modulation_routes.values()
    )
    print(f"       3C Modulation: {mod_route_count} routes across {mod_stems}")

    # ── 3D: FX chains — DNA-driven Ableton FX rack per stem ──
    mandate.fx_chains = _design_fx_chains(mandate.dna, intent)
    fx_stems = list(mandate.fx_chains.keys())
    fx_slot_count = sum(len(v) for v in mandate.fx_chains.values())
    print(f"       3D FX chains: {fx_slot_count} slots across {fx_stems}")

    # ── 3E: Morph — DNA-informed morphing (type from mood) ──
    morph_type = _select_morph_type(mandate.dna)
    mandate.morph_wavetables = _morph_all_wavetables(
        mandate.dna, mandate.wavetables, mandate.modulation_routes,
    )
    wt_count = len(mandate.wavetables.frames)
    morph_count = len(mandate.morph_wavetables)
    print(f"       3E Morph: {morph_count} {morph_type} morphs — {wt_count} total WTs")

    # ── 3F: Serum 2 presets — build base + DNA mutation ──
    if _HAS_SERUM2_PRESET:
        try:
            mandate.serum2_presets = s2_build_all_presets()
            mandate.serum2_state_map = s2_get_preset_state_map()
            preset_names = list(mandate.serum2_presets.keys())
            print(f"       3F Presets: {len(preset_names)} Serum 2 presets — "
                  f"{', '.join(preset_names[:4])}...")
        except Exception as exc:
            log.warning("STAGE 3F: serum2_preset failed: %s", exc)
            print(f"       3F Presets: Serum 2 skipped ({exc})")
    else:
        print("       3F Presets: serum2_preset not available (cbor2?)")

    # ── 3G: REMOVED — Python sketch renderers deleted (Path B) ──
    #    All synth audio now comes exclusively from Serum 2 → ALS → Ableton
    #    bounce (Path A).  The _sketch_* functions produced numpy preview
    #    audio that was disconnected from the wavetable/modulation/FX
    #    design in 3A-3E.  Serum 2 presets (3F→3H+) carry the WT frames,
    #    mod matrix, and FX chains — Ableton renders the final wet audio.
    print("       → 3G Skipped — all audio via Serum 2 → Ableton bounce")

    # ── 3H: Configure — REBUILD stem specs with 3A-3E data ──
    #    2A stem_configs were built before modulation_routes, fx_chains,
    #    wavetable_packs, and morph_wavetables existed — mod_matrix/lfos/
    #    wavetable_frames were all empty.  Rebuild now that 3A-3E are done.
    print("       → 3H Configure stem specs (rebuild with 3A-3E data)...")
    mandate.stem_configs = _configure_stem_specs(mandate)
    tuning = getattr(mandate.dna, "tuning_hz", 440.0)
    _s3h_mod_routes = sum(len(c.mod_matrix) for c in mandate.stem_configs.values())
    _s3h_wt_frames = sum(len(c.wavetable_frames) for c in mandate.stem_configs.values())
    print(f"       {len(mandate.stem_configs)} stem configs "
          f"(root={_freq_to_midi(mandate.dna.root_freq, tuning)} "
          f"{mandate.dna.key}{mandate.dna.scale}, "
          f"mod_routes={_s3h_mod_routes}, wt_frames={_s3h_wt_frames})")

    # ── 3H+: DNA-mutate Serum 2 presets per stem ──
    print("       → 3H+ Mutate Serum 2 presets...")
    s4_state_map = _mutate_presets_dna(mandate, mandate.stem_configs)
    if s4_state_map:
        mandate.serum2_state_map.update(s4_state_map)
    print(f"       {len(s4_state_map)} preset states generated")

    # ── 3I: ALS — build render .als with ghost kick sidechain ──
    print("       → 3I Build render .als...")
    mandate.render_als_path = _build_render_als(
        mandate, mandate.stem_configs, mandate.serum2_state_map,
        mandate.midi_sequences,
    )
    if mandate.render_als_path:
        print(f"       Render session: {mandate.render_als_path}")
    else:
        print("       Render session: skipped (als_generator unavailable)")

    # ── 3I+: Audio manifest — 4E stem entries (5E added at Stage 4F) ──
    mandate.audio_manifest = _build_audio_manifest(safe_name=_safe_name)
    s4_count = sum(1 for f in mandate.audio_manifest.files if f.stage == "4E")
    print(f"       3I+ Manifest: {s4_count} stem bounce entries (5E deferred to 4F)")

    # ── 3J: Live bounce (optional) — Serum 2 wet render via Ableton ──
    bounces: dict[str, Path] = {}
    try:
        bounces = _bounce_render_tracks(mandate.render_als_path, mandate=mandate)
    except RuntimeError as exc:
        log.warning("3J Live bounce skipped: %s", exc)
        print(f"  ⚠ 3J Live bounce skipped: {exc}")

    # ── 3J+: Multi-pass resampling — Subtronics-style sound design ──
    #    Bass stems (neuro, wobble, riddim, mid_bass) get 3 passes:
    #      Pass 1: Saturator + OTT (body & grit)
    #      Pass 2: Auto Filter + Phaser (texture & movement)
    #      Pass 3: Freq Shifter + OTT (final character)
    #    sub_bass stays clean for club playback.
    if bounces:
        try:
            bounces = _resample_passes(bounces, mandate, num_passes=3)
        except RuntimeError as exc:
            log.warning("3J+ resample skipped: %s", exc)
            print(f"  ⚠ 3J+ resample skipped: {exc}")

    # ── 3K: Collect + production skeleton ──
    mandate.audio_clips = _collect_bounced_audio(
        bounces, manifest=mandate.audio_manifest)
    s4_delivered = sum(
        1 for f in mandate.audio_manifest.files
        if f.stage == "4E" and f.delivered
    )
    s4_total = sum(
        1 for f in mandate.audio_manifest.files if f.stage == "4E"
    )
    if mandate.audio_clips:
        print(f"       3K: {s4_delivered}/{s4_total} Serum 2 bounces collected")
    else:
        print(f"       3K: using synthesis audio (Ableton bounce available via ALS)")

    mandate.production_als_path = _build_production_skeleton(
        mandate, mandate.audio_clips, mandate.serum2_state_map,
        mandate.midi_sequences, mandate.stem_configs,
    )
    if mandate.production_als_path:
        print(f"       3K: Production session: {mandate.production_als_path}")

    mandate.phase_log.append({
        "step": "synth_factory", "status": "complete",
        "wt_intake": wt_count_intake, "wt_total": wt_count,
        "morph_type": morph_type, "morph_count": morph_count,
        "mod_route_count": mod_route_count, "fx_slot_count": fx_slot_count,
        "serum2_presets": len(mandate.serum2_presets),
        "stem_configs": len(mandate.stem_configs),
        "render_als": str(mandate.render_als_path) if mandate.render_als_path else None,
        "bounces_found": len(mandate.audio_clips),
    })

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║ STAGE 4: DRUM FACTORY — samples, rack, loops                    ║
    # ║   Galactia selection → Processing → 128 Rack → Loop MIDI →     ║
    # ║   Pattern factory → ALS → Bounce → Collect                     ║
    # ╚════════════════════════════════════════════════════════════════════╝
    print("  [Stage 4] DRUM FACTORY — samples, rack, loops...")

    # ── 4A: Select drum samples from Galactia ──
    mandate.drums = _collect_drums(mandate.dna, intent)
    drum_sources = [getattr(mandate.drums, f"{a}_source") for a in
                    ("kick", "snare", "hat_closed", "hat_open", "clap",
                     "crash", "ride", "perc")
                    if getattr(mandate.drums, f"{a}_source")]
    print(f"       4A Drums: {len(drum_sources)} hits — {', '.join(drum_sources[:3])}")

    # ── 4A+: Galactia FX already collected in Stage 2B ──
    fx_count = sum(len(v) for v in [mandate.galactia_fx.risers, mandate.galactia_fx.impacts,
                                     mandate.galactia_fx.reverses, mandate.galactia_fx.falling,
                                     mandate.galactia_fx.rising, mandate.galactia_fx.shepard,
                                     mandate.galactia_fx.buildups])
    print(f"       4A+ FX samples: {fx_count} (pre-loaded in Stage 2B)")

    # ── 4B: Galactia zone map (raw audio → Rack128 zones) ──
    print("       4B Mapping Galactia samples to Rack zones...")
    try:
        from engine.galatcia import map_galactia_to_zones
        mandate.galactia_zone_map = map_galactia_to_zones()
        gal_summary = mandate.galactia_zone_map.summary()
        gal_total = mandate.galactia_zone_map.total_audio
        print(f"       Galactia zone map: {gal_total} audio samples — {gal_summary}")
    except Exception as exc:
        log.warning("GALACTIA ZONE MAP: failed (%s)", exc)
        print(f"  ⚠ Galactia zone map failed: {exc}")
        mandate.galactia_zone_map = None

    # ── 4C: Process/sketch drum samples ──
    print("       4C Processing drums...")
    mandate.drums = _sketch_drums(mandate.drums, mandate.dna)

    # ── 4D: Build 128 Rack (drums + FX + synth zones) ──
    print("       4D Building 128 Rack...")
    mandate.rack_128 = _build_128_rack(mandate.drums, mandate.galactia_fx)
    # Load Galactia raw audio into remaining rack zones
    if mandate.galactia_zone_map is not None:
        _galactia_counts = dict(mandate.rack_128.zone_counts)
        for zone, samples in mandate.galactia_zone_map.zones.items():
            for name, audio, source in samples:
                _rack_add(mandate.rack_128, _galactia_counts, zone,
                          name, audio, source)
        mandate.rack_128.zone_counts = _galactia_counts

    # ── 4D+: Fill synth zones (bass, leads, wobble, riddim, growl, melody, etc.) ──
    _synth_counts = dict(mandate.rack_128.zone_counts)
    _fill_synth_zones(
        mandate.rack_128, _synth_counts,
        bass=mandate.bass,
        leads=mandate.leads,
        atmosphere=mandate.atmosphere,
        fx=mandate.fx,
        vocals=mandate.vocals,
        wavetables=mandate.wavetables,
        galactia_fx=mandate.galactia_fx,
        melody=mandate.melody,
        wobble=mandate.wobble_bass,
        riddim=mandate.riddim_bass,
        growl=mandate.growl_textures,
    )
    mandate.rack_128.zone_counts = _synth_counts

    total_slots = sum(mandate.rack_128.zone_counts.values())
    zone_str = " | ".join(f"{z}={c}" for z, c in mandate.rack_128.zone_counts.items() if c > 0)
    print(f"       4D complete: {total_slots}/128 slots — {zone_str}")

    # MIDI map the rack
    mandate.rack_midi_map = _build_rack_midi_map(mandate.rack_128)
    print(f"       MIDI map: {len(mandate.rack_midi_map.note_map)} notes assigned")

    # ── 4E: Drum loops (all section types) ──
    print("       4E Building drum loops...")
    mandate.drum_loops = _build_drum_loops(mandate.drums, mandate.dna, mandate.sections)
    loop_names = list(mandate.drum_loops.patterns.keys())
    print(f"       Loops: {len(loop_names)} patterns — {', '.join(loop_names)}")

    mandate.loop_midi_maps = _build_loop_midi_maps(
        mandate.drum_loops, mandate.rack_128, mandate.dna)
    total_hits = sum(len(lm.hits) for lm in mandate.loop_midi_maps)
    print(f"       Loop MIDI: {len(mandate.loop_midi_maps)} patterns, {total_hits} hits")

    # ── 4F: Pattern factory — MIDI patterns per section × zone group ──
    print("       4F Pattern Factory — building render patterns per section...")
    render_patterns: dict[str, dict[str, list]] = {}
    section_roles = {}

    def _role_from_name(name: str) -> str:
        """Derive section role from its name (e.g. 'drop1' → 'drop')."""
        nl = name.lower()
        for keyword in ("intro", "build", "drop", "break", "bridge", "outro", "vip"):
            if keyword in nl:
                return keyword
        return "verse"

    if mandate.arrangement_template is not None:
        for sec in getattr(mandate.arrangement_template, "sections", []):
            sec_name = getattr(sec, "name", str(sec))
            section_roles[sec_name] = _role_from_name(sec_name)
    if not section_roles and mandate.sections:
        for sec_name in mandate.sections:
            section_roles[sec_name] = _role_from_name(sec_name)

    # Drum-only zones — synth stems are separate WAV tracks from Stage 4
    _ROLE_ZONES: dict[str, list[str]] = {
        "intro":  ["kicks", "hats", "fx"],
        "build":  ["kicks", "snares", "hats", "perc", "fx", "transitions"],
        "drop":   ["kicks", "snares", "hats", "perc", "fx"],
        "break":  ["hats", "perc"],
        "bridge": ["kicks", "hats", "fx"],
        "verse":  ["kicks", "snares", "hats", "perc"],
        "outro":  ["kicks", "hats"],
        "vip":    ["kicks", "snares", "hats", "perc", "fx", "transitions"],
    }

    for sec_name, role in section_roles.items():
        active_zones = _ROLE_ZONES.get(role, _ROLE_ZONES["verse"])
        sec_patterns: dict[str, list] = {}

        # DNA-driven pattern parameters
        _dd = mandate.dna.drums
        _hat_steps = _dd.hat_density // 2  # 8 or 16 steps per bar
        _hat_step_dur = 4.0 / _hat_steps    # 0.5 or 0.25 beats
        _kick_vel = int(70 + _dd.kick_drive * 57)    # 70–127
        _snare_vel = int(70 + _dd.snare_noise_mix * 57)
        _hat_vel_on = int(55 + _dd.hat_brightness * 45)   # 55–100
        _hat_vel_off = int(_hat_vel_on * 0.7)
        _style = getattr(mandate.dna, "style", "dubstep").lower()

        for zone in active_zones:
            zone_slots = [
                (name, data["zone_num"])
                for name, data in mandate.rack_128.slots.items()
                if data.get("zone") == zone
            ]
            if not zone_slots:
                continue

            hits: list[dict] = []
            n_bars = mandate.sections.get(sec_name, 8)

            if zone in ("kicks",):
                for bar in range(n_bars):
                    # Halftime kick on 1
                    slot = zone_slots[0]
                    hits.append({"note": slot[1], "time": bar * 4.0,
                                 "duration": 0.5, "velocity": _kick_vel})
                    # Kick on 3 for halftime (dubstep standard)
                    if role in ("drop", "vip"):
                        hits.append({"note": slot[1], "time": bar * 4.0 + 2.0,
                                     "duration": 0.5, "velocity": int(_kick_vel * 0.85)})
                    # Double-kick fill for aggressive styles
                    if _style in ("tearout", "brostep") and role in ("drop", "vip") and bar % 4 == 3:
                        hits.append({"note": slot[1], "time": bar * 4.0 + 1.0,
                                     "duration": 0.25, "velocity": int(_kick_vel * 0.7)})
            elif zone in ("snares",):
                for bar in range(n_bars):
                    slot = zone_slots[0]
                    if role in ("drop", "vip"):
                        # Snare on 3 (beat 2.0 in 0-indexed) — halftime
                        hits.append({"note": slot[1], "time": bar * 4.0 + 3.0,
                                     "duration": 0.5, "velocity": _snare_vel})
                    elif role == "build":
                        # Rolls: subdivisions accelerate per bar
                        divisions = [4, 8, 16, 32][min(bar % 4, 3)]
                        step_t = 4.0 / divisions
                        for hit_i in range(divisions):
                            vel_ramp = 0.5 + 0.5 * (bar % 4) / 3 * hit_i / max(divisions - 1, 1)
                            hits.append({"note": slot[1],
                                         "time": bar * 4.0 + hit_i * step_t,
                                         "duration": min(step_t, 0.5),
                                         "velocity": int(_snare_vel * vel_ramp)})
                    else:
                        hits.append({"note": slot[1], "time": bar * 4.0 + 2.0,
                                     "duration": 0.5, "velocity": int(_snare_vel * 0.8)})
            elif zone in ("hats",):
                _groove_nudge = _dd.hi_hat_separation_ms / 1000.0 * (mandate.dna.bpm / 60.0)
                for bar in range(n_bars):
                    for step in range(_hat_steps):
                        slot = zone_slots[step % len(zone_slots)]
                        vel = _hat_vel_on if step % 2 == 0 else _hat_vel_off
                        hits.append({"note": slot[1],
                                     "time": bar * 4.0 + step * _hat_step_dur + (_groove_nudge if step % 2 == 1 else 0.0),
                                     "duration": _hat_step_dur * 0.8,
                                     "velocity": vel})
            elif zone in ("fx", "transitions"):
                if zone_slots:
                    slot = zone_slots[0]
                    hits.append({"note": slot[1], "time": 0.0,
                                 "duration": 4.0, "velocity": 80})
                    if n_bars > 4 and len(zone_slots) > 1:
                        slot2 = zone_slots[1]
                        hits.append({"note": slot2[1],
                                     "time": (n_bars - 2) * 4.0,
                                     "duration": 8.0, "velocity": 75})
            elif zone in ("perc",):
                for bar in range(n_bars):
                    for sixteenth in (1, 3, 5, 7, 9, 11, 13, 15):
                        slot = zone_slots[sixteenth % len(zone_slots)]
                        hits.append({"note": slot[1],
                                     "time": bar * 4.0 + sixteenth * 0.25,
                                     "duration": 0.25, "velocity": 65})

            if hits:
                sec_patterns[zone] = hits

        if sec_patterns:
            render_patterns[sec_name] = sec_patterns

    mandate.render_patterns = render_patterns
    n_sections = len(render_patterns)
    n_total_hits = sum(
        sum(len(hits) for hits in zones.values())
        for zones in render_patterns.values()
    )
    print(f"       4F complete: {n_sections} sections, {n_total_hits} total MIDI hits")

    # Add 5E manifest entries from actual render patterns
    manifest = mandate.audio_manifest
    s5_dir = Path("output") / _safe_name / "stage5_renders"
    for sec_name, zone_map in render_patterns.items():
        for zone_group in zone_map:
            clip_name = f"{sec_name}_{zone_group}"
            manifest.files.append(AudioFileSpec(
                name=clip_name,
                stem_type="pattern_5e",
                function=f"Section '{sec_name}' — {zone_group} pattern render",
                stage="5E",
                path=s5_dir / f"{clip_name}.wav",
            ))
    s5e_final = sum(1 for f in manifest.files if f.stage == "5E")
    print(f"       Manifest updated: {s5e_final} pattern renders (actual zones)")

    # ── 4F+: FX chains per drum zone group (synth FX are in Stage 3D) ──
    print("       4F+ FX chains — drum zone groups...")
    _dd_fx = mandate.dna.drums
    _energy_fx = getattr(mandate.dna, "energy", 0.7)
    fx_chains_s5: dict[str, list[dict]] = {
        "kicks":     [{"type": "Compressor", "params": {"Ratio": round(2.0 + _dd_fx.kick_drive * 3.0, 1), "Attack": round(_dd_fx.kick_attack / 1000.0, 4)}}],
        "snares":    [{"type": "Compressor", "params": {"Ratio": round(_dd_fx.snare_compression, 1)}},
                      {"type": "Reverb", "params": {"DecayTime": round(0.1 + _dd_fx.clap_reverb * 2.0, 2), "DryWet": round(0.05 + _dd_fx.clap_reverb * 0.3, 2)}}],
        "hats":      [{"type": "EQ Eight", "params": {"HPFreq": round(_dd_fx.hat_frequency)}},
                      {"type": "Compressor", "params": {"Ratio": 2.0}}],
        "perc":      [{"type": "Saturator", "params": {"Drive": round(0.1 + _energy_fx * 0.3, 2)}},
                      {"type": "Delay", "params": {"Time": "1/16", "Feedback": 0.2, "DryWet": 0.1}}],
        "fx":        [{"type": "Reverb", "params": {"DecayTime": 2.0, "DryWet": 0.4}},
                      {"type": "Delay", "params": {"Time": "1/8", "Feedback": 0.3}}],
        "transitions": [{"type": "Auto Filter", "params": {"Frequency": 8000, "Type": "HP"}},
                        {"type": "Reverb", "params": {"DecayTime": 1.5, "DryWet": 0.5}}],
    }
    mandate.fx_chains["stage5"] = fx_chains_s5
    active_fx = sum(1 for chain in fx_chains_s5.values() if chain)
    print(f"       4F+ complete: {active_fx} zone FX chains configured")

    # ── 4G: ALS build + bounce + collect ──
    print("       → 4G Build drum render .als...")
    mandate.stage5_als_path = _build_stage5_als(mandate)
    if mandate.stage5_als_path:
        clip_layout = _get_stage5_clip_layout(mandate)
        print(f"       Render session: {mandate.stage5_als_path} "
              f"({len(clip_layout)} clips)")
    else:
        print("       Render session: skipped (als_generator unavailable)")

    s5_bounces: dict[str, Path] = {}
    _ui_mode = os.environ.get("DUBFORGE_UI_MODE") == "1"
    if _ui_mode:
        print("  ⚠ 5G Live bounce deferred — open ALS in Ableton manually to render stems")
    try:
        if not _ui_mode:
            s5_bounces = _bounce_stage5_patterns(
                mandate.stage5_als_path, mandate,
            )
    except RuntimeError as exc:
        log.warning("5G Live bounce skipped: %s", exc)
        print(f"  ⚠ 5G Live bounce skipped: {exc}")

    mandate.stage5_renders = _collect_stage5_renders(
        s5_bounces, manifest=mandate.audio_manifest)
    s5e_delivered = sum(
        1 for f in mandate.audio_manifest.files
        if f.stage == "5E" and f.delivered
    )
    s5e_total = sum(
        1 for f in mandate.audio_manifest.files if f.stage == "5E"
    )
    if mandate.stage5_renders:
        total_wavs = sum(len(g) for g in mandate.stage5_renders.values())
        print(f"       4G: {s5e_delivered}/{s5e_total} pattern renders collected "
              f"({len(mandate.stage5_renders)} sections)")
    else:
        print(f"       4G: pattern ALS ready (open in Live to bounce {s5e_total} renders)")

    mandate.phase_log.append({
        "step": "drum_factory", "status": "complete",
        "drum_count": len(drum_sources), "fx_count": fx_count,
        "total_slots": total_slots,
        "zones": mandate.rack_128.zone_counts,
        "render_sections": n_sections, "render_hits": n_total_hits,
        "fx_chains": active_fx,
        "stage5_als": str(mandate.stage5_als_path) if mandate.stage5_als_path else None,
        "stage5_bounces": sum(
            len(g) for g in mandate.stage5_renders.values()
        ) if mandate.stage5_renders else 0,
        "manifest_total": mandate.audio_manifest.total,
        "manifest_delivered": mandate.audio_manifest.delivered_count,
    })

    # ══════════════════════════════════════════════════════════════════════
    n_wobble = len(mandate.wobble_bass.patterns)
    n_riddim = len(mandate.riddim_bass.patterns)
    n_arps = len(mandate.melody.arp_patterns)
    n_growl = len(mandate.growl_textures.frames)
    n_loops = len(mandate.drum_loops.patterns)
    n_midi_maps = len(mandate.loop_midi_maps)
    has_melody = mandate.melody.lead_melody is not None
    has_chords = mandate.chord_progression is not None
    n_render_secs = len(mandate.render_patterns)
    n_render_hits = sum(
        sum(len(h) for h in zones.values())
        for zones in mandate.render_patterns.values()
    )
    gal_count = mandate.galactia_zone_map.total_audio if mandate.galactia_zone_map else 0

    print(f"\n═══ PHASE 1 COMPLETE — SongMandate ready ═══")
    print(f"    {mandate.dna.name}: {mandate.total_bars} bars, "
          f"{total_slots}/128 rack slots")
    print(f"    drums={len(drum_sources)}, loops={n_loops}, "
          f"midi_maps={n_midi_maps}")
    print(f"    bass={len(mandate.bass.sounds)} types, "
          f"leads={len(mandate.leads.screech)} pitches, "
          f"chords={'✓' if has_chords else '✗'}, "
          f"melody={'✓' if has_melody else '✗'}")
    print(f"    arps={n_arps}, wobble={n_wobble}, riddim={n_riddim}, "
          f"growl={n_growl} frames, "
          f"tasks={len(mandate.arrange_tasks)}")
    print(f"    galactia={gal_count} samples, "
          f"render={n_render_secs} sections/{n_render_hits} hits")

    m = mandate.audio_manifest
    if m.delivered_count > 0:
        print(f"\n    Live bounces: {m.delivered_count}/{m.total} delivered")
    if m.pending and m.delivered_count > 0:
        print(f"    Pending: {len(m.pending)} (open ALS in Live to bounce)")

    # ── ICM workspace handoff ──────────────────────────────────────────
    try:
        from engine.workspace_io import write_phase_one_outputs
        write_phase_one_outputs(mandate)
        print("  ✓ Workspace: mwp/stages/01-generation/output/ updated")
    except Exception as _ws_exc:
        print(f"  ⚠ Workspace write skipped: {_ws_exc}")

    return mandate
