"""Tests for engine.audio_math — Session 228."""
import pytest
from engine.audio_math import AudioMath


class TestAudioMath:
    def test_add(self):
        a = [0.5, 0.3, 0.1]
        b = [0.1, 0.2, 0.3]
        result = AudioMath.add(a, b)
        assert len(result) == 3
        assert abs(result[0] - 0.6) < 0.01

    def test_scale(self):
        signal = [0.5, -0.5]
        result = AudioMath.scale(signal, 0.5)
        assert abs(result[0] - 0.25) < 0.01

    def test_invert(self):
        signal = [0.5, -0.3]
        result = AudioMath.invert(signal)
        assert abs(result[0] + 0.5) < 0.01

    def test_stats(self):
        am = AudioMath()
        signal = [0.5, -0.5, 0.3, -0.3]
        stats = am.stats(signal)
        assert stats.peak == 0.5
        assert stats.sample_count == 4
