"""Tests for engine.spectral_gate — Session 224."""
import math
import pytest
from engine.spectral_gate import SpectralGate, BandGateConfig

SR = 44100


class TestSpectralGate:
    def test_create(self):
        sg = SpectralGate()
        assert isinstance(sg, SpectralGate)

    def test_gate(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        sg = SpectralGate()
        config = BandGateConfig(low_freq=20.0, high_freq=20000.0, threshold_db=-40.0)
        result = sg.gate_band(signal, config)
        assert len(result) > 0
