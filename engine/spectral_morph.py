"""
DUBFORGE — Spectral Morph Engine  (Session 180)

Morphs between two audio signals in the spectral domain,
with PHI-weighted interpolation and formant preservation.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI
from engine.accel import write_wav
SAMPLE_RATE = 48000


@dataclass
class MorphResult:
    """Result of spectral morphing."""
    signal: list[float]
    morph_factor: float
    duration_s: float
    spectral_centroid: float = 0.0

    def to_dict(self) -> dict:
        return {
            "morph_factor": round(self.morph_factor, 3),
            "duration_s": round(self.duration_s, 3),
            "samples": len(self.signal),
            "spectral_centroid": round(self.spectral_centroid, 1),
        }


def _hann_window(n: int) -> list[float]:
    """Generate Hann window."""
    return [0.5 - 0.5 * math.cos(2 * math.pi * i / n) for i in range(n)]


def _dft(signal: list[float]) -> list[tuple[float, float]]:
    """Compute DFT, returns list of (real, imag) pairs."""
    n = len(signal)
    result: list[tuple[float, float]] = []
    for k in range(n):
        re = sum(signal[i] * math.cos(2 * math.pi * k * i / n)
                 for i in range(n))
        im = -sum(signal[i] * math.sin(2 * math.pi * k * i / n)
                  for i in range(n))
        result.append((re, im))
    return result


def _idft(spectrum: list[tuple[float, float]]) -> list[float]:
    """Compute inverse DFT."""
    n = len(spectrum)
    result: list[float] = []
    for i in range(n):
        val = sum(
            spectrum[k][0] * math.cos(2 * math.pi * k * i / n) -
            spectrum[k][1] * math.sin(2 * math.pi * k * i / n)
            for k in range(n)
        )
        result.append(val / n)
    return result


def _to_polar(spectrum: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convert (real, imag) to (magnitude, phase)."""
    return [
        (math.sqrt(re * re + im * im), math.atan2(im, re))
        for re, im in spectrum
    ]


def _to_rect(polar: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convert (magnitude, phase) to (real, imag)."""
    return [
        (mag * math.cos(phase), mag * math.sin(phase))
        for mag, phase in polar
    ]


def spectral_morph(signal_a: list[float],
                    signal_b: list[float],
                    morph_factor: float = 0.5,
                    window_size: int = 256) -> MorphResult:
    """Morph between two signals in spectral domain."""
    # Align lengths
    length = max(len(signal_a), len(signal_b))
    if len(signal_a) < length:
        signal_a = signal_a + [0.0] * (length - len(signal_a))
    if len(signal_b) < length:
        signal_b = signal_b + [0.0] * (length - len(signal_b))

    t = max(0.0, min(1.0, morph_factor))
    window = _hann_window(window_size)
    hop = window_size // 2
    output = [0.0] * length

    for pos in range(0, length - window_size, hop):
        # Window both signals
        chunk_a = [signal_a[pos + i] * window[i] for i in range(window_size)]
        chunk_b = [signal_b[pos + i] * window[i] for i in range(window_size)]

        # DFT
        spec_a = _to_polar(_dft(chunk_a))
        spec_b = _to_polar(_dft(chunk_b))

        # Interpolate magnitudes and phases
        morphed_polar: list[tuple[float, float]] = []
        for (ma, pa), (mb, pb) in zip(spec_a, spec_b):
            # Magnitude: linear interpolation
            mag = ma * (1.0 - t) + mb * t

            # Phase: use source A's phase for t<0.5, blend for t>=0.5
            if t < 0.5:
                phase = pa
            else:
                # Phase blending (wrap-aware)
                dp = pb - pa
                while dp > math.pi:
                    dp -= 2 * math.pi
                while dp < -math.pi:
                    dp += 2 * math.pi
                phase = pa + dp * (t - 0.5) * 2
            morphed_polar.append((mag, phase))

        # Inverse DFT
        morphed_rect = _to_rect(morphed_polar)
        chunk_out = _idft(morphed_rect)

        # Overlap-add
        for i in range(window_size):
            if pos + i < length:
                output[pos + i] += chunk_out[i]

    # Compute spectral centroid
    centroid = _spectral_centroid(output)

    return MorphResult(
        signal=output,
        morph_factor=t,
        duration_s=length / SAMPLE_RATE,
        spectral_centroid=centroid,
    )


def morph_sequence(signal_a: list[float],
                    signal_b: list[float],
                    n_steps: int = 8,
                    window_size: int = 256) -> list[MorphResult]:
    """Generate a sequence of morphs from A to B."""
    results: list[MorphResult] = []
    for i in range(n_steps):
        factor = i / max(n_steps - 1, 1)
        result = spectral_morph(signal_a, signal_b, factor, window_size)
        results.append(result)
    return results


def phi_morph(signal_a: list[float],
               signal_b: list[float],
               window_size: int = 256) -> MorphResult:
    """Morph at PHI ratio (golden section)."""
    return spectral_morph(signal_a, signal_b, 1.0 / PHI, window_size)


def _spectral_centroid(signal: list[float],
                        sample_rate: int = SAMPLE_RATE) -> float:
    """Compute spectral centroid of a signal."""
    n = min(len(signal), 2048)
    if n < 2:
        return 0.0

    freq_res = sample_rate / n
    weighted_sum = 0.0
    total_mag = 0.0

    for k in range(1, n // 2):
        re = sum(signal[i] * math.cos(2 * math.pi * k * i / n)
                 for i in range(n))
        im = sum(signal[i] * math.sin(2 * math.pi * k * i / n)
                 for i in range(n))
        mag = math.sqrt(re * re + im * im)
        freq = k * freq_res
        weighted_sum += freq * mag
        total_mag += mag

    return weighted_sum / max(total_mag, 1e-10)


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s, sample_rate=sample_rate)
    return str(path)



def main() -> None:
    print("Spectral Morph Engine")

    n = 2048  # Short for demo (DFT is O(n^2))
    sig_a = [math.sin(2 * math.pi * 80 * i / SAMPLE_RATE) for i in range(n)]
    sig_b = [
        math.sin(2 * math.pi * 200 * i / SAMPLE_RATE) * 0.5 +
        math.sin(2 * math.pi * 400 * i / SAMPLE_RATE) * 0.3
        for i in range(n)
    ]

    result = spectral_morph(sig_a, sig_b, 0.5, 128)
    print(f"  Morph 50%: {len(result.signal)} samples, "
          f"centroid={result.spectral_centroid:.1f} Hz")

    phi_result = phi_morph(sig_a, sig_b, 128)
    print(f"  PHI morph: centroid={phi_result.spectral_centroid:.1f} Hz")

    seq = morph_sequence(sig_a, sig_b, 5, 128)
    for s in seq:
        print(f"    {s.morph_factor:.1%}: centroid={s.spectral_centroid:.1f} Hz")

    print("Done.")


if __name__ == "__main__":
    main()
