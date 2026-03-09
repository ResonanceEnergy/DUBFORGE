"""Tests for engine.pattern_recognizer — Session 173."""
import math
import pytest
from engine.pattern_recognizer import (
    detect_rhythmic_patterns, detect_spectral_patterns,
    analyze_patterns, PatternMatch, PatternProfile,
)

SR = 44100


class TestPatternRecognizer:
    def test_rhythmic(self):
        signal = [0.5 * math.sin(2 * math.pi * 100 * i / SR) for i in range(SR)]
        patterns = detect_rhythmic_patterns(signal, 140)
        assert isinstance(patterns, list)

    def test_spectral(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        patterns = detect_spectral_patterns(signal)
        assert isinstance(patterns, list)

    def test_analyze(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        profile = analyze_patterns(signal, 140)
        assert isinstance(profile, PatternProfile)
