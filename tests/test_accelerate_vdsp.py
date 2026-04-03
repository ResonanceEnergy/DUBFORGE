"""Tests for engine.accelerate_vdsp — Apple Accelerate framework bridge."""

import math

import numpy as np
import pytest

from engine.accelerate_vdsp import (
    HAS_VDSP,
    biquad_bandpass,
    biquad_highpass,
    biquad_lowpass,
    vdsp_biquad,
    vdsp_convolve,
    vdsp_fft,
    vdsp_ifft,
    vdsp_normalize,
    vdsp_peak,
    vdsp_rms,
)

SR = 48000


def _sine(freq: float = 440.0, dur: float = 0.1, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


def _noise(n: int = 4800) -> np.ndarray:
    return np.random.default_rng(42).standard_normal(n).astype(np.float64)


# ─── FFT ────────────────────────────────────────────────────────────────
class TestVDSPFFT:
    def test_fft_matches_numpy(self):
        sig = _sine()
        result = vdsp_fft(sig)
        ref = np.fft.rfft(sig)
        np.testing.assert_allclose(result, ref, atol=1e-10)

    def test_ifft_roundtrip(self):
        sig = _sine()
        spectrum = vdsp_fft(sig)
        recovered = vdsp_ifft(spectrum, n=len(sig))
        np.testing.assert_allclose(recovered, sig, atol=1e-10)

    def test_fft_with_n(self):
        sig = _sine(dur=0.01)
        result = vdsp_fft(sig, n=1024)
        assert len(result) == 513


# ─── RMS ────────────────────────────────────────────────────────────────
class TestVDSPRMS:
    def test_rms_positive(self):
        sig = _sine()
        r = vdsp_rms(sig)
        assert r > 0

    def test_rms_sine_approx(self):
        # RMS of a pure sine ≈ 1/√2
        sig = _sine(dur=1.0)
        r = vdsp_rms(sig)
        assert abs(r - 1.0 / math.sqrt(2)) < 0.01

    def test_rms_zero_signal(self):
        sig = np.zeros(1000)
        assert vdsp_rms(sig) == 0.0

    def test_rms_matches_numpy(self):
        sig = _noise(1024)
        vdsp_val = vdsp_rms(sig)
        numpy_val = float(np.sqrt(np.mean(sig ** 2)))
        assert abs(vdsp_val - numpy_val) < 0.05  # float32 precision


# ─── PEAK ───────────────────────────────────────────────────────────────
class TestVDSPPeak:
    def test_peak_positive(self):
        sig = _sine()
        p = vdsp_peak(sig)
        assert p > 0

    def test_peak_matches_numpy(self):
        sig = _noise(1024)
        vdsp_val = vdsp_peak(sig)
        numpy_val = float(np.max(np.abs(sig)))
        assert abs(vdsp_val - numpy_val) < 0.01

    def test_peak_unit_signal(self):
        sig = np.array([0.0, 0.5, -1.0, 0.3])
        assert vdsp_peak(sig) == pytest.approx(1.0, abs=0.01)


# ─── NORMALIZE ──────────────────────────────────────────────────────────
class TestVDSPNormalize:
    def test_normalize_to_peak(self):
        sig = _sine() * 0.3
        normed = vdsp_normalize(sig, target_peak=1.0)
        peak = np.max(np.abs(normed))
        assert abs(peak - 1.0) < 0.01

    def test_normalize_custom_target(self):
        sig = _sine() * 0.5
        normed = vdsp_normalize(sig, target_peak=0.8)
        peak = np.max(np.abs(normed))
        assert abs(peak - 0.8) < 0.01

    def test_normalize_silent(self):
        sig = np.zeros(100)
        normed = vdsp_normalize(sig)
        np.testing.assert_array_equal(normed, sig)


# ─── BIQUAD FILTERS ────────────────────────────────────────────────────
class TestBiquadFilters:
    def test_lowpass_reduces_high_freq(self):
        noise = _noise(4800)
        filtered = biquad_lowpass(noise, cutoff_hz=1000.0)
        spec_orig = np.abs(np.fft.rfft(noise))
        spec_filt = np.abs(np.fft.rfft(filtered))
        high = slice(len(spec_orig) // 2, None)
        assert np.mean(spec_filt[high]) < np.mean(spec_orig[high])

    def test_highpass_reduces_low_freq(self):
        noise = _noise(4800)
        filtered = biquad_highpass(noise, cutoff_hz=5000.0)
        spec_orig = np.abs(np.fft.rfft(noise))
        spec_filt = np.abs(np.fft.rfft(filtered))
        low = slice(0, len(spec_orig) // 4)
        assert np.mean(spec_filt[low]) < np.mean(spec_orig[low])

    def test_bandpass_shape(self):
        noise = _noise(4800)
        filtered = biquad_bandpass(noise, center_hz=2000.0, q=2.0)
        assert len(filtered) == len(noise)

    def test_lowpass_preserves_length(self):
        sig = _sine()
        filtered = biquad_lowpass(sig, cutoff_hz=500.0)
        assert len(filtered) == len(sig)

    def test_biquad_direct(self):
        sig = _sine()
        # Simple identity-ish filter
        result = vdsp_biquad(sig, 1.0, 0.0, 0.0, 0.0, 0.0)
        np.testing.assert_allclose(result, sig, atol=1e-10)


# ─── CONVOLUTION ────────────────────────────────────────────────────────
class TestVDSPConvolve:
    def test_matches_numpy(self):
        sig = _sine()
        kernel = np.random.default_rng(42).standard_normal(64).astype(np.float64)
        result = vdsp_convolve(sig, kernel)
        ref = np.convolve(sig, kernel, mode="full")
        np.testing.assert_allclose(result, ref, atol=1e-3)

    def test_short_kernel_fallback(self):
        sig = _sine()
        kernel = np.array([1.0, -1.0])
        result = vdsp_convolve(sig, kernel)
        ref = np.convolve(sig, kernel, mode="full")
        np.testing.assert_allclose(result, ref, atol=1e-10)

    def test_output_length(self):
        sig = np.ones(100)
        kernel = np.ones(10)
        result = vdsp_convolve(sig, kernel)
        assert len(result) == 109  # full mode: len(sig) + len(kernel) - 1
