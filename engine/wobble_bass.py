"""
DUBFORGE Engine — Wobble Bass Synthesizer

Synthesizes LFO-modulated wobble bass tones for dubstep:
  - Classic Wobble:  standard LFO-filtered bass
  - Slow Wobble:     half-time deep wobble
  - Fast Wobble:     rapid LFO modulation
  - Vowel Wobble:    formant-shaped LFO wobble
  - Growl Wobble:    distorted aggressive wobble

All sounds use phi-ratio envelopes and Fibonacci tuning.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/wobble_bass_*.wav
    output/analysis/wobble_bass_manifest.json
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import write_wav

_log = get_logger("dubforge.wobble_bass")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WobblePreset:
    """Settings for a single wobble bass sound."""
    name: str
    wobble_type: str        # classic | slow | fast | vowel | growl
    frequency: float = 55.0
    duration_s: float = 2.0
    lfo_rate: float = 4.0   # Hz
    lfo_depth: float = 0.8  # 0-1
    filter_cutoff: float = 0.7
    resonance: float = 0.5
    attack_s: float = 0.01
    release_s: float = 0.2
    distortion: float = 0.0
    sub_mix: float = 0.3


@dataclass
class WobbleBank:
    """Collection of wobble bass presets."""
    name: str
    presets: list[WobblePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s, sample_rate=sample_rate)
    return str(path)



def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak
    return signal


def _envelope(n: int, preset: WobblePreset,
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

def synthesize_classic_wobble(preset: WobblePreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Classic wobble — standard LFO-filtered saw bass."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Rich saw-like source
    signal = np.zeros(n)
    for h in range(1, 10):
        signal += ((-1) ** (h + 1)) * np.sin(2 * math.pi * preset.frequency * h * t) / h

    # LFO modulates amplitude (simulating filter sweep)
    lfo = 0.5 + 0.5 * np.sin(2 * math.pi * preset.lfo_rate * t) * preset.lfo_depth
    signal *= lfo

    # Sub layer
    sub = np.sin(2 * math.pi * preset.frequency * t) * preset.sub_mix
    signal = signal * (1 - preset.sub_mix) + sub

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


def synthesize_slow_wobble(preset: WobblePreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Slow wobble — half-time deep wobble for heavy drops."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Deep square-ish source
    signal = np.sin(2 * math.pi * preset.frequency * t)
    signal += 0.5 * np.sign(np.sin(2 * math.pi * preset.frequency * t))

    # Slow LFO
    rate = preset.lfo_rate * 0.5
    lfo = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * math.pi * rate * t)) ** preset.lfo_depth
    signal *= lfo

    sub = np.sin(2 * math.pi * preset.frequency * t) * preset.sub_mix
    signal = signal * (1 - preset.sub_mix) + sub

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_fast_wobble(preset: WobblePreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Fast wobble — rapid LFO modulation for aggressive texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, 8):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / (h ** 0.8)

    # Fast LFO with square shape
    rate = preset.lfo_rate * 2
    lfo_raw = np.sin(2 * math.pi * rate * t)
    lfo = 0.2 + 0.8 * np.clip(lfo_raw * 3, -1, 1) * 0.5 + 0.5
    signal *= lfo * preset.lfo_depth + (1 - preset.lfo_depth)

    sub = np.sin(2 * math.pi * preset.frequency * t) * preset.sub_mix
    signal = signal * (1 - preset.sub_mix) + sub

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))
    signal *= env
    return _normalize(signal)


def synthesize_vowel_wobble(preset: WobblePreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Vowel wobble — formant-shaped LFO wobble with vocal quality."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Source with rich harmonics
    signal = np.zeros(n)
    for h in range(1, 12):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / h

    # Formant-like LFO: two resonant peaks sweep
    lfo_phase = 2 * math.pi * preset.lfo_rate * t
    formant1 = 300 + 400 * (0.5 + 0.5 * np.sin(lfo_phase))
    formant2 = 800 + 600 * (0.5 + 0.5 * np.sin(lfo_phase * PHI))

    # Apply formant emphasis via amplitude modulation
    mod1 = np.sin(2 * math.pi * formant1 * t / sample_rate * 100)
    mod2 = np.sin(2 * math.pi * formant2 * t / sample_rate * 100)
    formant_mod = 0.5 + 0.25 * mod1 + 0.25 * mod2
    signal *= formant_mod * preset.lfo_depth + (1 - preset.lfo_depth)

    sub = np.sin(2 * math.pi * preset.frequency * t) * preset.sub_mix
    signal = signal * (1 - preset.sub_mix) + sub

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_growl_wobble(preset: WobblePreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Growl wobble — distorted aggressive wobble with grit."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Aggressive saw stack
    signal = np.zeros(n)
    for h in range(1, 15):
        signal += ((-1) ** (h + 1)) * np.sin(2 * math.pi * preset.frequency * h * t) / h

    # Pre-distortion
    signal = np.tanh(signal * 2)

    # LFO with growl character
    lfo = 0.5 + 0.5 * np.sin(2 * math.pi * preset.lfo_rate * t)
    lfo = lfo ** 0.5  # softer waveform shape
    signal *= lfo * preset.lfo_depth + (1 - preset.lfo_depth) * 0.3

    sub = np.sin(2 * math.pi * preset.frequency * t) * preset.sub_mix
    signal = signal * (1 - preset.sub_mix) + sub

    # Additional distortion
    drive = 1 + (preset.distortion + 0.3) * 4
    signal = np.tanh(signal * drive)
    signal *= env
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_wobble(preset: WobblePreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct wobble bass synthesizer."""
    synths = {
        "classic": synthesize_classic_wobble,
        "slow": synthesize_slow_wobble,
        "fast": synthesize_fast_wobble,
        "vowel": synthesize_vowel_wobble,
        "growl": synthesize_growl_wobble,
    }
    fn = synths.get(preset.wobble_type)
    if fn is None:
        raise ValueError(f"Unknown wobble type: {preset.wobble_type}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def classic_wobble_bank() -> WobbleBank:
    """Classic wobble bass presets."""
    return WobbleBank(
        name="CLASSIC_WOBBLES",
        presets=[
            WobblePreset("classic_E1_4hz", "classic", 41.20, lfo_rate=4.0,
                         lfo_depth=0.8, distortion=0.1),
            WobblePreset("classic_A1_2hz", "classic", 55.00, lfo_rate=2.0,
                         lfo_depth=0.9, distortion=0.05),
            WobblePreset("classic_C2_8hz", "classic", 65.41, lfo_rate=8.0,
                         lfo_depth=0.7, distortion=0.2),
            WobblePreset("classic_F1_6hz", "classic", 43.65, lfo_rate=6.0,
                         lfo_depth=0.85, sub_mix=0.4),
        ],
    )


def slow_wobble_bank() -> WobbleBank:
    """Slow wobble bass presets."""
    return WobbleBank(
        name="SLOW_WOBBLES",
        presets=[
            WobblePreset("slow_E1_1hz", "slow", 41.20, lfo_rate=1.0,
                         lfo_depth=0.9, duration_s=4.0),
            WobblePreset("slow_A1_half", "slow", 55.00, lfo_rate=0.5,
                         lfo_depth=1.0, duration_s=4.0, sub_mix=0.4),
            WobblePreset("slow_C2_2hz", "slow", 65.41, lfo_rate=2.0,
                         lfo_depth=0.8, distortion=0.1),
            WobblePreset("slow_F1_deep", "slow", 43.65, lfo_rate=0.75,
                         lfo_depth=0.95, duration_s=3.0),
        ],
    )


def fast_wobble_bank() -> WobbleBank:
    """Fast wobble bass presets."""
    return WobbleBank(
        name="FAST_WOBBLES",
        presets=[
            WobblePreset("fast_E1_16hz", "fast", 41.20, lfo_rate=16.0,
                         lfo_depth=0.7, distortion=0.3),
            WobblePreset("fast_A1_12hz", "fast", 55.00, lfo_rate=12.0,
                         lfo_depth=0.8, distortion=0.25),
            WobblePreset("fast_C2_24hz", "fast", 65.41, lfo_rate=24.0,
                         lfo_depth=0.6, distortion=0.4),
            WobblePreset("fast_F1_20hz", "fast", 43.65, lfo_rate=20.0,
                         lfo_depth=0.75, distortion=0.35),
        ],
    )


def vowel_wobble_bank() -> WobbleBank:
    """Vowel wobble bass presets."""
    return WobbleBank(
        name="VOWEL_WOBBLES",
        presets=[
            WobblePreset("vowel_E1_4hz", "vowel", 41.20, lfo_rate=4.0,
                         lfo_depth=0.8, distortion=0.1),
            WobblePreset("vowel_A1_3hz", "vowel", 55.00, lfo_rate=3.0,
                         lfo_depth=0.9, distortion=0.05),
            WobblePreset("vowel_C2_6hz", "vowel", 65.41, lfo_rate=6.0,
                         lfo_depth=0.7, distortion=0.15),
            WobblePreset("vowel_F1_2hz", "vowel", 43.65, lfo_rate=2.0,
                         lfo_depth=0.85, sub_mix=0.35),
        ],
    )


def growl_wobble_bank() -> WobbleBank:
    """Growl wobble bass presets."""
    return WobbleBank(
        name="GROWL_WOBBLES",
        presets=[
            WobblePreset("growl_E1_4hz", "growl", 41.20, lfo_rate=4.0,
                         lfo_depth=0.9, distortion=0.6),
            WobblePreset("growl_A1_8hz", "growl", 55.00, lfo_rate=8.0,
                         lfo_depth=0.8, distortion=0.7),
            WobblePreset("growl_C2_3hz", "growl", 65.41, lfo_rate=3.0,
                         lfo_depth=1.0, distortion=0.5),
            WobblePreset("growl_F1_6hz", "growl", 43.65, lfo_rate=6.0,
                         lfo_depth=0.85, distortion=0.8),
        ],
    )


ALL_WOBBLE_BANKS: dict[str, callable] = {
    "classic": classic_wobble_bank,
    "slow": slow_wobble_bank,
    "fast": fast_wobble_bank,
    "vowel": vowel_wobble_bank,
    "growl": growl_wobble_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST & MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_wobble_manifest(output_dir: str = "output") -> dict:
    """Write wobble bass manifest JSON and return summary."""
    manifest: dict = {"banks": {}}
    out_base = Path(output_dir)
    wav_dir = out_base / "wavetables"
    wav_dir.mkdir(parents=True, exist_ok=True)

    for bank_key, bank_fn in ALL_WOBBLE_BANKS.items():
        bank = bank_fn()
        bank_data: list[dict] = []
        for preset in bank.presets:
            signal = synthesize_wobble(preset)
            wav_path = wav_dir / f"wobble_bass_{preset.name}.wav"
            _write_wav(signal, str(wav_path))
            bank_data.append({
                "name": preset.name,
                "type": preset.wobble_type,
                "frequency": preset.frequency,
                "lfo_rate": preset.lfo_rate,
                "wav": str(wav_path),
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = {
            "bank_name": bank.name,
            "presets": bank_data,
        }

    manifest_path = out_base / "analysis" / "wobble_bass_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Wobble bass manifest → %s", manifest_path)
    return manifest


def main():
    """Generate all wobble bass presets."""
    _log.info("═══ Wobble Bass Generator ═══")
    write_wobble_manifest()
    _log.info("Done.")


if __name__ == "__main__":
    main()
