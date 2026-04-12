"""
DUBFORGE Engine — Guitar-Synth Hybrid Layer

Combines Karplus-Strong physical modelling (guitar-like plucks/strums)
with supersaw/FM synthesis to create hybrid textures used in melodic
dubstep breakdowns and ambient sections.

Workflow order:
  Phase 1 Stage 4G (SYNTH FACTORY) → sketch_guitar_hybrid().
  Creates layered output: guitar body + synth shimmer + optional distortion.

Hybrid modes:
    pluck_pad       — KS pluck + evolving pad layer
    strum_supersaw  — KS multi-string strum + supersaw swell
    harmonic_bell   — KS harmonic overtones + FM bell tones
    power_chord     — KS power chord stack + distorted synth
    ambient_string  — KS long decay + reverb + granular shimmer

Banks: 5 modes × 4 presets = 20 presets
"""

from __future__ import annotations

import json
from typing import Any, Callable
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI, FIBONACCI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import write_wav

_log = get_logger("dubforge.guitar_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GuitarSynthPreset:
    """Configuration for guitar-synth hybrid."""
    name: str
    mode: str  # pluck_pad | strum_supersaw | harmonic_bell | power_chord | ambient_string
    frequency: float = 110.0
    duration_s: float = 3.0
    # Guitar layer
    damping: float = 0.5  # string damping (0=bright, 1=dark)
    pluck_position: float = 0.5
    feedback: float = 0.998
    num_strings: int = 1  # for strum modes
    # Synth layer
    synth_mix: float = 0.4  # 0=all guitar, 1=all synth
    synth_detune: float = 0.1  # detune cents for unison
    synth_voices: int = 5  # unison voices
    fm_ratio: float = PHI
    fm_depth: float = 1.0
    # Processing
    drive: float = 0.0
    reverb: float = 0.3
    brightness: float = 0.6


@dataclass
class GuitarSynthBank:
    name: str
    presets: list[GuitarSynthPreset] = field(default_factory=list)


@dataclass
class GuitarSynthResult:
    name: str
    mode: str
    audio: np.ndarray
    guitar_layer: np.ndarray
    synth_layer: np.ndarray


# ═══════════════════════════════════════════════════════════════════════════
# GUITAR LAYER — Karplus-Strong
# ═══════════════════════════════════════════════════════════════════════════

def _karplus_strong(freq: float, duration_s: float, damping: float = 0.5,
                    pluck_pos: float = 0.5, feedback: float = 0.998,
                    brightness: float = 0.6, sr: int = SAMPLE_RATE,
                    seed: int = 42) -> np.ndarray:
    """Single Karplus-Strong string synthesis."""
    rng = random.Random(seed)
    n_samples = int(duration_s * sr)
    period = max(2, int(sr / max(20, min(freq, sr / 2))))

    # Initialize delay line with filtered noise burst
    delay_line = [0.0] * period
    for i in range(period):
        delay_line[i] = rng.uniform(-1, 1)
    # Pluck position filter: zero at pluck point
    pluck_idx = max(1, int(pluck_pos * period))
    for i in range(period):
        if i % pluck_idx == 0:
            delay_line[i] *= 0.5

    output = np.zeros(n_samples)
    idx = 0
    for i in range(n_samples):
        output[i] = delay_line[idx]
        next_idx = (idx + 1) % period
        # Low-pass average with damping
        blend = 0.5 + damping * 0.3
        new_val = blend * delay_line[idx] + (1 - blend) * delay_line[next_idx]
        new_val *= feedback
        # Brightness: mix in original for attack
        if i < period * 2 and brightness > 0.5:
            new_val = new_val * 0.8 + delay_line[idx] * 0.2
        delay_line[idx] = new_val
        idx = next_idx

    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak
    return output


def _strum_chord(freqs: list[float], duration_s: float, preset: GuitarSynthPreset,
                 sr: int = SAMPLE_RATE) -> np.ndarray:
    """Strum multiple strings with staggered onset."""
    n = int(duration_s * sr)
    output = np.zeros(n)
    strum_delay = int(0.02 * sr)  # 20ms between strings

    for i, freq in enumerate(freqs):
        string = _karplus_strong(
            freq, duration_s, preset.damping, preset.pluck_position,
            preset.feedback, preset.brightness, sr, seed=42 + i
        )
        onset = i * strum_delay
        end = min(n, onset + len(string))
        output[onset:end] += string[:end - onset]

    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak
    return output


# ═══════════════════════════════════════════════════════════════════════════
# SYNTH LAYERS
# ═══════════════════════════════════════════════════════════════════════════

def _supersaw_layer(freq: float, duration_s: float, detune: float = 0.1,
                    voices: int = 5, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Supersaw unison layer."""
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    output = np.zeros(n)
    for v in range(voices):
        offset = (v - voices // 2) * detune
        f = freq * (2 ** (offset / 1200))
        # Band-limited saw
        sig = np.zeros(n)
        for k in range(1, 12):
            if f * k > sr / 2:
                break
            sig += ((-1) ** (k + 1)) * np.sin(2 * math.pi * f * k * t) / k
        sig *= 2.0 / math.pi
        output += sig / voices
    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak
    return output


def _fm_bell_layer(freq: float, duration_s: float, fm_ratio: float = PHI,
                   fm_depth: float = 1.0, sr: int = SAMPLE_RATE) -> np.ndarray:
    """FM bell/metallic tone."""
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    # FM modulator
    mod = fm_depth * np.sin(2 * math.pi * freq * fm_ratio * t)
    # FM carrier
    sig = np.sin(2 * math.pi * freq * t + mod)
    # Bell envelope: fast attack, medium decay
    env = np.exp(-t * 3.0)
    sig *= env
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig /= peak
    return sig


def _pad_layer(freq: float, duration_s: float,
               sr: int = SAMPLE_RATE) -> np.ndarray:
    """Slow-evolving pad layer."""
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    # Soft harmonics with phi-spaced detuning
    for k in range(1, 6):
        detune = 1 + 0.002 * k * PHI
        sig += np.sin(2 * math.pi * freq * k * detune * t) / (k ** 1.5)
    # Slow attack envelope
    env = np.ones(n)
    attack_n = min(int(0.5 * sr), n // 2)
    release_n = min(int(1.0 * sr), n // 2)
    env[:attack_n] = np.linspace(0, 1, attack_n)
    env[-release_n:] = np.linspace(1, 0, release_n)
    sig *= env
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig /= peak
    return sig


# ═══════════════════════════════════════════════════════════════════════════
# PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def _apply_drive(sig: np.ndarray, drive: float) -> np.ndarray:
    if drive <= 0:
        return sig
    gain = 1.0 + drive * 6.0
    return np.tanh(sig * gain)


def _simple_reverb(sig: np.ndarray, amount: float,
                   sr: int = SAMPLE_RATE) -> np.ndarray:
    if amount <= 0:
        return sig
    n = len(sig)
    out = sig.copy().astype(np.float64)
    delays = [int(sr * d) for d in [0.023, 0.029, 0.037, 0.041]]
    for delay in delays:
        if delay >= n:
            continue
        fb = amount * 0.4
        for i in range(delay, n):
            out[i] += fb * out[i - delay]
    peak = np.max(np.abs(out))
    if peak > 0:
        out /= peak
    return out


def _normalize(sig: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(sig))
    return sig / peak * 0.95 if peak > 0 else sig


# ═══════════════════════════════════════════════════════════════════════════
# HYBRID SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synth_pluck_pad(preset: GuitarSynthPreset) -> GuitarSynthResult:
    """KS pluck + evolving pad layer."""
    guitar = _karplus_strong(preset.frequency, preset.duration_s,
                             preset.damping, preset.pluck_position,
                             preset.feedback, preset.brightness)
    synth = _pad_layer(preset.frequency, preset.duration_s)
    mix = guitar * (1 - preset.synth_mix) + synth * preset.synth_mix
    mix = _apply_drive(mix, preset.drive)
    mix = _simple_reverb(mix, preset.reverb)
    return GuitarSynthResult(preset.name, "pluck_pad", _normalize(mix), guitar, synth)


def synth_strum_supersaw(preset: GuitarSynthPreset) -> GuitarSynthResult:
    """KS multi-string strum + supersaw swell."""
    # Build chord frequencies (root, 5th, octave)
    root = preset.frequency
    freqs = [root, root * 3/2, root * 2][:preset.num_strings]
    guitar = _strum_chord(freqs, preset.duration_s, preset)
    synth = _supersaw_layer(preset.frequency, preset.duration_s,
                            preset.synth_detune, preset.synth_voices)
    mix = guitar * (1 - preset.synth_mix) + synth * preset.synth_mix
    mix = _apply_drive(mix, preset.drive)
    mix = _simple_reverb(mix, preset.reverb)
    return GuitarSynthResult(preset.name, "strum_supersaw", _normalize(mix), guitar, synth)


def synth_harmonic_bell(preset: GuitarSynthPreset) -> GuitarSynthResult:
    """KS harmonic overtones + FM bell tones."""
    guitar = _karplus_strong(preset.frequency, preset.duration_s,
                             damping=0.2, pluck_pos=0.3,
                             feedback=preset.feedback, brightness=0.9)
    synth = _fm_bell_layer(preset.frequency, preset.duration_s,
                           preset.fm_ratio, preset.fm_depth)
    mix = guitar * (1 - preset.synth_mix) + synth * preset.synth_mix
    mix = _simple_reverb(mix, preset.reverb)
    return GuitarSynthResult(preset.name, "harmonic_bell", _normalize(mix), guitar, synth)


def synth_power_chord(preset: GuitarSynthPreset) -> GuitarSynthResult:
    """KS power chord stack + distorted synth."""
    root = preset.frequency
    freqs = [root, root * 3/2, root * 2, root * 3]
    guitar = _strum_chord(freqs, preset.duration_s, preset)
    synth = _supersaw_layer(preset.frequency, preset.duration_s,
                            preset.synth_detune * 3, 7)
    mix = guitar * (1 - preset.synth_mix) + synth * preset.synth_mix
    mix = _apply_drive(mix, max(preset.drive, 0.5))
    mix = _simple_reverb(mix, preset.reverb * 0.5)
    return GuitarSynthResult(preset.name, "power_chord", _normalize(mix), guitar, synth)


def synth_ambient_string(preset: GuitarSynthPreset) -> GuitarSynthResult:
    """KS long decay + reverb + pad shimmer."""
    guitar = _karplus_strong(preset.frequency, preset.duration_s,
                             damping=0.8, feedback=0.9997, brightness=0.3)
    synth = _pad_layer(preset.frequency, preset.duration_s)
    mix = guitar * (1 - preset.synth_mix) + synth * preset.synth_mix
    mix = _simple_reverb(mix, max(preset.reverb, 0.6))
    return GuitarSynthResult(preset.name, "ambient_string", _normalize(mix), guitar, synth)


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

HYBRID_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "pluck_pad": synth_pluck_pad,
    "strum_supersaw": synth_strum_supersaw,
    "harmonic_bell": synth_harmonic_bell,
    "power_chord": synth_power_chord,
    "ambient_string": synth_ambient_string,
}


def run_guitar_synth(preset: GuitarSynthPreset) -> GuitarSynthResult:
    fn = HYBRID_FUNCTIONS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown guitar-synth mode: {preset.mode}")
    return fn(preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def pluck_pad_bank() -> GuitarSynthBank:
    return GuitarSynthBank("pluck_pad", [
        GuitarSynthPreset("warm_pluck_pad", "pluck_pad", frequency=130.81, synth_mix=0.3, reverb=0.4),
        GuitarSynthPreset("bright_pluck_pad", "pluck_pad", frequency=220, synth_mix=0.5, brightness=0.8),
        GuitarSynthPreset("dark_pluck_pad", "pluck_pad", frequency=82.41, damping=0.7, synth_mix=0.6),
        GuitarSynthPreset("airy_pluck_pad", "pluck_pad", frequency=164.81, synth_mix=0.7, reverb=0.7),
    ])


def strum_supersaw_bank() -> GuitarSynthBank:
    return GuitarSynthBank("strum_supersaw", [
        GuitarSynthPreset("gentle_strum", "strum_supersaw", num_strings=3, synth_mix=0.3),
        GuitarSynthPreset("heavy_strum", "strum_supersaw", num_strings=3, synth_mix=0.5, drive=0.4),
        GuitarSynthPreset("wide_strum", "strum_supersaw", num_strings=3, synth_mix=0.4, synth_detune=0.3),
        GuitarSynthPreset("epic_strum", "strum_supersaw", num_strings=3, synth_mix=0.6, synth_voices=7),
    ])


def harmonic_bell_bank() -> GuitarSynthBank:
    return GuitarSynthBank("harmonic_bell", [
        GuitarSynthPreset("crystal_bell", "harmonic_bell", frequency=440, synth_mix=0.5, fm_depth=2.0),
        GuitarSynthPreset("dark_bell", "harmonic_bell", frequency=220, synth_mix=0.4, fm_depth=0.5),
        GuitarSynthPreset("phi_bell", "harmonic_bell", frequency=432, synth_mix=0.6, fm_ratio=PHI),
        GuitarSynthPreset("deep_bell", "harmonic_bell", frequency=110, synth_mix=0.3, fm_depth=3.0),
    ])


def power_chord_bank() -> GuitarSynthBank:
    return GuitarSynthBank("power_chord", [
        GuitarSynthPreset("drop_d", "power_chord", frequency=73.42, drive=0.7, synth_mix=0.4),
        GuitarSynthPreset("e_power", "power_chord", frequency=82.41, drive=0.6, synth_mix=0.5),
        GuitarSynthPreset("a_power", "power_chord", frequency=110, drive=0.8, synth_mix=0.3),
        GuitarSynthPreset("heavy_power", "power_chord", frequency=65.41, drive=1.0, synth_mix=0.6),
    ])


def ambient_string_bank() -> GuitarSynthBank:
    return GuitarSynthBank("ambient_string", [
        GuitarSynthPreset("ethereal_string", "ambient_string", frequency=220, reverb=0.8, synth_mix=0.5),
        GuitarSynthPreset("deep_string", "ambient_string", frequency=82.41, reverb=0.7, synth_mix=0.6),
        GuitarSynthPreset("shimmer_string", "ambient_string", frequency=330, reverb=0.9, synth_mix=0.7),
        GuitarSynthPreset("dark_string", "ambient_string", frequency=55, reverb=0.6, synth_mix=0.4, duration_s=6.0),
    ])


ALL_GUITAR_SYNTH_BANKS = [
    pluck_pad_bank, strum_supersaw_bank, harmonic_bell_bank,
    power_chord_bank, ambient_string_bank,
]


def export_guitar_synth(results: list[GuitarSynthResult],
                        output_dir: str = "output/guitar_synth") -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for r in results:
        path = out / f"{r.name}.wav"
        write_wav(str(path), r.audio, SAMPLE_RATE)
        paths.append(str(path))
    return paths


def write_guitar_synth_manifest(results: list[GuitarSynthResult],
                                output_dir: str = "output/analysis") -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "guitar_synth_manifest.json"
    data = [{"name": r.name, "mode": r.mode, "samples": len(r.audio)} for r in results]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
