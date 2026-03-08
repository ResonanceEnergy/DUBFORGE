"""
DUBFORGE Engine — Glitch Engine

Synthesizes glitch/stutter/beat-repeat effects for dubstep:
  - Stutter:      rapid repeat/chop effect
  - Bitcrush:     bit-depth reduction glitch
  - Tape Stop:    decelerating pitch-down effect
  - Granular Glitch: random grain scatter
  - Buffer Glitch:   buffer-repeat freeze

All sounds use phi-ratio timing and Fibonacci patterns.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/glitch_*.wav
    output/analysis/glitch_engine_manifest.json
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

_log = get_logger("dubforge.glitch_engine")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GlitchPreset:
    """Settings for a single glitch effect."""
    name: str
    glitch_type: str        # stutter | bitcrush | tape_stop | granular_glitch | buffer_glitch
    frequency: float = 200.0
    duration_s: float = 2.0
    rate: float = 8.0       # repetition rate in Hz
    depth: float = 0.8      # effect depth 0-1
    mix: float = 1.0        # dry/wet 0-1
    attack_s: float = 0.005
    release_s: float = 0.1
    distortion: float = 0.0


@dataclass
class GlitchBank:
    """Collection of glitch presets."""
    name: str
    presets: list[GlitchPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    return str(out)


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak
    return signal


def _envelope(n: int, preset: GlitchPreset,
              sample_rate: int) -> np.ndarray:
    attack = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return env


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_stutter(preset: GlitchPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Stutter — rapid repeat/chop effect on a tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Source tone
    source = np.sin(2 * math.pi * preset.frequency * t)
    for h in [2, 3, 5]:
        source += 0.3 / h * np.sin(2 * math.pi * preset.frequency * h * t)

    # Stutter gate
    chop_period = max(1, int(sample_rate / max(0.1, preset.rate)))
    gate = np.zeros(n)
    on_len = max(1, int(chop_period * (1 - preset.depth * 0.5)))
    for start in range(0, n, chop_period):
        end = min(start + on_len, n)
        gate[start:end] = 1.0

    signal = source * gate
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


def synthesize_bitcrush(preset: GlitchPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Bitcrush — bit-depth reduction for lo-fi digital glitch."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Source
    source = np.zeros(n)
    for h in range(1, 8):
        source += np.sin(2 * math.pi * preset.frequency * h * t) / h

    source = _normalize(source)

    # Bit depth reduction
    bits = max(2, int(16 - preset.depth * 14))
    levels = 2 ** bits
    signal = np.round(source * levels / 2) / (levels / 2)

    # Sample rate reduction
    sr_factor = max(1, int(preset.rate))
    if sr_factor > 1:
        for i in range(0, n, sr_factor):
            signal[i:i + sr_factor] = signal[i]

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_tape_stop(preset: GlitchPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tape stop — decelerating pitch-down effect."""
    n = int(preset.duration_s * sample_rate)
    env = _envelope(n, preset, sample_rate)

    # Decelerating frequency curve
    speed = np.linspace(1.0, 0.01, n) ** preset.depth
    phase = np.cumsum(2 * math.pi * preset.frequency * speed / sample_rate)

    signal = np.sin(phase)
    signal += 0.3 * np.sin(phase * 2)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_granular_glitch(preset: GlitchPreset,
                               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Granular glitch — random grain scatter from a tone source."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Source tone
    source = np.sin(2 * math.pi * preset.frequency * t)
    for h in [2, 3]:
        source += 0.4 / h * np.sin(2 * math.pi * preset.frequency * h * t)

    # Scatter grains
    rng = np.random.default_rng(42)
    grain_size = max(64, int(sample_rate / max(1, preset.rate)))
    output = np.zeros(n)
    n_grains = max(1, int(preset.depth * n / grain_size * 2))
    for _ in range(n_grains):
        src_pos = rng.integers(0, max(1, n - grain_size))
        dst_pos = rng.integers(0, max(1, n - grain_size))
        window = np.hanning(grain_size)
        output[dst_pos:dst_pos + grain_size] += (
            source[src_pos:src_pos + grain_size] * window
        )

    signal = output * preset.mix + source * (1 - preset.mix)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_buffer_glitch(preset: GlitchPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Buffer glitch — buffer-repeat freeze effect."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Source tone
    source = np.sin(2 * math.pi * preset.frequency * t)
    source += 0.3 * np.sin(2 * math.pi * preset.frequency * 3 * t)

    # Buffer repeat: capture a chunk and loop it
    buf_size = max(64, int(sample_rate / max(1, preset.rate)))
    output = np.zeros(n)
    freeze_start = int(n * 0.2)
    buffer = source[freeze_start:freeze_start + buf_size].copy()

    # First 20% is dry, rest is frozen buffer
    dry_end = int(n * (1 - preset.depth))
    output[:dry_end] = source[:dry_end]
    for i in range(dry_end, n):
        output[i] = buffer[(i - dry_end) % buf_size]

    signal = output
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_glitch(preset: GlitchPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct glitch synthesizer."""
    synths = {
        "stutter": synthesize_stutter,
        "bitcrush": synthesize_bitcrush,
        "tape_stop": synthesize_tape_stop,
        "granular_glitch": synthesize_granular_glitch,
        "buffer_glitch": synthesize_buffer_glitch,
    }
    fn = synths.get(preset.glitch_type)
    if fn is None:
        raise ValueError(f"Unknown glitch type: {preset.glitch_type}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def stutter_glitch_bank() -> GlitchBank:
    """Stutter glitch presets."""
    return GlitchBank(
        name="STUTTER_GLITCHES",
        presets=[
            GlitchPreset("stutter_8hz", "stutter", rate=8.0, depth=0.7),
            GlitchPreset("stutter_16hz", "stutter", rate=16.0, depth=0.8),
            GlitchPreset("stutter_4hz_heavy", "stutter", rate=4.0, depth=0.9,
                         distortion=0.3),
            GlitchPreset("stutter_32hz_fast", "stutter", rate=32.0, depth=0.6),
        ],
    )


def bitcrush_glitch_bank() -> GlitchBank:
    """Bitcrush glitch presets."""
    return GlitchBank(
        name="BITCRUSH_GLITCHES",
        presets=[
            GlitchPreset("bitcrush_8bit", "bitcrush", depth=0.5, rate=1.0),
            GlitchPreset("bitcrush_4bit", "bitcrush", depth=0.75, rate=2.0),
            GlitchPreset("bitcrush_2bit_harsh", "bitcrush", depth=0.9, rate=4.0,
                         distortion=0.2),
            GlitchPreset("bitcrush_6bit_mild", "bitcrush", depth=0.6, rate=1.0),
        ],
    )


def tape_stop_glitch_bank() -> GlitchBank:
    """Tape stop glitch presets."""
    return GlitchBank(
        name="TAPE_STOP_GLITCHES",
        presets=[
            GlitchPreset("tapestop_fast", "tape_stop", duration_s=1.0,
                         depth=0.9),
            GlitchPreset("tapestop_slow", "tape_stop", duration_s=3.0,
                         depth=0.7),
            GlitchPreset("tapestop_dist", "tape_stop", duration_s=2.0,
                         depth=0.8, distortion=0.4),
            GlitchPreset("tapestop_deep", "tape_stop", duration_s=2.5,
                         depth=1.0, frequency=100.0),
        ],
    )


def granular_glitch_bank() -> GlitchBank:
    """Granular glitch presets."""
    return GlitchBank(
        name="GRANULAR_GLITCHES",
        presets=[
            GlitchPreset("gglitch_scatter", "granular_glitch", rate=8.0,
                         depth=0.7, mix=0.8),
            GlitchPreset("gglitch_dense", "granular_glitch", rate=16.0,
                         depth=0.9, mix=1.0),
            GlitchPreset("gglitch_sparse", "granular_glitch", rate=4.0,
                         depth=0.5, mix=0.6),
            GlitchPreset("gglitch_chaos", "granular_glitch", rate=24.0,
                         depth=1.0, mix=1.0, distortion=0.3),
        ],
    )


def buffer_glitch_bank() -> GlitchBank:
    """Buffer glitch presets."""
    return GlitchBank(
        name="BUFFER_GLITCHES",
        presets=[
            GlitchPreset("bufglitch_short", "buffer_glitch", rate=8.0,
                         depth=0.6),
            GlitchPreset("bufglitch_long", "buffer_glitch", rate=4.0,
                         depth=0.8, duration_s=3.0),
            GlitchPreset("bufglitch_tiny", "buffer_glitch", rate=32.0,
                         depth=0.9),
            GlitchPreset("bufglitch_dist", "buffer_glitch", rate=16.0,
                         depth=0.7, distortion=0.4),
        ],
    )


ALL_GLITCH_BANKS: dict[str, callable] = {
    "stutter": stutter_glitch_bank,
    "bitcrush": bitcrush_glitch_bank,
    "tape_stop": tape_stop_glitch_bank,
    "granular_glitch": granular_glitch_bank,
    "buffer_glitch": buffer_glitch_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST & MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_glitch_manifest(output_dir: str = "output") -> dict:
    """Write glitch engine manifest JSON and return summary."""
    manifest: dict = {"banks": {}}
    out_base = Path(output_dir)
    wav_dir = out_base / "wavetables"
    wav_dir.mkdir(parents=True, exist_ok=True)

    for bank_key, bank_fn in ALL_GLITCH_BANKS.items():
        bank = bank_fn()
        bank_data: list[dict] = []
        for preset in bank.presets:
            signal = synthesize_glitch(preset)
            wav_path = wav_dir / f"glitch_{preset.name}.wav"
            _write_wav(signal, str(wav_path))
            bank_data.append({
                "name": preset.name,
                "type": preset.glitch_type,
                "rate": preset.rate,
                "wav": str(wav_path),
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = {
            "bank_name": bank.name,
            "presets": bank_data,
        }

    manifest_path = out_base / "analysis" / "glitch_engine_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Glitch manifest → %s", manifest_path)
    return manifest


def main():
    """Generate all glitch effect presets."""
    _log.info("═══ Glitch Engine ═══")
    write_glitch_manifest()
    _log.info("Done.")


if __name__ == "__main__":
    main()
