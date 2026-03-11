"""
DUBFORGE — Harmonic Generator  (Session 219)

Generate harmonic series, overtones, partials from fundamentals.
PHI harmonics, sub-harmonics, inharmonic spectra.
"""

import math
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000
@dataclass
class Partial:
    """A single partial/harmonic."""
    frequency: float
    amplitude: float
    phase: float = 0.0
    harmonic_number: float = 1.0


@dataclass
class HarmonicSpectrum:
    """A complete harmonic spectrum."""
    fundamental: float
    partials: list[Partial]

    @property
    def partial_count(self) -> int:
        return len(self.partials)

    def to_dict(self) -> dict:
        return {
            "fundamental": round(self.fundamental, 2),
            "partial_count": self.partial_count,
            "partials": [
                {
                    "freq": round(p.frequency, 2),
                    "amp": round(p.amplitude, 4),
                    "harmonic": round(p.harmonic_number, 3),
                }
                for p in self.partials
            ],
        }


class HarmonicGenerator:
    """Generate harmonic content."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def harmonic_series(self, fundamental: float,
                        count: int = 16,
                        rolloff: float = 1.0) -> HarmonicSpectrum:
        """Generate standard harmonic series."""
        partials: list[Partial] = []
        for n in range(1, count + 1):
            freq = fundamental * n
            if freq >= self.sample_rate / 2:
                break
            amp = 1.0 / (n ** rolloff)
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=float(n),
            ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def odd_harmonics(self, fundamental: float,
                      count: int = 8,
                      rolloff: float = 1.0) -> HarmonicSpectrum:
        """Generate odd-only harmonics (square wave character)."""
        partials: list[Partial] = []
        for i in range(count):
            n = 2 * i + 1
            freq = fundamental * n
            if freq >= self.sample_rate / 2:
                break
            amp = 1.0 / (n ** rolloff)
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=float(n),
            ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def even_harmonics(self, fundamental: float,
                       count: int = 8,
                       rolloff: float = 1.0) -> HarmonicSpectrum:
        """Generate even harmonics + fundamental."""
        partials = [Partial(
            frequency=fundamental,
            amplitude=1.0,
            harmonic_number=1.0,
        )]

        for i in range(1, count + 1):
            n = 2 * i
            freq = fundamental * n
            if freq >= self.sample_rate / 2:
                break
            amp = 1.0 / (n ** rolloff)
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=float(n),
            ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def sub_harmonics(self, fundamental: float,
                      count: int = 4) -> HarmonicSpectrum:
        """Generate sub-harmonics (below fundamental)."""
        partials: list[Partial] = []
        for n in range(count, 0, -1):
            div = n + 1
            freq = fundamental / div
            amp = 0.5 / n
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=1.0 / div,
            ))

        # Add fundamental
        partials.append(Partial(
            frequency=fundamental,
            amplitude=1.0,
            harmonic_number=1.0,
        ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def phi_harmonics(self, fundamental: float,
                      count: int = 12) -> HarmonicSpectrum:
        """Generate PHI-ratio harmonic series."""
        partials: list[Partial] = []
        for i in range(count):
            freq = fundamental * (PHI ** i)
            if freq >= self.sample_rate / 2:
                break
            amp = 1.0 / (PHI ** i)
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=PHI ** i,
            ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def inharmonic_spectrum(self, fundamental: float,
                            stretch: float = 1.0,
                            count: int = 16) -> HarmonicSpectrum:
        """Generate inharmonic spectrum (stretched partials)."""
        partials: list[Partial] = []
        for n in range(1, count + 1):
            # Stretched harmonic: f * n^(1+stretch/100)
            freq = fundamental * (n ** (1 + stretch / 100))
            if freq >= self.sample_rate / 2:
                break
            amp = 1.0 / n
            partials.append(Partial(
                frequency=freq,
                amplitude=amp,
                harmonic_number=freq / fundamental,
            ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def bell_spectrum(self, fundamental: float) -> HarmonicSpectrum:
        """Generate bell-like inharmonic spectrum."""
        # Bell ratios (approximately based on church bell)
        ratios = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514,
                  2.662, 3.0, 3.642, 4.0]
        amps = [0.3, 1.0, 0.8, 0.5, 0.4, 0.3,
                0.25, 0.2, 0.15, 0.1]

        partials: list[Partial] = []
        for ratio, amp in zip(ratios, amps):
            freq = fundamental * ratio
            if freq < self.sample_rate / 2:
                partials.append(Partial(
                    frequency=freq,
                    amplitude=amp,
                    harmonic_number=ratio,
                ))

        return HarmonicSpectrum(fundamental=fundamental, partials=partials)

    def render(self, spectrum: HarmonicSpectrum,
               duration_s: float = 1.0,
               amplitude: float = 0.8) -> list[float]:
        """Render spectrum to audio samples."""
        n = int(duration_s * self.sample_rate)
        samples = [0.0] * n

        # Normalize partial amplitudes
        total_amp = sum(p.amplitude for p in spectrum.partials) or 1.0

        for partial in spectrum.partials:
            norm_amp = partial.amplitude / total_amp * amplitude
            for i in range(n):
                t = i / self.sample_rate
                samples[i] += norm_amp * math.sin(
                    2 * math.pi * partial.frequency * t + partial.phase
                )

        return samples

    def render_with_decay(self, spectrum: HarmonicSpectrum,
                          duration_s: float = 2.0,
                          decay_rate: float = 3.0) -> list[float]:
        """Render with per-partial exponential decay."""
        n = int(duration_s * self.sample_rate)
        samples = [0.0] * n

        total_amp = sum(p.amplitude for p in spectrum.partials) or 1.0

        for partial in spectrum.partials:
            norm_amp = partial.amplitude / total_amp * 0.8
            # Higher harmonics decay faster
            partial_decay = decay_rate * partial.harmonic_number

            for i in range(n):
                t = i / self.sample_rate
                env = math.exp(-partial_decay * t)
                samples[i] += norm_amp * env * math.sin(
                    2 * math.pi * partial.frequency * t + partial.phase
                )

        return samples

    @staticmethod
    def _write_wav(path: str, samples: list[float],
                   sr: int = SAMPLE_RATE) -> None:
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            data = b""
            for s in samples:
                c = max(-1.0, min(1.0, s))
                data += struct.pack("<h", int(c * 32767))
            wf.writeframes(data)


def main() -> None:
    print("Harmonic Generator")
    gen = HarmonicGenerator()

    fund = A4_432  # 432 Hz

    spectra = {
        "harmonic": gen.harmonic_series(fund, 16),
        "odd": gen.odd_harmonics(fund, 8),
        "even": gen.even_harmonics(fund, 8),
        "sub": gen.sub_harmonics(fund, 4),
        "phi": gen.phi_harmonics(fund, 8),
        "inharmonic": gen.inharmonic_spectrum(fund, stretch=2.0),
        "bell": gen.bell_spectrum(fund),
    }

    for name, spec in spectra.items():
        d = spec.to_dict()
        print(f"  {name}: {d['partial_count']} partials, "
              f"fundamental={d['fundamental']}Hz")

    # Quick render test
    audio = gen.render(spectra["phi"], duration_s=0.5)
    print(f"\n  PHI render: {len(audio)} samples, "
          f"peak={max(abs(s) for s in audio):.3f}")

    bell = gen.render_with_decay(spectra["bell"], duration_s=2.0)
    print(f"  Bell render: {len(bell)} samples")

    print("Done.")


if __name__ == "__main__":
    main()
