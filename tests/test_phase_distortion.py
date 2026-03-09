"""Tests for engine.phase_distortion — Session 161."""
import pytest
from engine.phase_distortion import render_pd, PDPatch, PD_PRESETS


class TestPhaseDistortion:
    def test_render_basic(self):
        patch = PDPatch(name="test")
        samples = render_pd(patch, 440.0, 0.3)
        assert len(samples) > 0

    def test_presets_exist(self):
        assert len(PD_PRESETS) >= 2

    def test_render_preset(self):
        name = list(PD_PRESETS.keys())[0]
        samples = render_pd(PD_PRESETS[name], 432.0, 0.3)
        assert len(samples) > 0
