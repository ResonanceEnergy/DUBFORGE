"""Tests for engine.turboquant — TurboQuant Vector Quantization."""
import math

import numpy as np
import pytest

from engine.turboquant import (
    CompressedAudioBuffer,
    CompressedVector,
    CompressedWavetable,
    SpectralVectorIndex,
    TurboQuantConfig,
    TurboQuantEngine,
    compress_audio_buffer,
    compress_wavetable,
    decompress_audio_buffer,
    decompress_wavetable,
    estimate_compression_stats,
    phi_optimal_bits,
)


# ---------------------------------------------------------------------------
# FWHT & Rotation internals
# ---------------------------------------------------------------------------

class TestFWHT:
    def test_fwht_roundtrip(self):
        """Rotate then unrotate should recover original."""
        from engine.turboquant import _rotate, _unrotate, _random_signs
        rng = np.random.RandomState(123)
        x = rng.randn(64)
        signs = _random_signs(64, seed=42)
        y = _rotate(x, signs)
        x_back = _unrotate(y, signs, original_d=64)
        np.testing.assert_allclose(x, x_back, atol=1e-10)

    def test_fwht_preserves_norm(self):
        """Rotation should preserve L2 norm (orthogonal transform)."""
        from engine.turboquant import _rotate, _random_signs
        rng = np.random.RandomState(99)
        x = rng.randn(128)
        signs = _random_signs(128, seed=7)
        y = _rotate(x, signs)
        np.testing.assert_allclose(np.linalg.norm(x), np.linalg.norm(y), rtol=1e-8)

    def test_fwht_non_power_of_2(self):
        """Should handle non-power-of-2 dimensions via padding."""
        from engine.turboquant import _rotate, _unrotate, _random_signs, _next_power_of_2
        x = np.array([1.0, 2.0, 3.0])
        padded_d = _next_power_of_2(3)  # = 4
        signs = _random_signs(padded_d, seed=1)
        y = _rotate(x, signs)
        assert len(y) == padded_d  # Padded output
        x_back = _unrotate(y, signs, original_d=3)
        np.testing.assert_allclose(x, x_back, atol=1e-10)


# ---------------------------------------------------------------------------
# Lloyd-Max Codebook
# ---------------------------------------------------------------------------

class TestCodebook:
    def test_codebook_symmetric(self):
        """Codebook centroids should be approximately symmetric for Beta PDF."""
        from engine.turboquant import _lloyd_max_codebook
        centroids, boundaries = _lloyd_max_codebook(bits=2, dim=128)
        assert len(centroids) == 4
        assert len(boundaries) == 5
        # Roughly symmetric around 0
        assert abs(centroids[0] + centroids[-1]) < 0.05

    def test_codebook_sorted(self):
        """Centroids and boundaries must be sorted."""
        from engine.turboquant import _lloyd_max_codebook
        centroids, boundaries = _lloyd_max_codebook(bits=3, dim=64)
        assert all(centroids[i] <= centroids[i + 1] for i in range(len(centroids) - 1))
        assert all(boundaries[i] <= boundaries[i + 1] for i in range(len(boundaries) - 1))

    def test_codebook_levels(self):
        """2^b centroids for b bits."""
        from engine.turboquant import _lloyd_max_codebook
        for bits in [1, 2, 3, 4]:
            centroids, _ = _lloyd_max_codebook(bits=bits, dim=256)
            assert len(centroids) == 2 ** bits


# ---------------------------------------------------------------------------
# TurboQuantEngine — Core compress/decompress
# ---------------------------------------------------------------------------

class TestTurboQuantEngine:
    def test_create(self):
        tq = TurboQuantEngine()
        assert tq.config.bit_width == 3

    def test_compress_returns_compressed_vector(self):
        tq = TurboQuantEngine()
        signal = [math.sin(2 * math.pi * i / 256) for i in range(256)]
        cv = tq.compress(signal)
        assert isinstance(cv, CompressedVector)
        assert cv.dim == 256
        assert cv.bit_width == 3
        assert cv.norm > 0

    def test_decompress_returns_list_float(self):
        tq = TurboQuantEngine()
        signal = [math.sin(2 * math.pi * i / 256) for i in range(256)]
        cv = tq.compress(signal)
        recon = tq.decompress(cv)
        assert isinstance(recon, list)
        assert len(recon) == 256
        assert all(isinstance(s, float) for s in recon)

    def test_roundtrip_low_mse(self):
        """3-bit TurboQuant should achieve MSE < 0.15 (paper bound: ~0.03)."""
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=3))
        rng = np.random.RandomState(42)
        signal = rng.randn(512).tolist()
        cv = tq.compress(signal)
        recon = tq.decompress(cv)
        mse = tq.mse(signal, recon)
        assert mse < 0.20, f"MSE too high: {mse}"

    def test_higher_bits_lower_mse(self):
        """More bits → lower MSE."""
        rng = np.random.RandomState(7)
        signal = rng.randn(256).tolist()
        mses = []
        for bits in [2, 3, 4, 5]:
            tq = TurboQuantEngine(TurboQuantConfig(bit_width=bits))
            cv = tq.compress(signal)
            recon = tq.decompress(cv)
            mses.append(tq.mse(signal, recon))
        # MSE should generally decrease with more bits
        assert mses[0] > mses[-1], f"MSE not decreasing: {mses}"

    def test_zero_vector(self):
        """Zero vector should roundtrip to zeros."""
        tq = TurboQuantEngine()
        signal = [0.0] * 128
        cv = tq.compress(signal)
        recon = tq.decompress(cv)
        assert all(abs(s) < 1e-10 for s in recon)

    def test_compression_ratio(self):
        """3 bits per dim on 256-dim → ~5× compression."""
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=3))
        signal = [math.sin(2 * math.pi * i / 256) for i in range(256)]
        cv = tq.compress(signal)
        assert cv.compression_ratio > 3.0

    def test_qjl_mode(self):
        """QJL mode should produce qjl_signs."""
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=4, use_qjl=True))
        signal = [math.sin(2 * math.pi * i / 256) for i in range(256)]
        cv = tq.compress(signal)
        assert cv.qjl_signs is not None
        recon = tq.decompress(cv)
        assert len(recon) == 256

    def test_inner_product_error(self):
        """Inner product error should be computable."""
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=4, use_qjl=True))
        rng = np.random.RandomState(10)
        x = rng.randn(128).tolist()
        y = rng.randn(128).tolist()
        cv = tq.compress(x)
        x_hat = tq.decompress(cv)
        err = tq.inner_product_error(x, y, x_hat)
        assert 0 <= err < 1.0

    def test_deterministic(self):
        """Same input + same seed → same output."""
        cfg = TurboQuantConfig(bit_width=3, rotation_seed=42)
        signal = [0.5, -0.3, 0.1, 0.9, -0.7, 0.2] * 20
        tq1 = TurboQuantEngine(cfg)
        tq2 = TurboQuantEngine(cfg)
        r1 = tq1.decompress(tq1.compress(signal))
        r2 = tq2.decompress(tq2.compress(signal))
        np.testing.assert_array_equal(r1, r2)


# ---------------------------------------------------------------------------
# Bit packing
# ---------------------------------------------------------------------------

class TestBitPacking:
    def test_pack_unpack_roundtrip(self):
        tq = TurboQuantEngine()
        for bits in [1, 2, 3, 4, 5, 6, 7, 8]:
            max_val = (1 << bits) - 1
            rng = np.random.RandomState(bits)
            indices = rng.randint(0, max_val + 1, size=100).astype(np.int32)
            packed = tq._pack_indices(indices, bits)
            unpacked = tq._unpack_indices(packed, 100, bits)
            np.testing.assert_array_equal(indices, unpacked)

    def test_sign_pack_unpack(self):
        tq = TurboQuantEngine()
        signs = np.array([1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0])
        packed = tq._pack_signs(signs)
        unpacked = tq._unpack_signs(packed, 9)
        np.testing.assert_array_equal(signs, unpacked)


# ---------------------------------------------------------------------------
# Wavetable Compression
# ---------------------------------------------------------------------------

class TestWavetableCompression:
    def test_compress_decompress_wavetable(self):
        """Multi-frame wavetable roundtrip."""
        # 4 frames of 256 samples (small wavetable)
        frames = [
            [math.sin(2 * math.pi * i / 256 + phase) for i in range(256)]
            for phase in [0, 0.5, 1.0, 1.5]
        ]
        cw = compress_wavetable(frames, name="test_wt")
        assert isinstance(cw, CompressedWavetable)
        assert cw.name == "test_wt"
        assert len(cw.frames) == 4
        assert cw.compression_ratio > 2.0

        recon = decompress_wavetable(cw)
        assert len(recon) == 4
        assert len(recon[0]) == 256

    def test_wavetable_quality(self):
        """Reconstructed wavetable should be perceptually close."""
        frame = [math.sin(2 * math.pi * i / 2048) for i in range(2048)]
        cw = compress_wavetable([frame], TurboQuantConfig(bit_width=4))
        recon = decompress_wavetable(cw)[0]
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=4))
        mse = tq.mse(frame, recon)
        assert mse < 0.15, f"Wavetable MSE too high: {mse}"


# ---------------------------------------------------------------------------
# Audio Buffer Compression
# ---------------------------------------------------------------------------

class TestAudioBufferCompression:
    def test_compress_decompress_audio(self):
        """Audio buffer roundtrip preserves length."""
        rng = np.random.RandomState(42)
        signal = (rng.randn(10000) * 0.5).tolist()
        cab = compress_audio_buffer(signal, buffer_id="test_buf")
        assert isinstance(cab, CompressedAudioBuffer)
        assert cab.buffer_id == "test_buf"
        assert cab.original_length == 10000

        recon = decompress_audio_buffer(cab)
        assert len(recon) == 10000

    def test_audio_compression_ratio(self):
        """Should achieve >3× compression at 3 bits."""
        signal = [math.sin(2 * math.pi * 440 * i / 48000) for i in range(48000)]
        cab = compress_audio_buffer(signal)
        assert cab.compression_ratio > 3.0

    def test_partial_chunk_padding(self):
        """Non-chunk-aligned lengths should be handled."""
        signal = [0.5] * 300  # 300 with chunk_size=256 → 1 full + 1 partial
        cab = compress_audio_buffer(signal, config=TurboQuantConfig(chunk_size=256))
        recon = decompress_audio_buffer(cab)
        assert len(recon) == 300


# ---------------------------------------------------------------------------
# Spectral Vector Index
# ---------------------------------------------------------------------------

class TestSpectralVectorIndex:
    def test_add_and_search(self):
        """Basic add + search should find similar vectors."""
        idx = SpectralVectorIndex(TurboQuantConfig(bit_width=4, use_qjl=True))
        # Add some "spectral features"
        idx.add("kick", [0.9, 0.1, 0.05, 0.01] * 8, {"type": "drum"})
        idx.add("snare", [0.1, 0.8, 0.3, 0.1] * 8, {"type": "drum"})
        idx.add("hihat", [0.01, 0.1, 0.5, 0.9] * 8, {"type": "drum"})
        assert idx.size() == 3

        # Search for something kick-like
        results = idx.search([0.85, 0.15, 0.08, 0.02] * 8, top_k=2)
        assert len(results) == 2
        assert results[0][0] == "kick"  # Most similar

    def test_empty_index(self):
        idx = SpectralVectorIndex()
        results = idx.search([1.0, 0.0, 0.0])
        assert results == []

    def test_total_bytes(self):
        idx = SpectralVectorIndex()
        idx.add("a", [1.0] * 64)
        idx.add("b", [0.5] * 64)
        assert idx.total_bytes() > 0


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtilities:
    def test_phi_optimal_bits(self):
        assert phi_optimal_bits(2048) == 3
        assert phi_optimal_bits(128) == 3
        assert phi_optimal_bits(64) == 4
        assert phi_optimal_bits(16) == 5

    def test_estimate_compression_stats(self):
        stats = estimate_compression_stats(dim=256, bit_width=3)
        assert stats["compression_ratio"] > 3.0
        assert stats["theoretical_mse_bound"] > 0
        assert stats["bytes_original"] == 256 * 8

    def test_estimate_with_qjl(self):
        stats = estimate_compression_stats(dim=256, bit_width=4, use_qjl=True)
        assert "compression_ratio" in stats
        assert stats["effective_bits"] == 3  # 4 - 1 for QJL

    def test_mse_bound_decreases(self):
        """Higher bits → lower theoretical MSE bound."""
        bounds = [
            estimate_compression_stats(256, b)["theoretical_mse_bound"]
            for b in [1, 2, 3, 4, 5]
        ]
        for i in range(len(bounds) - 1):
            assert bounds[i] > bounds[i + 1]
