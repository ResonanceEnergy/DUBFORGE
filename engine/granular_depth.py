"""
DUBFORGE Engine — Granular Depth Processor

Deep granular processing for existing audio buffers — time-stretch,
pitch-shift, grain cloud generation, and paulstretch-style freezing.

Unlike granular_synth.py (which synthesizes from scratch), this module
takes an existing audio buffer and granulates it with full independent
control of time and pitch.

Workflow order:
  Phase 1 Stage 4G → after initial synth sketch.
  Takes raw synth/bass audio and creates granular textures from it.
  Also usable in Phase 2 for granular transition FX.

Modes:
    time_stretch   — extreme slow-down without pitch change (paulstretch-style)
    pitch_grain    — pitch-shift via grain resampling (no time change)
    cloud_process  — scatter existing audio into grain cloud
    freeze_frame   — freeze a single moment and sustain it
    morph_grain    — crossfade between two audio sources via grains

Banks: 5 modes × 4 presets = 20 presets
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import fft, ifft, write_wav

_log = get_logger("dubforge.granular_depth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GranularDepthPreset:
    """Configuration for granular depth processing."""
    name: str
    mode: str  # time_stretch | pitch_grain | cloud_process | freeze_frame | morph_grain
    duration_s: float = 4.0
    grain_size_ms: float = 50.0
    grain_overlap: float = 0.75  # 0-1: overlap between grains
    pitch_semitones: float = 0.0
    stretch_factor: float = 2.0  # >1 = slow, <1 = fast
    density: float = 0.8
    scatter: float = 0.0  # random position jitter
    freeze_position: float = 0.5  # 0-1 for freeze mode
    brightness: float = 0.6
    reverb_mix: float = 0.0
    source_frequency: float = 110.0  # for generating test source


@dataclass
class GranularDepthBank:
    name: str
    presets: list[GranularDepthPreset] = field(default_factory=list)


@dataclass
class GranularDepthResult:
    name: str
    mode: str
    audio: np.ndarray
    grain_count: int
    output_duration_s: float


# ═══════════════════════════════════════════════════════════════════════════
# DSP HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _hann_window(n: int) -> np.ndarray:
    return 0.5 * (1 - np.cos(2 * np.pi * np.arange(n) / max(1, n - 1)))


def _normalize(sig: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(sig))
    return sig / peak * 0.95 if peak > 0 else sig


def _generate_test_source(freq: float, duration_s: float,
                          sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a rich test source (multi-harmonic saw + noise)."""
    n = int(duration_s * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for k in range(1, 12):
        if freq * k > sr / 2:
            break
        sig += ((-1) ** (k + 1)) * np.sin(2 * math.pi * freq * k * t) / k
    sig *= 2.0 / math.pi
    return _normalize(sig)


# ═══════════════════════════════════════════════════════════════════════════
# GRANULAR PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

def process_time_stretch(source: np.ndarray, preset: GranularDepthPreset,
                         sr: int = SAMPLE_RATE) -> GranularDepthResult:
    """
    Paulstretch-style extreme time stretching.
    Reads source grains, randomizes phases, overlaps to create sustained texture.
    """
    grain_n = max(64, int(preset.grain_size_ms * sr / 1000))
    hop_in = max(1, int(grain_n * (1 - preset.grain_overlap)))
    hop_out = max(1, int(hop_in * preset.stretch_factor))
    window = _hann_window(grain_n)

    src_n = len(source)
    out_n = int(src_n * preset.stretch_factor)
    output = np.zeros(out_n)
    rng = np.random.default_rng(42)

    read_pos = 0
    write_pos = 0
    grain_count = 0

    while read_pos + grain_n <= src_n and write_pos + grain_n <= out_n:
        grain = source[read_pos:read_pos + grain_n] * window
        # Paulstretch: randomize phases to remove transients
        spectrum = np.fft.rfft(grain)
        random_phase = rng.uniform(0, 2 * np.pi, len(spectrum))
        spectrum = np.abs(spectrum) * np.exp(1j * random_phase)
        grain = np.fft.irfft(spectrum, n=grain_n) * window
        # Write with overlap-add
        end = min(out_n, write_pos + grain_n)
        output[write_pos:end] += grain[:end - write_pos]
        read_pos += hop_in
        write_pos += hop_out
        grain_count += 1

    return GranularDepthResult(
        name=preset.name, mode="time_stretch",
        audio=_normalize(output), grain_count=grain_count,
        output_duration_s=out_n / sr,
    )


def process_pitch_grain(source: np.ndarray, preset: GranularDepthPreset,
                        sr: int = SAMPLE_RATE) -> GranularDepthResult:
    """
    Pitch shift via granular resampling — each grain is resampled
    at a new rate to shift pitch without changing duration.
    """
    ratio = 2.0 ** (preset.pitch_semitones / 12.0)
    grain_n = max(64, int(preset.grain_size_ms * sr / 1000))
    hop = max(1, int(grain_n * (1 - preset.grain_overlap)))
    window = _hann_window(grain_n)

    src_n = len(source)
    output = np.zeros(src_n)
    grain_count = 0

    read_pos = 0
    while read_pos + grain_n <= src_n:
        grain = source[read_pos:read_pos + grain_n] * window
        # Resample grain to shift pitch
        new_len = max(2, int(grain_n / ratio))
        indices = np.linspace(0, grain_n - 1, new_len)
        resampled = np.interp(indices, np.arange(grain_n), grain)
        # Fit back to original grain size
        if len(resampled) < grain_n:
            padded = np.zeros(grain_n)
            padded[:len(resampled)] = resampled
            resampled = padded
        else:
            resampled = resampled[:grain_n]
        resampled *= window
        end = min(src_n, read_pos + grain_n)
        output[read_pos:end] += resampled[:end - read_pos]
        read_pos += hop
        grain_count += 1

    return GranularDepthResult(
        name=preset.name, mode="pitch_grain",
        audio=_normalize(output), grain_count=grain_count,
        output_duration_s=src_n / sr,
    )


def process_cloud(source: np.ndarray, preset: GranularDepthPreset,
                  sr: int = SAMPLE_RATE) -> GranularDepthResult:
    """
    Scatter existing audio into a grain cloud — random read positions,
    random pitch jitter, variable grain sizes.
    """
    grain_n = max(64, int(preset.grain_size_ms * sr / 1000))
    src_n = len(source)
    out_n = int(preset.duration_s * sr)
    output = np.zeros(out_n)
    rng = np.random.default_rng(42)
    window = _hann_window(grain_n)

    num_grains = max(8, int(preset.density * out_n / grain_n * 2))
    grain_count = 0

    for _ in range(num_grains):
        # Random read position from source
        read_pos = rng.integers(0, max(1, src_n - grain_n))
        # Random write position in output
        write_pos = rng.integers(0, max(1, out_n - grain_n))
        # Position jitter
        jitter = int(preset.scatter * grain_n * rng.uniform(-1, 1))
        read_pos = max(0, min(src_n - grain_n, read_pos + jitter))

        grain = source[read_pos:read_pos + grain_n] * window
        # Pitch jitter
        if preset.pitch_semitones != 0:
            shift = rng.uniform(-abs(preset.pitch_semitones), abs(preset.pitch_semitones))
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
        grain_count += 1

    return GranularDepthResult(
        name=preset.name, mode="cloud_process",
        audio=_normalize(output), grain_count=grain_count,
        output_duration_s=out_n / sr,
    )


def process_freeze_frame(source: np.ndarray, preset: GranularDepthPreset,
                         sr: int = SAMPLE_RATE) -> GranularDepthResult:
    """
    Freeze a single moment from the source and sustain it as a drone
    using overlapping grains at the same read position.
    """
    grain_n = max(64, int(preset.grain_size_ms * sr / 1000))
    src_n = len(source)
    out_n = int(preset.duration_s * sr)
    output = np.zeros(out_n)
    window = _hann_window(grain_n)

    # Freeze position in source
    freeze_pos = int(preset.freeze_position * max(0, src_n - grain_n))
    freeze_pos = max(0, min(src_n - grain_n, freeze_pos))
    frozen_grain = source[freeze_pos:freeze_pos + grain_n] * window

    hop = max(1, int(grain_n * (1 - preset.grain_overlap)))
    write_pos = 0
    grain_count = 0

    while write_pos + grain_n <= out_n:
        end = min(out_n, write_pos + grain_n)
        output[write_pos:end] += frozen_grain[:end - write_pos]
        write_pos += hop
        grain_count += 1

    return GranularDepthResult(
        name=preset.name, mode="freeze_frame",
        audio=_normalize(output), grain_count=grain_count,
        output_duration_s=out_n / sr,
    )


def process_morph_grain(source_a: np.ndarray, source_b: np.ndarray,
                        preset: GranularDepthPreset,
                        sr: int = SAMPLE_RATE) -> GranularDepthResult:
    """
    Crossfade between two audio sources via alternating grains.
    Position in the morph (0→1) is controlled by time.
    """
    grain_n = max(64, int(preset.grain_size_ms * sr / 1000))
    out_n = int(preset.duration_s * sr)
    output = np.zeros(out_n)
    window = _hann_window(grain_n)
    hop = max(1, int(grain_n * (1 - preset.grain_overlap)))

    min_src = min(len(source_a), len(source_b))
    write_pos = 0
    grain_count = 0

    while write_pos + grain_n <= out_n:
        progress = write_pos / max(out_n - 1, 1)
        # Progressive crossfade A→B
        read_pos = (write_pos % max(1, min_src - grain_n))
        grain_a = source_a[read_pos:read_pos + grain_n] * window * (1 - progress)
        grain_b = source_b[read_pos:read_pos + grain_n] * window * progress
        grain = grain_a + grain_b
        end = min(out_n, write_pos + grain_n)
        output[write_pos:end] += grain[:end - write_pos]
        write_pos += hop
        grain_count += 1

    return GranularDepthResult(
        name=preset.name, mode="morph_grain",
        audio=_normalize(output), grain_count=grain_count,
        output_duration_s=out_n / sr,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

def run_granular_depth(preset: GranularDepthPreset,
                       source: np.ndarray | None = None,
                       source_b: np.ndarray | None = None) -> GranularDepthResult:
    """Run granular depth processing from a preset."""
    if source is None:
        source = _generate_test_source(preset.source_frequency, preset.duration_s)

    dispatch = {
        "time_stretch": lambda: process_time_stretch(source, preset),
        "pitch_grain": lambda: process_pitch_grain(source, preset),
        "cloud_process": lambda: process_cloud(source, preset),
        "freeze_frame": lambda: process_freeze_frame(source, preset),
        "morph_grain": lambda: process_morph_grain(
            source, source_b if source_b is not None else source[::-1], preset
        ),
    }
    fn = dispatch.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown granular depth mode: {preset.mode}")
    return fn()


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def time_stretch_bank() -> GranularDepthBank:
    return GranularDepthBank("time_stretch", [
        GranularDepthPreset("paulstretch_2x", "time_stretch", stretch_factor=2.0, grain_size_ms=80),
        GranularDepthPreset("paulstretch_4x", "time_stretch", stretch_factor=4.0, grain_size_ms=100),
        GranularDepthPreset("paulstretch_8x", "time_stretch", stretch_factor=8.0, grain_size_ms=120),
        GranularDepthPreset("subtle_stretch", "time_stretch", stretch_factor=1.5, grain_size_ms=50),
    ])


def pitch_grain_bank() -> GranularDepthBank:
    return GranularDepthBank("pitch_grain", [
        GranularDepthPreset("octave_up", "pitch_grain", pitch_semitones=12),
        GranularDepthPreset("octave_down", "pitch_grain", pitch_semitones=-12),
        GranularDepthPreset("fifth_up", "pitch_grain", pitch_semitones=7),
        GranularDepthPreset("phi_shift", "pitch_grain", pitch_semitones=8.12),  # ~PHI ratio
    ])


def cloud_process_bank() -> GranularDepthBank:
    return GranularDepthBank("cloud_process", [
        GranularDepthPreset("dense_cloud", "cloud_process", density=0.9, scatter=0.3),
        GranularDepthPreset("sparse_cloud", "cloud_process", density=0.3, scatter=0.8),
        GranularDepthPreset("pitched_cloud", "cloud_process", density=0.7, pitch_semitones=5),
        GranularDepthPreset("ambient_cloud", "cloud_process", density=0.5, grain_size_ms=100, duration_s=8.0),
    ])


def freeze_frame_bank() -> GranularDepthBank:
    return GranularDepthBank("freeze_frame", [
        GranularDepthPreset("attack_freeze", "freeze_frame", freeze_position=0.05, duration_s=6.0),
        GranularDepthPreset("mid_freeze", "freeze_frame", freeze_position=0.5, duration_s=6.0),
        GranularDepthPreset("tail_freeze", "freeze_frame", freeze_position=0.9, duration_s=6.0),
        GranularDepthPreset("phi_freeze", "freeze_frame", freeze_position=0.618, duration_s=8.0),
    ])


def morph_grain_bank() -> GranularDepthBank:
    return GranularDepthBank("morph_grain", [
        GranularDepthPreset("slow_morph", "morph_grain", duration_s=6.0, grain_size_ms=80),
        GranularDepthPreset("fast_morph", "morph_grain", duration_s=2.0, grain_size_ms=30),
        GranularDepthPreset("textured_morph", "morph_grain", duration_s=4.0, grain_size_ms=60, density=0.9),
        GranularDepthPreset("sparse_morph", "morph_grain", duration_s=4.0, grain_size_ms=100, density=0.4),
    ])


ALL_GRANULAR_DEPTH_BANKS = [
    time_stretch_bank, pitch_grain_bank, cloud_process_bank,
    freeze_frame_bank, morph_grain_bank,
]


def export_granular_depth_results(results: list[GranularDepthResult],
                                  output_dir: str = "output/granular") -> list[str]:
    """Write granular depth results as WAV files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for r in results:
        path = out / f"{r.name}.wav"
        write_wav(str(path), r.audio, SAMPLE_RATE)
        paths.append(str(path))
    return paths


def write_granular_depth_manifest(results: list[GranularDepthResult],
                                  output_dir: str = "output/analysis") -> str:
    """Write JSON manifest."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "granular_depth_manifest.json"
    data = [
        {"name": r.name, "mode": r.mode, "grains": r.grain_count,
         "duration_s": round(r.output_duration_s, 3)}
        for r in results
    ]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
