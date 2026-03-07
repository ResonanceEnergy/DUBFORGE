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

from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

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
    """Write signal to 16-bit mono WAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    _log.info("Wrote lead WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


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
    """Screech lead — aggressive distorted mid-range tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Square-ish tone (odd harmonics with bright character)
    signal = np.zeros(n)
    for h in range(1, 14, 2):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += (1.0 / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Aggressive distortion
    drive = max(preset.distortion, 0.3)
    signal = np.tanh(signal * (1 + drive * 5))

    # Resonant filter (emphasis at cutoff)
    cutoff = preset.filter_cutoff
    alpha = min(0.99, cutoff * 0.5 + 0.1)
    y1, y2 = 0.0, 0.0
    for i in range(n):
        y1 = y1 + alpha * (signal[i] - y1)
        y2 = y2 + alpha * (y1 - y2)
        signal[i] = y1 + preset.resonance * (y1 - y2)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env
    return _normalize(signal)


def synthesize_pluck_lead(preset: LeadPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pluck lead — short percussive attack with fast decay."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Bright sawtooth
    signal = np.zeros(n)
    for h in range(1, 10):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Filter with decaying cutoff (pluck character)
    progress = np.linspace(0, 1, n)
    filter_env = preset.filter_cutoff * np.exp(-progress * 4)
    y = 0.0
    for i in range(n):
        a = max(0.01, filter_env[i] * 0.6 + 0.05)
        y = y * (1 - a) + signal[i] * a
        signal[i] = y

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

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
    """Supersaw lead — stacked detuned saws for massive sound."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # 7 voices, detuned symmetrically
    detune = preset.detune_cents if preset.detune_cents > 0 else 15
    offsets = [-3, -2, -1, 0, 1, 2, 3]
    signal = np.zeros(n)

    for offset in offsets:
        cents = offset * (detune / 3)
        freq = preset.frequency * (2 ** (cents / 1200))
        voice = np.zeros(n)
        for h in range(1, 8):
            if freq * h > sample_rate / 2:
                break
            voice += ((-1) ** h / h) * np.sin(2 * math.pi * freq * h * t)
        signal += voice / 7

    # Filter
    alpha = min(0.99, preset.filter_cutoff * 0.5 + 0.1)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _normalize(signal)


def synthesize_acid_lead(preset: LeadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Acid lead — resonant filter sweep (303-inspired)."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Square wave source
    signal = np.zeros(n)
    for h in range(1, 12, 2):
        if preset.frequency * h > sample_rate / 2:
            break
        signal += (1.0 / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Sweeping resonant filter (key acid character)
    progress = np.linspace(0, 1, n)
    filter_sweep = preset.filter_cutoff * np.exp(-progress * 3)

    y1, y2 = 0.0, 0.0
    for i in range(n):
        a = max(0.01, filter_sweep[i] * 0.5 + 0.05)
        y1 = y1 + a * (signal[i] - y1)
        y2 = y2 + a * (y1 - y2)
        signal[i] = y1 + preset.resonance * 2 * (y1 - y2)

    env = _adsr_envelope(n, preset, sample_rate)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

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
            LeadPreset("screech_C4", "screech", 261.63,
                       distortion=0.5, filter_cutoff=0.7, resonance=0.4),
            LeadPreset("screech_E4", "screech", 329.63,
                       distortion=0.6, filter_cutoff=0.8, resonance=0.5),
            LeadPreset("screech_G4", "screech", 392.00,
                       distortion=0.4, filter_cutoff=0.6, resonance=0.3),
            LeadPreset("screech_A4", "screech", 440.00,
                       distortion=0.7, filter_cutoff=0.9, resonance=0.6),
        ],
    )


def pluck_lead_bank() -> LeadBank:
    """Pluck leads — percussive melodic hits."""
    return LeadBank(
        name="PLUCK_LEADS",
        presets=[
            LeadPreset("pluck_C4", "pluck", 261.63, duration_s=0.4,
                       attack_s=0.002, decay_s=0.15, sustain=0.3, release_s=0.1),
            LeadPreset("pluck_E4", "pluck", 329.63, duration_s=0.4,
                       attack_s=0.003, decay_s=0.12, sustain=0.25, release_s=0.08),
            LeadPreset("pluck_G4", "pluck", 392.00, duration_s=0.4,
                       attack_s=0.002, decay_s=0.18, sustain=0.35, release_s=0.12),
            LeadPreset("pluck_A4", "pluck", 440.00, duration_s=0.4,
                       attack_s=0.001, decay_s=0.1, sustain=0.2, release_s=0.08),
        ],
    )


def fm_lead_bank() -> LeadBank:
    """FM leads — metallic bell tones."""
    return LeadBank(
        name="FM_LEADS",
        presets=[
            LeadPreset("fm_lead_C4", "fm_lead", 261.63,
                       fm_ratio=2.0, fm_depth=3.0, distortion=0.1),
            LeadPreset("fm_lead_E4", "fm_lead", 329.63,
                       fm_ratio=3.0, fm_depth=2.5, distortion=0.15),
            LeadPreset("fm_lead_G4", "fm_lead", 392.00,
                       fm_ratio=1.5, fm_depth=4.0, distortion=0.2),
            LeadPreset("fm_lead_A4", "fm_lead", 440.00,
                       fm_ratio=2.5, fm_depth=2.0, distortion=0.05),
        ],
    )


def supersaw_lead_bank() -> LeadBank:
    """Supersaw leads — massive stacked saws."""
    return LeadBank(
        name="SUPERSAW_LEADS",
        presets=[
            LeadPreset("supersaw_C4", "supersaw", 261.63, duration_s=1.0,
                       detune_cents=15, filter_cutoff=0.7, attack_s=0.05),
            LeadPreset("supersaw_E4", "supersaw", 329.63, duration_s=1.0,
                       detune_cents=20, filter_cutoff=0.8, attack_s=0.03),
            LeadPreset("supersaw_G4", "supersaw", 392.00, duration_s=1.0,
                       detune_cents=12, filter_cutoff=0.6, attack_s=0.08),
            LeadPreset("supersaw_A4", "supersaw", 440.00, duration_s=1.0,
                       detune_cents=18, filter_cutoff=0.75, attack_s=0.04),
        ],
    )


def acid_lead_bank() -> LeadBank:
    """Acid leads — resonant 303-style sweeps."""
    return LeadBank(
        name="ACID_LEADS",
        presets=[
            LeadPreset("acid_C3", "acid", 130.81, duration_s=0.6,
                       filter_cutoff=0.9, resonance=0.7, distortion=0.3),
            LeadPreset("acid_E3", "acid", 164.81, duration_s=0.6,
                       filter_cutoff=0.8, resonance=0.6, distortion=0.25),
            LeadPreset("acid_G3", "acid", 196.00, duration_s=0.6,
                       filter_cutoff=0.95, resonance=0.8, distortion=0.4),
            LeadPreset("acid_A3", "acid", 220.00, duration_s=0.6,
                       filter_cutoff=0.85, resonance=0.5, distortion=0.2),
        ],
    )


ALL_LEAD_BANKS: dict[str, callable] = {
    "screech":  screech_lead_bank,
    "pluck":    pluck_lead_bank,
    "fm_lead":  fm_lead_bank,
    "supersaw": supersaw_lead_bank,
    "acid":     acid_lead_bank,
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
