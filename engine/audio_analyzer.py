"""
DUBFORGE — Audio Analyzer Dashboard  (Session 198)

Comprehensive audio analysis: waveform stats, spectral
analysis, loudness metering (LUFS-style), crest factor,
dynamic range, frequency distribution.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI
from engine.turboquant import SpectralVectorIndex, TurboQuantConfig

SAMPLE_RATE = 48000


@dataclass
class WaveformStats:
    """Basic waveform statistics."""
    peak: float = 0.0
    peak_db: float = -96.0
    rms: float = 0.0
    rms_db: float = -96.0
    crest_factor: float = 0.0
    dc_offset: float = 0.0
    zero_crossings: int = 0
    duration: float = 0.0
    sample_count: int = 0

    def to_dict(self) -> dict:
        return {
            "peak": round(self.peak, 4),
            "peak_db": round(self.peak_db, 1),
            "rms": round(self.rms, 4),
            "rms_db": round(self.rms_db, 1),
            "crest_factor": round(self.crest_factor, 2),
            "dc_offset": round(self.dc_offset, 6),
            "zero_crossings": self.zero_crossings,
            "duration": round(self.duration, 3),
        }


@dataclass
class SpectralProfile:
    """Frequency distribution analysis."""
    sub_energy: float = 0.0      # 20-60 Hz
    bass_energy: float = 0.0     # 60-250 Hz
    low_mid_energy: float = 0.0  # 250-500 Hz
    mid_energy: float = 0.0      # 500-2000 Hz
    high_mid_energy: float = 0.0  # 2000-6000 Hz
    high_energy: float = 0.0     # 6000-20000 Hz
    dominant_freq: float = 0.0
    spectral_centroid: float = 0.0

    def to_vector(self) -> list[float]:
        """Return spectral profile as a float vector for TQ indexing."""
        return [
            self.sub_energy, self.bass_energy, self.low_mid_energy,
            self.mid_energy, self.high_mid_energy, self.high_energy,
            self.dominant_freq, self.spectral_centroid,
        ]

    def to_dict(self) -> dict:
        return {
            "sub": round(self.sub_energy, 4),
            "bass": round(self.bass_energy, 4),
            "low_mid": round(self.low_mid_energy, 4),
            "mid": round(self.mid_energy, 4),
            "high_mid": round(self.high_mid_energy, 4),
            "high": round(self.high_energy, 4),
            "dominant_freq": round(self.dominant_freq, 1),
            "centroid": round(self.spectral_centroid, 1),
        }


@dataclass
class LoudnessMetering:
    """Loudness measurements."""
    integrated: float = -24.0  # LUFS-like
    short_term: float = -24.0
    momentary_peak: float = -24.0
    true_peak: float = 0.0
    loudness_range: float = 0.0

    def to_dict(self) -> dict:
        return {
            "integrated_lufs": round(self.integrated, 1),
            "short_term_lufs": round(self.short_term, 1),
            "momentary_peak_lufs": round(self.momentary_peak, 1),
            "true_peak_dbfs": round(self.true_peak, 1),
            "loudness_range": round(self.loudness_range, 1),
        }


@dataclass
class AnalysisReport:
    """Complete analysis report."""
    filepath: str = ""
    waveform: WaveformStats = None
    spectral: SpectralProfile = None
    loudness: LoudnessMetering = None
    phi_alignment: float = 0.0

    def __post_init__(self):
        if self.waveform is None:
            self.waveform = WaveformStats()
        if self.spectral is None:
            self.spectral = SpectralProfile()
        if self.loudness is None:
            self.loudness = LoudnessMetering()

    def to_dict(self) -> dict:
        return {
            "file": self.filepath,
            "waveform": self.waveform.to_dict(),
            "spectral": self.spectral.to_dict(),
            "loudness": self.loudness.to_dict(),
            "phi_alignment": round(self.phi_alignment, 4),
        }


class AudioAnalyzer:
    """Comprehensive audio analysis engine."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def read_wav(self, path: str) -> list[float]:
        """Read WAV as float samples."""
        with wave.open(path, "r") as wf:
            sw = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        if sw == 2:
            vals = struct.unpack(f"<{len(raw) // 2}h", raw)
            return [v / 32768.0 for v in vals]
        elif sw == 1:
            vals = struct.unpack(f"<{len(raw)}B", raw)
            return [(v - 128) / 128.0 for v in vals]
        return []

    def analyze_waveform(self, samples: list[float]) -> WaveformStats:
        """Compute waveform statistics."""
        if not samples:
            return WaveformStats()

        n = len(samples)
        peak = max(abs(s) for s in samples)
        peak_db = 20 * math.log10(peak) if peak > 0 else -96.0

        rms = math.sqrt(sum(s * s for s in samples) / n)
        rms_db = 20 * math.log10(rms) if rms > 0 else -96.0

        crest = peak / rms if rms > 0 else 0.0
        dc = sum(samples) / n

        zc = sum(1 for i in range(1, n)
                 if samples[i - 1] * samples[i] < 0)

        return WaveformStats(
            peak=peak, peak_db=peak_db,
            rms=rms, rms_db=rms_db,
            crest_factor=crest,
            dc_offset=dc,
            zero_crossings=zc,
            duration=n / self.sample_rate,
            sample_count=n,
        )

    def analyze_spectrum(self, samples: list[float],
                         fft_size: int = 2048) -> SpectralProfile:
        """Analyze frequency distribution via DFT."""
        if len(samples) < fft_size:
            padded = samples + [0.0] * (fft_size - len(samples))
        else:
            padded = samples[:fft_size]

        # Hann window
        windowed = [
            padded[i] * 0.5 * (1 - math.cos(2 * math.pi * i / fft_size))
            for i in range(fft_size)
        ]

        # DFT (real magnitudes only)
        half = fft_size // 2
        magnitudes: list[float] = []
        for k in range(half):
            re = sum(windowed[n] * math.cos(2 * math.pi * k * n / fft_size)
                     for n in range(fft_size))
            im = sum(windowed[n] * math.sin(2 * math.pi * k * n / fft_size)
                     for n in range(fft_size))
            magnitudes.append(math.sqrt(re * re + im * im) / fft_size)

        freq_per_bin = self.sample_rate / fft_size

        # Band energies
        bands = {
            "sub": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "high_mid": (2000, 6000),
            "high": (6000, min(20000, self.sample_rate // 2)),
        }

        energies: dict[str, float] = {}
        for band_name, (lo, hi) in bands.items():
            lo_bin = int(lo / freq_per_bin)
            hi_bin = min(int(hi / freq_per_bin), half - 1)
            energy = sum(m * m for m in magnitudes[lo_bin:hi_bin + 1])
            energies[band_name] = math.sqrt(energy) if energy > 0 else 0.0

        # Dominant frequency
        max_mag = max(magnitudes[1:]) if len(magnitudes) > 1 else 0
        dom_bin = magnitudes.index(max_mag) if max_mag > 0 else 0
        dom_freq = dom_bin * freq_per_bin

        # Spectral centroid
        total_mag = sum(magnitudes)
        if total_mag > 0:
            centroid = sum(i * freq_per_bin * magnitudes[i]
                           for i in range(half)) / total_mag
        else:
            centroid = 0.0

        return SpectralProfile(
            sub_energy=energies.get("sub", 0),
            bass_energy=energies.get("bass", 0),
            low_mid_energy=energies.get("low_mid", 0),
            mid_energy=energies.get("mid", 0),
            high_mid_energy=energies.get("high_mid", 0),
            high_energy=energies.get("high", 0),
            dominant_freq=dom_freq,
            spectral_centroid=centroid,
        )

    def measure_loudness(self, samples: list[float]) -> LoudnessMetering:
        """Measure loudness (simplified LUFS-like)."""
        if not samples:
            return LoudnessMetering()

        n = len(samples)

        # Integrated (full signal RMS → dB)
        rms = math.sqrt(sum(s * s for s in samples) / n)
        integrated = 20 * math.log10(rms) if rms > 0 else -96.0

        # Short-term (3 second windows)
        window = int(3 * self.sample_rate)
        short_term_vals: list[float] = []
        for i in range(0, n, window):
            chunk = samples[i:i + window]
            if chunk:
                r = math.sqrt(sum(s * s for s in chunk) / len(chunk))
                if r > 0:
                    short_term_vals.append(20 * math.log10(r))

        short_term = max(short_term_vals) if short_term_vals else -96.0

        # Momentary (400ms windows)
        moment_window = int(0.4 * self.sample_rate)
        moment_vals: list[float] = []
        for i in range(0, n, moment_window):
            chunk = samples[i:i + moment_window]
            if chunk:
                r = math.sqrt(sum(s * s for s in chunk) / len(chunk))
                if r > 0:
                    moment_vals.append(20 * math.log10(r))

        momentary = max(moment_vals) if moment_vals else -96.0

        # True peak
        peak = max(abs(s) for s in samples)
        true_peak = 20 * math.log10(peak) if peak > 0 else -96.0

        # Loudness range
        if short_term_vals:
            lr = max(short_term_vals) - min(short_term_vals)
        else:
            lr = 0.0

        return LoudnessMetering(
            integrated=integrated,
            short_term=short_term,
            momentary_peak=momentary,
            true_peak=true_peak,
            loudness_range=lr,
        )

    def measure_phi_alignment(self, samples: list[float]) -> float:
        """Measure how PHI-aligned the audio is."""
        if not samples:
            return 0.0

        stats = self.analyze_waveform(samples)
        spectrum = self.analyze_spectrum(samples)

        score = 0.0
        checks = 0

        # Check if dominant frequency relates to PHI
        if spectrum.dominant_freq > 0:
            ratio = spectrum.dominant_freq / (432.0 / 4)
            # How close to a PHI power?
            if ratio > 0:
                log_phi = math.log(ratio) / math.log(PHI)
                phi_err = abs(log_phi - round(log_phi))
                score += max(0, 1 - phi_err * 2)
            checks += 1

        # Check crest factor against PHI
        if stats.crest_factor > 0:
            cf_ratio = stats.crest_factor / PHI
            score += max(0, 1 - abs(cf_ratio - round(cf_ratio)))
            checks += 1

        # Check spectral centroid
        if spectrum.spectral_centroid > 0:
            cent_ratio = spectrum.spectral_centroid / 432.0
            log_r = math.log(max(0.01, cent_ratio)) / math.log(PHI)
            score += max(0, 1 - abs(log_r - round(log_r)) * 2)
            checks += 1

        return score / checks if checks > 0 else 0.0

    def analyze(self, samples: list[float],
                filepath: str = "") -> AnalysisReport:
        """Full analysis."""
        report = AnalysisReport(
            filepath=filepath,
            waveform=self.analyze_waveform(samples),
            spectral=self.analyze_spectrum(samples),
            loudness=self.measure_loudness(samples),
            phi_alignment=self.measure_phi_alignment(samples),
        )
        return report

    def analyze_file(self, path: str) -> AnalysisReport | None:
        """Analyze a WAV file."""
        if not os.path.exists(path):
            return None
        samples = self.read_wav(path)
        return self.analyze(samples, filepath=path)

    def compare(self, samples_a: list[float],
                samples_b: list[float]) -> dict:
        """Compare two audio signals."""
        report_a = self.analyze(samples_a, "A")
        report_b = self.analyze(samples_b, "B")

        return {
            "peak_diff_db": round(
                report_a.waveform.peak_db - report_b.waveform.peak_db, 1
            ),
            "rms_diff_db": round(
                report_a.waveform.rms_db - report_b.waveform.rms_db, 1
            ),
            "centroid_diff": round(
                report_a.spectral.spectral_centroid -
                report_b.spectral.spectral_centroid, 1
            ),
            "loudness_diff": round(
                report_a.loudness.integrated -
                report_b.loudness.integrated, 1
            ),
            "phi_a": round(report_a.phi_alignment, 3),
            "phi_b": round(report_b.phi_alignment, 3),
        }


def main() -> None:
    print("Audio Analyzer Dashboard")

    analyzer = AudioAnalyzer()

    # Generate test signal: 432 Hz sine
    n = SAMPLE_RATE * 2
    samples = [0.8 * math.sin(2 * math.pi * 432 * i / SAMPLE_RATE)
               for i in range(n)]

    report = analyzer.analyze(samples, "test_432hz.wav")

    print(f"\n  Waveform: {report.waveform.to_dict()}")
    print(f"  Spectral: {report.spectral.to_dict()}")
    print(f"  Loudness: {report.loudness.to_dict()}")
    print(f"  PHI alignment: {report.phi_alignment:.3f}")
    print("Done.")


if __name__ == "__main__":
    main()
