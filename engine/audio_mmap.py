"""
DUBFORGE Engine — Memory-Mapped Audio I/O

High-performance audio file reading/writing using numpy memory-mapped arrays.
Eliminates redundant copies for large audio files on a 64GB unified memory system.

Features:
  - Read WAV files as memory-mapped arrays (zero-copy access)
  - Write WAV with direct buffer writes (no intermediate copies)
  - Audio file pool with LRU-style caching
  - Shared write_wav that replaces the ~25 duplicated _write_wav functions

Usage:
    from engine.audio_mmap import (
        mmap_read_wav, write_wav_fast, AudioPool,
    )

    # Zero-copy read — only loads pages you touch
    samples, sr = mmap_read_wav("input.wav")

    # Fast write — single copy from float64 → int16 → disk
    write_wav_fast("output.wav", samples, sample_rate=48000)

    # Pool — cache frequently accessed files
    pool = AudioPool(max_bytes=4 * 1024**3)  # 4GB cache
    samples = pool.get("drums/kick.wav")
"""

from __future__ import annotations

import mmap
import os
import struct
import wave
from pathlib import Path

import numpy as np
import numpy.typing as npt

from engine.config_loader import IS_APPLE_SILICON
from engine.log import get_logger

_log = get_logger("dubforge.audio_mmap")

SAMPLE_RATE = 48000


# ═══════════════════════════════════════════════════════════════════════════
# WAV READING — memory-mapped
# ═══════════════════════════════════════════════════════════════════════════

def mmap_read_wav(path: str | Path,
                  dtype: type = np.float64) -> tuple[npt.NDArray, int]:
    """Read a WAV file using memory-mapped I/O.

    Returns (samples, sample_rate).
    Samples are float64 normalized to [-1.0, 1.0].

    For large files (>1MB), uses mmap for zero-copy access —
    the OS handles paging from disk to unified memory on demand.
    """
    path = str(path)
    file_size = os.path.getsize(path)

    # For small files, regular read is faster (no mmap overhead)
    if file_size < 1024 * 1024:
        return _read_wav_regular(path, dtype)

    return _read_wav_mmap(path, dtype)


def _read_wav_mmap(path: str,
                   dtype: type = np.float64) -> tuple[npt.NDArray, int]:
    """Memory-mapped WAV read — zero-copy for large files."""
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Parse RIFF header
            if mm[:4] != b"RIFF":
                raise ValueError(f"Not a RIFF file: {path}")
            if mm[8:12] != b"WAVE":
                raise ValueError(f"Not a WAVE file: {path}")

            # Find fmt and data chunks
            pos = 12
            fmt_data = None
            data_offset = 0
            data_size = 0
            sample_rate = SAMPLE_RATE
            channels = 1
            bits_per_sample = 16

            while pos < len(mm) - 8:
                chunk_id = mm[pos:pos + 4]
                chunk_size = struct.unpack_from("<I", mm, pos + 4)[0]

                if chunk_id == b"fmt ":
                    audio_format = struct.unpack_from("<H", mm, pos + 8)[0]
                    channels = struct.unpack_from("<H", mm, pos + 10)[0]
                    sample_rate = struct.unpack_from("<I", mm, pos + 12)[0]
                    bits_per_sample = struct.unpack_from("<H", mm, pos + 22)[0]
                elif chunk_id == b"data":
                    data_offset = pos + 8
                    data_size = chunk_size
                    break

                pos += 8 + chunk_size
                if chunk_size % 2:  # WAV chunks are word-aligned
                    pos += 1

            if data_offset == 0:
                raise ValueError(f"No data chunk found: {path}")

            # Create numpy array from mmap buffer
            bytes_per_sample = bits_per_sample // 8
            n_samples = data_size // (bytes_per_sample * channels)

            if bits_per_sample == 16:
                raw = np.frombuffer(mm, dtype=np.int16,
                                    count=n_samples * channels,
                                    offset=data_offset)
                samples = raw.astype(dtype) / 32768.0
            elif bits_per_sample == 24:
                # 24-bit needs manual unpacking
                raw_bytes = mm[data_offset:data_offset + data_size]
                samples = _decode_24bit(raw_bytes, n_samples * channels, dtype)
            elif bits_per_sample == 32:
                raw = np.frombuffer(mm, dtype=np.float32,
                                    count=n_samples * channels,
                                    offset=data_offset)
                samples = raw.astype(dtype)
            else:
                raise ValueError(f"Unsupported bit depth: {bits_per_sample}")

            # Convert to mono if stereo
            if channels == 2:
                samples = (samples[0::2] + samples[1::2]) * 0.5
            elif channels > 2:
                samples = samples.reshape(-1, channels).mean(axis=1)

            return samples, sample_rate

        finally:
            mm.close()


def _read_wav_regular(path: str,
                      dtype: type = np.float64) -> tuple[npt.NDArray, int]:
    """Regular WAV read for small files."""
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(dtype) / 32768.0
    elif width == 3:
        samples = _decode_24bit(raw, n_frames * channels, dtype)
    elif width == 4:
        samples = np.frombuffer(raw, dtype=np.float32).astype(dtype)
    else:
        samples = np.frombuffer(raw, dtype=np.int16).astype(dtype) / 32768.0

    if channels == 2:
        samples = (samples[0::2] + samples[1::2]) * 0.5
    elif channels > 2:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples, sr


def _decode_24bit(raw_bytes: bytes | memoryview,
                  n_samples: int,
                  dtype: type = np.float64) -> npt.NDArray:
    """Decode 24-bit PCM to float array."""
    raw = np.frombuffer(raw_bytes, dtype=np.uint8)[:n_samples * 3]
    # Unpack 3 bytes → 32-bit int
    samples_32 = np.zeros(n_samples, dtype=np.int32)
    samples_32 = (raw[0::3].astype(np.int32) |
                  (raw[1::3].astype(np.int32) << 8) |
                  (raw[2::3].astype(np.int32) << 16))
    # Sign extension from 24-bit
    samples_32[samples_32 >= 0x800000] -= 0x1000000
    return samples_32.astype(dtype) / 8388608.0


# ═══════════════════════════════════════════════════════════════════════════
# WAV WRITING — consolidated, replaces ~25 duplicated _write_wav functions
# ═══════════════════════════════════════════════════════════════════════════

def write_wav_fast(path: str | Path,
                   samples: npt.NDArray,
                   sample_rate: int = SAMPLE_RATE,
                   bits: int = 16,
                   normalize: bool = True) -> str:
    """Write WAV file — single shared implementation.

    Replaces the ~25 copy-pasted _write_wav functions across the engine.
    Handles float64/float32/int16 input, mono/stereo output.

    Args:
        path: Output file path
        samples: Audio samples (1D mono or 2D stereo)
        sample_rate: Sample rate in Hz
        bits: Bit depth (16 or 24)
        normalize: If True, normalize to -1..1 before writing

    Returns: Absolute path written
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure float64
    if isinstance(samples, list):
        samples = np.array(samples, dtype=np.float64)
    elif samples.dtype != np.float64:
        samples = samples.astype(np.float64)

    # Handle 2D (stereo)
    if samples.ndim == 2:
        channels = samples.shape[0] if samples.shape[0] <= 2 else samples.shape[1]
        if samples.shape[1] <= 2:
            samples = samples.T  # (n, 2) → (2, n) not needed, but ensure interleaved
        interleaved = samples.T.flatten()  # Interleave channels
    else:
        channels = 1
        interleaved = samples

    # Normalize
    if normalize:
        peak = np.max(np.abs(interleaved))
        if peak > 1e-10:
            interleaved = interleaved * (0.99 / peak)

    # Clamp
    interleaved = np.clip(interleaved, -1.0, 1.0)

    # Encode
    if bits == 16:
        pcm = (interleaved * 32767).astype(np.int16)
        sample_width = 2
    elif bits == 24:
        # 24-bit encoding
        scaled = (interleaved * 8388607).astype(np.int32)
        pcm_bytes = bytearray()
        for s in scaled:
            s_clamped = max(-8388608, min(8388607, int(s)))
            if s_clamped < 0:
                s_clamped += 0x1000000
            pcm_bytes.extend([
                s_clamped & 0xFF,
                (s_clamped >> 8) & 0xFF,
                (s_clamped >> 16) & 0xFF,
            ])
        sample_width = 3
    else:
        raise ValueError(f"Unsupported bit depth: {bits}")

    # Write using stdlib wave (handles RIFF headers correctly)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        if bits == 16:
            wf.writeframes(pcm.tobytes())
        else:
            wf.writeframes(bytes(pcm_bytes))

    return str(path.resolve())


def write_wav_stereo(path: str | Path,
                     left: npt.NDArray,
                     right: npt.NDArray,
                     sample_rate: int = SAMPLE_RATE,
                     bits: int = 16,
                     normalize: bool = True) -> str:
    """Write stereo WAV from separate L/R channels."""
    stereo = np.stack([left, right])
    return write_wav_fast(path, stereo, sample_rate, bits, normalize)


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO POOL — LRU cache for frequently accessed files
# ═══════════════════════════════════════════════════════════════════════════

class AudioPool:
    """In-memory audio file cache with LRU eviction.

    With 64GB unified memory, we can cache several GB of audio
    without impacting system performance.

    Usage:
        pool = AudioPool(max_bytes=4 * 1024**3)  # 4GB
        samples = pool.get("path/to/file.wav")
    """

    def __init__(self, max_bytes: int = 4 * 1024**3):
        self._cache: dict[str, tuple[npt.NDArray, int]] = {}
        self._access_order: list[str] = []
        self._current_bytes: int = 0
        self._max_bytes: int = max_bytes
        self._hits: int = 0
        self._misses: int = 0

    def get(self, path: str | Path,
            dtype: type = np.float64) -> tuple[npt.NDArray, int] | None:
        """Get audio samples from cache or load from disk."""
        key = str(Path(path).resolve())

        if key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]

        self._misses += 1

        # Load from disk
        try:
            samples, sr = mmap_read_wav(path, dtype)
        except (FileNotFoundError, OSError, ValueError):
            return None
        entry_bytes = samples.nbytes

        # Evict if needed
        while self._current_bytes + entry_bytes > self._max_bytes and self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                evicted = self._cache.pop(oldest_key)
                self._current_bytes -= evicted[0].nbytes

        # Cache
        self._cache[key] = (samples, sr)
        self._access_order.append(key)
        self._current_bytes += entry_bytes

        return samples, sr

    def preload(self, paths: list[str | Path]) -> int:
        """Preload multiple files into cache. Returns count loaded."""
        loaded = 0
        for p in paths:
            try:
                self.get(p)
                loaded += 1
            except Exception as e:
                _log.warning("AudioPool: failed to preload %s: %s", p, e)
        return loaded

    def evict(self, path: str | Path) -> bool:
        """Remove a specific file from cache."""
        key = str(Path(path).resolve())
        if key in self._cache:
            evicted = self._cache.pop(key)
            self._current_bytes -= evicted[0].nbytes
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._access_order.clear()
        self._current_bytes = 0

    def stats(self) -> dict:
        """Cache statistics."""
        total = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "bytes": self._current_bytes,
            "mb": self._current_bytes / (1024 * 1024),
            "max_mb": self._max_bytes / (1024 * 1024),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(total, 1),
        }


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL POOL — shared across engine modules
# ═══════════════════════════════════════════════════════════════════════════

# Default: 4GB cache (safe for 64GB system)
_global_pool: AudioPool | None = None


def get_audio_pool(max_bytes: int = 4 * 1024**3) -> AudioPool:
    """Get or create the global audio pool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = AudioPool(max_bytes)
    return _global_pool


# ═══════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Diagnostic: show audio I/O capabilities."""
    import time

    print("Audio Memory-Map Module")
    print(f"  Apple Silicon: {IS_APPLE_SILICON}")
    print(f"  Default pool: 4GB cache")

    # Benchmark: write + read cycle
    n = 48000 * 10  # 10 seconds
    signal = np.random.randn(n) * 0.5

    tmp_path = "/tmp/dubforge_mmap_test.wav"

    t0 = time.perf_counter_ns()
    write_wav_fast(tmp_path, signal)
    write_time = (time.perf_counter_ns() - t0) / 1e6

    t0 = time.perf_counter_ns()
    loaded, sr = mmap_read_wav(tmp_path)
    read_time = (time.perf_counter_ns() - t0) / 1e6

    print(f"\n  Write benchmark (10s @ 48kHz):")
    print(f"    time: {write_time:.1f}ms")
    print(f"    size: {os.path.getsize(tmp_path) / 1024:.1f}KB")

    print(f"\n  Read benchmark (mmap):")
    print(f"    time: {read_time:.1f}ms")
    print(f"    samples: {len(loaded)}")
    print(f"    sr: {sr}")

    # Pool test
    pool = AudioPool(max_bytes=100 * 1024 * 1024)  # 100MB
    t0 = time.perf_counter_ns()
    pool.get(tmp_path)
    cold = (time.perf_counter_ns() - t0) / 1e6
    t0 = time.perf_counter_ns()
    pool.get(tmp_path)
    hot = (time.perf_counter_ns() - t0) / 1e6

    print(f"\n  Pool benchmark:")
    print(f"    cold: {cold:.3f}ms")
    print(f"    hot:  {hot:.3f}ms")
    print(f"    speedup: {cold / max(hot, 0.001):.0f}×")
    print(f"    stats: {pool.stats()}")

    os.unlink(tmp_path)
    print("\nDone.")


if __name__ == "__main__":
    main()
