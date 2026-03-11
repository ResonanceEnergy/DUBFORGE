"""
DUBFORGE — Audio Buffer Pool  (Session 208)

Efficient audio buffer management: reusable buffers,
pooling, zero-copy operations, mixing utilities.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class AudioBuffer:
    """An audio buffer with metadata."""
    buffer_id: str
    samples: list[float]
    sample_rate: int = SAMPLE_RATE
    channels: int = 1
    label: str = ""
    in_use: bool = False

    @property
    def duration(self) -> float:
        if self.channels == 0:
            return 0.0
        return len(self.samples) / (self.sample_rate * self.channels)

    @property
    def length(self) -> int:
        return len(self.samples)

    @property
    def peak(self) -> float:
        return max(abs(s) for s in self.samples) if self.samples else 0.0

    @property
    def rms(self) -> float:
        if not self.samples:
            return 0.0
        return math.sqrt(sum(s * s for s in self.samples) / len(self.samples))

    def to_dict(self) -> dict:
        return {
            "id": self.buffer_id,
            "length": self.length,
            "duration": round(self.duration, 3),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "peak": round(self.peak, 4),
            "label": self.label,
            "in_use": self.in_use,
        }


class AudioBufferPool:
    """Pool of reusable audio buffers."""

    def __init__(self, max_buffers: int = 64,
                 default_size: int = SAMPLE_RATE):
        self.max_buffers = max_buffers
        self.default_size = default_size
        self.buffers: dict[str, AudioBuffer] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"buf_{self._counter:04d}"

    def allocate(self, size: int = 0, label: str = "",
                 fill: float = 0.0) -> AudioBuffer:
        """Allocate a new buffer."""
        # Try to reuse a free buffer of similar size
        size = size or self.default_size

        for buf in self.buffers.values():
            if not buf.in_use and len(buf.samples) >= size:
                buf.in_use = True
                buf.label = label
                # Reset samples
                for i in range(len(buf.samples)):
                    buf.samples[i] = fill
                return buf

        # Allocate new
        if len(self.buffers) >= self.max_buffers:
            # Evict oldest unused
            for bid, buf in list(self.buffers.items()):
                if not buf.in_use:
                    del self.buffers[bid]
                    break

        bid = self._next_id()
        buf = AudioBuffer(
            buffer_id=bid,
            samples=[fill] * size,
            label=label,
            in_use=True,
        )
        self.buffers[bid] = buf
        return buf

    def release(self, buffer_id: str) -> bool:
        """Release a buffer back to the pool."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return False
        buf.in_use = False
        return True

    def get(self, buffer_id: str) -> AudioBuffer | None:
        """Get a buffer by ID."""
        return self.buffers.get(buffer_id)

    def from_samples(self, samples: list[float],
                     label: str = "") -> AudioBuffer:
        """Create buffer from existing samples."""
        bid = self._next_id()
        buf = AudioBuffer(
            buffer_id=bid,
            samples=list(samples),
            label=label,
            in_use=True,
        )
        self.buffers[bid] = buf
        return buf

    def from_wav(self, path: str) -> AudioBuffer | None:
        """Load buffer from WAV file."""
        if not os.path.exists(path):
            return None
        with wave.open(path, "r") as wf:
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        if sw == 2:
            vals = struct.unpack(f"<{len(raw) // 2}h", raw)
            samples = [v / 32768.0 for v in vals]
        else:
            samples = [0.0]

        bid = self._next_id()
        buf = AudioBuffer(
            buffer_id=bid,
            samples=samples,
            sample_rate=sr,
            channels=ch,
            label=os.path.basename(path),
            in_use=True,
        )
        self.buffers[bid] = buf
        return buf

    def to_wav(self, buffer_id: str, path: str) -> str:
        """Save buffer to WAV file."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return ""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(buf.channels)
            wf.setsampwidth(2)
            wf.setframerate(buf.sample_rate)
            data = struct.pack(
                f"<{len(buf.samples)}h",
                *[max(-32768, min(32767, int(s * 32767)))
                  for s in buf.samples]
            )
            wf.writeframes(data)
        return path

    # --- Buffer Operations ---

    def copy(self, buffer_id: str, label: str = "") -> AudioBuffer | None:
        """Copy a buffer."""
        src = self.buffers.get(buffer_id)
        if not src:
            return None
        return self.from_samples(
            src.samples,
            label or f"{src.label}_copy"
        )

    def mix(self, buffer_ids: list[str],
            gains: list[float] = None) -> AudioBuffer:
        """Mix multiple buffers."""
        bufs = [self.buffers[bid] for bid in buffer_ids
                if bid in self.buffers]
        if not bufs:
            return self.allocate(label="empty_mix")

        if gains is None:
            gains = [1.0 / len(bufs)] * len(bufs)

        max_len = max(len(b.samples) for b in bufs)
        mixed = [0.0] * max_len

        for buf, gain in zip(bufs, gains):
            for i in range(len(buf.samples)):
                mixed[i] += buf.samples[i] * gain

        return self.from_samples(mixed, "mix")

    def concatenate(self, buffer_ids: list[str]) -> AudioBuffer:
        """Concatenate buffers end to end."""
        samples: list[float] = []
        for bid in buffer_ids:
            buf = self.buffers.get(bid)
            if buf:
                samples.extend(buf.samples)
        return self.from_samples(samples, "concat")

    def slice_buffer(self, buffer_id: str,
                     start_sample: int,
                     end_sample: int) -> AudioBuffer | None:
        """Slice a range from a buffer."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return None
        sliced = buf.samples[start_sample:end_sample]
        return self.from_samples(sliced, f"{buf.label}_slice")

    def apply_gain(self, buffer_id: str, gain_db: float) -> bool:
        """Apply gain to buffer in-place."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return False
        gain = 10.0 ** (gain_db / 20.0)
        buf.samples = [min(1.0, max(-1.0, s * gain))
                       for s in buf.samples]
        return True

    def normalize(self, buffer_id: str,
                  target_db: float = -1.0) -> bool:
        """Normalize buffer in-place."""
        buf = self.buffers.get(buffer_id)
        if not buf or not buf.samples:
            return False
        peak = max(abs(s) for s in buf.samples)
        if peak == 0:
            return True
        target = 10.0 ** (target_db / 20.0)
        gain = target / peak
        buf.samples = [s * gain for s in buf.samples]
        return True

    def reverse(self, buffer_id: str) -> bool:
        """Reverse buffer in-place."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return False
        buf.samples.reverse()
        return True

    def fade(self, buffer_id: str, fade_in_ms: float = 10,
             fade_out_ms: float = 50) -> bool:
        """Apply fade in/out."""
        buf = self.buffers.get(buffer_id)
        if not buf:
            return False

        fi = int(buf.sample_rate * fade_in_ms / 1000)
        fo = int(buf.sample_rate * fade_out_ms / 1000)

        for i in range(min(fi, len(buf.samples))):
            buf.samples[i] *= i / fi
        for i in range(min(fo, len(buf.samples))):
            idx = len(buf.samples) - 1 - i
            buf.samples[idx] *= i / fo

        return True

    # --- Stats ---

    def get_stats(self) -> dict:
        """Get pool statistics."""
        in_use = sum(1 for b in self.buffers.values() if b.in_use)
        total_samples = sum(len(b.samples) for b in self.buffers.values())
        return {
            "total_buffers": len(self.buffers),
            "in_use": in_use,
            "available": len(self.buffers) - in_use,
            "total_samples": total_samples,
            "memory_mb": round(
                total_samples * 8 / 1024 / 1024, 2
            ),
        }


def main() -> None:
    print("Audio Buffer Pool")

    pool = AudioBufferPool()

    # Allocate
    b1 = pool.allocate(SAMPLE_RATE, "sine_432")
    for i in range(len(b1.samples)):
        b1.samples[i] = 0.8 * math.sin(2 * math.pi * 432 * i / SAMPLE_RATE)

    b2 = pool.allocate(SAMPLE_RATE, "sine_216")
    for i in range(len(b2.samples)):
        b2.samples[i] = 0.5 * math.sin(2 * math.pi * 216 * i / SAMPLE_RATE)

    print(f"  B1: {b1.to_dict()}")
    print(f"  B2: {b2.to_dict()}")

    # Mix
    mixed = pool.mix([b1.buffer_id, b2.buffer_id])
    print(f"  Mixed: peak={mixed.peak:.3f}")

    # Normalize
    pool.normalize(mixed.buffer_id, -1.0)
    print(f"  Normalized: peak={mixed.peak:.3f}")

    # Stats
    print(f"\n  Pool: {pool.get_stats()}")
    print("Done.")


if __name__ == "__main__":
    main()
