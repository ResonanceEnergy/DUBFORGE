"""Tests for engine.dither — Session 213."""
import pytest
from engine.dither import DitherEngine, DitherConfig


class TestDither:
    def test_create(self):
        d = DitherEngine()
        assert isinstance(d, DitherEngine)

    def test_rpdf(self):
        d = DitherEngine()
        signal = [0.5] * 1000
        config = DitherConfig(dither_type="rpdf", target_bits=16)
        result = d.apply_dither(signal, config)
        assert len(result) == len(signal)

    def test_tpdf(self):
        d = DitherEngine()
        signal = [0.5] * 1000
        config = DitherConfig(dither_type="tpdf", target_bits=16)
        result = d.apply_dither(signal, config)
        assert len(result) == len(signal)
