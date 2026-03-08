"""
DUBFORGE Engine — Drone Synthesizer

Synthesizes sustained drone/atmosphere sounds for dubstep:
  - Harmonic Drone: stacked harmonic series drone
  - Beating Drone:  detuned unison for beating effect
  - Dark Drone:     low filtered rumble drone
  - Shimmer Drone:  high-register shimmering texture
  - Evolving Drone: slowly modulating long drone

All sounds use phi-ratio harmonics and Fibonacci tuning.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/drone_*.wav
    output/analysis/drone_synth_manifest.json
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

_log = get_logger("dubforge.drone_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DronePreset:
    """Settings for a single drone sound."""
    name: str
    drone_type: str         # harmonic | beating | dark | shimmer | evolving
    frequency: float = 55.0
    duration_s: float = 8.0
    num_voices: int = 5
    detune_cents: float = 5.0
    brightness: float = 0.5
    movement: float = 0.3   # modulation amount 0-1
    attack_s: float = 1.0
    release_s: float = 2.0
    distortion: float = 0.0
    reverb_amount: float = 0.4


@dataclass
class DroneBank:
    """Collection of drone presets."""
    name: str
    presets: list[DronePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    return str(out)


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak
    return signal


def _envelope(n: int, preset: DronePreset,
              sample_rate: int) -> np.ndarray:
    attack = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return env


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_harmonic_drone(preset: DronePreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Harmonic drone — stacked harmonic series."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, preset.num_voices + 1):
        amp = 1.0 / (h ** (1 - preset.brightness * 0.5))
        freq = preset.frequency * h
        # Slight movement via slow modulation
        mod = 1.0 + preset.movement * 0.01 * np.sin(
            2 * math.pi * (0.1 * h / PHI) * t)
        signal += amp * np.sin(2 * math.pi * freq * mod * t)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


def synthesize_beating_drone(preset: DronePreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Beating drone — detuned unison voices creating beat frequencies."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    cent_ratio = 2 ** (preset.detune_cents / 1200)
    for v in range(preset.num_voices):
        offset = (v - preset.num_voices // 2) * cent_ratio
        freq = preset.frequency * (1 + offset * 0.001)
        signal += np.sin(2 * math.pi * freq * t)

    # Add subtle sub
    signal += 0.3 * np.sin(2 * math.pi * preset.frequency * t)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 2))
    signal *= env
    return _normalize(signal)


def synthesize_dark_drone(preset: DronePreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Dark drone — low filtered rumble drone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    # Low harmonics only
    signal = np.zeros(n)
    max_h = max(2, int(3 + preset.brightness * 5))
    for h in range(1, max_h + 1):
        amp = 1.0 / h
        mod = 1.0 + preset.movement * 0.005 * np.sin(
            2 * math.pi * 0.05 * h * t)
        signal += amp * np.sin(2 * math.pi * preset.frequency * h * mod * t)

    # Rumble modulation
    rumble = 0.3 * np.sin(2 * math.pi * 0.5 * t) * preset.movement
    signal *= (1 + rumble)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    signal *= env
    return _normalize(signal)


def synthesize_shimmer_drone(preset: DronePreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Shimmer drone — high-register shimmering texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    # High harmonics and octave-shifted layers
    for h in range(1, preset.num_voices + 1):
        freq = preset.frequency * (2 * h)  # octave up
        amp = preset.brightness / h
        phase_mod = preset.movement * 0.02 * np.sin(
            2 * math.pi * (0.15 * h) * t)
        signal += amp * np.sin(2 * math.pi * freq * t + phase_mod)

    # Add sparkle
    rng = np.random.default_rng(77)
    sparkle = rng.standard_normal(n) * 0.05 * preset.brightness
    signal += sparkle

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 2))
    signal *= env
    return _normalize(signal)


def synthesize_evolving_drone(preset: DronePreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Evolving drone — slowly modulating long drone."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    env = _envelope(n, preset, sample_rate)

    signal = np.zeros(n)
    for h in range(1, preset.num_voices + 1):
        # Each voice evolves at different rate
        mod_rate = 0.05 + 0.03 * h / PHI
        amp_mod = 0.5 + 0.5 * np.sin(2 * math.pi * mod_rate * t)
        freq_mod = 1.0 + preset.movement * 0.005 * np.sin(
            2 * math.pi * mod_rate * PHI * t)
        freq = preset.frequency * h * freq_mod
        signal += amp_mod / h * np.sin(2 * math.pi * freq * t)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    signal *= env
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_drone(preset: DronePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct drone synthesizer."""
    synths = {
        "harmonic": synthesize_harmonic_drone,
        "beating": synthesize_beating_drone,
        "dark": synthesize_dark_drone,
        "shimmer": synthesize_shimmer_drone,
        "evolving": synthesize_evolving_drone,
    }
    fn = synths.get(preset.drone_type)
    if fn is None:
        raise ValueError(f"Unknown drone type: {preset.drone_type}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def harmonic_drone_bank() -> DroneBank:
    """Harmonic drone presets."""
    return DroneBank(
        name="HARMONIC_DRONES",
        presets=[
            DronePreset("hdrone_A1", "harmonic", 55.0, brightness=0.6,
                        movement=0.3),
            DronePreset("hdrone_E1", "harmonic", 41.20, brightness=0.5,
                        movement=0.4, num_voices=7),
            DronePreset("hdrone_C2", "harmonic", 65.41, brightness=0.7,
                        movement=0.2),
            DronePreset("hdrone_D2", "harmonic", 73.42, brightness=0.8,
                        movement=0.5, distortion=0.1),
        ],
    )


def beating_drone_bank() -> DroneBank:
    """Beating drone presets."""
    return DroneBank(
        name="BEATING_DRONES",
        presets=[
            DronePreset("bdrone_A1", "beating", 55.0, detune_cents=5.0,
                        num_voices=5),
            DronePreset("bdrone_E1", "beating", 41.20, detune_cents=8.0,
                        num_voices=7),
            DronePreset("bdrone_C2", "beating", 65.41, detune_cents=3.0,
                        num_voices=3),
            DronePreset("bdrone_F1", "beating", 43.65, detune_cents=10.0,
                        num_voices=9),
        ],
    )


def dark_drone_bank() -> DroneBank:
    """Dark drone presets."""
    return DroneBank(
        name="DARK_DRONES",
        presets=[
            DronePreset("ddrone_A0", "dark", 27.50, brightness=0.2,
                        movement=0.4),
            DronePreset("ddrone_E1", "dark", 41.20, brightness=0.3,
                        movement=0.5, distortion=0.2),
            DronePreset("ddrone_C1", "dark", 32.70, brightness=0.15,
                        movement=0.3),
            DronePreset("ddrone_D1", "dark", 36.71, brightness=0.25,
                        movement=0.6, distortion=0.1),
        ],
    )


def shimmer_drone_bank() -> DroneBank:
    """Shimmer drone presets."""
    return DroneBank(
        name="SHIMMER_DRONES",
        presets=[
            DronePreset("sdrone_A2", "shimmer", 110.0, brightness=0.8,
                        movement=0.3),
            DronePreset("sdrone_E2", "shimmer", 82.41, brightness=0.9,
                        movement=0.4),
            DronePreset("sdrone_C3", "shimmer", 130.81, brightness=0.7,
                        movement=0.5, num_voices=7),
            DronePreset("sdrone_G2", "shimmer", 98.00, brightness=0.85,
                        movement=0.2),
        ],
    )


def evolving_drone_bank() -> DroneBank:
    """Evolving drone presets."""
    return DroneBank(
        name="EVOLVING_DRONES",
        presets=[
            DronePreset("edrone_A1_slow", "evolving", 55.0, duration_s=12.0,
                        movement=0.5, brightness=0.6),
            DronePreset("edrone_E1_deep", "evolving", 41.20, duration_s=10.0,
                        movement=0.7, brightness=0.4),
            DronePreset("edrone_C2_mod", "evolving", 65.41, duration_s=8.0,
                        movement=0.8, brightness=0.7),
            DronePreset("edrone_F1_long", "evolving", 43.65, duration_s=16.0,
                        movement=0.6, brightness=0.5),
        ],
    )


ALL_DRONE_BANKS: dict[str, callable] = {
    "harmonic": harmonic_drone_bank,
    "beating": beating_drone_bank,
    "dark": dark_drone_bank,
    "shimmer": shimmer_drone_bank,
    "evolving": evolving_drone_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST & MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_drone_manifest(output_dir: str = "output") -> dict:
    """Write drone synth manifest JSON and return summary."""
    manifest: dict = {"banks": {}}
    out_base = Path(output_dir)
    wav_dir = out_base / "wavetables"
    wav_dir.mkdir(parents=True, exist_ok=True)

    for bank_key, bank_fn in ALL_DRONE_BANKS.items():
        bank = bank_fn()
        bank_data: list[dict] = []
        for preset in bank.presets:
            signal = synthesize_drone(preset)
            wav_path = wav_dir / f"drone_{preset.name}.wav"
            _write_wav(signal, str(wav_path))
            bank_data.append({
                "name": preset.name,
                "type": preset.drone_type,
                "frequency": preset.frequency,
                "wav": str(wav_path),
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = {
            "bank_name": bank.name,
            "presets": bank_data,
        }

    manifest_path = out_base / "analysis" / "drone_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    _log.info("Drone manifest → %s", manifest_path)
    return manifest


def main():
    """Generate all drone synth presets."""
    _log.info("═══ Drone Synthesizer ═══")
    write_drone_manifest()
    _log.info("Done.")


if __name__ == "__main__":
    main()
