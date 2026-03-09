"""Tests for engine.frequency_analyzer — Session 212."""
import math
import pytest
from engine.frequency_analyzer import FrequencyAnalyzer

SR = 44100


class TestFrequencyAnalyzer:
    def test_create(self):
        fa = FrequencyAnalyzer()
        assert isinstance(fa, FrequencyAnalyzer)

    def test_spectrum(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        fa = FrequencyAnalyzer()
        spectrum = fa.compute_spectrum(signal)
        assert len(spectrum) > 0

    def test_peak_frequency(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        fa = FrequencyAnalyzer()
        spectrum = fa.compute_spectrum(signal)
        peak = fa.peak_frequency(spectrum)
        assert abs(peak - 440) < 20  # should be close to 440
