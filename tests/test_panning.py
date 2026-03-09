"""Tests for engine.panning — Session 220."""
import pytest
from engine.panning import PanningEngine


class TestPanning:
    def test_create(self):
        pe = PanningEngine()
        assert isinstance(pe, PanningEngine)

    def test_pan(self):
        pe = PanningEngine()
        signal = [0.5] * 1000
        result = pe.pan_constant_power(signal, 0.0)  # center
        assert len(result.left) == len(signal)
        assert len(result.right) == len(signal)
