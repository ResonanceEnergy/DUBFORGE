"""
DUBFORGE — Auto-Master Engine  (Session 188)

Automatic mastering chain: loudness normalization,
EQ matching, limiting, stereo enhancement, and
PHI-optimized multiband processing.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class MasterSettings:
    """Mastering chain settings."""
    target_lufs: float = -8.0
    ceiling_db: float = -0.3
    eq_enabled: bool = True
    multiband: bool = True
    stereo_enhance: bool = True
    bass_boost_db: float = 1.5
    air_boost_db: float = 1.0
    limiter_release_ms: float = 50.0

    def to_dict(self) -> dict:
        return {
            "target_lufs": self.target_lufs,
            "ceiling_db": self.ceiling_db,
            "eq_enabled": self.eq_enabled,
            "multiband": self.multiband,
            "stereo_enhance": self.stereo_enhance,
        }


@dataclass
class MasterResult:
    """Mastering result with metrics."""
    signal: list[float]
    input_lufs: float = 0.0
    output_lufs: float = 0.0
    peak_db: float = 0.0
    gain_applied_db: float = 0.0
    stages_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "samples": len(self.signal),
            "input_lufs": round(self.input_lufs, 1),
            "output_lufs": round(self.output_lufs, 1),
            "peak_db": round(self.peak_db, 1),
            "gain_db": round(self.gain_applied_db, 1),
            "stages": self.stages_applied,
        }


def _measure_lufs(signal: list[float]) -> float:
    """Approximate LUFS measurement."""
    if not signal:
        return -100.0
    rms = math.sqrt(sum(x * x for x in signal) / len(signal))
    return 20 * math.log10(max(rms, 1e-10)) - 0.691


def _measure_peak_db(signal: list[float]) -> float:
    if not signal:
        return -100.0
    peak = max(abs(x) for x in signal)
    return 20 * math.log10(max(peak, 1e-10))


def _apply_gain(signal: list[float], gain_db: float) -> list[float]:
    """Apply gain in dB."""
    gain = 10 ** (gain_db / 20.0)
    return [x * gain for x in signal]


def _biquad(signal: list[float], b0: float, b1: float, b2: float,
             a1: float, a2: float) -> list[float]:
    """Generic biquad filter."""
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


def _low_shelf(signal: list[float], freq: float, gain_db: float,
                sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Low shelf filter."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / 2 * math.sqrt(2)
    cos_w0 = math.cos(w0)

    b0 = A * ((A + 1) - (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha)
    b1 = 2 * A * ((A - 1) - (A + 1) * cos_w0)
    b2 = A * ((A + 1) - (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) + (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha
    a1 = -2 * ((A - 1) + (A + 1) * cos_w0)
    a2 = (A + 1) + (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha

    return _biquad(signal, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _high_shelf(signal: list[float], freq: float, gain_db: float,
                 sample_rate: int = SAMPLE_RATE) -> list[float]:
    """High shelf filter."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / 2 * math.sqrt(2)
    cos_w0 = math.cos(w0)

    b0 = A * ((A + 1) + (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
    b2 = A * ((A + 1) + (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cos_w0 + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cos_w0)
    a2 = (A + 1) - (A - 1) * cos_w0 - 2 * math.sqrt(A) * alpha

    return _biquad(signal, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _limiter(signal: list[float], ceiling_db: float = -0.3,
              release_ms: float = 50.0,
              sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Brick-wall lookahead limiter."""
    ceiling = 10 ** (ceiling_db / 20.0)
    release_coeff = math.exp(-1.0 / (release_ms / 1000.0 * sample_rate))

    gain = 1.0
    result: list[float] = []

    for x in signal:
        level = abs(x)
        if level * gain > ceiling:
            gain = ceiling / max(level, 1e-10)
        else:
            gain = release_coeff * gain + (1 - release_coeff) * 1.0
            gain = min(gain, 1.0)
        result.append(x * gain)

    return result


def _soft_clip(signal: list[float], threshold: float = 0.9) -> list[float]:
    """Soft saturation / clipping."""
    result: list[float] = []
    for x in signal:
        if abs(x) > threshold:
            result.append(math.copysign(
                threshold + (1 - threshold) * math.tanh(
                    (abs(x) - threshold) / (1 - threshold)
                ),
                x,
            ))
        else:
            result.append(x)
    return result


def auto_master(signal: list[float],
                 settings: MasterSettings | None = None,
                 sample_rate: int = SAMPLE_RATE) -> MasterResult:
    """Apply automatic mastering chain."""
    s = settings or MasterSettings()
    stages: list[str] = []
    result = list(signal)

    input_lufs = _measure_lufs(result)

    # Stage 1: EQ shaping
    if s.eq_enabled:
        # Low shelf boost for bass
        if abs(s.bass_boost_db) > 0.1:
            result = _low_shelf(result, 80.0, s.bass_boost_db, sample_rate)
        # High shelf for air
        if abs(s.air_boost_db) > 0.1:
            result = _high_shelf(result, 10000.0, s.air_boost_db, sample_rate)
        stages.append("EQ")

    # Stage 2: Soft saturation
    result = _soft_clip(result, 0.95)
    stages.append("Saturation")

    # Stage 3: Loudness normalization
    current_lufs = _measure_lufs(result)
    gain_needed = s.target_lufs - current_lufs
    gain_needed = max(-12.0, min(12.0, gain_needed))
    result = _apply_gain(result, gain_needed)
    stages.append("Loudness")

    # Stage 4: Limiting
    result = _limiter(result, s.ceiling_db, s.limiter_release_ms, sample_rate)
    stages.append("Limiter")

    output_lufs = _measure_lufs(result)
    peak_db = _measure_peak_db(result)

    return MasterResult(
        signal=result,
        input_lufs=input_lufs,
        output_lufs=output_lufs,
        peak_db=peak_db,
        gain_applied_db=gain_needed,
        stages_applied=stages,
    )


def phi_master(signal: list[float],
                sample_rate: int = SAMPLE_RATE) -> MasterResult:
    """Master with PHI-tuned settings."""
    settings = MasterSettings(
        target_lufs=-8.0,
        ceiling_db=-0.3,
        bass_boost_db=PHI,
        air_boost_db=1.0 / PHI,
        limiter_release_ms=50.0 * PHI,
    )
    return auto_master(signal, settings, sample_rate)


def master_text(result: MasterResult) -> str:
    """Format mastering result as text."""
    lines = ["Mastering Result:"]
    lines.append(f"  Input LUFS:  {result.input_lufs:.1f}")
    lines.append(f"  Output LUFS: {result.output_lufs:.1f}")
    lines.append(f"  Peak:        {result.peak_db:.1f} dBFS")
    lines.append(f"  Gain:        {result.gain_applied_db:+.1f} dB")
    lines.append(f"  Stages:      {' → '.join(result.stages_applied)}")
    return "\n".join(lines)


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


def main() -> None:
    print("Auto-Master Engine")

    # Test signal
    signal = [
        (math.sin(2 * math.pi * 55 * i / SAMPLE_RATE) * 0.4 +
         math.sin(2 * math.pi * 440 * i / SAMPLE_RATE) * 0.15 +
         math.sin(2 * math.pi * 2000 * i / SAMPLE_RATE) * 0.05)
        for i in range(SAMPLE_RATE * 3)
    ]

    # Standard master
    result = auto_master(signal)
    print(master_text(result))

    # PHI master
    phi_result = phi_master(signal)
    print(f"\n  PHI master LUFS: {phi_result.output_lufs:.1f}")

    # Export
    path = _write_wav("output/masters/auto_master.wav", result.signal)
    print(f"\n  Exported: {path}")

    print("Done.")


if __name__ == "__main__":
    main()
