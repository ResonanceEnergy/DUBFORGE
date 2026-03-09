"""
DUBFORGE — Audio Math  (Session 228)

Mathematical audio operations — convolution, correlation,
spectral math, PHI-weighted interpolation, sample statistics.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
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
        result = [0.0] * n
        for i in range(len(a)):
            result[i] += a[i] * gain_a
        for i in range(len(b)):
            result[i] += b[i] * gain_b
        return result

    @staticmethod
    def subtract(a: list[float], b: list[float]) -> list[float]:
        """Subtract b from a."""
        n = max(len(a), len(b))
        result = [0.0] * n
        for i in range(len(a)):
            result[i] += a[i]
        for i in range(len(b)):
            result[i] -= b[i]
        return result

    @staticmethod
    def multiply(a: list[float], b: list[float]) -> list[float]:
        """Multiply (ring modulate) two signals."""
        n = min(len(a), len(b))
        return [a[i] * b[i] for i in range(n)]

    @staticmethod
    def scale(samples: list[float], gain: float) -> list[float]:
        """Scale by constant."""
        return [s * gain for s in samples]

    @staticmethod
    def invert(samples: list[float]) -> list[float]:
        """Phase invert."""
        return [-s for s in samples]

    @staticmethod
    def abs_signal(samples: list[float]) -> list[float]:
        """Full-wave rectification."""
        return [abs(s) for s in samples]

    @staticmethod
    def half_rectify(samples: list[float]) -> list[float]:
        """Half-wave rectification."""
        return [max(0.0, s) for s in samples]

    def convolve(self, a: list[float], b: list[float]) -> list[float]:
        """Linear convolution."""
        na, nb = len(a), len(b)
        n = na + nb - 1
        result = [0.0] * n

        for i in range(na):
            for j in range(nb):
                result[i + j] += a[i] * b[j]

        return result

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
        return [a[i] * (1 - t) + b[i] * t for i in range(n)]

    @staticmethod
    def interpolate_phi(a: list[float], b: list[float]) -> list[float]:
        """PHI-weighted interpolation."""
        t = 1.0 / PHI  # ~0.618
        n = min(len(a), len(b))
        return [a[i] * (1 - t) + b[i] * t for i in range(n)]

    @staticmethod
    def interpolate_cosine(a: list[float], b: list[float],
                           t: float) -> list[float]:
        """Cosine interpolation (smoother)."""
        t2 = (1 - math.cos(t * math.pi)) / 2
        n = min(len(a), len(b))
        return [a[i] * (1 - t2) + b[i] * t2 for i in range(n)]

    @staticmethod
    def normalize(samples: list[float],
                  target: float = 0.95) -> list[float]:
        """Normalize to target peak."""
        pk = max(abs(s) for s in samples) if samples else 1.0
        if pk <= 0:
            return list(samples)
        gain = target / pk
        return [s * gain for s in samples]

    @staticmethod
    def rms(samples: list[float]) -> float:
        """Compute RMS."""
        if not samples:
            return 0.0
        return math.sqrt(sum(s * s for s in samples) / len(samples))

    def stats(self, samples: list[float]) -> AudioStats:
        """Compute statistical properties."""
        if not samples:
            return AudioStats(0, 0, 0, 0, 0, 0, 0)

        peak = max(abs(s) for s in samples)
        r = self.rms(samples)
        dc = sum(samples) / len(samples)

        # Zero crossings
        zc = sum(
            1 for i in range(1, len(samples))
            if (samples[i] >= 0) != (samples[i - 1] >= 0)
        )

        # Dynamic range
        # Find minimum non-zero level
        sorted_abs = sorted(abs(s) for s in samples if abs(s) > 0.0001)
        min_level = sorted_abs[0] if sorted_abs else 0.0001
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
        return [0.5 * (1 - math.cos(2 * math.pi * i / (n - 1)))
                for i in range(n)]

    @staticmethod
    def window_hamming(n: int) -> list[float]:
        """Generate Hamming window."""
        return [0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1))
                for i in range(n)]

    @staticmethod
    def window_blackman(n: int) -> list[float]:
        """Generate Blackman window."""
        return [
            0.42 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) +
            0.08 * math.cos(4 * math.pi * i / (n - 1))
            for i in range(n)
        ]

    @staticmethod
    def apply_window(samples: list[float],
                     window: list[float]) -> list[float]:
        """Apply window function."""
        n = min(len(samples), len(window))
        return [samples[i] * window[i] for i in range(n)]


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
