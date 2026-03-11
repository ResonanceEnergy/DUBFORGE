"""
DUBFORGE — Style Transfer Engine  (Session 187)

Transfers spectral characteristics from a reference signal
onto a target signal, preserving target's temporal structure.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class SpectralProfile:
    """Spectral envelope profile."""
    band_energies: list[float]
    band_centers: list[float]
    spectral_tilt: float = 0.0
    brightness: float = 0.0

    def to_dict(self) -> dict:
        return {
            "n_bands": len(self.band_energies),
            "tilt": round(self.spectral_tilt, 3),
            "brightness": round(self.brightness, 3),
        }


@dataclass
class TransferResult:
    """Result of style transfer."""
    signal: list[float]
    transfer_amount: float
    source_profile: SpectralProfile
    target_profile: SpectralProfile

    def to_dict(self) -> dict:
        return {
            "samples": len(self.signal),
            "transfer_amount": round(self.transfer_amount, 2),
            "source": self.source_profile.to_dict(),
            "target": self.target_profile.to_dict(),
        }


def _compute_profile(signal: list[float], n_bands: int = 16,
                      sample_rate: int = SAMPLE_RATE) -> SpectralProfile:
    """Compute spectral profile of a signal."""
    n = min(len(signal), 4096)
    if n < 64:
        return SpectralProfile([], [], 0.0, 0.0)

    # Window
    windowed = [
        signal[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / n))
        for i in range(n)
    ]

    freq_res = sample_rate / n
    energies: list[float] = []
    centers: list[float] = []

    bins_per_band = max(1, (n // 2) // n_bands)

    for b in range(n_bands):
        start_k = b * bins_per_band + 1
        end_k = min(start_k + bins_per_band, n // 2)
        center_freq = ((start_k + end_k) / 2) * freq_res
        centers.append(center_freq)

        energy = 0.0
        for k in range(start_k, end_k):
            re = sum(windowed[i] * math.cos(2 * math.pi * k * i / n)
                     for i in range(n))
            im = sum(windowed[i] * math.sin(2 * math.pi * k * i / n)
                     for i in range(n))
            energy += re * re + im * im
        energies.append(energy / max(bins_per_band, 1))

    # Spectral tilt (high/low ratio)
    low_e = sum(energies[:n_bands // 2]) if energies else 1
    high_e = sum(energies[n_bands // 2:]) if energies else 1
    tilt = math.log10(max(high_e, 1e-10) / max(low_e, 1e-10))

    # Brightness
    total = sum(energies) if energies else 1
    weighted = sum(c * e for c, e in zip(centers, energies))
    brightness = weighted / max(total, 1e-10) / (sample_rate / 2)

    return SpectralProfile(energies, centers, tilt, brightness)


def _biquad_peak(signal: list[float], center: float,
                  gain_db: float, q: float = 1.0,
                  sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply peaking EQ band."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * min(center, sample_rate * 0.49) / sample_rate
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


def transfer_style(source: list[float], target: list[float],
                    amount: float = 0.7,
                    n_bands: int = 12,
                    sample_rate: int = SAMPLE_RATE) -> TransferResult:
    """Transfer spectral style from source to target."""
    src_profile = _compute_profile(source, n_bands, sample_rate)
    tgt_profile = _compute_profile(target, n_bands, sample_rate)

    if not src_profile.band_energies or not tgt_profile.band_energies:
        return TransferResult(list(target), amount, src_profile, tgt_profile)

    result = list(target)
    n = min(len(src_profile.band_energies), len(tgt_profile.band_energies))

    for i in range(n):
        src_e = max(src_profile.band_energies[i], 1e-20)
        tgt_e = max(tgt_profile.band_energies[i], 1e-20)

        # Gain difference in dB
        diff_db = 10 * math.log10(src_e / tgt_e)
        # Apply only a fraction
        apply_db = diff_db * amount
        # Limit
        apply_db = max(-12.0, min(12.0, apply_db))

        if abs(apply_db) > 0.5 and i < len(src_profile.band_centers):
            center = src_profile.band_centers[i]
            if 30 < center < sample_rate * 0.45:
                q = PHI  # Golden Q
                result = _biquad_peak(result, center, apply_db, q, sample_rate)

    return TransferResult(result, amount, src_profile, tgt_profile)


def match_brightness(source: list[float], target: list[float],
                      sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Match brightness of target to source."""
    src_p = _compute_profile(source, 8, sample_rate)
    tgt_p = _compute_profile(target, 8, sample_rate)

    diff = src_p.brightness - tgt_p.brightness
    # Apply shelf filter to match
    if abs(diff) < 0.01:
        return list(target)

    gain_db = diff * 12.0  # Scale to dB
    gain_db = max(-8.0, min(8.0, gain_db))

    # High shelf approximation
    return _biquad_peak(target, 4000.0, gain_db, 0.5, sample_rate)


def transfer_text(result: TransferResult) -> str:
    """Format transfer result as text."""
    lines = ["Style Transfer Result:"]
    lines.append(f"  Transfer amount: {result.transfer_amount:.0%}")
    lines.append(f"  Source tilt: {result.source_profile.spectral_tilt:.3f}")
    lines.append(f"  Target tilt: {result.target_profile.spectral_tilt:.3f}")
    lines.append(f"  Source brightness: {result.source_profile.brightness:.3f}")
    lines.append(f"  Target brightness: {result.target_profile.brightness:.3f}")
    lines.append(f"  Output samples: {len(result.signal)}")
    return "\n".join(lines)


def main() -> None:
    print("Style Transfer Engine")

    n = 4096
    # Source: bright, harsh
    source = [
        math.sin(2 * math.pi * 200 * i / SAMPLE_RATE) * 0.3 +
        math.sin(2 * math.pi * 2000 * i / SAMPLE_RATE) * 0.3 +
        math.sin(2 * math.pi * 8000 * i / SAMPLE_RATE) * 0.2
        for i in range(n)
    ]

    # Target: dark, muffled
    target = [
        math.sin(2 * math.pi * 60 * i / SAMPLE_RATE) * 0.5 +
        math.sin(2 * math.pi * 120 * i / SAMPLE_RATE) * 0.3
        for i in range(n)
    ]

    result = transfer_style(source, target, 0.7, 12)
    print(transfer_text(result))

    # Brightness match
    matched = match_brightness(source, target)
    mp = _compute_profile(matched, 8)
    print(f"\n  After brightness match: {mp.brightness:.3f}")

    print("Done.")


if __name__ == "__main__":
    main()
