"""Tests for engine.crossfade — Session 211."""
import pytest
from engine.crossfade import CrossfadeEngine, FadeConfig


class TestCrossfade:
    def test_create(self):
        cf = CrossfadeEngine()
        assert isinstance(cf, CrossfadeEngine)

    def test_crossfade(self):
        cf = CrossfadeEngine()
        a = [0.8] * 10000
        b = [0.3] * 10000
        config = FadeConfig(duration_ms=50)
        result = cf.crossfade(a, b, config)
        assert len(result) > 0

    def test_fade_in(self):
        cf = CrossfadeEngine()
        signal = [0.8] * 10000
        config = FadeConfig(duration_ms=50)
        result = cf.fade_in(signal, config)
        assert len(result) == len(signal)
        assert abs(result[0]) < 0.01

    def test_fade_out(self):
        cf = CrossfadeEngine()
        signal = [0.8] * 10000
        config = FadeConfig(duration_ms=50)
        result = cf.fade_out(signal, config)
        assert len(result) == len(signal)
