"""Tests for engine.harmonic_gen — Session 219."""
import pytest
from engine.harmonic_gen import HarmonicGenerator


class TestHarmonicGen:
    def test_create(self):
        hg = HarmonicGenerator()
        assert isinstance(hg, HarmonicGenerator)

    def test_render(self):
        hg = HarmonicGenerator()
        spectrum = hg.harmonic_series(440.0)
        samples = hg.render(spectrum, duration_s=0.5)
        assert len(samples) > 0
