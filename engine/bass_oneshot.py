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
