"""Tests for engine.dynamics — Session 179."""
import math
import pytest
from engine.dynamics import analyze_dynamics, compress, limit, DynamicsProfile

SR = 44100


class TestDynamics:
    def test_analyze_dynamics(self):
        signal = [0.8 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        profile = analyze_dynamics(signal)
        assert isinstance(profile, DynamicsProfile)
        assert profile.peak_db != 0.0

    def test_compress(self):
        signal = [0.8 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = compress(signal)
        assert len(result) == len(signal)

    def test_limit(self):
        signal = [0.9 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = limit(signal)
        assert len(result) == len(signal)
