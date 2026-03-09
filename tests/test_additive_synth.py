"""Tests for engine.additive_synth — Session 157."""
import pytest
from engine.additive_synth import (
    render_additive, AdditivePatch, Partial, phi_partials,
    harmonic_partials, morph_patches,
)


class TestAdditiveSynth:
    def test_render_basic(self):
        patch = AdditivePatch(name="test")
        samples = render_additive(patch, 440.0, 0.3)
        assert len(samples) > 0

    def test_phi_partials(self):
        partials = phi_partials(8)
        assert len(partials) == 8

    def test_harmonic_partials(self):
        partials = harmonic_partials(6)
        assert len(partials) == 6

    def test_morph(self):
        a = AdditivePatch(name="a", partials=phi_partials(4))
        b = AdditivePatch(name="b", partials=harmonic_partials(4))
        c = morph_patches(a, b, 0.5)
        assert "Morph" in c.name or "a" in c.name
