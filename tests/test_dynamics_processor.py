"""Tests for engine.dynamics_processor — Session 221."""
import math
import pytest
from engine.dynamics_processor import DynamicsProcessor, GateConfig

SR = 44100


class TestDynamicsProcessor:
    def test_create(self):
        dp = DynamicsProcessor()
        assert isinstance(dp, DynamicsProcessor)

    def test_gate(self):
        dp = DynamicsProcessor()
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = dp.gate(signal, GateConfig(threshold_db=-30.0))
        assert len(result) == len(signal)
