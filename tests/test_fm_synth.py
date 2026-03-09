"""Tests for engine.fm_synth — Session 156."""
import pytest
from engine.fm_synth import render_fm, FMPatch, FMOperator, FM_PRESETS


class TestFMSynth:
    def test_render_basic(self):
        patch = FMPatch(name="test")
        samples = render_fm(patch, 440.0, 0.5)
        assert len(samples) > 0
        assert max(abs(s) for s in samples) <= 1.0

    def test_presets(self):
        assert len(FM_PRESETS) >= 3

    def test_render_preset(self):
        for name in list(FM_PRESETS.keys())[:2]:
            patch = FM_PRESETS[name]
            samples = render_fm(patch, 432.0, 0.3)
            assert len(samples) > 0

    def test_operator(self):
        op = FMOperator(freq_ratio=2.0, amplitude=0.5)
        assert op.freq_ratio == 2.0
