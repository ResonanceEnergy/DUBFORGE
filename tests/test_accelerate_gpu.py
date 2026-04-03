"""Tests for engine.accelerate_gpu — MLX GPU acceleration layer."""

import numpy as np
import pytest

from engine.accelerate_gpu import (
    HAS_MLX,
    additive_synth,
    batch_fft,
    batch_ifft,
    convolve_fast,
    elementwise_exp,
    elementwise_sin,
    elementwise_tanh,
    fft_irfft,
    fft_rfft,
    generate_wavetable_frames,
    matmul,
    svf_lowpass_fast,
)

SR = 48000


def _sine(freq: float = 440.0, dur: float = 0.1, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


# ─── FFT ────────────────────────────────────────────────────────────────
class TestFFT:
    def test_rfft_returns_complex(self):
        sig = _sine()
        result = fft_rfft(sig)
        assert np.iscomplexobj(result)
        assert len(result) == len(sig) // 2 + 1

    def test_rfft_matches_numpy(self):
        sig = _sine(220.0, 0.05)
        accel = fft_rfft(sig)
        ref = np.fft.rfft(sig)
        np.testing.assert_allclose(np.abs(accel), np.abs(ref), atol=1e-3)

    def test_irfft_roundtrip(self):
        sig = _sine()
        spectrum = fft_rfft(sig)
        recovered = fft_irfft(spectrum, n=len(sig))
        np.testing.assert_allclose(recovered, sig, atol=1e-6)

    def test_rfft_with_n(self):
        sig = _sine(dur=0.01)
        result = fft_rfft(sig, n=1024)
        assert len(result) == 513

    def test_irfft_with_n(self):
        sig = _sine()
        spec = fft_rfft(sig)
        result = fft_irfft(spec, n=2048)
        assert len(result) == 2048


class TestBatchFFT:
    def test_batch_fft_shape(self):
        frames = [_sine(f) for f in [220.0, 440.0, 880.0]]
        result = batch_fft(frames)
        assert result.shape[0] == 3
        assert result.shape[1] == len(frames[0]) // 2 + 1

    def test_batch_roundtrip(self):
        frames = [_sine(f, 0.01) for f in [440.0, 880.0]]
        n = len(frames[0])
        spectra = batch_fft(frames)
        recovered = batch_ifft(spectra, n=n)
        for i, f in enumerate(frames):
            np.testing.assert_allclose(recovered[i], f, atol=1e-6)


# ─── MATRIX OPS ────────────────────────────────────────────────────────
class TestMatmul:
    def test_basic(self):
        a = np.random.randn(4, 8)
        b = np.random.randn(8, 3)
        result = matmul(a, b)
        np.testing.assert_allclose(result, a @ b, atol=1e-4)

    def test_large(self):
        a = np.random.randn(256, 512)
        b = np.random.randn(512, 128)
        result = matmul(a, b)
        np.testing.assert_allclose(result, a @ b, atol=1e-3)


class TestElementwise:
    def test_sin(self):
        x = np.linspace(0, 2 * np.pi, 1000)
        np.testing.assert_allclose(elementwise_sin(x), np.sin(x), atol=1e-5)

    def test_tanh(self):
        x = np.linspace(-5, 5, 1000)
        np.testing.assert_allclose(elementwise_tanh(x), np.tanh(x), atol=1e-5)

    def test_exp(self):
        x = np.linspace(-3, 3, 1000)
        np.testing.assert_allclose(elementwise_exp(x), np.exp(x), atol=1e-4)


# ─── SVF FILTER ─────────────────────────────────────────────────────────
class TestSVFFilter:
    def test_lowpass_reduces_high_freq(self):
        # White noise through lowpass should attenuate high frequencies
        rng = np.random.default_rng(42)
        noise = rng.standard_normal(4800)
        filtered = svf_lowpass_fast(noise, cutoff_hz=1000.0)
        # Check that high-frequency energy is reduced
        spec_orig = np.abs(np.fft.rfft(noise))
        spec_filt = np.abs(np.fft.rfft(filtered))
        high_band = slice(len(spec_orig) // 2, None)
        assert np.mean(spec_filt[high_band]) < np.mean(spec_orig[high_band])

    def test_lowpass_preserves_length(self):
        sig = _sine()
        filtered = svf_lowpass_fast(sig, cutoff_hz=2000.0)
        assert len(filtered) == len(sig)

    def test_lowpass_dc_passthrough(self):
        dc = np.ones(1000)
        filtered = svf_lowpass_fast(dc, cutoff_hz=5000.0)
        # DC should pass through a lowpass
        assert np.mean(filtered[500:]) > 0.5


# ─── ADDITIVE SYNTH ────────────────────────────────────────────────────
class TestAdditiveSynth:
    def test_basic_sine(self):
        sig = additive_synth(440.0, 0.1, [(1.0, 1.0)])
        assert len(sig) == int(0.1 * SR)
        assert np.max(np.abs(sig)) > 0

    def test_multiple_harmonics(self):
        harmonics = [(1.0, 1.0), (2.0, 0.5), (3.0, 0.25)]
        sig = additive_synth(440.0, 0.5, harmonics)
        assert len(sig) == int(0.5 * SR)

    def test_zero_harmonics(self):
        sig = additive_synth(440.0, 0.01, [])
        assert np.all(sig == 0)


# ─── CONVOLUTION ────────────────────────────────────────────────────────
class TestConvolveFast:
    def test_matches_numpy_full(self):
        sig = _sine()
        kernel = np.random.randn(256)
        accel = convolve_fast(sig, kernel, mode="full")
        ref = np.convolve(sig, kernel, mode="full")
        np.testing.assert_allclose(accel, ref, atol=1e-4)

    def test_matches_numpy_same(self):
        sig = _sine()
        kernel = np.random.randn(256)
        accel = convolve_fast(sig, kernel, mode="same")
        ref = np.convolve(sig, kernel, mode="same")
        np.testing.assert_allclose(accel, ref, atol=1e-4)

    def test_short_kernel_fallback(self):
        sig = _sine()
        kernel = np.array([0.5, 0.5])
        result = convolve_fast(sig, kernel, mode="full")
        ref = np.convolve(sig, kernel, mode="full")
        np.testing.assert_allclose(result, ref, atol=1e-10)


# ─── WAVETABLE GENERATION ──────────────────────────────────────────────
class TestWavetableFrames:
    def test_generates_correct_count(self):
        def hfn(i, n):
            return [(1.0, 1.0), (2.0, 0.5)]
        frames = generate_wavetable_frames(440.0, 8, 2048, hfn)
        assert len(frames) == 8
        assert all(len(f) == 2048 for f in frames)

    def test_frames_normalized(self):
        def hfn(i, n):
            return [(1.0, 1.0), (2.0, 0.5), (3.0, 0.25)]
        frames = generate_wavetable_frames(440.0, 4, 1024, hfn)
        for f in frames:
            assert np.max(np.abs(f)) <= 1.0 + 1e-10

    def test_empty_harmonics(self):
        def hfn(i, n):
            return []
        frames = generate_wavetable_frames(440.0, 2, 512, hfn)
        for f in frames:
            assert np.all(f == 0)
