"""
DUBFORGE Engine — Sub Bass One-Shot Synthesizer

Synthesizes sub-bass one-shots from scratch:
  - Deep Sine:  pure sine sub with phi-shaped envelope
  - Octave:     sine + octave harmonic for presence
  - Fifth:      sine + fifth harmonic for grit
  - Harmonic:   multi-harmonic sub stack
  - Rumble:     modulated low-frequency rumble

All sounds use phi-ratio envelopes and Fibonacci tuning.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/sub_bass_*.wav
    output/analysis/sub_bass_manifest.json
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
from engine.turboquant import (
    compress_audio_buffer,
    CompressedAudioBuffer,
    phi_optimal_bits,
    TurboQuantConfig,
)
from engine.accel import convolve, write_wav

_log = get_logger("dubforge.sub_bass")


def tq_compress_sub_bass(
    signal: np.ndarray,
    label: str = "sub_bass",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress sub bass synthesis output."""
    samples = signal.tolist()
    bits = phi_optimal_bits(len(samples))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(samples, label, cfg, sample_rate=sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SubBassPreset:
    """Settings for a single sub-bass one-shot."""
    name: str
    sub_type: str           # deep_sine | octave | fifth | harmonic | rumble
    frequency: float = 40.0  # Hz
    duration_s: float = 1.5
    attack_s: float = 0.01
    decay_s: float = 0.3
    sustain: float = 0.8
    release_s: float = 0.4
    drive: float = 0.0      # 0..1 soft saturation
    sub_weight: float = 1.0  # fundamental level
    harmonic_mix: float = 0.3  # upper harmonic level
    lfo_rate: float = 0.0   # Hz, 0 = off
    lfo_depth: float = 0.0  # 0..1 pitch modulation depth


@dataclass
class SubBassBank:
    """Collection of sub-bass presets."""
    name: str
    presets: list[SubBassPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIS HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _adsr_envelope(n: int, preset: SubBassPreset,
                   sample_rate: int) -> np.ndarray:
    """Build ADSR envelope for sub-bass."""
    env = np.zeros(n)
    a = max(1, min(int(preset.attack_s * sample_rate), n // 4))
    d = max(1, min(int(preset.decay_s * sample_rate), n // 4))
    r = max(1, min(int(preset.release_s * sample_rate), n // 4))
    s_len = max(0, n - a - d - r)

    env[:a] = np.linspace(0, 1, a)
    env[a:a + d] = np.linspace(1, preset.sustain, d)
    env[a + d:a + d + s_len] = preset.sustain
    env[a + d + s_len:] = np.linspace(preset.sustain, 0, r)
    return env


def _soft_clip(signal: np.ndarray, drive: float) -> np.ndarray:
    """Apply soft saturation."""
    if drive <= 0:
        return signal
    gain = 1.0 + drive * 4.0
    return np.tanh(signal * gain) / np.tanh(gain)


def _apply_lfo(t: np.ndarray, preset: SubBassPreset) -> np.ndarray:
    """Return pitch modulation multiplier from LFO."""
    if preset.lfo_rate <= 0 or preset.lfo_depth <= 0:
        return np.ones_like(t)
    mod = 1.0 + preset.lfo_depth * 0.1 * np.sin(2 * math.pi * preset.lfo_rate * t)
    return mod


# ═══════════════════════════════════════════════════════════════════════════
# SUB-BASS SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_deep_sine(preset: SubBassPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pure sine sub-bass with phi-shaped envelope."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    signal = np.sin(2 * math.pi * preset.frequency * mod * t)
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_octave(preset: SubBassPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sine + octave harmonic for upper register presence."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    fundamental = np.sin(2 * math.pi * preset.frequency * mod * t)
    octave = np.sin(2 * math.pi * preset.frequency * 2 * mod * t)
    signal = preset.sub_weight * fundamental + preset.harmonic_mix * octave
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_fifth(preset: SubBassPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sine + perfect fifth (3:2 ratio) harmonic for grit."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    fundamental = np.sin(2 * math.pi * preset.frequency * mod * t)
    fifth = np.sin(2 * math.pi * preset.frequency * 1.5 * mod * t)
    signal = preset.sub_weight * fundamental + preset.harmonic_mix * fifth
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_harmonic(preset: SubBassPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Multi-harmonic sub stack using Fibonacci partial levels."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    fib_levels = [1.0, 0.618, 0.382, 0.236, 0.146]  # phi decay
    harmonics = [1, 2, 3, 5, 8]  # Fibonacci harmonic numbers
    signal = np.zeros(n)
    for h, lvl in zip(harmonics, fib_levels):
        amp = preset.sub_weight if h == 1 else preset.harmonic_mix * lvl
        signal += amp * np.sin(2 * math.pi * preset.frequency * h * mod * t)
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_rumble(preset: SubBassPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Modulated low-frequency rumble with noise component."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)

    # Base sine with built-in slow modulation
    mod_rate = max(preset.lfo_rate, PHI)  # always some modulation
    mod = 1.0 + 0.05 * np.sin(2 * math.pi * mod_rate * t)
    fundamental = np.sin(2 * math.pi * preset.frequency * mod * t)

    # Low-passed noise rumble component
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(n)
    # Simple low-pass: cumulative average
    kernel_size = max(1, int(sample_rate / (preset.frequency * 2)))
    kernel = np.ones(kernel_size) / kernel_size
    noise_lp = convolve(noise, kernel, mode="same")
    noise_lp /= np.max(np.abs(noise_lp)) + 1e-10

    signal = preset.sub_weight * fundamental + preset.harmonic_mix * noise_lp * 0.5
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_pulse_sub(preset: SubBassPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Square-pulse sub-bass with variable duty cycle."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    # Build square from odd harmonics (bandlimited)
    signal = np.zeros(n)
    for h in range(1, 8, 2):
        freq = preset.frequency * h
        if freq > sample_rate / 2:
            break
        amp = preset.sub_weight / h if h == 1 else preset.harmonic_mix / h
        signal += amp * np.sin(2 * math.pi * freq * mod * t)
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_triangle_sub(preset: SubBassPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Triangle-wave sub-bass — warm and round."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)
    mod = _apply_lfo(t, preset)

    # Triangle from odd harmonics with alternating sign and 1/h² decay
    signal = np.zeros(n)
    for i, h in enumerate(range(1, 10, 2)):
        freq = preset.frequency * h
        if freq > sample_rate / 2:
            break
        sign = (-1) ** i
        amp = sign / (h * h)
        signal += amp * np.sin(2 * math.pi * freq * mod * t)
    signal *= (8 / (math.pi ** 2))
    signal = preset.sub_weight * signal
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_fm_sub(preset: SubBassPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM sub-bass — frequency-modulated sub tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # FM synthesis with sub-friendly ratio
    mod_freq = preset.frequency * PHI
    mod_index = preset.harmonic_mix * 2
    modulator = mod_index * np.sin(2 * math.pi * mod_freq * t)
    signal = np.sin(2 * math.pi * preset.frequency * t + modulator)

    # Add pure sub for weight
    signal = signal * 0.6 + 0.4 * np.sin(2 * math.pi * preset.frequency * t)
    signal *= preset.sub_weight

    env = _adsr_envelope(n, preset, sample_rate)
    signal = _soft_clip(signal * env, preset.drive)
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_distorted_sub(preset: SubBassPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Distorted sub-bass — saturated sub for aggressive low end."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich sub with harmonics
    signal = np.sin(2 * math.pi * preset.frequency * t)
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * 2 * t)
    signal += 0.1 * np.sin(2 * math.pi * preset.frequency * 3 * t)

    # Heavy saturation
    drive = 0.5 + preset.drive * 2
    signal = np.tanh(signal * drive * 3)
    signal *= preset.sub_weight

    env = _adsr_envelope(n, preset, sample_rate)
    signal = signal * env
    return signal / (np.max(np.abs(signal)) + 1e-10)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_sub_bass(preset: SubBassPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct sub-bass synthesizer."""
    synthesizers = {
        "deep_sine": synthesize_deep_sine,
        "octave": synthesize_octave,
        "fifth": synthesize_fifth,
        "harmonic": synthesize_harmonic,
        "rumble": synthesize_rumble,
        "pulse": synthesize_pulse_sub,
        "triangle": synthesize_triangle_sub,
        "fm_sub": synthesize_fm_sub,
        "distorted": synthesize_distorted_sub,
    }
    fn = synthesizers.get(preset.sub_type)
    if fn is None:
        raise ValueError(f"Unknown sub_type: {preset.sub_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 notes = 20 presets
# ═══════════════════════════════════════════════════════════════════════════

_SUB_NOTES = [
    ("E1", 41.20),
    ("A1", 55.00),
    ("C2", 65.41),
    ("F1", 43.65),
]


def deep_sine_bank() -> SubBassBank:
    """Pure sine sub-bass — 4 presets."""
    return SubBassBank(
        name="deep_sine",
        presets=[
            SubBassPreset(f"deep_sine_{note}", "deep_sine", freq,
                          duration_s=2.0, attack_s=0.02, decay_s=0.2,
                          sustain=0.9, release_s=0.5, drive=0.0)
            for note, freq in _SUB_NOTES
        ],
    )


def octave_bank() -> SubBassBank:
    """Sine + octave sub-bass — 4 presets."""
    return SubBassBank(
        name="octave",
        presets=[
            SubBassPreset(f"octave_{note}", "octave", freq,
                          duration_s=1.5, attack_s=0.01, decay_s=0.25,
                          sustain=0.85, release_s=0.4,
                          harmonic_mix=0.25, drive=0.1)
            for note, freq in _SUB_NOTES
        ],
    )


def fifth_bank() -> SubBassBank:
    """Sine + fifth sub-bass — 4 presets."""
    return SubBassBank(
        name="fifth",
        presets=[
            SubBassPreset(f"fifth_{note}", "fifth", freq,
                          duration_s=1.5, attack_s=0.01, decay_s=0.3,
                          sustain=0.8, release_s=0.35,
                          harmonic_mix=0.2, drive=0.15)
            for note, freq in _SUB_NOTES
        ],
    )


def harmonic_bank() -> SubBassBank:
    """Multi-harmonic sub stack — 4 presets."""
    return SubBassBank(
        name="harmonic",
        presets=[
            SubBassPreset(f"harmonic_{note}", "harmonic", freq,
                          duration_s=1.8, attack_s=0.015, decay_s=0.35,
                          sustain=0.75, release_s=0.45,
                          harmonic_mix=0.15, drive=0.2)
            for note, freq in _SUB_NOTES
        ],
    )


def rumble_bank() -> SubBassBank:
    """Modulated rumble sub — 4 presets."""
    return SubBassBank(
        name="rumble",
        presets=[
            SubBassPreset(f"rumble_{note}", "rumble", freq,
                          duration_s=2.0, attack_s=0.03, decay_s=0.4,
                          sustain=0.7, release_s=0.6,
                          harmonic_mix=0.3, drive=0.25,
                          lfo_rate=PHI, lfo_depth=0.3)
            for note, freq in _SUB_NOTES
        ],
    )


def pulse_sub_bank() -> SubBassBank:
    """Pulse-wave sub-bass — 4 presets."""
    return SubBassBank(
        name="pulse",
        presets=[
            SubBassPreset(f"pulse_{note}", "pulse", freq,
                          duration_s=1.8, attack_s=0.01, decay_s=0.2,
                          sustain=0.85, release_s=0.4,
                          harmonic_mix=0.2, drive=0.15)
            for note, freq in _SUB_NOTES
        ],
    )


def triangle_sub_bank() -> SubBassBank:
    """Triangle-wave sub-bass — warm round tone — 4 presets."""
    return SubBassBank(
        name="triangle",
        presets=[
            SubBassPreset(f"triangle_{note}", "triangle", freq,
                          duration_s=2.0, attack_s=0.02, decay_s=0.3,
                          sustain=0.88, release_s=0.5, drive=0.05)
            for note, freq in _SUB_NOTES
        ],
    )


def fm_sub_bank() -> SubBassBank:
    """FM sub-bass — frequency-modulated sub tones — 4 presets."""
    return SubBassBank(
        name="fm_sub",
        presets=[
            SubBassPreset(f"fm_sub_{note}", "fm_sub", freq,
                          duration_s=2.0, attack_s=0.01, decay_s=0.25,
                          sustain=0.85, release_s=0.4,
                          harmonic_mix=0.4, drive=0.1)
            for note, freq in _SUB_NOTES
        ],
    )


def distorted_sub_bank() -> SubBassBank:
    """Distorted sub-bass — saturated aggressive low end — 4 presets."""
    return SubBassBank(
        name="distorted",
        presets=[
            SubBassPreset(f"distorted_{note}", "distorted", freq,
                          duration_s=1.5, attack_s=0.01, decay_s=0.2,
                          sustain=0.9, release_s=0.3, drive=0.6)
            for note, freq in _SUB_NOTES
        ],
    )


ALL_SUB_BASS_BANKS: dict[str, callable] = {
    "deep_sines": deep_sine_bank,
    "octaves": octave_bank,
    "fifths": fifth_bank,
    "harmonics": harmonic_bank,
    "rumbles": rumble_bank,
    # v2.2
    "pulses": pulse_sub_bank,
    "triangles": triangle_sub_bank,
    # v2.3
    "fm_subs": fm_sub_bank,
    "distorteds": distorted_sub_bank,
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



def write_sub_bass_manifest(output_dir: str = "output") -> dict:
    """Synthesize all sub-bass presets and write manifest JSON."""
    out = Path(output_dir)
    wav_dir = out / "wavetables"
    manifest: dict = {"module": "sub_bass", "banks": {}}

    for bank_key, bank_fn in ALL_SUB_BASS_BANKS.items():
        bank = bank_fn()
        entries = []
        for preset in bank.presets:
            audio = synthesize_sub_bass(preset)
            fname = f"sub_bass_{preset.name}.wav"
            _write_wav(wav_dir / fname, audio)
            entries.append({
                "name": preset.name,
                "sub_type": preset.sub_type,
                "frequency": preset.frequency,
                "duration_s": preset.duration_s,
                "file": fname,
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = entries

    manifest_path = out / "analysis" / "sub_bass_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    _log.info("Sub-bass manifest → %s", manifest_path)
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all sub-bass one-shots."""
    _log.info("═══ DUBFORGE Sub-Bass Generator ═══")
    manifest = write_sub_bass_manifest()
    total = sum(len(v) for v in manifest["banks"].values())
    _log.info("Generated %d sub-bass presets across %d banks",
              total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
