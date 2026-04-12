"""
DUBFORGE Engine — Serum 2 LFO Shape Control

Generate custom LFO shapes for Serum 2's internal LFOs.
Serum 2 supports user-drawn LFO shapes — this module generates
mathematically-derived shapes and can push them via the controller bridge.

Serum 2 LFO architecture:
  - 4 LFOs, each with custom drawable shape (128 or 256 points)
  - Shapes stored as normalized float arrays [0.0, 1.0]
  - Rate can be synced to BPM or free Hz
  - Supports unipolar / bipolar mode

Modes:
    phi_step       — Phi-ratio stepped modulation (golden ratio divisions)
    fibonacci_wave — Fibonacci sequence as wave shape
    fractal_lfo    — Self-similar fractal waveform
    euclidean_gate — Euclidean rhythm as gate LFO
    harmonic_stack — Additive harmonics with phi-weighted amplitudes

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

_log = get_logger("dubforge.serum_lfo_shapes")

# Serum LFO shape resolution
LFO_POINTS = 256  # number of sample points in a drawable shape
LFO_MIN = 0.0
LFO_MAX = 1.0
LFO_CENTER = 0.5


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SerumLFOPreset:
    """Configuration for an LFO shape."""
    name: str
    mode: str  # phi_step | fibonacci_wave | fractal_lfo | euclidean_gate | harmonic_stack
    points: int = LFO_POINTS
    # Phi step params
    num_steps: int = 8
    step_curve: float = 0.0  # 0 = hard steps, 1 = smooth interpolation
    # Fibonacci params
    fib_terms: int = 13
    # Fractal params
    fractal_depth: int = 5
    fractal_roughness: float = 0.5
    # Euclidean params
    pulses: int = 5
    rotation: int = 0
    gate_width: float = 0.5  # 0–1 fraction of each step
    # Harmonic params
    num_harmonics: int = 8
    harmonic_falloff: float = PHI  # amplitude = 1/n^falloff
    phase_spread: float = 0.0  # radians spread per harmonic
    # General
    bipolar: bool = False
    smoothing: int = 0  # rolling average window size


@dataclass
class SerumLFOBank:
    name: str
    presets: list[SerumLFOPreset] = field(default_factory=list)


@dataclass
class SerumLFOResult:
    name: str
    mode: str
    shape: np.ndarray  # float array [0..1] or [-1..1] if bipolar
    points: int


# ═══════════════════════════════════════════════════════════════════════════
# SHAPE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_01(arr: np.ndarray) -> np.ndarray:
    """Normalize array to [0, 1] range."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-12:
        return np.full_like(arr, 0.5)
    return (arr - mn) / (mx - mn)


def _normalize_bipolar(arr: np.ndarray) -> np.ndarray:
    """Normalize array to [-1, 1] range."""
    peak = np.max(np.abs(arr))
    if peak < 1e-12:
        return arr
    return arr / peak


def _smooth(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple rolling average smoothing."""
    if window < 2:
        return arr
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def generate_phi_step(preset: SerumLFOPreset) -> SerumLFOResult:
    """
    Golden ratio step modulation.
    Divides the LFO cycle into steps at phi-ratio proportions.
    Each step has a height determined by (step_index / PHI) mod 1.
    """
    n = preset.points
    shape = np.zeros(n)
    # Calculate step boundaries using phi
    boundaries = []
    for k in range(preset.num_steps):
        pos = ((k * PHI) % 1.0) * n
        boundaries.append(int(pos))
    boundaries.sort()
    boundaries.append(n)

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        height = ((i + 1) * PHI) % 1.0
        if preset.step_curve > 0 and end - start > 1:
            # Smooth transition
            ramp_len = max(1, int((end - start) * preset.step_curve * 0.5))
            shape[start:end] = height
            if ramp_len > 0 and start > 0:
                ramp = np.linspace(shape[max(0, start - 1)], height, ramp_len)
                actual = min(ramp_len, end - start)
                shape[start:start + actual] = ramp[:actual]
        else:
            shape[start:end] = height

    shape = _smooth(shape, preset.smoothing)
    if preset.bipolar:
        shape = shape * 2 - 1
    return SerumLFOResult(preset.name, "phi_step", shape, n)


def generate_fibonacci_wave(preset: SerumLFOPreset) -> SerumLFOResult:
    """
    Fibonacci sequence mapped as a waveform.
    Each Fibonacci number becomes a sample height, interpolated across the cycle.
    """
    n = preset.points
    fib = [0, 1]
    for _ in range(preset.fib_terms - 2):
        fib.append(fib[-1] + fib[-2])

    # Map fibonacci values as control points
    x_points = np.linspace(0, n - 1, len(fib))
    y_points = np.array(fib, dtype=np.float64)
    y_points = _normalize_01(y_points)

    shape = np.interp(np.arange(n), x_points, y_points)

    # Add wraparound smoothing
    wrap = min(16, n // 8)
    for i in range(wrap):
        t = i / wrap
        shape[i] = shape[i] * t + shape[-1] * (1 - t)

    shape = _smooth(shape, preset.smoothing)
    if preset.bipolar:
        shape = shape * 2 - 1
    return SerumLFOResult(preset.name, "fibonacci_wave", shape, n)


def generate_fractal_lfo(preset: SerumLFOPreset) -> SerumLFOResult:
    """
    Midpoint displacement fractal waveform.
    Creates self-similar shapes with controllable roughness.
    """
    n = preset.points
    # Start with two endpoints
    rng = np.random.default_rng(42)
    shape = np.zeros(n)
    shape[0] = 0.5
    shape[n - 1] = 0.5

    step = n - 1
    roughness = preset.fractal_roughness
    amplitude = 0.5

    for _ in range(min(preset.fractal_depth, 12)):
        half = step // 2
        if half < 1:
            break
        # Midpoint displacement
        for i in range(half, n - 1, step):
            left = shape[max(0, i - half)]
            right = shape[min(n - 1, i + half)]
            shape[i] = (left + right) / 2 + rng.uniform(-amplitude, amplitude)
        step = half
        amplitude *= 2 ** (-roughness)

    shape = np.clip(shape, 0, 1)
    shape = _smooth(shape, preset.smoothing)
    if preset.bipolar:
        shape = shape * 2 - 1
    return SerumLFOResult(preset.name, "fractal_lfo", shape, n)


def _euclidean_rhythm(steps: int, pulses: int, rotation: int = 0) -> list[bool]:
    """Bjorklund's algorithm for Euclidean rhythms."""
    if pulses >= steps:
        return [True] * steps
    if pulses <= 0:
        return [False] * steps

    pattern: list[list[bool]] = [[True] for _ in range(pulses)] + \
                                 [[False] for _ in range(steps - pulses)]

    while True:
        remainder = len(pattern) - pulses
        if remainder <= 1:
            break
        split = min(pulses, remainder)
        new_pattern = []
        for i in range(split):
            new_pattern.append(pattern[i] + pattern[len(pattern) - 1 - i])
        leftover = pattern[split:len(pattern) - split]
        pattern = new_pattern + leftover
        pulses = len(new_pattern)

    flat = [b for group in pattern for b in group]
    # Apply rotation
    if rotation:
        rotation = rotation % len(flat)
        flat = flat[rotation:] + flat[:rotation]
    return flat


def generate_euclidean_gate(preset: SerumLFOPreset) -> SerumLFOResult:
    """
    Euclidean rhythm mapped as a gate LFO.
    True = gate open (high), False = gate closed (low).
    """
    n = preset.points
    steps = max(2, preset.num_steps)
    rhythm = _euclidean_rhythm(steps, preset.pulses, preset.rotation)

    step_size = n / steps
    shape = np.zeros(n)
    for i, gate in enumerate(rhythm):
        start = int(i * step_size)
        end = int(start + step_size * preset.gate_width)
        end = min(end, int((i + 1) * step_size), n)
        if gate:
            shape[start:end] = 1.0

    shape = _smooth(shape, preset.smoothing)
    if preset.bipolar:
        shape = shape * 2 - 1
    return SerumLFOResult(preset.name, "euclidean_gate", shape, n)


def generate_harmonic_stack(preset: SerumLFOPreset) -> SerumLFOResult:
    """
    Additive synthesis LFO — sum of harmonics with phi-weighted amplitudes.
    Each harmonic n has amplitude 1/n^falloff.
    """
    n = preset.points
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    shape = np.zeros(n)

    for h in range(1, preset.num_harmonics + 1):
        amp = 1.0 / (h ** preset.harmonic_falloff)
        phase = h * preset.phase_spread
        shape += amp * np.sin(h * t + phase)

    if preset.bipolar:
        shape = _normalize_bipolar(shape)
    else:
        shape = _normalize_01(shape)

    shape = _smooth(shape, preset.smoothing)
    return SerumLFOResult(preset.name, "harmonic_stack", shape, n)


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

LFO_GENERATORS: dict[str, Callable[..., Any]] = {
    "phi_step": generate_phi_step,
    "fibonacci_wave": generate_fibonacci_wave,
    "fractal_lfo": generate_fractal_lfo,
    "euclidean_gate": generate_euclidean_gate,
    "harmonic_stack": generate_harmonic_stack,
}


def generate_lfo_shape(preset: SerumLFOPreset) -> SerumLFOResult:
    """Generate an LFO shape from a preset."""
    fn = LFO_GENERATORS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown LFO mode: {preset.mode}")
    return fn(preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def phi_step_bank() -> SerumLFOBank:
    return SerumLFOBank("phi_step", [
        SerumLFOPreset("phi_8_hard", "phi_step", num_steps=8, step_curve=0.0),
        SerumLFOPreset("phi_13_smooth", "phi_step", num_steps=13, step_curve=0.6),
        SerumLFOPreset("phi_5_bipolar", "phi_step", num_steps=5, bipolar=True),
        SerumLFOPreset("phi_21_fine", "phi_step", num_steps=21, step_curve=0.3, smoothing=4),
    ])


def fibonacci_wave_bank() -> SerumLFOBank:
    return SerumLFOBank("fibonacci_wave", [
        SerumLFOPreset("fib_8", "fibonacci_wave", fib_terms=8),
        SerumLFOPreset("fib_13_smooth", "fibonacci_wave", fib_terms=13, smoothing=8),
        SerumLFOPreset("fib_21_bipolar", "fibonacci_wave", fib_terms=21, bipolar=True),
        SerumLFOPreset("fib_5_basic", "fibonacci_wave", fib_terms=5),
    ])


def fractal_lfo_bank() -> SerumLFOBank:
    return SerumLFOBank("fractal_lfo", [
        SerumLFOPreset("fractal_smooth", "fractal_lfo", fractal_depth=4, fractal_roughness=0.3),
        SerumLFOPreset("fractal_rough", "fractal_lfo", fractal_depth=8, fractal_roughness=0.8),
        SerumLFOPreset("fractal_deep", "fractal_lfo", fractal_depth=10, fractal_roughness=0.5),
        SerumLFOPreset("fractal_bipolar", "fractal_lfo", fractal_depth=6, fractal_roughness=0.6,
                       bipolar=True),
    ])


def euclidean_gate_bank() -> SerumLFOBank:
    return SerumLFOBank("euclidean_gate", [
        SerumLFOPreset("euclid_5_8", "euclidean_gate", num_steps=8, pulses=5),
        SerumLFOPreset("euclid_3_8", "euclidean_gate", num_steps=8, pulses=3),
        SerumLFOPreset("euclid_7_16", "euclidean_gate", num_steps=16, pulses=7,
                       gate_width=0.3),
        SerumLFOPreset("euclid_5_13_fib", "euclidean_gate", num_steps=13, pulses=5,
                       rotation=3),
    ])


def harmonic_stack_bank() -> SerumLFOBank:
    return SerumLFOBank("harmonic_stack", [
        SerumLFOPreset("harm_phi_decay", "harmonic_stack", num_harmonics=8,
                       harmonic_falloff=PHI),
        SerumLFOPreset("harm_slow_decay", "harmonic_stack", num_harmonics=12,
                       harmonic_falloff=0.5),
        SerumLFOPreset("harm_spread", "harmonic_stack", num_harmonics=8,
                       phase_spread=PHI),
        SerumLFOPreset("harm_bipolar", "harmonic_stack", num_harmonics=6,
                       harmonic_falloff=1.0, bipolar=True),
    ])


ALL_SERUM_LFO_BANKS = [
    phi_step_bank, fibonacci_wave_bank, fractal_lfo_bank,
    euclidean_gate_bank, harmonic_stack_bank,
]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_lfo_shapes(results: list[SerumLFOResult],
                      output_dir: str = "output/lfo_shapes") -> list[str]:
    """Export LFO shapes as JSON files (float arrays)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for r in results:
        path = out / f"{r.name}.json"
        data = {
            "name": r.name,
            "mode": r.mode,
            "points": r.points,
            "shape": r.shape.tolist(),
        }
        path.write_text(json.dumps(data, indent=2))
        paths.append(str(path))
    return paths


def write_lfo_manifest(results: list[SerumLFOResult],
                       output_dir: str = "output/analysis") -> str:
    """Write a manifest of generated LFO shapes."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "serum_lfo_shapes_manifest.json"
    data = [{"name": r.name, "mode": r.mode, "points": r.points,
             "min": float(r.shape.min()), "max": float(r.shape.max())}
            for r in results]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
