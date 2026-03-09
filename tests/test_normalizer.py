"""Tests for engine.normalizer — Session 214."""
import math
import pytest
from engine.normalizer import AudioNormalizer

SR = 44100


class TestNormalizer:
    def test_create(self):
        n = AudioNormalizer()
        assert isinstance(n, AudioNormalizer)

    def test_peak_normalize(self):
        signal = [0.3 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        n = AudioNormalizer()
        norm_result = n.normalize_peak(signal, target_db=-0.3)
        peak = max(abs(s) for s in norm_result.samples)
        assert peak > 0.9
