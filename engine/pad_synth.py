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

_log = get_logger("dubforge.pad_synth")


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
    """Write signal to 16-bit mono WAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    _log.info("Wrote pad WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


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
    """Lush pad — detuned saw layers with slow filter sweep."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    detune = 2 ** (preset.detune_cents / 1200)
    freqs = [preset.frequency, preset.frequency * detune,
             preset.frequency / detune]

    signal = np.zeros(n)
    for f in freqs:
        for h in range(1, 8):
            if f * h > sample_rate / 2:
                break
            signal += ((-1) ** h / h) * np.sin(2 * math.pi * f * h * t) / 3

    # Slow filter sweep using LFO
    lfo_r = preset.lfo_rate if preset.lfo_rate > 0 else 1 / PHI
    cutoff_mod = preset.filter_cutoff + 0.2 * np.sin(2 * math.pi * lfo_r * t)
    cutoff_mod = np.clip(cutoff_mod, 0.01, 0.99)

    # Simple lowpass approximation
    y = 0.0
    for i in range(n):
        y = y * (1 - cutoff_mod[i]) + signal[i] * cutoff_mod[i]
        signal[i] = y

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_dark_pad(preset: PadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Dark pad — low-register drone with harmonic movement."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Sub fundamental + detuned pair
    detune = 2 ** (preset.detune_cents / 1200)
    signal = 0.5 * np.sin(2 * math.pi * preset.frequency * t)
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * detune * t)
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency / detune * t)

    # Slow amplitude modulation
    am_rate = 1 / (PHI * 2)
    am = 0.7 + 0.3 * np.sin(2 * math.pi * am_rate * t)
    signal *= am

    # Darkness: aggressive lowpass
    alpha = max(0.01, preset.filter_cutoff * 0.3)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_shimmer_pad(preset: PadPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Shimmer pad — high-register sparkle with pitched delays."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Build from sine + octave above
    signal = 0.5 * np.sin(2 * math.pi * preset.frequency * t)
    signal += 0.35 * np.sin(2 * math.pi * preset.frequency * 2 * t)
    signal += 0.2 * np.sin(2 * math.pi * preset.frequency * 3 * t)

    # Pitch-shifted delay (simulated octave delay effect)
    delay_samples = max(1, int(sample_rate * (1 / PHI)))
    delayed = np.zeros(n)
    if delay_samples < n:
        delayed[delay_samples:] = signal[:-delay_samples] * 0.4
    signal += delayed

    # Brightness filter
    alpha = max(0.01, preset.brightness * 0.6 + 0.1)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_evolving_pad(preset: PadPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Evolving pad — cross-fading waveform morph."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Morph between sine → saw over time
    progress = np.linspace(0, 1, n)
    sine = np.sin(2 * math.pi * preset.frequency * t)

    saw = np.zeros(n)
    for h in range(1, 10):
        if preset.frequency * h > sample_rate / 2:
            break
        saw += ((-1) ** h / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Phi-timed crossfade
    morph = progress ** (1 / PHI)
    signal = sine * (1 - morph) + saw * morph

    # Detuned doubler
    detune = 2 ** (preset.detune_cents / 1200)
    doubler = np.sin(2 * math.pi * preset.frequency * detune * t)
    signal = 0.7 * signal + 0.3 * doubler

    # Sweeping filter
    cutoff = 0.1 + 0.4 * morph
    y = 0.0
    for i in range(n):
        y = y * (1 - cutoff[i]) + signal[i] * cutoff[i]
        signal[i] = y

    signal = _apply_pad_envelope(signal, preset, sample_rate)
    return _normalize(signal)


def synthesize_choir_pad(preset: PadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Choir pad — formant-filtered layers simulating vocal tones."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Rich source (many harmonics)
    source = np.zeros(n)
    for h in range(1, 12):
        if preset.frequency * h > sample_rate / 2:
            break
        source += (1.0 / h) * np.sin(2 * math.pi * preset.frequency * h * t)

    # Formant frequencies (simplified vowel 'ah')
    formants = [730, 1090, 2440]
    signal = np.zeros(n)
    for fc in formants:
        # Bandpass via resonator
        bw = fc * 0.1  # 10% bandwidth
        alpha_bp = min(0.99, bw / (sample_rate / 2))
        y1, y2 = 0.0, 0.0
        bp = np.zeros(n)
        for i in range(n):
            y1 = y1 + alpha_bp * (source[i] - y1)
            y2 = y2 + alpha_bp * (y1 - y2)
            bp[i] = y1 - y2
        signal += bp

    # Slow vibrato
    vib_depth = preset.frequency * 0.005
    phase_mod = vib_depth * np.sin(2 * math.pi * (1 / PHI) * t)
    signal *= (1 + 0.1 * np.sin(2 * math.pi * phase_mod))

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
            PadPreset("lush_C3", "lush", 130.81, duration_s=6.0,
                      detune_cents=12, filter_cutoff=0.4, attack_s=0.8),
            PadPreset("lush_E3", "lush", 164.81, duration_s=6.0,
                      detune_cents=15, filter_cutoff=0.5, attack_s=0.6),
            PadPreset("lush_G3", "lush", 196.00, duration_s=6.0,
                      detune_cents=10, filter_cutoff=0.6, attack_s=1.0),
            PadPreset("lush_A3", "lush", 220.00, duration_s=6.0,
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
            PadPreset("shimmer_C4", "shimmer", 261.63, duration_s=5.0,
                      brightness=0.8, attack_s=0.3),
            PadPreset("shimmer_E4", "shimmer", 329.63, duration_s=5.0,
                      brightness=0.9, attack_s=0.4),
            PadPreset("shimmer_G4", "shimmer", 392.00, duration_s=5.0,
                      brightness=0.7, attack_s=0.5),
            PadPreset("shimmer_A4", "shimmer", 440.00, duration_s=5.0,
                      brightness=1.0, attack_s=0.2),
        ],
    )


def evolving_pad_bank() -> PadBank:
    """Evolving pads — slow morphing textures."""
    return PadBank(
        name="EVOLVING_PADS",
        presets=[
            PadPreset("evolve_C3", "evolving", 130.81, duration_s=8.0,
                      detune_cents=15, filter_cutoff=0.3, attack_s=1.0),
            PadPreset("evolve_D3", "evolving", 146.83, duration_s=8.0,
                      detune_cents=12, filter_cutoff=0.4, attack_s=1.2),
            PadPreset("evolve_E3", "evolving", 164.81, duration_s=8.0,
                      detune_cents=20, filter_cutoff=0.25, attack_s=0.8),
            PadPreset("evolve_G3", "evolving", 196.00, duration_s=8.0,
                      detune_cents=10, filter_cutoff=0.35, attack_s=1.5),
        ],
    )


def choir_pad_bank() -> PadBank:
    """Choir pads — formant-filtered vocal textures."""
    return PadBank(
        name="CHOIR_PADS",
        presets=[
            PadPreset("choir_C3", "choir", 130.81, duration_s=6.0,
                      attack_s=0.6, brightness=0.6),
            PadPreset("choir_E3", "choir", 164.81, duration_s=6.0,
                      attack_s=0.8, brightness=0.7),
            PadPreset("choir_G3", "choir", 196.00, duration_s=6.0,
                      attack_s=0.5, brightness=0.5),
            PadPreset("choir_A3", "choir", 220.00, duration_s=6.0,
                      attack_s=0.7, brightness=0.8),
        ],
    )


ALL_PAD_BANKS: dict[str, callable] = {
    "lush":     lush_pad_bank,
    "dark":     dark_pad_bank,
    "shimmer":  shimmer_pad_bank,
    "evolving": evolving_pad_bank,
    "choir":    choir_pad_bank,
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
