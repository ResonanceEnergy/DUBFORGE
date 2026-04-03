"""
DUBFORGE Engine — Lead Synthesizer

Synthesizes lead sounds for dubstep melodic lines:
  - Screech Lead:  aggressive mid-range distorted tone
  - Pluck Lead:    short-attack percussive pluck
  - FM Lead:       frequency-modulated bell/metallic lead
  - Supersaw Lead: stacked detuned saws (trance-style)
  - Acid Lead:     resonant filter sweep (303-inspired)

All leads use phi-ratio envelopes and Fibonacci harmonics.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/lead_*.wav
    output/analysis/lead_synth_manifest.json

Based on Subtronics production analysis:
  - Screech leads accent drop hooks
  - Pluck leads drive melodic breakdowns
  - FM leads add metallic texture to intros
  - Supersaws power build sections
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

_log = get_logger("dubforge.lead_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LeadPreset:
    """Settings for a single lead sound."""
    name: str
    lead_type: str          # screech | pluck | fm_lead | supersaw | acid
    frequency: float        # fundamental in Hz
    duration_s: float = 0.5
    attack_s: float = 0.01
    decay_s: float = 0.1
    sustain: float = 0.7    # 0-1 level
    release_s: float = 0.15
    detune_cents: float = 0.0
    fm_ratio: float = 1.0
    fm_depth: float = 0.0
    filter_cutoff: float = 0.8     # 0-1 normalised
    resonance: float = 0.3
    distortion: float = 0.0


@dataclass
class LeadBank:
    """Collection of lead presets."""
    name: str
    presets: list[LeadPreset] = field(default_factory=list)


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


def _adsr_envelope(n: int, preset: LeadPreset,
                   sample_rate: int) -> np.ndarray:
    """Generate ADSR envelope."""
    attack = max(1, int(preset.attack_s * sample_rate))
    decay = max(1, int(preset.decay_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))
    sustain_len = max(0, n - attack - decay - release)

    env = np.zeros(n)
    idx = 0
    # Attack
    seg = min(attack, n - idx)
    env[idx:idx + seg] = np.linspace(0, 1, seg)
    idx += seg
    # Decay
    if idx < n:
        seg = min(decay, n - idx)
        env[idx:idx + seg] = np.linspace(1, preset.sustain, seg)
        idx += seg
    # Sustain
    if idx < n:
        seg = min(sustain_len, n - idx)
        env[idx:idx + seg] = preset.sustain
        idx += seg
    # Release
    if idx < n:
        seg = min(release, n - idx)
        env[idx:idx + seg] = np.linspace(preset.sustain, 0, seg)
        idx += seg

    return env


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_screech_lead(preset: LeadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Screech lead — aggressive distorted mid-range tone.

    UPGRADED: Bandlimited square source, oversampled tube distortion,
    SVF 24dB/oct filter with resonance.
    """
    from engine.dsp_core import (osc_square, svf_lowpass_24,
                                 saturate_aggressive)

    n = int(preset.duration_s * sample_rate)

    # Bandlimited square source (odd harmonics)
    signal = osc_square(preset.frequency, preset.duration_s, sample_rate)

    # Aggressive oversampled distortion
    drive = max(preset.distortion, 0.3)
    signal = saturate_aggressive(signal, 1.0 + drive * 4, sample_rate)

    # SVF 24dB/oct with resonance
    cutoff_hz = 500 + preset.filter_cutoff * 6000
    signal = svf_lowpass_24(signal, cutoff_hz, preset.resonance * 0.8,
                            sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    return _normalize(signal)


def synthesize_pluck_lead(preset: LeadPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pluck lead — short percussive attack with fast decay.

    UPGRADED: Bandlimited saw source, SVF lowpass with decaying cutoff
    envelope (pluck character), oversampled saturation.
    """
    from engine.dsp_core import osc_saw_np, svf_lowpass, saturate_warm

    n = int(preset.duration_s * sample_rate)

    # Bandlimited saw source
    signal = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)

    # SVF lowpass with decaying cutoff envelope (pluck character)
    progress = np.linspace(0, 1, n)
    cutoff_env = 500 + preset.filter_cutoff * 8000 * np.exp(-progress * 4)
    signal = svf_lowpass(signal, cutoff_env, 0.2, sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = saturate_warm(signal, 1.0 + preset.distortion * 3, sample_rate)

    return _normalize(signal)


def synthesize_fm_lead(preset: LeadPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM lead — frequency-modulated bell/metallic tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    carrier = preset.frequency
    modulator = carrier * preset.fm_ratio
    depth = preset.fm_depth * carrier

    # FM with decaying modulation index
    progress = np.linspace(0, 1, n)
    mod_env = np.exp(-progress * 2)
    mod_signal = depth * mod_env * np.sin(2 * math.pi * modulator * t)
    signal = np.sin(2 * math.pi * carrier * t + mod_signal)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _normalize(signal)


def synthesize_supersaw_lead(preset: LeadPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Supersaw lead — stacked detuned saws for massive sound.

    UPGRADED: Bandlimited saw via osc_saw_np, 1/sqrt(n) scaling,
    SVF lowpass filter, oversampled saturation.
    """
    from engine.dsp_core import osc_saw_np, svf_lowpass, saturate_warm

    n = int(preset.duration_s * sample_rate)

    # 7 voices, detuned symmetrically
    detune = preset.detune_cents if preset.detune_cents > 0 else 15
    offsets = [-3, -2, -1, 0, 1, 2, 3]
    signal = np.zeros(n)

    for offset in offsets:
        cents = offset * (detune / 3)
        freq = preset.frequency * (2 ** (cents / 1200))
        signal += osc_saw_np(freq, preset.duration_s, sample_rate)

    # 1/sqrt(n) scaling instead of /7
    signal /= math.sqrt(len(offsets))

    # SVF lowpass
    cutoff_hz = 500 + preset.filter_cutoff * 6000
    signal = svf_lowpass(signal, cutoff_hz, 0.15, sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = saturate_warm(signal, 1.0 + preset.distortion * 3, sample_rate)

    return _normalize(signal)


def synthesize_acid_lead(preset: LeadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Acid lead — resonant filter sweep (303-inspired).

    UPGRADED: PolyBLEP square source, SVF 24dB/oct with high resonance
    and decaying filter sweep, oversampled saturation.
    """
    from engine.dsp_core import osc_square, svf_lowpass_24, saturate_warm

    n = int(preset.duration_s * sample_rate)

    # Bandlimited square source
    signal = osc_square(preset.frequency, preset.duration_s, sample_rate)

    # SVF 24dB/oct with resonance and decaying filter sweep
    progress = np.linspace(0, 1, n)
    cutoff_env = 400 + preset.filter_cutoff * 5000 * np.exp(-progress * 3)
    signal = svf_lowpass_24(signal, cutoff_env,
                            min(0.85, preset.resonance * 0.9), sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = saturate_warm(signal, 1.0 + preset.distortion * 3, sample_rate)

    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# v2.0 — 3 new lead types (12 presets)
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_saw_lead(preset: LeadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Saw lead — raw bright sawtooth with subtle detune.

    UPGRADED: Bandlimited saw via osc_saw_np, SVF lowpass with resonance.
    """
    from engine.dsp_core import osc_saw_np, svf_lowpass, saturate_warm

    n = int(preset.duration_s * sample_rate)

    detune = 2 ** (preset.detune_cents / 1200) if preset.detune_cents else 1.002
    signal = osc_saw_np(preset.frequency, preset.duration_s, sample_rate)
    signal += osc_saw_np(preset.frequency * detune, preset.duration_s, sample_rate)
    signal *= 0.5

    # SVF lowpass with resonance
    cutoff_hz = 500 + preset.filter_cutoff * 6000
    signal = svf_lowpass(signal, cutoff_hz, preset.resonance * 0.6, sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    if preset.distortion > 0:
        signal = saturate_warm(signal, 1.0 + preset.distortion * 3, sample_rate)
    return _normalize(signal)


def synthesize_pwm_lead(preset: LeadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """PWM lead — pulse-width modulated square with movement.

    UPGRADED: PolyBLEP anti-aliased square, SVF lowpass filter.
    """
    from engine.dsp_core import osc_square, svf_lowpass, saturate_warm

    n = int(preset.duration_s * sample_rate)

    # PolyBLEP square (anti-aliased)
    signal = osc_square(preset.frequency, preset.duration_s, sample_rate,
                        duty=0.35)

    # SVF lowpass filter
    cutoff_hz = 500 + preset.filter_cutoff * 5000
    signal = svf_lowpass(signal, cutoff_hz, 0.2, sample_rate)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    if preset.distortion > 0:
        signal = saturate_warm(signal, 1.0 + preset.distortion * 3, sample_rate)
    return _normalize(signal)


def synthesize_formant_lead(preset: LeadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Formant lead — vowel-shaped resonance on a saw source."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Saw source
    signal = np.zeros(n)
    for h in range(1, 12):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Formant filter — two resonant peaks ("ah" vowel morphing to "ee")
    formants = [(730, 1090), (270, 2290)]  # (start_f, end_f) per peak
    filtered = np.zeros(n)
    for start_f, end_f in formants:
        freq_sweep = np.linspace(start_f, end_f, n)
        y1, y2 = 0.0, 0.0
        layer = np.zeros(n)
        for i in range(n):
            a = min(0.99, freq_sweep[i] / sample_rate * 2)
            y1 = y1 + a * (signal[i] - y1)
            y2 = y2 + a * (y1 - y2)
            layer[i] = y1 + preset.resonance * 2 * (y1 - y2)
        filtered += layer * 0.5

    env = _adsr_envelope(n, preset, sample_rate)
    filtered *= env
    if preset.distortion > 0:
        filtered = np.tanh(filtered * (1 + preset.distortion * 3))
    return _normalize(filtered)


def synthesize_phase_lead(preset: LeadPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Phase lead — dual-oscillator with phase modulation sweep."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)

    # Two oscillators with evolving phase offset
    phase_sweep = np.linspace(0, math.pi * preset.filter_cutoff * 4, n)
    osc1 = np.sin(2 * math.pi * preset.frequency * t)
    osc2 = np.sin(2 * math.pi * preset.frequency * t + phase_sweep)

    signal = osc1 + osc2 * 0.8
    # Soft clip for presence
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_ring_mod_lead(preset: LeadPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ring modulation lead — carrier * modulator for metallic tones."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    env = _adsr_envelope(n, preset, sample_rate)

    carrier = np.sin(2 * math.pi * preset.frequency * t)
    mod_freq = preset.frequency * preset.fm_ratio
    modulator = np.sin(2 * math.pi * mod_freq * t)

    # Ring modulation with dry/wet mix
    wet = carrier * modulator
    dry_mix = max(0, 1.0 - preset.fm_depth)
    signal = dry_mix * carrier + preset.fm_depth * wet

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_wavetable_lead(preset: LeadPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Wavetable lead — morphing waveform shapes for evolving timbre."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _adsr_envelope(n, preset, sample_rate)

    phase = (preset.frequency * t) % 1.0
    sine = np.sin(2 * math.pi * phase)
    saw = 2 * phase - 1
    sq = np.sign(np.sin(2 * math.pi * phase))

    morph = np.linspace(0, 2, n)
    signal = np.zeros(n)
    for i in range(n):
        m = morph[i]
        if m < 1:
            signal[i] = sine[i] * (1 - m) + saw[i] * m
        else:
            mm = m - 1
            signal[i] = saw[i] * (1 - mm) + sq[i] * mm

    if preset.filter_cutoff > 0.5:
        signal += 0.2 * np.sin(2 * math.pi * preset.frequency * 2 * t)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


def synthesize_granular_lead(preset: LeadPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Granular lead — grain-cloud texture on lead tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _adsr_envelope(n, preset, sample_rate)

    # Base tone
    signal = np.sin(2 * math.pi * preset.frequency * t)

    # Grain cloud overlay
    grain_size = max(1, int(0.02 * sample_rate))
    rng = np.random.default_rng(42)
    grains = np.zeros(n)
    for pos in range(0, n - grain_size, grain_size * 2):
        grain = rng.standard_normal(grain_size) * 0.3
        window = np.hanning(grain_size)
        grains[pos:pos + grain_size] += grain * window

    signal = signal * 0.7 + grains * preset.filter_cutoff

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_sync_lead(preset: LeadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sync lead — oscillator hard-sync for cutting harmonics."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _adsr_envelope(n, preset, sample_rate)

    master_freq = preset.frequency
    ratio = preset.fm_ratio if preset.fm_ratio else PHI
    slave_freq = master_freq * ratio

    master_phase = (master_freq * t) % 1.0
    slave_phase = np.zeros(n)
    acc = 0.0
    for i in range(n):
        if i > 0 and master_phase[i] < master_phase[i - 1]:
            acc = 0.0
        acc += slave_freq / sample_rate
        slave_phase[i] = acc

    signal = np.sin(2 * math.pi * slave_phase)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


def synthesize_chip_lead(preset: LeadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Chip lead — retro chiptune square wave."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    phase = (preset.frequency * t) % 1.0
    signal = np.where(phase < 0.5, 1.0, -1.0).astype(float)
    vibrato = np.sin(2 * np.pi * 6.0 * t) * 0.005
    signal *= (1 + vibrato)
    signal *= preset.filter_cutoff
    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    return _normalize(signal)


def synthesize_distorted_lead(preset: LeadPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Distorted lead — heavily driven sawtooth."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    phase = (preset.frequency * t) % 1.0
    signal = 2 * phase - 1
    signal = np.tanh(signal * (2 + preset.distortion * 6))
    signal += 0.3 * np.sin(2 * np.pi * preset.frequency * 2 * t)
    signal *= 0.5
    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    return _normalize(signal)


def synthesize_harmonic_lead(preset: LeadPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Harmonic lead — additive harmonics with rich tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    signal = np.zeros(n)
    for h in range(1, 8):
        amp = preset.filter_cutoff / h
        signal += amp * np.sin(2 * np.pi * preset.frequency * h * t)
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= 0.5
    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    return _normalize(signal)


def synthesize_lead(preset: LeadPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct lead synthesizer."""
    synthesizers = {
        "screech": synthesize_screech_lead,
        "pluck": synthesize_pluck_lead,
        "fm_lead": synthesize_fm_lead,
        "supersaw": synthesize_supersaw_lead,
        "acid": synthesize_acid_lead,
        "saw": synthesize_saw_lead,
        "pwm": synthesize_pwm_lead,
        "formant": synthesize_formant_lead,
        "phase_lead": synthesize_phase_lead,
        "ring_mod": synthesize_ring_mod_lead,
        "wavetable": synthesize_wavetable_lead,
        "granular": synthesize_granular_lead,
        "sync": synthesize_sync_lead,
        # v2.4
        "chip": synthesize_chip_lead,
        "distorted_lead": synthesize_distorted_lead,
        "harmonic_lead": synthesize_harmonic_lead,
    }
    fn = synthesizers.get(preset.lead_type)
    if fn is None:
        raise ValueError(f"Unknown lead_type: {preset.lead_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 Subtronics-inspired lead sounds
# ═══════════════════════════════════════════════════════════════════════════

def screech_lead_bank() -> LeadBank:
    """Screech leads — aggressive drop accents."""
    return LeadBank(
        name="SCREECH_LEADS",
        presets=[
            LeadPreset("screech_C4", "screech", 256.87,
                       distortion=0.5, filter_cutoff=0.7, resonance=0.4),
            LeadPreset("screech_E4", "screech", 323.64,
                       distortion=0.6, filter_cutoff=0.8, resonance=0.5),
            LeadPreset("screech_G4", "screech", 384.87,
                       distortion=0.4, filter_cutoff=0.6, resonance=0.3),
            LeadPreset("screech_A4", "screech", 432.00,
                       distortion=0.7, filter_cutoff=0.9, resonance=0.6),
        ],
    )


def pluck_lead_bank() -> LeadBank:
    """Pluck leads — percussive melodic hits."""
    return LeadBank(
        name="PLUCK_LEADS",
        presets=[
            LeadPreset("pluck_C4", "pluck", 256.87, duration_s=0.4,
                       attack_s=0.002, decay_s=0.15, sustain=0.3, release_s=0.1),
            LeadPreset("pluck_E4", "pluck", 323.64, duration_s=0.4,
                       attack_s=0.003, decay_s=0.12, sustain=0.25, release_s=0.08),
            LeadPreset("pluck_G4", "pluck", 384.87, duration_s=0.4,
                       attack_s=0.002, decay_s=0.18, sustain=0.35, release_s=0.12),
            LeadPreset("pluck_A4", "pluck", 432.00, duration_s=0.4,
                       attack_s=0.001, decay_s=0.1, sustain=0.2, release_s=0.08),
        ],
    )


def fm_lead_bank() -> LeadBank:
    """FM leads — metallic bell tones."""
    return LeadBank(
        name="FM_LEADS",
        presets=[
            LeadPreset("fm_lead_C4", "fm_lead", 256.87,
                       fm_ratio=2.0, fm_depth=3.0, distortion=0.1),
            LeadPreset("fm_lead_E4", "fm_lead", 323.64,
                       fm_ratio=3.0, fm_depth=2.5, distortion=0.15),
            LeadPreset("fm_lead_G4", "fm_lead", 384.87,
                       fm_ratio=1.5, fm_depth=4.0, distortion=0.2),
            LeadPreset("fm_lead_A4", "fm_lead", 432.00,
                       fm_ratio=2.5, fm_depth=2.0, distortion=0.05),
        ],
    )


def supersaw_lead_bank() -> LeadBank:
    """Supersaw leads — massive stacked saws."""
    return LeadBank(
        name="SUPERSAW_LEADS",
        presets=[
            LeadPreset("supersaw_C4", "supersaw", 256.87, duration_s=1.0,
                       detune_cents=15, filter_cutoff=0.7, attack_s=0.05),
            LeadPreset("supersaw_E4", "supersaw", 323.64, duration_s=1.0,
                       detune_cents=20, filter_cutoff=0.8, attack_s=0.03),
            LeadPreset("supersaw_G4", "supersaw", 384.87, duration_s=1.0,
                       detune_cents=12, filter_cutoff=0.6, attack_s=0.08),
            LeadPreset("supersaw_A4", "supersaw", 432.00, duration_s=1.0,
                       detune_cents=18, filter_cutoff=0.75, attack_s=0.04),
        ],
    )


def acid_lead_bank() -> LeadBank:
    """Acid leads — resonant 303-style sweeps."""
    return LeadBank(
        name="ACID_LEADS",
        presets=[
            LeadPreset("acid_C3", "acid", 128.43, duration_s=0.6,
                       filter_cutoff=0.9, resonance=0.7, distortion=0.3),
            LeadPreset("acid_E3", "acid", 161.81, duration_s=0.6,
                       filter_cutoff=0.8, resonance=0.6, distortion=0.25),
            LeadPreset("acid_G3", "acid", 192.44, duration_s=0.6,
                       filter_cutoff=0.95, resonance=0.8, distortion=0.4),
            LeadPreset("acid_A3", "acid", 216.00, duration_s=0.6,
                       filter_cutoff=0.85, resonance=0.5, distortion=0.2),
        ],
    )


def saw_lead_bank() -> LeadBank:
    """Saw leads — bright raw sawtooth."""
    return LeadBank(
        name="SAW_LEADS",
        presets=[
            LeadPreset("saw_C4", "saw", 256.87, duration_s=0.6,
                       detune_cents=8, filter_cutoff=0.8, resonance=0.3),
            LeadPreset("saw_E4", "saw", 323.64, duration_s=0.6,
                       detune_cents=10, filter_cutoff=0.85, resonance=0.35),
            LeadPreset("saw_G4", "saw", 384.87, duration_s=0.6,
                       detune_cents=6, filter_cutoff=0.75, resonance=0.25),
            LeadPreset("saw_A4", "saw", 432.00, duration_s=0.6,
                       detune_cents=12, filter_cutoff=0.9, resonance=0.4),
        ],
    )


def pwm_lead_bank() -> LeadBank:
    """PWM leads — pulse-width modulated movement."""
    return LeadBank(
        name="PWM_LEADS",
        presets=[
            LeadPreset("pwm_C4", "pwm", 256.87, duration_s=0.8,
                       filter_cutoff=0.7, distortion=0.1),
            LeadPreset("pwm_E4", "pwm", 323.64, duration_s=0.8,
                       filter_cutoff=0.75, distortion=0.15),
            LeadPreset("pwm_G4", "pwm", 384.87, duration_s=0.8,
                       filter_cutoff=0.65, distortion=0.05),
            LeadPreset("pwm_A4", "pwm", 432.00, duration_s=0.8,
                       filter_cutoff=0.8, distortion=0.2),
        ],
    )


def formant_lead_bank() -> LeadBank:
    """Formant leads — vowel-shaped resonance."""
    return LeadBank(
        name="FORMANT_LEADS",
        presets=[
            LeadPreset("formant_C4", "formant", 256.87, duration_s=0.7,
                       resonance=0.6, distortion=0.15),
            LeadPreset("formant_E4", "formant", 323.64, duration_s=0.7,
                       resonance=0.5, distortion=0.1),
            LeadPreset("formant_G4", "formant", 384.87, duration_s=0.7,
                       resonance=0.7, distortion=0.2),
            LeadPreset("formant_A4", "formant", 432.00, duration_s=0.7,
                       resonance=0.55, distortion=0.12),
        ],
    )


def phase_lead_bank() -> LeadBank:
    """Phase leads — dual-oscillator phase sweep."""
    return LeadBank(
        name="PHASE_LEADS",
        presets=[
            LeadPreset("phase_C4", "phase_lead", 256.87, duration_s=0.6,
                       filter_cutoff=0.7, distortion=0.1),
            LeadPreset("phase_E4", "phase_lead", 323.64, duration_s=0.6,
                       filter_cutoff=0.8, distortion=0.15),
            LeadPreset("phase_G4", "phase_lead", 384.87, duration_s=0.6,
                       filter_cutoff=0.6, distortion=0.05),
            LeadPreset("phase_A4", "phase_lead", 432.00, duration_s=0.6,
                       filter_cutoff=0.75, distortion=0.12),
        ],
    )


def ring_mod_lead_bank() -> LeadBank:
    """Ring mod leads — metallic ring modulation tones."""
    return LeadBank(
        name="RING_MOD_LEADS",
        presets=[
            LeadPreset("ring_mod_C4", "ring_mod", 256.87, duration_s=0.5,
                       fm_ratio=1.5, fm_depth=0.6, distortion=0.1),
            LeadPreset("ring_mod_E4", "ring_mod", 323.64, duration_s=0.5,
                       fm_ratio=2.0, fm_depth=0.5, distortion=0.15),
            LeadPreset("ring_mod_G4", "ring_mod", 384.87, duration_s=0.5,
                       fm_ratio=1.618, fm_depth=0.7, distortion=0.08),
            LeadPreset("ring_mod_A4", "ring_mod", 432.00, duration_s=0.5,
                       fm_ratio=1.333, fm_depth=0.55, distortion=0.12),
        ],
    )


def wavetable_lead_bank() -> LeadBank:
    """Wavetable leads — morphing waveform timbres."""
    return LeadBank(
        name="WAVETABLE_LEADS",
        presets=[
            LeadPreset("wavetable_C4", "wavetable", 256.87, duration_s=0.5,
                       filter_cutoff=0.7, distortion=0.1),
            LeadPreset("wavetable_E4", "wavetable", 323.64, duration_s=0.5,
                       filter_cutoff=0.8, distortion=0.2),
            LeadPreset("wavetable_G4", "wavetable", 384.87, duration_s=0.6,
                       filter_cutoff=0.6, distortion=0.05),
            LeadPreset("wavetable_A4", "wavetable", 432.00, duration_s=0.5,
                       filter_cutoff=0.9, distortion=0.15),
        ],
    )


def granular_lead_bank() -> LeadBank:
    """Granular leads — grain-cloud textured tones."""
    return LeadBank(
        name="GRANULAR_LEADS",
        presets=[
            LeadPreset("granular_C4", "granular", 256.87, duration_s=0.6,
                       filter_cutoff=0.6, distortion=0.1),
            LeadPreset("granular_E4", "granular", 323.64, duration_s=0.5,
                       filter_cutoff=0.7, distortion=0.15),
            LeadPreset("granular_G4", "granular", 384.87, duration_s=0.5,
                       filter_cutoff=0.5, distortion=0.05),
            LeadPreset("granular_A4", "granular", 432.00, duration_s=0.6,
                       filter_cutoff=0.8, distortion=0.2),
        ],
    )


def sync_lead_bank() -> LeadBank:
    """Sync leads — hard-sync oscillator cutting harmonics."""
    return LeadBank(
        name="SYNC_LEADS",
        presets=[
            LeadPreset("sync_C4", "sync", 256.87, duration_s=0.5,
                       fm_ratio=PHI, distortion=0.15),
            LeadPreset("sync_E4", "sync", 323.64, duration_s=0.5,
                       fm_ratio=2.0, distortion=0.2),
            LeadPreset("sync_G4", "sync", 384.87, duration_s=0.5,
                       fm_ratio=1.5, distortion=0.1),
            LeadPreset("sync_A4", "sync", 432.00, duration_s=0.5,
                       fm_ratio=2.5, distortion=0.25),
        ],
    )


def chip_lead_bank() -> LeadBank:
    """Chip leads — retro chiptune square tones."""
    return LeadBank(
        name="CHIP_LEADS",
        presets=[
            LeadPreset("chip_C4", "chip", 256.87, duration_s=0.5,
                       filter_cutoff=0.9),
            LeadPreset("chip_E4", "chip", 323.64, duration_s=0.5,
                       filter_cutoff=0.8),
            LeadPreset("chip_G4", "chip", 384.87, duration_s=0.5,
                       filter_cutoff=0.7),
            LeadPreset("chip_A4", "chip", 432.00, duration_s=0.5,
                       filter_cutoff=0.85),
        ],
    )


def distorted_lead_bank() -> LeadBank:
    """Distorted leads — heavily driven sawtooth screamers."""
    return LeadBank(
        name="DISTORTED_LEADS",
        presets=[
            LeadPreset("dist_lead_C4", "distorted_lead", 256.87, duration_s=0.5,
                       distortion=0.7, filter_cutoff=0.9),
            LeadPreset("dist_lead_E4", "distorted_lead", 323.64, duration_s=0.5,
                       distortion=0.8, filter_cutoff=0.85),
            LeadPreset("dist_lead_G4", "distorted_lead", 384.87, duration_s=0.5,
                       distortion=0.6, filter_cutoff=0.95),
            LeadPreset("dist_lead_A4", "distorted_lead", 432.00, duration_s=0.5,
                       distortion=0.9, filter_cutoff=0.8),
        ],
    )


def harmonic_lead_bank() -> LeadBank:
    """Harmonic leads — rich additive harmonic tones."""
    return LeadBank(
        name="HARMONIC_LEADS",
        presets=[
            LeadPreset("harmonic_C4", "harmonic_lead", 256.87, duration_s=0.5,
                       filter_cutoff=0.8),
            LeadPreset("harmonic_E4", "harmonic_lead", 323.64, duration_s=0.5,
                       filter_cutoff=0.7),
            LeadPreset("harmonic_G4", "harmonic_lead", 384.87, duration_s=0.5,
                       filter_cutoff=0.9, distortion=0.1),
            LeadPreset("harmonic_A4", "harmonic_lead", 432.00, duration_s=0.5,
                       filter_cutoff=0.75, distortion=0.15),
        ],
    )


ALL_LEAD_BANKS: dict[str, callable] = {
    "screech":  screech_lead_bank,
    "pluck":    pluck_lead_bank,
    "fm_lead":  fm_lead_bank,
    "supersaw": supersaw_lead_bank,
    "acid":     acid_lead_bank,
    # v2.0
    "saw":      saw_lead_bank,
    "pwm":      pwm_lead_bank,
    "formant":  formant_lead_bank,
    # v2.1
    "phase_lead": phase_lead_bank,
    "ring_mod":   ring_mod_lead_bank,
    # v2.3
    "wavetable":  wavetable_lead_bank,
    "granular":   granular_lead_bank,
    "sync":       sync_lead_bank,
    # v2.4
    "chip":           chip_lead_bank,
    "distorted_lead": distorted_lead_bank,
    "harmonic_lead":  harmonic_lead_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_lead_manifest(banks: dict[str, LeadBank], out_dir: str) -> str:
    """Write JSON manifest of generated lead sounds."""
    manifest = {
        "generator": "DUBFORGE Lead Synthesizer",
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
                    "type": p.lead_type,
                    "frequency": round(p.frequency, 2),
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "lead_synth_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote lead manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all lead WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, LeadBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_LEAD_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_lead(preset)
            path = f"{wav_dir}/lead_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_lead_manifest(banks, analysis_dir)
    _log.info("Lead synthesis complete — %d WAVs across %d banks", total, len(banks))


if __name__ == "__main__":
    main()
