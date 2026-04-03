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
from engine.accel import fft, ifft, convolve, write_wav

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
    """Delegates to engine.audio_mmap.write_wav_fast."""
    out_path = Path(path)
    write_wav(str(out_path), signal, sample_rate=sample_rate)
    n = len(signal)
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
        spectrum = fft(block)
        freqs = np.fft.rfftfreq(block_size, d=1.0 / sample_rate)

        # 2nd-order Butterworth-style rolloff
        response = 1.0 / (1.0 + (freqs / max(cutoff, 1.0)) ** 4)
        spectrum *= response

        filtered = ifft(spectrum, n=block_size)
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
    wet = convolve(signal, ir, mode="full")[:len(signal)]
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


def synthesize_downlifter(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Downlifter — high→low filtered noise sweep (reverse riser)."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 1, n)

    progress = np.linspace(0, 1, n)
    phi_curve = (1 - progress) ** PHI
    freq_sweep = preset.end_freq + (preset.start_freq - preset.end_freq) * phi_curve

    signal = np.zeros(n)
    y1 = 0.0
    for i in range(n):
        alpha = min(0.99, max(0.001, freq_sweep[i] / (sample_rate / 2)))
        y1 = y1 * (1 - alpha) + noise[i] * alpha
        signal[i] = y1

    signal *= (1 - progress * 0.8) ** (1 / PHI)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_siren(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Siren — oscillating pitch tone for tension and movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    center = preset.start_freq
    depth = preset.end_freq
    lfo_rate = PHI
    freq_mod = center + depth * np.sin(2 * math.pi * lfo_rate * t)

    phase = np.cumsum(2 * math.pi * freq_mod / sample_rate)
    signal = np.sin(phase)
    signal += 0.3 * np.sin(phase * 2)
    signal += 0.15 * np.sin(phase * 3)

    attack = max(1, int(0.05 * n))
    release = max(1, int(0.15 * n))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_drone(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Drone — sustained tension tone with slow movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    freq1 = preset.start_freq
    freq2 = freq1 * (1 + 0.005)
    signal = 0.5 * np.sin(2 * math.pi * freq1 * t)
    signal += 0.5 * np.sin(2 * math.pi * freq2 * t)

    if preset.sub_freq > 0:
        signal += 0.3 * np.sin(2 * math.pi * preset.sub_freq * t)

    am = 0.7 + 0.3 * np.sin(2 * math.pi * (1 / PHI) * t)
    signal *= am

    attack = max(1, int(0.1 * n))
    release = max(1, int(0.2 * n))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_texture(preset: FXPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Texture — metallic resonance via comb-filtered noise."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(77)
    noise = rng.normal(0, 1, n)

    delay = max(1, int(sample_rate / max(preset.start_freq, 20)))
    signal = np.zeros(n)
    for i in range(n):
        fb = signal[i - delay] if i >= delay else 0.0
        signal[i] = noise[i] + 0.7 * fb

    brightness = preset.transient_brightness
    alpha = min(0.99, brightness * 0.5 + 0.01)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    env_a = max(1, int(0.005 * n))
    env_d = max(1, int(0.3 * n))
    env = np.zeros(n)
    env[:env_a] = np.linspace(0, 1, env_a)
    tail_start = env_a + env_d
    if tail_start < n:
        env[env_a:tail_start] = np.linspace(1, 0.1, env_d)
        remaining = n - tail_start
        env[tail_start:] = 0.1 * np.exp(-np.arange(remaining) / max(1, n * 0.2))
    else:
        env[env_a:] = np.linspace(1, 0, n - env_a)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 6))

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
        "downlifter": synthesize_downlifter,
        "siren": synthesize_siren,
        "drone": synthesize_drone,
        "texture": synthesize_texture,
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


def downlifter_presets() -> FXBank:
    """Downlifter variants — high→low sweeps for section endings."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="DOWNLIFTERS",
        presets=[
            FXPreset("downlifter_8bar", "downlifter", duration_s=8 * bar_s,
                     start_freq=14000, end_freq=150, distortion=0.1, reverb_amount=0.2),
            FXPreset("downlifter_4bar", "downlifter", duration_s=4 * bar_s,
                     start_freq=12000, end_freq=200, distortion=0.15, reverb_amount=0.25),
            FXPreset("downlifter_2bar", "downlifter", duration_s=2 * bar_s,
                     start_freq=10000, end_freq=300, distortion=0.2, reverb_amount=0.15),
            FXPreset("downlifter_quick", "downlifter", duration_s=bar_s,
                     start_freq=8000, end_freq=500, distortion=0.3, reverb_amount=0.1),
        ],
    )


def siren_presets() -> FXBank:
    """Siren FX — oscillating pitch tones for tension."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="SIRENS",
        presets=[
            FXPreset("siren_rise", "siren", duration_s=4 * bar_s,
                     start_freq=800, end_freq=600, distortion=0.2, reverb_amount=0.3),
            FXPreset("siren_fast", "siren", duration_s=2 * bar_s,
                     start_freq=1200, end_freq=800, distortion=0.3, reverb_amount=0.2),
            FXPreset("siren_low", "siren", duration_s=4 * bar_s,
                     start_freq=400, end_freq=300, distortion=0.1, reverb_amount=0.4),
            FXPreset("siren_aggressive", "siren", duration_s=2 * bar_s,
                     start_freq=1500, end_freq=1000, distortion=0.5, reverb_amount=0.15),
        ],
    )


def drone_presets() -> FXBank:
    """Drone variants — sustained tension tones."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="DRONES",
        presets=[
            FXPreset("drone_dark", "drone", duration_s=8 * bar_s,
                     start_freq=80, sub_freq=40, distortion=0.1, reverb_amount=0.5),
            FXPreset("drone_mid", "drone", duration_s=8 * bar_s,
                     start_freq=200, sub_freq=100, distortion=0.2, reverb_amount=0.4),
            FXPreset("drone_high", "drone", duration_s=4 * bar_s,
                     start_freq=500, sub_freq=250, distortion=0.15, reverb_amount=0.3),
            FXPreset("drone_menacing", "drone", duration_s=8 * bar_s,
                     start_freq=60, sub_freq=30, distortion=0.4, reverb_amount=0.6),
        ],
    )


def texture_presets() -> FXBank:
    """Texture variants — metallic hits and noise bursts."""
    return FXBank(
        name="TEXTURES",
        presets=[
            FXPreset("texture_metallic", "texture", duration_s=0.5,
                     start_freq=2000, transient_brightness=0.9,
                     distortion=0.2, reverb_amount=0.4),
            FXPreset("texture_noise_burst", "texture", duration_s=0.3,
                     start_freq=5000, transient_brightness=0.7,
                     distortion=0.1, reverb_amount=0.2),
            FXPreset("texture_bell", "texture", duration_s=1.0,
                     start_freq=800, transient_brightness=0.5,
                     distortion=0.0, reverb_amount=0.6),
            FXPreset("texture_industrial", "texture", duration_s=0.4,
                     start_freq=3000, transient_brightness=1.0,
                     distortion=0.5, reverb_amount=0.15),
        ],
    )


def big_impact_presets() -> FXBank:
    """Big impact variants — layered heavyweight hits."""
    return FXBank(
        name="BIG_IMPACTS",
        presets=[
            FXPreset("impact_mega", "impact", duration_s=3.0,
                     sub_freq=30, transient_brightness=1.0,
                     distortion=0.5, reverb_amount=0.7),
            FXPreset("impact_crisp", "impact", duration_s=1.0,
                     sub_freq=60, transient_brightness=0.9,
                     distortion=0.3, reverb_amount=0.3),
            FXPreset("impact_room", "impact", duration_s=2.5,
                     sub_freq=45, transient_brightness=0.7,
                     distortion=0.1, reverb_amount=0.8),
            FXPreset("impact_808", "impact", duration_s=1.5,
                     sub_freq=35, transient_brightness=0.5,
                     distortion=0.4, reverb_amount=0.4),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# v1.9 — 10 new FX presets (3 banks)
# ═══════════════════════════════════════════════════════════════════════════

def long_riser_presets() -> FXBank:
    """Extended risers — 16/32 bar builds with slow filter sweep."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="LONG_RISERS",
        presets=[
            FXPreset("riser_16bar_wide", "riser", duration_s=16 * bar_s,
                     start_freq=80, end_freq=16000, distortion=0.05,
                     reverb_amount=0.4),
            FXPreset("riser_32bar_epic", "riser", duration_s=32 * bar_s,
                     start_freq=60, end_freq=14000, distortion=0.08,
                     reverb_amount=0.5),
            FXPreset("riser_16bar_gritty", "riser", duration_s=16 * bar_s,
                     start_freq=120, end_freq=12000, distortion=0.4,
                     reverb_amount=0.25),
        ],
    )


def cinematic_impact_presets() -> FXBank:
    """Cinematic impacts — deep, boomy, reverb-heavy hits."""
    return FXBank(
        name="CINEMATIC_IMPACTS",
        presets=[
            FXPreset("cinematic_boom", "impact", duration_s=4.0,
                     sub_freq=25, transient_brightness=0.6,
                     distortion=0.2, reverb_amount=0.9),
            FXPreset("cinematic_crack", "impact", duration_s=2.0,
                     sub_freq=35, transient_brightness=1.0,
                     distortion=0.3, reverb_amount=0.7),
            FXPreset("cinematic_rumble", "impact", duration_s=5.0,
                     sub_freq=20, transient_brightness=0.3,
                     distortion=0.1, reverb_amount=0.95),
            FXPreset("cinematic_punch", "impact", duration_s=1.5,
                     sub_freq=50, transient_brightness=0.9,
                     distortion=0.4, reverb_amount=0.5),
        ],
    )


def dark_drone_presets() -> FXBank:
    """Dark drone variants — ominous sustained textures."""
    return FXBank(
        name="DARK_DRONES",
        presets=[
            FXPreset("drone_abyss", "drone", duration_s=8.0,
                     start_freq=30, end_freq=60, distortion=0.3,
                     reverb_amount=0.8),
            FXPreset("drone_void", "drone", duration_s=10.0,
                     start_freq=40, end_freq=40, distortion=0.5,
                     reverb_amount=0.9),
            FXPreset("drone_pressure", "drone", duration_s=6.0,
                     start_freq=50, end_freq=80, distortion=0.4,
                     reverb_amount=0.6),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# v2.1 — 12 new FX presets (3 banks)
# ═══════════════════════════════════════════════════════════════════════════

def laser_presets() -> FXBank:
    """Laser / zap FX — fast siren sweeps for sci-fi transitions."""
    return FXBank(
        name="LASERS",
        presets=[
            FXPreset("laser_zap", "siren", duration_s=0.15,
                     start_freq=4000, end_freq=200, distortion=0.4,
                     reverb_amount=0.1),
            FXPreset("laser_pew", "siren", duration_s=0.1,
                     start_freq=6000, end_freq=400, distortion=0.5,
                     reverb_amount=0.05),
            FXPreset("laser_beam", "siren", duration_s=0.3,
                     start_freq=3000, end_freq=800, distortion=0.3,
                     reverb_amount=0.2),
            FXPreset("laser_blaster", "siren", duration_s=0.2,
                     start_freq=5000, end_freq=300, distortion=0.6,
                     reverb_amount=0.15),
        ],
    )


def sweep_presets() -> FXBank:
    """Wide sweep FX — full-spectrum risers for dramatic builds."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="SWEEPS",
        presets=[
            FXPreset("sweep_full_up", "riser", duration_s=8 * bar_s,
                     start_freq=20, end_freq=20000, distortion=0.05,
                     reverb_amount=0.5),
            FXPreset("sweep_full_down", "riser", duration_s=8 * bar_s,
                     start_freq=18000, end_freq=30, distortion=0.08,
                     reverb_amount=0.4),
            FXPreset("sweep_narrow_hi", "riser", duration_s=4 * bar_s,
                     start_freq=5000, end_freq=18000, distortion=0.1,
                     reverb_amount=0.35),
            FXPreset("sweep_sub_to_top", "riser", duration_s=16 * bar_s,
                     start_freq=25, end_freq=16000, distortion=0.03,
                     reverb_amount=0.6),
        ],
    )


def alarm_presets() -> FXBank:
    """Alarm FX — repeating siren tones for urgency and tension."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="ALARMS",
        presets=[
            FXPreset("alarm_hi_lo", "siren", duration_s=4 * bar_s,
                     start_freq=1800, end_freq=900, distortion=0.2,
                     reverb_amount=0.25),
            FXPreset("alarm_rapid", "siren", duration_s=2 * bar_s,
                     start_freq=2200, end_freq=1800, distortion=0.35,
                     reverb_amount=0.15),
            FXPreset("alarm_slow_pulse", "siren", duration_s=8 * bar_s,
                     start_freq=1000, end_freq=600, distortion=0.1,
                     reverb_amount=0.4),
            FXPreset("alarm_emergency", "siren", duration_s=4 * bar_s,
                     start_freq=2500, end_freq=1200, distortion=0.45,
                     reverb_amount=0.2),
        ],
    )


def wobble_fx_presets() -> FXBank:
    """Wobble FX — low-frequency modulated textures for drops."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="WOBBLE_FX",
        presets=[
            FXPreset("wobble_slow_drone", "drone", duration_s=8 * bar_s,
                     start_freq=60, end_freq=60, distortion=0.3,
                     reverb_amount=0.4),
            FXPreset("wobble_mid_texture", "texture", duration_s=4 * bar_s,
                     start_freq=200, end_freq=800, distortion=0.2,
                     reverb_amount=0.3),
            FXPreset("wobble_sub_pulse", "subdrop", duration_s=4 * bar_s,
                     start_freq=40, end_freq=25, distortion=0.1,
                     reverb_amount=0.5),
            FXPreset("wobble_siren_lfo", "siren", duration_s=8 * bar_s,
                     start_freq=400, end_freq=200, distortion=0.15,
                     reverb_amount=0.35),
        ],
    )


def stutter_fx_presets() -> FXBank:
    """Stutter FX — glitchy repeated impact textures."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="STUTTER_FX",
        presets=[
            FXPreset("stutter_impact_1", "impact", duration_s=2 * bar_s,
                     start_freq=80, end_freq=80, distortion=0.5,
                     reverb_amount=0.2),
            FXPreset("stutter_impact_2", "impact", duration_s=bar_s,
                     start_freq=120, end_freq=120, distortion=0.6,
                     reverb_amount=0.15),
            FXPreset("stutter_riser", "riser", duration_s=4 * bar_s,
                     start_freq=200, end_freq=4000, distortion=0.3,
                     reverb_amount=0.3),
            FXPreset("stutter_downlift", "downlifter", duration_s=2 * bar_s,
                     start_freq=3000, end_freq=100, distortion=0.4,
                     reverb_amount=0.25),
        ],
    )


def feedback_fx_presets() -> FXBank:
    """Feedback FX — resonant self-oscillating textures."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return FXBank(
        name="FEEDBACK_FX",
        presets=[
            FXPreset("fb_drone_low", "drone", duration_s=8 * bar_s,
                     start_freq=50, end_freq=50, distortion=0.6,
                     reverb_amount=0.5),
            FXPreset("fb_siren_high", "siren", duration_s=4 * bar_s,
                     start_freq=3000, end_freq=1000, distortion=0.7,
                     reverb_amount=0.3),
            FXPreset("fb_texture_mid", "texture", duration_s=4 * bar_s,
                     start_freq=500, end_freq=2000, distortion=0.5,
                     reverb_amount=0.4),
            FXPreset("fb_subdrop_deep", "subdrop", duration_s=4 * bar_s,
                     start_freq=30, end_freq=15, distortion=0.4,
                     reverb_amount=0.6),
        ],
    )


ALL_FX_BANKS: dict[str, callable] = {
    "risers":      riser_presets,
    "impacts":     impact_presets,
    "subdrops":    subdrop_presets,
    "downlifters": downlifter_presets,
    "sirens":      siren_presets,
    "drones":      drone_presets,
    "textures":    texture_presets,
    "big_impacts": big_impact_presets,
    "long_risers": long_riser_presets,
    "cinematic_impacts": cinematic_impact_presets,
    "dark_drones": dark_drone_presets,
    # v2.1
    "laser":       laser_presets,
    "sweeps":      sweep_presets,
    "alarms":      alarm_presets,
    # v2.3
    "wobble_fx":   wobble_fx_presets,
    "stutter_fx":  stutter_fx_presets,
    "feedback_fx": feedback_fx_presets,
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
