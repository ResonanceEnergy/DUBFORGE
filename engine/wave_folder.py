"""
DUBFORGE — Wave Folder Engine  (Session 159)

Waveshaping via folding — wraps signal back when it exceeds
boundaries, creating rich harmonic overtones. Classic West Coast
synthesis technique with PHI-ratio fold points.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000


@dataclass
class WaveFolderPatch:
    """Wave folder configuration."""
    name: str = "Fold"
    fold_amount: float = 3.0  # Number of folds
    symmetry: float = 0.5  # 0=asymmetric, 0.5=symmetric, 1=inverse
    bias: float = 0.0  # DC offset before folding
    pre_gain: float = 1.0
    post_gain: float = 0.8
    mix: float = 1.0  # Wet/dry


def fold(x: float, amount: float = 3.0) -> float:
    """Basic wave folding."""
    x = x * amount
    # Fold using triangle wave wrapping
    phase = x + 1.0  # shift to 0-2 range
    period = 4.0
    phase = phase % period
    if phase < 0:
        phase += period
    if phase < 2:
        return phase - 1.0
    else:
        return 3.0 - phase


def fold_tanh(x: float, amount: float = 3.0) -> float:
    """Soft wave folding with tanh saturation."""
    x = x * amount
    return math.tanh(math.sin(x * math.pi / 2))


def fold_sinusoidal(x: float, amount: float = 3.0) -> float:
    """Sinusoidal wave folding."""
    return math.sin(x * amount * math.pi / 2)


def fold_phi(x: float, amount: float = 3.0) -> float:
    """PHI-ratio wave folding with golden section fold points."""
    x = x * amount
    # Fold at PHI intervals
    fold_point = 1.0 / PHI
    while abs(x) > fold_point:
        if x > fold_point:
            x = 2 * fold_point - x
        elif x < -fold_point:
            x = -2 * fold_point - x
    return x / fold_point  # Normalize to -1..1


def fold_multi(x: float, amount: float = 3.0,
               stages: int = 3) -> float:
    """Multi-stage wave folding."""
    for _ in range(stages):
        x = fold(x, amount / stages)
    return x


FOLD_ALGORITHMS: dict[str, callable] = {
    "standard": fold,
    "tanh": fold_tanh,
    "sinusoidal": fold_sinusoidal,
    "phi": fold_phi,
    "multi": fold_multi,
}


def process_signal(signal: list[float], patch: WaveFolderPatch,
                    algorithm: str = "standard") -> list[float]:
    """Apply wave folding to a signal."""
    fold_fn = FOLD_ALGORITHMS.get(algorithm, fold)
    output = [0.0] * len(signal)

    for i, s in enumerate(signal):
        # Pre-gain and bias
        x = s * patch.pre_gain + patch.bias

        # Apply symmetry
        if patch.symmetry < 0.5:
            # Asymmetric: fold only positive
            if x > 0:
                wet = fold_fn(x, patch.fold_amount)
            else:
                wet = x
        elif patch.symmetry > 0.5:
            # Inverse asymmetric: fold only negative
            if x < 0:
                wet = fold_fn(x, patch.fold_amount)
            else:
                wet = x
        else:
            # Symmetric
            wet = fold_fn(x, patch.fold_amount)

        # Mix
        output[i] = (wet * patch.mix + s * (1 - patch.mix)) * patch.post_gain

    return output


def generate_folded_wave(freq: float = A4_432, duration: float = 2.0,
                          patch: WaveFolderPatch | None = None,
                          algorithm: str = "standard",
                          sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate a folded waveform from a sine source."""
    if patch is None:
        patch = WaveFolderPatch()
    n = int(duration * sample_rate)
    dt = 1.0 / sample_rate

    # Source: sine wave
    source = [math.sin(2 * math.pi * freq * i * dt) for i in range(n)]

    # Apply folding
    return process_signal(source, patch, algorithm)


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


# Presets
WAVEFOLDER_PRESETS: dict[str, tuple[WaveFolderPatch, str]] = {
    "gentle": (WaveFolderPatch("Gentle", 2.0, 0.5, 0.0, 1.0, 0.8),
               "standard"),
    "aggressive": (WaveFolderPatch("Aggressive", 5.0, 0.5, 0.0, 1.5, 0.7),
                   "standard"),
    "phi_fold": (WaveFolderPatch("PHI Fold", PHI * 2, 0.5, 0.0, 1.0, 0.8),
                 "phi"),
    "warm_tanh": (WaveFolderPatch("Warm Tanh", 3.0, 0.5, 0.1, 1.2, 0.8),
                  "tanh"),
    "metallic": (WaveFolderPatch("Metallic", 4.0, 0.5, 0.0, 2.0, 0.7),
                 "sinusoidal"),
    "multi_stage": (WaveFolderPatch("Multi Stage", 6.0, 0.5, 0.0, 1.0, 0.7),
                    "multi"),
    "asymmetric": (WaveFolderPatch("Asymmetric", 4.0, 0.2, 0.0, 1.0, 0.8),
                   "standard"),
}


def render_preset(name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    preset = WAVEFOLDER_PRESETS.get(name, WAVEFOLDER_PRESETS["gentle"])
    patch, algo = preset
    signal = generate_folded_wave(freq, duration, patch, algo)
    path = os.path.join(output_dir, f"wavefold_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Wave Folder Engine")
    for name, (patch, algo) in WAVEFOLDER_PRESETS.items():
        sig = generate_folded_wave(A4_432, 0.5, patch, algo)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name} ({algo}): fold={patch.fold_amount:.1f}, "
              f"peak={peak:.4f}")
    path = render_preset("phi_fold", A4_432, 2.0)
    print(f"  Rendered: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
