"""
DUBFORGE Engine — Sidechain Compression / Ducking Engine

Generates sidechain ducking envelopes for pumping bass effects.
All timing parameters use phi-ratio relationships.

Shapes:
    pump        — classic 4-on-floor sidechain pump
    hard_cut    — aggressive instant duck with fast release
    smooth      — gentle volume ducking
    bounce      — retriggered multi-pump per beat
    phi_curve   — golden-ratio shaped release curve

Banks: 5 shape types × 4 presets = 20 presets
"""

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from engine.config_loader import PHI

SAMPLE_RATE = 44100
# --- Data Models ----------------------------------------------------------

@dataclass
class SidechainPreset:
    """A single sidechain ducking preset."""
    name: str
    shape: str  # pump | hard_cut | smooth | bounce | phi_curve
    attack_ms: float = 0.5
    release_ms: float = 150.0
    depth: float = 1.0          # 0-1, how much ducking
    hold_ms: float = 10.0
    curve_exp: float = 2.0      # exponent for release curve
    retrigger_rate: float = 1.0  # bounces per beat (for bounce shape)
    mix: float = 1.0
    bpm: float = 150.0


@dataclass
class SidechainBank:
    """Collection of sidechain presets."""
    name: str
    presets: list[SidechainPreset] = field(default_factory=list)


# --- Envelope Generators -------------------------------------------------

def _normalize(signal: np.ndarray) -> np.ndarray:
    mx = np.max(np.abs(signal))
    if mx > 1e-10:
        return signal / mx
    return signal


def generate_pump_envelope(preset: SidechainPreset,
                           duration_s: float = 4.0,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Classic 4-on-floor pump — duck on every beat."""
    n = int(duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    attack_samples = max(1, int(preset.attack_ms / 1000.0 * sample_rate))
    hold_samples = max(1, int(preset.hold_ms / 1000.0 * sample_rate))
    release_samples = max(1, int(preset.release_ms / 1000.0 * sample_rate))

    envelope = np.ones(n)
    pos = 0
    while pos < n:
        # Attack (duck down)
        for i in range(min(attack_samples, n - pos)):
            t = i / max(1, attack_samples)
            envelope[pos + i] = 1.0 - preset.depth * t

        pos += attack_samples
        # Hold at ducked level
        for i in range(min(hold_samples, max(0, n - pos))):
            envelope[pos + i] = 1.0 - preset.depth
        pos += hold_samples
        # Release (come back up)
        for i in range(min(release_samples, max(0, n - pos))):
            t = i / max(1, release_samples)
            curve = t ** preset.curve_exp
            envelope[pos + i] = (1.0 - preset.depth) + preset.depth * curve
        pos += release_samples
        # Fill rest of beat with 1.0
        remaining = beat_samples - attack_samples - hold_samples - release_samples
        pos += max(0, remaining)

    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope * preset.mix + (1.0 - preset.mix) * np.ones(n)


def generate_hard_cut_envelope(preset: SidechainPreset,
                               duration_s: float = 4.0,
                               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Hard cut — instant duck, fast release."""
    n = int(duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    release_samples = max(1, int(preset.release_ms / 1000.0 * sample_rate))

    envelope = np.ones(n)
    pos = 0
    while pos < n:
        # Instant duck
        if pos < n:
            envelope[pos] = 1.0 - preset.depth
        # Fast release
        for i in range(1, min(release_samples, max(0, n - pos))):
            t = i / max(1, release_samples)
            envelope[pos + i] = (1.0 - preset.depth) + preset.depth * (t ** 1.5)
        pos += beat_samples

    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope * preset.mix + (1.0 - preset.mix) * np.ones(n)


def generate_smooth_envelope(preset: SidechainPreset,
                             duration_s: float = 4.0,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Smooth — gentle sinusoidal ducking."""
    n = int(duration_s * sample_rate)
    beat_freq = preset.bpm / 60.0
    t = np.linspace(0, duration_s, n, endpoint=False)
    # Half-cosine per beat for smooth pump
    phase = beat_freq * t * 2 * np.pi
    envelope = 1.0 - preset.depth * 0.5 * (1.0 - np.cos(phase))
    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope * preset.mix + (1.0 - preset.mix) * np.ones(n)


def generate_bounce_envelope(preset: SidechainPreset,
                             duration_s: float = 4.0,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Bounce — multiple retriggers per beat."""
    n = int(duration_s * sample_rate)
    retrig_freq = (preset.bpm / 60.0) * preset.retrigger_rate
    retrig_samples = max(1, int(sample_rate / retrig_freq))
    release_samples = max(1, int(preset.release_ms / 1000.0 * sample_rate))

    envelope = np.ones(n)
    pos = 0
    while pos < n:
        # Quick duck
        duck_len = min(release_samples, retrig_samples, n - pos)
        for i in range(duck_len):
            t = i / max(1, duck_len)
            envelope[pos + i] = (1.0 - preset.depth) + preset.depth * (t ** preset.curve_exp)
        pos += retrig_samples

    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope * preset.mix + (1.0 - preset.mix) * np.ones(n)


def generate_phi_curve_envelope(preset: SidechainPreset,
                                duration_s: float = 4.0,
                                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Phi curve — golden-ratio shaped release envelope."""
    n = int(duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    attack_samples = max(1, int(preset.attack_ms / 1000.0 * sample_rate))
    # Phi-split: release uses phi ratio of beat duration
    phi_release = int(beat_samples / PHI)
    phi_hold = beat_samples - phi_release - attack_samples

    envelope = np.ones(n)
    pos = 0
    while pos < n:
        # Attack
        for i in range(min(attack_samples, n - pos)):
            t = i / max(1, attack_samples)
            envelope[pos + i] = 1.0 - preset.depth * t
        pos += attack_samples
        # Hold
        for i in range(min(max(0, phi_hold), max(0, n - pos))):
            envelope[pos + i] = 1.0 - preset.depth
        pos += max(0, phi_hold)
        # Phi-shaped release (1/phi exponent)
        for i in range(min(phi_release, max(0, n - pos))):
            t = i / max(1, phi_release)
            curve = t ** (1.0 / PHI)
            envelope[pos + i] = (1.0 - preset.depth) + preset.depth * curve
        pos += phi_release

    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope * preset.mix + (1.0 - preset.mix) * np.ones(n)


# --- Router ---------------------------------------------------------------

def generate_sidechain(preset: SidechainPreset,
                       duration_s: float = 4.0,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct sidechain envelope generator."""
    generators = {
        "pump": generate_pump_envelope,
        "hard_cut": generate_hard_cut_envelope,
        "smooth": generate_smooth_envelope,
        "bounce": generate_bounce_envelope,
        "phi_curve": generate_phi_curve_envelope,
    }
    gen = generators.get(preset.shape)
    if gen is None:
        raise ValueError(f"Unknown sidechain shape: {preset.shape}")
    return gen(preset, duration_s, sample_rate)


def apply_sidechain(signal: np.ndarray, preset: SidechainPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply sidechain ducking envelope to an audio signal."""
    duration_s = len(signal) / sample_rate
    envelope = generate_sidechain(preset, duration_s, sample_rate)
    # Match lengths
    if len(envelope) > len(signal):
        envelope = envelope[:len(signal)]
    elif len(envelope) < len(signal):
        envelope = np.pad(envelope, (0, len(signal) - len(envelope)),
                          constant_values=1.0)
    return signal * envelope


# --- Banks ----------------------------------------------------------------

def pump_sidechain_bank() -> SidechainBank:
    """Classic pump sidechain presets."""
    return SidechainBank(
        name="PUMP_SIDECHAIN",
        presets=[
            SidechainPreset("Pump Standard", "pump", attack_ms=0.5, release_ms=150.0, depth=0.9),
            SidechainPreset("Pump Deep", "pump", attack_ms=1.0, release_ms=200.0, depth=1.0),
            SidechainPreset("Pump Light", "pump", attack_ms=0.5, release_ms=100.0, depth=0.6),
            SidechainPreset("Pump Slow", "pump", attack_ms=2.0, release_ms=300.0, depth=0.8),
        ],
    )


def hard_cut_sidechain_bank() -> SidechainBank:
    """Aggressive hard-cut sidechain presets."""
    return SidechainBank(
        name="HARD_CUT_SIDECHAIN",
        presets=[
            SidechainPreset("Hard Cut Weapon", "hard_cut", release_ms=80.0, depth=1.0),
            SidechainPreset("Hard Cut Snappy", "hard_cut", release_ms=50.0, depth=0.95),
            SidechainPreset("Hard Cut Medium", "hard_cut", release_ms=120.0, depth=0.85),
            SidechainPreset("Hard Cut Extreme", "hard_cut", release_ms=40.0, depth=1.0),
        ],
    )


def smooth_sidechain_bank() -> SidechainBank:
    """Gentle smooth sidechain presets."""
    return SidechainBank(
        name="SMOOTH_SIDECHAIN",
        presets=[
            SidechainPreset("Smooth Standard", "smooth", depth=0.5),
            SidechainPreset("Smooth Deep", "smooth", depth=0.8),
            SidechainPreset("Smooth Subtle", "smooth", depth=0.3),
            SidechainPreset("Smooth Wide", "smooth", depth=0.65, release_ms=200.0),
        ],
    )


def bounce_sidechain_bank() -> SidechainBank:
    """Multi-trigger bounce sidechain presets."""
    return SidechainBank(
        name="BOUNCE_SIDECHAIN",
        presets=[
            SidechainPreset("Bounce 2x", "bounce", retrigger_rate=2.0, depth=0.8),
            SidechainPreset("Bounce 4x", "bounce", retrigger_rate=4.0, depth=0.7),
            SidechainPreset("Bounce Triplet", "bounce", retrigger_rate=3.0, depth=0.85),
            SidechainPreset("Bounce 8x Stutter", "bounce", retrigger_rate=8.0, depth=0.6),
        ],
    )


def phi_curve_sidechain_bank() -> SidechainBank:
    """Golden-ratio curve sidechain presets."""
    return SidechainBank(
        name="PHI_CURVE_SIDECHAIN",
        presets=[
            SidechainPreset("Phi Standard", "phi_curve", depth=0.9),
            SidechainPreset("Phi Deep", "phi_curve", depth=1.0, attack_ms=1.0),
            SidechainPreset("Phi Light", "phi_curve", depth=0.5),
            SidechainPreset("Phi Fast", "phi_curve", depth=0.85, attack_ms=0.2),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_SIDECHAIN_BANKS: dict[str, Callable[[], SidechainBank]] = {
    "pump": pump_sidechain_bank,
    "hard_cut": hard_cut_sidechain_bank,
    "smooth": smooth_sidechain_bank,
    "bounce": bounce_sidechain_bank,
    "phi_curve": phi_curve_sidechain_bank,
}


# --- WAV Export ---------------------------------------------------------------

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _export_path(path: Path) -> str:
    """Return stable POSIX-style paths for cross-platform callers/tests."""
    return path.as_posix()


def _test_signal(duration_s: float = 1.0, freq: float = 200.0,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a test sine for processing demos."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return 0.8 * np.sin(2.0 * np.pi * freq * t)


def export_sidechain_demos(output_dir: str = "output") -> list[str]:
    """Render all sidechain presets applied to a test signal and write .wav."""
    sig = _test_signal(duration_s=2.0)
    out = Path(output_dir) / "wavetables" / "sidechain"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for bank_name, bank_fn in ALL_SIDECHAIN_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            processed = apply_sidechain(sig, preset, SAMPLE_RATE)
            fname = f"sc_{preset.name}.wav"
            _write_wav(out / fname, processed)
            paths.append(_export_path(out / fname))
    return paths


# --- Manifest -------------------------------------------------------------

def write_sidechain_manifest(output_dir: str = "output") -> dict:
    """Write sidechain manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_SIDECHAIN_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "sidechain_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_sidechain_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_sidechain_demos()
    print(f"Sidechain Engine: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
