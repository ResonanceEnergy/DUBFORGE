"""
DUBFORGE Engine — Creative Vocal Mangler

Advanced vocal chopping and mangling beyond basic formant chops.
Takes synthesized vocal material and applies destructive creative processing:
glitch slicing, granular scatter, formant morphing, reverse builds, and
beat-synced stutter patterns.

Workflow order:
  Phase 1 Stage 4G → after vocal_chop.py generates raw chops.
  This module takes those chops and mangles them into usable production elements.
  Also usable in Phase 2 for transition FX.

Unlike vocal_chop.py (which synthesizes vowel sounds from scratch),
this module processes existing vocal audio with creative destruction.

Modes:
    glitch_slice    — micro-chop + random reorder + pitch randomise
    granular_vocal  — granular cloud from vocal source
    formant_morph   — sweep through vowel space over time
    reverse_build   — reverse reverb vocal sweep (transition FX)
    stutter_gate    — beat-synced gate + pitch staircase

Banks: 5 modes × 4 presets = 20 presets
"""

from __future__ import annotations
from typing import Any, Callable

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import fft, ifft, write_wav

_log = get_logger("dubforge.vocal_mangle")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VocalManglePreset:
    """Configuration for vocal mangling."""
    name: str
    mode: str  # glitch_slice | granular_vocal | formant_morph | reverse_build | stutter_gate
    duration_s: float = 2.0
    bpm: float = 150.0
    # Source generation
    source_vowel: str = "ah"
    source_freq: float = 220.0
    # Processing params
    slice_size_ms: float = 50.0
    pitch_range: float = 12.0  # semitones random range
    density: float = 0.7
    reverb_decay: float = 0.5
    gate_divisions: int = 16  # 16th notes per bar
    formant_speed: float = 1.0  # vowel sweep speed
    distortion: float = 0.0


@dataclass
class VocalMangleBank:
    name: str
    presets: list[VocalManglePreset] = field(default_factory=list)


@dataclass
class VocalMangleResult:
    name: str
    mode: str
    audio: np.ndarray


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE GENERATOR (formant-shaped vocal material)
# ═══════════════════════════════════════════════════════════════════════════

VOWEL_FORMANTS: dict[str, list[tuple[float, float]]] = {
    "ah": [(730, 160), (1090, 180), (2440, 220)],
    "oh": [(570, 140), (840, 160), (2410, 200)],
    "eh": [(530, 130), (1840, 190), (2480, 220)],
    "ee": [(270, 90), (2290, 200), (3010, 240)],
    "oo": [(300, 100), (870, 130), (2240, 190)],
}


def _generate_vocal_source(freq: float, duration_s: float, vowel: str = "ah",
                           sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate formant-shaped source material."""
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    # Saw-like source
    sig = np.zeros(n)
    for k in range(1, 20):
        if freq * k > sr / 2:
            break
        sig += ((-1) ** (k + 1)) * np.sin(2 * math.pi * freq * k * t) / k
    sig *= 2.0 / math.pi
    # Apply formant filter
    formants = VOWEL_FORMANTS.get(vowel, VOWEL_FORMANTS["ah"])
    spectrum = fft(sig)
    n_spec = len(spectrum)
    freqs_hz = np.fft.rfftfreq(n, d=1.0 / sr)
    response = np.ones(n_spec)
    for center, bw in formants:
        response += 3.0 * np.exp(-0.5 * ((freqs_hz - center) / max(bw, 1)) ** 2)
    spectrum *= response
    result = ifft(spectrum, n=n)
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak
    return result


def _normalize(sig: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(sig))
    return sig / peak * 0.95 if peak > 0 else sig


def _hann(n: int) -> np.ndarray:
    return 0.5 * (1 - np.cos(2 * np.pi * np.arange(n) / max(1, n - 1)))


# ═══════════════════════════════════════════════════════════════════════════
# MANGLING PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

def mangle_glitch_slice(source: np.ndarray, preset: VocalManglePreset,
                        sr: int = SAMPLE_RATE) -> VocalMangleResult:
    """
    Micro-chop vocal into tiny slices, randomly reorder and pitch-shift each.
    Creates glitchy, broken vocal textures.
    """
    n = len(source)
    slice_n = max(32, int(preset.slice_size_ms * sr / 1000))
    num_slices = n // slice_n
    if num_slices < 2:
        return VocalMangleResult(preset.name, "glitch_slice", source)

    slices = [source[i * slice_n:(i + 1) * slice_n] for i in range(num_slices)]
    rng = np.random.default_rng(42)
    window = _hann(slice_n)

    output = np.zeros(n)
    pos = 0
    for _ in range(num_slices):
        idx = rng.integers(0, num_slices)
        sl = slices[idx].copy() * window
        # Random pitch shift
        shift = rng.uniform(-preset.pitch_range, preset.pitch_range)
        ratio = 2.0 ** (shift / 12.0)
        new_len = max(2, int(slice_n / ratio))
        indices = np.linspace(0, slice_n - 1, new_len)
        resampled = np.interp(indices, np.arange(slice_n), sl)
        # Fit back
        if len(resampled) < slice_n:
            padded = np.zeros(slice_n)
            padded[:len(resampled)] = resampled
            resampled = padded
        else:
            resampled = resampled[:slice_n]
        # Random reverse
        if rng.random() > 0.6:
            resampled = resampled[::-1]
        end = min(n, pos + slice_n)
        output[pos:end] += resampled[:end - pos]
        pos += slice_n
        if pos >= n:
            break

    if preset.distortion > 0:
        output = np.tanh(output * (1 + preset.distortion * 5))
    return VocalMangleResult(preset.name, "glitch_slice", _normalize(output))


def mangle_granular_vocal(source: np.ndarray, preset: VocalManglePreset,
                          sr: int = SAMPLE_RATE) -> VocalMangleResult:
    """
    Scatter vocal into grain cloud with random read positions and pitch jitter.
    """
    grain_n = max(64, int(preset.slice_size_ms * sr / 1000))
    src_n = len(source)
    out_n = int(preset.duration_s * sr)
    output = np.zeros(out_n)
    rng = np.random.default_rng(42)
    window = _hann(grain_n)

    num_grains = max(8, int(preset.density * out_n / grain_n * 2))
    for _ in range(num_grains):
        read_pos = rng.integers(0, max(1, src_n - grain_n))
        write_pos = rng.integers(0, max(1, out_n - grain_n))
        grain = source[read_pos:read_pos + grain_n] * window
        # Pitch jitter
        shift = rng.uniform(-preset.pitch_range * 0.3, preset.pitch_range * 0.3)
        if abs(shift) > 0.5:
            ratio = 2.0 ** (shift / 12.0)
            new_len = max(2, int(grain_n / ratio))
            indices = np.linspace(0, grain_n - 1, new_len)
            grain = np.interp(indices, np.arange(grain_n), grain)
            if len(grain) < grain_n:
                padded = np.zeros(grain_n)
                padded[:len(grain)] = grain
                grain = padded
            else:
                grain = grain[:grain_n]
            grain *= window
        end = min(out_n, write_pos + grain_n)
        output[write_pos:end] += grain[:end - write_pos]

    return VocalMangleResult(preset.name, "granular_vocal", _normalize(output))


def mangle_formant_morph(source: np.ndarray, preset: VocalManglePreset,
                         sr: int = SAMPLE_RATE) -> VocalMangleResult:
    """
    Sweep through vowel formant space over time.
    Re-applies formant filter with time-varying center frequencies.
    """
    n = len(source)
    vowel_keys = list(VOWEL_FORMANTS.keys())
    num_segments = max(4, int(preset.formant_speed * 8))
    seg_len = n // num_segments
    output = np.zeros(n)
    freqs_hz = np.fft.rfftfreq(seg_len, d=1.0 / sr) if seg_len > 0 else np.array([0.0])

    for i in range(num_segments):
        start = i * seg_len
        end = min(n, start + seg_len)
        actual_len = end - start
        if actual_len < 2:
            continue
        seg = source[start:end].copy()
        # Interpolate between vowels
        progress = i / max(num_segments - 1, 1)
        vowel_pos = progress * (len(vowel_keys) - 1)
        v_idx = int(vowel_pos)
        v_frac = vowel_pos - v_idx
        f_a = VOWEL_FORMANTS[vowel_keys[min(v_idx, len(vowel_keys) - 1)]]
        f_b = VOWEL_FORMANTS[vowel_keys[min(v_idx + 1, len(vowel_keys) - 1)]]
        # Apply blended formant
        seg_freqs = np.fft.rfftfreq(actual_len, d=1.0 / sr)
        spectrum = np.fft.rfft(seg)
        response = np.ones(len(spectrum))
        for j in range(min(len(f_a), len(f_b))):
            ca, ba = f_a[j]
            cb, bb = f_b[j]
            center = ca * (1 - v_frac) + cb * v_frac
            bw = ba * (1 - v_frac) + bb * v_frac
            response += 3.0 * np.exp(-0.5 * ((seg_freqs - center) / max(bw, 1)) ** 2)
        spectrum *= response
        seg = np.fft.irfft(spectrum, n=actual_len)
        # Crossfade at boundaries
        fade = min(256, actual_len // 4)
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        output[start:end] += seg

    return VocalMangleResult(preset.name, "formant_morph", _normalize(output))


def mangle_reverse_build(source: np.ndarray, preset: VocalManglePreset,
                         sr: int = SAMPLE_RATE) -> VocalMangleResult:
    """
    Reverse reverb vocal sweep — classic transition FX technique.
    Process: reverse source → add reverb → reverse again → fade in.
    """
    n = len(source)
    # Reverse
    reversed_src = source[::-1].copy()
    # Apply reverb tail
    out = reversed_src.astype(np.float64)
    delays = [int(sr * d) for d in [0.029, 0.037, 0.047, 0.059]]
    fb = preset.reverb_decay * 0.6
    for delay in delays:
        if delay >= n:
            continue
        for i in range(delay, n):
            out[i] += fb * out[i - delay]
    out = _normalize(out)
    # Reverse back
    out = out[::-1]
    # Fade in
    fade_n = min(int(0.1 * sr), n // 4)
    out[:fade_n] *= np.linspace(0, 1, fade_n)
    return VocalMangleResult(preset.name, "reverse_build", _normalize(out))


def mangle_stutter_gate(source: np.ndarray, preset: VocalManglePreset,
                        sr: int = SAMPLE_RATE) -> VocalMangleResult:
    """
    Beat-synced gate pattern with pitch staircasing.
    Chops vocal into beat divisions and applies rhythmic gate + pitch ramp.
    """
    n = len(source)
    beat_s = 60.0 / preset.bpm
    division_s = beat_s / (preset.gate_divisions / 4)
    division_n = max(1, int(division_s * sr))

    output = np.zeros(n)
    num_divisions = n // division_n
    rng = np.random.default_rng(42)

    # Gate pattern (Fibonacci-inspired)
    gate_pattern = [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1]

    for i in range(num_divisions):
        start = i * division_n
        end = min(n, start + division_n)
        actual = end - start
        gate_on = gate_pattern[i % len(gate_pattern)]
        if not gate_on:
            continue
        chunk = source[start:end].copy()
        # Pitch staircase: rising pitch over time
        pitch_shift = (i / max(num_divisions, 1)) * preset.pitch_range - preset.pitch_range / 2
        if abs(pitch_shift) > 0.5:
            ratio = 2.0 ** (pitch_shift / 12.0)
            new_len = max(2, int(actual / ratio))
            indices = np.linspace(0, actual - 1, new_len)
            chunk = np.interp(indices, np.arange(actual), chunk)
            if len(chunk) < actual:
                padded = np.zeros(actual)
                padded[:len(chunk)] = chunk
                chunk = padded
            else:
                chunk = chunk[:actual]
        # Apply envelope per slice
        fade = min(64, actual // 4)
        if fade > 0:
            chunk[:fade] *= np.linspace(0, 1, fade)
            chunk[-fade:] *= np.linspace(1, 0, fade)
        output[start:end] = chunk

    return VocalMangleResult(preset.name, "stutter_gate", _normalize(output))


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

MANGLE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "glitch_slice": mangle_glitch_slice,
    "granular_vocal": mangle_granular_vocal,
    "formant_morph": mangle_formant_morph,
    "reverse_build": mangle_reverse_build,
    "stutter_gate": mangle_stutter_gate,
}


def run_vocal_mangle(preset: VocalManglePreset,
                     source: np.ndarray | None = None) -> VocalMangleResult:
    """Run vocal mangling from a preset."""
    if source is None:
        source = _generate_vocal_source(
            preset.source_freq, preset.duration_s, preset.source_vowel
        )
    fn = MANGLE_FUNCTIONS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown vocal mangle mode: {preset.mode}")
    return fn(source, preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def glitch_slice_bank() -> VocalMangleBank:
    return VocalMangleBank("glitch_slice", [
        VocalManglePreset("micro_glitch", "glitch_slice", slice_size_ms=20, pitch_range=12),
        VocalManglePreset("macro_glitch", "glitch_slice", slice_size_ms=100, pitch_range=7),
        VocalManglePreset("extreme_glitch", "glitch_slice", slice_size_ms=10, pitch_range=24, distortion=0.5),
        VocalManglePreset("subtle_glitch", "glitch_slice", slice_size_ms=50, pitch_range=3),
    ])


def granular_vocal_bank() -> VocalMangleBank:
    return VocalMangleBank("granular_vocal", [
        VocalManglePreset("dense_vocal_cloud", "granular_vocal", density=0.9, slice_size_ms=30),
        VocalManglePreset("sparse_vocal_cloud", "granular_vocal", density=0.3, slice_size_ms=80),
        VocalManglePreset("pitched_vocal_cloud", "granular_vocal", density=0.7, pitch_range=12),
        VocalManglePreset("long_vocal_cloud", "granular_vocal", density=0.5, duration_s=6.0),
    ])


def formant_morph_bank() -> VocalMangleBank:
    return VocalMangleBank("formant_morph", [
        VocalManglePreset("slow_morph", "formant_morph", formant_speed=0.5, duration_s=4.0),
        VocalManglePreset("fast_morph", "formant_morph", formant_speed=3.0),
        VocalManglePreset("sweep_morph", "formant_morph", formant_speed=1.5, source_vowel="ee"),
        VocalManglePreset("deep_morph", "formant_morph", formant_speed=1.0, source_freq=110),
    ])


def reverse_build_bank() -> VocalMangleBank:
    return VocalMangleBank("reverse_build", [
        VocalManglePreset("short_reverse", "reverse_build", duration_s=1.0, reverb_decay=0.4),
        VocalManglePreset("long_reverse", "reverse_build", duration_s=4.0, reverb_decay=0.7),
        VocalManglePreset("dark_reverse", "reverse_build", reverb_decay=0.8, source_freq=110),
        VocalManglePreset("bright_reverse", "reverse_build", reverb_decay=0.5, source_freq=440),
    ])


def stutter_gate_bank() -> VocalMangleBank:
    return VocalMangleBank("stutter_gate", [
        VocalManglePreset("tight_gate_16th", "stutter_gate", gate_divisions=16),
        VocalManglePreset("fast_gate_32nd", "stutter_gate", gate_divisions=32),
        VocalManglePreset("slow_gate_8th", "stutter_gate", gate_divisions=8),
        VocalManglePreset("pitched_gate", "stutter_gate", gate_divisions=16, pitch_range=24),
    ])


ALL_VOCAL_MANGLE_BANKS = [
    glitch_slice_bank, granular_vocal_bank, formant_morph_bank,
    reverse_build_bank, stutter_gate_bank,
]


def export_vocal_mangle(results: list[VocalMangleResult],
                        output_dir: str = "output/vocal_mangle") -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for r in results:
        path = out / f"{r.name}.wav"
        write_wav(str(path), r.audio, SAMPLE_RATE)
        paths.append(str(path))
    return paths


def write_vocal_mangle_manifest(results: list[VocalMangleResult],
                                output_dir: str = "output/analysis") -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "vocal_mangle_manifest.json"
    data = [{"name": r.name, "mode": r.mode, "samples": len(r.audio)} for r in results]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
