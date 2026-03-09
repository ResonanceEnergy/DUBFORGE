"""
DUBFORGE — Resonance Engine  (Session 226)

Resonant filter bank, comb filters, resonant bodies,
formant resonance, PHI-tuned resonance.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 48000
A4_432 = 432.0


@dataclass
class ResonatorConfig:
    """Resonator configuration."""
    frequency: float = 440.0
    resonance: float = 0.9  # Q factor, 0-1
    gain: float = 1.0
    damping: float = 0.01


class ResonanceEngine:
    """Resonance and comb filter processing."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def resonant_filter(self, samples: list[float],
                        frequency: float = 440.0,
                        resonance: float = 0.9) -> list[float]:
        """Apply resonant bandpass filter (biquad)."""
        omega = 2 * math.pi * frequency / self.sample_rate
        alpha = math.sin(omega) / (2 * max(0.1, resonance * 20))

        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(omega)
        a2 = 1 - alpha

        # Normalize
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0

        result: list[float] = []
        x1 = x2 = y1 = y2 = 0.0

        for s in samples:
            y = b0 * s + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1 = x1, s
            y2, y1 = y1, y
            result.append(y)

        return result

    def comb_filter(self, samples: list[float],
                    delay_ms: float = 10.0,
                    feedback: float = 0.7) -> list[float]:
        """Apply comb filter (feedforward + feedback)."""
        delay_samples = max(1, int(delay_ms * self.sample_rate / 1000))
        buffer = [0.0] * delay_samples
        buf_idx = 0

        result: list[float] = []
        for s in samples:
            delayed = buffer[buf_idx]
            out = s + delayed * feedback
            buffer[buf_idx] = out
            buf_idx = (buf_idx + 1) % delay_samples
            result.append(out * 0.5)

        return result

    def comb_filter_tuned(self, samples: list[float],
                          frequency: float = 440.0,
                          feedback: float = 0.9) -> list[float]:
        """Comb filter tuned to a frequency."""
        delay_ms = 1000.0 / frequency
        return self.comb_filter(samples, delay_ms, feedback)

    def resonant_body(self, samples: list[float],
                      frequencies: list[float] | None = None,
                      damping: float = 0.01) -> list[float]:
        """Simulate a resonant body (parallel resonators)."""
        if frequencies is None:
            # Guitar-like body resonances
            frequencies = [100, 200, 400, 800, 1600]

        n = len(samples)
        result = [0.0] * n

        for freq in frequencies:
            resonated = self.resonant_filter(samples, freq, 0.95)
            # Apply damping
            for i in range(n):
                result[i] += resonated[i] * (1 - damping)

        # Normalize
        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 0:
            result = [s / pk * 0.9 for s in result]

        return result

    def phi_resonance(self, samples: list[float],
                      fundamental: float = 100.0,
                      count: int = 6) -> list[float]:
        """Apply PHI-ratio tuned resonators."""
        frequencies = [fundamental * (PHI ** i) for i in range(count)
                       if fundamental * (PHI ** i) < self.sample_rate / 2]

        n = len(samples)
        result = list(samples)

        for freq in frequencies:
            resonated = self.resonant_filter(
                samples, freq, 0.95
            )
            gain = 1.0 / (PHI ** frequencies.index(freq))
            for i in range(n):
                result[i] += resonated[i] * gain * 0.3

        # Limit
        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 1.0:
            result = [s / pk for s in result]

        return result

    def allpass(self, samples: list[float],
                delay_ms: float = 5.0,
                coefficient: float = 0.7) -> list[float]:
        """Apply allpass filter (phase shift, used in reverbs)."""
        delay = max(1, int(delay_ms * self.sample_rate / 1000))
        buffer = [0.0] * delay
        buf_idx = 0

        result: list[float] = []
        for s in samples:
            delayed = buffer[buf_idx]
            out = -coefficient * s + delayed
            buffer[buf_idx] = s + coefficient * out
            buf_idx = (buf_idx + 1) % delay
            result.append(out)

        return result

    def formant_filter(self, samples: list[float],
                       vowel: str = "a") -> list[float]:
        """Apply formant resonance (vowel filter)."""
        formants = {
            "a": [(800, 0.9), (1200, 0.8), (2500, 0.6)],
            "e": [(400, 0.9), (2000, 0.8), (2800, 0.6)],
            "i": [(300, 0.9), (2300, 0.8), (3000, 0.6)],
            "o": [(500, 0.9), (800, 0.8), (2500, 0.6)],
            "u": [(350, 0.9), (600, 0.8), (2400, 0.6)],
        }

        freqs_qs = formants.get(vowel, formants["a"])
        n = len(samples)
        result = [0.0] * n

        for freq, q in freqs_qs:
            filtered = self.resonant_filter(samples, freq, q)
            for i in range(n):
                result[i] += filtered[i]

        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 0:
            result = [s / pk * 0.8 for s in result]

        return result

    def get_resonance_spectrum(self, frequency: float,
                               count: int = 8) -> list[dict]:
        """Get harmonic resonance frequencies."""
        return [
            {
                "harmonic": n,
                "frequency": round(frequency * n, 2),
                "phi_frequency": round(frequency * (PHI ** (n - 1)), 2),
            }
            for n in range(1, count + 1)
        ]


def main() -> None:
    print("Resonance Engine")
    engine = ResonanceEngine()

    # Impulse signal
    n = SAMPLE_RATE
    impulse: list[float] = [0.0] * n
    impulse[0] = 1.0

    # Test resonant filter
    res = engine.resonant_filter(impulse, 440, 0.99)
    print(f"  Resonant 440Hz: peak={max(abs(s) for s in res):.3f}")

    # Comb filter
    comb = engine.comb_filter(impulse, delay_ms=5, feedback=0.8)
    print(f"  Comb filter: peak={max(abs(s) for s in comb):.3f}")

    # PHI resonance
    noise = [0.5 * math.sin(2 * math.pi * 100 * i / SAMPLE_RATE) +
             0.3 * math.sin(2 * math.pi * 250 * i / SAMPLE_RATE)
             for i in range(n)]

    phi_res = engine.phi_resonance(noise, fundamental=100)
    print(f"  PHI resonance: peak={max(abs(s) for s in phi_res):.3f}")

    # Formant
    for vowel in "aeiou":
        fmt = engine.formant_filter(noise, vowel)
        print(f"  Formant '{vowel}': peak={max(abs(s) for s in fmt):.3f}")

    # Spectrum info
    spec = engine.get_resonance_spectrum(100)
    for s in spec[:4]:
        print(f"  H{s['harmonic']}: {s['frequency']}Hz "
              f"(PHI: {s['phi_frequency']}Hz)")

    print("Done.")


if __name__ == "__main__":
    main()
