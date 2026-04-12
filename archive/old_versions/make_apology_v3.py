#!/usr/bin/env python3
"""DUBFORGE — "The Apology That Never Came" DNA Builder + Full Track Renderer.

Provides:
  - build_apology_dna()      → SongDNA-like object for the V8/V9 pipeline
  - kill_noise_sources()     → patch noise generators to reduce floor
  - set_female_vocal_chops() → configure vocal chop engine for female voice

This module bridges the V3-era monolithic renderer with the V8/V9
stem-based pipeline system.  The DNA object carries all musical parameters
that the pipeline scripts need (arrangement, key, BPM, sub-DNAs).

    Title:  The Apology That Never Came
    BPM:    140   (halftime dubstep)
    Key:    D minor
    Tuning: 432 Hz (A4 = 432 Hz)
    Layout: double_drop — 128 bars, 9 sections
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.variation_engine import (
    ArrangementSection,
    SongDNA,
    DrumDNA,
    BassDNA,
    LeadDNA,
    AtmosphereDNA,
    FxDNA,
    MixDNA,
    VariationEngine,
    SongBlueprint,
)

# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════

SAMPLE_RATE = 48000
BPM = 140
KEY = "D"
SCALE = "minor"
ROOT_FREQ = 36.71  # D1 at A4=432 Hz

# D minor frequency table (A4 = 432 Hz tuning)
KEY_FREQS = {
    "D1": 36.71, "E1": 41.20, "F1": 43.65, "G1": 49.00,
    "A1": 54.00, "Bb1": 57.27, "C2": 64.22,
    "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.00,
    "A2": 108.00, "Bb2": 114.54, "C3": 128.43,
    "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00,
    "A3": 216.00, "Bb3": 229.07, "C4": 256.87,
    "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 432.00, "Bb4": 458.14, "C5": 513.74,
}

# D minor scale MIDI notes (for vocal_tts targets etc.)
# D E F G A Bb C → MIDI 50 52 53 55 57 58 60 (octave 3)
MIDI_TABLE = {
    "D": [26, 38, 50, 62, 74],
    "E": [28, 40, 52, 64, 76],
    "F": [29, 41, 53, 65, 77],
    "G": [31, 43, 55, 67, 79],
    "A": [33, 45, 57, 69, 81],
    "Bb": [34, 46, 58, 70, 82],
    "C": [24, 36, 48, 60, 72],
}


# ═══════════════════════════════════════════════════════════════════
# Arrangement: double_drop — 128 bars, 9 sections
# ═══════════════════════════════════════════════════════════════════

_ARRANGEMENT = [
    ArrangementSection("intro", 16, 0.15,
                       ["drone", "pad", "texture"]),
    ArrangementSection("build", 8, 0.50,
                       ["kick", "riser", "snare_roll", "pad"]),
    ArrangementSection("drop1", 16, 1.00,
                       ["kick", "snare", "hats", "sub", "bass", "lead",
                        "noise_bed"]),
    ArrangementSection("drop1b", 16, 1.00,
                       ["kick", "snare", "hats", "sub", "bass_alt", "lead",
                        "chops", "noise_bed"]),
    ArrangementSection("break", 16, 0.25,
                       ["pad", "plucks", "drone", "texture"]),
    ArrangementSection("build2", 8, 0.60,
                       ["kick", "riser", "snare_roll", "swell"]),
    ArrangementSection("drop2", 16, 1.00,
                       ["kick", "snare", "hats", "sub", "bass", "lead",
                        "chops", "noise_bed"]),
    ArrangementSection("drop2b", 16, 1.00,
                       ["kick", "snare", "hats", "sub", "bass_alt", "lead",
                        "extra_bass", "chops", "noise_bed"]),
    ArrangementSection("outro", 16, 0.10,
                       ["pad_fade", "drone"]),
]

TOTAL_BARS = sum(s.bars for s in _ARRANGEMENT)  # 128


# ═══════════════════════════════════════════════════════════════════
# DNA Sub-specifications (tuned for "The Apology That Never Came")
# ═══════════════════════════════════════════════════════════════════

_DRUM_DNA = DrumDNA(
    kick_pitch=42.0,
    kick_fm_depth=4.0,
    kick_drive=0.60,
    kick_sub_weight=0.70,
    kick_attack=2.5,
    snare_pitch=220.0,
    snare_noise_mix=0.55,
    snare_metallic=0.25,
    snare_compression=10.0,
    hat_frequency=8500.0,
    hat_metallic=0.18,
    hat_brightness=0.90,
    clap_brightness=0.90,
    clap_reverb=0.18,
    snare_ott=0.30,
    hat_density=16,
)

_BASS_DNA = BassDNA(
    primary_type="dist_fm",
    secondary_type="sync",
    tertiary_type="neuro",
    fm_depth=5.0,
    fm_feedback=0.20,
    distortion=0.40,
    filter_cutoff=0.70,
    acid_resonance=0.0,
    growl_resampler=True,
    lfo_rate=2.5,
    lfo_depth=0.55,
    sub_weight=0.90,
    mid_drive=0.75,
    pitch_dive_semi=12.0,
    wavefold_thresh=0.0,
    bitcrush_bits=0,
    ott_amount=0.20,
    ring_mod_freq=0.0,
)

_LEAD_DNA = LeadDNA(
    use_additive=True,
    additive_partials=24,
    additive_rolloff="sawtooth",
    use_fm=True,
    fm_operators=4,
    fm_depth=3.5,
    brightness=0.72,
    reverb_decay=0.6,
    shimmer=0.15,
    supersaw_voices=7,
    supersaw_detune=30.0,
    supersaw_cutoff=6000.0,
    ott_amount=0.25,
    phrase_length=4,
    chord_progression=[0, 5, 2, 4],  # i-VI-III-VII in minor
)

_ATMOS_DNA = AtmosphereDNA(
    pad_type="dark",
    pad_attack=2.5,
    pad_brightness=0.28,
    reverb_decay=3.5,
    stereo_width=1.4,
    shimmer=0.12,
    granular_density=0.0,
    drone_voices=7,
    drone_movement=0.50,
    use_karplus_drone=False,
    noise_bed_type="pink",
    noise_bed_level=0.12,
)

_FX_DNA = FxDNA(
    riser_intensity=0.85,
    impact_intensity=0.90,
    glitch_amount=0.0,
    tape_degrade=0.0,
    stutter_rate=16.0,
    pitch_dive_range=12.0,
    vocal_chop_distortion=0.30,
    beat_repeat_probability=0.20,
    riser_start_freq=150.0,
    riser_end_freq=8000.0,
    boom_decay=2.0,
)

_MIX_DNA = MixDNA(
    target_lufs=-9.0,
    stereo_width=1.0,
    master_drive=0.30,
    eq_low_boost=1.0,
    eq_high_boost=1.3,
    compression_ratio=3.0,
    sidechain_depth=0.80,
    ceiling_db=-0.3,
    eq_low_freq=80.0,
    eq_high_freq=8000.0,
    compression_threshold=-12.0,
    limiter_enabled=True,
)


# ═══════════════════════════════════════════════════════════════════
# ApologyDNA — wraps SongDNA with .title alias
# ═══════════════════════════════════════════════════════════════════

class ApologyDNA(SongDNA):
    """SongDNA subclass that adds a .title property (v9 scripts use dna.title)."""

    @property
    def title(self) -> str:
        return self.name


def build_apology_dna() -> ApologyDNA:
    """Build the deterministic DNA for 'The Apology That Never Came'.

    Returns an ApologyDNA with all sub-specifications locked in.
    Called by every V8/V9 pipeline script.
    """
    dna = ApologyDNA(
        name="The Apology That Never Came",
        style="dubstep",
        theme="melancholy defiance — the moment you stop waiting for an apology "
              "that will never come and find your own freedom",
        mood_name="melancholy_epic",
        tags=["dubstep", "halftime", "emotional", "heavy", "vocal",
              "subtronics", "riddim", "melodic"],
        seed=0xDEAD_FACE,
        key=KEY,
        scale=SCALE,
        bpm=BPM,
        root_freq=ROOT_FREQ,
        freq_table=dict(KEY_FREQS),
        arrangement=list(_ARRANGEMENT),
        total_bars=TOTAL_BARS,
        drums=_DRUM_DNA,
        bass=_BASS_DNA,
        lead=_LEAD_DNA,
        atmosphere=_ATMOS_DNA,
        fx=_FX_DNA,
        mix=_MIX_DNA,
        bass_rotation=["dist_fm", "sync", "neuro", "acid", "growl",
                       "formant", "fm_growl"],
        chop_vowels=["ah", "oh", "ee", "oo"],
        notes="V9 pipeline: harmonized singing, double-tracked vocals, "
              "per-section dynamics",
    )
    return dna


# ═══════════════════════════════════════════════════════════════════
# Noise / vocal helpers
# ═══════════════════════════════════════════════════════════════════

def kill_noise_sources():
    """Patch engine noise generators to reduce noise floor.

    Disables mastering dither for production renders,
    gates noise beds, and caps riser noise levels.
    """
    try:
        from engine import mastering_chain
        if hasattr(mastering_chain, "DITHER_ENABLED"):
            mastering_chain.DITHER_ENABLED = False  # type: ignore[attr-defined]
    except ImportError:
        pass

    try:
        from engine import noise_generator
        if hasattr(noise_generator, "DEFAULT_GATE_DB"):
            noise_generator.DEFAULT_GATE_DB = -55.0  # type: ignore[attr-defined]
    except ImportError:
        pass

    try:
        from engine import riser_synth
        if hasattr(riser_synth, "MAX_NOISE_GAIN"):
            riser_synth.MAX_NOISE_GAIN = 0.15  # type: ignore[attr-defined]
    except ImportError:
        pass


def set_female_vocal_chops():
    """Configure the vocal chop engine for female voice samples.

    Sets the vocal chop pitch range, formant preservation, and
    selects female-range vowel formants.
    """
    try:
        from engine import vocal_chop
        if hasattr(vocal_chop, "PITCH_RANGE"):
            vocal_chop.PITCH_RANGE = (55, 75)  # MIDI range: G2–D#4  # type: ignore[attr-defined]
        if hasattr(vocal_chop, "FORMANT_PRESERVE"):
            vocal_chop.FORMANT_PRESERVE = True  # type: ignore[attr-defined]
        if hasattr(vocal_chop, "VOICE_TYPE"):
            vocal_chop.VOICE_TYPE = "female"  # type: ignore[attr-defined]
    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════════════
# CLI — standalone render (legacy, for quick testing)
# ═══════════════════════════════════════════════════════════════════

def main():
    """Quick CLI: build DNA and print summary."""
    parser = argparse.ArgumentParser(description="DUBFORGE — Apology DNA builder")
    parser.add_argument("--summary", action="store_true", help="Print DNA summary")
    args = parser.parse_args()

    dna = build_apology_dna()
    kill_noise_sources()
    set_female_vocal_chops()

    if args.summary or True:
        print(dna.summary())
        print(f"\n  .title = {dna.title}")
        print(f"  Sections: {len(dna.arrangement)}")
        for s in dna.arrangement:
            print(f"    {s.name:10s}: {s.bars:3d} bars, "
                  f"energy={s.energy:.2f}, elements={s.elements}")


if __name__ == "__main__":
    main()
