"""
DUBFORGE Engine — Formant Synthesizer

Synthesizes vowel/formant-shaped sounds for dubstep:
  - Ah Formant:    open vowel 'ah' resonance
  - Ee Formant:    bright vowel 'ee' resonance
  - Oh Formant:    round vowel 'oh' resonance
  - Oo Formant:    deep vowel 'oo' resonance
  - Morph Formant: sweeping between vowel shapes

All sounds use phi-ratio envelopes and Fibonacci harmonics.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/formant_*.wav
    output/analysis/formant_synth_manifest.json
"""

from __future__ import annotations

import json
from typing import Any, Callable
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import write_wav

_log = get_logger("dubforge.formant_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FormantPreset:
    """Settings for a single formant sound."""
    name: str
    formant_type: str       # ah | ee | oh | oo | morph
    frequency: float = 110.0
    duration_s: float = 2.0
    formant1: float = 800.0   # F1 center freq Hz
    formant2: float = 1200.0  # F2 center freq Hz
    bandwidth: float = 100.0
    brightness: float = 0.6
    attack_s: float = 0.05
    release_s: float = 0.3
    distortion: float = 0.0
    vibrato_rate: float = 0.0


@dataclass
class FormantBank:
    """Collection of formant presets."""
    name: str
    presets: list[FormantPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

# Vowel formant frequencies (F1, F2) in Hz
VOWEL_FORMANTS = {
    "ah": (730, 1090),
    "ee": (270, 2290),
    "oh": (570, 840),
    "oo": (300, 870),
}


def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s, sample_rate=sample_rate)
    return str(path)



def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak
    return signal


def _envelope(n: int, preset: FormantPreset,
              sample_rate: int) -> np.ndarray:
    attack = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return env


def _formant_filter(signal: np.ndarray, f_center: float,
                    bw: float, sample_rate: int) -> np.ndarray:
    """Simple resonant peak at f_center via additive sin modulation."""
    n = len(signal)
    t = np.arange(n) / sample_rate
    resonance = np.sin(2 * math.pi * f_center * t) * np.exp(-bw * t * 0.1)
    return signal * 0.6 + resonance * 0.4 * np.max(np.abs(signal))


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_ah_formant(preset: FormantPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ah formant — open vowel 'ah' resonance."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Rich source with harmonics
    signal = np.zeros(n)
    for h in range(1, 15):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / h

    # Apply 'ah' formant resonances
    f1, f2 = VOWEL_FORMANTS["ah"]
    res1 = np.sin(2 * math.pi * f1 * t)
    res2 = np.sin(2 * math.pi * f2 * t) * 0.7
    signal = signal * 0.5 + (res1 + res2) * 0.25 * preset.brightness

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_ee_formant(preset: FormantPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ee formant — bright vowel 'ee' resonance."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, 12):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / h

    f1, f2 = VOWEL_FORMANTS["ee"]
    res1 = np.sin(2 * math.pi * f1 * t)
    res2 = np.sin(2 * math.pi * f2 * t) * 0.6
    signal = signal * 0.5 + (res1 + res2) * 0.3 * preset.brightness

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_oh_formant(preset: FormantPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Oh formant — round vowel 'oh' resonance."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, 10):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / (h ** 0.8)

    f1, f2 = VOWEL_FORMANTS["oh"]
    res1 = np.sin(2 * math.pi * f1 * t)
    res2 = np.sin(2 * math.pi * f2 * t) * 0.8
    signal = signal * 0.5 + (res1 + res2) * 0.25 * preset.brightness

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_oo_formant(preset: FormantPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Oo formant — deep vowel 'oo' resonance."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, 8):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / h

    f1, f2 = VOWEL_FORMANTS["oo"]
    res1 = np.sin(2 * math.pi * f1 * t)
    res2 = np.sin(2 * math.pi * f2 * t) * 0.5
    signal = signal * 0.6 + (res1 + res2) * 0.2 * preset.brightness

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_morph_formant(preset: FormantPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Morph formant — sweeping between vowel shapes."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, 12):
        signal += np.sin(2 * math.pi * preset.frequency * h * t) / h

    # Morph between ah→ee→oh→oo over duration
    morph = np.linspace(0, 3, n)
    vowels = ["ah", "ee", "oh", "oo"]
    result = np.zeros(n)
    for i in range(n):
        idx = min(int(morph[i]), 2)
        frac = morph[i] - idx
        v1 = vowels[idx]
        v2 = vowels[idx + 1]
        f1a, f2a = VOWEL_FORMANTS[v1]
        f1b, f2b = VOWEL_FORMANTS[v2]
        f1_cur = f1a + (f1b - f1a) * frac
        f2_cur = f2a + (f2b - f2a) * frac
        result[i] = (signal[i] * 0.5
                     + 0.25 * math.sin(2 * math.pi * f1_cur * t[i])
                     + 0.25 * math.sin(2 * math.pi * f2_cur * t[i]))

    result *= preset.brightness

    if preset.distortion > 0:
        result = np.tanh(result * (1 + preset.distortion * 3))
    result *= env
    return _normalize(result)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_formant(preset: FormantPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct formant synthesizer."""
    synths = {
        "ah": synthesize_ah_formant,
        "ee": synthesize_ee_formant,
        "oh": synthesize_oh_formant,
        "oo": synthesize_oo_formant,
        "morph": synthesize_morph_formant,
    }
    fn = synths.get(preset.formant_type)
    if fn is None:
        raise ValueError(f"Unknown formant type: {preset.formant_type}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def ah_formant_bank() -> FormantBank:
    """Ah formant presets."""
    return FormantBank(
        name="AH_FORMANTS",
        presets=[
            FormantPreset("ah_E2", "ah", 82.41, brightness=0.7),
            FormantPreset("ah_A2", "ah", 110.00, brightness=0.8),
            FormantPreset("ah_C3", "ah", 130.81, brightness=0.6, distortion=0.1),
            FormantPreset("ah_G2", "ah", 98.00, brightness=0.75, duration_s=3.0),
        ],
    )


def ee_formant_bank() -> FormantBank:
    """Ee formant presets."""
    return FormantBank(
        name="EE_FORMANTS",
        presets=[
            FormantPreset("ee_E2", "ee", 82.41, brightness=0.8),
            FormantPreset("ee_A2", "ee", 110.00, brightness=0.9),
            FormantPreset("ee_C3", "ee", 130.81, brightness=0.7, distortion=0.15),
            FormantPreset("ee_G2", "ee", 98.00, brightness=0.85),
        ],
    )


def oh_formant_bank() -> FormantBank:
    """Oh formant presets."""
    return FormantBank(
        name="OH_FORMANTS",
        presets=[
            FormantPreset("oh_E2", "oh", 82.41, brightness=0.6),
            FormantPreset("oh_A2", "oh", 110.00, brightness=0.7),
            FormantPreset("oh_C3", "oh", 130.81, brightness=0.5, distortion=0.1),
            FormantPreset("oh_G2", "oh", 98.00, brightness=0.65, duration_s=3.0),
        ],
    )


def oo_formant_bank() -> FormantBank:
    """Oo formant presets."""
    return FormantBank(
        name="OO_FORMANTS",
        presets=[
            FormantPreset("oo_E2", "oo", 82.41, brightness=0.5),
            FormantPreset("oo_A2", "oo", 110.00, brightness=0.6),
            FormantPreset("oo_C3", "oo", 130.81, brightness=0.4, distortion=0.1),
            FormantPreset("oo_G2", "oo", 98.00, brightness=0.55, duration_s=3.0),
        ],
    )


def morph_formant_bank() -> FormantBank:
    """Morph formant presets."""
    return FormantBank(
        name="MORPH_FORMANTS",
        presets=[
            FormantPreset("morph_E2_slow", "morph", 82.41, duration_s=4.0,
                          brightness=0.7),
            FormantPreset("morph_A2_fast", "morph", 110.00, duration_s=2.0,
                          brightness=0.8),
            FormantPreset("morph_C3_dist", "morph", 130.81, duration_s=3.0,
                          brightness=0.6, distortion=0.2),
            FormantPreset("morph_G2_long", "morph", 98.00, duration_s=6.0,
                          brightness=0.75),
        ],
    )


ALL_FORMANT_BANKS: dict[str, Callable[..., Any]] = {
    "ah": ah_formant_bank,
    "ee": ee_formant_bank,
    "oh": oh_formant_bank,
    "oo": oo_formant_bank,
    "morph": morph_formant_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST & MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_formant_manifest(output_dir: str = "output") -> dict:
    """Write formant synth manifest JSON and return summary."""
    manifest: dict = {"banks": {}}
    out_base = Path(output_dir)
    wav_dir = out_base / "wavetables"
    wav_dir.mkdir(parents=True, exist_ok=True)

    for bank_key, bank_fn in ALL_FORMANT_BANKS.items():
        bank = bank_fn()
        bank_data: list[dict] = []
        for preset in bank.presets:
            signal = synthesize_formant(preset)
            wav_path = wav_dir / f"formant_{preset.name}.wav"
            _write_wav(signal, str(wav_path))
            bank_data.append({
                "name": preset.name,
                "type": preset.formant_type,
                "frequency": preset.frequency,
                "wav": str(wav_path),
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = {
            "bank_name": bank.name,
            "presets": bank_data,
        }

    manifest_path = out_base / "analysis" / "formant_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Formant manifest → %s", manifest_path)
    return manifest


def main():
    """Generate all formant synth presets."""
    _log.info("═══ Formant Synthesizer ═══")
    write_formant_manifest()
    _log.info("Done.")


if __name__ == "__main__":
    main()
