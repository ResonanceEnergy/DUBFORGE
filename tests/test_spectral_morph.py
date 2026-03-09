"""Tests for engine.spectral_morph — Session 180."""
import math
import pytest
from engine.spectral_morph import spectral_morph, MorphResult

SR = 44100


class TestSpectralMorph:
    def test_morph(self):
        a = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        b = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = spectral_morph(a, b, morph_factor=0.5)
        assert isinstance(result, MorphResult)
        assert len(result.signal) > 0

    def test_morph_result_to_dict(self):
        a = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        b = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = spectral_morph(a, b, morph_factor=0.5)
        d = result.to_dict()
        assert "morph_factor" in d
