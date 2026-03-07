"""
DUBFORGE Engine — FX Generator

Synthesizes transition FX sounds for dubstep arrangements:
  - Risers: filtered noise sweeps (low → high) with gain curve
  - Impacts: sub thump + transient + noise tail on the 1
  - Sub drops: descending sine pitch sweep (classic dubstep sub drop)

All FX are synthesized with phi-ratio timing and Fibonacci structure.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/fx_riser_*.wav
    output/wavetables/fx_impact_*.wav
    output/wavetables/fx_subdrop_*.wav
    output/analysis/fx_manifest.json

Based on Subtronics production analysis:
  - White noise risers frame every build section
  - Sub impacts hit on beat 1 of every drop
  - Pitch-diving sub drops punctuate transitions
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

_log = get_logger("dubforge.fx_generator")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_BPM = 150


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FXPreset:
    """Settings for a single FX sound."""
    name: str
    fx_type: str        # "riser" | "impact" | "subdrop"
    duration_s: float
    # Riser params
    start_freq: float = 200.0
    end_freq: float = 12000.0
    # Impact params
    sub_freq: float = 50.0
    transient_brightness: float = 0.8
    # Sub drop params
    drop_start_freq: float = 120.0
    drop_end_freq: float = 25.0
    # Common
    distortion: float = 0.0
    reverb_amount: float = 0.3


@dataclass
class FXBank:
    """Collection of FX presets."""
    name: str
    presets: list[FXPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav_raw(signal: np.ndarray, path: str,
                   sample_rate: int = SAMPLE_RATE) -> str:
    """Write arbitrary-length signal to 16-bit mono WAV."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(signal)
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        int_data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(int_data.tobytes())

    _log.info("Wrote FX WAV: %s (%d samples, %.3fs)",
              out_path.name, n, n / sample_rate)
    return str(out_path)


def _lowpass_sweep(
    signal: np.ndarray,
    start_freq: float,
    end_freq: float,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Apply a sweeping lowpass filter using windowed FFT blocks."""
    block_size = 2048
    hop = block_size // 2
    n = len(signal)
    output = np.zeros(n)
    window = np.hanning(block_size)
    total_blocks = max(1, (n - block_size) // hop + 1)

    for i in range(total_blocks):
        start = i * hop
        end = min(start + block_size, n)
        if end - start < block_size:
            break

        progress = i / max(total_blocks - 1, 1)
        cutoff = start_freq + (end_freq - start_freq) * progress

        block = signal[start:start + block_size] * window
        spectrum = np.fft.rfft(block)
        freqs = np.fft.rfftfreq(block_size, d=1.0 / sample_rate)

        # 2nd-order Butterworth-style rolloff
        response = 1.0 / (1.0 + (freqs / max(cutoff, 1.0)) ** 4)
        spectrum *= response

        filtered = np.fft.irfft(spectrum, n=block_size)
        output[start:start + block_size] += filtered * window

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak

    return output


def _simple_reverb(
    signal: np.ndarray,
    amount: float = 0.3,
    decay_s: float = 0.5,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Simple convolution reverb using exponentially decaying noise."""
    if amount <= 0:
        return signal

    n_ir = int(decay_s * sample_rate)
    rng = np.random.default_rng(777)
    ir = rng.normal(0, 1, n_ir)
    ir *= np.exp(-np.linspace(0, 8, n_ir))
    ir /= np.max(np.abs(ir))

    # Convolve (trim to original length)
    wet = np.convolve(signal, ir, mode="full")[:len(signal)]
    peak = np.max(np.abs(wet))
    if peak > 0:
        wet /= peak

    return signal * (1 - amount) + wet * amount


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_riser(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize a riser: filtered white noise sweep from low → high.
    Gain follows phi-exponential curve (quiet start → loud finish).
    """
    n = int(preset.duration_s * sample_rate)

    # White noise source
    rng = np.random.default_rng(123)
    noise = rng.normal(0, 1, n)

    # Sweeping lowpass filter
    signal = _lowpass_sweep(noise, preset.start_freq, preset.end_freq, sample_rate)

    # Phi-exponential gain curve: quiet start → loud finish
    progress = np.linspace(0, 1, n)
    gain_curve = progress ** (1.0 / PHI)  # phi-shaped rise
    signal *= gain_curve

    # Optional distortion for grit
    if preset.distortion > 0:
        drive = 1.0 + preset.distortion * 6.0
        signal = np.tanh(signal * drive)

    # Reverb tail
    signal = _simple_reverb(signal, preset.reverb_amount, 0.3, sample_rate)

    # Final normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95

    return signal


def synthesize_impact(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize an impact: sub thump + bright transient + noise tail.
    The sound that hits on beat 1 of every Subtronics drop.
    """
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # --- Layer 1: Sub thump (pitched down sine with fast decay) ---
    sub_env = np.exp(-t * 8.0)  # fast decay
    # Pitch envelope: starts higher, drops to sub_freq
    pitch_env = preset.sub_freq * (1.0 + 3.0 * np.exp(-t * 20.0))
    phase = np.cumsum(pitch_env / sample_rate) * 2 * math.pi
    sub = np.sin(phase) * sub_env * 0.9

    # --- Layer 2: Bright transient click ---
    transient_dur = int(0.01 * sample_rate)  # 10ms click
    transient = np.zeros(n)
    if transient_dur > 0:
        rng = np.random.default_rng(456)
        click = rng.normal(0, 1, min(transient_dur, n))
        click *= np.exp(-np.linspace(0, 10, len(click)))
        transient[:len(click)] = click * preset.transient_brightness

    # --- Layer 3: Noise tail (reverbed crash-like decay) ---
    rng2 = np.random.default_rng(789)
    tail_noise = rng2.normal(0, 1, n)
    tail_env = np.exp(-t * 4.0)  # slower decay
    tail = tail_noise * tail_env * 0.3

    # Combine layers
    signal = sub + transient + tail

    # Distortion
    if preset.distortion > 0:
        drive = 1.0 + preset.distortion * 4.0
        signal = np.tanh(signal * drive)

    # Reverb
    signal = _simple_reverb(signal, preset.reverb_amount, 0.6, sample_rate)

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95

    return signal


def synthesize_subdrop(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize a sub drop: descending sine pitch sweep.
    Classic dubstep transition sound — pitch dives from ~120 Hz to ~25 Hz.
    Uses phi-curve for the pitch descent.
    """
    n = int(preset.duration_s * sample_rate)
    progress = np.linspace(0, 1, n)

    # Phi-curved pitch descent: fast at start, slows at bottom
    phi_curve = 1.0 - progress ** PHI
    freq_curve = preset.drop_end_freq + (preset.drop_start_freq - preset.drop_end_freq) * phi_curve

    # Generate sine with instantaneous frequency
    phase = np.cumsum(freq_curve / sample_rate) * 2 * math.pi
    signal = np.sin(phase)

    # Amplitude envelope: sustain then fade
    env = np.ones(n)
    fade_start = int(0.7 * n)  # fade starts at 70%
    fade_len = n - fade_start
    if fade_len > 0:
        env[fade_start:] = np.exp(-np.linspace(0, 5, fade_len))
    signal *= env

    # Add subtle harmonics for warmth
    harmonic2 = np.sin(phase * 2) * 0.15
    harmonic3 = np.sin(phase * 3) * 0.05
    signal = signal + harmonic2 + harmonic3

    # Slight distortion for weight
    if preset.distortion > 0:
        drive = 1.0 + preset.distortion * 3.0
        signal = np.tanh(signal * drive)

    # Reverb
    signal = _simple_reverb(signal, preset.reverb_amount, 0.4, sample_rate)

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95

    return signal


def synthesize_fx(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct synthesizer based on fx_type."""
    synthesizers = {
        "riser": synthesize_riser,
        "impact": synthesize_impact,
        "subdrop": synthesize_subdrop,
    }
    fn = synthesizers.get(preset.fx_type)
    if fn is None:
        raise ValueError(f"Unknown fx_type: {preset.fx_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — Subtronics-calibrated FX
# ═══════════════════════════════════════════════════════════════════════════

def riser_presets() -> FXBank:
    """Riser variants for build sections."""
    return FXBank(
        name="RISERS",
        presets=[
            FXPreset("riser_8bar", "riser", duration_s=8 * (4 * 60 / DEFAULT_BPM),
                     start_freq=150, end_freq=14000, distortion=0.1, reverb_amount=0.2),
            FXPreset("riser_4bar", "riser", duration_s=4 * (4 * 60 / DEFAULT_BPM),
                     start_freq=200, end_freq=12000, distortion=0.2, reverb_amount=0.3),
            FXPreset("riser_2bar_bright", "riser", duration_s=2 * (4 * 60 / DEFAULT_BPM),
                     start_freq=500, end_freq=16000, distortion=0.3, reverb_amount=0.15),
        ],
    )


def impact_presets() -> FXBank:
    """Impact variants for drop entrances."""
    return FXBank(
        name="IMPACTS",
        presets=[
            FXPreset("impact_sub_heavy", "impact", duration_s=1.5,
                     sub_freq=40, transient_brightness=1.0,
                     distortion=0.2, reverb_amount=0.4),
            FXPreset("impact_tight", "impact", duration_s=0.8,
                     sub_freq=55, transient_brightness=0.6,
                     distortion=0.1, reverb_amount=0.2),
            FXPreset("impact_dark", "impact", duration_s=2.0,
                     sub_freq=35, transient_brightness=0.4,
                     distortion=0.4, reverb_amount=0.6),
        ],
    )


def subdrop_presets() -> FXBank:
    """Sub drop variants for transitions."""
    return FXBank(
        name="SUB_DROPS",
        presets=[
            FXPreset("subdrop_classic", "subdrop", duration_s=1.0,
                     drop_start_freq=120, drop_end_freq=25,
                     distortion=0.1, reverb_amount=0.2),
            FXPreset("subdrop_long", "subdrop", duration_s=2.0,
                     drop_start_freq=150, drop_end_freq=20,
                     distortion=0.0, reverb_amount=0.3),
            FXPreset("subdrop_dirty", "subdrop", duration_s=0.8,
                     drop_start_freq=100, drop_end_freq=30,
                     distortion=0.5, reverb_amount=0.15),
        ],
    )


ALL_FX_BANKS: dict[str, callable] = {
    "risers":    riser_presets,
    "impacts":   impact_presets,
    "subdrops":  subdrop_presets,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_fx_manifest(banks: dict[str, FXBank], out_dir: str) -> str:
    """Write JSON manifest of all generated FX files."""
    manifest = {
        "generator": "DUBFORGE FX Generator",
        "sample_rate": SAMPLE_RATE,
        "bpm": DEFAULT_BPM,
        "banks": {},
    }
    for bank_name, bank in banks.items():
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [
                {
                    "name": p.name,
                    "type": p.fx_type,
                    "duration_s": round(p.duration_s, 3),
                    "wav_file": f"fx_{p.name}.wav",
                }
                for p in bank.presets
            ],
        }

    manifest_path = Path(out_dir) / "fx_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Wrote FX manifest: %s", manifest_path.name)
    return str(manifest_path)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    wav_dir = Path("output/wavetables")
    analysis_dir = Path("output/analysis")

    banks: dict[str, FXBank] = {}
    total_wavs = 0

    for bank_name, gen_fn in ALL_FX_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        print(f"  FX Bank: {bank.name} ({len(bank.presets)} presets)")

        for preset in bank.presets:
            signal = synthesize_fx(preset)
            wav_path = wav_dir / f"fx_{preset.name}.wav"
            _write_wav_raw(signal, str(wav_path))
            total_wavs += 1

    # Manifest
    write_fx_manifest(banks, str(analysis_dir))

    print(f"FX Generator complete — {total_wavs} WAVs across {len(banks)} banks.")


if __name__ == "__main__":
    main()
