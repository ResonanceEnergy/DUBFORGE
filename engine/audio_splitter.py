"""
DUBFORGE — Audio Splitter  (Session 210)

Split audio by silence detection, beat grid, fixed duration,
or PHI-ratio points. Exports segments as individual files.
"""

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class AudioSegment:
    """A segment of audio with metadata."""
    samples: list[float]
    start_sample: int
    end_sample: int
    index: int
    label: str = ""

    @property
    def duration(self) -> float:
        return len(self.samples) / SAMPLE_RATE

    @property
    def start_time(self) -> float:
        return self.start_sample / SAMPLE_RATE

    @property
    def end_time(self) -> float:
        return self.end_sample / SAMPLE_RATE

    @property
    def peak(self) -> float:
        if not self.samples:
            return 0.0
        return max(abs(s) for s in self.samples)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "label": self.label,
            "start_time": round(self.start_time, 4),
            "end_time": round(self.end_time, 4),
            "duration": round(self.duration, 4),
            "peak": round(self.peak, 4),
            "sample_count": len(self.samples),
        }


class AudioSplitter:
    """Split audio into segments."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def split_by_silence(self, samples: list[float],
                         threshold: float = 0.01,
                         min_silence_ms: float = 100,
                         min_segment_ms: float = 50) -> list[AudioSegment]:
        """Split audio at silence gaps."""
        min_silence_samples = int(min_silence_ms * self.sample_rate / 1000)
        min_segment_samples = int(min_segment_ms * self.sample_rate / 1000)

        segments: list[AudioSegment] = []
        in_sound = False
        segment_start = 0
        silence_count = 0
        idx = 0

        for i, s in enumerate(samples):
            if abs(s) > threshold:
                if not in_sound:
                    segment_start = i
                    in_sound = True
                silence_count = 0
            else:
                if in_sound:
                    silence_count += 1
                    if silence_count >= min_silence_samples:
                        end = i - silence_count
                        seg_samples = samples[segment_start:end]
                        if len(seg_samples) >= min_segment_samples:
                            segments.append(AudioSegment(
                                samples=seg_samples,
                                start_sample=segment_start,
                                end_sample=end,
                                index=idx,
                                label=f"segment_{idx:03d}",
                            ))
                            idx += 1
                        in_sound = False
                        silence_count = 0

        # Capture final segment
        if in_sound:
            seg_samples = samples[segment_start:]
            if len(seg_samples) >= min_segment_samples:
                segments.append(AudioSegment(
                    samples=seg_samples,
                    start_sample=segment_start,
                    end_sample=len(samples),
                    index=idx,
                    label=f"segment_{idx:03d}",
                ))

        return segments

    def split_by_duration(self, samples: list[float],
                          duration_ms: float = 1000,
                          overlap_ms: float = 0) -> list[AudioSegment]:
        """Split into fixed-duration segments."""
        chunk_size = int(duration_ms * self.sample_rate / 1000)
        overlap_size = int(overlap_ms * self.sample_rate / 1000)
        step = max(1, chunk_size - overlap_size)

        segments: list[AudioSegment] = []
        idx = 0
        pos = 0

        while pos < len(samples):
            end = min(pos + chunk_size, len(samples))
            seg_samples = samples[pos:end]

            segments.append(AudioSegment(
                samples=seg_samples,
                start_sample=pos,
                end_sample=end,
                index=idx,
                label=f"chunk_{idx:03d}",
            ))
            idx += 1
            pos += step

        return segments

    def split_by_beats(self, samples: list[float],
                       bpm: float = 140,
                       beats_per_segment: int = 4) -> list[AudioSegment]:
        """Split at beat boundaries."""
        beat_samples = int(60 / bpm * self.sample_rate)
        chunk_size = beat_samples * beats_per_segment

        segments: list[AudioSegment] = []
        idx = 0
        pos = 0

        while pos < len(samples):
            end = min(pos + chunk_size, len(samples))
            segments.append(AudioSegment(
                samples=samples[pos:end],
                start_sample=pos,
                end_sample=end,
                index=idx,
                label=f"bar_{idx:03d}",
            ))
            idx += 1
            pos += chunk_size

        return segments

    def split_by_transients(self, samples: list[float],
                            sensitivity: float = 0.3,
                            min_gap_ms: float = 50) -> list[AudioSegment]:
        """Split at transient (onset) points."""
        min_gap_samples = int(min_gap_ms * self.sample_rate / 1000)

        # Compute onset function (energy derivative)
        window = max(1, self.sample_rate // 200)  # 5ms window
        energy: list[float] = []

        for i in range(0, len(samples) - window, window):
            e = sum(s * s for s in samples[i:i + window]) / window
            energy.append(e)

        # Find peaks in onset function
        onsets = [0]  # Always start at beginning
        threshold = sensitivity * max(energy) if energy else 0

        for i in range(1, len(energy) - 1):
            if (energy[i] > energy[i - 1] and
                    energy[i] > energy[i + 1] and
                    energy[i] > threshold):
                sample_pos = i * window
                if sample_pos - onsets[-1] >= min_gap_samples:
                    onsets.append(sample_pos)

        # Create segments
        segments: list[AudioSegment] = []
        for idx in range(len(onsets)):
            start = onsets[idx]
            end = onsets[idx + 1] if idx + 1 < len(onsets) else len(samples)

            segments.append(AudioSegment(
                samples=samples[start:end],
                start_sample=start,
                end_sample=end,
                index=idx,
                label=f"hit_{idx:03d}",
            ))

        return segments

    def split_by_phi(self, samples: list[float],
                     depth: int = 5) -> list[AudioSegment]:
        """Split at PHI ratio points (golden section)."""
        n = len(samples)
        # Generate split points using PHI
        points = set([0, n])

        def phi_subdivide(start: int, end: int, d: int) -> None:
            if d <= 0 or end - start < 2:
                return
            length = end - start
            p1 = start + int(length / PHI)
            p2 = start + int(length / (PHI * PHI))
            points.add(p1)
            points.add(p2)
            phi_subdivide(start, p1, d - 1)
            phi_subdivide(p1, end, d - 1)

        phi_subdivide(0, n, depth)

        sorted_points = sorted(points)
        segments: list[AudioSegment] = []

        for idx in range(len(sorted_points) - 1):
            start = sorted_points[idx]
            end = sorted_points[idx + 1]
            if end > start:
                segments.append(AudioSegment(
                    samples=samples[start:end],
                    start_sample=start,
                    end_sample=end,
                    index=idx,
                    label=f"phi_{idx:03d}",
                ))

        return segments

    def split_at_points(self, samples: list[float],
                        split_times: list[float]) -> list[AudioSegment]:
        """Split at specific time points (seconds)."""
        points = [0] + [
            min(int(t * self.sample_rate), len(samples))
            for t in sorted(split_times)
        ] + [len(samples)]

        # Remove duplicates and sort
        points = sorted(set(points))

        segments: list[AudioSegment] = []
        for idx in range(len(points) - 1):
            start = points[idx]
            end = points[idx + 1]
            if end > start:
                segments.append(AudioSegment(
                    samples=samples[start:end],
                    start_sample=start,
                    end_sample=end,
                    index=idx,
                    label=f"split_{idx:03d}",
                ))

        return segments

    @staticmethod
    def crossfade(seg_a: AudioSegment, seg_b: AudioSegment,
                  fade_samples: int = 441) -> AudioSegment:
        """Crossfade between two segments."""
        a = seg_a.samples
        b = seg_b.samples
        fade = min(fade_samples, len(a), len(b))

        result = list(a[:-fade])
        for i in range(fade):
            t = i / fade
            result.append(a[len(a) - fade + i] * (1 - t) + b[i] * t)
        result.extend(b[fade:])

        return AudioSegment(
            samples=result,
            start_sample=seg_a.start_sample,
            end_sample=seg_a.start_sample + len(result),
            index=0,
            label="crossfaded",
        )

    @staticmethod
    def _write_wav(path: str, samples: list[float],
                   sample_rate: int = SAMPLE_RATE) -> None:
        """Write 16-bit mono WAV."""
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            data = b""
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                data += struct.pack("<h", int(clamped * 32767))
            wf.writeframes(data)

    def export_segments(self, segments: list[AudioSegment],
                        output_dir: str,
                        prefix: str = "seg") -> list[str]:
        """Export segments as individual WAV files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        paths: list[str] = []
        for seg in segments:
            fname = f"{prefix}_{seg.index:03d}_{seg.label}.wav"
            fpath = str(out / fname)
            self._write_wav(fpath, seg.samples, self.sample_rate)
            paths.append(fpath)

        return paths


def main() -> None:
    print("Audio Splitter")
    splitter = AudioSplitter()

    # Generate test signal: 3 tones separated by silence
    n = SAMPLE_RATE * 3
    samples: list[float] = [0.0] * n

    # Tone bursts
    for start_ms, freq in [(200, 220), (1200, 440), (2200, 660)]:
        s = int(start_ms * SAMPLE_RATE / 1000)
        dur = int(0.3 * SAMPLE_RATE)
        for i in range(dur):
            if s + i < n:
                t = i / SAMPLE_RATE
                samples[s + i] = 0.8 * math.sin(2 * math.pi * freq * t)

    # Silence split
    segs = splitter.split_by_silence(samples)
    print(f"  Silence split: {len(segs)} segments")
    for s in segs:
        print(f"    {s.label}: {s.start_time:.3f}s - {s.end_time:.3f}s "
              f"({s.duration:.3f}s)")

    # Beat split
    beat_segs = splitter.split_by_beats(samples, bpm=140, beats_per_segment=4)
    print(f"  Beat split: {len(beat_segs)} segments")

    # PHI split
    phi_segs = splitter.split_by_phi(samples, depth=3)
    print(f"  PHI split: {len(phi_segs)} segments")

    # Duration split
    dur_segs = splitter.split_by_duration(samples, duration_ms=500)
    print(f"  Duration split: {len(dur_segs)} segments")

    print("Done.")


if __name__ == "__main__":
    main()
