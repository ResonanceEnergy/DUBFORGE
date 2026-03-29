"""
DUBFORGE — Saturation Engine  (Session 225)

Saturation/warmth processors — tube, tape, transistor,
console, PHI-saturation, harmonic enhancement.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
from engine.turboquant import (
    compress_audio_buffer,
    CompressedAudioBuffer,
    phi_optimal_bits,
    TurboQuantConfig,
)
SAMPLE_RATE = 48000


def tq_compress_saturation(
    signal: list[float],
    label: str = "saturation",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress saturation output."""
    bits = phi_optimal_bits(len(signal))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(signal, label, cfg, sample_rate=sample_rate)


SATURATION_TYPES = [
    "tube", "tape", "transistor", "console", "phi", "hard", "soft",
]


@dataclass
class SatConfig:
    """Saturation configuration."""
    sat_type: str = "tape"
    drive: float = 0.5  # 0-1
    mix: float = 1.0  # wet/dry
    output_gain: float = 1.0
    tone: float = 0.5  # 0=dark, 1=bright


class SaturationEngine:
    """Apply saturation/warmth to audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _tube(self, x: float, drive: float) -> float:
        """Tube saturation — asymmetric soft clip."""
        d = 1 + drive * 10
        if x >= 0:
            return 1.0 - math.exp(-d * x) if d * x < 50 else 1.0
        else:
            return -(1.0 - math.exp(d * x)) if -d * x < 50 else -1.0

    def _tape(self, x: float, drive: float) -> float:
        """Tape saturation — smooth compression."""
        d = 1 + drive * 5
        return math.tanh(d * x)

    def _transistor(self, x: float, drive: float) -> float:
        """Transistor saturation — harder clipping."""
        d = 1 + drive * 8
        driven = d * x
        if abs(driven) < 1.0:
            return driven - (driven ** 3) / 3
        return math.copysign(2 / 3, driven)

    def _console(self, x: float, drive: float) -> float:
        """Console saturation — subtle harmonic enrichment."""
        d = 1 + drive * 3
        driven = d * x
        return driven / (1 + abs(driven))

    def _phi(self, x: float, drive: float) -> float:
        """PHI saturation — golden ratio waveshaping."""
        d = 1 + drive * PHI * 4
        driven = d * x
        return math.tanh(driven) * (1 / PHI) + \
            math.tanh(driven * PHI) * (1 - 1 / PHI)

    def _hard(self, x: float, drive: float) -> float:
        """Hard clipping."""
        d = 1 + drive * 10
        return max(-1.0, min(1.0, d * x))

    def _soft(self, x: float, drive: float) -> float:
        """Soft clipping (cubic)."""
        d = 1 + drive * 5
        driven = d * x
        if abs(driven) <= 1 / 3:
            return 2 * driven
        elif abs(driven) <= 2 / 3:
            sign = 1 if driven >= 0 else -1
            v = abs(driven)
            return sign * (3 - (2 - 3 * v) ** 2) / 3
        else:
            return math.copysign(1.0, driven)

    def _get_saturator(self, sat_type: str) -> callable:
        """Get saturation function by type."""
        return {
            "tube": self._tube,
            "tape": self._tape,
            "transistor": self._transistor,
            "console": self._console,
            "phi": self._phi,
            "hard": self._hard,
            "soft": self._soft,
        }.get(sat_type, self._tape)

    def saturate(self, samples: list[float],
                 config: SatConfig | None = None) -> list[float]:
        """Apply saturation to audio."""
        cfg = config or SatConfig()
        saturator = self._get_saturator(cfg.sat_type)

        result: list[float] = []
        for s in samples:
            wet = saturator(s, cfg.drive) * cfg.output_gain
            dry = s * cfg.output_gain

            # Tone control (simple)
            if hasattr(self, '_prev'):
                if cfg.tone < 0.5:
                    # Darker: low-pass
                    alpha = cfg.tone * 2
                    wet = alpha * wet + (1 - alpha) * self._prev
            self._prev = wet

            # Mix
            out = wet * cfg.mix + dry * (1 - cfg.mix)
            result.append(max(-1.0, min(1.0, out)))

        self._prev = 0.0
        return result

    def harmonic_exciter(self, samples: list[float],
                         amount: float = 0.3,
                         frequency: float = 3000) -> list[float]:
        """Add harmonic excitement above a frequency."""
        # Simple high-shelf + saturation
        result: list[float] = []
        prev = 0.0
        alpha = 2 * math.pi * frequency / self.sample_rate

        for s in samples:
            # High-frequency extraction
            hf = s - prev * (1 - alpha)
            prev = s

            # Saturate high frequencies
            excited = math.tanh(hf * (1 + amount * 5)) * amount
            result.append(s + excited)

        # Normalize
        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 1.0:
            result = [s / pk for s in result]

        return result

    def warmth(self, samples: list[float],
               amount: float = 0.5) -> list[float]:
        """Add warmth (subtle tube + low-end boost)."""
        cfg = SatConfig(
            sat_type="tube",
            drive=amount * 0.3,
            mix=amount,
            output_gain=1.0,
        )
        return self.saturate(samples, cfg)

    def compare_types(self, samples: list[float],
                      drive: float = 0.5) -> dict[str, dict]:
        """Compare all saturation types."""
        results: dict[str, dict] = {}

        for sat_type in SATURATION_TYPES:
            cfg = SatConfig(sat_type=sat_type, drive=drive)
            output = self.saturate(samples, cfg)

            pk = max(abs(s) for s in output) if output else 0
            rms = math.sqrt(sum(s * s for s in output) / len(output)) \
                if output else 0

            results[sat_type] = {
                "peak": round(pk, 4),
                "rms": round(rms, 4),
                "crest_db": round(
                    20 * math.log10(pk / rms) if rms > 0 else 0, 1
                ),
            }

        return results


def main() -> None:
    print("Saturation Engine")
    engine = SaturationEngine()

    # Test signal
    n = SAMPLE_RATE
    samples = [0.5 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    results = engine.compare_types(samples, drive=0.6)
    for sat_type, stats in results.items():
        print(f"  {sat_type:12s}: peak={stats['peak']:.4f} "
              f"rms={stats['rms']:.4f} crest={stats['crest_db']:.1f}dB")

    # Warmth
    warm = engine.warmth(samples, 0.5)
    print(f"\n  Warmth: peak={max(abs(s) for s in warm):.3f}")

    # Exciter
    excited = engine.harmonic_exciter(samples, 0.4)
    print(f"  Exciter: peak={max(abs(s) for s in excited):.3f}")

    print("Done.")


if __name__ == "__main__":
    main()
