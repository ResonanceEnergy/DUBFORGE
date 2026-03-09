"""Tests for engine.vocoder — Session 163."""
import math
import pytest
from engine.vocoder import vocode, render_vocoder, VocoderPatch, VOCODER_PRESETS

SR = 44100


class TestVocoder:
    def test_render_basic(self):
        patch = VocoderPatch(name="test", n_bands=8)
        samples = render_vocoder(440.0, 0.3, patch)
        assert len(samples) > 0

    def test_vocode(self):
        n = SR // 4
        mod = [0.5 * math.sin(2 * math.pi * 100 * i / SR) for i in range(n)]
        car = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(n)]
        patch = VocoderPatch(name="test", n_bands=8)
        result = vocode(mod, car, patch)
        assert len(result) == n

    def test_presets(self):
        assert len(VOCODER_PRESETS) >= 2
