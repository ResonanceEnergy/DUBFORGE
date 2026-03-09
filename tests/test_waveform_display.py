"""Tests for engine.waveform_display — Session 231."""
import math
import pytest
from engine.waveform_display import WaveformDisplay

SR = 44100


class TestWaveformDisplay:
    def test_create(self):
        wd = WaveformDisplay()
        assert isinstance(wd, WaveformDisplay)

    def test_ascii_waveform(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        wd = WaveformDisplay()
        art = wd.render_ascii(signal, width=60, height=10)
        assert isinstance(art, str)
        assert len(art) > 0

    def test_level_meter(self):
        wd = WaveformDisplay()
        meter = wd.render_meter(-3.0)
        assert isinstance(meter, str)
