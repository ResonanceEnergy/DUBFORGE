"""Tests for engine.spectrogram_chat — Session 146."""
import pytest
from engine.spectrogram_chat import SpectrogramResult


class TestSpectrogramResult:
    def test_dataclass(self):
        r = SpectrogramResult(module_name="sub_bass", png_base64="abc",
                              width=400, height=200,
                              freq_range_hz=(20.0, 8000.0),
                              time_range_s=(0.0, 1.0),
                              peak_freq_hz=55.0, elapsed_ms=10.0)
        assert r.module_name == "sub_bass"
        assert r.width == 400
        assert r.peak_freq_hz == 55.0
