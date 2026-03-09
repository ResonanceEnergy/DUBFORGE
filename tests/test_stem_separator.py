"""Tests for engine.stem_separator — Session 182."""
import math
import pytest
from engine.stem_separator import separate_stems, StemSet

SR = 44100


class TestStemSeparator:
    def test_separate(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = separate_stems(signal)
        assert isinstance(result, StemSet)
        assert len(result.stems) > 0

    def test_stem_set_to_dict(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = separate_stems(signal)
        d = result.to_dict()
        assert "stems" in d
