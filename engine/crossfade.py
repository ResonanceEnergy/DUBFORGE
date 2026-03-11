"""
DUBFORGE — Crossfade Engine  (Session 211)

Generate and apply crossfades between audio regions —
linear, equal-power, S-curve, PHI-curve, logarithmic.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000

FADE_TYPES = {
    "linear", "equal_power", "s_curve",
    "logarithmic", "exponential", "phi",
}


@dataclass
class FadeConfig:
    """Crossfade configuration."""
    fade_type: str = "equal_power"
    duration_ms: float = 50
    curve_amount: float = 1.0  # shape parameter


class CrossfadeEngine:
    """Apply crossfades to audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _fade_curve(self, t: float, fade_type: str,
                    curve: float = 1.0) -> float:
        """Compute fade value at position t (0-1)."""
        t = max(0.0, min(1.0, t))

        if fade_type == "linear":
            return t
        elif fade_type == "equal_power":
            return math.sqrt(t)
        elif fade_type == "s_curve":
            return t * t * (3 - 2 * t)
        elif fade_type == "logarithmic":
            return math.log1p(t * (math.e - 1)) if t > 0 else 0.0
        elif fade_type == "exponential":
            return (math.exp(t * curve) - 1) / (math.exp(curve) - 1) \
                if curve != 0 else t
        elif fade_type == "phi":
            return t ** (1.0 / PHI)
        return t

    def fade_in(self, samples: list[float],
                config: FadeConfig | None = None) -> list[float]:
        """Apply fade-in."""
        cfg = config or FadeConfig()
        fade_samples = int(cfg.duration_ms * self.sample_rate / 1000)
        fade_samples = min(fade_samples, len(samples))

        result = list(samples)
        for i in range(fade_samples):
            t = i / fade_samples
            gain = self._fade_curve(t, cfg.fade_type, cfg.curve_amount)
            result[i] *= gain

        return result

    def fade_out(self, samples: list[float],
                 config: FadeConfig | None = None) -> list[float]:
        """Apply fade-out."""
        cfg = config or FadeConfig()
        fade_samples = int(cfg.duration_ms * self.sample_rate / 1000)
        fade_samples = min(fade_samples, len(samples))

        result = list(samples)
        n = len(result)
        for i in range(fade_samples):
            t = i / fade_samples
            gain = self._fade_curve(t, cfg.fade_type, cfg.curve_amount)
            result[n - 1 - i] *= gain

        return result

    def crossfade(self, audio_a: list[float],
                  audio_b: list[float],
                  config: FadeConfig | None = None) -> list[float]:
        """Crossfade between two audio segments."""
        cfg = config or FadeConfig()
        fade_samples = int(cfg.duration_ms * self.sample_rate / 1000)
        fade_samples = min(fade_samples, len(audio_a), len(audio_b))

        # Non-faded portion of A
        result = list(audio_a[:-fade_samples]) if fade_samples > 0 else list(audio_a)

        # Crossfade region
        for i in range(fade_samples):
            t = i / fade_samples
            gain_b = self._fade_curve(t, cfg.fade_type, cfg.curve_amount)
            gain_a = 1.0 - gain_b

            if cfg.fade_type == "equal_power":
                gain_a = math.sqrt(1.0 - t)
                gain_b = math.sqrt(t)

            a_idx = len(audio_a) - fade_samples + i
            s = audio_a[a_idx] * gain_a + audio_b[i] * gain_b
            result.append(s)

        # Non-faded portion of B
        result.extend(audio_b[fade_samples:])

        return result

    def crossfade_regions(self, regions: list[list[float]],
                          config: FadeConfig | None = None) -> list[float]:
        """Crossfade a sequence of audio regions."""
        if not regions:
            return []
        if len(regions) == 1:
            return list(regions[0])

        result = list(regions[0])
        for i in range(1, len(regions)):
            result = self.crossfade(result, regions[i], config)

        return result

    def generate_fade_curve(self, duration_ms: float,
                            fade_type: str = "equal_power",
                            curve: float = 1.0) -> list[float]:
        """Generate a fade curve as sample values."""
        n = int(duration_ms * self.sample_rate / 1000)
        return [self._fade_curve(i / n, fade_type, curve)
                for i in range(n)]

    def phi_crossfade(self, audio_a: list[float],
                      audio_b: list[float]) -> list[float]:
        """PHI-ratio crossfade — golden section blend."""
        cfg = FadeConfig(
            fade_type="phi",
            duration_ms=len(audio_a) / self.sample_rate * 1000 / PHI,
        )
        return self.crossfade(audio_a, audio_b, cfg)


def main() -> None:
    print("Crossfade Engine")
    engine = CrossfadeEngine()

    n = SAMPLE_RATE  # 1 second
    tone_a = [0.8 * math.sin(2 * math.pi * 220 * i / SAMPLE_RATE)
              for i in range(n)]
    tone_b = [0.8 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
              for i in range(n)]

    for fade_type in FADE_TYPES:
        cfg = FadeConfig(fade_type=fade_type, duration_ms=100)
        result = engine.crossfade(tone_a, tone_b, cfg)
        print(f"  {fade_type}: {len(result)} samples")

    # PHI crossfade
    phi = engine.phi_crossfade(tone_a, tone_b)
    print(f"  phi_crossfade: {len(phi)} samples")

    # Fade in/out
    fi = engine.fade_in(tone_a, FadeConfig(duration_ms=50))
    fo = engine.fade_out(tone_a, FadeConfig(duration_ms=50))
    print(f"  fade_in: start={fi[0]:.4f}")
    print(f"  fade_out: end={fo[-1]:.4f}")

    print("Done.")


if __name__ == "__main__":
    main()
