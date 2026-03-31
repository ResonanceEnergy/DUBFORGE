"""
DUBFORGE — Audio Math  (Session 228)

Mathematical audio operations — convolution, correlation,
spectral math, PHI-weighted interpolation, sample statistics.
"""

import math
from dataclasses import dataclass

import numpy as np

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class AudioStats:
    """Statistical properties of audio."""
    peak: float
    rms: float
    crest_factor: float
    dc_offset: float
    zero_crossings: int
    dynamic_range_db: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "peak": round(self.peak, 6),
            "rms": round(self.rms, 6),
            "crest_factor": round(self.crest_factor, 2),
            "dc_offset": round(self.dc_offset, 6),
            "zero_crossings": self.zero_crossings,
            "dynamic_range_db": round(self.dynamic_range_db, 1),
            "sample_count": self.sample_count,
        }


class AudioMath:
    """Mathematical audio operations."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    @staticmethod
    def add(a: list[float], b: list[float],
            gain_a: float = 1.0, gain_b: float = 1.0) -> list[float]:
        """Add two signals."""
        n = max(len(a), len(b))
        arr_a = np.zeros(n)
        arr_b = np.zeros(n)
        arr_a[:len(a)] = a
        arr_b[:len(b)] = b
        return (arr_a * gain_a + arr_b * gain_b).tolist()

    @staticmethod
    def subtract(a: list[float], b: list[float]) -> list[float]:
        """Subtract b from a."""
        n = max(len(a), len(b))
        arr_a = np.zeros(n)
        arr_b = np.zeros(n)
        arr_a[:len(a)] = a
        arr_b[:len(b)] = b
        return (arr_a - arr_b).tolist()

    @staticmethod
    def multiply(a: list[float], b: list[float]) -> list[float]:
        """Multiply (ring modulate) two signals."""
        n = min(len(a), len(b))
        return (np.asarray(a[:n]) * np.asarray(b[:n])).tolist()

    @staticmethod
    def scale(samples: list[float], gain: float) -> list[float]:
        """Scale by constant."""
        return (np.asarray(samples) * gain).tolist()

    @staticmethod
    def invert(samples: list[float]) -> list[float]:
        """Phase invert."""
        return (-np.asarray(samples)).tolist()

    @staticmethod
    def abs_signal(samples: list[float]) -> list[float]:
        """Full-wave rectification."""
        return np.abs(np.asarray(samples)).tolist()

    @staticmethod
    def half_rectify(samples: list[float]) -> list[float]:
        """Half-wave rectification."""
        return np.maximum(0.0, np.asarray(samples)).tolist()

    def convolve(self, a: list[float], b: list[float]) -> list[float]:
        """Linear convolution."""
        return np.convolve(a, b).tolist()

    def correlate(self, a: list[float], b: list[float]) -> list[float]:
        """Cross-correlation."""
        return self.convolve(a, list(reversed(b)))

    def autocorrelate(self, samples: list[float]) -> list[float]:
        """Auto-correlation."""
        return self.correlate(samples, samples)

    @staticmethod
    def interpolate_linear(a: list[float], b: list[float],
                           t: float) -> list[float]:
        """Linear interpolation between two signals."""
        n = min(len(a), len(b))
        aa = np.asarray(a[:n])
        bb = np.asarray(b[:n])
        return (aa * (1 - t) + bb * t).tolist()

    @staticmethod
    def interpolate_phi(a: list[float], b: list[float]) -> list[float]:
        """PHI-weighted interpolation."""
        t = 1.0 / PHI  # ~0.618
        n = min(len(a), len(b))
        aa = np.asarray(a[:n])
        bb = np.asarray(b[:n])
        return (aa * (1 - t) + bb * t).tolist()

    @staticmethod
    def interpolate_cosine(a: list[float], b: list[float],
                           t: float) -> list[float]:
        """Cosine interpolation (smoother)."""
        t2 = (1 - math.cos(t * math.pi)) / 2
        n = min(len(a), len(b))
        aa = np.asarray(a[:n])
        bb = np.asarray(b[:n])
        return (aa * (1 - t2) + bb * t2).tolist()

    @staticmethod
    def normalize(samples: list[float],
                  target: float = 0.95) -> list[float]:
        """Normalize to target peak."""
        arr = np.asarray(samples)
        pk = float(np.max(np.abs(arr))) if len(arr) > 0 else 1.0
        if pk <= 0:
            return list(samples)
        return (arr * (target / pk)).tolist()

    @staticmethod
    def rms(samples: list[float]) -> float:
        """Compute RMS."""
        if not samples:
            return 0.0
        arr = np.asarray(samples)
        return float(np.sqrt(np.mean(arr * arr)))

    def stats(self, samples: list[float]) -> AudioStats:
        """Compute statistical properties."""
        if not samples:
            return AudioStats(0, 0, 0, 0, 0, 0, 0)

        arr = np.asarray(samples)
        abs_arr = np.abs(arr)
        peak = float(np.max(abs_arr))
        r = float(np.sqrt(np.mean(arr * arr)))
        dc = float(np.mean(arr))

        # Zero crossings
        signs = arr >= 0
        zc = int(np.sum(signs[1:] != signs[:-1]))

        # Dynamic range
        nonzero = abs_arr[abs_arr > 0.0001]
        min_level = float(np.min(nonzero)) if len(nonzero) > 0 else 0.0001
        dr = 20 * math.log10(peak / min_level) if min_level > 0 else 0

        crest = peak / r if r > 0 else 0

        return AudioStats(
            peak=peak,
            rms=r,
            crest_factor=crest,
            dc_offset=dc,
            zero_crossings=zc,
            dynamic_range_db=dr,
            sample_count=len(samples),
        )

    @staticmethod
    def window_hanning(n: int) -> list[float]:
        """Generate Hanning window."""
        return np.hanning(n).tolist()

    @staticmethod
    def window_hamming(n: int) -> list[float]:
        """Generate Hamming window."""
        return np.hamming(n).tolist()

    @staticmethod
    def window_blackman(n: int) -> list[float]:
        """Generate Blackman window."""
        return np.blackman(n).tolist()

    @staticmethod
    def apply_window(samples: list[float],
                     window: list[float]) -> list[float]:
        """Apply window function."""
        n = min(len(samples), len(window))
        return (np.asarray(samples[:n]) * np.asarray(window[:n])).tolist()


def main() -> None:
    print("Audio Math")
    am = AudioMath()

    n = SAMPLE_RATE
    sine = [0.8 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
            for i in range(n)]
    cosine = [0.6 * math.cos(2 * math.pi * 330 * i / SAMPLE_RATE)
              for i in range(n)]

    # Stats
    s = am.stats(sine)
    d = s.to_dict()
    print(f"  Peak: {d['peak']}")
    print(f"  RMS: {d['rms']}")
    print(f"  Crest: {d['crest_factor']}")
    print(f"  Zero crossings: {d['zero_crossings']}")

    # Operations
    added = am.add(sine, cosine)
    print(f"\n  Add: peak={max(abs(s) for s in added):.3f}")

    mult = am.multiply(sine, cosine)
    print(f"  Multiply: peak={max(abs(s) for s in mult):.3f}")

    phi = am.interpolate_phi(sine, cosine)
    print(f"  PHI interp: peak={max(abs(s) for s in phi):.3f}")

    # Windows
    for name, fn in [("hanning", am.window_hanning),
                      ("hamming", am.window_hamming),
                      ("blackman", am.window_blackman)]:
        w = fn(1024)
        print(f"  {name}: center={w[512]:.4f}")

    print("Done.")


if __name__ == "__main__":
    main()
