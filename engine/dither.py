"""
DUBFORGE — Dither Engine  (Session 213)

Dithering and noise shaping for bit-depth reduction.
TPDF, RPDF, shaped noise, PHI-distributed dither.
"""

import math
import random
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class DitherConfig:
    """Dithering configuration."""
    dither_type: str = "tpdf"  # none, rpdf, tpdf, shaped, phi
    target_bits: int = 16
    noise_shaping: bool = False
    shape_order: int = 1  # 1st or 2nd order
    amplitude: float = 1.0  # dither amplitude in LSB


class DitherEngine:
    """Apply dithering for bit-depth reduction."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.error_buffer: list[float] = [0.0, 0.0]

    def _quantize(self, value: float, bits: int) -> float:
        """Quantize to target bit depth."""
        levels = 2 ** (bits - 1) - 1
        return round(value * levels) / levels

    def _rpdf_noise(self) -> float:
        """Rectangular probability density function noise."""
        return self.rng.uniform(-1, 1)

    def _tpdf_noise(self) -> float:
        """Triangular probability density function noise."""
        return self.rng.uniform(-1, 1) + self.rng.uniform(-1, 1)

    def _phi_noise(self) -> float:
        """PHI-distributed noise (quasi-random)."""
        # Low-discrepancy sequence based on PHI
        if not hasattr(self, '_phi_state'):
            self._phi_state = self.rng.random()
        self._phi_state = (self._phi_state + 1.0 / PHI) % 1.0
        return self._phi_state * 2 - 1

    def apply_dither(self, samples: list[float],
                     config: DitherConfig | None = None) -> list[float]:
        """Apply dithering to audio samples."""
        cfg = config or DitherConfig()
        lsb = 1.0 / (2 ** (cfg.target_bits - 1) - 1)
        self.error_buffer = [0.0, 0.0]

        result: list[float] = []

        for s in samples:
            # Generate dither noise
            if cfg.dither_type == "none":
                noise = 0.0
            elif cfg.dither_type == "rpdf":
                noise = self._rpdf_noise() * lsb * cfg.amplitude * 0.5
            elif cfg.dither_type == "tpdf":
                noise = self._tpdf_noise() * lsb * cfg.amplitude * 0.5
            elif cfg.dither_type == "shaped":
                noise = self._tpdf_noise() * lsb * cfg.amplitude * 0.5
            elif cfg.dither_type == "phi":
                noise = self._phi_noise() * lsb * cfg.amplitude * 0.5
            else:
                noise = 0.0

            # Add noise shaping feedback
            shaped = s
            if cfg.noise_shaping:
                if cfg.shape_order >= 1:
                    shaped -= self.error_buffer[0] * 0.5
                if cfg.shape_order >= 2:
                    shaped += self.error_buffer[1] * 0.25

            # Add dither then quantize
            dithered = shaped + noise
            quantized = self._quantize(dithered, cfg.target_bits)
            quantized = max(-1.0, min(1.0, quantized))

            # Track quantization error for noise shaping
            error = quantized - shaped
            self.error_buffer[1] = self.error_buffer[0]
            self.error_buffer[0] = error

            result.append(quantized)

        return result

    def reduce_bit_depth(self, samples: list[float],
                         target_bits: int = 16,
                         dither: bool = True) -> list[float]:
        """Reduce bit depth with optional dithering."""
        cfg = DitherConfig(
            dither_type="tpdf" if dither else "none",
            target_bits=target_bits,
            noise_shaping=dither,
        )
        return self.apply_dither(samples, cfg)

    def truncate(self, samples: list[float],
                 target_bits: int = 16) -> list[float]:
        """Simple truncation (no dither)."""
        levels = 2 ** (target_bits - 1) - 1
        return [
            math.floor(s * levels) / levels
            for s in samples
        ]

    def measure_noise_floor(self, samples: list[float]) -> float:
        """Measure noise floor in dB."""
        if not samples:
            return -120.0

        # Use quiet section (last 10%)
        n = max(1, len(samples) // 10)
        tail = samples[-n:]
        rms = math.sqrt(sum(s * s for s in tail) / n) if tail else 0
        return 20 * math.log10(rms) if rms > 0 else -120.0

    def compare_dither_types(self, samples: list[float],
                             target_bits: int = 16) -> dict[str, dict]:
        """Compare all dither types on same input."""
        results: dict[str, dict] = {}

        for dtype in ["none", "rpdf", "tpdf", "shaped", "phi"]:
            cfg = DitherConfig(
                dither_type=dtype,
                target_bits=target_bits,
                noise_shaping=(dtype == "shaped"),
            )
            self.rng = random.Random(42)  # Reset for consistency
            dithered = self.apply_dither(samples, cfg)

            # Compute error stats
            errors = [d - s for d, s in zip(dithered, samples)]
            rms_error = math.sqrt(sum(e * e for e in errors) / len(errors)) \
                if errors else 0
            max_error = max(abs(e) for e in errors) if errors else 0

            results[dtype] = {
                "rms_error": round(rms_error, 8),
                "max_error": round(max_error, 8),
                "snr_db": round(-20 * math.log10(rms_error), 1) if rms_error > 0 else 120,
            }

        return results


def main() -> None:
    print("Dither Engine")
    engine = DitherEngine()

    # Test signal: low-level sine
    n = SAMPLE_RATE
    samples = [0.01 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    results = engine.compare_dither_types(samples, target_bits=16)
    for dtype, stats in results.items():
        print(f"  {dtype:8s}: RMS={stats['rms_error']:.8f} "
              f"SNR={stats['snr_db']:.1f}dB")

    # Quick reduce
    reduced = engine.reduce_bit_depth(samples, target_bits=8)
    print(f"\n  8-bit reduction: {len(reduced)} samples")
    print(f"  Noise floor: {engine.measure_noise_floor(reduced):.1f} dB")

    print("Done.")


if __name__ == "__main__":
    main()
