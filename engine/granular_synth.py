"""
DUBFORGE Engine — Granular Synth

Granular synthesis engine: slices audio into tiny grains and reassembles
with pitch, density, scatter, and envelope control. Five granular modes:
cloud, scatter, stretch, freeze, shimmer — all governed by phi/Fibonacci.

Outputs:
    output/wavetables/granular_*.wav
    output/analysis/granular_synth_manifest.json
"""

from __future__ import annotations

import json
from typing import Any, Callable
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)
from engine.accel import write_wav

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class GranularPreset:
    """Configuration for a granular synthesis patch."""
    name: str
    grain_type: str  # cloud | scatter | stretch | freeze | shimmer
    frequency: float = 220.0
    duration_s: float = 4.0
    grain_size_ms: float = 50.0
    grain_density: float = 0.7  # 0-1: sparse to dense
    pitch_spread: float = 0.0  # semitones
    attack_s: float = 0.1
    release_s: float = 0.5
    brightness: float = 0.6
    reverb_amount: float = 0.3
    scatter_amount: float = 0.0
    distortion: float = 0.0


@dataclass
class GranularBank:
    """A named collection of granular presets."""
    name: str
    presets: list[GranularPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _grain_envelope(n: int) -> np.ndarray:
    """Hann window grain envelope."""
    return 0.5 * (1 - np.cos(2 * math.pi * np.arange(n) / max(1, n - 1)))


def _global_envelope(n: int, preset: GranularPreset,
                     sample_rate: int) -> np.ndarray:
    """Attack-sustain-release envelope for overall output."""
    env = np.ones(n)
    attack_n = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release_n = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env[:attack_n] = np.linspace(0, 1, attack_n)
    env[-release_n:] = np.linspace(1, 0, release_n)
    return env


def _soft_clip(signal: np.ndarray, drive: float) -> np.ndarray:
    """Soft-clip distortion."""
    if drive <= 0:
        return signal
    gain = 1.0 + drive * 5.0
    return np.tanh(signal * gain) / np.tanh(gain)


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        return signal / peak * 0.95
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_cloud(preset: GranularPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Cloud grains — dense overlapping grains creating thick textures."""
    n = int(preset.duration_s * sample_rate)
    output = np.zeros(n)
    rng = np.random.default_rng(42)

    grain_n = max(64, int(preset.grain_size_ms * sample_rate / 1000))
    hop = max(1, int(grain_n * (1 - preset.grain_density * 0.8)))
    env = _grain_envelope(grain_n)

    pos = 0
    while pos < n:
        # Slight pitch variation per grain
        pitch_shift = 2 ** (rng.uniform(-preset.pitch_spread, preset.pitch_spread) / 12)
        freq = preset.frequency * pitch_shift
        t_grain = np.arange(grain_n) / sample_rate
        grain = np.sin(2 * math.pi * freq * t_grain)
        # Add harmonics for brightness
        if preset.brightness > 0.3:
            grain += 0.3 * preset.brightness * np.sin(4 * math.pi * freq * t_grain)
        grain *= env
        end = min(n, pos + grain_n)
        output[pos:end] += grain[:end - pos]
        pos += hop

    output = _soft_clip(output, preset.distortion)
    output *= _global_envelope(n, preset, sample_rate)
    return _normalize(output)


def synthesize_scatter(preset: GranularPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Scatter grains — randomly placed sparse grains with wide stereo feel."""
    n = int(preset.duration_s * sample_rate)
    output = np.zeros(n)
    rng = np.random.default_rng(55)

    grain_n = max(64, int(preset.grain_size_ms * sample_rate / 1000))
    # Number of grains based on density
    num_grains = max(8, int(preset.grain_density * n / grain_n * 2))
    env = _grain_envelope(grain_n)

    for _ in range(num_grains):
        pos = rng.integers(0, max(1, n - grain_n))
        pitch_shift = 2 ** (rng.uniform(-preset.pitch_spread, preset.pitch_spread) / 12)
        freq = preset.frequency * pitch_shift

        scatter_offset = rng.uniform(-preset.scatter_amount, preset.scatter_amount)
        freq *= 2 ** (scatter_offset / 12)

        t_grain = np.arange(grain_n) / sample_rate
        grain = np.sin(2 * math.pi * freq * t_grain)
        if preset.brightness > 0.4:
            grain += 0.25 * np.sin(2 * math.pi * freq * 2 * t_grain)
        grain *= env * rng.uniform(0.4, 1.0)
        end = min(n, pos + grain_n)
        output[pos:end] += grain[:end - pos]

    output = _soft_clip(output, preset.distortion)
    output *= _global_envelope(n, preset, sample_rate)
    return _normalize(output)


def synthesize_stretch(preset: GranularPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Stretch grains — time-stretched with evolving pitch."""
    n = int(preset.duration_s * sample_rate)
    output = np.zeros(n)

    grain_n = max(128, int(preset.grain_size_ms * sample_rate / 1000))
    hop = max(1, int(grain_n * 0.25))  # 75% overlap for smooth stretching
    env = _grain_envelope(grain_n)

    # Source: single cycle of waveform at base frequency
    cycle_len = max(2, int(sample_rate / preset.frequency))
    t_cycle = np.arange(cycle_len) / sample_rate
    source = np.sin(2 * math.pi * preset.frequency * t_cycle)
    source += preset.brightness * 0.4 * np.sin(4 * math.pi * preset.frequency * t_cycle)

    pos = 0
    read_pos = 0.0
    while pos < n:
        # Read from source with slow read pointer advancement
        start_idx = int(read_pos) % cycle_len
        grain = np.zeros(grain_n)
        for i in range(grain_n):
            grain[i] = source[(start_idx + i) % cycle_len]
        grain *= env
        end = min(n, pos + grain_n)
        output[pos:end] += grain[:end - pos]
        pos += hop
        read_pos += hop * 0.1 * (1 - preset.grain_density * 0.8)

    output = _soft_clip(output, preset.distortion)
    output *= _global_envelope(n, preset, sample_rate)
    return _normalize(output)


def synthesize_freeze(preset: GranularPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Freeze grains — single frozen grain repeated for sustained drones."""
    n = int(preset.duration_s * sample_rate)
    output = np.zeros(n)

    grain_n = max(128, int(preset.grain_size_ms * sample_rate / 1000))
    env = _grain_envelope(grain_n)

    # Create the frozen grain
    t_grain = np.arange(grain_n) / sample_rate
    grain = np.sin(2 * math.pi * preset.frequency * t_grain)
    grain += preset.brightness * 0.5 * np.sin(4 * math.pi * preset.frequency * t_grain)
    grain += 0.15 * np.sin(2 * math.pi * preset.frequency * PHI * t_grain)
    grain *= env

    hop = max(1, int(grain_n * (1 - preset.grain_density * 0.9)))
    pos = 0
    while pos < n:
        end = min(n, pos + grain_n)
        output[pos:end] += grain[:end - pos]
        pos += hop

    output = _soft_clip(output, preset.distortion)
    output *= _global_envelope(n, preset, sample_rate)
    return _normalize(output)


def synthesize_shimmer(preset: GranularPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Shimmer grains — pitch-shifted grains creating ethereal octave effects."""
    n = int(preset.duration_s * sample_rate)
    output = np.zeros(n)
    rng = np.random.default_rng(77)

    grain_n = max(64, int(preset.grain_size_ms * sample_rate / 1000))
    hop = max(1, int(grain_n * (1 - preset.grain_density * 0.7)))
    env = _grain_envelope(grain_n)

    # Shimmer: layer grains at octave intervals
    pitch_layers = [1.0, 2.0, 0.5, PHI]  # root, octave up, octave down, phi
    layer_amps = [1.0, 0.5 * preset.brightness, 0.3, 0.2]

    pos = 0
    layer_idx = 0
    while pos < n:
        ratio = pitch_layers[layer_idx % len(pitch_layers)]
        amp = layer_amps[layer_idx % len(layer_amps)]
        freq = preset.frequency * ratio
        pitch_jitter = 2 ** (rng.uniform(-0.5, 0.5) * preset.pitch_spread / 12)
        freq *= pitch_jitter

        t_grain = np.arange(grain_n) / sample_rate
        grain = np.sin(2 * math.pi * freq * t_grain) * amp
        grain *= env
        end = min(n, pos + grain_n)
        output[pos:end] += grain[:end - pos]
        pos += hop
        layer_idx += 1

    output = _soft_clip(output, preset.distortion)
    output *= _global_envelope(n, preset, sample_rate)
    return _normalize(output)


# ═══════════════════════════════════════════════════════════════════════════
# v2.4 SYNTHESIZERS — dust, reverse, spectral
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_dust(preset: GranularPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Dust granular — sparse micro-grain crackles."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.RandomState(42)
    signal = np.zeros(n)
    grain_samples = max(1, int(preset.grain_size_ms * sample_rate / 1000))
    t_grain = np.linspace(0, 1, grain_samples, endpoint=False)
    num_grains = int(preset.grain_density * n / grain_samples)
    for _ in range(num_grains):
        pos = rng.randint(0, max(1, n - grain_samples))
        freq = preset.frequency * (1 + rng.uniform(-preset.pitch_spread, preset.pitch_spread) / 12)
        grain = np.sin(2 * np.pi * freq * t_grain / sample_rate * np.arange(grain_samples))
        grain *= np.hanning(grain_samples)
        grain *= rng.uniform(0.3, 1.0)
        end = min(pos + grain_samples, n)
        signal[pos:end] += grain[:end - pos]
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


def synthesize_reverse(preset: GranularPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Reverse granular — reversed grain playback."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.RandomState(43)
    signal = np.zeros(n)
    grain_samples = max(1, int(preset.grain_size_ms * sample_rate / 1000))
    t_grain = np.arange(grain_samples)
    num_grains = int(preset.grain_density * n / grain_samples)
    for _ in range(num_grains):
        pos = rng.randint(0, max(1, n - grain_samples))
        freq = preset.frequency * (1 + rng.uniform(-preset.pitch_spread, preset.pitch_spread) / 12)
        grain = np.sin(2 * np.pi * freq * t_grain / sample_rate)
        grain *= np.hanning(grain_samples)
        grain = grain[::-1]  # reverse
        end = min(pos + grain_samples, n)
        signal[pos:end] += grain[:end - pos]
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


def synthesize_spectral(preset: GranularPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Spectral granular — harmonically-rich spectral grains."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.RandomState(44)
    signal = np.zeros(n)
    grain_samples = max(1, int(preset.grain_size_ms * sample_rate / 1000))
    t_grain = np.arange(grain_samples)
    num_grains = int(preset.grain_density * n / grain_samples)
    for _ in range(num_grains):
        pos = rng.randint(0, max(1, n - grain_samples))
        freq = preset.frequency * (1 + rng.uniform(-preset.pitch_spread, preset.pitch_spread) / 12)
        grain = np.zeros(grain_samples)
        for h in range(1, 6):
            amp = preset.brightness / h
            grain += amp * np.sin(2 * np.pi * freq * h * t_grain / sample_rate)
        grain *= np.hanning(grain_samples)
        end = min(pos + grain_samples, n)
        signal[pos:end] += grain[:end - pos]
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_granular(preset: GranularPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct granular synthesizer."""
    synthesizers = {
        "cloud": synthesize_cloud,
        "scatter": synthesize_scatter,
        "stretch": synthesize_stretch,
        "freeze": synthesize_freeze,
        "shimmer": synthesize_shimmer,
        "dust": synthesize_dust,
        "reverse": synthesize_reverse,
        "spectral": synthesize_spectral,
    }
    fn = synthesizers.get(preset.grain_type)
    if fn is None:
        raise ValueError(f"Unknown grain_type: {preset.grain_type!r}")
    return fn(preset, sample_rate)

def tq_compress_granular(
    signal: np.ndarray,
    name: str,
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress a granular synthesis render."""
    samples = signal.tolist()
    bits = phi_optimal_bits(len(samples))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(samples, name, cfg, sample_rate=sample_rate)

# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 presets = 20
# ═══════════════════════════════════════════════════════════════════════════


def cloud_bank() -> GranularBank:
    """Cloud granular — dense overlapping grain textures."""
    return GranularBank(
        name="CLOUD_GRAINS",
        presets=[
            GranularPreset("cloud_low_A2", "cloud", 110.0, duration_s=5.0,
                           grain_size_ms=60, grain_density=0.8, brightness=0.5),
            GranularPreset("cloud_mid_E3", "cloud", 164.81, duration_s=5.0,
                           grain_size_ms=40, grain_density=0.9, brightness=0.7),
            GranularPreset("cloud_hi_A3", "cloud", 220.0, duration_s=4.0,
                           grain_size_ms=30, grain_density=0.85, brightness=0.8),
            GranularPreset("cloud_deep_E2", "cloud", 82.41, duration_s=6.0,
                           grain_size_ms=80, grain_density=0.75, brightness=0.4),
        ],
    )


def scatter_bank() -> GranularBank:
    """Scatter granular — sparse randomly-placed grains."""
    return GranularBank(
        name="SCATTER_GRAINS",
        presets=[
            GranularPreset("scatter_wide_C3", "scatter", 130.81, duration_s=5.0,
                           grain_size_ms=45, grain_density=0.4, scatter_amount=5.0,
                           pitch_spread=3.0),
            GranularPreset("scatter_tight_G3", "scatter", 196.0, duration_s=4.0,
                           grain_size_ms=30, grain_density=0.3, scatter_amount=2.0,
                           pitch_spread=1.0),
            GranularPreset("scatter_dense_A3", "scatter", 220.0, duration_s=4.0,
                           grain_size_ms=50, grain_density=0.6, scatter_amount=4.0,
                           pitch_spread=5.0),
            GranularPreset("scatter_lo_E2", "scatter", 82.41, duration_s=6.0,
                           grain_size_ms=70, grain_density=0.35, scatter_amount=3.0,
                           pitch_spread=2.0),
        ],
    )


def stretch_bank() -> GranularBank:
    """Stretch granular — time-stretched evolving tones."""
    return GranularBank(
        name="STRETCH_GRAINS",
        presets=[
            GranularPreset("stretch_slow_A2", "stretch", 110.0, duration_s=6.0,
                           grain_size_ms=100, grain_density=0.6, brightness=0.5),
            GranularPreset("stretch_mid_D3", "stretch", 146.83, duration_s=5.0,
                           grain_size_ms=80, grain_density=0.7, brightness=0.6),
            GranularPreset("stretch_bright_G3", "stretch", 196.0, duration_s=4.0,
                           grain_size_ms=60, grain_density=0.8, brightness=0.8),
            GranularPreset("stretch_deep_E2", "stretch", 82.41, duration_s=8.0,
                           grain_size_ms=120, grain_density=0.5, brightness=0.3),
        ],
    )


def freeze_bank() -> GranularBank:
    """Freeze granular — sustained frozen grain drones."""
    return GranularBank(
        name="FREEZE_GRAINS",
        presets=[
            GranularPreset("freeze_warm_C3", "freeze", 130.81, duration_s=6.0,
                           grain_size_ms=80, grain_density=0.85, brightness=0.5),
            GranularPreset("freeze_bright_E3", "freeze", 164.81, duration_s=5.0,
                           grain_size_ms=60, grain_density=0.9, brightness=0.8),
            GranularPreset("freeze_dark_A2", "freeze", 110.0, duration_s=8.0,
                           grain_size_ms=100, grain_density=0.8, brightness=0.3),
            GranularPreset("freeze_hi_A3", "freeze", 220.0, duration_s=4.0,
                           grain_size_ms=40, grain_density=0.95, brightness=0.7),
        ],
    )


def shimmer_bank() -> GranularBank:
    """Shimmer granular — ethereal octave-shifted grain layers."""
    return GranularBank(
        name="SHIMMER_GRAINS",
        presets=[
            GranularPreset("shimmer_ethereal_C3", "shimmer", 130.81, duration_s=6.0,
                           grain_size_ms=50, grain_density=0.7, pitch_spread=2.0,
                           brightness=0.8),
            GranularPreset("shimmer_deep_E2", "shimmer", 82.41, duration_s=8.0,
                           grain_size_ms=70, grain_density=0.6, pitch_spread=3.0,
                           brightness=0.6),
            GranularPreset("shimmer_bright_A3", "shimmer", 220.0, duration_s=4.0,
                           grain_size_ms=35, grain_density=0.8, pitch_spread=1.5,
                           brightness=0.9),
            GranularPreset("shimmer_warm_G3", "shimmer", 196.0, duration_s=5.0,
                           grain_size_ms=55, grain_density=0.75, pitch_spread=2.5,
                           brightness=0.5),
        ],
    )


def dust_bank() -> GranularBank:
    """Dust granular — sparse micro-grain crackles."""
    return GranularBank(
        name="DUST_GRAINS",
        presets=[
            GranularPreset("dust_sparse_C4", "dust", 261.63, duration_s=5.0,
                           grain_size_ms=15, grain_density=0.3, pitch_spread=1.0,
                           brightness=0.4),
            GranularPreset("dust_dense_A3", "dust", 220.0, duration_s=4.0,
                           grain_size_ms=10, grain_density=0.8, pitch_spread=0.5,
                           brightness=0.6),
            GranularPreset("dust_wide_E3", "dust", 164.81, duration_s=6.0,
                           grain_size_ms=20, grain_density=0.5, pitch_spread=3.0,
                           brightness=0.5),
            GranularPreset("dust_tiny_G4", "dust", 392.00, duration_s=3.0,
                           grain_size_ms=5, grain_density=0.6, pitch_spread=2.0,
                           brightness=0.7),
        ],
    )


def reverse_grain_bank() -> GranularBank:
    """Reverse granular — reversed grain textures."""
    return GranularBank(
        name="REVERSE_GRAINS",
        presets=[
            GranularPreset("reverse_slow_C3", "reverse", 130.81, duration_s=6.0,
                           grain_size_ms=80, grain_density=0.5, pitch_spread=1.0,
                           brightness=0.5),
            GranularPreset("reverse_fast_E4", "reverse", 329.63, duration_s=3.0,
                           grain_size_ms=30, grain_density=0.8, pitch_spread=2.0,
                           brightness=0.7),
            GranularPreset("reverse_deep_A2", "reverse", 110.0, duration_s=8.0,
                           grain_size_ms=100, grain_density=0.4, pitch_spread=0.5,
                           brightness=0.3),
            GranularPreset("reverse_bright_G3", "reverse", 196.0, duration_s=5.0,
                           grain_size_ms=50, grain_density=0.7, pitch_spread=1.5,
                           brightness=0.8),
        ],
    )


def spectral_grain_bank() -> GranularBank:
    """Spectral granular — harmonically-rich spectral layers."""
    return GranularBank(
        name="SPECTRAL_GRAINS",
        presets=[
            GranularPreset("spectral_rich_C3", "spectral", 130.81, duration_s=5.0,
                           grain_size_ms=60, grain_density=0.7, pitch_spread=1.0,
                           brightness=0.8),
            GranularPreset("spectral_dark_E2", "spectral", 82.41, duration_s=7.0,
                           grain_size_ms=80, grain_density=0.5, pitch_spread=0.5,
                           brightness=0.3),
            GranularPreset("spectral_bright_A3", "spectral", 220.0, duration_s=4.0,
                           grain_size_ms=40, grain_density=0.8, pitch_spread=2.0,
                           brightness=0.9),
            GranularPreset("spectral_wide_G3", "spectral", 196.0, duration_s=6.0,
                           grain_size_ms=70, grain_density=0.6, pitch_spread=3.0,
                           brightness=0.6),
        ],
    )


ALL_GRANULAR_BANKS: dict[str, Callable[..., Any]] = {
    "cloud":   cloud_bank,
    "scatter": scatter_bank,
    "stretch": stretch_bank,
    "freeze":  freeze_bank,
    "shimmer": shimmer_bank,
    # v2.4
    "dust":     dust_bank,
    "reverse":  reverse_grain_bank,
    "spectral": spectral_grain_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════


def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(samples, dtype=np.float64) if not isinstance(samples, np.ndarray) else samples
    write_wav(str(path), _s, sample_rate=sample_rate)



def write_granular_manifest(output_dir: str = "output") -> dict:
    """Generate all granular presets, write WAVs, and save manifest."""
    base = Path(output_dir)
    manifest: dict = {"module": "granular_synth", "banks": {}}

    for bank_key, bank_fn in ALL_GRANULAR_BANKS.items():
        bank = bank_fn()
        bank_info: list[dict] = []
        for preset in bank.presets:
            audio = synthesize_granular(preset)
            wav_path = base / "wavetables" / f"granular_{preset.name}.wav"
            _write_wav(wav_path, audio)
            # TQ sidecar
            cab = tq_compress_granular(audio, preset.name)
            tq_path = base / "wavetables" / f"granular_{preset.name}.tq"
            import pickle
            tq_path.write_bytes(pickle.dumps(cab))
            bank_info.append({
                "name": preset.name,
                "grain_type": preset.grain_type,
                "frequency": preset.frequency,
                "duration_s": preset.duration_s,
                "wav": str(wav_path),
            })
        manifest["banks"][bank_key] = {
            "name": bank.name,
            "presets": bank_info,
        }

    manifest_path = base / "analysis" / "granular_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Granular manifest → %s", manifest_path)
    return manifest


def main() -> None:
    """Entry point for granular_synth module."""
    logger.info("=== DUBFORGE Granular Synth ===")
    manifest = write_granular_manifest()
    total = sum(len(b["presets"]) for b in manifest["banks"].values())
    logger.info("Generated %d granular presets across %d banks",
                total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
