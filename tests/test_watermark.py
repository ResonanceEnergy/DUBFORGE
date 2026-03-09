"""Tests for engine.watermark — Session 184."""
import math
import pytest
from engine.watermark import embed_watermark, extract_watermark, embed_id, detect_dubforge

SR = 44100


class TestWatermark:
    def test_embed_watermark(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = embed_watermark(signal, "DUBFORGE")
        assert len(result) == len(signal)

    def test_embed_id(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = embed_id(signal, "PHI42")
        assert len(result) == len(signal)

    def test_detect_dubforge(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = detect_dubforge(signal)
        assert result is None or isinstance(result, str)
