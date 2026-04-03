"""Tests for engine.audio_mmap — memory-mapped audio I/O."""

import os
import tempfile

import numpy as np
import pytest

from engine.audio_mmap import (
    AudioPool,
    get_audio_pool,
    mmap_read_wav,
    write_wav_fast,
    write_wav_stereo,
)

SR = 48000


def _sine(freq: float = 440.0, dur: float = 0.5, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return (0.8 * np.sin(2.0 * np.pi * freq * t)).astype(np.float64)


# ─── WRITE WAV ──────────────────────────────────────────────────────────
class TestWriteWav:
    def test_write_creates_file(self, tmp_path):
        sig = _sine()
        path = str(tmp_path / "test.wav")
        result = write_wav_fast(path, sig, sample_rate=SR)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_write_creates_parent_dirs(self, tmp_path):
        sig = _sine()
        path = str(tmp_path / "deep" / "nested" / "dir" / "test.wav")
        write_wav_fast(path, sig)
        assert os.path.exists(path)

    def test_write_16bit(self, tmp_path):
        sig = _sine()
        path = str(tmp_path / "16bit.wav")
        write_wav_fast(path, sig, bits=16)
        size = os.path.getsize(path)
        # 16-bit mono: header + 2 bytes per sample
        expected_data = len(sig) * 2
        assert size > expected_data  # includes WAV header

    def test_write_24bit(self, tmp_path):
        sig = _sine()
        path = str(tmp_path / "24bit.wav")
        write_wav_fast(path, sig, bits=24)
        size = os.path.getsize(path)
        expected_data = len(sig) * 3
        assert size > expected_data

    def test_write_invalid_bits(self, tmp_path):
        sig = _sine()
        path = str(tmp_path / "bad.wav")
        with pytest.raises(ValueError, match="Unsupported bit depth"):
            write_wav_fast(path, sig, bits=32)

    def test_write_normalize(self, tmp_path):
        sig = _sine() * 2.0  # Over unity
        path = str(tmp_path / "norm.wav")
        write_wav_fast(path, sig, normalize=True)
        samples, sr = mmap_read_wav(path)
        assert np.max(np.abs(samples)) <= 1.0

    def test_write_list_input(self, tmp_path):
        sig = [0.0, 0.5, -0.5, 1.0, -1.0]
        path = str(tmp_path / "list.wav")
        write_wav_fast(path, sig)
        assert os.path.exists(path)


# ─── READ WAV ───────────────────────────────────────────────────────────
class TestReadWav:
    def test_roundtrip_16bit(self, tmp_path):
        sig = _sine(dur=0.1)
        path = str(tmp_path / "rt.wav")
        write_wav_fast(path, sig, sample_rate=SR, bits=16)
        samples, sr = mmap_read_wav(path)
        assert sr == SR
        assert len(samples) == len(sig)
        # 16-bit quantization → some error is expected
        np.testing.assert_allclose(samples, sig / np.max(np.abs(sig)) * 0.99,
                                   atol=0.01)

    def test_read_returns_float64(self, tmp_path):
        sig = _sine(dur=0.01)
        path = str(tmp_path / "f64.wav")
        write_wav_fast(path, sig)
        samples, sr = mmap_read_wav(path)
        assert samples.dtype == np.float64

    def test_read_sample_rate(self, tmp_path):
        sig = _sine(dur=0.01)
        for sr_in in [44100, 48000, 96000]:
            path = str(tmp_path / f"sr{sr_in}.wav")
            write_wav_fast(path, sig, sample_rate=sr_in)
            _, sr_out = mmap_read_wav(path)
            assert sr_out == sr_in

    def test_read_nonexistent(self):
        with pytest.raises((FileNotFoundError, OSError)):
            mmap_read_wav("/nonexistent/path.wav")


# ─── WRITE STEREO ──────────────────────────────────────────────────────
class TestWriteStereo:
    def test_stereo_creates_file(self, tmp_path):
        left = _sine(440.0, 0.1)
        right = _sine(880.0, 0.1)
        path = str(tmp_path / "stereo.wav")
        write_wav_stereo(path, left, right, sample_rate=SR)
        assert os.path.exists(path)


# ─── AUDIO POOL ────────────────────────────────────────────────────────
class TestAudioPool:
    def test_pool_creation(self):
        pool = AudioPool(max_bytes=100 * 1024 * 1024)
        stats = pool.stats()
        assert stats["entries"] == 0
        assert stats["max_mb"] == 100.0

    def test_pool_get_and_cache(self, tmp_path):
        sig = _sine(dur=0.05)
        path = str(tmp_path / "cached.wav")
        write_wav_fast(path, sig, sample_rate=SR)

        pool = AudioPool(max_bytes=10 * 1024 * 1024)
        # First read: miss
        result = pool.get(path)
        assert result is not None
        samples, sr = result
        assert len(samples) == len(sig)
        stats = pool.stats()
        assert stats["misses"] == 1

        # Second read: hit
        result2 = pool.get(path)
        assert result2 is not None
        samples2, _ = result2
        stats2 = pool.stats()
        assert stats2["hits"] == 1

    def test_pool_eviction(self, tmp_path):
        # Create a tiny pool that can only hold ~1 file
        pool = AudioPool(max_bytes=10000)
        sig = _sine(dur=0.5)  # ~96KB of float64

        paths = []
        for i in range(3):
            path = str(tmp_path / f"file{i}.wav")
            write_wav_fast(path, sig, sample_rate=SR)
            paths.append(path)

        # Load all - should evict oldest
        for p in paths:
            pool.get(p)

        # Pool should have evicted entries
        stats = pool.stats()
        assert stats["entries"] <= 2  # Can't hold 3 large files in 10KB

    def test_pool_clear(self, tmp_path):
        sig = _sine(dur=0.01)
        path = str(tmp_path / "clear.wav")
        write_wav_fast(path, sig, sample_rate=SR)

        pool = AudioPool(max_bytes=10 * 1024 * 1024)
        pool.get(path)
        assert pool.stats()["entries"] == 1
        pool.clear()
        assert pool.stats()["entries"] == 0

    def test_global_pool(self):
        pool = get_audio_pool()
        assert pool is not None
        assert pool.stats()["max_mb"] > 0

    def test_pool_nonexistent_file(self):
        pool = AudioPool(max_bytes=1024)
        result = pool.get("/nonexistent/audio.wav")
        assert result is None
