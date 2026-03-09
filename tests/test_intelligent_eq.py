"""Tests for engine.intelligent_eq — Session 178."""
import math
import pytest
from engine.intelligent_eq import analyze_spectrum, auto_eq, EQProfile

SR = 44100


class TestIntelligentEQ:
    def test_analyze_spectrum(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        profile = analyze_spectrum(signal)
        assert isinstance(profile, EQProfile)
        assert len(profile.bands) > 0

    def test_profile_to_dict(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        profile = analyze_spectrum(signal)
        d = profile.to_dict()
        assert isinstance(d, dict)
        assert "bands" in d

    def test_auto_eq(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        processed = auto_eq(signal)
        assert len(processed) == len(signal)
