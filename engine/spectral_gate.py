"""
DUBFORGE — Spectral Gate  (Session 224)

Frequency-selective gating — gate individual frequency bands
for surgical noise removal and creative effects.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class BandGateConfig:
    """Configuration for a frequency band gate."""
    low_freq: float
    high_freq: float
    threshold_db: float = -40.0
    attack_ms: float = 5.0
    release_ms: float = 50.0
    enabled: bool = True


class SpectralGate:
    """Frequency-selective noise gate."""

    def __init__(self, sample_rate: int = SAMPLE_RATE,
                 fft_size: int = 1024):
        self.sample_rate = sample_rate
        self.fft_size = fft_size

    def _dft_bin_range(self, low_freq: float,
                       high_freq: float) -> tuple[int, int]:
        """Get DFT bin range for frequency band."""
        lo = max(0, int(low_freq * self.fft_size / self.sample_rate))
        hi = min(
            self.fft_size // 2,
            int(high_freq * self.fft_size / self.sample_rate),
        )
        return lo, hi

    def _band_energy(self, samples: list[float],
                     low_freq: float, high_freq: float) -> float:
        """Compute energy in a frequency band."""
        n = min(len(samples), self.fft_size)
        lo_bin, hi_bin = self._dft_bin_range(low_freq, high_freq)

        energy = 0.0
        for k in range(lo_bin, hi_bin + 1):
            real = 0.0
            imag = 0.0
            for i in range(n):
                angle = 2 * math.pi * k * i / n
                real += samples[i] * math.cos(angle)
                imag -= samples[i] * math.sin(angle)
            energy += (real * real + imag * imag) / (n * n)

        return math.sqrt(energy)

    def gate_band(self, samples: list[float],
                  config: BandGateConfig) -> list[float]:
        """Apply gate to a specific frequency band."""
        if not config.enabled or not samples:
            return list(samples)

        threshold = 10 ** (config.threshold_db / 20)
        attack_samples = max(1, int(config.attack_ms * self.sample_rate / 1000))
        release_samples = max(1, int(config.release_ms * self.sample_rate / 1000))

        # Process in overlapping blocks
        hop = self.fft_size // 2
        result = list(samples)
        env = 0.0

        for block_start in range(0, len(samples) - self.fft_size, hop):
            block = samples[block_start:block_start + self.fft_size]

            # Measure band energy
            energy = self._band_energy(block, config.low_freq, config.high_freq)

            # Gate envelope
            if energy > threshold:
                target = 1.0
                coeff = 1.0 / attack_samples
            else:
                target = 0.0
                coeff = 1.0 / release_samples

            for i in range(hop):
                env += (target - env) * coeff
                idx = block_start + i
                if idx < len(result):
                    result[idx] *= env

        return result

    def multi_band_gate(self, samples: list[float],
                        bands: list[BandGateConfig] | None = None) -> list[float]:
        """Apply gates to multiple frequency bands."""
        if bands is None:
            bands = self.default_bands()

        result = list(samples)
        for band in bands:
            if band.enabled:
                result = self.gate_band(result, band)

        return result

    def default_bands(self) -> list[BandGateConfig]:
        """Get default dubstep-oriented band gates."""
        return [
            BandGateConfig(20, 100, threshold_db=-50, release_ms=100),
            BandGateConfig(100, 500, threshold_db=-45, release_ms=80),
            BandGateConfig(500, 2000, threshold_db=-40, release_ms=60),
            BandGateConfig(2000, 8000, threshold_db=-35, release_ms=40),
            BandGateConfig(8000, 20000, threshold_db=-30, release_ms=30),
        ]

    def phi_bands(self) -> list[BandGateConfig]:
        """PHI-spaced frequency band gates."""
        bands: list[BandGateConfig] = []
        freq = 30.0

        for i in range(8):
            next_freq = freq * PHI
            if next_freq > self.sample_rate / 2:
                break
            bands.append(BandGateConfig(
                low_freq=freq,
                high_freq=next_freq,
                threshold_db=-40 - i * 2,
                release_ms=80 - i * 5,
            ))
            freq = next_freq

        return bands

    def spectral_freeze(self, samples: list[float],
                        position: float = 0.5) -> list[float]:
        """Freeze spectrum at a point (creative effect)."""
        n = len(samples)
        pos = int(position * n)
        pos = max(0, min(pos, n - self.fft_size))

        # Extract spectrum at position
        block = samples[pos:pos + self.fft_size]

        # Resynthesize with frozen spectrum
        result: list[float] = []
        for i in range(n):
            # Use modular indexing into frozen block
            idx = i % self.fft_size
            s = block[idx] * 0.5
            result.append(s)

        return result

    def analyze_bands(self, samples: list[float]) -> dict[str, float]:
        """Analyze energy in each default band."""
        result: dict[str, float] = {}
        for band in self.default_bands():
            energy = self._band_energy(
                samples[:self.fft_size] if len(samples) >= self.fft_size
                else samples,
                band.low_freq,
                band.high_freq,
            )
            db = 20 * math.log10(energy) if energy > 0 else -120
            result[f"{band.low_freq:.0f}-{band.high_freq:.0f}Hz"] = round(db, 1)
        return result


def main() -> None:
    print("Spectral Gate")
    gate = SpectralGate(fft_size=512)

    # Signal with noise
    import random
    rng = random.Random(42)
    n = SAMPLE_RATE
    samples: list[float] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        signal = 0.5 * math.sin(2 * math.pi * 200 * t)
        noise = rng.gauss(0, 0.05)
        samples.append(signal + noise)

    # Analyze
    bands = gate.analyze_bands(samples)
    print("  Band energy:")
    for band, db in bands.items():
        print(f"    {band}: {db} dB")

    # Apply gate
    gated = gate.multi_band_gate(samples)
    print(f"\n  Gated: {len(gated)} samples")
    print(f"  Input peak: {max(abs(s) for s in samples):.3f}")
    print(f"  Output peak: {max(abs(s) for s in gated):.3f}")

    print("Done.")


if __name__ == "__main__":
    main()
