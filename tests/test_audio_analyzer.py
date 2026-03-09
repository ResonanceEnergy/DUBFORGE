"""Tests for engine.audio_analyzer — Session 198."""
import math
import pytest
from engine.audio_analyzer import AudioAnalyzer, AnalysisReport

SR = 44100


class TestAudioAnalyzer:
    def test_create(self):
        aa = AudioAnalyzer()
        assert isinstance(aa, AudioAnalyzer)

    def test_analyze(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        aa = AudioAnalyzer()
        result = aa.analyze(signal)
        assert isinstance(result, AnalysisReport)
