"""
DUBFORGE — Intelligent EQ Engine  (Session 178)

Auto-EQ with frequency analysis, surgical notch detection,
and PHI-banded equalization for dubstep mixing.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100

# Dubstep-tuned frequency bands
EQ_BANDS: list[dict] = [
    {"name": "sub", "low": 20, "high": 60, "target_db": -3},
    {"name": "bass", "low": 60, "high": 200, "target_db": 0},
    {"name": "low_mid", "low": 200, "high": 800, "target_db": -2},
    {"name": "mid", "low": 800, "high": 2500, "target_db": -1},
    {"name": "high_mid", "low": 2500, "high": 6000, "target_db": 0},
    {"name": "presence", "low": 6000, "high": 12000, "target_db": -1},
    {"name": "air", "low": 12000, "high": 20000, "target_db": -3},
]


@dataclass
class BandAnalysis:
    """Analysis of a single EQ band."""
    name: str
    low_hz: float
    high_hz: float
    energy_db: float
    target_db: float = 0.0

    @property
    def correction_db(self) -> float:
        return self.target_db - self.energy_db

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "range_hz": f"{self.low_hz}-{self.high_hz}",
            "energy_db": round(self.energy_db, 1),
            "target_db": round(self.target_db, 1),
            "correction_db": round(self.correction_db, 1),
        }


@dataclass
class ResonancePeak:
    """A detected resonance peak."""
    freq_hz: float
    magnitude_db: float
    q: float = 4.0

    def to_dict(self) -> dict:
        return {
            "freq_hz": round(self.freq_hz, 1),
            "magnitude_db": round(self.magnitude_db, 1),
            "q": round(self.q, 1),
        }


@dataclass
class EQProfile:
    """Complete EQ analysis."""
    bands: list[BandAnalysis] = field(default_factory=list)
    resonances: list[ResonancePeak] = field(default_factory=list)
    overall_db: float = 0.0
    crest_factor: float = 0.0
    balance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "bands": [b.to_dict() for b in self.bands],
            "resonances": [r.to_dict() for r in self.resonances],
            "overall_db": round(self.overall_db, 1),
            "crest_factor": round(self.crest_factor, 1),
            "balance_score": round(self.balance_score, 2),
        }


def _dft_band_energy(signal: list[float], low_hz: float, high_hz: float,
                      sample_rate: int = SAMPLE_RATE) -> float:
    """Compute energy in a frequency band using DFT."""
    n = min(len(signal), 4096)
    if n == 0:
        return -100.0

    # Window
    windowed = [
        signal[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / n))
        for i in range(n)
    ]

    # DFT for band
    freq_res = sample_rate / n
    low_bin = max(1, int(low_hz / freq_res))
    high_bin = min(n // 2, int(high_hz / freq_res))

    energy = 0.0
    for k in range(low_bin, high_bin + 1):
        re = sum(windowed[i] * math.cos(2 * math.pi * k * i / n)
                 for i in range(n))
        im = sum(windowed[i] * math.sin(2 * math.pi * k * i / n)
                 for i in range(n))
        energy += re * re + im * im

    if energy <= 0:
        return -100.0

    return 10 * math.log10(energy / n)


def analyze_spectrum(signal: list[float],
                      sample_rate: int = SAMPLE_RATE) -> EQProfile:
    """Analyze signal spectrum across EQ bands."""
    bands: list[BandAnalysis] = []

    for band in EQ_BANDS:
        energy = _dft_band_energy(signal, band["low"], band["high"], sample_rate)
        bands.append(BandAnalysis(
            name=band["name"],
            low_hz=band["low"],
            high_hz=band["high"],
            energy_db=energy,
            target_db=band["target_db"],
        ))

    # Overall level
    rms = math.sqrt(sum(x * x for x in signal) / max(len(signal), 1))
    overall_db = 20 * math.log10(max(rms, 1e-10))

    # Crest factor
    peak = max(abs(x) for x in signal) if signal else 0.0
    crest = 20 * math.log10(max(peak, 1e-10) / max(rms, 1e-10)) if rms > 0 else 0.0

    # Balance score: how close to target
    if bands:
        diffs = [abs(b.correction_db) for b in bands]
        avg_diff = sum(diffs) / len(diffs)
        balance = max(0.0, 1.0 - avg_diff / 12.0)
    else:
        balance = 0.0

    return EQProfile(
        bands=bands,
        overall_db=overall_db,
        crest_factor=crest,
        balance_score=balance,
    )


def detect_resonances(signal: list[float],
                       threshold_db: float = 6.0,
                       sample_rate: int = SAMPLE_RATE) -> list[ResonancePeak]:
    """Detect spectral resonance peaks."""
    n = min(len(signal), 4096)
    if n < 64:
        return []

    windowed = [
        signal[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / n))
        for i in range(n)
    ]

    freq_res = sample_rate / n
    magnitudes: list[float] = []

    for k in range(1, n // 2):
        re = sum(windowed[i] * math.cos(2 * math.pi * k * i / n)
                 for i in range(n))
        im = sum(windowed[i] * math.sin(2 * math.pi * k * i / n)
                 for i in range(n))
        mag = math.sqrt(re * re + im * im) / n
        magnitudes.append(mag)

    if not magnitudes:
        return []

    # Find peaks
    peaks: list[ResonancePeak] = []
    avg_mag = sum(magnitudes) / len(magnitudes)

    for i in range(1, len(magnitudes) - 1):
        if (magnitudes[i] > magnitudes[i - 1] and
                magnitudes[i] > magnitudes[i + 1]):
            db_above = 20 * math.log10(
                max(magnitudes[i], 1e-10) / max(avg_mag, 1e-10)
            )
            if db_above > threshold_db:
                freq = (i + 1) * freq_res
                if 40 <= freq <= 16000:
                    # Estimate Q from peak width
                    width = 1
                    for j in range(i + 1, min(i + 20, len(magnitudes))):
                        if magnitudes[j] < magnitudes[i] * 0.707:
                            break
                        width += 1
                    q = max(0.5, freq / (width * freq_res))
                    peaks.append(ResonancePeak(freq, db_above, min(q, 20)))

    peaks.sort(key=lambda p: p.magnitude_db, reverse=True)
    return peaks[:8]


def apply_eq_band(signal: list[float], center_hz: float,
                   gain_db: float, q: float = 1.0,
                   sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply a single parametric EQ band (biquad peaking)."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * center_hz / sample_rate
    alpha = math.sin(w0) / (2 * q)

    b0 = 1 + alpha * A
    b1 = -2 * math.cos(w0)
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * math.cos(w0)
    a2 = 1 - alpha / A

    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0

    x1 = x2 = y1 = y2 = 0.0
    result: list[float] = []

    for x in signal:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2 = x1
        x1 = x
        y2 = y1
        y1 = y
        result.append(y)

    return result


def auto_eq(signal: list[float],
             sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Automatically EQ signal to match target curve."""
    profile = analyze_spectrum(signal, sample_rate)
    result = list(signal)

    for band in profile.bands:
        correction = band.correction_db
        # Limit correction to ±6 dB
        correction = max(-6.0, min(6.0, correction))
        if abs(correction) > 0.5:
            center = math.sqrt(band.low_hz * band.high_hz)
            q = center / (band.high_hz - band.low_hz) * PHI
            result = apply_eq_band(result, center, correction, q, sample_rate)

    return result


def eq_text(profile: EQProfile) -> str:
    """Format EQ analysis as text."""
    lines = ["EQ Analysis:"]
    lines.append(f"  Overall: {profile.overall_db:.1f} dB, "
                 f"Crest: {profile.crest_factor:.1f} dB, "
                 f"Balance: {profile.balance_score:.0%}")

    for band in profile.bands:
        bar = "█" * max(0, int((band.energy_db + 60) / 3))
        correction = f" ({band.correction_db:+.1f})" if abs(band.correction_db) > 1 else ""
        lines.append(f"  {band.name:>10}: {bar} {band.energy_db:.1f} dB{correction}")

    if profile.resonances:
        lines.append("  Resonances:")
        for r in profile.resonances[:4]:
            lines.append(f"    {r.freq_hz:.0f} Hz: +{r.magnitude_db:.1f} dB (Q={r.q:.1f})")

    return "\n".join(lines)


def main() -> None:
    print("Intelligent EQ Engine")

    # Test signal: bass + mid + some resonance
    signal = [
        (math.sin(2 * math.pi * 60 * i / SAMPLE_RATE) * 0.5 +
         math.sin(2 * math.pi * 1000 * i / SAMPLE_RATE) * 0.2 +
         math.sin(2 * math.pi * 3500 * i / SAMPLE_RATE) * 0.3)
        for i in range(SAMPLE_RATE * 2)
    ]

    profile = analyze_spectrum(signal)
    print(eq_text(profile))

    resonances = detect_resonances(signal)
    print(f"\n  Resonances found: {len(resonances)}")

    # Auto-EQ
    eqd = auto_eq(signal)
    profile2 = analyze_spectrum(eqd)
    print(f"\n  After auto-EQ balance: {profile2.balance_score:.0%}")
    print("Done.")


if __name__ == "__main__":
    main()
