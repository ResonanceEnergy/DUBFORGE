"""
DUBFORGE — Audio Normalizer  (Session 214)

Peak, RMS, LUFS-like, and PHI normalization.
Headroom control, true-peak limiting.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class NormConfig:
    """Normalization configuration."""
    mode: str = "peak"  # peak, rms, lufs, phi
    target_db: float = -0.3
    headroom_db: float = 0.3
    true_peak_limit: bool = True


@dataclass
class NormResult:
    """Result of normalization."""
    samples: list[float]
    input_peak_db: float
    output_peak_db: float
    gain_db: float
    input_rms_db: float
    output_rms_db: float

    def to_dict(self) -> dict:
        return {
            "input_peak_db": round(self.input_peak_db, 2),
            "output_peak_db": round(self.output_peak_db, 2),
            "gain_db": round(self.gain_db, 2),
            "input_rms_db": round(self.input_rms_db, 2),
            "output_rms_db": round(self.output_rms_db, 2),
        }


class AudioNormalizer:
    """Normalize audio levels."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    @staticmethod
    def _db_to_linear(db: float) -> float:
        return 10 ** (db / 20)

    @staticmethod
    def _linear_to_db(linear: float) -> float:
        return 20 * math.log10(linear) if linear > 0 else -120.0

    @staticmethod
    def peak(samples: list[float]) -> float:
        """Get peak level."""
        if not samples:
            return 0.0
        return max(abs(s) for s in samples)

    @staticmethod
    def rms(samples: list[float]) -> float:
        """Get RMS level."""
        if not samples:
            return 0.0
        return math.sqrt(sum(s * s for s in samples) / len(samples))

    def lufs_integrated(self, samples: list[float]) -> float:
        """Simplified LUFS-like measurement."""
        # K-weighted filter approximation: high-shelf + high-pass
        # Simplified: just use RMS with pre-emphasis
        if not samples:
            return -120.0

        # Apply simple high-shelf boost (+4dB above 1.5kHz area)
        filtered: list[float] = []
        prev = 0.0
        alpha = 0.9  # high-shelf approximation
        for s in samples:
            hp = s - prev * alpha
            prev = s
            boosted = s + hp * 0.6  # boost high frequencies
            filtered.append(boosted)

        # RMS of filtered signal
        r = self.rms(filtered)
        return self._linear_to_db(r) - 0.691  # LUFS offset

    def normalize_peak(self, samples: list[float],
                       target_db: float = -0.3) -> NormResult:
        """Normalize to peak level."""
        pk = self.peak(samples)
        target = self._db_to_linear(target_db)

        gain = target / pk if pk > 0 else 1.0
        result = [s * gain for s in samples]

        return NormResult(
            samples=result,
            input_peak_db=self._linear_to_db(pk),
            output_peak_db=self._linear_to_db(self.peak(result)),
            gain_db=self._linear_to_db(gain),
            input_rms_db=self._linear_to_db(self.rms(samples)),
            output_rms_db=self._linear_to_db(self.rms(result)),
        )

    def normalize_rms(self, samples: list[float],
                      target_db: float = -18.0) -> NormResult:
        """Normalize to RMS level."""
        r = self.rms(samples)
        target = self._db_to_linear(target_db)

        gain = target / r if r > 0 else 1.0
        result = [s * gain for s in samples]

        # Limit peak
        pk = self.peak(result)
        if pk > 1.0:
            limit_gain = 0.999 / pk
            result = [s * limit_gain for s in result]
            gain *= limit_gain

        return NormResult(
            samples=result,
            input_peak_db=self._linear_to_db(self.peak(samples)),
            output_peak_db=self._linear_to_db(self.peak(result)),
            gain_db=self._linear_to_db(gain),
            input_rms_db=self._linear_to_db(r),
            output_rms_db=self._linear_to_db(self.rms(result)),
        )

    def normalize_lufs(self, samples: list[float],
                       target_lufs: float = -14.0) -> NormResult:
        """Normalize to LUFS target."""
        current = self.lufs_integrated(samples)
        gain_db = target_lufs - current
        gain = self._db_to_linear(gain_db)

        result = [s * gain for s in samples]

        # True-peak limit
        pk = self.peak(result)
        if pk > self._db_to_linear(-0.1):
            limit = self._db_to_linear(-0.1) / pk
            result = [s * limit for s in result]
            gain *= limit
            gain_db = self._linear_to_db(gain)

        return NormResult(
            samples=result,
            input_peak_db=self._linear_to_db(self.peak(samples)),
            output_peak_db=self._linear_to_db(self.peak(result)),
            gain_db=gain_db,
            input_rms_db=self._linear_to_db(self.rms(samples)),
            output_rms_db=self._linear_to_db(self.rms(result)),
        )

    def normalize_phi(self, samples: list[float]) -> NormResult:
        """PHI-based normalization — target is 1/PHI peak."""
        target = 1.0 / PHI  # ~0.618
        return self.normalize_peak(
            samples,
            target_db=self._linear_to_db(target),
        )

    def normalize(self, samples: list[float],
                  config: NormConfig | None = None) -> NormResult:
        """Normalize with config."""
        cfg = config or NormConfig()

        if cfg.mode == "peak":
            return self.normalize_peak(samples, cfg.target_db)
        elif cfg.mode == "rms":
            return self.normalize_rms(samples, cfg.target_db)
        elif cfg.mode == "lufs":
            return self.normalize_lufs(samples, cfg.target_db)
        elif cfg.mode == "phi":
            return self.normalize_phi(samples)
        else:
            return self.normalize_peak(samples, cfg.target_db)

    def true_peak_limit(self, samples: list[float],
                        ceiling_db: float = -0.1) -> list[float]:
        """Apply true-peak limiting."""
        ceiling = self._db_to_linear(ceiling_db)
        result: list[float] = []

        for s in samples:
            if abs(s) > ceiling:
                result.append(math.copysign(ceiling, s))
            else:
                result.append(s)

        return result

    def match_loudness(self, source: list[float],
                       reference: list[float]) -> NormResult:
        """Match loudness of source to reference."""
        ref_rms = self.rms(reference)
        return self.normalize_rms(
            source,
            target_db=self._linear_to_db(ref_rms),
        )


def main() -> None:
    print("Audio Normalizer")
    norm = AudioNormalizer()

    # Generate quiet signal
    n = SAMPLE_RATE
    samples = [0.1 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    print(f"  Input peak: {norm._linear_to_db(norm.peak(samples)):.1f} dB")
    print(f"  Input RMS: {norm._linear_to_db(norm.rms(samples)):.1f} dB")

    for mode in ["peak", "rms", "lufs", "phi"]:
        cfg = NormConfig(mode=mode)
        result = norm.normalize(samples, cfg)
        d = result.to_dict()
        print(f"  {mode:5s}: gain={d['gain_db']:+.1f}dB "
              f"peak={d['output_peak_db']:.1f}dB "
              f"rms={d['output_rms_db']:.1f}dB")

    print("Done.")


if __name__ == "__main__":
    main()
