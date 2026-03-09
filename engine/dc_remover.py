"""
DUBFORGE — DC Offset Remover  (Session 215)

Remove DC offset from audio using high-pass filter,
mean subtraction, or adaptive methods.
"""

import math

PHI = 1.6180339887
SAMPLE_RATE = 44100


class DCRemover:
    """Remove DC offset from audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def detect_dc(self, samples: list[float]) -> float:
        """Detect DC offset (mean value)."""
        if not samples:
            return 0.0
        return sum(samples) / len(samples)

    def remove_mean(self, samples: list[float]) -> list[float]:
        """Remove DC by subtracting mean."""
        dc = self.detect_dc(samples)
        return [s - dc for s in samples]

    def remove_highpass(self, samples: list[float],
                        cutoff: float = 5.0) -> list[float]:
        """Remove DC using first-order high-pass filter."""
        if not samples:
            return []

        # RC high-pass filter
        rc = 1.0 / (2 * math.pi * cutoff)
        dt = 1.0 / self.sample_rate
        alpha = rc / (rc + dt)

        result: list[float] = [samples[0]]
        for i in range(1, len(samples)):
            result.append(alpha * (result[i - 1] + samples[i] - samples[i - 1]))

        return result

    def remove_adaptive(self, samples: list[float],
                        window_ms: float = 500) -> list[float]:
        """Remove DC using sliding window mean subtraction."""
        if not samples:
            return []

        window = max(1, int(window_ms * self.sample_rate / 1000))
        result: list[float] = []

        # Running sum for efficiency
        _running_sum = sum(samples[:min(window, len(samples))])

        for i in range(len(samples)):
            # Window bounds
            start = max(0, i - window // 2)
            end = min(len(samples), i + window // 2 + 1)
            w = end - start

            # Compute local mean
            local_mean = sum(samples[start:end]) / w
            result.append(samples[i] - local_mean)

        return result

    def remove_phi_weighted(self, samples: list[float]) -> list[float]:
        """Remove DC with PHI-weighted exponential decay."""
        if not samples:
            return []

        # Exponential moving average with PHI time constant
        alpha = 1.0 / (PHI * self.sample_rate * 0.01)  # ~16ms time constant
        ema = samples[0]
        result: list[float] = []

        for s in samples:
            ema = alpha * s + (1 - alpha) * ema
            result.append(s - ema)

        return result

    def analyze(self, samples: list[float]) -> dict:
        """Analyze DC offset characteristics."""
        if not samples:
            return {"dc_offset": 0, "dc_db": -120, "needs_removal": False}

        dc = self.detect_dc(samples)
        peak = max(abs(s) for s in samples) if samples else 1.0
        dc_ratio = abs(dc) / peak if peak > 0 else 0

        return {
            "dc_offset": round(dc, 8),
            "dc_db": round(20 * math.log10(abs(dc)), 1) if abs(dc) > 0 else -120,
            "dc_ratio": round(dc_ratio, 6),
            "needs_removal": dc_ratio > 0.001,
            "sample_count": len(samples),
        }

    def auto_remove(self, samples: list[float]) -> list[float]:
        """Automatically choose and apply best DC removal."""
        info = self.analyze(samples)

        if not info["needs_removal"]:
            return list(samples)

        # Use high-pass for general case
        return self.remove_highpass(samples)


def main() -> None:
    print("DC Offset Remover")
    remover = DCRemover()

    # Signal with DC offset
    n = SAMPLE_RATE
    dc_offset = 0.15
    samples = [dc_offset + 0.5 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    info = remover.analyze(samples)
    print(f"  DC offset: {info['dc_offset']:.6f}")
    print(f"  DC dB: {info['dc_db']:.1f}")
    print(f"  Needs removal: {info['needs_removal']}")

    # Test all methods
    for method_name, method in [
        ("mean", remover.remove_mean),
        ("highpass", remover.remove_highpass),
        ("adaptive", remover.remove_adaptive),
        ("phi_weighted", remover.remove_phi_weighted),
        ("auto", remover.auto_remove),
    ]:
        result = method(samples)
        residual = remover.detect_dc(result)
        print(f"  {method_name:15s}: residual DC = {residual:+.8f}")

    print("Done.")


if __name__ == "__main__":
    main()
