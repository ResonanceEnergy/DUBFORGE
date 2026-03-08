"""
DUBFORGE Engine — Pitch Automation

Generates pitch automation curves for drop-tuning, pitch dives,
risers, wobbles, staircase effects, and glides.

Types:
    dive        — pitch drops down (classic dubstep drop tuning)
    rise        — pitch sweeps upward
    wobble      — oscillating pitch modulation
    staircase   — discrete pitch steps
    glide       — smooth portamento-style pitch bend

Banks: 5 types × 4 presets = 20 presets
"""

from dataclasses import dataclass, field

import numpy as np

from engine.phi_core import SAMPLE_RATE

PHI = 1.6180339887


# --- Data Models ----------------------------------------------------------

@dataclass
class PitchAutoPreset:
    """A single pitch automation preset."""
    name: str
    auto_type: str  # dive | rise | wobble | staircase | glide
    start_semitones: float = 0.0  # starting pitch offset
    end_semitones: float = -12.0  # ending pitch offset
    duration_s: float = 1.0
    curve_exp: float = 2.0       # curve shape exponent
    rate_hz: float = 4.0         # for wobble type
    steps: int = 4               # for staircase type
    depth_semitones: float = 12.0  # for wobble type


@dataclass
class PitchAutoBank:
    """Collection of pitch automation presets."""
    name: str
    presets: list[PitchAutoPreset] = field(default_factory=list)


# --- Curve Generators -----------------------------------------------------

def generate_dive_curve(preset: PitchAutoPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch dive — drops from start to end semitones."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, 1, n)
    # Exponential dive curve
    curve = t ** preset.curve_exp
    semitones = preset.start_semitones + (preset.end_semitones - preset.start_semitones) * curve
    return semitones


def generate_rise_curve(preset: PitchAutoPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch rise — sweeps upward."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, 1, n)
    # Inverse exponential for rise
    curve = 1.0 - (1.0 - t) ** preset.curve_exp
    semitones = preset.start_semitones + (preset.end_semitones - preset.start_semitones) * curve
    return semitones


def generate_wobble_curve(preset: PitchAutoPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch wobble — oscillating pitch modulation."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, preset.duration_s, n)
    wobble = np.sin(2 * np.pi * preset.rate_hz * t)
    semitones = preset.start_semitones + preset.depth_semitones * wobble
    return semitones


def generate_staircase_curve(preset: PitchAutoPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch staircase — discrete pitch steps."""
    n = int(preset.duration_s * sample_rate)
    steps = max(1, preset.steps)
    step_size = (preset.end_semitones - preset.start_semitones) / steps

    semitones = np.zeros(n)
    step_samples = n // steps
    for i in range(steps):
        start_idx = i * step_samples
        end_idx = min((i + 1) * step_samples, n)
        semitones[start_idx:end_idx] = preset.start_semitones + step_size * i

    # Fill remaining
    if steps * step_samples < n:
        semitones[steps * step_samples:] = preset.end_semitones

    return semitones


def generate_glide_curve(preset: PitchAutoPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch glide — smooth S-curve portamento."""
    n = int(preset.duration_s * sample_rate)
    t = np.linspace(0, 1, n)
    # Smooth S-curve (sigmoid-like)
    s_curve = 0.5 * (1.0 + np.tanh(6.0 * (t - 0.5)))
    semitones = preset.start_semitones + (preset.end_semitones - preset.start_semitones) * s_curve
    return semitones


# --- Router ---------------------------------------------------------------

def generate_pitch_automation(preset: PitchAutoPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct pitch automation curve generator."""
    generators = {
        "dive": generate_dive_curve,
        "rise": generate_rise_curve,
        "wobble": generate_wobble_curve,
        "staircase": generate_staircase_curve,
        "glide": generate_glide_curve,
    }
    gen = generators.get(preset.auto_type)
    if gen is None:
        raise ValueError(f"Unknown pitch automation type: {preset.auto_type}")
    return gen(preset, sample_rate)


def apply_pitch_automation(signal: np.ndarray, preset: PitchAutoPreset,
                           base_freq: float = 55.0,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply pitch automation to an audio signal via resampling ratio.

    Returns pitch-shifted signal (approximate via phase accumulation).
    """
    n = len(signal)
    duration_s = n / sample_rate
    auto_preset = PitchAutoPreset(
        name=preset.name, auto_type=preset.auto_type,
        start_semitones=preset.start_semitones,
        end_semitones=preset.end_semitones,
        duration_s=duration_s, curve_exp=preset.curve_exp,
        rate_hz=preset.rate_hz, steps=preset.steps,
        depth_semitones=preset.depth_semitones,
    )
    semitones = generate_pitch_automation(auto_preset, sample_rate)

    # Convert semitones to frequency ratios
    ratios = 2.0 ** (semitones / 12.0)

    # Phase accumulation for pitch shifting
    phase = np.cumsum(ratios)
    phase = phase % n

    # Interpolate the signal at new phase positions
    indices = phase.astype(int) % n
    return signal[indices]


# --- Banks ----------------------------------------------------------------

def dive_pitch_bank() -> PitchAutoBank:
    """Pitch dive presets — classic drop-tuning."""
    return PitchAutoBank(
        name="DIVE_PITCH",
        presets=[
            PitchAutoPreset("Dive Octave", "dive", 0, -12, 0.5, curve_exp=2.0),
            PitchAutoPreset("Dive 2 Octave", "dive", 0, -24, 0.8, curve_exp=2.5),
            PitchAutoPreset("Dive Fifth", "dive", 0, -7, 0.3, curve_exp=1.5),
            PitchAutoPreset("Dive Slow", "dive", 0, -12, 2.0, curve_exp=3.0),
        ],
    )


def rise_pitch_bank() -> PitchAutoBank:
    """Pitch rise presets — upward sweeps."""
    return PitchAutoBank(
        name="RISE_PITCH",
        presets=[
            PitchAutoPreset("Rise Octave", "rise", -12, 0, 1.0, curve_exp=2.0),
            PitchAutoPreset("Rise 2 Oct", "rise", -24, 0, 2.0, curve_exp=2.5),
            PitchAutoPreset("Rise Quick", "rise", -7, 0, 0.3, curve_exp=1.5),
            PitchAutoPreset("Rise Wide", "rise", -12, 12, 1.5, curve_exp=2.0),
        ],
    )


def wobble_pitch_bank() -> PitchAutoBank:
    """Pitch wobble presets — oscillating modulation."""
    return PitchAutoBank(
        name="WOBBLE_PITCH",
        presets=[
            PitchAutoPreset("Wobble Slow", "wobble", rate_hz=2.0, depth_semitones=3.0),
            PitchAutoPreset("Wobble Fast", "wobble", rate_hz=8.0, depth_semitones=2.0),
            PitchAutoPreset("Wobble Deep", "wobble", rate_hz=4.0, depth_semitones=7.0),
            PitchAutoPreset("Wobble Subtle", "wobble", rate_hz=3.0, depth_semitones=1.0),
        ],
    )


def staircase_pitch_bank() -> PitchAutoBank:
    """Staircase pitch presets — stepped pitch changes."""
    return PitchAutoBank(
        name="STAIRCASE_PITCH",
        presets=[
            PitchAutoPreset("Stairs Down 4", "staircase", 0, -12, 1.0, steps=4),
            PitchAutoPreset("Stairs Down 8", "staircase", 0, -12, 2.0, steps=8),
            PitchAutoPreset("Stairs Up 4", "staircase", -12, 0, 1.0, steps=4),
            PitchAutoPreset("Stairs Chr", "staircase", 0, -12, 1.0, steps=12),
        ],
    )


def glide_pitch_bank() -> PitchAutoBank:
    """Glide pitch presets — smooth portamento."""
    return PitchAutoBank(
        name="GLIDE_PITCH",
        presets=[
            PitchAutoPreset("Glide Down Oct", "glide", 0, -12, 0.5),
            PitchAutoPreset("Glide Up Oct", "glide", -12, 0, 0.5),
            PitchAutoPreset("Glide Slow", "glide", 0, -7, 2.0),
            PitchAutoPreset("Glide Wide", "glide", -12, 12, 1.0),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_PITCH_AUTO_BANKS: dict[str, callable] = {
    "dive": dive_pitch_bank,
    "rise": rise_pitch_bank,
    "wobble": wobble_pitch_bank,
    "staircase": staircase_pitch_bank,
    "glide": glide_pitch_bank,
}


# --- Manifest -------------------------------------------------------------

def write_pitch_automation_manifest(output_dir: str = "output") -> dict:
    """Write pitch automation manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_PITCH_AUTO_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "pitch_automation_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_pitch_automation_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    print(f"Pitch Automation: {len(manifest['banks'])} banks, {total} presets")


if __name__ == "__main__":
    main()
