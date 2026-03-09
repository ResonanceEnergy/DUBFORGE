"""Tests for engine.vector_synth — Session 162."""
import pytest
from engine.vector_synth import render_vector, VectorPatch, VectorPoint, VECTOR_PRESETS


class TestVectorSynth:
    def test_render_basic(self):
        patch = VectorPatch(name="test")
        samples = render_vector(patch, 440.0, 0.3)
        assert len(samples) > 0

    def test_presets(self):
        assert len(VECTOR_PRESETS) >= 2

    def test_vector_point(self):
        p = VectorPoint(wave_type="sine")
        assert p.wave_type == "sine"
