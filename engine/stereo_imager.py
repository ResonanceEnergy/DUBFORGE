"""
DUBFORGE Engine — Stereo Imaging

Provides stereo width processing for mono-to-wide conversion.
Uses various psychoacoustic techniques for spatial widening.

Types:
    haas            — Haas effect (short delay on one channel)
    mid_side        — M/S processing (boost side, cut mid)
    frequency_split — Widen highs, keep bass mono
    phase           — Phase-based stereo widening
    psychoacoustic  — Complex psychoacoustic widener

Banks: 5 types × 4 presets = 20 presets
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
class StereoPreset:
    """A single stereo imaging preset."""
    name: str
    image_type: str  # haas | mid_side | frequency_split | phase | psychoacoustic
    width: float = 1.0         # stereo width 0-2 (1 = unchanged)
    delay_ms: float = 10.0     # haas delay in ms
    crossover_hz: float = 250.0  # freq split crossover
    mix: float = 1.0
    pan_law: float = -3.0      # dB pan law
    phase_amount: float = 0.5  # phase rotation amount


@dataclass
class StereoBank:
    """Collection of stereo imaging presets."""
    name: str
    presets: list[StereoPreset] = field(default_factory=list)


# --- Processing -----------------------------------------------------------

def _mono_to_stereo(signal: np.ndarray) -> np.ndarray:
    """Ensure signal is stereo (n, 2)."""
    if signal.ndim == 1:
        return np.column_stack([signal, signal])
    return signal


def _to_mid_side(stereo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert LR to MS."""
    mid = (stereo[:, 0] + stereo[:, 1]) * 0.5
    side = (stereo[:, 0] - stereo[:, 1]) * 0.5
    return mid, side


def _from_mid_side(mid: np.ndarray, side: np.ndarray) -> np.ndarray:
    """Convert MS to LR."""
    left = mid + side
    right = mid - side
    return np.column_stack([left, right])


def apply_haas(signal: np.ndarray, preset: StereoPreset,
               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Haas effect — short delay on one channel creates width."""
    stereo = _mono_to_stereo(signal)
    delay_samples = max(1, int(preset.delay_ms / 1000.0 * sample_rate))
    n = len(stereo)

    result = np.zeros_like(stereo)
    result[:, 0] = stereo[:, 0]  # Left: dry
    # Right: delayed
    result[delay_samples:, 1] = stereo[:n - delay_samples, 1]
    result[:delay_samples, 1] = 0.0

    # Mix
    return result * preset.mix + stereo * (1.0 - preset.mix)


def apply_mid_side(signal: np.ndarray, preset: StereoPreset,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """M/S width processing — adjust side level relative to mid."""
    stereo = _mono_to_stereo(signal)
    mid, side = _to_mid_side(stereo)

    # Width control: 0 = mono, 1 = normal, 2 = extra wide
    side_gain = preset.width
    result = _from_mid_side(mid, side * side_gain)

    return result * preset.mix + stereo * (1.0 - preset.mix)


def apply_frequency_split(signal: np.ndarray, preset: StereoPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Frequency split — widen above crossover, keep bass mono."""
    stereo = _mono_to_stereo(signal)
    n = len(stereo)

    # Simple IIR crossover (first-order for efficiency)
    fc = preset.crossover_hz
    rc = 1.0 / (2.0 * np.pi * fc)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)

    # Low-pass filter for bass (mono)
    low_l = np.zeros(n)
    low_r = np.zeros(n)
    for i in range(1, n):
        low_l[i] = low_l[i - 1] + alpha * (stereo[i, 0] - low_l[i - 1])
        low_r[i] = low_r[i - 1] + alpha * (stereo[i, 1] - low_r[i - 1])

    # High = original - low
    high_l = stereo[:, 0] - low_l
    high_r = stereo[:, 1] - low_r

    # Sum bass to mono
    bass_mono = (low_l + low_r) * 0.5

    # Widen highs
    mid_h, side_h = _to_mid_side(np.column_stack([high_l, high_r]))
    wide_high = _from_mid_side(mid_h, side_h * preset.width)

    # Recombine
    result = np.column_stack([bass_mono, bass_mono]) + wide_high
    return result * preset.mix + stereo * (1.0 - preset.mix)


def apply_phase_stereo(signal: np.ndarray, preset: StereoPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Phase-based stereo widening using all-pass filters."""
    stereo = _mono_to_stereo(signal)
    n = len(stereo)

    # Simple phase offset via Hilbert-like approximation
    # Apply small phase shift to one channel
    shift_samples = max(1, int(preset.phase_amount * 20))

    result = stereo.copy()
    if shift_samples < n:
        result[shift_samples:, 1] = stereo[:n - shift_samples, 1]
        result[:shift_samples, 1] = stereo[:shift_samples, 1] * 0.5

    # Width adjustment via M/S
    mid, side = _to_mid_side(result)
    result = _from_mid_side(mid, side * preset.width)

    return result * preset.mix + stereo * (1.0 - preset.mix)


def apply_psychoacoustic(signal: np.ndarray, preset: StereoPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Complex psychoacoustic widening — combines Haas + M/S + freq split."""
    stereo = _mono_to_stereo(signal)
    n = len(stereo)

    # Step 1: Haas on highs
    fc = preset.crossover_hz
    rc = 1.0 / (2.0 * np.pi * fc)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)

    low_l = np.zeros(n)
    low_r = np.zeros(n)
    for i in range(1, n):
        low_l[i] = low_l[i - 1] + alpha * (stereo[i, 0] - low_l[i - 1])
        low_r[i] = low_r[i - 1] + alpha * (stereo[i, 1] - low_r[i - 1])

    high_l = stereo[:, 0] - low_l
    high_r = stereo[:, 1] - low_r

    # Haas on highs only
    delay_samples = max(1, int(preset.delay_ms / 1000.0 * sample_rate))
    high_r_delayed = np.zeros(n)
    if delay_samples < n:
        high_r_delayed[delay_samples:] = high_r[:n - delay_samples]

    # M/S on highs
    highs = np.column_stack([high_l, high_r_delayed])
    mid_h, side_h = _to_mid_side(highs)
    wide_high = _from_mid_side(mid_h, side_h * preset.width)

    # Bass stays mono
    bass_mono = (low_l + low_r) * 0.5
    result = np.column_stack([bass_mono, bass_mono]) + wide_high

    return result * preset.mix + stereo * (1.0 - preset.mix)


# --- Router ---------------------------------------------------------------

def apply_stereo_imaging(signal: np.ndarray, preset: StereoPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct stereo imaging processor."""
    processors = {
        "haas": apply_haas,
        "mid_side": apply_mid_side,
        "frequency_split": apply_frequency_split,
        "phase": apply_phase_stereo,
        "psychoacoustic": apply_psychoacoustic,
    }
    proc = processors.get(preset.image_type)
    if proc is None:
        raise ValueError(f"Unknown stereo image type: {preset.image_type}")
    return proc(signal, preset, sample_rate)


# --- Banks ----------------------------------------------------------------

def haas_stereo_bank() -> StereoBank:
    return StereoBank(
        name="HAAS_STEREO",
        presets=[
            StereoPreset("Haas Subtle", "haas", delay_ms=5.0, mix=0.8),
            StereoPreset("Haas Medium", "haas", delay_ms=12.0, mix=1.0),
            StereoPreset("Haas Wide", "haas", delay_ms=20.0, mix=1.0),
            StereoPreset("Haas Extreme", "haas", delay_ms=30.0, mix=0.7),
        ],
    )


def mid_side_stereo_bank() -> StereoBank:
    return StereoBank(
        name="MID_SIDE_STEREO",
        presets=[
            StereoPreset("MS Narrow", "mid_side", width=0.5),
            StereoPreset("MS Normal", "mid_side", width=1.0),
            StereoPreset("MS Wide", "mid_side", width=1.5),
            StereoPreset("MS Extra Wide", "mid_side", width=2.0),
        ],
    )


def freq_split_stereo_bank() -> StereoBank:
    return StereoBank(
        name="FREQ_SPLIT_STEREO",
        presets=[
            StereoPreset("Split Low XO", "frequency_split", crossover_hz=150.0, width=1.5),
            StereoPreset("Split Standard", "frequency_split", crossover_hz=250.0, width=1.5),
            StereoPreset("Split High XO", "frequency_split", crossover_hz=400.0, width=1.8),
            StereoPreset("Split Wide", "frequency_split", crossover_hz=200.0, width=2.0),
        ],
    )


def phase_stereo_bank() -> StereoBank:
    return StereoBank(
        name="PHASE_STEREO",
        presets=[
            StereoPreset("Phase Subtle", "phase", phase_amount=0.3, width=1.2),
            StereoPreset("Phase Medium", "phase", phase_amount=0.5, width=1.5),
            StereoPreset("Phase Wide", "phase", phase_amount=0.7, width=1.8),
            StereoPreset("Phase Extreme", "phase", phase_amount=1.0, width=2.0),
        ],
    )


def psychoacoustic_stereo_bank() -> StereoBank:
    return StereoBank(
        name="PSYCHOACOUSTIC_STEREO",
        presets=[
            StereoPreset("Psycho Subtle", "psychoacoustic", delay_ms=8.0, width=1.3,
                          crossover_hz=200.0),
            StereoPreset("Psycho Standard", "psychoacoustic", delay_ms=12.0, width=1.5,
                          crossover_hz=250.0),
            StereoPreset("Psycho Wide", "psychoacoustic", delay_ms=18.0, width=1.8,
                          crossover_hz=300.0),
            StereoPreset("Psycho Max", "psychoacoustic", delay_ms=25.0, width=2.0,
                          crossover_hz=200.0),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_STEREO_BANKS: dict[str, Callable[[], StereoBank]] = {
    "haas": haas_stereo_bank,
    "mid_side": mid_side_stereo_bank,
    "frequency_split": freq_split_stereo_bank,
    "phase": phase_stereo_bank,
    "psychoacoustic": psychoacoustic_stereo_bank,
}


# --- WAV Export ---------------------------------------------------------------

def _write_wav_stereo(path: Path, samples: np.ndarray,
                      sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit stereo WAV. *samples* shape ``(n, 2)``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
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


def export_stereo_demos(output_dir: str = "output") -> list[str]:
    """Render all stereo imaging presets and write stereo .wav."""
    sig = _test_signal()
    out = Path(output_dir) / "wavetables" / "stereo_imager"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for bank_name, bank_fn in ALL_STEREO_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            processed = apply_stereo_imaging(sig, preset, SAMPLE_RATE)
            fname = f"stereo_{preset.name}.wav"
            _write_wav_stereo(out / fname, processed)
            paths.append(_export_path(out / fname))
    return paths


# --- Manifest -------------------------------------------------------------

def write_stereo_imager_manifest(output_dir: str = "output") -> dict:
    """Write stereo imager manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_STEREO_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "stereo_imager_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_stereo_imager_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_stereo_demos()
    print(f"Stereo Imager: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
