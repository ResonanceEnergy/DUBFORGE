"""Tests for engine.ring_mod — Session 160."""
import math
import pytest
from engine.ring_mod import ring_modulate, phi_ring_mod, RingModPatch

SR = 44100


class TestRingMod:
    def test_ring_modulate(self):
        signal = [0.8 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        patch = RingModPatch(name="test", carrier_freq=200.0)
        result = ring_modulate(signal, patch)
        assert len(result) == len(signal)

    def test_phi_ring_mod(self):
        result = phi_ring_mod(440.0, 0.3)
        assert len(result) > 0
