"""
DUBFORGE Engine — Multiband Distortion

Per-band distortion processing with independent drive controls
for low, mid, and high frequency bands.

Types:
    warm        — soft saturation, tube-style warmth
    aggressive  — hard-clipping aggressive distortion
    digital     — bit-crushing / sample-rate reduction
    tube        — asymmetric tube-style overdrive
    tape        — tape saturation with compression

Banks: 5 types × 4 presets = 20 presets
"""

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from engine.config_loader import PHI
from engine.turboquant import (
    compress_audio_buffer,
    CompressedAudioBuffer,
    phi_optimal_bits,
    TurboQuantConfig,
)

SAMPLE_RATE = 44100


def tq_compress_distortion(
    signal: np.ndarray,
    label: str = "distortion",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress multiband distortion output."""
    samples = signal.tolist()
    bits = phi_optimal_bits(len(samples))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(samples, label, cfg, sample_rate=sample_rate)


# --- Data Models ----------------------------------------------------------

@dataclass
class MultibandDistPreset:
    """A single multiband distortion preset."""
    name: str
    dist_type: str  # warm | aggressive | digital | tube | tape
    low_drive: float = 0.3       # low-band drive 0-1
    mid_drive: float = 0.5       # mid-band drive 0-1
    high_drive: float = 0.4      # high-band drive 0-1
    crossover_low: float = 200.0   # Hz, low-mid split
    crossover_high: float = 2000.0  # Hz, mid-high split
    output_gain: float = 0.8      # output level 0-1
    mix: float = 1.0              # wet/dry mix
    bit_depth: int = 8            # for digital type
    sample_reduce: int = 4        # downsample factor for digital type


@dataclass
class MultibandDistBank:
    """Collection of multiband distortion presets."""
    name: str
    presets: list[MultibandDistPreset] = field(default_factory=list)


# --- Band Splitting -------------------------------------------------------

def _split_bands(signal: np.ndarray, crossover_low: float,
                 crossover_high: float,
                 sample_rate: int = SAMPLE_RATE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split signal into low, mid, high bands using simple IIR filters."""
    n = len(signal)
    dt = 1.0 / sample_rate

    # Low-pass for bass
    rc_lo = 1.0 / (2.0 * np.pi * crossover_low)
    alpha_lo = dt / (rc_lo + dt)

    # Low-pass for mid-high split
    rc_hi = 1.0 / (2.0 * np.pi * crossover_high)
    alpha_hi = dt / (rc_hi + dt)

    low = np.zeros(n)
    mid_high_lp = np.zeros(n)

    for i in range(1, n):
        low[i] = low[i - 1] + alpha_lo * (signal[i] - low[i - 1])
        mid_high_lp[i] = mid_high_lp[i - 1] + alpha_hi * (signal[i] - mid_high_lp[i - 1])

    # Mid = signal above low crossover, below high crossover
    above_low = signal - low
    mid = np.zeros(n)
    for i in range(1, n):
        mid[i] = mid[i - 1] + alpha_hi * (above_low[i] - mid[i - 1])
    mid = mid  # LP of above_low

    # High = everything above mid-high crossover
    high = above_low - mid

    return low, mid, high


# --- Distortion Algorithms -----------------------------------------------

def _warm_distort(signal: np.ndarray, drive: float) -> np.ndarray:
    """Soft saturation — tanh waveshaping."""
    if drive < 1e-6:
        return signal
    gain = 1.0 + drive * 8.0
    return np.tanh(signal * gain) / np.tanh(gain)


def _aggressive_distort(signal: np.ndarray, drive: float) -> np.ndarray:
    """Hard clipping distortion."""
    if drive < 1e-6:
        return signal
    gain = 1.0 + drive * 15.0
    clipped = np.clip(signal * gain, -1.0, 1.0)
    return clipped


def _digital_distort(signal: np.ndarray, drive: float,
                     bit_depth: int = 8, sample_reduce: int = 4) -> np.ndarray:
    """Bit-crush and sample rate reduction."""
    # Bit reduction
    levels = 2 ** bit_depth
    quantized = np.round(signal * levels) / levels

    # Sample rate reduction
    if sample_reduce > 1:
        reduced = np.zeros_like(quantized)
        for i in range(0, len(quantized), sample_reduce):
            end = min(i + sample_reduce, len(quantized))
            reduced[i:end] = quantized[i]
        quantized = reduced

    # Blend with drive amount
    return signal * (1.0 - drive) + quantized * drive


def _tube_distort(signal: np.ndarray, drive: float) -> np.ndarray:
    """Asymmetric tube-style overdrive."""
    if drive < 1e-6:
        return signal
    gain = 1.0 + drive * 10.0
    driven = signal * gain
    # Asymmetric — positive clips harder than negative
    pos = np.tanh(driven * 1.2)
    neg = np.tanh(driven * 0.8)
    result = np.where(driven >= 0, pos, neg)
    return result / max(1e-10, np.max(np.abs(result)))


def _tape_distort(signal: np.ndarray, drive: float) -> np.ndarray:
    """Tape saturation with soft compression."""
    if drive < 1e-6:
        return signal
    gain = 1.0 + drive * 6.0
    # Tape-style saturation using sin approximation
    saturated = np.sin(np.arctan(signal * gain))
    return saturated


# --- Distortion Router ----------------------------------------------------

def _get_distortion_fn(dist_type: str):
    """Get the distortion function for a given type."""
    fns = {
        "warm": _warm_distort,
        "aggressive": _aggressive_distort,
        "tube": _tube_distort,
        "tape": _tape_distort,
    }
    return fns.get(dist_type, _warm_distort)


# --- Processing -----------------------------------------------------------

def apply_multiband_distortion(signal: np.ndarray, preset: MultibandDistPreset,
                               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply multiband distortion to a signal."""
    # Split into bands
    low, mid, high = _split_bands(
        signal, preset.crossover_low, preset.crossover_high, sample_rate,
    )

    # Apply distortion per band
    if preset.dist_type == "digital":
        low_dist = _digital_distort(low, preset.low_drive,
                                    preset.bit_depth, preset.sample_reduce)
        mid_dist = _digital_distort(mid, preset.mid_drive,
                                    preset.bit_depth, preset.sample_reduce)
        high_dist = _digital_distort(high, preset.high_drive,
                                     preset.bit_depth, preset.sample_reduce)
    else:
        dist_fn = _get_distortion_fn(preset.dist_type)
        low_dist = dist_fn(low, preset.low_drive)
        mid_dist = dist_fn(mid, preset.mid_drive)
        high_dist = dist_fn(high, preset.high_drive)

    # Recombine
    wet = (low_dist + mid_dist + high_dist) * preset.output_gain
    return wet * preset.mix + signal * (1.0 - preset.mix)


# --- Banks ----------------------------------------------------------------

def warm_distortion_bank() -> MultibandDistBank:
    return MultibandDistBank(
        name="WARM_DISTORTION",
        presets=[
            MultibandDistPreset("Warm Subtle", "warm", 0.2, 0.3, 0.2),
            MultibandDistPreset("Warm Drive", "warm", 0.4, 0.6, 0.3),
            MultibandDistPreset("Warm Heavy", "warm", 0.6, 0.8, 0.5),
            MultibandDistPreset("Warm Bass Focus", "warm", 0.7, 0.3, 0.2),
        ],
    )


def aggressive_distortion_bank() -> MultibandDistBank:
    return MultibandDistBank(
        name="AGGRESSIVE_DISTORTION",
        presets=[
            MultibandDistPreset("Aggro Light", "aggressive", 0.3, 0.5, 0.3),
            MultibandDistPreset("Aggro Full", "aggressive", 0.7, 0.9, 0.7),
            MultibandDistPreset("Aggro Mid Scoop", "aggressive", 0.8, 0.3, 0.6),
            MultibandDistPreset("Aggro Destroy", "aggressive", 1.0, 1.0, 1.0),
        ],
    )


def digital_distortion_bank() -> MultibandDistBank:
    return MultibandDistBank(
        name="DIGITAL_DISTORTION",
        presets=[
            MultibandDistPreset("Bitcrush 12", "digital", 0.5, 0.5, 0.5,
                                bit_depth=12, sample_reduce=2),
            MultibandDistPreset("Bitcrush 8", "digital", 0.7, 0.7, 0.7,
                                bit_depth=8, sample_reduce=4),
            MultibandDistPreset("Bitcrush 4", "digital", 0.9, 0.9, 0.9,
                                bit_depth=4, sample_reduce=8),
            MultibandDistPreset("Bitcrush Lo-Fi", "digital", 0.6, 0.8, 0.4,
                                bit_depth=6, sample_reduce=6),
        ],
    )


def tube_distortion_bank() -> MultibandDistBank:
    return MultibandDistBank(
        name="TUBE_DISTORTION",
        presets=[
            MultibandDistPreset("Tube Warm", "tube", 0.3, 0.4, 0.2),
            MultibandDistPreset("Tube Drive", "tube", 0.5, 0.7, 0.4),
            MultibandDistPreset("Tube Crunch", "tube", 0.7, 0.9, 0.6),
            MultibandDistPreset("Tube Saturate", "tube", 0.8, 0.8, 0.8),
        ],
    )


def tape_distortion_bank() -> MultibandDistBank:
    return MultibandDistBank(
        name="TAPE_DISTORTION",
        presets=[
            MultibandDistPreset("Tape Subtle", "tape", 0.2, 0.3, 0.2),
            MultibandDistPreset("Tape Warm", "tape", 0.4, 0.5, 0.3),
            MultibandDistPreset("Tape Hot", "tape", 0.6, 0.7, 0.5),
            MultibandDistPreset("Tape Slam", "tape", 0.8, 0.9, 0.7),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_MULTIBAND_DIST_BANKS: dict[str, Callable[[], MultibandDistBank]] = {
    "warm": warm_distortion_bank,
    "aggressive": aggressive_distortion_bank,
    "digital": digital_distortion_bank,
    "tube": tube_distortion_bank,
    "tape": tape_distortion_bank,
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


def export_distortion_demos(output_dir: str = "output") -> list[str]:
    """Render all distortion presets applied to a test signal and write .wav."""
    sig = _test_signal()
    out = Path(output_dir) / "wavetables" / "multiband_distortion"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for bank_name, bank_fn in ALL_MULTIBAND_DIST_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            processed = apply_multiband_distortion(sig, preset, SAMPLE_RATE)
            fname = f"dist_{preset.name}.wav"
            _write_wav(out / fname, processed)
            paths.append(_export_path(out / fname))
    return paths


# --- Manifest -------------------------------------------------------------

def write_multiband_distortion_manifest(output_dir: str = "output") -> dict:
    """Write multiband distortion manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_MULTIBAND_DIST_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "multiband_distortion_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_multiband_distortion_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_distortion_demos()
    print(f"Multiband Distortion: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
