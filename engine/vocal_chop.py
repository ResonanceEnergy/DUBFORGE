"""
DUBFORGE Engine — Vocal Chop Synthesizer

Generates synthesized vocal-style sounds for dubstep drops:
  - Formant vowel chops ("ah", "oh", "eh", "ee", "oo")
  - Vocal stutters (rapid-fire pitched repeats)
  - Drop shouts (percussive formant-shaped transients)

All sounds are synthesized from scratch (no samples required).
Uses formant filter banks to shape noise/saw into vowel-like tones.

Outputs:
    output/wavetables/vocal_chop_*.wav   — Individual chop WAVs
    output/midi/vocal_chops_pattern.mid  — MIDI trigger pattern
    output/analysis/vocal_chop_manifest.json

Based on Subtronics vocal processing analysis:
  - Pitched formant chops in drops
  - Stutter edits (32nd repetitions with pitch drift)
  - "Bruh" / "wub" style percussive vocal hits
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

_log = get_logger("dubforge.vocal_chop")


# ═══════════════════════════════════════════════════════════════════════════
# FORMANT DATA — Real vowel formant frequencies (Hz)
# ═══════════════════════════════════════════════════════════════════════════

# (F1, F2, F3) center frequencies and bandwidths for each vowel
VOWEL_FORMANTS: dict[str, list[tuple[float, float]]] = {
    "ah": [(730, 80), (1090, 90), (2440, 120)],    # /ɑ/ as in "father"
    "oh": [(570, 70), (840, 80), (2410, 110)],      # /ɔ/ as in "bought"
    "eh": [(530, 60), (1840, 100), (2480, 120)],    # /ɛ/ as in "bet"
    "ee": [(270, 40), (2290, 110), (3010, 130)],    # /i/ as in "beet"
    "oo": [(300, 45), (870, 60), (2240, 100)],      # /u/ as in "boot"
}

# Fundamental frequencies for different pitches (MIDI note → Hz)
CHOP_NOTES = {
    "C3": 130.81,
    "D3": 146.83,
    "E3": 164.81,
    "F3": 174.61,
    "G3": 196.00,
    "A3": 220.00,
    "C4": 261.63,
    "E4": 329.63,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VocalChop:
    """A single synthesized vocal chop."""
    name: str
    vowel: str
    note: str
    duration_s: float = 0.25
    attack_s: float = 0.005
    release_s: float = 0.05
    formant_shift: float = 0.0      # semitones to shift formants
    distortion: float = 0.0         # 0-1 drive amount
    stutter_count: int = 0          # 0 = no stutter
    stutter_pitch_drift: float = 0  # semitones drift per stutter


@dataclass
class VocalChopBank:
    """Collection of vocal chops for a drop section."""
    name: str
    chops: list[VocalChop] = field(default_factory=list)
    bpm: float = 150.0


# ═══════════════════════════════════════════════════════════════════════════
# DSP — FORMANT FILTER
# ═══════════════════════════════════════════════════════════════════════════

def _bandpass_filter(
    signal: np.ndarray,
    center_freq: float,
    bandwidth: float,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Apply a 2nd-order bandpass filter using FFT."""
    n = len(signal)
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    # Gaussian bandpass response
    sigma = bandwidth / 2.0
    if sigma < 1.0:
        sigma = 1.0
    response = np.exp(-0.5 * ((freqs - center_freq) / sigma) ** 2)
    spectrum *= response

    return np.fft.irfft(spectrum, n=n)


def formant_filter(
    signal: np.ndarray,
    vowel: str,
    formant_shift_semitones: float = 0.0,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """
    Apply formant filter bank to shape signal into a vowel sound.
    """
    formants = VOWEL_FORMANTS.get(vowel, VOWEL_FORMANTS["ah"])

    # Apply formant shift
    shift_ratio = 2.0 ** (formant_shift_semitones / 12.0)

    result = np.zeros_like(signal, dtype=np.float64)
    gains = [1.0, 0.5, 0.25]  # F1 loudest, F3 quietest

    for i, (center, bw) in enumerate(formants):
        shifted_center = center * shift_ratio
        shifted_bw = bw * shift_ratio
        filtered = _bandpass_filter(signal, shifted_center, shifted_bw, sample_rate)
        gain = gains[i] if i < len(gains) else 0.1
        result += filtered * gain

    # Normalize
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak

    return result


def _generate_source(
    freq: float,
    duration_s: float,
    source_type: str = "saw",
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Generate a raw source waveform: saw, pulse, or noise."""
    n_samples = int(duration_s * sample_rate)
    t = np.arange(n_samples) / sample_rate

    if source_type == "saw":
        # Band-limited sawtooth (additive synthesis, 20 harmonics)
        signal = np.zeros(n_samples)
        for k in range(1, 21):
            harmonic_freq = freq * k
            if harmonic_freq > sample_rate / 2:
                break
            signal += ((-1) ** (k + 1)) * np.sin(2 * math.pi * harmonic_freq * t) / k
        signal *= 2.0 / math.pi
    elif source_type == "pulse":
        # Pulse wave with phi duty cycle
        phase = (t * freq) % 1.0
        duty = 1.0 / PHI  # ~0.618
        signal = np.where(phase < duty, 1.0, -1.0).astype(np.float64)
    elif source_type == "noise":
        # Shaped noise — better for breathy / "bruh" sounds
        rng = np.random.default_rng(42)
        signal = rng.normal(0, 1, n_samples)
        # Add tonal component
        signal += 0.3 * np.sin(2 * math.pi * freq * t)
    else:
        signal = np.sin(2 * math.pi * freq * t)

    # Normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal /= peak

    return signal


def _apply_envelope(
    signal: np.ndarray,
    attack_s: float = 0.005,
    release_s: float = 0.05,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Apply attack-release amplitude envelope."""
    n = len(signal)
    envelope = np.ones(n)

    attack_samples = int(attack_s * sample_rate)
    release_samples = int(release_s * sample_rate)

    # Attack ramp
    if attack_samples > 0 and attack_samples < n:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Release ramp (exponential decay)
    if release_samples > 0 and release_samples < n:
        decay = np.exp(-np.linspace(0, 5, release_samples))
        envelope[n - release_samples:] = decay

    return signal * envelope


def _waveshape(signal: np.ndarray, drive: float = 0.5) -> np.ndarray:
    """Soft-clip distortion for grit."""
    if drive <= 0:
        return signal
    amount = 1.0 + drive * 8.0
    return np.tanh(signal * amount)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIS — Core vocal chop generator
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_chop(chop: VocalChop, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize a single vocal chop:
      1. Generate source waveform (saw/pulse/noise)
      2. Apply formant filter bank for vowel character
      3. Apply distortion
      4. Shape with attack-release envelope
      5. Optionally apply stutter
    """
    freq = CHOP_NOTES.get(chop.note, 220.0)

    # Choose source type based on vowel
    source_map = {"ah": "saw", "oh": "pulse", "eh": "saw", "ee": "saw", "oo": "pulse"}
    source_type = source_map.get(chop.vowel, "saw")

    # Stutter: generate one micro-chop and repeat
    if chop.stutter_count > 1:
        micro_dur = chop.duration_s / chop.stutter_count
        segments = []
        for s in range(chop.stutter_count):
            drift = chop.stutter_pitch_drift * s
            shifted_freq = freq * (2.0 ** (drift / 12.0))
            src = _generate_source(shifted_freq, micro_dur, source_type, sample_rate)
            src = formant_filter(src, chop.vowel, chop.formant_shift, sample_rate)
            src = _waveshape(src, chop.distortion)
            src = _apply_envelope(src, 0.002, micro_dur * 0.3, sample_rate)
            # Fade volume per stutter (phi decay)
            volume = (1.0 / PHI) ** (s * 0.5)
            segments.append(src * volume)
        signal = np.concatenate(segments)
    else:
        signal = _generate_source(freq, chop.duration_s, source_type, sample_rate)
        signal = formant_filter(signal, chop.vowel, chop.formant_shift, sample_rate)
        signal = _waveshape(signal, chop.distortion)
        signal = _apply_envelope(signal, chop.attack_s, chop.release_s, sample_rate)

    # Final normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95

    return signal


def write_chop_wav(
    signal: np.ndarray,
    path: str,
    sample_rate: int = SAMPLE_RATE,
) -> str:
    """Write a vocal chop to a WAV file."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    import wave

    n = len(signal)
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Convert float → int16
        int_data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(int_data.tobytes())

    _log.info("Wrote vocal chop WAV: %s (%d samples, %.3fs)",
              out_path.name, n, n / sample_rate)
    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — Subtronics-style vocal chop banks
# ═══════════════════════════════════════════════════════════════════════════

def drop_vowel_chops() -> VocalChopBank:
    """
    5 vowel chops at different pitches for drop layering.
    Classic "ah-oh-eh" dubstep vocal hits.
    """
    return VocalChopBank(
        name="DROP_VOWEL_CHOPS",
        chops=[
            VocalChop("vowel_ah_C3", "ah", "C3", 0.3, distortion=0.3),
            VocalChop("vowel_oh_E3", "oh", "E3", 0.25, distortion=0.2),
            VocalChop("vowel_eh_G3", "eh", "G3", 0.2, distortion=0.4),
            VocalChop("vowel_ee_C4", "ee", "C4", 0.15, formant_shift=2.0),
            VocalChop("vowel_oo_F3", "oo", "F3", 0.3, distortion=0.1),
        ],
    )


def stutter_chops() -> VocalChopBank:
    """
    Rapid-fire vocal stutters with pitch drift.
    That classic "b-b-b-bruh" Subtronics edit sound.
    """
    return VocalChopBank(
        name="STUTTER_CHOPS",
        chops=[
            VocalChop("stutter_ah_x8", "ah", "A3", 0.5,
                       stutter_count=8, stutter_pitch_drift=-0.5,
                       distortion=0.5),
            VocalChop("stutter_eh_x6", "eh", "E3", 0.4,
                       stutter_count=6, stutter_pitch_drift=1.0,
                       distortion=0.3),
            VocalChop("stutter_oh_x12", "oh", "C3", 0.6,
                       stutter_count=12, stutter_pitch_drift=-0.3,
                       distortion=0.6),
            VocalChop("stutter_ee_x4", "ee", "C4", 0.3,
                       stutter_count=4, stutter_pitch_drift=2.0,
                       distortion=0.2),
        ],
    )


def drop_shout_chops() -> VocalChopBank:
    """
    Short percussive vocal hits — "bruh" / "wub" style.
    Formant-shaped noise transients with heavy distortion.
    """
    return VocalChopBank(
        name="DROP_SHOUT_CHOPS",
        chops=[
            VocalChop("shout_bruh", "ah", "C3", 0.12,
                       attack_s=0.001, release_s=0.08,
                       distortion=0.7, formant_shift=-3.0),
            VocalChop("shout_wub", "oo", "E3", 0.15,
                       attack_s=0.002, release_s=0.1,
                       distortion=0.8, formant_shift=-5.0),
            VocalChop("shout_yah", "eh", "G3", 0.1,
                       attack_s=0.001, release_s=0.06,
                       distortion=0.6, formant_shift=2.0),
        ],
    )


def pitched_alt_chops() -> VocalChopBank:
    """Alternate-pitched vowel chops at different registers."""
    return VocalChopBank(
        name="PITCHED_ALT_CHOPS",
        chops=[
            VocalChop("vowel_ah_low_E3", "ah", "E3", 0.35, distortion=0.2),
            VocalChop("vowel_oh_mid_G3", "oh", "G3", 0.25, distortion=0.15),
            VocalChop("vowel_eh_high_E4", "eh", "E4", 0.2, distortion=0.3,
                       formant_shift=3.0),
            VocalChop("vowel_ee_deep_C3", "ee", "C3", 0.3, distortion=0.1,
                       formant_shift=-4.0),
            VocalChop("vowel_oo_bright_A3", "oo", "A3", 0.25, distortion=0.2,
                       formant_shift=5.0),
            VocalChop("vowel_ah_scream_E4", "ah", "E4", 0.15,
                       attack_s=0.001, distortion=0.6, formant_shift=7.0),
        ],
    )


def extreme_stutter_chops() -> VocalChopBank:
    """Extreme stutter variants — faster, wilder pitch effects."""
    return VocalChopBank(
        name="EXTREME_STUTTER_CHOPS",
        chops=[
            VocalChop("stutter_oh_x16", "oh", "E3", 0.5,
                       stutter_count=16, stutter_pitch_drift=-0.2,
                       distortion=0.4),
            VocalChop("stutter_ah_x4_up", "ah", "C3", 0.4,
                       stutter_count=4, stutter_pitch_drift=3.0,
                       distortion=0.3),
            VocalChop("stutter_ee_x8_down", "ee", "C4", 0.5,
                       stutter_count=8, stutter_pitch_drift=-2.0,
                       distortion=0.5),
            VocalChop("stutter_oo_x24_micro", "oo", "A3", 0.6,
                       stutter_count=24, stutter_pitch_drift=-0.1,
                       distortion=0.7),
            VocalChop("stutter_eh_x6_wide", "eh", "G3", 0.45,
                       stutter_count=6, stutter_pitch_drift=5.0,
                       distortion=0.2),
        ],
    )


def formant_shifted_chops() -> VocalChopBank:
    """Extreme formant-shifted vowels — alien/robot vocal textures."""
    return VocalChopBank(
        name="FORMANT_SHIFTED_CHOPS",
        chops=[
            VocalChop("formant_up_ah", "ah", "C3", 0.3,
                       formant_shift=8.0, distortion=0.2),
            VocalChop("formant_down_oh", "oh", "E3", 0.3,
                       formant_shift=-8.0, distortion=0.3),
            VocalChop("formant_up_ee", "ee", "A3", 0.25,
                       formant_shift=12.0, distortion=0.4),
            VocalChop("formant_down_eh", "eh", "G3", 0.25,
                       formant_shift=-10.0, distortion=0.5),
            VocalChop("formant_extreme_oo", "oo", "C4", 0.2,
                       formant_shift=15.0, distortion=0.6),
        ],
    )


def breathy_noise_chops() -> VocalChopBank:
    """Breathy noise-heavy vocal textures — whisper / air sounds."""
    return VocalChopBank(
        name="BREATHY_NOISE_CHOPS",
        chops=[
            VocalChop("breathy_ah", "ah", "C3", 0.4,
                       attack_s=0.02, release_s=0.15,
                       distortion=0.0, formant_shift=1.0),
            VocalChop("breathy_oh", "oh", "E3", 0.35,
                       attack_s=0.03, release_s=0.12,
                       distortion=0.0, formant_shift=-1.0),
            VocalChop("whisper_ee", "ee", "A3", 0.3,
                       attack_s=0.04, release_s=0.1,
                       distortion=0.1, formant_shift=3.0),
            VocalChop("whisper_eh", "eh", "G3", 0.25,
                       attack_s=0.03, release_s=0.08,
                       distortion=0.05, formant_shift=2.0),
        ],
    )


def robotic_chops() -> VocalChopBank:
    """Robotic vocal chops — hard-tuned metallic vowel textures."""
    return VocalChopBank(
        name="ROBOTIC_CHOPS",
        chops=[
            VocalChop("robot_ah_C3", "ah", "C3", 0.25,
                       attack_s=0.001, release_s=0.05,
                       formant_shift=6.0, distortion=0.5),
            VocalChop("robot_oh_E3", "oh", "E3", 0.2,
                       attack_s=0.001, release_s=0.04,
                       formant_shift=8.0, distortion=0.6),
            VocalChop("robot_ee_G3", "ee", "G3", 0.3,
                       attack_s=0.001, release_s=0.06,
                       formant_shift=10.0, distortion=0.7),
            VocalChop("robot_oo_A3", "oo", "A3", 0.25,
                       attack_s=0.001, release_s=0.05,
                       formant_shift=12.0, distortion=0.4),
        ],
    )


def granular_chops() -> VocalChopBank:
    """Granular vocal chops — micro-stuttered grain-cloud textures."""
    return VocalChopBank(
        name="GRANULAR_CHOPS",
        chops=[
            VocalChop("grain_ah_C4", "ah", "C4", 0.5,
                       stutter_count=32, stutter_pitch_drift=0.5,
                       distortion=0.2),
            VocalChop("grain_eh_E4", "eh", "E4", 0.4,
                       stutter_count=24, stutter_pitch_drift=-0.3,
                       distortion=0.3),
            VocalChop("grain_oh_G3", "oh", "G3", 0.6,
                       stutter_count=48, stutter_pitch_drift=0.2,
                       distortion=0.15),
            VocalChop("grain_ee_A3", "ee", "A3", 0.45,
                       stutter_count=16, stutter_pitch_drift=1.0,
                       distortion=0.25),
        ],
    )


def glitched_chops() -> VocalChopBank:
    """Glitched vocal chops — extreme pitch drift and distortion."""
    return VocalChopBank(
        name="GLITCHED_CHOPS",
        chops=[
            VocalChop("glitch_ah_C4", "ah", "C4", 0.3,
                       stutter_count=16, stutter_pitch_drift=2.0,
                       distortion=0.5),
            VocalChop("glitch_oh_E4", "oh", "E4", 0.25,
                       stutter_count=20, stutter_pitch_drift=-1.5,
                       distortion=0.6),
            VocalChop("glitch_ee_G3", "ee", "G3", 0.35,
                       stutter_count=24, stutter_pitch_drift=1.0,
                       distortion=0.4),
            VocalChop("glitch_eh_A3", "eh", "A3", 0.4,
                       stutter_count=12, stutter_pitch_drift=-2.0,
                       distortion=0.55),
        ],
    )


def whisper_chops() -> VocalChopBank:
    """Whisper vocal chops — breathy low-volume with formant shift."""
    return VocalChopBank(
        name="WHISPER_CHOPS",
        chops=[
            VocalChop("whisper_ah_C4", "ah", "C4", 0.4,
                       attack_s=0.02, release_s=0.1,
                       formant_shift=-6.0, distortion=0.0),
            VocalChop("whisper_oh_E4", "oh", "E4", 0.35,
                       attack_s=0.02, release_s=0.08,
                       formant_shift=-8.0, distortion=0.05),
            VocalChop("whisper_oo_G3", "oo", "G3", 0.5,
                       attack_s=0.03, release_s=0.12,
                       formant_shift=-4.0, distortion=0.0),
            VocalChop("whisper_ee_A3", "ee", "A3", 0.3,
                       attack_s=0.015, release_s=0.1,
                       formant_shift=-10.0, distortion=0.02),
        ],
    )


def pitched_down_chops() -> VocalChopBank:
    """Pitched-down vocal chops — deep formant shifted effects."""
    return VocalChopBank(
        name="PITCHED_DOWN_CHOPS",
        chops=[
            VocalChop("pdown_ah_C3", "ah", "C3", 0.5,
                       formant_shift=-12.0, distortion=0.1),
            VocalChop("pdown_oh_E3", "oh", "E3", 0.4,
                       formant_shift=-15.0, distortion=0.15),
            VocalChop("pdown_oo_G2", "oo", "G2", 0.6,
                       formant_shift=-18.0, distortion=0.05),
            VocalChop("pdown_eh_A2", "eh", "A2", 0.5,
                       formant_shift=-20.0, distortion=0.2),
        ],
    )


def chopped_stutter_chops() -> VocalChopBank:
    """Chopped stutter — rapid retriggered vocal fragments."""
    return VocalChopBank(
        name="CHOPPED_STUTTER_CHOPS",
        chops=[
            VocalChop("cstut_ah_C4", "ah", "C4", 0.3,
                       stutter_count=8, stutter_pitch_drift=1.0,
                       distortion=0.2),
            VocalChop("cstut_oh_E4", "oh", "E4", 0.25,
                       stutter_count=12, stutter_pitch_drift=2.0,
                       distortion=0.3),
            VocalChop("cstut_oo_G4", "oo", "G4", 0.35,
                       stutter_count=6, stutter_pitch_drift=-1.0,
                       distortion=0.15),
            VocalChop("cstut_ee_A4", "ee", "A4", 0.2,
                       stutter_count=16, stutter_pitch_drift=3.0,
                       distortion=0.4),
        ],
    )


def ethereal_chops() -> VocalChopBank:
    """Ethereal vocal chops — reverb-heavy dreamy fragments."""
    return VocalChopBank(
        name="ETHEREAL_CHOPS",
        chops=[
            VocalChop("ether_ah_C5", "ah", "C5", 0.6,
                       attack_s=0.05, release_s=0.2,
                       formant_shift=6.0, distortion=0.0),
            VocalChop("ether_oh_E5", "oh", "E5", 0.5,
                       attack_s=0.04, release_s=0.15,
                       formant_shift=8.0, distortion=0.0),
            VocalChop("ether_oo_G4", "oo", "G4", 0.7,
                       attack_s=0.06, release_s=0.25,
                       formant_shift=4.0, distortion=0.0),
            VocalChop("ether_ee_A4", "ee", "A4", 0.45,
                       attack_s=0.03, release_s=0.18,
                       formant_shift=10.0, distortion=0.02),
        ],
    )


ALL_CHOP_BANKS: dict[str, callable] = {
    "drop_vowel":      drop_vowel_chops,
    "stutter":         stutter_chops,
    "drop_shout":      drop_shout_chops,
    "pitched_alt":     pitched_alt_chops,
    "extreme_stutter": extreme_stutter_chops,
    "formant_shifted": formant_shifted_chops,
    "breathy_noise":   breathy_noise_chops,
    # v2.0
    "robotic":         robotic_chops,
    "granular":        granular_chops,
    # v2.2
    "glitched":        glitched_chops,
    "whisper":         whisper_chops,
    # v2.3
    "pitched_down":    pitched_down_chops,
    "chopped_stutter": chopped_stutter_chops,
    "ethereal":        ethereal_chops,
}


# ═══════════════════════════════════════════════════════════════════════════
# MIDI TRIGGER PATTERN
# ═══════════════════════════════════════════════════════════════════════════

def write_chop_midi_pattern(
    bank: VocalChopBank,
    path: str,
    base_note: int = 60,
) -> str:
    """
    Write a MIDI pattern that triggers chops sequentially.
    Each chop maps to a different note starting from base_note.
    """
    import mido

    TICKS = 480
    mid = mido.MidiFile(type=0, ticks_per_beat=TICKS)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("track_name", name=bank.name, time=0))
    track.append(mido.MetaMessage("set_tempo",
                                  tempo=mido.bpm2tempo(bank.bpm), time=0))

    for i, chop in enumerate(bank.chops):
        note = base_note + i
        dur_ticks = int(chop.duration_s * (bank.bpm / 60.0) * TICKS)
        dur_ticks = max(TICKS // 4, dur_ticks)

        track.append(mido.Message("note_on", note=note, velocity=100,
                                  time=0 if i == 0 else TICKS))
        track.append(mido.Message("note_off", note=note, velocity=0,
                                  time=dur_ticks))

    track.append(mido.MetaMessage("end_of_track", time=0))

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out_path))
    _log.info("Wrote vocal chop MIDI: %s (%d chops)", out_path.name, len(bank.chops))
    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_chop_manifest(banks: dict[str, VocalChopBank], out_dir: str) -> str:
    """Write JSON manifest of all generated vocal chop files."""
    manifest = {
        "generator": "DUBFORGE Vocal Chop Synthesizer",
        "sample_rate": SAMPLE_RATE,
        "banks": {},
    }
    for bank_name, bank in banks.items():
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "bpm": bank.bpm,
            "chop_count": len(bank.chops),
            "chops": [
                {
                    "name": c.name,
                    "vowel": c.vowel,
                    "note": c.note,
                    "duration_s": c.duration_s,
                    "stutter_count": c.stutter_count,
                    "wav_file": f"vocal_chop_{c.name}.wav",
                }
                for c in bank.chops
            ],
        }

    manifest_path = Path(out_dir) / "vocal_chop_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Wrote vocal chop manifest: %s", manifest_path.name)
    return str(manifest_path)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    wav_dir = Path("output/wavetables")
    midi_dir = Path("output/midi")
    analysis_dir = Path("output/analysis")

    banks: dict[str, VocalChopBank] = {}
    total_wavs = 0

    for bank_name, gen_fn in ALL_CHOP_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        print(f"  Bank: {bank.name} ({len(bank.chops)} chops)")

        for chop in bank.chops:
            signal = synthesize_chop(chop)
            wav_path = wav_dir / f"vocal_chop_{chop.name}.wav"
            write_chop_wav(signal, str(wav_path))
            total_wavs += 1

        # MIDI pattern per bank
        midi_path = midi_dir / f"vocal_chops_{bank_name}.mid"
        write_chop_midi_pattern(bank, str(midi_path))

    # Manifest
    write_chop_manifest(banks, str(analysis_dir))

    print(f"Vocal Chop Synthesizer complete — {total_wavs} WAVs, "
          f"{len(banks)} MIDI patterns.")


if __name__ == "__main__":
    main()
