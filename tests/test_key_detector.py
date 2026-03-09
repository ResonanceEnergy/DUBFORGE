"""Tests for engine.key_detector — Session 209."""
import math
import pytest
from engine.key_detector import KeyDetector, KeyResult

SR = 44100


class TestKeyDetector:
    def test_create(self):
        kd = KeyDetector()
        assert isinstance(kd, KeyDetector)

    def test_detect_key(self):
        # Generate A major signal (440 Hz)
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        kd = KeyDetector()
        result = kd.detect_key(signal)
        assert isinstance(result, KeyResult)
