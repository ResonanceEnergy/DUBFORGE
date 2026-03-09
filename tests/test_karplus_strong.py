"""Tests for engine.karplus_strong — Session 186."""
import pytest
from engine.karplus_strong import render_ks, KarplusStrongPatch


class TestKarplusStrong:
    def test_render_default(self):
        samples = render_ks()
        assert len(samples) > 0

    def test_render_with_patch(self):
        patch = KarplusStrongPatch(frequency=440.0, duration=0.5)
        samples = render_ks(patch)
        assert len(samples) > 0
        assert len(samples) == int(0.5 * 44100)
