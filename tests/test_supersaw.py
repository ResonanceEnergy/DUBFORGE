"""Tests for engine.supersaw — Session 158."""
import pytest
from engine.supersaw import render_supersaw, render_supersaw_mono, SupersawPatch, SUPERSAW_PRESETS


class TestSupersaw:
    def test_render_mono(self):
        patch = SupersawPatch(name="test")
        samples = render_supersaw_mono(patch, 440.0, 0.3)
        assert len(samples) > 0

    def test_render_stereo(self):
        patch = SupersawPatch(name="test")
        left, right = render_supersaw(patch, 440.0, 0.3)
        assert len(left) > 0
        assert len(right) > 0

    def test_presets(self):
        assert len(SUPERSAW_PRESETS) >= 2
