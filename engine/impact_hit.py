"""
DUBFORGE Engine — Impact Hit

Impact/hit generator for drops and punctuation. Five impact types:
sub_boom, metal_crash, cinematic_hit, distorted_impact, reverse_hit —
all governed by phi/Fibonacci doctrine.

Outputs:
    output/wavetables/impact_*.wav
    output/analysis/impact_hit_manifest.json
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

logger = get_logger(__name__)


@dataclass
class ImpactPreset:
    """Configuration for an impact/hit synthesis patch."""
    name: str
    impact_type: str  # sub_boom | metal_crash | cinematic_hit | distorted_impact | reverse_hit
    duration_s: float = 2.0
    frequency: float = 50.0
    decay_s: float = 1.5
    brightness: float = 0.5
    intensity: float = 0.9
    distortion: float = 0.0
    reverb_amount: float = 0.4


@dataclass
class ImpactBank:
    """A named collection of impact presets."""
    name: str
    presets: list[ImpactPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        return signal / peak * 0.95
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_sub_boom(preset: ImpactPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sub boom — massive low frequency impact."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Pitch drops rapidly from higher frequency to sub
    start_freq = preset.frequency * 4
    freq_curve = start_freq * np.exp(-t * 8 / preset.decay_s) + preset.frequency
    phase = np.cumsum(2 * math.pi * freq_curve / sample_rate)
    signal = np.sin(phase)

    # Sub harmonic layer
    sub_phase = np.cumsum(2 * math.pi * preset.frequency * np.ones(n) / sample_rate)
    signal += 0.6 * np.sin(sub_phase)

    # Exponential decay envelope
    env = np.exp(-t * 3 / preset.decay_s) * preset.intensity
    # Hard transient click
    click_n = max(1, int(0.003 * sample_rate))
    click_env = np.zeros(n)
    click_env[:click_n] = np.linspace(1.0, 0, click_n) ** 0.5
    signal = signal * env + 0.3 * np.sin(2 * math.pi * 200 * t) * click_env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 6))
    return _normalize(signal)


def synthesize_metal_crash(preset: ImpactPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Metal crash — bright metallic impact texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Metallic partials at inharmonic ratios
    ratios = [1.0, 1.47, 2.09, 2.56, 3.14, 4.27, 5.63, 7.11]
    signal = np.zeros(n)
    for r in ratios:
        freq = preset.frequency * r
        if freq > sample_rate / 2:
            break
        amp = 1.0 / (r ** 0.5)
        decay_rate = 2 + r * 0.8
        signal += amp * np.sin(2 * math.pi * freq * t) * np.exp(-t * decay_rate / preset.decay_s)

    # Add noise burst for attack
    noise_burst = rng.standard_normal(n)
    noise_env = np.exp(-t * 20) * preset.brightness
    signal += noise_burst * noise_env

    # Overall envelope
    env = np.exp(-t * 2 / preset.decay_s)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


def synthesize_cinematic_hit(preset: ImpactPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Cinematic hit — layered boom + noise + tone."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(77)

    # Sub layer — pitch-dropping boom
    drop_freq = preset.frequency * 3 * np.exp(-t * 6) + preset.frequency
    phase = np.cumsum(2 * math.pi * drop_freq / sample_rate)
    sub_layer = np.sin(phase) * np.exp(-t * 2 / preset.decay_s)

    # Mid tonal layer
    mid_layer = np.zeros(n)
    for h in [1, PHI, PHI ** 2]:
        freq = preset.frequency * h * 3
        if freq < sample_rate / 2:
            mid_layer += np.sin(2 * math.pi * freq * t) * np.exp(-t * 4 / preset.decay_s)
    mid_layer *= 0.4

    # Noise transient
    noise = rng.standard_normal(n)
    noise_env = np.exp(-t * 15) * preset.brightness
    noise_layer = noise * noise_env

    signal = sub_layer + mid_layer + noise_layer

    # Overall envelope
    env = np.ones(n)
    env *= np.exp(-t * 1.5 / preset.decay_s)
    env[:max(1, int(0.001 * sample_rate))] *= np.linspace(0, 1,
                                                           max(1, int(0.001 * sample_rate)))
    signal *= env * preset.intensity

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))
    return _normalize(signal)


def synthesize_distorted_impact(preset: ImpactPreset,
                                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Distorted impact — heavy saturation on a transient hit."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Raw sharp waveform
    freq = preset.frequency
    signal = np.sin(2 * math.pi * freq * t)
    signal += 0.5 * np.sin(2 * math.pi * freq * 2 * t)
    signal += 0.3 * np.sin(2 * math.pi * freq * 3 * t)

    # Pitch drop on attack
    pitch_env = np.exp(-t * 12)
    fast_phase = np.cumsum(2 * math.pi * freq * 4 * pitch_env / sample_rate)
    signal += 0.6 * np.sin(fast_phase)

    # Heavy saturation
    drive = 3.0 + preset.distortion * 10
    signal = np.tanh(signal * drive)

    # Decay envelope
    env = np.exp(-t * 3 / preset.decay_s) * preset.intensity
    signal *= env

    return _normalize(signal)


def synthesize_reverse_hit(preset: ImpactPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Reverse hit — reversed impact for pre-drop effects."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(99)

    # Forward impact first
    freq = preset.frequency
    drop_freq = freq * 3 * np.exp(-t * 8) + freq
    phase = np.cumsum(2 * math.pi * drop_freq / sample_rate)
    tone = np.sin(phase)

    # Noise layer
    noise = rng.standard_normal(n) * 0.3
    noise_env = np.exp(-t * 10)
    forward = (tone + noise * noise_env) * np.exp(-t * 2 / preset.decay_s)

    # Reverse it
    signal = forward[::-1].copy()

    # Fade out tail
    fade_n = max(1, int(0.05 * sample_rate))
    signal[-fade_n:] *= np.linspace(1, 0, fade_n)

    signal *= preset.intensity

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_impact(preset: ImpactPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct impact hit synthesizer."""
    synthesizers = {
        "sub_boom": synthesize_sub_boom,
        "metal_crash": synthesize_metal_crash,
        "cinematic_hit": synthesize_cinematic_hit,
        "distorted_impact": synthesize_distorted_impact,
        "reverse_hit": synthesize_reverse_hit,
    }
    fn = synthesizers.get(preset.impact_type)
    if fn is None:
        raise ValueError(f"Unknown impact_type: {preset.impact_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 presets = 20
# ═══════════════════════════════════════════════════════════════════════════


def sub_boom_bank() -> ImpactBank:
    """Sub boom impacts — massive low-end hits."""
    return ImpactBank(
        name="SUB_BOOMS",
        presets=[
            ImpactPreset("subboom_30hz_short", "sub_boom", duration_s=1.5,
                         frequency=30.0, decay_s=1.0, intensity=1.0),
            ImpactPreset("subboom_50hz_long", "sub_boom", duration_s=3.0,
                         frequency=50.0, decay_s=2.5, intensity=0.9),
            ImpactPreset("subboom_40hz_tight", "sub_boom", duration_s=1.0,
                         frequency=40.0, decay_s=0.7, intensity=1.0),
            ImpactPreset("subboom_60hz_dist", "sub_boom", duration_s=2.0,
                         frequency=60.0, decay_s=1.5, distortion=0.4),
        ],
    )


def metal_crash_bank() -> ImpactBank:
    """Metal crash impacts — bright metallic textures."""
    return ImpactBank(
        name="METAL_CRASHES",
        presets=[
            ImpactPreset("mcrash_bright", "metal_crash", duration_s=3.0,
                         frequency=200.0, decay_s=2.5, brightness=0.8),
            ImpactPreset("mcrash_dark", "metal_crash", duration_s=2.5,
                         frequency=150.0, decay_s=2.0, brightness=0.4),
            ImpactPreset("mcrash_short", "metal_crash", duration_s=1.0,
                         frequency=250.0, decay_s=0.8, brightness=0.7),
            ImpactPreset("mcrash_epic", "metal_crash", duration_s=5.0,
                         frequency=180.0, decay_s=4.0, brightness=0.9),
        ],
    )


def cinematic_hit_bank() -> ImpactBank:
    """Cinematic hit impacts — layered boom + noise + tone."""
    return ImpactBank(
        name="CINEMATIC_HITS",
        presets=[
            ImpactPreset("chit_standard", "cinematic_hit", duration_s=3.0,
                         frequency=60.0, decay_s=2.5, brightness=0.7),
            ImpactPreset("chit_massive", "cinematic_hit", duration_s=5.0,
                         frequency=40.0, decay_s=4.0, brightness=0.6, intensity=1.0),
            ImpactPreset("chit_tight", "cinematic_hit", duration_s=1.5,
                         frequency=80.0, decay_s=1.0, brightness=0.8),
            ImpactPreset("chit_dark", "cinematic_hit", duration_s=3.0,
                         frequency=50.0, decay_s=2.0, brightness=0.3, distortion=0.2),
        ],
    )


def distorted_impact_bank() -> ImpactBank:
    """Distorted impact — heavy saturation on transient hits."""
    return ImpactBank(
        name="DISTORTED_IMPACTS",
        presets=[
            ImpactPreset("dimp_heavy", "distorted_impact", duration_s=2.0,
                         frequency=60.0, decay_s=1.5, distortion=0.8),
            ImpactPreset("dimp_crunch", "distorted_impact", duration_s=1.5,
                         frequency=80.0, decay_s=1.0, distortion=0.6),
            ImpactPreset("dimp_destroy", "distorted_impact", duration_s=2.5,
                         frequency=45.0, decay_s=2.0, distortion=1.0),
            ImpactPreset("dimp_warm", "distorted_impact", duration_s=2.0,
                         frequency=70.0, decay_s=1.5, distortion=0.3),
        ],
    )


def reverse_hit_bank() -> ImpactBank:
    """Reverse hit — reversed impacts for pre-drop effects."""
    return ImpactBank(
        name="REVERSE_HITS",
        presets=[
            ImpactPreset("rhit_2s", "reverse_hit", duration_s=2.0,
                         frequency=60.0, decay_s=1.5, intensity=0.9),
            ImpactPreset("rhit_4s", "reverse_hit", duration_s=4.0,
                         frequency=50.0, decay_s=3.0, intensity=0.8),
            ImpactPreset("rhit_1s_short", "reverse_hit", duration_s=1.0,
                         frequency=80.0, decay_s=0.7, intensity=1.0),
            ImpactPreset("rhit_3s_dist", "reverse_hit", duration_s=3.0,
                         frequency=55.0, decay_s=2.0, distortion=0.4),
        ],
    )


ALL_IMPACT_BANKS: dict[str, callable] = {
    "sub_booms":          sub_boom_bank,
    "metal_crashes":      metal_crash_bank,
    "cinematic_hits":     cinematic_hit_bank,
    "distorted_impacts":  distorted_impact_bank,
    "reverse_hits":       reverse_hit_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════


def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def write_impact_manifest(output_dir: str = "output") -> dict:
    """Generate all impact presets, write WAVs, and save manifest."""
    base = Path(output_dir)
    manifest: dict = {"module": "impact_hit", "banks": {}}

    for bank_key, bank_fn in ALL_IMPACT_BANKS.items():
        bank = bank_fn()
        bank_info: list[dict] = []
        for preset in bank.presets:
            audio = synthesize_impact(preset)
            wav_path = base / "wavetables" / f"impact_{preset.name}.wav"
            _write_wav(wav_path, audio)
            bank_info.append({
                "name": preset.name,
                "impact_type": preset.impact_type,
                "duration_s": preset.duration_s,
                "wav": str(wav_path),
            })
        manifest["banks"][bank_key] = {
            "name": bank.name,
            "presets": bank_info,
        }

    manifest_path = base / "analysis" / "impact_hit_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Impact manifest → %s", manifest_path)
    return manifest


def main() -> None:
    """Entry point for impact_hit module."""
    logger.info("=== DUBFORGE Impact Hit ===")
    manifest = write_impact_manifest()
    total = sum(len(b["presets"]) for b in manifest["banks"].values())
    logger.info("Generated %d impact presets across %d banks",
                total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
