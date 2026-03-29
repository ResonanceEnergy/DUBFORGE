"""
DUBFORGE Engine — Chord Pad

Chord pad generator: synthesizes full chord voicings as pad textures.
Five chord types: minor7, major7, sus4, dim, power — each generating
multi-voice harmonic pads governed by phi/Fibonacci doctrine.

Outputs:
    output/wavetables/chord_pad_*.wav
    output/analysis/chord_pad_manifest.json
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
from engine.turboquant import (
    compress_audio_buffer,
    CompressedAudioBuffer,
    phi_optimal_bits,
    TurboQuantConfig,
)

logger = get_logger(__name__)


def tq_compress_chord_pad(
    signal: np.ndarray,
    label: str = "chord_pad",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress chord pad synthesis output."""
    samples = signal.tolist()
    bits = phi_optimal_bits(len(samples))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(samples, label, cfg, sample_rate=sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# CHORD INTERVALS (semitones from root)
# ═══════════════════════════════════════════════════════════════════════════

CHORD_INTERVALS = {
    "minor7":  [0, 3, 7, 10],     # root, m3, P5, m7
    "major7":  [0, 4, 7, 11],     # root, M3, P5, M7
    "sus4":    [0, 5, 7, 12],     # root, P4, P5, octave
    "dim":     [0, 3, 6, 9],      # root, m3, dim5, dim7
    "power":   [0, 7, 12, 19],    # root, P5, oct, oct+P5
}


@dataclass
class ChordPadPreset:
    """Configuration for a chord pad patch."""
    name: str
    chord_type: str  # minor7 | major7 | sus4 | dim | power
    root_freq: float = 130.81  # C3
    duration_s: float = 5.0
    detune_cents: float = 8.0
    attack_s: float = 0.5
    release_s: float = 1.0
    brightness: float = 0.5
    warmth: float = 0.6
    stereo_width: float = 0.3
    reverb_amount: float = 0.4
    distortion: float = 0.0


@dataclass
class ChordPadBank:
    """A named collection of chord pad presets."""
    name: str
    presets: list[ChordPadPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _pad_envelope(n: int, preset: ChordPadPreset,
                  sample_rate: int) -> np.ndarray:
    """Smooth attack-sustain-release envelope."""
    env = np.ones(n)
    attack_n = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    release_n = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env[:attack_n] = np.linspace(0, 1, attack_n)
    env[-release_n:] = np.linspace(1, 0, release_n)
    return env


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        return signal / peak * 0.95
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_minor7_pad(preset: ChordPadPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Minor 7th chord pad — lush melancholy voicing."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    intervals = CHORD_INTERVALS["minor7"]
    signal = np.zeros(n)

    for i, semitones in enumerate(intervals):
        freq = preset.root_freq * (2 ** (semitones / 12))
        detune = 2 ** (preset.detune_cents * (i - 1.5) / 1200 / 4)
        # Saw-like with harmonics for warmth
        tone = np.sin(2 * math.pi * freq * detune * t)
        tone += preset.warmth * 0.3 * np.sin(4 * math.pi * freq * detune * t)
        tone += preset.brightness * 0.15 * np.sin(6 * math.pi * freq * detune * t)
        signal += tone * (1.0 - i * 0.1)  # slightly reduce upper voices

    # Slow LFO modulation
    lfo = 1.0 + 0.05 * np.sin(2 * math.pi * PHI * 0.2 * t)
    signal *= lfo
    signal *= _pad_envelope(n, preset, sample_rate)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    return _normalize(signal)


def synthesize_major7_pad(preset: ChordPadPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Major 7th chord pad — bright dreamy voicing."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    intervals = CHORD_INTERVALS["major7"]
    signal = np.zeros(n)

    for i, semitones in enumerate(intervals):
        freq = preset.root_freq * (2 ** (semitones / 12))
        detune = 2 ** (preset.detune_cents * (i - 1.5) / 1200 / 4)
        tone = np.sin(2 * math.pi * freq * detune * t)
        # Brighter harmonics
        tone += preset.brightness * 0.4 * np.sin(4 * math.pi * freq * detune * t)
        tone += preset.brightness * 0.2 * np.sin(6 * math.pi * freq * detune * t)
        signal += tone * (1.0 - i * 0.08)

    lfo = 1.0 + 0.04 * np.sin(2 * math.pi * 0.15 * t)
    signal *= lfo
    signal *= _pad_envelope(n, preset, sample_rate)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    return _normalize(signal)


def synthesize_sus4_pad(preset: ChordPadPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sus4 chord pad — open, unresolved tension."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    intervals = CHORD_INTERVALS["sus4"]
    signal = np.zeros(n)

    for i, semitones in enumerate(intervals):
        freq = preset.root_freq * (2 ** (semitones / 12))
        detune = 2 ** (preset.detune_cents * (i - 1.5) / 1200 / 4)
        tone = np.sin(2 * math.pi * freq * detune * t)
        tone += preset.warmth * 0.25 * np.sin(4 * math.pi * freq * detune * t)
        signal += tone

    # Evolving phase for movement
    phase_mod = 0.03 * np.sin(2 * math.pi * PHI * 0.3 * t)
    signal *= (1 + phase_mod)
    signal *= _pad_envelope(n, preset, sample_rate)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    return _normalize(signal)


def synthesize_dim_pad(preset: ChordPadPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Diminished chord pad — dark, tense, symmetric voicing."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    intervals = CHORD_INTERVALS["dim"]
    signal = np.zeros(n)

    for i, semitones in enumerate(intervals):
        freq = preset.root_freq * (2 ** (semitones / 12))
        detune = 2 ** (preset.detune_cents * (i - 1.5) / 1200 / 4)
        tone = np.sin(2 * math.pi * freq * detune * t)
        # Dark harmonics — emphasize fundamental
        tone += 0.15 * np.sin(4 * math.pi * freq * detune * t)
        signal += tone * (1.0 - i * 0.12)

    # Tremolo for tension
    tremolo = 1.0 + 0.08 * np.sin(2 * math.pi * 3.0 * t)
    signal *= tremolo
    signal *= _pad_envelope(n, preset, sample_rate)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


def synthesize_power_pad(preset: ChordPadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Power chord pad — heavy root+fifth+octaves for aggression."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    intervals = CHORD_INTERVALS["power"]
    signal = np.zeros(n)

    for i, semitones in enumerate(intervals):
        freq = preset.root_freq * (2 ** (semitones / 12))
        detune = 2 ** (preset.detune_cents * (i - 1) / 1200 / 3)
        # Thicker saw-like tone for power
        tone = np.sin(2 * math.pi * freq * detune * t)
        tone += 0.5 * np.sin(4 * math.pi * freq * detune * t)
        tone += preset.brightness * 0.3 * np.sin(6 * math.pi * freq * detune * t)
        tone += preset.brightness * 0.15 * np.sin(8 * math.pi * freq * detune * t)
        weight = 1.0 if i < 2 else 0.7  # root and fifth louder
        signal += tone * weight

    signal *= _pad_envelope(n, preset, sample_rate)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# v2.4 SYNTHESIZERS — aug, add9, stacked
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_aug_pad(preset: ChordPadPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Augmented chord pad — root, major 3rd, aug 5th."""
    import math
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    ratios = [1.0, 2 ** (4/12), 2 ** (8/12)]  # aug triad
    signal = np.zeros(n)
    for r in ratios:
        f = preset.root_freq * r
        detune = preset.detune_cents / 1200
        signal += np.sin(2 * math.pi * f * t)
        signal += 0.5 * np.sin(2 * math.pi * f * (1 + detune) * t)
    signal *= preset.brightness / len(ratios)
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


def synthesize_add9_pad(preset: ChordPadPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Add9 chord pad — triad plus 9th interval."""
    import math
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    ratios = [1.0, 2 ** (4/12), 2 ** (7/12), 2 ** (14/12)]  # major add9
    signal = np.zeros(n)
    for r in ratios:
        f = preset.root_freq * r
        detune = preset.detune_cents / 1200
        signal += np.sin(2 * math.pi * f * t)
        signal += 0.4 * np.sin(2 * math.pi * f * (1 + detune) * t)
    signal *= preset.brightness / len(ratios)
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


def synthesize_stacked_pad(preset: ChordPadPreset, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Stacked chord pad — dense octave-stacked voicing."""
    import math
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    ratios = [0.5, 1.0, 2 ** (7/12), 2.0, 2.0 * 2 ** (7/12)]
    signal = np.zeros(n)
    for r in ratios:
        f = preset.root_freq * r
        detune = preset.detune_cents / 1200
        signal += np.sin(2 * math.pi * f * t)
        signal += 0.3 * np.sin(2 * math.pi * f * (1 + detune) * t)
    signal *= preset.brightness / len(ratios)
    env = np.ones(n)
    att = max(1, int(preset.attack_s * sample_rate))
    rel = max(1, int(preset.release_s * sample_rate))
    env[:att] = np.linspace(0, 1, att)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    signal *= env
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal /= mx
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_chord_pad(preset: ChordPadPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct chord pad synthesizer."""
    synthesizers = {
        "minor7": synthesize_minor7_pad,
        "major7": synthesize_major7_pad,
        "sus4": synthesize_sus4_pad,
        "dim": synthesize_dim_pad,
        "power": synthesize_power_pad,
        "aug": synthesize_aug_pad,
        "add9": synthesize_add9_pad,
        "stacked": synthesize_stacked_pad,
    }
    fn = synthesizers.get(preset.chord_type)
    if fn is None:
        raise ValueError(f"Unknown chord_type: {preset.chord_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 presets = 20
# ═══════════════════════════════════════════════════════════════════════════


def minor7_pad_bank() -> ChordPadBank:
    """Minor 7th chord pads — melancholy and lush."""
    return ChordPadBank(
        name="MINOR7_PADS",
        presets=[
            ChordPadPreset("min7_C3", "minor7", 130.81, duration_s=6.0,
                           detune_cents=10, brightness=0.5, warmth=0.7),
            ChordPadPreset("min7_E3", "minor7", 164.81, duration_s=5.0,
                           detune_cents=8, brightness=0.6, warmth=0.6),
            ChordPadPreset("min7_G3", "minor7", 196.0, duration_s=5.0,
                           detune_cents=12, brightness=0.4, warmth=0.8),
            ChordPadPreset("min7_A3", "minor7", 220.0, duration_s=4.0,
                           detune_cents=6, brightness=0.55, warmth=0.65),
        ],
    )


def major7_pad_bank() -> ChordPadBank:
    """Major 7th chord pads — bright and dreamy."""
    return ChordPadBank(
        name="MAJOR7_PADS",
        presets=[
            ChordPadPreset("maj7_C3", "major7", 130.81, duration_s=6.0,
                           detune_cents=8, brightness=0.7, warmth=0.5),
            ChordPadPreset("maj7_F3", "major7", 174.61, duration_s=5.0,
                           detune_cents=10, brightness=0.8, warmth=0.4),
            ChordPadPreset("maj7_G3", "major7", 196.0, duration_s=5.0,
                           detune_cents=6, brightness=0.65, warmth=0.55),
            ChordPadPreset("maj7_Bb3", "major7", 233.08, duration_s=4.0,
                           detune_cents=12, brightness=0.75, warmth=0.45),
        ],
    )


def sus4_pad_bank() -> ChordPadBank:
    """Sus4 chord pads — open and unresolved."""
    return ChordPadBank(
        name="SUS4_PADS",
        presets=[
            ChordPadPreset("sus4_C3", "sus4", 130.81, duration_s=6.0,
                           detune_cents=10, brightness=0.6, warmth=0.6),
            ChordPadPreset("sus4_D3", "sus4", 146.83, duration_s=5.0,
                           detune_cents=8, brightness=0.5, warmth=0.7),
            ChordPadPreset("sus4_E3", "sus4", 164.81, duration_s=5.0,
                           detune_cents=12, brightness=0.55, warmth=0.65),
            ChordPadPreset("sus4_A3", "sus4", 220.0, duration_s=4.0,
                           detune_cents=6, brightness=0.7, warmth=0.5),
        ],
    )


def dim_pad_bank() -> ChordPadBank:
    """Diminished chord pads — dark and tense."""
    return ChordPadBank(
        name="DIM_PADS",
        presets=[
            ChordPadPreset("dim_C3", "dim", 130.81, duration_s=5.0,
                           detune_cents=6, brightness=0.3, warmth=0.4),
            ChordPadPreset("dim_Eb3", "dim", 155.56, duration_s=5.0,
                           detune_cents=8, brightness=0.25, warmth=0.5),
            ChordPadPreset("dim_F#3", "dim", 185.0, duration_s=4.0,
                           detune_cents=10, brightness=0.35, warmth=0.35),
            ChordPadPreset("dim_A3", "dim", 220.0, duration_s=4.0,
                           detune_cents=5, brightness=0.2, warmth=0.6),
        ],
    )


def power_pad_bank() -> ChordPadBank:
    """Power chord pads — heavy root+fifth aggression."""
    return ChordPadBank(
        name="POWER_PADS",
        presets=[
            ChordPadPreset("power_C2", "power", 65.41, duration_s=6.0,
                           detune_cents=15, brightness=0.7, distortion=0.2),
            ChordPadPreset("power_D2", "power", 73.42, duration_s=5.0,
                           detune_cents=12, brightness=0.6, distortion=0.3),
            ChordPadPreset("power_E2", "power", 82.41, duration_s=5.0,
                           detune_cents=10, brightness=0.65, distortion=0.25),
            ChordPadPreset("power_A1", "power", 55.0, duration_s=8.0,
                           detune_cents=18, brightness=0.5, distortion=0.15),
        ],
    )


def aug_pad_bank() -> ChordPadBank:
    """Augmented chord pads — tense and shimmering."""
    return ChordPadBank(
        name="AUG_PADS",
        presets=[
            ChordPadPreset("aug_C3", "aug", 130.81, duration_s=5.0,
                           detune_cents=10, brightness=0.6),
            ChordPadPreset("aug_E3", "aug", 164.81, duration_s=4.0,
                           detune_cents=8, brightness=0.7),
            ChordPadPreset("aug_G3", "aug", 196.0, duration_s=6.0,
                           detune_cents=12, brightness=0.5),
            ChordPadPreset("aug_A3", "aug", 220.0, duration_s=5.0,
                           detune_cents=6, brightness=0.65),
        ],
    )


def add9_pad_bank() -> ChordPadBank:
    """Add9 chord pads — open and airy."""
    return ChordPadBank(
        name="ADD9_PADS",
        presets=[
            ChordPadPreset("add9_C3", "add9", 130.81, duration_s=5.0,
                           detune_cents=10, brightness=0.6),
            ChordPadPreset("add9_D3", "add9", 146.83, duration_s=4.0,
                           detune_cents=8, brightness=0.7),
            ChordPadPreset("add9_F3", "add9", 174.61, duration_s=6.0,
                           detune_cents=12, brightness=0.5),
            ChordPadPreset("add9_A3", "add9", 220.0, duration_s=5.0,
                           detune_cents=6, brightness=0.65),
        ],
    )


def stacked_pad_bank() -> ChordPadBank:
    """Stacked chord pads — dense octave-layered voicings."""
    return ChordPadBank(
        name="STACKED_PADS",
        presets=[
            ChordPadPreset("stacked_C2", "stacked", 65.41, duration_s=6.0,
                           detune_cents=15, brightness=0.6),
            ChordPadPreset("stacked_E2", "stacked", 82.41, duration_s=5.0,
                           detune_cents=12, brightness=0.7),
            ChordPadPreset("stacked_G2", "stacked", 98.0, duration_s=7.0,
                           detune_cents=10, brightness=0.5),
            ChordPadPreset("stacked_A2", "stacked", 110.0, duration_s=6.0,
                           detune_cents=8, brightness=0.65),
        ],
    )


ALL_CHORD_PAD_BANKS: dict[str, callable] = {
    "minor7": minor7_pad_bank,
    "major7": major7_pad_bank,
    "sus4":   sus4_pad_bank,
    "dim":    dim_pad_bank,
    "power":  power_pad_bank,
    # v2.4
    "aug":     aug_pad_bank,
    "add9":    add9_pad_bank,
    "stacked": stacked_pad_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════


def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def write_chord_pad_manifest(output_dir: str = "output") -> dict:
    """Generate all chord pad presets, write WAVs, and save manifest."""
    base = Path(output_dir)
    manifest: dict = {"module": "chord_pad", "banks": {}}

    for bank_key, bank_fn in ALL_CHORD_PAD_BANKS.items():
        bank = bank_fn()
        bank_info: list[dict] = []
        for preset in bank.presets:
            audio = synthesize_chord_pad(preset)
            wav_path = base / "wavetables" / f"chord_pad_{preset.name}.wav"
            _write_wav(wav_path, audio)
            bank_info.append({
                "name": preset.name,
                "chord_type": preset.chord_type,
                "root_freq": preset.root_freq,
                "duration_s": preset.duration_s,
                "wav": str(wav_path),
            })
        manifest["banks"][bank_key] = {
            "name": bank.name,
            "presets": bank_info,
        }

    manifest_path = base / "analysis" / "chord_pad_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Chord pad manifest → %s", manifest_path)
    return manifest


def main() -> None:
    """Entry point for chord_pad module."""
    logger.info("=== DUBFORGE Chord Pad Generator ===")
    manifest = write_chord_pad_manifest()
    total = sum(len(b["presets"]) for b in manifest["banks"].values())
    logger.info("Generated %d chord pad presets across %d banks",
                total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
