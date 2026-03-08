"""
DUBFORGE Engine — Bass One-Shot Generator

Synthesizes bass one-shot WAV samples at specific pitches:
  - Sub Sine:   pure sine sub-bass foundation
  - Reese Bass: detuned sawtooth layers (classic DnB/dubstep)
  - FM Bass:    frequency-modulated metallic tone
  - Square Bass: filtered square wave for punch
  - Growl Bass: distorted complex waveform for aggression

All bass sounds use phi-ratio envelopes and Fibonacci-informed harmonics.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/bass_*.wav
    output/analysis/bass_oneshot_manifest.json

Based on Subtronics production analysis:
  - Sub layers anchor every drop section
  - Reese movement creates stereo width (mono version for design)
  - FM modulation drives metallic growl tone-shaping
  - Growl shots punctuate rhythmic patterns
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

_log = get_logger("dubforge.bass_oneshot")


# ═══════════════════════════════════════════════════════════════════════════
# MIDI NOTE FREQUENCIES
# ═══════════════════════════════════════════════════════════════════════════

def _midi_to_freq(note: int) -> float:
    """Convert MIDI note number to frequency in Hz (A4=440)."""
    return 440.0 * (2 ** ((note - 69) / 12))


NOTE_C1 = _midi_to_freq(24)   # ~32.70 Hz
NOTE_D1 = _midi_to_freq(26)   # ~36.71 Hz
NOTE_E1 = _midi_to_freq(28)   # ~41.20 Hz
NOTE_F1 = _midi_to_freq(29)   # ~43.65 Hz
NOTE_C2 = _midi_to_freq(36)   # ~65.41 Hz
NOTE_D2 = _midi_to_freq(38)   # ~73.42 Hz
NOTE_E2 = _midi_to_freq(40)   # ~82.41 Hz
NOTE_F2 = _midi_to_freq(41)   # ~87.31 Hz


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BassPreset:
    """Settings for a single bass one-shot."""
    name: str
    bass_type: str          # sub_sine | reese | fm | square | growl
    frequency: float        # fundamental frequency in Hz
    duration_s: float = 0.8
    attack_s: float = 0.005
    release_s: float = 0.2
    detune_cents: float = 0.0
    fm_ratio: float = 1.0
    fm_depth: float = 0.0
    distortion: float = 0.0
    filter_cutoff: float = 1.0   # 0-1 normalised


@dataclass
class BassBank:
    """Collection of bass presets."""
    name: str
    presets: list[BassPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _apply_bass_envelope(
    signal: np.ndarray, preset: BassPreset, sample_rate: int,
) -> np.ndarray:
    """Apply attack/release envelope, distortion, and normalisation."""
    n = len(signal)

    # AD envelope
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    if release < n:
        env[-release:] = np.linspace(1, 0, release)
    signal = signal * env

    # Optional distortion
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    # Normalise
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    """Write signal to 16-bit mono WAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    _log.info("Wrote bass WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_sub_sine(preset: BassPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pure sine sub-bass — clean low-end foundation."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    signal = np.sin(2 * math.pi * preset.frequency * t)
    # Subtle 2nd harmonic for presence
    signal += 0.15 * np.sin(2 * math.pi * preset.frequency * 2 * t)

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_reese(preset: BassPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Reese bass — detuned sawtooth layers for movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    detune_ratio = 2 ** (preset.detune_cents / 1200)
    freq1 = preset.frequency
    freq2 = preset.frequency * detune_ratio
    freq3 = preset.frequency / detune_ratio

    # Sawtooth via harmonic series (6 harmonics per voice)
    signal = np.zeros(n)
    for f in [freq1, freq2, freq3]:
        for h in range(1, 7):
            if f * h > sample_rate / 2:
                break
            signal += ((-1) ** h / h) * np.sin(2 * math.pi * f * h * t) / 3

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_fm_bass(preset: BassPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM bass — frequency-modulated for metallic/aggressive tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    carrier = preset.frequency
    modulator = carrier * preset.fm_ratio
    depth = preset.fm_depth * carrier

    # FM synthesis: carrier + modulator
    mod_signal = depth * np.sin(2 * math.pi * modulator * t)
    signal = np.sin(2 * math.pi * carrier * t + mod_signal)

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_square_bass(preset: BassPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Square bass — filtered square wave for punchy tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Square wave via odd harmonics with filter rolloff
    signal = np.zeros(n)
    for h in range(1, 12, 2):
        if preset.frequency * h > sample_rate / 2:
            break
        amp = 1.0 / h
        if h > 1:
            amp *= max(0.01, preset.filter_cutoff ** (h - 1))
        signal += amp * np.sin(2 * math.pi * preset.frequency * h * t)

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_growl_bass(preset: BassPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Growl bass — distorted complex waveform for aggressive drops."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich sawtooth
    signal = np.zeros(n)
    for h in range(1, 10):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Wobble LFO at phi-rate
    wobble = 0.5 + 0.5 * np.sin(2 * math.pi * PHI * 2 * t)
    signal *= wobble

    # Heavy distortion (override preset minimum)
    preset_copy = BassPreset(
        name=preset.name,
        bass_type=preset.bass_type,
        frequency=preset.frequency,
        duration_s=preset.duration_s,
        attack_s=preset.attack_s,
        release_s=preset.release_s,
        distortion=max(preset.distortion, 0.3),
    )
    return _apply_bass_envelope(signal, preset_copy, sample_rate)


def synthesize_wobble_bass(preset: BassPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Wobble bass — LFO-modulated amplitude for classic dubstep wobble."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich saw source
    signal = np.zeros(n)
    for h in range(1, 8):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Wobble LFO — rate controlled by fm_ratio (reusing field)
    wobble_rate = preset.fm_ratio if preset.fm_ratio > 0 else PHI * 3
    wobble = 0.5 + 0.5 * np.sin(2 * math.pi * wobble_rate * t)
    signal *= wobble

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_neuro_bass(preset: BassPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Neuro bass — phase-distorted complex tone for aggressive neurofunk."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Phase distortion: modulate phase of carrier
    carrier_phase = 2 * math.pi * preset.frequency * t
    pd_amount = preset.fm_depth if preset.fm_depth > 0 else 2.0
    phase_mod = pd_amount * np.sin(carrier_phase * 0.5)
    signal = np.sin(carrier_phase + phase_mod)
    signal += 0.5 * np.sin(carrier_phase * 2 + phase_mod * 1.5)

    # Aggressive distortion
    drive = max(preset.distortion, 0.4)
    signal = np.tanh(signal * (1 + drive * 5))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_acid_bass(preset: BassPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Acid bass — 303-style resonant filter sweep."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Square source
    signal = np.zeros(n)
    for h in range(1, 10, 2):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += (1.0 / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Decaying resonant filter
    progress = np.linspace(0, 1, n)
    cutoff_env = preset.filter_cutoff * np.exp(-progress * 3)
    y1, y2 = 0.0, 0.0
    for i in range(n):
        a = max(0.01, cutoff_env[i] * 0.5 + 0.05)
        y1 = y1 + a * (signal[i] - y1)
        y2 = y2 + a * (y1 - y2)
        signal[i] = y1 + 0.6 * (y1 - y2)  # resonance boost

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_donk_bass(preset: BassPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Donk bass — pitch-bending percussive hit."""
    n = int(preset.duration_s * sample_rate)

    # Rapid pitch descent
    progress = np.linspace(0, 1, n)
    freq_env = preset.frequency * (1 + 3 * np.exp(-progress * 20))
    phase = np.cumsum(2 * math.pi * freq_env / sample_rate)
    signal = np.sin(phase)

    # Percussive envelope — override attack/release
    attack = max(1, int(0.002 * sample_rate))
    release = max(1, int(0.1 * sample_rate))
    env = np.zeros(n)
    env[:attack] = np.linspace(0, 1, attack)
    body = min(n - attack, int(0.05 * sample_rate))
    env[attack:attack + body] = 1.0
    tail_start = attack + body
    if tail_start < n:
        remaining = n - tail_start
        env[tail_start:] = np.exp(-np.arange(remaining) / max(1, release))
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# v2.0 — 3 new bass types (12 presets)
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_saw_bass(preset: BassPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Saw bass — bright sawtooth with harmonic saturation."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    signal = np.zeros(n)
    for h in range(1, 16):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Harmonic saturation
    signal = np.tanh(signal * 1.5) * 0.8 + signal * 0.2

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_tape_bass(preset: BassPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tape bass — warm analog-style with tape saturation and wow."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Slightly detuned triangle for warmth
    detune = 2 ** (preset.detune_cents / 1200) if preset.detune_cents else 1.003
    signal = np.zeros(n)
    for freq in [preset.frequency, preset.frequency * detune]:
        for h in range(1, 8, 2):
            if freq * h > sample_rate / 2:
                break
            signal += ((-1) ** ((h - 1) // 2)) / (h * h) * np.sin(
                2 * math.pi * freq * h * t)
    signal *= 0.5

    # Tape wow (slow pitch wobble)
    wow = 1.0 + 0.002 * np.sin(2 * math.pi * 0.8 * t)
    phase = np.cumsum(2 * math.pi * preset.frequency * wow / sample_rate)
    signal += 0.3 * np.sin(phase)

    # Tape saturation (gentle)
    signal = np.tanh(signal * 1.2)

    # Lowpass for warmth
    alpha = 0.15
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_dist_fm_bass(preset: BassPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Distorted FM bass — heavy FM with aggressive waveshaping."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    carrier = preset.frequency
    ratio = preset.fm_ratio if preset.fm_ratio > 1 else 2.5
    depth = preset.fm_depth if preset.fm_depth > 0 else 4.0
    modulator = carrier * ratio

    # FM with fixed modulation (no decay)
    mod_signal = depth * carrier * np.sin(2 * math.pi * modulator * t)
    signal = np.sin(2 * math.pi * carrier * t + mod_signal)

    # Multi-stage distortion
    signal = np.tanh(signal * 2)
    drive = max(preset.distortion, 0.5)
    signal = np.tanh(signal * (1 + drive * 4))

    # Bandpass emphasis around fundamental
    alpha = max(0.05, preset.filter_cutoff * 0.3)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = signal[i] * 0.3 + y * 0.7

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_ring_mod_bass(preset: BassPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ring-modulated bass — metallic clanging tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    carrier = np.sin(2 * math.pi * preset.frequency * t)
    ratio = preset.fm_ratio if preset.fm_ratio > 1 else 1.618
    mod_freq = preset.frequency * ratio
    modulator = np.sin(2 * math.pi * mod_freq * t)

    # Ring modulation (multiply)
    signal = carrier * modulator

    # Add sub for weight
    signal += 0.5 * np.sin(2 * math.pi * preset.frequency * t)

    # Filter
    if preset.filter_cutoff < 1.0:
        alpha = max(0.05, preset.filter_cutoff * 0.4)
        y = 0.0
        for i in range(n):
            y = y * (1 - alpha) + signal[i] * alpha
            signal[i] = y

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_phase_bass(preset: BassPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Phase-modulated bass — thick phasing sweep."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Two detuned oscillators with sweeping phase offset
    detune = 2 ** (preset.detune_cents / 1200) if preset.detune_cents else 1.005
    lfo_rate = PHI * 0.5
    phase_sweep = 2 * math.pi * np.sin(2 * math.pi * lfo_rate * t)

    osc1 = np.sin(2 * math.pi * preset.frequency * t)
    osc2 = np.sin(2 * math.pi * preset.frequency * detune * t + phase_sweep)
    signal = osc1 + osc2

    # Add sub harmonic
    signal += 0.4 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.5

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_bitcrush_bass(preset: BassPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Bitcrushed bass — reduced bit-depth crunch."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    signal = np.sin(2 * math.pi * preset.frequency * t)
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * 2 * t)

    # Bitcrush effect
    bits = max(2, 16 - int(preset.distortion * 12))
    levels = 2 ** bits
    signal = np.round(signal * levels) / levels

    # Downsample simulation
    crush_factor = max(1, int(4 + preset.distortion * 8))
    for i in range(0, n, crush_factor):
        signal[i:i + crush_factor] = signal[i]

    signal += 0.4 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.5

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_formant_bass(preset: BassPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Formant bass — vowel-shaped resonances on bass tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich harmonic source
    signal = np.zeros(n)
    for h in range(1, 10):
        signal += (0.7 ** h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Simple formant filter: resonances at vowel frequencies
    formant_freqs = [600, 1200, 2400]  # "ah" vowel
    filtered = np.zeros(n)
    for ff in formant_freqs:
        alpha = min(0.99, ff / sample_rate * 2 * math.pi)
        y = 0.0
        for i in range(n):
            y = y * (1 - alpha) + signal[i] * alpha
            filtered[i] += y * 0.33

    signal = filtered + 0.5 * np.sin(2 * math.pi * preset.frequency * t)
    signal *= 0.5

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_sync_bass(preset: BassPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Hard-sync bass — oscillator sync for aggressive harmonics."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Master oscillator
    master_freq = preset.frequency
    # Slave oscillator at higher ratio
    ratio = preset.fm_ratio if preset.fm_ratio else PHI
    slave_freq = master_freq * ratio

    master_phase = (master_freq * t) % 1.0
    # Reset slave phase at master zero-crossings
    slave_phase = np.zeros(n)
    acc = 0.0
    for i in range(n):
        if i > 0 and master_phase[i] < master_phase[i - 1]:
            acc = 0.0
        acc += slave_freq / sample_rate
        slave_phase[i] = acc

    signal = np.sin(2 * math.pi * slave_phase)
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.5

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_wavetable_bass(preset: BassPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Wavetable bass — morphing between waveform shapes."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    phase = (preset.frequency * t) % 1.0

    # Morph between sine, triangle, saw, square
    sine = np.sin(2 * math.pi * phase)
    tri = 2 * np.abs(2 * phase - 1) - 1
    saw = 2 * phase - 1
    sq = np.sign(np.sin(2 * math.pi * phase))

    # Morph position sweeps over time
    morph = np.linspace(0, 3, n)
    signal = np.zeros(n)
    for i in range(n):
        m = morph[i]
        if m < 1:
            signal[i] = sine[i] * (1 - m) + tri[i] * m
        elif m < 2:
            mm = m - 1
            signal[i] = tri[i] * (1 - mm) + saw[i] * mm
        else:
            mm = m - 2
            signal[i] = saw[i] * (1 - mm) + sq[i] * mm

    signal += 0.4 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.5

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_amplitude_bass(preset: BassPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Amplitude-modulated bass — tremolo-style movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    carrier = np.sin(2 * math.pi * preset.frequency * t)
    mod_rate = preset.fm_ratio * 4.0
    mod = 0.5 + 0.5 * np.sin(2 * math.pi * mod_rate * t)
    signal = carrier * mod

    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.6

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_octave_bass(preset: BassPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Octave bass — fundamental stacked with octave for thickness."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    fund = np.sin(2 * math.pi * preset.frequency * t)
    octave_up = np.sin(2 * math.pi * preset.frequency * 2 * t) * 0.6
    octave_down = np.sin(2 * math.pi * preset.frequency * 0.5 * t) * 0.8
    signal = fund + octave_up + octave_down
    signal *= 0.35

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_pulse_width_bass(preset: BassPreset,
                                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pulse-width bass — variable pulse width for tonal movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    phase = (preset.frequency * t) % 1.0
    pw_mod = 0.3 + 0.2 * np.sin(2 * math.pi * 0.5 * t)
    signal = np.where(phase < pw_mod, 1.0, -1.0).astype(float)

    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * 0.5 * t)
    signal *= 0.5

    if preset.filter_cutoff < 1.0:
        cutoff_n = max(1, int(preset.filter_cutoff * 10))
        kernel = np.ones(cutoff_n) / cutoff_n
        signal = np.convolve(signal, kernel, mode="same")

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _apply_bass_envelope(signal, preset, sample_rate)


def synthesize_bass(preset: BassPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct bass synthesizer."""
    synthesizers = {
        "sub_sine": synthesize_sub_sine,
        "reese": synthesize_reese,
        "fm": synthesize_fm_bass,
        "square": synthesize_square_bass,
        "growl": synthesize_growl_bass,
        "wobble": synthesize_wobble_bass,
        "neuro": synthesize_neuro_bass,
        "acid": synthesize_acid_bass,
        "donk": synthesize_donk_bass,
        "saw": synthesize_saw_bass,
        "tape": synthesize_tape_bass,
        "dist_fm": synthesize_dist_fm_bass,
        "ring_mod": synthesize_ring_mod_bass,
        "phase": synthesize_phase_bass,
        "bitcrush": synthesize_bitcrush_bass,
        "formant": synthesize_formant_bass,
        "sync": synthesize_sync_bass,
        "wavetable": synthesize_wavetable_bass,
        # v2.4
        "amplitude": synthesize_amplitude_bass,
        "octave": synthesize_octave_bass,
        "pulse_width": synthesize_pulse_width_bass,
    }
    fn = synthesizers.get(preset.bass_type)
    if fn is None:
        raise ValueError(f"Unknown bass_type: {preset.bass_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 Subtronics-calibrated bass one-shots
# ═══════════════════════════════════════════════════════════════════════════

def sub_sine_bank() -> BassBank:
    """Pure sub-bass one-shots at four root notes."""
    return BassBank(
        name="SUB_SINE",
        presets=[
            BassPreset("sub_C1", "sub_sine", NOTE_C1, duration_s=1.0),
            BassPreset("sub_D1", "sub_sine", NOTE_D1, duration_s=1.0),
            BassPreset("sub_E1", "sub_sine", NOTE_E1, duration_s=1.0),
            BassPreset("sub_F1", "sub_sine", NOTE_F1, duration_s=1.0),
        ],
    )


def reese_bank() -> BassBank:
    """Reese bass — detuned saw layers, classic DnB/dubstep."""
    return BassBank(
        name="REESE",
        presets=[
            BassPreset("reese_C2", "reese", NOTE_C2,
                       detune_cents=15, distortion=0.1),
            BassPreset("reese_D2", "reese", NOTE_D2,
                       detune_cents=20, distortion=0.15),
            BassPreset("reese_E2", "reese", NOTE_E2,
                       detune_cents=12, distortion=0.1),
            BassPreset("reese_F2", "reese", NOTE_F2,
                       detune_cents=18, distortion=0.2),
        ],
    )


def fm_bass_bank() -> BassBank:
    """FM bass — metallic/aggressive modulated tone."""
    return BassBank(
        name="FM_BASS",
        presets=[
            BassPreset("fm_C2", "fm", NOTE_C2,
                       fm_ratio=2.0, fm_depth=3.0, distortion=0.2),
            BassPreset("fm_D2", "fm", NOTE_D2,
                       fm_ratio=1.5, fm_depth=2.5, distortion=0.15),
            BassPreset("fm_E2", "fm", NOTE_E2,
                       fm_ratio=3.0, fm_depth=4.0, distortion=0.3),
            BassPreset("fm_F2", "fm", NOTE_F2,
                       fm_ratio=2.5, fm_depth=2.0, distortion=0.1),
        ],
    )


def square_bass_bank() -> BassBank:
    """Square bass — punchy filtered square wave."""
    return BassBank(
        name="SQUARE_BASS",
        presets=[
            BassPreset("square_C2", "square", NOTE_C2,
                       filter_cutoff=0.7, distortion=0.1),
            BassPreset("square_D2", "square", NOTE_D2,
                       filter_cutoff=0.5, distortion=0.15),
            BassPreset("square_E2", "square", NOTE_E2,
                       filter_cutoff=0.8, distortion=0.05),
            BassPreset("square_F2", "square", NOTE_F2,
                       filter_cutoff=0.6, distortion=0.2),
        ],
    )


def growl_bass_bank() -> BassBank:
    """Growl bass — distorted, wobbling, aggressive."""
    return BassBank(
        name="GROWL_BASS",
        presets=[
            BassPreset("growl_C2", "growl", NOTE_C2, distortion=0.6),
            BassPreset("growl_D2", "growl", NOTE_D2, distortion=0.8),
            BassPreset("growl_E2", "growl", NOTE_E2, distortion=0.5),
            BassPreset("growl_F2", "growl", NOTE_F2, distortion=0.7),
        ],
    )


def wobble_bass_bank() -> BassBank:
    """Wobble bass — LFO-modulated dubstep classic."""
    return BassBank(
        name="WOBBLE_BASS",
        presets=[
            BassPreset("wobble_C2", "wobble", NOTE_C2, fm_ratio=3.0, distortion=0.2),
            BassPreset("wobble_D2", "wobble", NOTE_D2, fm_ratio=4.0, distortion=0.3),
            BassPreset("wobble_E2", "wobble", NOTE_E2, fm_ratio=2.0, distortion=0.15),
            BassPreset("wobble_F2", "wobble", NOTE_F2, fm_ratio=5.0, distortion=0.25),
        ],
    )


def neuro_bass_bank() -> BassBank:
    """Neuro bass — phase-distorted aggressive neurofunk."""
    return BassBank(
        name="NEURO_BASS",
        presets=[
            BassPreset("neuro_C2", "neuro", NOTE_C2,
                       fm_depth=2.5, distortion=0.5),
            BassPreset("neuro_D2", "neuro", NOTE_D2,
                       fm_depth=3.0, distortion=0.6),
            BassPreset("neuro_E2", "neuro", NOTE_E2,
                       fm_depth=2.0, distortion=0.4),
            BassPreset("neuro_F2", "neuro", NOTE_F2,
                       fm_depth=3.5, distortion=0.7),
        ],
    )


def acid_bass_bank() -> BassBank:
    """Acid bass — 303-style resonant filter sweeps."""
    return BassBank(
        name="ACID_BASS",
        presets=[
            BassPreset("acid_C2", "acid", NOTE_C2,
                       filter_cutoff=0.9, distortion=0.3),
            BassPreset("acid_D2", "acid", NOTE_D2,
                       filter_cutoff=0.8, distortion=0.25),
            BassPreset("acid_E2", "acid", NOTE_E2,
                       filter_cutoff=0.95, distortion=0.4),
            BassPreset("acid_F2", "acid", NOTE_F2,
                       filter_cutoff=0.85, distortion=0.2),
        ],
    )


def donk_bass_bank() -> BassBank:
    """Donk bass — pitch-bending percussive bass hits."""
    return BassBank(
        name="DONK_BASS",
        presets=[
            BassPreset("donk_C2", "donk", NOTE_C2, duration_s=0.3, distortion=0.3),
            BassPreset("donk_D2", "donk", NOTE_D2, duration_s=0.3, distortion=0.4),
            BassPreset("donk_E2", "donk", NOTE_E2, duration_s=0.3, distortion=0.2),
            BassPreset("donk_F2", "donk", NOTE_F2, duration_s=0.3, distortion=0.35),
        ],
    )


def saw_bass_bank() -> BassBank:
    """Saw bass — bright harmonically rich sawtooth."""
    return BassBank(
        name="SAW_BASS",
        presets=[
            BassPreset("saw_bass_C2", "saw", NOTE_C2, distortion=0.2),
            BassPreset("saw_bass_D2", "saw", NOTE_D2, distortion=0.3),
            BassPreset("saw_bass_E2", "saw", NOTE_E2, distortion=0.15),
            BassPreset("saw_bass_F2", "saw", NOTE_F2, distortion=0.25),
        ],
    )


def tape_bass_bank() -> BassBank:
    """Tape bass — warm analog tape-saturated tone."""
    return BassBank(
        name="TAPE_BASS",
        presets=[
            BassPreset("tape_bass_C2", "tape", NOTE_C2, detune_cents=5),
            BassPreset("tape_bass_D2", "tape", NOTE_D2, detune_cents=8),
            BassPreset("tape_bass_E2", "tape", NOTE_E2, detune_cents=3),
            BassPreset("tape_bass_F2", "tape", NOTE_F2, detune_cents=6),
        ],
    )


def dist_fm_bass_bank() -> BassBank:
    """Distorted FM bass — aggressive waveshaped FM."""
    return BassBank(
        name="DIST_FM_BASS",
        presets=[
            BassPreset("dist_fm_C2", "dist_fm", NOTE_C2,
                       fm_ratio=2.5, fm_depth=4.0, distortion=0.6),
            BassPreset("dist_fm_D2", "dist_fm", NOTE_D2,
                       fm_ratio=3.0, fm_depth=3.5, distortion=0.7),
            BassPreset("dist_fm_E2", "dist_fm", NOTE_E2,
                       fm_ratio=2.0, fm_depth=5.0, distortion=0.5),
            BassPreset("dist_fm_F2", "dist_fm", NOTE_F2,
                       fm_ratio=2.5, fm_depth=3.0, distortion=0.8),
        ],
    )


def ring_mod_bass_bank() -> BassBank:
    """Ring-modulated bass — metallic clanging tone."""
    return BassBank(
        name="RING_MOD_BASS",
        presets=[
            BassPreset("ring_mod_C2", "ring_mod", NOTE_C2,
                       fm_ratio=1.618, filter_cutoff=0.7),
            BassPreset("ring_mod_D2", "ring_mod", NOTE_D2,
                       fm_ratio=2.0, filter_cutoff=0.6),
            BassPreset("ring_mod_E2", "ring_mod", NOTE_E2,
                       fm_ratio=1.5, filter_cutoff=0.8),
            BassPreset("ring_mod_F2", "ring_mod", NOTE_F2,
                       fm_ratio=PHI, filter_cutoff=0.65),
        ],
    )


def phase_bass_bank() -> BassBank:
    """Phase-modulated bass — thick phasing sweep."""
    return BassBank(
        name="PHASE_BASS",
        presets=[
            BassPreset("phase_bass_C2", "phase", NOTE_C2,
                       detune_cents=8),
            BassPreset("phase_bass_D2", "phase", NOTE_D2,
                       detune_cents=12),
            BassPreset("phase_bass_E2", "phase", NOTE_E2,
                       detune_cents=5),
            BassPreset("phase_bass_F2", "phase", NOTE_F2,
                       detune_cents=10),
        ],
    )


def bitcrush_bass_bank() -> BassBank:
    """Bitcrushed bass — crunchy bit-reduced tones."""
    return BassBank(
        name="BITCRUSH_BASS",
        presets=[
            BassPreset("bitcrush_C2", "bitcrush", NOTE_C2, distortion=0.5),
            BassPreset("bitcrush_D2", "bitcrush", NOTE_D2, distortion=0.7),
            BassPreset("bitcrush_E2", "bitcrush", NOTE_E2, distortion=0.3),
            BassPreset("bitcrush_F2", "bitcrush", NOTE_F2, distortion=0.8),
        ],
    )


def formant_bass_bank() -> BassBank:
    """Formant bass — vowel-shaped resonances."""
    return BassBank(
        name="FORMANT_BASS",
        presets=[
            BassPreset("formant_bass_C2", "formant", NOTE_C2,
                       filter_cutoff=0.6),
            BassPreset("formant_bass_D2", "formant", NOTE_D2,
                       filter_cutoff=0.7),
            BassPreset("formant_bass_E2", "formant", NOTE_E2,
                       filter_cutoff=0.5),
            BassPreset("formant_bass_F2", "formant", NOTE_F2,
                       filter_cutoff=0.8),
        ],
    )


def sync_bass_bank() -> BassBank:
    """Hard-sync bass — aggressive oscillator sync tones."""
    return BassBank(
        name="SYNC_BASS",
        presets=[
            BassPreset("sync_bass_C2", "sync", NOTE_C2,
                       fm_ratio=PHI, distortion=0.2),
            BassPreset("sync_bass_D2", "sync", NOTE_D2,
                       fm_ratio=2.0, distortion=0.3),
            BassPreset("sync_bass_E2", "sync", NOTE_E2,
                       fm_ratio=1.5, distortion=0.15),
            BassPreset("sync_bass_F2", "sync", NOTE_F2,
                       fm_ratio=2.5, distortion=0.4),
        ],
    )


def wavetable_bass_bank() -> BassBank:
    """Wavetable bass — morphing waveform shapes."""
    return BassBank(
        name="WAVETABLE_BASS",
        presets=[
            BassPreset("wavetable_bass_C2", "wavetable", NOTE_C2,
                       distortion=0.1),
            BassPreset("wavetable_bass_D2", "wavetable", NOTE_D2,
                       distortion=0.2),
            BassPreset("wavetable_bass_E2", "wavetable", NOTE_E2,
                       distortion=0.0),
            BassPreset("wavetable_bass_F2", "wavetable", NOTE_F2,
                       distortion=0.3),
        ],
    )


def amplitude_bass_bank() -> BassBank:
    """Amplitude-modulated bass — tremolo-driven movement."""
    return BassBank(
        name="AMPLITUDE_BASS",
        presets=[
            BassPreset("amplitude_C2", "amplitude", NOTE_C2,
                       fm_ratio=1.0, distortion=0.1),
            BassPreset("amplitude_D2", "amplitude", NOTE_D2,
                       fm_ratio=1.5, distortion=0.2),
            BassPreset("amplitude_E2", "amplitude", NOTE_E2,
                       fm_ratio=0.8, distortion=0.15),
            BassPreset("amplitude_F2", "amplitude", NOTE_F2,
                       fm_ratio=2.0, distortion=0.3),
        ],
    )


def octave_bass_bank() -> BassBank:
    """Octave bass — layered octave stacking."""
    return BassBank(
        name="OCTAVE_BASS",
        presets=[
            BassPreset("octave_C2", "octave", NOTE_C2, distortion=0.1),
            BassPreset("octave_D2", "octave", NOTE_D2, distortion=0.2),
            BassPreset("octave_E2", "octave", NOTE_E2, distortion=0.05),
            BassPreset("octave_F2", "octave", NOTE_F2, distortion=0.3),
        ],
    )


def pulse_width_bass_bank() -> BassBank:
    """Pulse-width bass — PWM tonal movement."""
    return BassBank(
        name="PULSE_WIDTH_BASS",
        presets=[
            BassPreset("pw_bass_C2", "pulse_width", NOTE_C2,
                       filter_cutoff=0.7, distortion=0.2),
            BassPreset("pw_bass_D2", "pulse_width", NOTE_D2,
                       filter_cutoff=0.6, distortion=0.3),
            BassPreset("pw_bass_E2", "pulse_width", NOTE_E2,
                       filter_cutoff=0.8, distortion=0.15),
            BassPreset("pw_bass_F2", "pulse_width", NOTE_F2,
                       filter_cutoff=0.5, distortion=0.4),
        ],
    )


ALL_BASS_BANKS: dict[str, callable] = {
    "sub_sine":    sub_sine_bank,
    "reese":       reese_bank,
    "fm_bass":     fm_bass_bank,
    "square_bass": square_bass_bank,
    "growl_bass":  growl_bass_bank,
    "wobble_bass": wobble_bass_bank,
    "neuro_bass":  neuro_bass_bank,
    "acid_bass":   acid_bass_bank,
    "donk_bass":   donk_bass_bank,
    # v2.0
    "saw_bass":    saw_bass_bank,
    "tape_bass":   tape_bass_bank,
    "dist_fm_bass": dist_fm_bass_bank,
    # v2.2
    "ring_mod_bass": ring_mod_bass_bank,
    "phase_bass":    phase_bass_bank,
    # v2.3
    "bitcrush_bass":  bitcrush_bass_bank,
    "formant_bass":   formant_bass_bank,
    "sync_bass":      sync_bass_bank,
    "wavetable_bass": wavetable_bass_bank,
    # v2.4
    "amplitude_bass": amplitude_bass_bank,
    "octave_bass":    octave_bass_bank,
    "pulse_width_bass": pulse_width_bass_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_bass_manifest(banks: dict[str, BassBank], out_dir: str) -> str:
    """Write JSON manifest of generated bass one-shots."""
    manifest = {
        "generator": "DUBFORGE Bass One-Shot Generator",
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
                    "type": p.bass_type,
                    "frequency": round(p.frequency, 2),
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "bass_oneshot_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote bass manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all bass one-shot WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, BassBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_BASS_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_bass(preset)
            path = f"{wav_dir}/bass_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_bass_manifest(banks, analysis_dir)
    _log.info(
        "Bass one-shot generation complete — %d WAVs across %d banks",
        total, len(banks),
    )


if __name__ == "__main__":
    main()
