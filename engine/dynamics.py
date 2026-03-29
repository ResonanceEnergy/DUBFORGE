"""
DUBFORGE — Dynamic Range Optimizer Engine  (Session 179)

Compressor, limiter, expander, and transient shaper
with PHI-tuned attack/release and auto-gain.
"""

import math
from dataclasses import dataclass

import numpy as np

PHI = 1.6180339887
SAMPLE_RATE = 44100

from engine.turboquant import (  # noqa: E402
    compress_audio_buffer,
    CompressedAudioBuffer,
    phi_optimal_bits,
    TurboQuantConfig,
)


def tq_compress_dynamics(
    signal: list[float],
    label: str = "dynamics",
    config: TurboQuantConfig | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> CompressedAudioBuffer:
    """TQ-compress dynamics-processed audio."""
    bits = phi_optimal_bits(len(signal))
    cfg = config or TurboQuantConfig(bit_width=bits)
    return compress_audio_buffer(signal, label, cfg, sample_rate=sample_rate)


@dataclass
class CompressorSettings:
    """Compressor parameters."""
    threshold_db: float = -12.0
    ratio: float = 4.0
    attack_ms: float = 5.0
    release_ms: float = 50.0
    knee_db: float = 3.0
    makeup_db: float = 0.0
    mix: float = 1.0


@dataclass
class DynamicsProfile:
    """Analysis of dynamic range."""
    peak_db: float = 0.0
    rms_db: float = 0.0
    crest_factor_db: float = 0.0
    dynamic_range_db: float = 0.0
    lufs: float = 0.0

    def to_dict(self) -> dict:
        return {
            "peak_db": round(self.peak_db, 1),
            "rms_db": round(self.rms_db, 1),
            "crest_factor_db": round(self.crest_factor_db, 1),
            "dynamic_range_db": round(self.dynamic_range_db, 1),
            "lufs": round(self.lufs, 1),
        }


def analyze_dynamics(signal: list[float],
                      sample_rate: int = SAMPLE_RATE) -> DynamicsProfile:
    """Analyze dynamic range of signal."""
    if isinstance(signal, np.ndarray):
        if signal.size == 0:
            return DynamicsProfile()
        # Flatten stereo to mono for analysis
        if signal.ndim == 2:
            signal = signal.mean(axis=1)
        peak = float(np.max(np.abs(signal)))
        rms = float(np.sqrt(np.mean(signal ** 2)))
        peak_db = 20 * math.log10(max(peak, 1e-10))
        rms_db = 20 * math.log10(max(rms, 1e-10))
        crest = peak_db - rms_db
        lufs = rms_db - 0.691
        block_size = int(sample_rate * 0.05)
        block_rms_list: list[float] = []
        for i in range(0, len(signal) - block_size, block_size):
            block = signal[i:i + block_size]
            br = float(np.sqrt(np.mean(block ** 2)))
            if br > 1e-10:
                block_rms_list.append(20 * math.log10(br))
        dynamic_range = (max(block_rms_list) - min(block_rms_list)
                         if block_rms_list else 0.0)
        return DynamicsProfile(
            peak_db=peak_db, rms_db=rms_db,
            crest_factor_db=crest,
            dynamic_range_db=dynamic_range, lufs=lufs,
        )
    elif not signal:
        return DynamicsProfile()

    peak = max(abs(x) for x in signal)
    rms = math.sqrt(sum(x * x for x in signal) / len(signal))

    peak_db = 20 * math.log10(max(peak, 1e-10))
    rms_db = 20 * math.log10(max(rms, 1e-10))
    crest = peak_db - rms_db

    # Simple LUFS approximation (K-weighted RMS)
    lufs = rms_db - 0.691

    # Dynamic range (RMS of blocks)
    block_size = int(sample_rate * 0.05)
    block_rms_list: list[float] = []
    for i in range(0, len(signal) - block_size, block_size):
        block = signal[i:i + block_size]
        br = math.sqrt(sum(x * x for x in block) / len(block))
        if br > 1e-10:
            block_rms_list.append(20 * math.log10(br))

    if block_rms_list:
        dynamic_range = max(block_rms_list) - min(block_rms_list)
    else:
        dynamic_range = 0.0

    return DynamicsProfile(
        peak_db=peak_db,
        rms_db=rms_db,
        crest_factor_db=crest,
        dynamic_range_db=dynamic_range,
        lufs=lufs,
    )


def compress(signal: list[float],
             settings: CompressorSettings | None = None,
             sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply compression."""
    s = settings or CompressorSettings()
    if isinstance(signal, np.ndarray):
        if signal.size == 0:
            return []
    elif not signal:
        return []

    attack_coeff = math.exp(-1.0 / (s.attack_ms / 1000.0 * sample_rate))
    release_coeff = math.exp(-1.0 / (s.release_ms / 1000.0 * sample_rate))

    envelope = 0.0
    makeup_linear = 10 ** (s.makeup_db / 20.0)
    result: list[float] = []

    for x in signal:
        level = abs(x)
        if level > envelope:
            envelope = attack_coeff * envelope + (1 - attack_coeff) * level
        else:
            envelope = release_coeff * envelope + (1 - release_coeff) * level

        env_db = 20 * math.log10(max(envelope, 1e-10))

        # Soft knee
        if s.knee_db > 0:
            knee_start = s.threshold_db - s.knee_db / 2
            knee_end = s.threshold_db + s.knee_db / 2
            if env_db < knee_start:
                gain_db = 0.0
            elif env_db > knee_end:
                gain_db = (s.threshold_db - env_db) * (1 - 1 / s.ratio)
            else:
                # Quadratic knee
                t = (env_db - knee_start) / s.knee_db
                gain_db = t * t * (s.threshold_db - env_db) * (1 - 1 / s.ratio)
        else:
            if env_db > s.threshold_db:
                gain_db = (s.threshold_db - env_db) * (1 - 1 / s.ratio)
            else:
                gain_db = 0.0

        gain = 10 ** (gain_db / 20.0) * makeup_linear
        compressed = x * gain
        result.append(x * (1.0 - s.mix) + compressed * s.mix)

    return result


def limit(signal: list[float], ceiling_db: float = -0.3,
          release_ms: float = 50.0,
          sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Brick-wall limiter."""
    ceiling = 10 ** (ceiling_db / 20.0)
    release_coeff = math.exp(-1.0 / (release_ms / 1000.0 * sample_rate))

    gain_reduction = 1.0
    result: list[float] = []

    for x in signal:
        level = abs(x)
        if level * gain_reduction > ceiling:
            gain_reduction = ceiling / max(level, 1e-10)
        else:
            gain_reduction = release_coeff * gain_reduction + (1 - release_coeff) * 1.0
            gain_reduction = min(gain_reduction, 1.0)
        result.append(x * gain_reduction)

    return result


def expand(signal: list[float], threshold_db: float = -40.0,
           ratio: float = 2.0, attack_ms: float = 1.0,
           release_ms: float = 20.0,
           sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Downward expander / gate."""
    attack_coeff = math.exp(-1.0 / (attack_ms / 1000.0 * sample_rate))
    release_coeff = math.exp(-1.0 / (release_ms / 1000.0 * sample_rate))

    envelope = 0.0
    result: list[float] = []

    for x in signal:
        level = abs(x)
        if level > envelope:
            envelope = attack_coeff * envelope + (1 - attack_coeff) * level
        else:
            envelope = release_coeff * envelope + (1 - release_coeff) * level

        env_db = 20 * math.log10(max(envelope, 1e-10))
        if env_db < threshold_db:
            gain_db = (threshold_db - env_db) * (ratio - 1)
            gain = 10 ** (-gain_db / 20.0)
        else:
            gain = 1.0

        result.append(x * gain)

    return result


def transient_shape(signal: list[float],
                     attack_gain: float = 1.5,
                     sustain_gain: float = 0.8,
                     sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Shape transients (attack/sustain balance)."""
    fast_env = 0.0
    slow_env = 0.0
    fast_coeff = math.exp(-1.0 / (0.001 * sample_rate))  # 1ms
    slow_coeff = math.exp(-1.0 / (0.05 * sample_rate))   # 50ms

    result: list[float] = []

    for x in signal:
        level = abs(x)
        fast_env = fast_coeff * fast_env + (1 - fast_coeff) * level
        slow_env = slow_coeff * slow_env + (1 - slow_coeff) * level

        # Transient = fast - slow
        transient = max(0, fast_env - slow_env)
        _sustain = slow_env

        if slow_env > 1e-10:
            transient_ratio = transient / slow_env
        else:
            transient_ratio = 0.0

        # Apply shaping
        gain = 1.0 + transient_ratio * (attack_gain - 1.0)
        gain *= sustain_gain + (1.0 - sustain_gain) * transient_ratio

        result.append(x * gain)

    return result


def phi_compress(signal: list[float],
                  sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Compression with PHI-tuned parameters."""
    settings = CompressorSettings(
        threshold_db=-12.0,
        ratio=PHI * 2,  # ~3.236
        attack_ms=5.0 / PHI,  # ~3.09ms
        release_ms=50.0 * PHI,  # ~80.9ms
        knee_db=3.0,
        makeup_db=3.0,
    )
    return compress(signal, settings, sample_rate)


def dynamics_text(profile: DynamicsProfile) -> str:
    """Format dynamics analysis as text."""
    lines = [
        "Dynamics Analysis:",
        f"  Peak: {profile.peak_db:.1f} dB",
        f"  RMS: {profile.rms_db:.1f} dB",
        f"  Crest: {profile.crest_factor_db:.1f} dB",
        f"  Dynamic Range: {profile.dynamic_range_db:.1f} dB",
        f"  LUFS: {profile.lufs:.1f}",
    ]
    return "\n".join(lines)


def main() -> None:
    print("Dynamic Range Optimizer Engine")

    # Test signal with dynamics
    signal: list[float] = []
    for i in range(SAMPLE_RATE * 2):
        t = i / SAMPLE_RATE
        # Kick-like transient
        env = math.exp(-t * 4) if (t % 0.5) < 0.01 else 0.3
        signal.append(env * math.sin(2 * math.pi * 60 * t) * 0.8)

    # Analyze
    profile = analyze_dynamics(signal)
    print(dynamics_text(profile))

    # Compress
    compressed = compress(signal)
    p2 = analyze_dynamics(compressed)
    print("\n  After compression:")
    print(f"    Crest: {p2.crest_factor_db:.1f} dB (was {profile.crest_factor_db:.1f})")

    # PHI compress
    phi_c = phi_compress(signal)
    p3 = analyze_dynamics(phi_c)
    print(f"    PHI compressed crest: {p3.crest_factor_db:.1f} dB")

    # Limit
    limited = limit(signal, -3.0)
    p4 = analyze_dynamics(limited)
    print(f"    Limited peak: {p4.peak_db:.1f} dB")

    # Transient shape
    shaped = transient_shape(signal, 2.0, 0.7)
    p5 = analyze_dynamics(shaped)
    print(f"    Transient shaped crest: {p5.crest_factor_db:.1f} dB")

    print("Done.")


if __name__ == "__main__":
    main()
