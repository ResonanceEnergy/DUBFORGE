"""Tests for engine.tuning_system — Session 201."""
import pytest
from engine.tuning_system import TuningSystem


class TestTuningSystem:
    def test_create(self):
        ts = TuningSystem()
        assert isinstance(ts, TuningSystem)

    def test_equal_temperament_midi(self):
        ts = TuningSystem()
        freq = ts.equal_temperament_midi(69)  # A4
        assert abs(freq - 432.0) < 5  # Close to 432
