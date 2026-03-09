#!/usr/bin/env python3
"""DUBFORGE Variation Engine — Song DNA from Name + Theme.

Every track starts as a SongBlueprint (user intent) and gets expanded into
a SongDNA (complete synthesis specification) that forge.py consumes.

Design inspired by Subtronics' name↔sound philosophy:
  - "Scream Saver"  → screaming FM leads, chaotic energy
  - "Spacetime"     → cosmic pads, wide reverb, atmospheric
  - "String Theory" → plucky Karplus-Strong, arpeggiated precision
  - "Hollow Point"  → sharp transients, impact-focused, aggressive
  - "Amnesia"       → hazy, glitched, tape-degraded, dreamlike
  - "Clockwork"     → mechanical, precise rhythms, metallic

The engine uses semantic word→parameter mappings to translate
evocative track names into concrete synthesis decisions, then adds
controlled randomness for uniqueness within the stylistic constraints.

Architecture:
    SongBlueprint (user input)
         ↓
    VariationEngine.forge_dna()
         ↓
    SongDNA (complete spec)
         ↓
    forge.py render_full_track(dna)
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from engine.config_loader import PHI
from engine.mood_engine import (
    MOODS,
    blend_moods,
    get_mood_suggestion,
    resolve_mood,
)
from engine.tag_system import TAXONOMY

# ═══════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════

# All 12 chromatic notes
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Frequency lookup for all notes C1–B5
_FREQ_TABLE: dict[str, float] = {}
for _oct in range(1, 6):
    for _i, _n in enumerate(NOTES):
        _midi = 12 * (_oct + 1) + _i
        _FREQ_TABLE[f"{_n}{_oct}"] = 440.0 * (2.0 ** ((_midi - 69) / 12.0))

# Scale intervals (semitones from root)
SCALE_INTERVALS: dict[str, list[int]] = {
    "minor":          [0, 2, 3, 5, 7, 8, 10],
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "dorian":         [0, 2, 3, 5, 7, 9, 10],
    "lydian":         [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "pentatonic":     [0, 3, 5, 7, 10],
    "blues":          [0, 3, 5, 6, 7, 10],
    "whole_tone":     [0, 2, 4, 6, 8, 10],
    "chromatic":      list(range(12)),
}

# BPM ranges per sub-genre
BPM_RANGES: dict[str, tuple[int, int]] = {
    "dubstep":        (138, 152),
    "riddim":         (140, 155),
    "melodic":        (130, 150),
    "brostep":        (145, 160),
    "tearout":        (140, 155),
    "hybrid":         (135, 155),
    "deep_dubstep":   (138, 145),
    "colour_bass":    (130, 145),
    "experimental":   (120, 160),
}

# ═══════════════════════════════════════════
#  Semantic Word → Parameter Mappings
# ═══════════════════════════════════════════
# Subtronics-inspired: track names are metaphors for sonic attributes.
# Each keyword nudges synthesis params in a specific direction.

# fmt: off
WORD_ATOMS: dict[str, dict[str, float]] = {
    # ── Aggression / Violence ──
    "scream":    {"energy": 1.0, "darkness": 0.6, "distortion": 0.9, "fm_depth": 8.0, "attack_sharpness": 0.95, "formant_shift": 4.0},
    "shatter":   {"energy": 0.95, "darkness": 0.5, "distortion": 0.85, "transient_attack": 3.5, "granular_density": 0.8},
    "hollow":    {"energy": 0.85, "darkness": 0.7, "distortion": 0.7, "transient_attack": 3.0, "reverb_decay": 0.4},
    "bullet":    {"energy": 0.9, "darkness": 0.6, "transient_attack": 4.0, "distortion": 0.6, "kick_drive": 0.8},
    "blade":     {"energy": 0.88, "darkness": 0.55, "distortion": 0.75, "brightness": 0.85, "transient_attack": 2.8},
    "war":       {"energy": 1.0, "darkness": 0.8, "distortion": 0.9, "fm_depth": 7.0, "sub_weight": 0.9},
    "crush":     {"energy": 0.92, "darkness": 0.65, "distortion": 0.95, "bitcrush_depth": 6.0},
    "fang":      {"energy": 0.87, "darkness": 0.75, "distortion": 0.8, "fm_depth": 5.0, "brightness": 0.7},
    "venom":     {"energy": 0.85, "darkness": 0.8, "distortion": 0.7, "acid_resonance": 0.85, "filter_sweep": 0.9},
    "rage":      {"energy": 1.0, "darkness": 0.7, "distortion": 1.0, "fm_depth": 10.0, "chaos": 0.9},
    "impact":    {"energy": 0.95, "darkness": 0.5, "transient_attack": 4.5, "sub_weight": 0.95, "reverb_decay": 0.6},

    # ── Darkness / Mystery ──
    "shadow":    {"energy": 0.5, "darkness": 0.9, "reverb_decay": 1.5, "brightness": 0.2, "sub_weight": 0.7},
    "void":      {"energy": 0.3, "darkness": 1.0, "reverb_decay": 3.0, "brightness": 0.1, "sub_weight": 0.8, "pad_attack": 3.0},
    "abyss":     {"energy": 0.4, "darkness": 0.95, "reverb_decay": 2.5, "sub_weight": 0.9, "pad_attack": 2.5},
    "phantom":   {"energy": 0.5, "darkness": 0.85, "reverb_decay": 2.0, "chorus_depth": 0.6, "brightness": 0.25},
    "eclipse":   {"energy": 0.6, "darkness": 0.9, "reverb_decay": 1.8, "pad_attack": 2.0, "filter_sweep": 0.7},
    "midnight":  {"energy": 0.45, "darkness": 0.88, "reverb_decay": 1.6, "brightness": 0.2, "sub_weight": 0.75},
    "obsidian":  {"energy": 0.55, "darkness": 0.92, "distortion": 0.5, "brightness": 0.15, "sub_weight": 0.85},
    "crypt":     {"energy": 0.5, "darkness": 0.95, "reverb_decay": 2.2, "metallic": 0.6, "brightness": 0.18},
    "amnesia":   {"energy": 0.4, "darkness": 0.7, "reverb_decay": 2.5, "glitch_amount": 0.7, "tape_degrade": 0.6},

    # ── Space / Cosmic ──
    "space":     {"energy": 0.55, "darkness": 0.4, "reverb_decay": 3.5, "stereo_width": 1.8, "shimmer": 0.7, "pad_attack": 2.5},
    "cosmic":    {"energy": 0.6, "darkness": 0.35, "reverb_decay": 3.0, "stereo_width": 1.7, "shimmer": 0.8, "brightness": 0.6},
    "nebula":    {"energy": 0.5, "darkness": 0.45, "reverb_decay": 4.0, "granular_density": 0.6, "stereo_width": 1.9},
    "orbit":     {"energy": 0.65, "darkness": 0.3, "lfo_rate": 0.5, "stereo_width": 1.6, "reverb_decay": 2.0},
    "pulsar":    {"energy": 0.8, "darkness": 0.5, "lfo_rate": 8.0, "brightness": 0.75, "sync_bass": True},
    "nova":      {"energy": 0.9, "darkness": 0.3, "brightness": 0.9, "transient_attack": 3.0, "reverb_decay": 1.5},
    "galaxy":    {"energy": 0.6, "darkness": 0.4, "reverb_decay": 3.5, "stereo_width": 2.0, "pad_attack": 3.0},
    "stellar":   {"energy": 0.7, "darkness": 0.3, "brightness": 0.8, "shimmer": 0.6, "stereo_width": 1.5},
    "warp":      {"energy": 0.75, "darkness": 0.5, "pitch_dive_range": 24.0, "glitch_amount": 0.5, "fm_depth": 5.0},

    # ── Mechanical / Industrial ──
    "clockwork": {"energy": 0.7, "darkness": 0.6, "metallic": 0.8, "groove_swing": 0.0, "transient_attack": 2.5},
    "machine":   {"energy": 0.8, "darkness": 0.65, "metallic": 0.7, "distortion": 0.6, "groove_swing": 0.0},
    "piston":    {"energy": 0.85, "darkness": 0.55, "transient_attack": 3.0, "metallic": 0.5, "groove_swing": 0.0},
    "circuit":   {"energy": 0.7, "darkness": 0.5, "bitcrush_depth": 8.0, "glitch_amount": 0.4, "metallic": 0.3},
    "engine":    {"energy": 0.9, "darkness": 0.6, "distortion": 0.7, "fm_depth": 4.0, "sub_weight": 0.8},
    "chrome":    {"energy": 0.75, "darkness": 0.4, "metallic": 0.9, "brightness": 0.8, "distortion": 0.3},
    "rust":      {"energy": 0.6, "darkness": 0.75, "distortion": 0.8, "bitcrush_depth": 6.0, "brightness": 0.3},
    "forge":     {"energy": 0.85, "darkness": 0.65, "distortion": 0.75, "metallic": 0.6, "fm_depth": 6.0},
    "titanium":  {"energy": 0.8, "darkness": 0.4, "metallic": 0.95, "brightness": 0.75, "transient_attack": 2.0},

    # ── Nature / Organic ──
    "thunder":   {"energy": 0.95, "darkness": 0.6, "sub_weight": 1.0, "reverb_decay": 2.0, "transient_attack": 4.0},
    "storm":     {"energy": 0.9, "darkness": 0.55, "noise_amount": 0.5, "reverb_decay": 1.5, "chaos": 0.6},
    "earthquake":{"energy": 1.0, "darkness": 0.7, "sub_weight": 1.0, "distortion": 0.8, "lfo_rate": 1.0},
    "lava":      {"energy": 0.8, "darkness": 0.7, "distortion": 0.85, "filter_sweep": 0.8, "warmth": 0.9},
    "tidal":     {"energy": 0.65, "darkness": 0.4, "lfo_rate": 0.3, "reverb_decay": 2.5, "filter_sweep": 0.6},
    "crystal":   {"energy": 0.5, "darkness": 0.2, "metallic": 0.7, "brightness": 0.95, "reverb_decay": 1.8},
    "glacier":   {"energy": 0.4, "darkness": 0.3, "reverb_decay": 4.0, "brightness": 0.7, "pad_attack": 4.0},
    "vortex":    {"energy": 0.85, "darkness": 0.55, "lfo_rate": 6.0, "filter_sweep": 0.9, "stereo_width": 1.6},

    # ── Mind / Psyche ──
    "dream":     {"energy": 0.3, "darkness": 0.3, "reverb_decay": 3.5, "shimmer": 0.8, "brightness": 0.6, "pad_attack": 3.0},
    "hypnotic":  {"energy": 0.6, "darkness": 0.55, "lfo_rate": 2.0, "reverb_decay": 1.5, "repetition": 0.9},
    "psyche":    {"energy": 0.7, "darkness": 0.5, "chorus_depth": 0.7, "phaser_depth": 0.6, "stereo_width": 1.8},
    "delirium":  {"energy": 0.8, "darkness": 0.6, "glitch_amount": 0.8, "pitch_dive_range": 12.0, "chaos": 0.7},
    "trance":    {"energy": 0.65, "darkness": 0.35, "lfo_rate": 2.5, "pad_attack": 1.5, "reverb_decay": 2.0},
    "euphoria":  {"energy": 0.85, "darkness": 0.15, "brightness": 0.9, "stereo_width": 1.7, "shimmer": 0.6},
    "zen":       {"energy": 0.2, "darkness": 0.3, "reverb_decay": 4.0, "brightness": 0.5, "pad_attack": 4.0},

    # ── Science / Abstract ──
    "atom":      {"energy": 0.7, "darkness": 0.5, "sub_weight": 0.95, "distortion": 0.4, "minimalism": 0.8},
    "quantum":   {"energy": 0.75, "darkness": 0.45, "glitch_amount": 0.6, "stereo_width": 1.5, "chaos": 0.5},
    "fractal":   {"energy": 0.65, "darkness": 0.5, "complexity": 0.9, "granular_density": 0.7, "self_similar": True},
    "string":    {"energy": 0.6, "darkness": 0.35, "karplus_strong": True, "brightness": 0.7, "arp_density": 0.8},
    "helix":     {"energy": 0.7, "darkness": 0.45, "lfo_rate": 3.0, "filter_sweep": 0.7, "stereo_width": 1.3},
    "cipher":    {"energy": 0.6, "darkness": 0.7, "glitch_amount": 0.5, "bitcrush_depth": 10.0, "metallic": 0.4},
    "prism":     {"energy": 0.65, "darkness": 0.2, "brightness": 0.95, "stereo_width": 1.8, "shimmer": 0.5},

    # ── Texture / Material ──
    "velvet":    {"energy": 0.4, "darkness": 0.35, "warmth": 0.9, "brightness": 0.3, "pad_attack": 2.0},
    "glass":     {"energy": 0.5, "darkness": 0.2, "metallic": 0.6, "brightness": 0.9, "reverb_decay": 2.0},
    "acid":      {"energy": 0.8, "darkness": 0.5, "acid_resonance": 0.9, "filter_sweep": 1.0, "distortion": 0.6},
    "neon":      {"energy": 0.75, "darkness": 0.25, "brightness": 0.95, "saturation": 0.5, "stereo_width": 1.4},
    "liquid":    {"energy": 0.5, "darkness": 0.35, "lfo_rate": 1.5, "filter_sweep": 0.7, "warmth": 0.7},
    "static":    {"energy": 0.55, "darkness": 0.6, "noise_amount": 0.7, "bitcrush_depth": 8.0, "glitch_amount": 0.3},
    "ember":     {"energy": 0.6, "darkness": 0.55, "warmth": 0.85, "distortion": 0.4, "brightness": 0.4},

    # ── Emotional State ──
    "wrath":     {"energy": 1.0, "darkness": 0.85, "distortion": 1.0, "fm_depth": 9.0, "chaos": 0.85},
    "grief":     {"energy": 0.3, "darkness": 0.9, "reverb_decay": 3.0, "pad_attack": 3.5, "brightness": 0.15},
    "bliss":     {"energy": 0.7, "darkness": 0.1, "brightness": 0.9, "shimmer": 0.7, "stereo_width": 1.6},
    "fury":      {"energy": 0.98, "darkness": 0.7, "distortion": 0.95, "transient_attack": 3.5, "fm_depth": 8.0},
    "serenity":  {"energy": 0.2, "darkness": 0.2, "reverb_decay": 4.0, "brightness": 0.6, "pad_attack": 4.0},
    "chaos":     {"energy": 0.95, "darkness": 0.6, "glitch_amount": 0.9, "chaos": 1.0, "fm_depth": 7.0},

    # ── Bass culture vernacular ──
    "wobble":    {"energy": 0.75, "darkness": 0.5, "lfo_rate": 3.0, "bass_type": "wobble"},
    "growl":     {"energy": 0.85, "darkness": 0.65, "fm_depth": 8.0, "distortion": 0.8, "bass_type": "growl"},
    "riddim":    {"energy": 0.8, "darkness": 0.6, "groove_swing": 0.0, "minimalism": 0.7, "bass_type": "dist_fm"},
    "filthy":    {"energy": 0.9, "darkness": 0.75, "distortion": 0.9, "fm_depth": 7.0, "bass_type": "neuro"},
    "heavy":     {"energy": 0.85, "darkness": 0.7, "sub_weight": 0.95, "distortion": 0.7, "bass_type": "dist_fm"},
    "deep":      {"energy": 0.5, "darkness": 0.7, "sub_weight": 0.9, "reverb_decay": 1.5, "brightness": 0.3},
    "tearout":   {"energy": 0.95, "darkness": 0.65, "distortion": 0.85, "transient_attack": 3.0, "bass_type": "sync"},
}
# fmt: on


# ═══════════════════════════════════════════
#  Arrangement Archetypes
# ═══════════════════════════════════════════

@dataclass
class ArrangementSection:
    """One section of the arrangement."""
    name: str
    bars: int
    energy: float  # 0–1
    elements: list[str] = field(default_factory=list)


ARRANGEMENT_ARCHETYPES: dict[str, list[ArrangementSection]] = {
    "standard": [
        ArrangementSection("intro",  8, 0.2, ["drone", "pad", "hats_sparse"]),
        ArrangementSection("build",  4, 0.5, ["kick", "snare_roll", "riser", "pad"]),
        ArrangementSection("drop1", 16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops", "noise_bed"]),
        ArrangementSection("break",  8, 0.35, ["pad", "plucks", "sub_long", "reverb_fx"]),
        ArrangementSection("build2", 4, 0.55, ["kick", "snare_roll", "riser", "swell"]),
        ArrangementSection("drop2", 16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops", "noise_bed", "extra_bass"]),
        ArrangementSection("outro",  8, 0.15, ["kick_fade", "pad_fade", "sub_fade"]),
    ],
    "extended_intro": [
        ArrangementSection("intro",  16, 0.15, ["drone", "pad", "texture", "hats_sparse"]),
        ArrangementSection("build",   4, 0.5, ["kick", "snare_roll", "riser"]),
        ArrangementSection("drop1",  16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead"]),
        ArrangementSection("break",   8, 0.3, ["pad", "plucks"]),
        ArrangementSection("build2",  4, 0.55, ["kick", "snare_roll", "riser"]),
        ArrangementSection("drop2",  16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "extra_bass"]),
        ArrangementSection("outro",   8, 0.1, ["pad_fade", "sub_fade"]),
    ],
    "double_drop": [
        ArrangementSection("intro",   8, 0.2, ["drone", "pad"]),
        ArrangementSection("build",   4, 0.5, ["kick", "riser"]),
        ArrangementSection("drop1",   8, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead"]),
        ArrangementSection("drop1b",  8, 1.0, ["kick", "snare", "hats", "sub", "bass_alt", "lead"]),
        ArrangementSection("break",   8, 0.3, ["pad", "plucks"]),
        ArrangementSection("build2",  4, 0.6, ["kick", "riser"]),
        ArrangementSection("drop2",   8, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops"]),
        ArrangementSection("drop2b",  8, 1.0, ["kick", "snare", "hats", "sub", "bass_alt", "lead", "extra_bass"]),
        ArrangementSection("outro",   8, 0.1, ["pad_fade"]),
    ],
    "minimal": [
        ArrangementSection("intro",   4, 0.15, ["drone"]),
        ArrangementSection("build",   4, 0.4, ["kick", "riser"]),
        ArrangementSection("drop1",  16, 1.0, ["kick", "snare", "hats", "sub", "bass"]),
        ArrangementSection("break",   4, 0.25, ["pad"]),
        ArrangementSection("drop2",  16, 1.0, ["kick", "snare", "hats", "sub", "bass"]),
        ArrangementSection("outro",   4, 0.1, ["kick_fade"]),
    ],
    "progressive": [
        ArrangementSection("intro",  16, 0.1, ["pad", "texture", "drone"]),
        ArrangementSection("verse1",  8, 0.35, ["kick_lite", "hats_sparse", "pad", "sub_long"]),
        ArrangementSection("build",   8, 0.55, ["kick", "snare_roll", "riser", "swell"]),
        ArrangementSection("drop1",  16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops"]),
        ArrangementSection("break",  16, 0.25, ["pad", "plucks", "texture"]),
        ArrangementSection("build2",  8, 0.6, ["kick", "snare_roll", "riser"]),
        ArrangementSection("drop2",  16, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "extra_bass"]),
        ArrangementSection("outro",  16, 0.08, ["pad_fade", "texture"]),
    ],
}


# ═══════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════

@dataclass
class SongBlueprint:
    """User-facing song specification — the creative intent.

    This is what you hand to the VariationEngine.
    """
    name: str                                # "Hollow Point"
    style: str = "dubstep"                   # dubstep, riddim, melodic, tearout...
    theme: str = ""                          # "dark aggression", "cosmic voyage"
    mood: str = ""                           # mood_engine mood or blend "dark+aggressive"
    sound_style: str = ""                    # "growl heavy", "acid metallic"
    key: str = ""                            # "F", "C#", "" = auto-pick
    scale: str = ""                          # "minor", "phrygian", "" = auto
    bpm: int = 0                             # 0 = auto-pick from style range
    arrangement: str = ""                    # archetype name or "" = auto
    tags: list[str] = field(default_factory=list)
    seed: int = 0                            # 0 = random seed from name hash
    notes: str = ""                          # free-form artist notes


@dataclass
class DrumDNA:
    """Per-song drum personality."""
    kick_pitch: float = 45.0
    kick_fm_depth: float = 3.0
    kick_drive: float = 0.55
    kick_sub_weight: float = 0.65
    kick_attack: float = 3.0

    snare_pitch: float = 230.0
    snare_noise_mix: float = 0.5
    snare_metallic: float = 0.2
    snare_compression: float = 8.0

    hat_frequency: float = 8000.0
    hat_metallic: float = 0.15
    hat_brightness: float = 0.95

    clap_brightness: float = 0.95
    clap_reverb: float = 0.15

    snare_ott: float = 0.35
    hat_density: int = 16  # subdivisions per bar (8, 16, 32)


@dataclass
class BassDNA:
    """Per-song bass personality — what types to use and how hard to push them."""
    primary_type: str = "dist_fm"
    secondary_type: str = "sync"
    tertiary_type: str = "neuro"
    fm_depth: float = 8.0
    fm_feedback: float = 0.5
    distortion: float = 0.7
    filter_cutoff: float = 0.8
    acid_resonance: float = 0.0
    growl_resampler: bool = True
    lfo_rate: float = 2.5
    lfo_depth: float = 0.8
    sub_weight: float = 0.9
    mid_drive: float = 0.85

    pitch_dive_semi: float = 12.0
    wavefold_thresh: float = 0.6
    bitcrush_bits: int = 0  # 0 = off
    ott_amount: float = 0.4
    ring_mod_freq: float = 0.0  # 0 = off


@dataclass
class LeadDNA:
    """Per-song lead personality."""
    use_additive: bool = True
    additive_partials: int = 16
    additive_rolloff: str = "sawtooth"
    use_fm: bool = True
    fm_operators: int = 2
    fm_depth: float = 3.0
    brightness: float = 0.7
    reverb_decay: float = 0.5
    shimmer: float = 0.0

    supersaw_voices: int = 7
    supersaw_detune: float = 35.0
    supersaw_cutoff: float = 5500.0
    ott_amount: float = 0.3


@dataclass
class AtmosphereDNA:
    """Per-song atmosphere personality."""
    pad_type: str = "dark"
    pad_attack: float = 2.0
    pad_brightness: float = 0.3
    reverb_decay: float = 3.0
    stereo_width: float = 1.5
    shimmer: float = 0.0
    granular_density: float = 0.0
    drone_voices: int = 7
    drone_movement: float = 0.45
    use_karplus_drone: bool = False
    noise_bed_type: str = "pink"
    noise_bed_level: float = 0.15


@dataclass
class FxDNA:
    """Per-song FX personality."""
    riser_intensity: float = 0.85
    impact_intensity: float = 0.95
    glitch_amount: float = 0.0
    tape_degrade: float = 0.0
    stutter_rate: float = 16.0
    pitch_dive_range: float = 12.0
    vocal_chop_distortion: float = 0.35
    beat_repeat_probability: float = 0.25

    riser_start_freq: float = 150.0
    riser_end_freq: float = 8000.0
    boom_decay: float = 2.0


@dataclass
class MixDNA:
    """Per-song mix/master personality."""
    target_lufs: float = -7.5
    stereo_width: float = 1.3
    master_drive: float = 0.55
    eq_low_boost: float = 3.0
    eq_high_boost: float = 2.5
    compression_ratio: float = 3.5
    sidechain_depth: float = 0.7

    ceiling_db: float = -0.2
    eq_low_freq: float = 70.0
    eq_high_freq: float = 10000.0
    compression_threshold: float = -14.0
    limiter_enabled: bool = True


@dataclass
class SongDNA:
    """Complete song specification — every parameter forge.py needs.

    Generated by VariationEngine.forge_dna() from a SongBlueprint.
    """
    # Identity
    name: str
    style: str
    theme: str
    mood_name: str
    tags: list[str]
    seed: int

    # Musical
    key: str
    scale: str
    bpm: int
    root_freq: float  # Hz of root note octave 1

    # Frequency table for this key
    freq_table: dict[str, float] = field(default_factory=dict)

    # Arrangement
    arrangement: list[ArrangementSection] = field(default_factory=list)
    total_bars: int = 64

    # Sub-specifications
    drums: DrumDNA = field(default_factory=DrumDNA)
    bass: BassDNA = field(default_factory=BassDNA)
    lead: LeadDNA = field(default_factory=LeadDNA)
    atmosphere: AtmosphereDNA = field(default_factory=AtmosphereDNA)
    fx: FxDNA = field(default_factory=FxDNA)
    mix: MixDNA = field(default_factory=MixDNA)

    # Bass type rotation for drops
    bass_rotation: list[str] = field(default_factory=lambda: [
        "dist_fm", "sync", "neuro", "acid", "growl", "formant", "fm_growl"
    ])

    # Vocal chop vowels
    chop_vowels: list[str] = field(default_factory=lambda: ["ah", "oh", "ee", "oo"])

    # Notes
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        d = asdict(self)
        # Convert ArrangementSections
        d["arrangement"] = [asdict(s) for s in self.arrangement]
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"═══ Song DNA: {self.name} ═══",
            f"  Style:  {self.style} | Mood: {self.mood_name}",
            f"  Key:    {self.key} {self.scale} | BPM: {self.bpm}",
            f"  Root:   {self.root_freq:.2f} Hz",
            f"  Theme:  {self.theme}",
            f"  Tags:   {', '.join(self.tags[:8])}",
            f"  Bars:   {self.total_bars}",
            f"  Arrangement: {' → '.join(s.name for s in self.arrangement)}",
            f"  Bass:   {self.bass.primary_type} / {self.bass.secondary_type} / {self.bass.tertiary_type}",
            f"          FM depth={self.bass.fm_depth:.1f} dist={self.bass.distortion:.2f}",
            f"  Drums:  kick@{self.drums.kick_pitch:.0f}Hz drive={self.drums.kick_drive:.2f}",
            f"  Lead:   {'additive' if self.lead.use_additive else ''}"
            f"{'+ FM' if self.lead.use_fm else ''} bright={self.lead.brightness:.2f}",
            f"  Atmos:  {self.atmosphere.pad_type} pad, verb={self.atmosphere.reverb_decay:.1f}s",
            f"  Mix:    {self.mix.target_lufs:.1f} LUFS, width={self.mix.stereo_width:.1f}",
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════
#  Variation Engine
# ═══════════════════════════════════════════

class VariationEngine:
    """Transforms a SongBlueprint into a complete SongDNA.

    Pipeline:
    1. Parse name → extract semantic word atoms
    2. Resolve mood (mood_engine integration)
    3. Pick key/scale/BPM (from mood or semantic atoms)
    4. Build frequency table for chosen key
    5. Select arrangement archetype
    6. Derive DrumDNA, BassDNA, LeadDNA, AtmosphereDNA, FxDNA, MixDNA
       from aggregated word atoms + mood profile
    7. Apply artistic variation (PHI-weighted randomness)
    8. Return complete SongDNA
    """

    def __init__(self, artistic_variance: float = 0.15):
        """Init with artistic variance level.

        artistic_variance: 0.0 = deterministic from name, 1.0 = heavy randomness
        Default 0.15 = "slightly artistic" — consistent character with subtle surprises
        """
        self.artistic_variance = artistic_variance

    def forge_dna(self, blueprint: SongBlueprint) -> SongDNA:
        """The main entry point — blueprint → DNA."""
        # Seed from name hash if not specified
        seed = blueprint.seed
        if seed == 0:
            seed = int(hashlib.sha256(blueprint.name.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # 1. Parse name + theme + sound_style into word atoms
        atoms = self._extract_atoms(blueprint)

        # 2. Aggregate atom parameters
        params = self._aggregate_params(atoms)

        # 3. Resolve mood
        mood_name = self._resolve_mood(blueprint, params)
        mood_sug = get_mood_suggestion(mood_name, bpm=140.0)

        # 4. Key / Scale / BPM
        key = self._pick_key(blueprint, mood_sug, params, rng)
        scale = self._pick_scale(blueprint, mood_sug, params, rng)
        bpm = self._pick_bpm(blueprint, params, rng)

        # 5. Build frequency table for this key
        freq_table = self._build_freq_table(key, scale)

        # Root frequency
        root_note = f"{key}1"
        root_freq = _FREQ_TABLE.get(root_note, 43.65)

        # 6. Arrangement
        arrangement, total_bars = self._pick_arrangement(blueprint, params, rng)

        # 7. Build sub-DNAs
        drums = self._build_drum_dna(params, rng)
        bass = self._build_bass_dna(params, rng)
        lead = self._build_lead_dna(params, rng)
        atmos = self._build_atmosphere_dna(params, rng)
        fx = self._build_fx_dna(params, rng)
        mix_dna = self._build_mix_dna(params, rng)

        # 8. Bass rotation order
        bass_rotation = self._pick_bass_rotation(bass, params, rng)

        # 9. Chop vowels
        chop_vowels = self._pick_chop_vowels(params, rng)

        # 10. Tags
        tags = self._build_tags(blueprint, mood_name, params)

        dna = SongDNA(
            name=blueprint.name,
            style=blueprint.style,
            theme=blueprint.theme or self._infer_theme(atoms),
            mood_name=mood_name,
            tags=tags,
            seed=seed,
            key=key,
            scale=scale,
            bpm=bpm,
            root_freq=root_freq,
            freq_table=freq_table,
            arrangement=arrangement,
            total_bars=total_bars,
            drums=drums,
            bass=bass,
            lead=lead,
            atmosphere=atmos,
            fx=fx,
            mix=mix_dna,
            bass_rotation=bass_rotation,
            chop_vowels=chop_vowels,
            notes=blueprint.notes,
        )

        return dna

    # ───────────────────────────────────────────
    #  Step 1: Extract word atoms from name/theme
    # ───────────────────────────────────────────

    def _extract_atoms(self, bp: SongBlueprint) -> list[dict[str, float]]:
        """Parse all text fields and find matching word atoms."""
        text = f"{bp.name} {bp.theme} {bp.sound_style} {bp.mood} {' '.join(bp.tags)}"
        words = text.lower().replace("-", " ").replace("_", " ").split()

        atoms = []
        matched_words = set()

        for word in words:
            # Direct match
            if word in WORD_ATOMS:
                atoms.append(WORD_ATOMS[word])
                matched_words.add(word)
                continue

            # Substring match — "screamsaver" contains "scream"
            for atom_key, atom_val in WORD_ATOMS.items():
                if atom_key in word and atom_key not in matched_words:
                    atoms.append(atom_val)
                    matched_words.add(atom_key)

            # Suffix patterns — words ending in common suffixes
            if word.endswith("tion") or word.endswith("sion"):
                atoms.append({"complexity": 0.1})
            if word.endswith("ness"):
                atoms.append({"pad_attack": 0.3})

        return atoms

    # ───────────────────────────────────────────
    #  Step 2: Aggregate parameters from atoms
    # ───────────────────────────────────────────

    def _aggregate_params(self, atoms: list[dict]) -> dict[str, float]:
        """Merge all atom parameters using weighted averaging.

        For numeric values: weighted mean (later atoms have slightly more weight).
        For boolean/string values: majority vote.
        """
        if not atoms:
            # Default aggressive dubstep
            return {"energy": 0.8, "darkness": 0.6, "distortion": 0.7, "fm_depth": 6.0}

        numeric_sums: dict[str, float] = {}
        numeric_counts: dict[str, int] = {}
        string_votes: dict[str, list] = {}

        for i, atom in enumerate(atoms):
            weight = 1.0 + i * 0.1  # later atoms slightly more weight
            for k, v in atom.items():
                if isinstance(v, (int, float)):
                    numeric_sums[k] = numeric_sums.get(k, 0.0) + float(v) * weight
                    numeric_counts[k] = numeric_counts.get(k, 0) + 1
                elif isinstance(v, bool):
                    string_votes.setdefault(k, []).append(v)
                elif isinstance(v, str):
                    string_votes.setdefault(k, []).append(v)

        params: dict[str, float] = {}
        for k in numeric_sums:
            total_weight = sum(1.0 + i * 0.1 for i in range(numeric_counts[k]))
            params[k] = numeric_sums[k] / total_weight

        # Boolean/string: most common value
        for k, votes in string_votes.items():
            if all(isinstance(v, bool) for v in votes):
                params[k] = 1.0 if sum(votes) > len(votes) / 2 else 0.0
            else:
                # Pick the most common string
                from collections import Counter
                params[k] = Counter(votes).most_common(1)[0][0]

        return params

    # ───────────────────────────────────────────
    #  Step 3: Resolve mood
    # ───────────────────────────────────────────

    def _resolve_mood(self, bp: SongBlueprint, params: dict) -> str:
        """Determine mood from blueprint + aggregated params."""
        if bp.mood:
            # Support "dark+aggressive" blend syntax
            if "+" in bp.mood:
                parts = bp.mood.split("+")
                if len(parts) == 2:
                    return f"{resolve_mood(parts[0])}+{resolve_mood(parts[1])}"
            return resolve_mood(bp.mood)

        # Infer from params
        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)

        if energy > 0.85 and darkness > 0.7:
            return "aggressive"
        elif energy > 0.85 and darkness < 0.3:
            return "euphoric"
        elif darkness > 0.8:
            return "dark"
        elif energy < 0.35:
            return "dreamy"
        elif energy > 0.7 and darkness > 0.5:
            return "heavy"
        elif params.get("chaos", 0) > 0.5:
            return "chaotic"
        elif params.get("metallic", 0) > 0.5:
            return "alien"
        elif energy < 0.5:
            return "chill"
        else:
            return "aggressive"

    # ───────────────────────────────────────────
    #  Step 4: Pick key / scale / bpm
    # ───────────────────────────────────────────

    def _pick_key(self, bp: SongBlueprint, mood, params: dict,
                  rng: random.Random) -> str:
        """Choose key — from blueprint, mood, or name-hash."""
        if bp.key:
            return bp.key

        # Mood suggestion key
        if hasattr(mood, "key") and mood.key:
            base_key = mood.key
        else:
            base_key = "F"

        # Artistic variance: sometimes shift key
        if rng.random() < self.artistic_variance:
            # Pick a "related" key (perfect 5th up/down, or relative minor)
            idx = NOTES.index(base_key) if base_key in NOTES else 5
            shifts = [-5, -3, 0, 2, 5, 7]  # musically related intervals
            shift = rng.choice(shifts)
            return NOTES[(idx + shift) % 12]

        return base_key

    def _pick_scale(self, bp: SongBlueprint, mood, params: dict,
                    rng: random.Random) -> str:
        """Choose scale from blueprint, mood, or darkness level."""
        if bp.scale:
            return bp.scale

        darkness = params.get("darkness", 0.5)

        if darkness > 0.8:
            candidates = ["phrygian", "harmonic_minor", "minor"]
        elif darkness > 0.5:
            candidates = ["minor", "dorian", "harmonic_minor"]
        elif darkness > 0.3:
            candidates = ["minor", "dorian", "mixolydian"]
        else:
            candidates = ["major", "lydian", "mixolydian"]

        # Artistic variance
        if rng.random() < self.artistic_variance:
            return rng.choice(list(SCALE_INTERVALS.keys()))

        return rng.choice(candidates)

    def _pick_bpm(self, bp: SongBlueprint, params: dict,
                  rng: random.Random) -> int:
        """Choose BPM from blueprint, style, or energy."""
        if bp.bpm > 0:
            return bp.bpm

        style = bp.style.lower().replace(" ", "_")
        lo, hi = BPM_RANGES.get(style, (138, 152))

        # Energy shifts BPM: high energy → higher BPM
        energy = params.get("energy", 0.7)
        center = lo + (hi - lo) * energy

        # Artistic variance
        variance = self.artistic_variance * 6
        bpm = int(center + rng.gauss(0, variance))
        return max(lo, min(hi, bpm))

    # ───────────────────────────────────────────
    #  Step 5: Frequency table
    # ───────────────────────────────────────────

    def _build_freq_table(self, key: str, scale: str) -> dict[str, float]:
        """Build a frequency lookup for the chosen key.

        Returns dict like {"F1": 43.65, "Ab1": 51.91, ...}
        covering octaves 1–5 with proper note names.
        """
        root_idx = NOTES.index(key) if key in NOTES else 5
        intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["minor"])

        freq_table: dict[str, float] = {}
        for octave in range(1, 6):
            for interval in intervals:
                note_idx = (root_idx + interval) % 12
                note_name = NOTES[note_idx]
                full_name = f"{note_name}{octave}"
                if full_name in _FREQ_TABLE:
                    freq_table[full_name] = _FREQ_TABLE[full_name]

        return freq_table

    # ───────────────────────────────────────────
    #  Step 6: Arrangement
    # ───────────────────────────────────────────

    def _pick_arrangement(self, bp: SongBlueprint, params: dict,
                          rng: random.Random) -> tuple[list[ArrangementSection], int]:
        """Pick and customize arrangement archetype."""
        if bp.arrangement and bp.arrangement in ARRANGEMENT_ARCHETYPES:
            arch_name = bp.arrangement
        else:
            energy = params.get("energy", 0.7)
            complexity = params.get("complexity", 0.5)

            if complexity > 0.7 or energy > 0.85:
                candidates = ["double_drop", "standard", "progressive"]
            elif energy < 0.4:
                candidates = ["progressive", "extended_intro"]
            elif params.get("minimalism", 0) > 0.5:
                candidates = ["minimal"]
            else:
                candidates = ["standard", "double_drop"]

            arch_name = rng.choice(candidates)

        sections = []
        for s in ARRANGEMENT_ARCHETYPES[arch_name]:
            # Deep copy
            sec = ArrangementSection(
                name=s.name,
                bars=s.bars,
                energy=s.energy,
                elements=list(s.elements),
            )
            # Artistic bar variance (±2 bars, multiples of 2)
            if rng.random() < self.artistic_variance and sec.bars >= 8:
                delta = rng.choice([-2, 0, 0, 2])
                sec.bars = max(4, sec.bars + delta)
            sections.append(sec)

        total_bars = sum(s.bars for s in sections)
        return sections, total_bars

    # ───────────────────────────────────────────
    #  Step 7: Sub-DNA builders
    # ───────────────────────────────────────────

    def _art(self, base: float, rng: random.Random,
             lo: float = 0.0, hi: float = 1.0) -> float:
        """Apply artistic variance to a value."""
        v = base + rng.gauss(0, self.artistic_variance * 0.3)
        return max(lo, min(hi, v))

    def _build_drum_dna(self, params: dict, rng: random.Random) -> DrumDNA:
        """Derive drum personality from aggregated params."""
        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)
        metallic = params.get("metallic", 0.2)

        return DrumDNA(
            kick_pitch=self._art(38.0 + darkness * 15.0, rng, 35.0, 65.0),
            kick_fm_depth=self._art(2.0 + energy * 4.0, rng, 1.0, 8.0),
            kick_drive=self._art(0.3 + energy * 0.4, rng, 0.1, 0.9),
            kick_sub_weight=self._art(
                params.get("sub_weight", 0.6 + darkness * 0.3), rng, 0.3, 1.0),
            kick_attack=self._art(
                params.get("transient_attack", 2.0 + energy * 2.0), rng, 1.0, 5.0),
            snare_pitch=self._art(180.0 + (1 - darkness) * 100.0, rng, 150.0, 350.0),
            snare_noise_mix=self._art(0.3 + energy * 0.3, rng, 0.1, 0.8),
            snare_metallic=self._art(metallic * 0.5, rng, 0.0, 0.6),
            snare_compression=self._art(4.0 + energy * 6.0, rng, 2.0, 12.0),
            hat_frequency=self._art(6000 + (1 - darkness) * 4000, rng, 5000, 12000),
            hat_metallic=self._art(metallic * 0.4, rng, 0.0, 0.5),
            hat_brightness=self._art(0.8 + energy * 0.15, rng, 0.6, 1.0),
            clap_brightness=self._art(0.85 + energy * 0.1, rng, 0.7, 1.0),
            clap_reverb=self._art(0.1 + (1 - energy) * 0.15, rng, 0.05, 0.35),
            snare_ott=self._art(0.2 + energy * 0.25, rng, 0.1, 0.6),
            hat_density=rng.choice([16, 16, 16, 32]) if energy > 0.8 else 16,
        )

    def _build_bass_dna(self, params: dict, rng: random.Random) -> BassDNA:
        """Derive bass personality."""
        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)

        # Bass type selection based on aggregated params
        bass_type_str = params.get("bass_type", "")

        # Primary bass type
        if isinstance(bass_type_str, str) and bass_type_str:
            primary = bass_type_str
        elif energy > 0.85:
            primary = rng.choice(["dist_fm", "neuro", "sync"])
        elif darkness > 0.7:
            primary = rng.choice(["dist_fm", "growl", "neuro"])
        else:
            primary = rng.choice(["dist_fm", "acid", "sync"])

        # Secondary/tertiary
        all_types = ["dist_fm", "sync", "neuro", "acid", "growl", "formant"]
        remaining = [t for t in all_types if t != primary]
        rng.shuffle(remaining)
        secondary = remaining[0]
        tertiary = remaining[1]

        return BassDNA(
            primary_type=primary,
            secondary_type=secondary,
            tertiary_type=tertiary,
            fm_depth=self._art(
                params.get("fm_depth", 5.0 + energy * 4.0), rng, 2.0, 12.0),
            fm_feedback=self._art(0.2 + energy * 0.4, rng, 0.0, 0.7),
            distortion=self._art(
                params.get("distortion", 0.4 + energy * 0.5), rng, 0.1, 1.0),
            filter_cutoff=self._art(
                params.get("filter_cutoff", 0.5 + energy * 0.4), rng, 0.2, 1.0),
            acid_resonance=self._art(
                params.get("acid_resonance", 0.0), rng, 0.0, 1.0),
            growl_resampler=energy > 0.6,
            lfo_rate=self._art(
                params.get("lfo_rate", 2.0 + energy * 3.0), rng, 0.5, 10.0),
            lfo_depth=self._art(0.5 + energy * 0.35, rng, 0.2, 1.0),
            sub_weight=self._art(
                params.get("sub_weight", 0.7 + darkness * 0.2), rng, 0.5, 1.0),
            mid_drive=self._art(0.5 + energy * 0.45, rng, 0.2, 1.0),
            pitch_dive_semi=self._art(
                params.get("pitch_dive_range", 12.0), rng, 6.0, 36.0),
            wavefold_thresh=self._art(
                0.7 - energy * 0.3, rng, 0.3, 0.8),
            bitcrush_bits=int(self._art(
                params.get("bitcrush_depth", 0.0), rng, 0.0, 12.0)) if params.get("bitcrush_depth", 0) > 0 else 0,
            ott_amount=self._art(0.25 + energy * 0.25, rng, 0.15, 0.6),
            ring_mod_freq=self._art(
                params.get("metallic", 0.0) * 200.0, rng, 0.0, 300.0) if params.get("metallic", 0) > 0.5 else 0.0,
        )

    def _build_lead_dna(self, params: dict, rng: random.Random) -> LeadDNA:
        """Derive lead personality."""
        energy = params.get("energy", 0.7)
        brightness = params.get("brightness", 0.5)
        darkness = params.get("darkness", 0.5)

        use_ks = params.get("karplus_strong", 0) > 0
        use_additive = not use_ks or energy > 0.5

        rolloff_map = {
            (True, True): "sawtooth",     # bright + energetic
            (True, False): "triangle",    # bright + calm
            (False, True): "square",      # dark + energetic
            (False, False): "natural",    # dark + calm
        }
        rolloff = rolloff_map[(brightness > 0.5, energy > 0.5)]

        return LeadDNA(
            use_additive=use_additive,
            additive_partials=int(self._art(8 + energy * 10, rng, 4, 24)),
            additive_rolloff=rolloff,
            use_fm=energy > 0.4,
            fm_operators=2 if energy < 0.7 else 3,
            fm_depth=self._art(
                params.get("fm_depth", 3.0) * 0.5, rng, 1.0, 6.0),
            brightness=self._art(brightness if brightness else 0.5 + energy * 0.3, rng, 0.2, 1.0),
            reverb_decay=self._art(
                params.get("reverb_decay", 0.5), rng, 0.2, 2.0),
            shimmer=self._art(
                params.get("shimmer", 0.0), rng, 0.0, 1.0),
            supersaw_voices=int(self._art(5 + energy * 4, rng, 3, 11)),
            supersaw_detune=self._art(25.0 + energy * 20.0, rng, 15.0, 50.0),
            supersaw_cutoff=self._art(
                3500 + brightness * 4000 if brightness else 5500, rng, 2000, 8000),
            ott_amount=self._art(0.2 + energy * 0.2, rng, 0.1, 0.5),
        )

    def _build_atmosphere_dna(self, params: dict, rng: random.Random) -> AtmosphereDNA:
        """Derive atmosphere personality."""
        darkness = params.get("darkness", 0.5)
        energy = params.get("energy", 0.7)

        if darkness > 0.7:
            pad_type = "dark"
        elif darkness < 0.3:
            pad_type = "lush"
        else:
            pad_type = rng.choice(["dark", "lush"])

        return AtmosphereDNA(
            pad_type=pad_type,
            pad_attack=self._art(
                params.get("pad_attack", 1.5 + (1 - energy) * 2.5), rng, 0.5, 5.0),
            pad_brightness=self._art(0.2 + (1 - darkness) * 0.5, rng, 0.1, 0.8),
            reverb_decay=self._art(
                params.get("reverb_decay", 2.0 + (1 - energy) * 2.0), rng, 0.5, 5.0),
            stereo_width=self._art(
                params.get("stereo_width", 1.3 + (1 - energy) * 0.5), rng, 1.0, 2.0),
            shimmer=self._art(
                params.get("shimmer", 0.0), rng, 0.0, 1.0),
            granular_density=self._art(
                params.get("granular_density", 0.3), rng, 0.0, 0.9),
            drone_voices=max(3, min(12, int(5 + darkness * 5 + rng.gauss(0, 1)))),
            drone_movement=self._art(0.3 + energy * 0.3, rng, 0.1, 0.8),
            use_karplus_drone=params.get("karplus_strong", 0) > 0 or darkness > 0.7,
            noise_bed_type="brown" if darkness > 0.6 else "pink",
            noise_bed_level=self._art(0.1 + (1 - energy) * 0.1, rng, 0.05, 0.3),
        )

    def _build_fx_dna(self, params: dict, rng: random.Random) -> FxDNA:
        """Derive FX personality."""
        energy = params.get("energy", 0.7)

        return FxDNA(
            riser_intensity=self._art(0.5 + energy * 0.45, rng, 0.3, 1.0),
            impact_intensity=self._art(0.6 + energy * 0.35, rng, 0.4, 1.0),
            glitch_amount=self._art(
                params.get("glitch_amount", 0.0), rng, 0.0, 1.0),
            tape_degrade=self._art(
                params.get("tape_degrade", 0.0), rng, 0.0, 0.8),
            stutter_rate=self._art(
                params.get("stutter_rate", 16.0), rng, 4.0, 32.0),
            pitch_dive_range=self._art(
                params.get("pitch_dive_range", 12.0), rng, 6.0, 36.0),
            vocal_chop_distortion=self._art(0.2 + energy * 0.3, rng, 0.0, 0.7),
            beat_repeat_probability=self._art(0.15 + energy * 0.2, rng, 0.0, 0.5),
            riser_start_freq=self._art(100 + (1 - energy) * 100, rng, 50, 300),
            riser_end_freq=self._art(6000 + energy * 4000, rng, 4000, 12000),
            boom_decay=self._art(1.5 + energy * 1.0, rng, 1.0, 3.0),
        )

    def _build_mix_dna(self, params: dict, rng: random.Random) -> MixDNA:
        """Derive mix/master personality."""
        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)

        return MixDNA(
            target_lufs=self._art(-8.0 + (1 - energy) * 2.0, rng, -10.0, -6.0),
            stereo_width=self._art(
                params.get("stereo_width", 1.2 + energy * 0.3), rng, 1.0, 1.8),
            master_drive=self._art(0.3 + energy * 0.4, rng, 0.1, 0.8),
            eq_low_boost=self._art(2.0 + darkness * 3.0, rng, 0.0, 6.0),
            eq_high_boost=self._art(1.5 + (1 - darkness) * 2.5, rng, 0.0, 5.0),
            compression_ratio=self._art(2.5 + energy * 2.0, rng, 1.5, 6.0),
            sidechain_depth=self._art(0.5 + energy * 0.3, rng, 0.3, 0.9),
            ceiling_db=self._art(-0.3 + energy * 0.15, rng, -0.5, -0.1),
            eq_low_freq=self._art(60 + darkness * 20, rng, 50, 90),
            eq_high_freq=self._art(9000 + (1 - darkness) * 3000, rng, 7000, 13000),
            compression_threshold=self._art(-16 + energy * 4, rng, -20, -10),
            limiter_enabled=True,
        )

    # ───────────────────────────────────────────
    #  Bass rotation & chop vowels
    # ───────────────────────────────────────────

    def _pick_bass_rotation(self, bass: BassDNA, params: dict,
                            rng: random.Random) -> list[str]:
        """Order the bass types for drop rotation."""
        all_types = [
            bass.primary_type, bass.secondary_type, bass.tertiary_type,
            "fm_growl", "growl_wt", "formant", "acid",
        ]
        # Remove duplicates, keep order
        seen = set()
        unique = []
        for t in all_types:
            if t not in seen:
                seen.add(t)
                unique.append(t)

        # Artistic shuffle — slight reorder
        if rng.random() < self.artistic_variance:
            # Swap two random positions
            if len(unique) >= 3:
                i, j = rng.sample(range(len(unique)), 2)
                unique[i], unique[j] = unique[j], unique[i]

        return unique

    def _pick_chop_vowels(self, params: dict, rng: random.Random) -> list[str]:
        """Pick vocal chop vowel order."""
        all_vowels = ["ah", "oh", "ee", "oo"]
        darkness = params.get("darkness", 0.5)

        if darkness > 0.7:
            # Dark = more "oh" and "oo"
            return ["oh", "oo", "ah", "ee"]
        elif darkness < 0.3:
            # Bright = more "ee" and "ah"
            return ["ee", "ah", "oh", "oo"]
        else:
            rng.shuffle(all_vowels)
            return all_vowels

    # ───────────────────────────────────────────
    #  Tags & theme inference
    # ───────────────────────────────────────────

    def _build_tags(self, bp: SongBlueprint, mood_name: str,
                    params: dict) -> list[str]:
        """Generate descriptive tags."""
        tags = list(bp.tags)
        tags.append(bp.style)
        tags.append(mood_name.replace("+", " "))

        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)

        if energy > 0.85:
            tags.append("high_energy")
        elif energy < 0.35:
            tags.append("low_energy")

        if darkness > 0.7:
            tags.append("dark")
        elif darkness < 0.3:
            tags.append("bright")

        if params.get("metallic", 0) > 0.5:
            tags.append("metallic")
        if params.get("distortion", 0) > 0.7:
            tags.append("distorted")
        if params.get("reverb_decay", 0) > 2.5:
            tags.append("atmospheric")
        if params.get("glitch_amount", 0) > 0.4:
            tags.append("glitchy")

        # Deduplicate
        seen = set()
        unique_tags = []
        for t in tags:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_tags.append(t)

        return unique_tags

    def _infer_theme(self, atoms: list[dict]) -> str:
        """Infer a theme description from the aggregated atoms."""
        if not atoms:
            return "aggressive dubstep"

        params = self._aggregate_params(atoms)
        energy = params.get("energy", 0.7)
        darkness = params.get("darkness", 0.5)

        descriptors = []
        if darkness > 0.7:
            descriptors.append("dark")
        elif darkness < 0.3:
            descriptors.append("bright")

        if energy > 0.85:
            descriptors.append("aggressive")
        elif energy > 0.6:
            descriptors.append("driving")
        elif energy < 0.35:
            descriptors.append("atmospheric")
        else:
            descriptors.append("balanced")

        if params.get("metallic", 0) > 0.5:
            descriptors.append("metallic")
        if params.get("reverb_decay", 0) > 2.5:
            descriptors.append("spacious")
        if params.get("chaos", 0) > 0.5:
            descriptors.append("chaotic")
        if params.get("warmth", 0) > 0.6:
            descriptors.append("warm")
        if params.get("acid_resonance", 0) > 0.5:
            descriptors.append("acid")

        return " ".join(descriptors[:3]) if descriptors else "aggressive"


# ═══════════════════════════════════════════
#  Convenience Functions
# ═══════════════════════════════════════════

def forge_song_dna(
    name: str,
    style: str = "dubstep",
    theme: str = "",
    mood: str = "",
    sound_style: str = "",
    key: str = "",
    scale: str = "",
    bpm: int = 0,
    **kwargs,
) -> SongDNA:
    """One-liner: name → SongDNA.

    Example:
        dna = forge_song_dna("Hollow Point", style="dubstep")
        dna = forge_song_dna("Nebula Dream", mood="dreamy", style="melodic")
        dna = forge_song_dna("Clockwork Fury", sound_style="metallic heavy")
    """
    bp = SongBlueprint(
        name=name, style=style, theme=theme, mood=mood,
        sound_style=sound_style, key=key, scale=scale, bpm=bpm,
        **kwargs,
    )
    engine = VariationEngine(artistic_variance=0.15)
    return engine.forge_dna(bp)


def save_dna(dna: SongDNA, path: Optional[str] = None) -> str:
    """Save SongDNA to JSON file."""
    if path is None:
        safe_name = dna.name.lower().replace(" ", "_").replace("'", "")
        path = str(Path("output") / "songs" / f"{safe_name}_dna.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(dna.to_json())
    return path


def load_dna(path: str) -> SongDNA:
    """Load SongDNA from JSON file."""
    with open(path) as f:
        d = json.load(f)

    # Reconstruct arrangement sections
    arrangement = [ArrangementSection(**s) for s in d.pop("arrangement", [])]

    # Reconstruct sub-DNAs
    drums = DrumDNA(**d.pop("drums", {}))
    bass = BassDNA(**d.pop("bass", {}))
    lead = LeadDNA(**d.pop("lead", {}))
    atmosphere = AtmosphereDNA(**d.pop("atmosphere", {}))
    fx = FxDNA(**d.pop("fx", {}))
    mix = MixDNA(**d.pop("mix", {}))

    return SongDNA(
        arrangement=arrangement,
        drums=drums, bass=bass, lead=lead,
        atmosphere=atmosphere, fx=fx, mix=mix,
        **d,
    )


# ═══════════════════════════════════════════
#  CLI Demo
# ═══════════════════════════════════════════

import os

if __name__ == "__main__":
    import sys

    # Demo: generate DNA for a few Subtronics-inspired names
    demo_songs = [
        SongBlueprint("Hollow Point", style="dubstep"),
        SongBlueprint("Nebula Dream", style="melodic", mood="dreamy"),
        SongBlueprint("Clockwork Fury", style="riddim", sound_style="metallic heavy"),
        SongBlueprint("Venom Eclipse", style="dubstep", theme="dark aggression"),
        SongBlueprint("Crystal Storm", style="hybrid"),
        SongBlueprint("Acid Phantom", style="dubstep", sound_style="acid resonant"),
        SongBlueprint("Quantum Forge", style="experimental"),
    ]

    engine = VariationEngine(artistic_variance=0.15)

    for bp in demo_songs:
        dna = engine.forge_dna(bp)
        print(dna.summary())
        print()

        # Save
        path = save_dna(dna)
        print(f"  Saved: {path}\n")
