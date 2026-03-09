"""Tests for engine.resonance — Session 226."""
import math
import pytest
from engine.resonance import ResonanceEngine

SR = 44100


class TestResonance:
    def test_create(self):
        re = ResonanceEngine()
        assert isinstance(re, ResonanceEngine)

    def test_resonant_filter(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        re_eng = ResonanceEngine()
        result = re_eng.resonant_filter(signal, 1000.0, 0.8)
        assert len(result) == len(signal)
