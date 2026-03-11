"""
DUBFORGE — Panning Engine  (Session 220)

Stereo panning: linear, constant power, binaural-like,
auto-pan LFO, PHI-spiral pan, mid-side processing.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class PanConfig:
    """Pan configuration."""
    position: float = 0.0  # -1 full left, +1 full right
    law: str = "constant_power"  # linear, constant_power, phi


@dataclass
class StereoOutput:
    """Stereo audio output."""
    left: list[float]
    right: list[float]

    @property
    def duration(self) -> float:
        return len(self.left) / SAMPLE_RATE

    @property
    def peak_left(self) -> float:
        return max(abs(s) for s in self.left) if self.left else 0

    @property
    def peak_right(self) -> float:
        return max(abs(s) for s in self.right) if self.right else 0


class PanningEngine:
    """Stereo panning processor."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def pan_linear(self, samples: list[float],
                   position: float = 0.0) -> StereoOutput:
        """Linear panning law."""
        p = (position + 1) / 2  # 0-1 range
        l_gain = 1.0 - p
        r_gain = p

        return StereoOutput(
            left=[s * l_gain for s in samples],
            right=[s * r_gain for s in samples],
        )

    def pan_constant_power(self, samples: list[float],
                           position: float = 0.0) -> StereoOutput:
        """Constant-power (equal-power) panning."""
        angle = (position + 1) * math.pi / 4  # 0 to pi/2
        l_gain = math.cos(angle)
        r_gain = math.sin(angle)

        return StereoOutput(
            left=[s * l_gain for s in samples],
            right=[s * r_gain for s in samples],
        )

    def pan_phi(self, samples: list[float],
                position: float = 0.0) -> StereoOutput:
        """PHI-weighted panning law."""
        p = (position + 1) / 2
        # PHI-shaped curves
        l_gain = (1 - p) ** (1 / PHI)
        r_gain = p ** (1 / PHI)

        # Normalize to maintain unity gain at center
        norm = math.sqrt(l_gain ** 2 + r_gain ** 2) or 1.0
        l_gain /= norm
        r_gain /= norm

        return StereoOutput(
            left=[s * l_gain for s in samples],
            right=[s * r_gain for s in samples],
        )

    def pan(self, samples: list[float],
            config: PanConfig | None = None) -> StereoOutput:
        """Apply panning with config."""
        cfg = config or PanConfig()
        pos = max(-1.0, min(1.0, cfg.position))

        if cfg.law == "linear":
            return self.pan_linear(samples, pos)
        elif cfg.law == "phi":
            return self.pan_phi(samples, pos)
        else:
            return self.pan_constant_power(samples, pos)

    def auto_pan(self, samples: list[float],
                 rate_hz: float = 2.0,
                 depth: float = 1.0,
                 shape: str = "sine") -> StereoOutput:
        """Auto-pan with LFO."""
        n = len(samples)
        left: list[float] = []
        right: list[float] = []

        for i in range(n):
            t = i / self.sample_rate

            # LFO position
            if shape == "sine":
                pos = math.sin(2 * math.pi * rate_hz * t) * depth
            elif shape == "triangle":
                phase = (t * rate_hz) % 1.0
                pos = (4 * abs(phase - 0.5) - 1) * depth
            elif shape == "square":
                phase = (t * rate_hz) % 1.0
                pos = (1.0 if phase < 0.5 else -1.0) * depth
            else:
                pos = math.sin(2 * math.pi * rate_hz * t) * depth

            # Constant power at each position
            angle = (pos + 1) * math.pi / 4
            left.append(samples[i] * math.cos(angle))
            right.append(samples[i] * math.sin(angle))

        return StereoOutput(left=left, right=right)

    def phi_spiral_pan(self, samples: list[float],
                       revolutions: float = 1.0) -> StereoOutput:
        """PHI-spiral panning — logarithmic spiral pan path."""
        n = len(samples)
        left: list[float] = []
        right: list[float] = []

        for i in range(n):
            t = i / n
            # PHI spiral angle
            angle_rad = t * revolutions * 2 * math.pi
            radius = PHI ** (t * 2 - 1)  # expanding/contracting

            pos = math.sin(angle_rad) * min(1.0, radius)
            a = (pos + 1) * math.pi / 4
            left.append(samples[i] * math.cos(a))
            right.append(samples[i] * math.sin(a))

        return StereoOutput(left=left, right=right)

    def mid_side_encode(self, left: list[float],
                        right: list[float]) -> tuple[list[float], list[float]]:
        """Encode stereo to mid-side."""
        n = min(len(left), len(right))
        mid = [(left[i] + right[i]) * 0.5 for i in range(n)]
        side = [(left[i] - right[i]) * 0.5 for i in range(n)]
        return mid, side

    def mid_side_decode(self, mid: list[float],
                        side: list[float]) -> tuple[list[float], list[float]]:
        """Decode mid-side to stereo."""
        n = min(len(mid), len(side))
        left = [mid[i] + side[i] for i in range(n)]
        right = [mid[i] - side[i] for i in range(n)]
        return left, right

    def stereo_width(self, left: list[float], right: list[float],
                     width: float = 1.0) -> tuple[list[float], list[float]]:
        """Adjust stereo width. 0=mono, 1=normal, 2=super wide."""
        mid, side = self.mid_side_encode(left, right)

        # Scale side signal
        side = [s * width for s in side]

        return self.mid_side_decode(mid, side)

    def haas_delay(self, samples: list[float],
                   delay_ms: float = 10,
                   side: str = "right") -> StereoOutput:
        """Haas effect — short delay creates spatial impression."""
        delay_samples = int(delay_ms * self.sample_rate / 1000)

        if side == "right":
            left = list(samples)
            right = [0.0] * delay_samples + list(samples)
            # Trim to match
            right = right[:len(samples)]
        else:
            right = list(samples)
            left = [0.0] * delay_samples + list(samples)
            left = left[:len(samples)]

        return StereoOutput(left=left, right=right)


def main() -> None:
    print("Panning Engine")
    panner = PanningEngine()

    # Test signal
    n = SAMPLE_RATE
    mono = [0.8 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
            for i in range(n)]

    # Test pan positions
    for pos in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        out = panner.pan_constant_power(mono, pos)
        print(f"  Pan {pos:+.1f}: L={out.peak_left:.3f} R={out.peak_right:.3f}")

    # Auto-pan
    auto = panner.auto_pan(mono, rate_hz=2.0, depth=0.8)
    print(f"\n  Auto-pan: L_peak={auto.peak_left:.3f} R_peak={auto.peak_right:.3f}")

    # PHI spiral
    spiral = panner.phi_spiral_pan(mono, revolutions=2.0)
    print(f"  PHI spiral: L={spiral.peak_left:.3f} R={spiral.peak_right:.3f}")

    # Stereo width
    stereo = panner.pan_constant_power(mono, 0.3)
    wide_l, wide_r = panner.stereo_width(stereo.left, stereo.right, 2.0)
    print(f"  Wide: L={max(abs(s) for s in wide_l):.3f} "
          f"R={max(abs(s) for s in wide_r):.3f}")

    # Haas
    haas = panner.haas_delay(mono, delay_ms=15)
    print(f"  Haas: L={haas.peak_left:.3f} R={haas.peak_right:.3f}")

    print("Done.")


if __name__ == "__main__":
    main()
