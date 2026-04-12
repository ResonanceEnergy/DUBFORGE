"""
DUBFORGE Engine — Live Resampling Feedback Loop

Iterative render → process → render pipeline for evolving sound design.
Each pass bounces audio, applies FX (distortion, reverb tail, pitch shift,
formant, spectral freeze), then feeds back into the next render cycle.

Workflow order in pipeline:
  Phase 1 Stage 4 (SYNTH FACTORY) → after initial synth sketch, before ALS build.
  Takes raw synth audio and evolves it through N resampling passes.

Resampling modes:
    bass_mangle    — iterative distortion + pitch dive + formant cycling
    whirlpool      — process → bounce → reverse → repeat (dreamy atmospheres)
    stutter_stack  — chop into grains → stutter → layer → bounce
    spectral_freeze — FFT freeze frame → evolve partials → bounce
    master_resample — full mix → reverse snippet → layer as transition FX

Based on:
  - edmprod.com resampling techniques (7 methods)
  - Subtronics/UBUR resampling chains (3 passes max)
  - ill.Gates Mudpie technique (chaos → chop → extract → resample)

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

_log = get_logger("dubforge.resample_feedback")

MAX_PASSES = 5  # safety limit to prevent infinite feedback


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ResamplePreset:
    """Configuration for a resampling feedback pass."""
    name: str
    mode: str  # bass_mangle | whirlpool | stutter_stack | spectral_freeze | master_resample
    passes: int = 3
    duration_s: float = 2.0
    frequency: float = 55.0
    drive: float = 0.618  # distortion amount per pass
    pitch_shift_semitones: float = -12.0  # per-pass pitch shift
    reverb_decay: float = 0.4
    formant_vowel: str = "A"
    grain_size_ms: float = 30.0
    freeze_position: float = 0.5  # 0-1 position for spectral freeze
    feedback_amount: float = 0.7  # how much of previous pass feeds forward
    brightness: float = 0.6


@dataclass
class ResampleBank:
    """Collection of resample presets."""
    name: str
    presets: list[ResamplePreset] = field(default_factory=list)


@dataclass
class ResampleResult:
    """Output of a resampling chain."""
    name: str
    passes_completed: int
    audio: np.ndarray
    pass_snapshots: list[np.ndarray] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(sig: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(sig))
    if peak > 0:
        return sig / peak * 0.95
    return sig


def _tanh_drive(sig: np.ndarray, drive: float) -> np.ndarray:
    """Soft-clip distortion with variable drive."""
    gain = 1.0 + drive * 8.0
    return np.tanh(sig * gain)


def _pitch_shift_fft(sig: np.ndarray, semitones: float) -> np.ndarray:
    """Simple FFT-based pitch shift."""
    if abs(semitones) < 0.01:
        return sig
    ratio = 2.0 ** (semitones / 12.0)
    spectrum = fft(sig)
    n = len(spectrum)
    shifted = np.zeros_like(spectrum)
    for i in range(n):
        new_idx = int(i * ratio)
        if 0 <= new_idx < n:
            shifted[new_idx] += spectrum[i]
    result = ifft(shifted, n=len(sig))
    return _normalize(result)


def _apply_reverb_tail(sig: np.ndarray, decay: float,
                       sr: int = SAMPLE_RATE) -> np.ndarray:
    """Simple algorithmic reverb via comb + allpass feedback."""
    if decay <= 0:
        return sig
    n = len(sig)
    out = np.copy(sig).astype(np.float64)
    # 4 comb filters at phi-ratio delays
    delays = [int(sr * d) for d in [0.029, 0.029 * PHI, 0.037, 0.037 * PHI]]
    for delay in delays:
        if delay >= n:
            continue
        fb = decay * 0.7
        for i in range(delay, n):
            out[i] += fb * out[i - delay]
    return _normalize(out)


def _reverse(sig: np.ndarray) -> np.ndarray:
    return sig[::-1].copy()


def _formant_shape(sig: np.ndarray, vowel: str) -> np.ndarray:
    """Simple formant filter."""
    formants = {
        "A": [730, 1090, 2440],
        "E": [660, 1720, 2410],
        "I": [390, 1990, 2550],
        "O": [570, 840, 2410],
        "U": [440, 1020, 2240],
    }
    centers = formants.get(vowel, formants["A"])
    spectrum = fft(sig)
    n = len(spectrum)
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / SAMPLE_RATE)
    response = np.ones(n)
    for c in centers:
        bw = c * 0.15
        response += 2.0 * np.exp(-0.5 * ((freqs - c) / bw) ** 2)
    spectrum *= response
    result = ifft(spectrum, n=len(sig))
    return _normalize(result)


def _spectral_freeze(sig: np.ndarray, position: float,
                     frame_size: int = 4096) -> np.ndarray:
    """Freeze a spectral frame and sustain it."""
    n = len(sig)
    start = int(position * max(n - frame_size, 1))
    frame = sig[start:start + frame_size]
    if len(frame) < frame_size:
        frame = np.pad(frame, (0, frame_size - len(frame)))
    frozen_spec = fft(frame)
    # Repeat the frozen frame across the full duration
    out = np.zeros(n)
    pos = 0
    window = 0.5 * (1 - np.cos(2 * np.pi * np.arange(frame_size) / max(1, frame_size - 1)))
    hop = frame_size // 2
    while pos < n:
        chunk = ifft(frozen_spec, n=frame_size) * window
        end = min(n, pos + frame_size)
        out[pos:end] += chunk[:end - pos]
        pos += hop
    return _normalize(out)


def _stutter_chop(sig: np.ndarray, grain_ms: float,
                  sr: int = SAMPLE_RATE) -> np.ndarray:
    """Chop into grains, shuffle, and re-layer with stutter."""
    grain_n = max(64, int(grain_ms * sr / 1000))
    n = len(sig)
    num_grains = n // grain_n
    if num_grains < 2:
        return sig
    grains = [sig[i * grain_n:(i + 1) * grain_n] for i in range(num_grains)]
    rng = np.random.default_rng(42)
    window = 0.5 * (1 - np.cos(2 * np.pi * np.arange(grain_n) / max(1, grain_n - 1)))
    out = np.zeros(n)
    pos = 0
    for _ in range(num_grains):
        idx = rng.integers(0, num_grains)
        grain = grains[idx] * window
        # Random stutter repeat
        repeats = rng.choice([1, 1, 2, 3])
        for _ in range(repeats):
            if pos + grain_n > n:
                break
            out[pos:pos + grain_n] += grain
            pos += grain_n // repeats if repeats > 1 else grain_n
        if pos >= n:
            break
    return _normalize(out)


# ═══════════════════════════════════════════════════════════════════════════
# GENERATE SOURCE
# ═══════════════════════════════════════════════════════════════════════════

def _generate_source(preset: ResamplePreset,
                     sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate initial source waveform."""
    n = int(preset.duration_s * sr)
    t = np.arange(n) / sr
    # Multi-harmonic saw-like source
    sig = np.zeros(n)
    for k in range(1, 16):
        if preset.frequency * k > sr / 2:
            break
        sig += ((-1) ** (k + 1)) * np.sin(2 * math.pi * preset.frequency * k * t) / k
    sig *= 2.0 / math.pi
    return _normalize(sig)


# ═══════════════════════════════════════════════════════════════════════════
# RESAMPLING PIPELINES
# ═══════════════════════════════════════════════════════════════════════════

def resample_bass_mangle(preset: ResamplePreset,
                         source: np.ndarray | None = None) -> ResampleResult:
    """
    Bass mangle: iterative distortion + pitch dive + formant cycling.
    Each pass: drive → pitch shift → formant → normalize → feed back.
    """
    sig = source if source is not None else _generate_source(preset)
    snapshots: list[np.ndarray] = [sig.copy()]
    vowels = ["A", "E", "I", "O", "U"]
    passes = min(preset.passes, MAX_PASSES)

    for i in range(passes):
        progress = i / max(passes - 1, 1)
        # Escalating drive per pass
        drive = preset.drive * (1 + progress * PHI)
        sig = _tanh_drive(sig, drive)
        # Progressive pitch dive
        shift = preset.pitch_shift_semitones * progress
        sig = _pitch_shift_fft(sig, shift)
        # Cycle through vowel formants
        vowel = vowels[i % len(vowels)]
        sig = _formant_shape(sig, vowel)
        # Feedback blend with previous
        if i > 0 and len(snapshots) > 0:
            blend = preset.feedback_amount * (1 - progress * 0.3)
            prev = snapshots[-1]
            min_len = min(len(sig), len(prev))
            sig[:min_len] = sig[:min_len] * (1 - blend) + prev[:min_len] * blend
        sig = _normalize(sig)
        snapshots.append(sig.copy())
        _log.info("bass_mangle pass %d/%d — drive=%.2f shift=%.1fst vowel=%s",
                  i + 1, passes, drive, shift, vowel)

    return ResampleResult(
        name=preset.name, passes_completed=passes,
        audio=sig, pass_snapshots=snapshots,
    )


def resample_whirlpool(preset: ResamplePreset,
                       source: np.ndarray | None = None) -> ResampleResult:
    """
    Whirlpool: process → bounce → reverse → repeat.
    Creates dreamy, stretched-out atmospheres.
    """
    sig = source if source is not None else _generate_source(preset)
    snapshots: list[np.ndarray] = [sig.copy()]
    passes = min(preset.passes, MAX_PASSES)

    for i in range(passes):
        # Apply reverb
        sig = _apply_reverb_tail(sig, preset.reverb_decay)
        # Bounce (normalize)
        sig = _normalize(sig)
        # Reverse
        sig = _reverse(sig)
        # Additional processing each pass
        if i % 2 == 0:
            sig = _pitch_shift_fft(sig, -2)  # slight pitch down
        else:
            sig = _pitch_shift_fft(sig, 3)  # slight pitch up
        sig = _normalize(sig)
        snapshots.append(sig.copy())
        _log.info("whirlpool pass %d/%d", i + 1, passes)

    return ResampleResult(
        name=preset.name, passes_completed=passes,
        audio=sig, pass_snapshots=snapshots,
    )


def resample_stutter_stack(preset: ResamplePreset,
                           source: np.ndarray | None = None) -> ResampleResult:
    """
    Stutter stack: chop → stutter → layer → bounce per pass.
    Creates glitchy, rhythmic textures.
    """
    sig = source if source is not None else _generate_source(preset)
    snapshots: list[np.ndarray] = [sig.copy()]
    passes = min(preset.passes, MAX_PASSES)

    for i in range(passes):
        grain_ms = preset.grain_size_ms / (1 + i * 0.5)
        sig = _stutter_chop(sig, grain_ms)
        sig = _tanh_drive(sig, preset.drive * 0.5)
        sig = _normalize(sig)
        snapshots.append(sig.copy())
        _log.info("stutter_stack pass %d/%d — grain=%.1fms", i + 1, passes, grain_ms)

    return ResampleResult(
        name=preset.name, passes_completed=passes,
        audio=sig, pass_snapshots=snapshots,
    )


def resample_spectral_freeze(preset: ResamplePreset,
                              source: np.ndarray | None = None) -> ResampleResult:
    """
    Spectral freeze: freeze a frame → evolve partials → bounce.
    Creates sustained, evolving drone textures.
    """
    sig = source if source is not None else _generate_source(preset)
    snapshots: list[np.ndarray] = [sig.copy()]
    passes = min(preset.passes, MAX_PASSES)

    for i in range(passes):
        position = preset.freeze_position + i * 0.1 * PHI
        position = position % 1.0
        sig = _spectral_freeze(sig, position)
        # Slight modulation per pass
        sig = _pitch_shift_fft(sig, (i - passes / 2) * 0.5)
        sig = _apply_reverb_tail(sig, preset.reverb_decay * 0.5)
        sig = _normalize(sig)
        snapshots.append(sig.copy())
        _log.info("spectral_freeze pass %d/%d — pos=%.2f", i + 1, passes, position)

    return ResampleResult(
        name=preset.name, passes_completed=passes,
        audio=sig, pass_snapshots=snapshots,
    )


def resample_master(preset: ResamplePreset,
                    source: np.ndarray | None = None) -> ResampleResult:
    """
    Master resample: take full mix → reverse snippet → layer as transition FX.
    """
    sig = source if source is not None else _generate_source(preset)
    snapshots: list[np.ndarray] = [sig.copy()]
    passes = min(preset.passes, MAX_PASSES)
    n = len(sig)

    for i in range(passes):
        # Take last beat-sized chunk
        chunk_size = min(n // 4, n)
        chunk = sig[-chunk_size:].copy()
        chunk = _reverse(chunk)
        chunk = _apply_reverb_tail(chunk, preset.reverb_decay)
        chunk = _normalize(chunk)
        # Layer back at transition point
        start = max(0, n - chunk_size * 2)
        end = min(n, start + len(chunk))
        sig[start:end] += chunk[:end - start] * preset.feedback_amount
        sig = _normalize(sig)
        snapshots.append(sig.copy())
        _log.info("master_resample pass %d/%d", i + 1, passes)

    return ResampleResult(
        name=preset.name, passes_completed=passes,
        audio=sig, pass_snapshots=snapshots,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

RESAMPLE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "bass_mangle": resample_bass_mangle,
    "whirlpool": resample_whirlpool,
    "stutter_stack": resample_stutter_stack,
    "spectral_freeze": resample_spectral_freeze,
    "master_resample": resample_master,
}


def run_resample_chain(preset: ResamplePreset,
                       source: np.ndarray | None = None) -> ResampleResult:
    """Run a resampling chain from a preset."""
    fn = RESAMPLE_FUNCTIONS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown resample mode: {preset.mode}")
    return fn(preset, source)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def bass_mangle_bank() -> ResampleBank:
    return ResampleBank("bass_mangle", [
        ResamplePreset("growl_mangle_3x", "bass_mangle", passes=3, frequency=55, drive=0.8),
        ResamplePreset("neuro_mangle_5x", "bass_mangle", passes=5, frequency=65, drive=1.0, pitch_shift_semitones=-7),
        ResamplePreset("subtle_mangle", "bass_mangle", passes=2, frequency=55, drive=0.3, feedback_amount=0.4),
        ResamplePreset("formant_mangle", "bass_mangle", passes=4, frequency=55, drive=0.6, formant_vowel="O"),
    ])


def whirlpool_bank() -> ResampleBank:
    return ResampleBank("whirlpool", [
        ResamplePreset("deep_whirlpool", "whirlpool", passes=4, reverb_decay=0.6, duration_s=4.0),
        ResamplePreset("shimmer_whirl", "whirlpool", passes=3, reverb_decay=0.8, frequency=220),
        ResamplePreset("dark_whirl", "whirlpool", passes=5, reverb_decay=0.5, frequency=40),
        ResamplePreset("quick_whirl", "whirlpool", passes=2, reverb_decay=0.4, duration_s=1.0),
    ])


def stutter_bank() -> ResampleBank:
    return ResampleBank("stutter_stack", [
        ResamplePreset("tight_stutter", "stutter_stack", passes=3, grain_size_ms=20),
        ResamplePreset("loose_stutter", "stutter_stack", passes=2, grain_size_ms=80),
        ResamplePreset("glitch_stutter", "stutter_stack", passes=4, grain_size_ms=10, drive=0.9),
        ResamplePreset("rhythmic_stutter", "stutter_stack", passes=3, grain_size_ms=50),
    ])


def freeze_bank() -> ResampleBank:
    return ResampleBank("spectral_freeze", [
        ResamplePreset("mid_freeze", "spectral_freeze", passes=3, freeze_position=0.5),
        ResamplePreset("attack_freeze", "spectral_freeze", passes=2, freeze_position=0.05),
        ResamplePreset("tail_freeze", "spectral_freeze", passes=4, freeze_position=0.9),
        ResamplePreset("evolve_freeze", "spectral_freeze", passes=5, freeze_position=0.3, reverb_decay=0.6),
    ])


def master_bank() -> ResampleBank:
    return ResampleBank("master_resample", [
        ResamplePreset("transition_reverse", "master_resample", passes=2, reverb_decay=0.5),
        ResamplePreset("heavy_feedback", "master_resample", passes=3, feedback_amount=0.9),
        ResamplePreset("subtle_layer", "master_resample", passes=1, feedback_amount=0.3),
        ResamplePreset("chaotic_master", "master_resample", passes=4, feedback_amount=0.8, drive=0.7),
    ])


ALL_RESAMPLE_BANKS = [
    bass_mangle_bank, whirlpool_bank, stutter_bank, freeze_bank, master_bank,
]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_resample_results(results: list[ResampleResult],
                            output_dir: str = "output/resampled") -> list[str]:
    """Write resample results as WAV files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for r in results:
        path = out / f"{r.name}.wav"
        write_wav(str(path), r.audio, SAMPLE_RATE)
        paths.append(str(path))
        _log.info("Exported resample: %s (%d passes)", path, r.passes_completed)
    return paths


def write_resample_manifest(results: list[ResampleResult],
                            output_dir: str = "output/analysis") -> str:
    """Write JSON manifest of resample results."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "resample_feedback_manifest.json"
    data = [
        {"name": r.name, "passes": r.passes_completed,
         "samples": len(r.audio), "snapshots": len(r.pass_snapshots)}
        for r in results
    ]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
