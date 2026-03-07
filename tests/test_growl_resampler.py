"""Tests for engine.growl_resampler — DSP transform functions."""

import numpy as np
import pytest

from engine.growl_resampler import (
    bit_reduce,
    comb_filter,
    generate_fm_source,
    generate_saw_source,
    pitch_shift,
    waveshape_distortion,
)


@pytest.fixture
def test_signal():
    """Generate a short test sine wave."""
    t = np.linspace(0, 1, 2048, endpoint=False)
    return np.sin(2 * np.pi * 150 * t)


class TestDSPTransforms:
    def test_pitch_shift_preserves_length(self, test_signal):
        result = pitch_shift(test_signal, semitones=3)
        assert len(result) == len(test_signal)

    def test_waveshape_bounded(self, test_signal):
        result = waveshape_distortion(test_signal, drive=0.5)
        assert np.max(np.abs(result)) <= 1.0 + 0.1

    def test_comb_filter_preserves_length(self, test_signal):
        result = comb_filter(test_signal, delay_ms=2.618, feedback=0.5)
        assert len(result) == len(test_signal)

    def test_bit_reduce_preserves_length(self, test_signal):
        result = bit_reduce(test_signal, bits=8)
        assert len(result) == len(test_signal)


class TestSourceGenerators:
    def test_saw_source_shape(self):
        saw = generate_saw_source(size=2048)
        assert saw.shape == (2048,)

    def test_fm_source_shape(self):
        fm = generate_fm_source(size=2048)
        assert fm.shape == (2048,)
