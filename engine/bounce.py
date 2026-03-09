"""
DUBFORGE — Bounce Engine  (Session 222)

Bounce/render audio with real-time processing chain,
offline render, stem bounce, multi-format export.
"""

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class BounceConfig:
    """Bounce/render configuration."""
    sample_rate: int = SAMPLE_RATE
    bit_depth: int = 16
    channels: int = 1
    normalize: bool = True
    target_peak: float = 0.95
    dither: bool = False
    tail_ms: float = 0.0  # extra silence at end


@dataclass
class BounceResult:
    """Result of a bounce operation."""
    path: str
    duration_s: float
    sample_count: int
    peak_db: float
    rms_db: float
    file_size_bytes: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "duration_s": round(self.duration_s, 3),
            "sample_count": self.sample_count,
            "peak_db": round(self.peak_db, 1),
            "rms_db": round(self.rms_db, 1),
            "file_size_bytes": self.file_size_bytes,
        }


class BounceEngine:
    """Render and export audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.processors: list[callable] = []

    def add_processor(self, fn: callable) -> None:
        """Add a processing function to the chain."""
        self.processors.append(fn)

    def clear_processors(self) -> None:
        """Clear processing chain."""
        self.processors.clear()

    def _process(self, samples: list[float]) -> list[float]:
        """Run samples through processing chain."""
        result = list(samples)
        for proc in self.processors:
            result = proc(result)
        return result

    @staticmethod
    def _peak_db(samples: list[float]) -> float:
        if not samples:
            return -120.0
        pk = max(abs(s) for s in samples)
        return 20 * math.log10(pk) if pk > 0 else -120.0

    @staticmethod
    def _rms_db(samples: list[float]) -> float:
        if not samples:
            return -120.0
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        return 20 * math.log10(rms) if rms > 0 else -120.0

    def bounce(self, samples: list[float],
               path: str,
               config: BounceConfig | None = None) -> BounceResult:
        """Bounce audio to file."""
        cfg = config or BounceConfig()

        # Process
        processed = self._process(samples)

        # Add tail
        if cfg.tail_ms > 0:
            tail = int(cfg.tail_ms * cfg.sample_rate / 1000)
            processed.extend([0.0] * tail)

        # Normalize
        if cfg.normalize:
            pk = max(abs(s) for s in processed) if processed else 1.0
            if pk > 0:
                gain = cfg.target_peak / pk
                processed = [s * gain for s in processed]

        # Write
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(cfg.channels)
            wf.setsampwidth(cfg.bit_depth // 8)
            wf.setframerate(cfg.sample_rate)

            max_val = 2 ** (cfg.bit_depth - 1) - 1
            _fmt = "<h" if cfg.bit_depth == 16 else "<i"

            data = b""
            for s in processed:
                clamped = max(-1.0, min(1.0, s))
                if cfg.bit_depth == 16:
                    data += struct.pack("<h", int(clamped * max_val))
                elif cfg.bit_depth == 24:
                    val = int(clamped * 8388607)
                    data += struct.pack("<i", val)[:3]
                else:
                    data += struct.pack("<h", int(clamped * 32767))

            wf.writeframes(data)

        fsize = Path(path).stat().st_size

        return BounceResult(
            path=path,
            duration_s=len(processed) / cfg.sample_rate,
            sample_count=len(processed),
            peak_db=self._peak_db(processed),
            rms_db=self._rms_db(processed),
            file_size_bytes=fsize,
        )

    def bounce_stems(self, stems: dict[str, list[float]],
                     output_dir: str,
                     config: BounceConfig | None = None) -> list[BounceResult]:
        """Bounce multiple stems."""
        results: list[BounceResult] = []
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for name, samples in stems.items():
            path = str(out / f"{name}.wav")
            result = self.bounce(samples, path, config)
            results.append(result)

        return results

    def bounce_mix(self, stems: dict[str, list[float]],
                   path: str,
                   gains: dict[str, float] | None = None,
                   config: BounceConfig | None = None) -> BounceResult:
        """Mix stems and bounce to single file."""
        # Find max length
        max_len = max(len(s) for s in stems.values()) if stems else 0
        mix = [0.0] * max_len

        for name, samples in stems.items():
            gain = (gains or {}).get(name, 1.0)
            for i in range(min(len(samples), max_len)):
                mix[i] += samples[i] * gain

        return self.bounce(mix, path, config)

    def bounce_loop(self, samples: list[float],
                    path: str,
                    repetitions: int = 4,
                    config: BounceConfig | None = None) -> BounceResult:
        """Bounce a looped version."""
        looped: list[float] = []
        for _ in range(repetitions):
            looped.extend(samples)
        return self.bounce(looped, path, config)

    def preview(self, samples: list[float],
                max_duration_s: float = 5.0) -> list[float]:
        """Generate a preview (truncated, processed)."""
        n = int(max_duration_s * self.sample_rate)
        preview = samples[:n]
        return self._process(preview)

    def get_bounce_info(self, samples: list[float],
                        config: BounceConfig | None = None) -> dict:
        """Get info about what a bounce would produce."""
        cfg = config or BounceConfig()
        n = len(samples) + int(cfg.tail_ms * cfg.sample_rate / 1000)

        bytes_per_sample = cfg.bit_depth // 8
        estimated_size = n * bytes_per_sample * cfg.channels + 44  # WAV header

        return {
            "duration_s": round(n / cfg.sample_rate, 3),
            "sample_count": n,
            "estimated_size_bytes": estimated_size,
            "estimated_size_mb": round(estimated_size / 1048576, 2),
            "bit_depth": cfg.bit_depth,
            "sample_rate": cfg.sample_rate,
            "channels": cfg.channels,
        }


def main() -> None:
    print("Bounce Engine")
    engine = BounceEngine()

    # Generate test stems
    n = SAMPLE_RATE * 2
    kick = [0.9 * math.sin(2 * math.pi * 60 * i / SAMPLE_RATE) *
            max(0, 1 - (i % (SAMPLE_RATE // 2)) / 2000)
            for i in range(n)]
    bass = [0.7 * math.sin(2 * math.pi * 40 * i / SAMPLE_RATE)
            for i in range(n)]
    lead = [0.4 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
            for i in range(n)]

    stems = {"kick": kick, "bass": bass, "lead": lead}

    # Info
    info = engine.get_bounce_info(kick)
    print(f"  Estimated: {info['duration_s']}s, {info['estimated_size_mb']}MB")

    # Bounce mix
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        result = engine.bounce_mix(
            stems,
            os.path.join(td, "mix.wav"),
            gains={"kick": 1.0, "bass": 0.8, "lead": 0.5},
        )
        d = result.to_dict()
        print(f"  Mix: {d['duration_s']}s, peak={d['peak_db']}dB, "
              f"size={d['file_size_bytes']}B")

        # Bounce stems
        stem_results = engine.bounce_stems(stems, os.path.join(td, "stems"))
        for r in stem_results:
            print(f"    {Path(r.path).name}: {r.peak_db:.1f}dB")

    print("Done.")


if __name__ == "__main__":
    main()
