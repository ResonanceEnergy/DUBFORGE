"""Tests for engine.saturation — Session 225."""
import math
import pytest
from engine.saturation import SaturationEngine, SatConfig

SR = 44100


class TestSaturation:
    def test_create(self):
        se = SaturationEngine()
        assert isinstance(se, SaturationEngine)

    def test_tube(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        se = SaturationEngine()
        result = se.saturate(signal, SatConfig(sat_type="tube", drive=0.5))
        assert len(result) == len(signal)

    def test_tape(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        se = SaturationEngine()
        result = se.saturate(signal, SatConfig(sat_type="tape", drive=0.5))
        assert len(result) == len(signal)
