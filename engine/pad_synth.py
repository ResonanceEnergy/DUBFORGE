"""
DUBFORGE Engine — Pad Synthesizer

Synthesizes atmospheric pad sounds for dubstep arrangements:
  - Lush Pad:    detuned saw layers with slow filter sweep
  - Dark Pad:    low-register drones with harmonic movement
  - Shimmer Pad: high-register pitched delays with sparkle
  - Evolving Pad: slow morphing texture via cross-faded waveforms
  - Choir Pad:   formant-filtered layers simulating vocal chords

All pads use phi-ratio timing for envelopes and LFO rates.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/pad_*.wav
    output/analysis/pad_synth_manifest.json

Based on Subtronics production analysis:
  - Lush pads underpin melodic bridges
  - Dark drones sustain tension under breakdowns
  - Shimmer textures accent atmospheric intros
  - Evolving pads create movement in transitions
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
from engine.accel import write_wav

_log = get_logger("dubforge.pad_synth")


def tq_compress_pad(
    signal: np.ndarray,
    label: str = "pad",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress pad synthesis output."""
    samples = signal.tolist()
    bits = phi_optimal_bits(len(samples))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(samples, label, cfg, sample_rate=sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PadPreset:
    """Settings for a single pad sound."""
    name: str
    pad_type: str           # lush | dark | shimmer | evolving | choir
    frequency: float        # fundamental in Hz
    duration_s: float = 4.0
    detune_cents: float = 10.0
    filter_cutoff: float = 0.5   # 0-1 normalised
    lfo_rate: float = 0.0        # Hz, 0 = auto (1/PHI)
    attack_s: float = 0.5
    release_s: float = 1.0
    reverb_amount: float = 0.4
    brightness: float = 0.5


@dataclass
class PadBank:
    """Collection of pad presets."""
    name: str
    presets: list[PadPreset] = field(default_factory=list)


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
    """Normalize signal to 0.95 peak."""
    peak = np.max(np.abs(signal))
    return signal / peak * 0.95 if peak > 0 else signal


def _apply_pad_envelope(signal: np.ndarray, preset: PadPreset,
                        sample_rate: int) -> np.ndarray:
    """Apply slow attack/release envelope."""
    n = len(signal)
    attack = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    if release < n:
        env[-release:] = np.linspace(1, 0, release)
    return signal * env


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_lush_pad(preset: PadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Lush pad — detuned saw layers with slow filter sweep.

    UPGRADED: Bandlimited saw voices, SVF lowpass with LFO modulation,
    chorus for stereo width.
    """
    from engine.dsp_core import (osc_saw_np, svf_lowpass,
                                 chorus as dsp_chorus)

    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    detune = 2 ** (preset.detune_cents / 1200)
    freqs = [preset.frequency, preset.frequency * detune,
             preset.frequency / detune]

    # Bandlimited saw voices
    signal = np.zeros(n)
    for f in freqs:
        signal += osc_saw_np(f, preset.duration_s, sample_rate) / 3.0

    # SVF lowpass with LFO modulation on cutoff
    lfo_r = preset.lfo_rate if preset.lfo_rate > 0 else 1 / PHI
    base_cutoff = 300 + preset.filter_cutoff * 4000
    cutoff_mod = base_cutoff + 1500 * np.sin(2 * math.pi * lfo_r * t)
    cutoff_mod = np.clip(cutoff_mod, 100, 10000)
    signal = svf_lowpass(signal, cutoff_mod, 0.2, sample_rate)

    # Chorus for lushness
    signal = dsp_chorus(signal, sample_rate, depth=0.004, rate=0.5, voices=4)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_dark_pad(preset: PadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Dark pad — low-register drone with harmonic movement.

    UPGRADED: Bandlimited detuned saw voices, white noise layer,
    SVF lowpass for darkness, chorus for width, Schroeder reverb for depth.
    """
    from engine.dsp_core import (osc_saw_np, svf_lowpass, white_noise,
                                 chorus as dsp_chorus, reverb_schroeder)

    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Three detuned bandlimited saw voices for richness
    detune = 2 ** (preset.detune_cents / 1200)
    sig1 = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)
    sig2 = osc_saw_np(preset.frequency * detune, preset.duration_s, sample_rate)
    sig3 = osc_saw_np(preset.frequency / detune, preset.duration_s, sample_rate)
    signal = (sig1 + sig2 + sig3) / 3.0

    # Noise layer for texture
    signal += white_noise(n) * 0.03

    # Slow amplitude modulation for organic movement
    am_rate = 1 / (PHI * 2)
    am = 0.7 + 0.3 * np.sin(2 * math.pi * am_rate * t)
    signal *= am

    # SVF lowpass for darkness (preset.filter_cutoff drives cutoff)
    cutoff_hz = 200 + preset.filter_cutoff * 1500
    signal = svf_lowpass(signal, cutoff_hz, 0.15, sample_rate)

    # Chorus for stereo width and thickness
    signal = dsp_chorus(signal, sample_rate, depth=0.003, rate=0.3, voices=3)

    # Reverb for depth (use preset.reverb_amount if available)
    rev_amt = getattr(preset, 'reverb_amount', 0.4)
    if rev_amt > 0:
        signal = reverb_schroeder(signal, sample_rate, decay=1.5, mix=rev_amt)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_shimmer_pad(preset: PadPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Shimmer pad — high-register sparkle with pitched delays.

    UPGRADED: Bandlimited saw voices at f/2f/3f, pitched octave delay,
    SVF highpass for shimmer, reverb for depth.
    """
    from engine.dsp_core import (osc_saw_np, svf_highpass,
                                 reverb_schroeder)

    n = int(preset.duration_s * sample_rate)

    # Layered bandlimited saws at fundamental + octave + 5th
    signal = 0.5 * osc_saw_np(preset.frequency, preset.duration_s, sample_rate)
    signal += 0.35 * osc_saw_np(preset.frequency * 2, preset.duration_s, sample_rate)
    signal += 0.2 * osc_saw_np(preset.frequency * 3, preset.duration_s, sample_rate)

    # Pitch-shifted delay (octave up shimmer effect)
    delay_samples = max(1, int(sample_rate * (1 / PHI)))
    delayed = np.zeros(n)
    if delay_samples < n:
        delayed[delay_samples:] = signal[:-delay_samples] * 0.4
    signal += delayed

    # SVF highpass for shimmer brightness
    hp_cutoff = 500 + preset.brightness * 2000
    signal = svf_highpass(signal, hp_cutoff, 0.1, sample_rate)

    # Reverb for ethereal depth
    rev_amt = getattr(preset, 'reverb_amount', 0.5)
    if rev_amt > 0:
        signal = reverb_schroeder(signal, sample_rate, decay=2.0, mix=rev_amt)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_evolving_pad(preset: PadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Evolving pad — cross-fading waveform morph.

    UPGRADED: Bandlimited saw via osc_saw_np, SVF filter sweep
    instead of single-pole, chorus for width.
    """
    from engine.dsp_core import osc_saw_np, svf_lowpass, chorus as dsp_chorus

    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Morph between sine → bandlimited saw over time
    progress = np.linspace(0, 1, n)
    sine = np.sin(2 * math.pi * preset.frequency * t)
    saw = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)

    # Phi-timed crossfade
    morph = progress ** (1 / PHI)
    signal = sine * (1 - morph) + saw * morph

    # Detuned doubler (bandlimited)
    detune = 2 ** (preset.detune_cents / 1200)
    doubler = osc_saw_np(preset.frequency * detune, preset.duration_s, sample_rate)
    signal = 0.7 * signal + 0.3 * doubler

    # SVF lowpass sweeping open with morph
    cutoff = 300 + 4000 * morph
    signal = svf_lowpass(signal, cutoff, 0.15, sample_rate)

    # Chorus for stereo width
    signal = dsp_chorus(signal, sample_rate, depth=0.003, rate=0.4, voices=3)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_choir_pad(preset: PadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Choir pad — formant-filtered layers simulating vocal tones.

    UPGRADED: Bandlimited saw source for rich harmonics,
    proper SVF bandpass at formant frequencies with resonance.
    """
    from engine.dsp_core import osc_saw_np, svf_bandpass

    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Bandlimited saw — provides all the harmonics needed for formant filtering
    source = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)

    # Proper SVF bandpass at vocal formant frequencies ('ah' vowel)
    formants = [730, 1090, 2440]
    signal = np.zeros(n)
    for fc in formants:
        signal += svf_bandpass(source, float(fc), 0.5, sample_rate) * 0.4

    # Sub fundamental for body
    signal += 0.25 * np.sin(2 * math.pi * preset.frequency * t)

    # Slow vibrato
    vib_depth = preset.frequency * 0.005
    phase_mod = vib_depth * np.sin(2 * math.pi * (1 / PHI) * t)
    signal *= (1 + 0.1 * np.sin(2 * math.pi * phase_mod))

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# v2.0 — 3 new pad types (12 presets)
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_glass_pad(preset: PadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Glass pad — crystalline bell-like harmonics with slow swell."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    signal = np.zeros(n)
    # Inharmonic partials at glass-bowl ratios
    ratios = [1.0, 2.76, 5.4, 8.93, 13.34]
    for i, r in enumerate(ratios):
        freq = preset.frequency * r
        if freq > sample_rate / 2:
            break
        amp = 0.4 / (i + 1) ** 0.8
        signal += amp * np.sin(2 * math.pi * freq * t)

    # Slow brightness swell
    swell = np.linspace(0.2, preset.brightness, n) ** PHI
    y = 0.0
    for i in range(n):
        a = max(0.01, swell[i] * 0.6)
        y = y * (1 - a) + signal[i] * a
        signal[i] = y

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_warm_pad(preset: PadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Warm pad — analog-style detuned saw layers with chorus.

    UPGRADED: Bandlimited saw voices, SVF lowpass for warmth, chorus.
    """
    from engine.dsp_core import (osc_saw_np, svf_lowpass,
                                 chorus as dsp_chorus)

    n = int(preset.duration_s * sample_rate)

    # Detuned bandlimited saw voices for analog warmth
    detune = 2 ** (preset.detune_cents / 1200)
    sig1 = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)
    sig2 = osc_saw_np(preset.frequency * detune, preset.duration_s, sample_rate)
    sig3 = osc_saw_np(preset.frequency / detune, preset.duration_s, sample_rate)
    signal = (sig1 * 0.5 + sig2 * 0.25 + sig3 * 0.25)

    # SVF lowpass for warmth
    cutoff_hz = 300 + preset.filter_cutoff * 3000
    signal = svf_lowpass(signal, cutoff_hz, 0.15, sample_rate)

    # Chorus for stereo width
    signal = dsp_chorus(signal, sample_rate, depth=0.004, rate=0.5, voices=4)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_granular_pad(preset: PadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Granular pad — cloud of micro-grains with pitch scatter."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(999)

    signal = np.zeros(n)
    grain_size = int(0.03 * sample_rate)  # 30ms grains
    num_grains = int(preset.duration_s * 40 * max(0.1, preset.brightness))

    for _ in range(num_grains):
        pos = rng.integers(0, max(1, n - grain_size))
        pitch_scatter = preset.frequency * (1 + rng.uniform(-0.05, 0.05)
                                            * preset.detune_cents / 10)
        g_t = np.arange(grain_size) / sample_rate
        grain = np.sin(2 * math.pi * pitch_scatter * g_t)
        # Hann window
        window = 0.5 * (1 - np.cos(2 * math.pi * np.arange(grain_size)
                                    / grain_size))
        grain *= window * rng.uniform(0.3, 0.8)
        end = min(n, pos + grain_size)
        signal[pos:end] += grain[:end - pos]

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_crystal_pad(preset: PadPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Crystal pad — bell-like tones with high harmonic shimmer."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Bell-like partials at non-integer ratios
    ratios = [1.0, 2.76, 4.17, 5.43, 7.89]
    amps = [1.0, 0.5, 0.3, 0.15, 0.08]
    signal = np.zeros(n)
    for ratio, amp in zip(ratios, amps):
        freq = preset.frequency * ratio
        if freq < sample_rate / 2:
            signal += amp * np.sin(2 * math.pi * freq * t)

    # High shimmer via amplitude modulation
    shimmer = 1.0 + preset.brightness * 0.3 * np.sin(
        2 * math.pi * preset.lfo_rate * PHI * t
    )
    signal *= shimmer
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_metallic_pad(preset: PadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Metallic pad — inharmonic resonant tones."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Metallic inharmonic partials
    ratios = [1.0, 1.414, 2.236, 3.162, 4.583]  # sqrt-based inharmonic
    amps = [1.0, 0.6, 0.4, 0.25, 0.12]
    signal = np.zeros(n)
    for ratio, amp in zip(ratios, amps):
        freq = preset.frequency * ratio
        if freq < sample_rate / 2:
            phase_offset = ratio * 0.5  # phase separation
            signal += amp * np.sin(
                2 * math.pi * freq * t + phase_offset
            )

    # Slow resonance modulation
    mod = 1.0 + 0.2 * np.sin(2 * math.pi * preset.lfo_rate * t)
    signal *= mod
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_noise_pad(preset: PadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Noise pad — filtered noise with tonal coloring.

    UPGRADED: Pink noise source, SVF bandpass at fundamental, reverb.
    """
    from engine.dsp_core import pink_noise, svf_bandpass, reverb_schroeder

    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Pink noise (more natural than white)
    noise = pink_noise(n)

    # SVF bandpass around fundamental for tonal coloring
    signal = svf_bandpass(noise, preset.frequency * 2, 0.3, sample_rate)

    # Add tonal reference sine
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * t)

    # LFO modulation
    mod = 1.0 + 0.15 * np.sin(2 * math.pi * preset.lfo_rate * t)
    signal *= mod

    # Reverb for space
    signal = reverb_schroeder(signal, sample_rate, decay=1.8, mix=0.4)

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_spectral_pad(preset: PadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Spectral pad — sparse harmonic spectrum with slow drift."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Use prime-numbered harmonics for unique color
    primes = [1, 2, 3, 5, 7, 11, 13]
    signal = np.zeros(n)
    for p in primes:
        freq = preset.frequency * p
        if freq > sample_rate / 2:
            break
        amp = 0.8 / p
        # Slow drift per harmonic
        drift = np.sin(2 * math.pi * preset.lfo_rate * p * 0.1 * t)
        signal += amp * np.sin(2 * math.pi * freq * t + drift * 0.5)

    mod = 1.0 + 0.1 * np.sin(2 * math.pi * preset.lfo_rate * t)
    signal *= mod
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_vocal_pad(preset: PadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Vocal pad — formant-like resonances for breathy texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich harmonics
    source = np.zeros(n)
    for h in range(1, 12):
        source += (0.7 ** h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Three formant resonances (vowel-like)
    formants = [500, 1500, 2500]
    signal = np.zeros(n)
    for ff in formants:
        alpha = min(0.99, ff / sample_rate * 2 * math.pi)
        y = 0.0
        for i in range(n):
            y = y * (1 - alpha) + source[i] * alpha
            signal[i] += y * 0.33

    mod = 1.0 + 0.1 * np.sin(2 * math.pi * preset.lfo_rate * t)
    signal *= mod
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_ambient_pad(preset: PadPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ambient pad — soft evolving ambient wash."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    lfo = preset.lfo_rate if preset.lfo_rate > 0 else 1.0 / PHI
    signal = np.zeros(n)
    for i in range(5):
        detune = preset.detune_cents * (i - 2) / 1200
        f = preset.frequency * (1 + detune)
        signal += np.sin(2 * math.pi * f * t) * (1.0 / (i + 1))
    mod = 0.7 + 0.3 * np.sin(2 * math.pi * lfo * t)
    signal *= mod * preset.brightness
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_fm_pad(preset: PadPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM pad — frequency modulated bell-like texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    lfo = preset.lfo_rate if preset.lfo_rate > 0 else 1.0 / PHI
    mod_freq = preset.frequency * PHI
    mod_index = 2.0 * preset.brightness
    modulator = np.sin(2 * math.pi * mod_freq * t) * mod_index
    signal = np.sin(2 * math.pi * preset.frequency * t + modulator)
    detune = preset.detune_cents / 1200
    signal += 0.5 * np.sin(2 * math.pi * preset.frequency * (1 + detune) * t + modulator * 0.5)
    signal *= 0.5
    signal *= 0.8 + 0.2 * np.sin(2 * math.pi * lfo * t)
    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_pad(preset: PadPreset,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct pad synthesizer."""
    synthesizers = {
        "lush": synthesize_lush_pad,
        "dark": synthesize_dark_pad,
        "shimmer": synthesize_shimmer_pad,
        "evolving": synthesize_evolving_pad,
        "choir": synthesize_choir_pad,
        "glass": synthesize_glass_pad,
        "warm": synthesize_warm_pad,
        "granular": synthesize_granular_pad,
        "crystal": synthesize_crystal_pad,
        "metallic": synthesize_metallic_pad,
        "noise": synthesize_noise_pad,
        "spectral": synthesize_spectral_pad,
        "vocal": synthesize_vocal_pad,
        # v2.4
        "ambient_pad": synthesize_ambient_pad,
        "fm_pad": synthesize_fm_pad,
    }
    fn = synthesizers.get(preset.pad_type)
    if fn is None:
        raise ValueError(f"Unknown pad_type: {preset.pad_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 Subtronics-inspired pad sounds
# ═══════════════════════════════════════════════════════════════════════════

def lush_pad_bank() -> PadBank:
    """Lush detuned saw pads at various registers."""
    return PadBank(
        name="LUSH_PADS",
        presets=[
            PadPreset("lush_C3", "lush", 128.43, duration_s=6.0,
                      detune_cents=12, filter_cutoff=0.4, attack_s=0.8),
            PadPreset("lush_E3", "lush", 161.81, duration_s=6.0,
                      detune_cents=15, filter_cutoff=0.5, attack_s=0.6),
            PadPreset("lush_G3", "lush", 192.44, duration_s=6.0,
                      detune_cents=10, filter_cutoff=0.6, attack_s=1.0),
            PadPreset("lush_A3", "lush", 216.00, duration_s=6.0,
                      detune_cents=18, filter_cutoff=0.35, attack_s=0.5),
        ],
    )


def dark_pad_bank() -> PadBank:
    """Dark low-register drone pads."""
    return PadBank(
        name="DARK_PADS",
        presets=[
            PadPreset("dark_C2", "dark", 65.41, duration_s=8.0,
                      detune_cents=8, filter_cutoff=0.2, attack_s=1.5),
            PadPreset("dark_D2", "dark", 73.42, duration_s=8.0,
                      detune_cents=10, filter_cutoff=0.15, attack_s=2.0),
            PadPreset("dark_E2", "dark", 82.41, duration_s=8.0,
                      detune_cents=6, filter_cutoff=0.25, attack_s=1.2),
            PadPreset("dark_F2", "dark", 87.31, duration_s=8.0,
                      detune_cents=12, filter_cutoff=0.1, attack_s=1.8),
        ],
    )


def shimmer_pad_bank() -> PadBank:
    """Shimmer pads — sparkly high textures."""
    return PadBank(
        name="SHIMMER_PADS",
        presets=[
            PadPreset("shimmer_C4", "shimmer", 256.87, duration_s=5.0,
                      brightness=0.8, attack_s=0.3),
            PadPreset("shimmer_E4", "shimmer", 323.64, duration_s=5.0,
                      brightness=0.9, attack_s=0.4),
            PadPreset("shimmer_G4", "shimmer", 384.87, duration_s=5.0,
                      brightness=0.7, attack_s=0.5),
            PadPreset("shimmer_A4", "shimmer", 432.00, duration_s=5.0,
                      brightness=1.0, attack_s=0.2),
        ],
    )


def evolving_pad_bank() -> PadBank:
    """Evolving pads — slow morphing textures."""
    return PadBank(
        name="EVOLVING_PADS",
        presets=[
            PadPreset("evolve_C3", "evolving", 128.43, duration_s=8.0,
                      detune_cents=15, filter_cutoff=0.3, attack_s=1.0),
            PadPreset("evolve_D3", "evolving", 146.83, duration_s=8.0,
                      detune_cents=12, filter_cutoff=0.4, attack_s=1.2),
            PadPreset("evolve_E3", "evolving", 161.81, duration_s=8.0,
                      detune_cents=20, filter_cutoff=0.25, attack_s=0.8),
            PadPreset("evolve_G3", "evolving", 192.44, duration_s=8.0,
                      detune_cents=10, filter_cutoff=0.35, attack_s=1.5),
        ],
    )


def choir_pad_bank() -> PadBank:
    """Choir pads — formant-filtered vocal textures."""
    return PadBank(
        name="CHOIR_PADS",
        presets=[
            PadPreset("choir_C3", "choir", 128.43, duration_s=6.0,
                      attack_s=0.6, brightness=0.6),
            PadPreset("choir_E3", "choir", 161.81, duration_s=6.0,
                      attack_s=0.8, brightness=0.7),
            PadPreset("choir_G3", "choir", 192.44, duration_s=6.0,
                      attack_s=0.5, brightness=0.5),
            PadPreset("choir_A3", "choir", 216.00, duration_s=6.0,
                      attack_s=0.7, brightness=0.8),
        ],
    )


def glass_pad_bank() -> PadBank:
    """Glass pads — crystalline bell-like tones."""
    return PadBank(
        name="GLASS_PADS",
        presets=[
            PadPreset("glass_C3", "glass", 128.43, duration_s=5.0,
                      brightness=0.8, filter_cutoff=0.7, attack_s=0.4),
            PadPreset("glass_E3", "glass", 161.81, duration_s=5.0,
                      brightness=0.9, filter_cutoff=0.8, attack_s=0.3),
            PadPreset("glass_G3", "glass", 192.44, duration_s=5.0,
                      brightness=0.7, filter_cutoff=0.6, attack_s=0.5),
            PadPreset("glass_A3", "glass", 216.00, duration_s=5.0,
                      brightness=1.0, filter_cutoff=0.9, attack_s=0.2),
        ],
    )


def warm_pad_bank() -> PadBank:
    """Warm pads — analog-style chorused triangles."""
    return PadBank(
        name="WARM_PADS",
        presets=[
            PadPreset("warm_C3", "warm", 128.43, duration_s=7.0,
                      detune_cents=15, filter_cutoff=0.3, attack_s=1.0),
            PadPreset("warm_D3", "warm", 146.83, duration_s=7.0,
                      detune_cents=12, filter_cutoff=0.25, attack_s=1.2),
            PadPreset("warm_E3", "warm", 161.81, duration_s=7.0,
                      detune_cents=18, filter_cutoff=0.35, attack_s=0.8),
            PadPreset("warm_G3", "warm", 192.44, duration_s=7.0,
                      detune_cents=10, filter_cutoff=0.2, attack_s=1.5),
        ],
    )


def granular_pad_bank() -> PadBank:
    """Granular pads — cloud-texture micro-grain ambience."""
    return PadBank(
        name="GRANULAR_PADS",
        presets=[
            PadPreset("granular_C3", "granular", 128.43, duration_s=6.0,
                      detune_cents=20, brightness=0.6, attack_s=0.5),
            PadPreset("granular_E3", "granular", 161.81, duration_s=6.0,
                      detune_cents=30, brightness=0.7, attack_s=0.6),
            PadPreset("granular_G3", "granular", 192.44, duration_s=6.0,
                      detune_cents=15, brightness=0.5, attack_s=0.8),
            PadPreset("granular_A3", "granular", 216.00, duration_s=6.0,
                      detune_cents=25, brightness=0.8, attack_s=0.4),
        ],
    )


def crystal_pad_bank() -> PadBank:
    """Crystal pads — bell-like shimmering tones."""
    return PadBank(
        name="CRYSTAL_PADS",
        presets=[
            PadPreset("crystal_C3", "crystal", 128.43, duration_s=5.0,
                      detune_cents=8, brightness=0.8, attack_s=0.3, lfo_rate=0.3),
            PadPreset("crystal_E3", "crystal", 161.81, duration_s=5.0,
                      detune_cents=12, brightness=0.9, attack_s=0.4, lfo_rate=0.25),
            PadPreset("crystal_G3", "crystal", 192.44, duration_s=5.0,
                      detune_cents=6, brightness=0.75, attack_s=0.35, lfo_rate=0.35),
            PadPreset("crystal_A3", "crystal", 216.00, duration_s=5.0,
                      detune_cents=10, brightness=0.85, attack_s=0.3, lfo_rate=0.2),
        ],
    )


def metallic_pad_bank() -> PadBank:
    """Metallic pads — inharmonic resonant tones."""
    return PadBank(
        name="METALLIC_PADS",
        presets=[
            PadPreset("metallic_C3", "metallic", 128.43, duration_s=5.0,
                      detune_cents=5, brightness=0.6, attack_s=0.4, lfo_rate=0.15),
            PadPreset("metallic_E3", "metallic", 161.81, duration_s=5.0,
                      detune_cents=8, brightness=0.5, attack_s=0.5, lfo_rate=0.2),
            PadPreset("metallic_G3", "metallic", 192.44, duration_s=5.0,
                      detune_cents=10, brightness=0.55, attack_s=0.45, lfo_rate=0.18),
            PadPreset("metallic_A3", "metallic", 216.00, duration_s=5.0,
                      detune_cents=7, brightness=0.65, attack_s=0.35, lfo_rate=0.22),
        ],
    )


def noise_pad_bank() -> PadBank:
    """Noise pads — filtered noise with tonal coloring."""
    return PadBank(
        name="NOISE_PADS",
        presets=[
            PadPreset("noise_C3", "noise", 128.43, duration_s=5.0,
                      brightness=0.6, attack_s=0.5, lfo_rate=0.15),
            PadPreset("noise_E3", "noise", 161.81, duration_s=5.0,
                      brightness=0.7, attack_s=0.4, lfo_rate=0.2),
            PadPreset("noise_G3", "noise", 192.44, duration_s=5.0,
                      brightness=0.5, attack_s=0.6, lfo_rate=0.1),
            PadPreset("noise_A3", "noise", 216.00, duration_s=5.0,
                      brightness=0.8, attack_s=0.45, lfo_rate=0.18),
        ],
    )


def spectral_pad_bank() -> PadBank:
    """Spectral pads — sparse prime-harmonic textures."""
    return PadBank(
        name="SPECTRAL_PADS",
        presets=[
            PadPreset("spectral_C3", "spectral", 128.43, duration_s=5.0,
                      brightness=0.7, attack_s=0.4, lfo_rate=0.12),
            PadPreset("spectral_E3", "spectral", 161.81, duration_s=5.0,
                      brightness=0.6, attack_s=0.5, lfo_rate=0.15),
            PadPreset("spectral_G3", "spectral", 192.44, duration_s=5.0,
                      brightness=0.8, attack_s=0.35, lfo_rate=0.1),
            PadPreset("spectral_A3", "spectral", 216.00, duration_s=5.0,
                      brightness=0.65, attack_s=0.45, lfo_rate=0.2),
        ],
    )


def vocal_pad_bank() -> PadBank:
    """Vocal pads — formant-like breathy textures."""
    return PadBank(
        name="VOCAL_PADS",
        presets=[
            PadPreset("vocal_C3", "vocal", 128.43, duration_s=5.0,
                      brightness=0.5, attack_s=0.5, lfo_rate=0.1),
            PadPreset("vocal_E3", "vocal", 161.81, duration_s=5.0,
                      brightness=0.6, attack_s=0.4, lfo_rate=0.15),
            PadPreset("vocal_G3", "vocal", 192.44, duration_s=5.0,
                      brightness=0.55, attack_s=0.55, lfo_rate=0.12),
            PadPreset("vocal_A3", "vocal", 216.00, duration_s=5.0,
                      brightness=0.7, attack_s=0.35, lfo_rate=0.18),
        ],
    )


def ambient_pad_bank() -> PadBank:
    """Ambient pads — soft evolving ambient washes."""
    return PadBank(
        name="AMBIENT_PADS",
        presets=[
            PadPreset("ambient_C3", "ambient_pad", 128.43, duration_s=6.0,
                      brightness=0.4, attack_s=1.0, lfo_rate=0.08),
            PadPreset("ambient_E3", "ambient_pad", 161.81, duration_s=5.0,
                      brightness=0.5, attack_s=0.8, lfo_rate=0.1),
            PadPreset("ambient_G3", "ambient_pad", 192.44, duration_s=7.0,
                      brightness=0.35, attack_s=1.2, lfo_rate=0.06),
            PadPreset("ambient_A3", "ambient_pad", 216.00, duration_s=5.0,
                      brightness=0.45, attack_s=0.9, lfo_rate=0.12),
        ],
    )


def fm_pad_bank() -> PadBank:
    """FM pads — frequency modulated bell-like textures."""
    return PadBank(
        name="FM_PADS",
        presets=[
            PadPreset("fm_pad_C3", "fm_pad", 128.43, duration_s=5.0,
                      brightness=0.6, attack_s=0.5, lfo_rate=0.1),
            PadPreset("fm_pad_E3", "fm_pad", 161.81, duration_s=4.0,
                      brightness=0.7, attack_s=0.4, lfo_rate=0.15),
            PadPreset("fm_pad_G3", "fm_pad", 192.44, duration_s=6.0,
                      brightness=0.5, attack_s=0.6, lfo_rate=0.08),
            PadPreset("fm_pad_A3", "fm_pad", 216.00, duration_s=5.0,
                      brightness=0.65, attack_s=0.45, lfo_rate=0.12),
        ],
    )


ALL_PAD_BANKS: dict[str, callable] = {
    "lush":     lush_pad_bank,
    "dark":     dark_pad_bank,
    "shimmer":  shimmer_pad_bank,
    "evolving": evolving_pad_bank,
    "choir":    choir_pad_bank,
    # v2.0
    "glass":    glass_pad_bank,
    "warm":     warm_pad_bank,
    "granular": granular_pad_bank,
    # v2.1
    "crystal":  crystal_pad_bank,
    "metallic": metallic_pad_bank,
    # v2.3
    "noise":    noise_pad_bank,
    "spectral": spectral_pad_bank,
    "vocal":    vocal_pad_bank,
    # v2.4
    "ambient_pad": ambient_pad_bank,
    "fm_pad":      fm_pad_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_pad_manifest(banks: dict[str, PadBank], out_dir: str) -> str:
    """Write JSON manifest of generated pad sounds."""
    manifest = {
        "generator": "DUBFORGE Pad Synthesizer",
        "sample_rate": SAMPLE_RATE,
        "banks": {},
    }
    for bank_name, bank in banks.items():
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [
                {
                    "name": p.name,
                    "type": p.pad_type,
                    "frequency": round(p.frequency, 2),
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "pad_synth_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote pad manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all pad WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, PadBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_PAD_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_pad(preset)
            path = f"{wav_dir}/pad_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_pad_manifest(banks, analysis_dir)
    _log.info("Pad synthesis complete — %d WAVs across %d banks", total, len(banks))


if __name__ == "__main__":
    main()
