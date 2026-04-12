"""
DUBFORGE Engine — LFO Modulation Matrix

Universal LFO system for modulating any parameter. Provides
waveform generators and modulation routing.

Types:
    sine          — smooth sine-wave modulation
    triangle      — linear triangle wave
    saw           — sawtooth wave (up or down)
    square        — square / pulse wave
    sample_hold   — random sample-and-hold (S&H)

Banks: 5 types × 4 presets = 20 presets
"""

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)
# --- Data Models ----------------------------------------------------------

@dataclass
class LFOPreset:
    """A single LFO preset."""
    name: str
    lfo_type: str  # sine | triangle | saw | square | sample_hold
    rate_hz: float = 1.0        # LFO frequency
    depth: float = 1.0          # modulation depth 0-1
    phase_offset: float = 0.0   # phase offset in radians
    sync_bpm: float = 0.0       # if > 0, sync to BPM (rate_hz ignored)
    sync_division: float = 1.0  # beats per cycle when synced
    pulse_width: float = 0.5    # for square wave
    polarity: str = "bipolar"   # bipolar (-1 to 1) | unipolar (0 to 1)


@dataclass
class LFOBank:
    """Collection of LFO presets."""
    name: str
    presets: list[LFOPreset] = field(default_factory=list)


# --- Waveform Generators -------------------------------------------------

def _to_unipolar(signal: np.ndarray) -> np.ndarray:
    """Convert bipolar (-1, 1) to unipolar (0, 1)."""
    return signal * 0.5 + 0.5


def generate_sine_lfo(preset: LFOPreset, duration_s: float,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Smooth sine-wave LFO."""
    n = int(duration_s * sample_rate)
    rate = _get_rate(preset)
    t = np.linspace(0, duration_s, n, endpoint=False)
    signal = np.sin(2 * np.pi * rate * t + preset.phase_offset)
    signal *= preset.depth
    if preset.polarity == "unipolar":
        signal = _to_unipolar(signal)
    return signal


def generate_triangle_lfo(preset: LFOPreset, duration_s: float,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Linear triangle wave LFO."""
    n = int(duration_s * sample_rate)
    rate = _get_rate(preset)
    t = np.linspace(0, duration_s, n, endpoint=False)
    phase = (rate * t + preset.phase_offset / (2 * np.pi)) % 1.0
    signal = 2.0 * np.abs(2.0 * phase - 1.0) - 1.0
    signal *= preset.depth
    if preset.polarity == "unipolar":
        signal = _to_unipolar(signal)
    return signal


def generate_saw_lfo(preset: LFOPreset, duration_s: float,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sawtooth wave LFO (upward ramp)."""
    n = int(duration_s * sample_rate)
    rate = _get_rate(preset)
    t = np.linspace(0, duration_s, n, endpoint=False)
    phase = (rate * t + preset.phase_offset / (2 * np.pi)) % 1.0
    signal = 2.0 * phase - 1.0
    signal *= preset.depth
    if preset.polarity == "unipolar":
        signal = _to_unipolar(signal)
    return signal


def generate_square_lfo(preset: LFOPreset, duration_s: float,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Square / pulse wave LFO with adjustable pulse width."""
    n = int(duration_s * sample_rate)
    rate = _get_rate(preset)
    t = np.linspace(0, duration_s, n, endpoint=False)
    phase = (rate * t + preset.phase_offset / (2 * np.pi)) % 1.0
    signal = np.where(phase < preset.pulse_width, 1.0, -1.0)
    signal *= preset.depth
    if preset.polarity == "unipolar":
        signal = _to_unipolar(signal)
    return signal


def generate_sample_hold_lfo(preset: LFOPreset, duration_s: float,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Random sample-and-hold LFO."""
    n = int(duration_s * sample_rate)
    rate = _get_rate(preset)
    step_samples = max(1, int(sample_rate / max(0.01, rate)))

    rng = np.random.default_rng(42)  # deterministic for reproducibility
    signal = np.zeros(n)
    pos = 0
    while pos < n:
        val = rng.uniform(-1, 1)
        end = min(pos + step_samples, n)
        signal[pos:end] = val
        pos = end

    signal *= preset.depth
    if preset.polarity == "unipolar":
        signal = _to_unipolar(signal)
    return signal


def _get_rate(preset: LFOPreset) -> float:
    """Get effective LFO rate, accounting for BPM sync."""
    if preset.sync_bpm > 0:
        return preset.sync_bpm / 60.0 / max(0.01, preset.sync_division)
    return preset.rate_hz


# --- Router ---------------------------------------------------------------

def generate_lfo(preset: LFOPreset, duration_s: float,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct LFO waveform generator."""
    generators = {
        "sine": generate_sine_lfo,
        "triangle": generate_triangle_lfo,
        "saw": generate_saw_lfo,
        "square": generate_square_lfo,
        "sample_hold": generate_sample_hold_lfo,
    }
    gen = generators.get(preset.lfo_type)
    if gen is None:
        raise ValueError(f"Unknown LFO type: {preset.lfo_type}")
    return gen(preset, duration_s, sample_rate)


def generate_lfo_compressed(preset: LFOPreset, duration_s: float,
                            sample_rate: int = SAMPLE_RATE) -> CompressedAudioBuffer:
    """Generate LFO signal and TQ-compress it."""
    signal = generate_lfo(preset, duration_s, sample_rate)
    samples = signal.tolist()
    tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(samples)))
    return compress_audio_buffer(
        samples, f"lfo_{preset.name}_{preset.lfo_type}", tq_cfg,
        sample_rate=sample_rate, label=preset.name,
    )


def apply_lfo(signal: np.ndarray, preset: LFOPreset,
              param_range: tuple[float, float] = (0.0, 1.0),
              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply LFO modulation to a parameter, returning modulated values."""
    duration_s = len(signal) / sample_rate
    lfo = generate_lfo(preset, duration_s, sample_rate)
    if len(lfo) != len(signal):
        lfo = np.interp(
            np.linspace(0, 1, len(signal)),
            np.linspace(0, 1, len(lfo)),
            lfo,
        )
    # Map LFO to param range
    lo, hi = param_range
    if preset.polarity == "bipolar":
        lfo_norm = (lfo + 1.0) / 2.0  # normalize to 0-1
    else:
        lfo_norm = lfo
    modulated = lo + (hi - lo) * lfo_norm
    return modulated


# --- Banks ----------------------------------------------------------------

def sine_lfo_bank() -> LFOBank:
    return LFOBank(
        name="SINE_LFO",
        presets=[
            LFOPreset("Sine Slow", "sine", rate_hz=0.5, depth=1.0),
            LFOPreset("Sine Medium", "sine", rate_hz=2.0, depth=0.8),
            LFOPreset("Sine Fast", "sine", rate_hz=8.0, depth=0.6),
            LFOPreset("Sine BPM Sync", "sine", sync_bpm=150.0, sync_division=2.0, depth=1.0),
        ],
    )


def triangle_lfo_bank() -> LFOBank:
    return LFOBank(
        name="TRIANGLE_LFO",
        presets=[
            LFOPreset("Tri Slow", "triangle", rate_hz=0.5, depth=1.0),
            LFOPreset("Tri Medium", "triangle", rate_hz=2.0, depth=0.8),
            LFOPreset("Tri Fast", "triangle", rate_hz=6.0, depth=0.7),
            LFOPreset("Tri BPM", "triangle", sync_bpm=150.0, sync_division=1.0, depth=1.0),
        ],
    )


def saw_lfo_bank() -> LFOBank:
    return LFOBank(
        name="SAW_LFO",
        presets=[
            LFOPreset("Saw Slow", "saw", rate_hz=0.5, depth=1.0),
            LFOPreset("Saw Medium", "saw", rate_hz=2.0, depth=0.8),
            LFOPreset("Saw Fast", "saw", rate_hz=8.0, depth=0.6),
            LFOPreset("Saw Ramp", "saw", rate_hz=1.0, depth=1.0, polarity="unipolar"),
        ],
    )


def square_lfo_bank() -> LFOBank:
    return LFOBank(
        name="SQUARE_LFO",
        presets=[
            LFOPreset("Square Standard", "square", rate_hz=2.0, depth=1.0),
            LFOPreset("Square Pulse 25", "square", rate_hz=2.0, depth=1.0, pulse_width=0.25),
            LFOPreset("Square Pulse 75", "square", rate_hz=2.0, depth=1.0, pulse_width=0.75),
            LFOPreset("Square Fast", "square", rate_hz=8.0, depth=0.7),
        ],
    )


def sample_hold_lfo_bank() -> LFOBank:
    return LFOBank(
        name="SAMPLE_HOLD_LFO",
        presets=[
            LFOPreset("S&H Slow", "sample_hold", rate_hz=1.0, depth=1.0),
            LFOPreset("S&H Medium", "sample_hold", rate_hz=4.0, depth=0.8),
            LFOPreset("S&H Fast", "sample_hold", rate_hz=12.0, depth=0.6),
            LFOPreset("S&H BPM", "sample_hold", sync_bpm=150.0, sync_division=0.5, depth=1.0),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_LFO_BANKS: dict[str, Callable[..., Any]] = {
    "sine": sine_lfo_bank,
    "triangle": triangle_lfo_bank,
    "saw": saw_lfo_bank,
    "square": square_lfo_bank,
    "sample_hold": sample_hold_lfo_bank,
}


# --- Manifest -------------------------------------------------------------

def write_lfo_matrix_manifest(output_dir: str = "output") -> dict:
    """Write LFO matrix manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_LFO_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "lfo_matrix_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_lfo_matrix_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    print(f"LFO Matrix: {len(manifest['banks'])} banks, {total} presets")


if __name__ == "__main__":
    main()
