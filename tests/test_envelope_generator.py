"""Tests for engine.envelope_generator — Session 202."""
import pytest
from engine.envelope_generator import EnvelopeGenerator


class TestEnvelopeGenerator:
    def test_create(self):
        eg = EnvelopeGenerator()
        assert isinstance(eg, EnvelopeGenerator)

    def test_adsr(self):
        eg = EnvelopeGenerator()
        env = eg.adsr(0.01, 0.1, 0.7, 0.3, 1.0)
        assert len(env) > 0
        assert max(env) <= 1.01
