"""Tests for engine.tempo_detector — Session 216."""
import math
import pytest
from engine.tempo_detector import TempoDetector

SR = 44100


class TestTempoDetector:
    def test_create(self):
        td = TempoDetector()
        assert isinstance(td, TempoDetector)

    def test_detect(self):
        # Create simple click track at 140 BPM
        beat_dur = int(60.0 / 140 * SR)
        signal = [0.0] * (beat_dur * 8)
        for beat in range(8):
            pos = beat * beat_dur
            for j in range(200):
                if pos + j < len(signal):
                    signal[pos + j] = 0.9 * math.exp(-j / 50.0)
        td = TempoDetector()
        result = td.detect(signal)
        assert isinstance(result.bpm, float)
        assert result.bpm > 0
