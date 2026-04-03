"""
DUBFORGE — Audio Stitcher  (Session 217)

Stitch multiple audio segments into arrangements.
Track layering, gap insertion, PHI-timed structures.
"""

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from engine.config_loader import PHI
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    decompress_audio_buffer,
)
from engine.accel import write_wav

SAMPLE_RATE = 48000


@dataclass
class StitchSegment:
    """A segment for stitching."""
    samples: list[float]
    start_time: float = 0.0  # where to place in timeline (seconds)
    gain: float = 1.0
    fade_in_ms: float = 0.0
    fade_out_ms: float = 0.0
    label: str = ""

    @property
    def duration(self) -> float:
        return len(self.samples) / SAMPLE_RATE

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration


@dataclass
class StitchConfig:
    """Stitching configuration."""
    gap_ms: float = 0.0
    crossfade_ms: float = 0.0
    normalize_output: bool = True
    target_peak: float = 0.95


class AudioStitcher:
    """Stitch audio segments together."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _apply_fade(self, samples: list[float],
                    fade_in_ms: float, fade_out_ms: float) -> list[float]:
        """Apply fade-in and fade-out."""
        result = list(samples)
        n = len(result)

        # Fade in
        fi = int(fade_in_ms * self.sample_rate / 1000)
        for i in range(min(fi, n)):
            result[i] *= i / fi

        # Fade out
        fo = int(fade_out_ms * self.sample_rate / 1000)
        for i in range(min(fo, n)):
            result[n - 1 - i] *= i / fo

        return result

    def stitch_sequential(self, segments: list[StitchSegment],
                          config: StitchConfig | None = None) -> list[float]:
        """Stitch segments sequentially with optional gaps."""
        cfg = config or StitchConfig()
        gap_samples = int(cfg.gap_ms * self.sample_rate / 1000)

        result: list[float] = []

        for i, seg in enumerate(segments):
            audio = self._apply_fade(
                [s * seg.gain for s in seg.samples],
                seg.fade_in_ms or (cfg.crossfade_ms if i > 0 else 0),
                seg.fade_out_ms or (cfg.crossfade_ms if i < len(segments) - 1 else 0),
            )
            result.extend(audio)

            # Add gap (not after last segment)
            if i < len(segments) - 1 and gap_samples > 0:
                result.extend([0.0] * gap_samples)

        if cfg.normalize_output and result:
            pk = max(abs(s) for s in result) or 1.0
            if pk > 0:
                gain = cfg.target_peak / pk
                result = [s * gain for s in result]

        return result

    def stitch_timeline(self, segments: list[StitchSegment]) -> list[float]:
        """Stitch segments at specific timeline positions (mix/overlay)."""
        if not segments:
            return []

        # Determine total length
        max_end = max(
            int(seg.end_time * self.sample_rate)
            for seg in segments
        )

        result = [0.0] * max_end

        for seg in segments:
            start_idx = int(seg.start_time * self.sample_rate)
            audio = self._apply_fade(
                [s * seg.gain for s in seg.samples],
                seg.fade_in_ms, seg.fade_out_ms,
            )

            for i, s in enumerate(audio):
                idx = start_idx + i
                if 0 <= idx < len(result):
                    result[idx] += s

        # Limit
        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 1.0:
            result = [s / pk for s in result]

        return result

    def stitch_crossfade(self, segments: list[StitchSegment],
                         crossfade_ms: float = 50) -> list[float]:
        """Stitch with crossfades between adjacent segments."""
        if not segments:
            return []
        if len(segments) == 1:
            return [s * segments[0].gain for s in segments[0].samples]

        xfade = int(crossfade_ms * self.sample_rate / 1000)

        result = [s * segments[0].gain for s in segments[0].samples]

        for i in range(1, len(segments)):
            next_audio = [s * segments[i].gain for s in segments[i].samples]
            actual_xfade = min(xfade, len(result), len(next_audio))

            if actual_xfade > 0:
                # Crossfade overlap
                for j in range(actual_xfade):
                    t = j / actual_xfade
                    idx = len(result) - actual_xfade + j
                    result[idx] = (result[idx] * math.sqrt(1 - t) +
                                   next_audio[j] * math.sqrt(t))

                result.extend(next_audio[actual_xfade:])
            else:
                result.extend(next_audio)

        return result

    def stitch_phi_arrangement(self, segments: list[StitchSegment],
                               total_duration_s: float = 30) -> list[float]:
        """Arrange segments at PHI-ratio time positions."""
        if not segments:
            return []

        # Generate PHI-spaced positions
        positions: list[float] = []
        pos = 0.0
        step = total_duration_s / (len(segments) * PHI)

        for i in range(len(segments)):
            positions.append(pos)
            pos += step * (PHI if i % 2 == 0 else 1.0 / PHI)

        # Place segments at PHI positions
        placed: list[StitchSegment] = []
        for i, seg in enumerate(segments):
            placed.append(StitchSegment(
                samples=seg.samples,
                start_time=positions[i] if i < len(positions) else 0,
                gain=seg.gain,
                fade_in_ms=seg.fade_in_ms or 10,
                fade_out_ms=seg.fade_out_ms or 10,
                label=seg.label or f"phi_{i}",
            ))

        return self.stitch_timeline(placed)

    def generate_silence(self, duration_ms: float) -> StitchSegment:
        """Generate a silence segment."""
        n = int(duration_ms * self.sample_rate / 1000)
        return StitchSegment(
            samples=[0.0] * n,
            label="silence",
        )

    @staticmethod
    def _write_wav(path: str, samples: list[float],
                   sample_rate: int = SAMPLE_RATE) -> None:
        """Delegates to engine.audio_mmap.write_wav_fast."""
        import numpy as np
        _s = np.asarray(samples, dtype=np.float64) if not isinstance(samples, np.ndarray) else samples
        write_wav(str(path), _s, sample_rate=sample_rate)


    def export(self, samples: list[float], path: str) -> str:
        """Export stitched audio to WAV."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._write_wav(path, samples)
        return path

    def export_compressed(self, samples: list[float],
                          label: str = "",
                          config: TurboQuantConfig | None = None) -> CompressedAudioBuffer:
        """Compress stitched audio for archival/streaming.

        Args:
            samples: Stitched audio samples.
            label: Label for the compressed buffer.
            config: TurboQuant config (default: 3-bit).

        Returns:
            CompressedAudioBuffer.
        """
        cfg = config or TurboQuantConfig(bit_width=3, chunk_size=256)
        return compress_audio_buffer(
            samples,
            buffer_id=label or "stitch",
            config=cfg,
            sample_rate=self.sample_rate,
            label=label,
        )

    @staticmethod
    def decompress_arrangement(cab: CompressedAudioBuffer,
                               config: TurboQuantConfig | None = None) -> list[float]:
        """Decompress a previously compressed arrangement."""
        return decompress_audio_buffer(cab, config)


def main() -> None:
    print("Audio Stitcher")
    stitcher = AudioStitcher()

    # Create test segments
    freqs = [220, 330, 440, 550, 660]
    segments: list[StitchSegment] = []

    for i, freq in enumerate(freqs):
        n = int(0.5 * SAMPLE_RATE)
        audio = [0.7 * math.sin(2 * math.pi * freq * j / SAMPLE_RATE)
                 for j in range(n)]
        segments.append(StitchSegment(
            samples=audio,
            gain=0.8,
            fade_in_ms=10,
            fade_out_ms=10,
            label=f"tone_{freq}Hz",
        ))

    # Sequential
    seq = stitcher.stitch_sequential(segments, StitchConfig(gap_ms=100))
    print(f"  Sequential: {len(seq) / SAMPLE_RATE:.2f}s")

    # Crossfade
    xfade = stitcher.stitch_crossfade(segments, crossfade_ms=50)
    print(f"  Crossfade: {len(xfade) / SAMPLE_RATE:.2f}s")

    # PHI arrangement
    phi = stitcher.stitch_phi_arrangement(segments, total_duration_s=5)
    print(f"  PHI arrangement: {len(phi) / SAMPLE_RATE:.2f}s")

    # Timeline
    for i, seg in enumerate(segments):
        seg.start_time = i * 0.3  # overlapping
    timeline = stitcher.stitch_timeline(segments)
    print(f"  Timeline: {len(timeline) / SAMPLE_RATE:.2f}s")

    print("Done.")


if __name__ == "__main__":
    main()
