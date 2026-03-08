"""
DUBFORGE Engine — Riddim Bass Sequencer

Generates riddim-style bass patterns with gaps, stutter, and space.
Riddim relies on rhythmic gaps between bass hits, where silence is
as important as the bass itself.

Types:
    minimal     — stripped-back riddim, lots of space
    heavy       — wall-of-bass with short gaps
    bounce      — syncopated bounce pattern
    stutter     — rapid-fire retriggered riddim
    triplet     — triplet-grid riddim

Banks: 5 types × 4 presets = 20 presets
"""

from dataclasses import dataclass, field

import numpy as np

from engine.phi_core import SAMPLE_RATE

PHI = 1.6180339887


# --- Data Models ----------------------------------------------------------

@dataclass
class RiddimPreset:
    """A single riddim bass preset."""
    name: str
    riddim_type: str  # minimal | heavy | bounce | stutter | triplet
    frequency: float = 55.0     # bass fundamental Hz
    duration_s: float = 4.0
    gap_ratio: float = 0.3      # proportion of beat that is silent
    attack_s: float = 0.005
    release_s: float = 0.02
    distortion: float = 0.5     # 0-1 distortion amount
    subdivisions: int = 4       # hits per beat
    bpm: float = 150.0
    depth: float = 1.0


@dataclass
class RiddimBank:
    """Collection of riddim presets."""
    name: str
    presets: list[RiddimPreset] = field(default_factory=list)


# --- Pattern Generators ---------------------------------------------------

def _distort(signal: np.ndarray, amount: float) -> np.ndarray:
    """Soft-clip distortion."""
    if amount < 1e-6:
        return signal
    # Tanh waveshaping
    drive = 1.0 + amount * 10.0
    out = np.tanh(signal * drive) / np.tanh(drive)
    return out


def _apply_envelope(signal: np.ndarray, attack: int, release: int) -> np.ndarray:
    """Apply attack/release envelope to a signal segment."""
    n = len(signal)
    attack = max(1, min(attack, n // 2))
    release = max(1, min(release, n // 2))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return signal * env


def generate_riddim_minimal(preset: RiddimPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Minimal riddim — lots of space between hits."""
    n = int(preset.duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    hit_samples = int(beat_samples * (1.0 - preset.gap_ratio))
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))

    output = np.zeros(n)
    pos = 0
    while pos < n:
        seg_len = min(hit_samples, n - pos)
        t = np.arange(seg_len) / sample_rate
        hit = np.sin(2 * np.pi * preset.frequency * t)
        hit = _apply_envelope(hit, attack, min(release, seg_len))
        hit = _distort(hit, preset.distortion)
        output[pos:pos + seg_len] = hit * preset.depth
        pos += beat_samples

    return output


def generate_riddim_heavy(preset: RiddimPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Heavy riddim — dense bass with short gaps."""
    n = int(preset.duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    # Heavy = very short gaps (invert gap ratio)
    hit_samples = int(beat_samples * max(0.7, 1.0 - preset.gap_ratio * 0.3))
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))

    output = np.zeros(n)
    pos = 0
    while pos < n:
        seg_len = min(hit_samples, n - pos)
        t = np.arange(seg_len) / sample_rate
        # Layer fundamental + octave for heaviness
        hit = np.sin(2 * np.pi * preset.frequency * t) * 0.7
        hit += np.sin(2 * np.pi * preset.frequency * 2 * t) * 0.3
        hit = _apply_envelope(hit, attack, min(release, seg_len))
        hit = _distort(hit, min(1.0, preset.distortion * 1.5))
        output[pos:pos + seg_len] = hit * preset.depth
        pos += beat_samples

    return output


def generate_riddim_bounce(preset: RiddimPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Bounce riddim — syncopated pattern with offbeat gaps."""
    n = int(preset.duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))

    # Bounce pattern: hit on 1, gap on &, hit on 2&, gap on 3, etc.
    pattern = [True, False, False, True, False, True, False, False]
    sub_len = beat_samples // len(pattern)

    output = np.zeros(n)
    pos = 0
    idx = 0
    while pos < n:
        if pattern[idx % len(pattern)]:
            seg_len = min(sub_len, n - pos)
            t = np.arange(seg_len) / sample_rate
            hit = np.sin(2 * np.pi * preset.frequency * t)
            hit = _apply_envelope(hit, attack, min(release, seg_len))
            hit = _distort(hit, preset.distortion)
            output[pos:pos + seg_len] = hit * preset.depth
        pos += sub_len
        idx += 1

    return output


def generate_riddim_stutter(preset: RiddimPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Stutter riddim — rapid retriggered bass hits."""
    n = int(preset.duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    sub_samples = max(1, beat_samples // max(1, preset.subdivisions))
    hit_len = int(sub_samples * (1.0 - preset.gap_ratio))
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))

    output = np.zeros(n)
    pos = 0
    while pos < n:
        seg_len = min(hit_len, n - pos)
        if seg_len > 0:
            t = np.arange(seg_len) / sample_rate
            hit = np.sin(2 * np.pi * preset.frequency * t)
            hit = _apply_envelope(hit, attack, min(release, seg_len))
            hit = _distort(hit, preset.distortion)
            output[pos:pos + seg_len] = hit * preset.depth
        pos += sub_samples

    return output


def generate_riddim_triplet(preset: RiddimPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Triplet riddim — triplet grid with swing-style gaps."""
    n = int(preset.duration_s * sample_rate)
    beat_samples = int(60.0 / preset.bpm * sample_rate)
    triplet = max(1, beat_samples // 3)
    hit_len = int(triplet * (1.0 - preset.gap_ratio))
    attack = max(1, int(preset.attack_s * sample_rate))
    release = max(1, int(preset.release_s * sample_rate))

    # Triplet pattern: hit, gap, hit  per beat
    pattern = [True, False, True]

    output = np.zeros(n)
    pos = 0
    idx = 0
    while pos < n:
        if pattern[idx % len(pattern)]:
            seg_len = min(hit_len, n - pos)
            if seg_len > 0:
                t = np.arange(seg_len) / sample_rate
                hit = np.sin(2 * np.pi * preset.frequency * t)
                hit = _apply_envelope(hit, attack, min(release, seg_len))
                hit = _distort(hit, preset.distortion)
                output[pos:pos + seg_len] = hit * preset.depth
        pos += triplet
        idx += 1

    return output


# --- Router ---------------------------------------------------------------

def generate_riddim(preset: RiddimPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to correct riddim generator."""
    generators = {
        "minimal": generate_riddim_minimal,
        "heavy": generate_riddim_heavy,
        "bounce": generate_riddim_bounce,
        "stutter": generate_riddim_stutter,
        "triplet": generate_riddim_triplet,
    }
    gen = generators.get(preset.riddim_type)
    if gen is None:
        raise ValueError(f"Unknown riddim type: {preset.riddim_type}")
    return gen(preset, sample_rate)


# --- Banks ----------------------------------------------------------------

def minimal_riddim_bank() -> RiddimBank:
    return RiddimBank(
        name="MINIMAL_RIDDIM",
        presets=[
            RiddimPreset("Minimal Pure", "minimal", gap_ratio=0.5, distortion=0.2),
            RiddimPreset("Minimal Wide", "minimal", gap_ratio=0.6, distortion=0.3),
            RiddimPreset("Minimal Dark", "minimal", gap_ratio=0.4, frequency=44.0, distortion=0.4),
            RiddimPreset("Minimal Space", "minimal", gap_ratio=0.7, distortion=0.1),
        ],
    )


def heavy_riddim_bank() -> RiddimBank:
    return RiddimBank(
        name="HEAVY_RIDDIM",
        presets=[
            RiddimPreset("Heavy Wall", "heavy", gap_ratio=0.15, distortion=0.8),
            RiddimPreset("Heavy Crush", "heavy", gap_ratio=0.1, distortion=1.0),
            RiddimPreset("Heavy Dense", "heavy", gap_ratio=0.2, distortion=0.7),
            RiddimPreset("Heavy Sub", "heavy", gap_ratio=0.12, frequency=36.7, distortion=0.6),
        ],
    )


def bounce_riddim_bank() -> RiddimBank:
    return RiddimBank(
        name="BOUNCE_RIDDIM",
        presets=[
            RiddimPreset("Bounce Standard", "bounce", gap_ratio=0.35, distortion=0.5),
            RiddimPreset("Bounce Tight", "bounce", gap_ratio=0.25, distortion=0.6),
            RiddimPreset("Bounce Loose", "bounce", gap_ratio=0.5, distortion=0.3),
            RiddimPreset("Bounce Deep", "bounce", gap_ratio=0.3, frequency=44.0, distortion=0.5),
        ],
    )


def stutter_riddim_bank() -> RiddimBank:
    return RiddimBank(
        name="STUTTER_RIDDIM",
        presets=[
            RiddimPreset("Stutter 4x", "stutter", subdivisions=4, gap_ratio=0.3, distortion=0.6),
            RiddimPreset("Stutter 8x", "stutter", subdivisions=8, gap_ratio=0.3, distortion=0.5),
            RiddimPreset("Stutter 16x", "stutter", subdivisions=16, gap_ratio=0.25, distortion=0.4),
            RiddimPreset("Stutter Dirty", "stutter", subdivisions=6, gap_ratio=0.2, distortion=0.9),
        ],
    )


def triplet_riddim_bank() -> RiddimBank:
    return RiddimBank(
        name="TRIPLET_RIDDIM",
        presets=[
            RiddimPreset("Triplet Standard", "triplet", gap_ratio=0.3, distortion=0.5),
            RiddimPreset("Triplet Heavy", "triplet", gap_ratio=0.2, distortion=0.8),
            RiddimPreset("Triplet Clean", "triplet", gap_ratio=0.4, distortion=0.2),
            RiddimPreset("Triplet Deep", "triplet", gap_ratio=0.35, frequency=44.0, distortion=0.6),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_RIDDIM_BANKS: dict[str, callable] = {
    "minimal": minimal_riddim_bank,
    "heavy": heavy_riddim_bank,
    "bounce": bounce_riddim_bank,
    "stutter": stutter_riddim_bank,
    "triplet": triplet_riddim_bank,
}


# --- Manifest -------------------------------------------------------------

def write_riddim_manifest(output_dir: str = "output") -> dict:
    """Write riddim engine manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_RIDDIM_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "riddim_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_riddim_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    print(f"Riddim Engine: {len(manifest['banks'])} banks, {total} presets")


if __name__ == "__main__":
    main()
