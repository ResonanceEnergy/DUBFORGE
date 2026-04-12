"""
DUBFORGE — Frequency Analyzer  (Session 212)

DFT-based frequency analysis with band energy,
spectral centroid, bandwidth, rolloff, flatness.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
from engine.turboquant import SpectralVectorIndex, TurboQuantConfig

SAMPLE_RATE = 44100

FREQUENCY_BANDS = {
    "sub": (20, 60),
    "bass": (60, 250),
    "low_mid": (250, 500),
    "mid": (500, 2000),
    "high_mid": (2000, 6000),
    "high": (6000, 20000),
}


@dataclass
class SpectralFeatures:
    """Computed spectral features."""
    centroid: float
    bandwidth: float
    rolloff: float
    flatness: float
    peak_freq: float
    band_energy: dict[str, float]
    dominant_band: str

    def to_dict(self) -> dict:
        return {
            "centroid_hz": round(self.centroid, 2),
            "bandwidth_hz": round(self.bandwidth, 2),
            "rolloff_hz": round(self.rolloff, 2),
            "flatness": round(self.flatness, 4),
            "peak_freq_hz": round(self.peak_freq, 2),
            "band_energy": {k: round(v, 4) for k, v in self.band_energy.items()},
            "dominant_band": self.dominant_band,
        }

    def to_feature_vector(self) -> list[float]:
        """Extract a normalized feature vector for TurboQuant indexing.

        Returns a 10-dimensional vector:
            [centroid, bandwidth, rolloff, flatness,
             sub, bass, low_mid, mid, high_mid, high]
        """
        bands = [
            self.band_energy.get("sub", 0.0),
            self.band_energy.get("bass", 0.0),
            self.band_energy.get("low_mid", 0.0),
            self.band_energy.get("mid", 0.0),
            self.band_energy.get("high_mid", 0.0),
            self.band_energy.get("high", 0.0),
        ]
        vec = [
            self.centroid / 20000.0,      # normalize to ~[0,1]
            self.bandwidth / 20000.0,
            self.rolloff / 20000.0,
            self.flatness,
        ] + bands
        return vec


class FrequencyAnalyzer:
    """Analyze frequency content of audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE,
                 fft_size: int = 4096):
        self.sample_rate = sample_rate
        self.fft_size = fft_size

    def compute_spectrum(self, samples: list[float]) -> list[float]:
        """Compute magnitude spectrum via DFT."""
        n = min(len(samples), self.fft_size)
        magnitudes: list[float] = []

        # Apply Hanning window
        windowed = [
            samples[i] * 0.5 * (1 - math.cos(2 * math.pi * i / (n - 1)))
            for i in range(n)
        ]

        # DFT (only positive frequencies)
        for k in range(n // 2):
            real = 0.0
            imag = 0.0
            for j in range(n):
                angle = 2 * math.pi * k * j / n
                real += windowed[j] * math.cos(angle)
                imag -= windowed[j] * math.sin(angle)
            mag = math.sqrt(real * real + imag * imag) / n
            magnitudes.append(mag)

        return magnitudes

    def bin_to_freq(self, bin_idx: int) -> float:
        """Convert FFT bin index to frequency."""
        return bin_idx * self.sample_rate / self.fft_size

    def freq_to_bin(self, freq: float) -> int:
        """Convert frequency to FFT bin index."""
        return int(freq * self.fft_size / self.sample_rate)

    def get_band_energy(self, spectrum: list[float]) -> dict[str, float]:
        """Get energy in each frequency band."""
        band_energy: dict[str, float] = {}
        total = sum(m * m for m in spectrum) or 1.0

        for name, (low, high) in FREQUENCY_BANDS.items():
            lo_bin = self.freq_to_bin(low)
            hi_bin = min(self.freq_to_bin(high), len(spectrum) - 1)
            energy = sum(
                spectrum[i] * spectrum[i]
                for i in range(lo_bin, hi_bin + 1)
            )
            band_energy[name] = energy / total

        return band_energy

    def spectral_centroid(self, spectrum: list[float]) -> float:
        """Compute spectral centroid (center of mass)."""
        num = sum(self.bin_to_freq(i) * spectrum[i]
                  for i in range(len(spectrum)))
        den = sum(spectrum) or 1.0
        return num / den

    def spectral_bandwidth(self, spectrum: list[float],
                           centroid: float) -> float:
        """Compute spectral bandwidth around centroid."""
        num = sum(
            spectrum[i] * (self.bin_to_freq(i) - centroid) ** 2
            for i in range(len(spectrum))
        )
        den = sum(spectrum) or 1.0
        return math.sqrt(num / den)

    def spectral_rolloff(self, spectrum: list[float],
                         percentile: float = 0.85) -> float:
        """Find frequency below which percentile% of energy."""
        total = sum(m * m for m in spectrum) or 1.0
        target = total * percentile
        cumulative = 0.0

        for i in range(len(spectrum)):
            cumulative += spectrum[i] * spectrum[i]
            if cumulative >= target:
                return self.bin_to_freq(i)

        return self.bin_to_freq(len(spectrum) - 1)

    def spectral_flatness(self, spectrum: list[float]) -> float:
        """Compute spectral flatness (tonality measure)."""
        # Geometric mean / arithmetic mean
        n = len(spectrum)
        if n == 0:
            return 0.0

        # Filter out zeros
        positive = [m for m in spectrum if m > 0]
        if not positive:
            return 0.0

        log_sum = sum(math.log(m) for m in positive)
        geo_mean = math.exp(log_sum / len(positive))
        arith_mean = sum(positive) / len(positive)

        return geo_mean / arith_mean if arith_mean > 0 else 0.0

    def peak_frequency(self, spectrum: list[float]) -> float:
        """Find frequency of highest spectral peak."""
        if not spectrum:
            return 0.0
        max_idx = max(range(len(spectrum)), key=lambda i: spectrum[i])
        return self.bin_to_freq(max_idx)

    def analyze(self, samples: list[float]) -> SpectralFeatures:
        """Full spectral analysis."""
        if not samples:
            return SpectralFeatures(
                centroid=0, bandwidth=0, rolloff=0, flatness=0,
                peak_freq=0, band_energy={}, dominant_band="",
            )

        spectrum = self.compute_spectrum(samples)
        centroid = self.spectral_centroid(spectrum)
        bandwidth = self.spectral_bandwidth(spectrum, centroid)
        rolloff = self.spectral_rolloff(spectrum)
        flatness = self.spectral_flatness(spectrum)
        peak = self.peak_frequency(spectrum)
        bands = self.get_band_energy(spectrum)

        dominant = max(bands, key=lambda k: bands.get(k, 0.0)) if bands else ""

        return SpectralFeatures(
            centroid=centroid,
            bandwidth=bandwidth,
            rolloff=rolloff,
            flatness=flatness,
            peak_freq=peak,
            band_energy=bands,
            dominant_band=dominant,
        )

    def compare(self, samples_a: list[float],
                samples_b: list[float]) -> dict:
        """Compare spectral characteristics of two signals."""
        a = self.analyze(samples_a)
        b = self.analyze(samples_b)

        return {
            "centroid_diff_hz": round(b.centroid - a.centroid, 2),
            "bandwidth_diff_hz": round(b.bandwidth - a.bandwidth, 2),
            "rolloff_diff_hz": round(b.rolloff - a.rolloff, 2),
            "flatness_diff": round(b.flatness - a.flatness, 4),
            "a": a.to_dict(),
            "b": b.to_dict(),
        }

    def build_spectral_index(
        self,
        named_samples: dict[str, list[float]],
        config: TurboQuantConfig | None = None,
    ) -> SpectralVectorIndex:
        """Build a TurboQuant spectral search index from named audio buffers.

        Args:
            named_samples: Mapping of name → audio samples.
            config: TurboQuant config (default: 4-bit with QJL).

        Returns:
            SpectralVectorIndex ready for similarity search.
        """
        idx = SpectralVectorIndex(config)
        for name, samples in named_samples.items():
            features = self.analyze(samples)
            vec = features.to_feature_vector()
            idx.add(name, vec, metadata=features.to_dict())
        return idx

    def find_similar(self, query_samples: list[float],
                     index: SpectralVectorIndex,
                     top_k: int = 5) -> list[tuple[str, float, dict]]:
        """Find sounds most similar to query using a spectral index.

        Args:
            query_samples: Audio samples to match against.
            index: Pre-built SpectralVectorIndex.
            top_k: Number of results.

        Returns:
            List of (name, similarity, metadata) tuples.
        """
        features = self.analyze(query_samples)
        vec = features.to_feature_vector()
        return index.search(vec, top_k=top_k)

    def phi_bands(self, spectrum: list[float],
                  base_freq: float = 40.0,
                  count: int = 8) -> dict[str, float]:
        """Compute energy in PHI-spaced frequency bands."""
        result: dict[str, float] = {}
        total = sum(m * m for m in spectrum) or 1.0

        freq = base_freq
        for i in range(count):
            next_freq = freq * PHI
            lo = self.freq_to_bin(freq)
            hi = min(self.freq_to_bin(next_freq), len(spectrum) - 1)

            energy = sum(
                spectrum[j] * spectrum[j]
                for j in range(lo, hi + 1)
            )
            result[f"phi_{i}_{freq:.0f}_{next_freq:.0f}"] = energy / total
            freq = next_freq

        return result


def main() -> None:
    print("Frequency Analyzer")
    analyzer = FrequencyAnalyzer()

    # Generate test signal: multi-frequency
    n = SAMPLE_RATE
    samples: list[float] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        s = (0.5 * math.sin(2 * math.pi * 100 * t) +
             0.3 * math.sin(2 * math.pi * 440 * t) +
             0.2 * math.sin(2 * math.pi * 2000 * t))
        samples.append(s)

    features = analyzer.analyze(samples)
    d = features.to_dict()
    print(f"  Centroid: {d['centroid_hz']} Hz")
    print(f"  Peak: {d['peak_freq_hz']} Hz")
    print(f"  Rolloff: {d['rolloff_hz']} Hz")
    print(f"  Flatness: {d['flatness']}")
    print(f"  Dominant: {d['dominant_band']}")
    for band, energy in d['band_energy'].items():
        print(f"    {band}: {energy}")

    print("Done.")


if __name__ == "__main__":
    main()
