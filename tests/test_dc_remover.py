"""Tests for engine.dc_remover — Session 215."""
import pytest
from engine.dc_remover import DCRemover


class TestDCRemover:
    def test_create(self):
        dc = DCRemover()
        assert isinstance(dc, DCRemover)

    def test_remove_mean(self):
        dc = DCRemover()
        signal = [0.5 + 0.3 * i / 100 for i in range(100)]
        result = dc.remove_mean(signal)
        mean = sum(result) / len(result)
        assert abs(mean) < 0.01
