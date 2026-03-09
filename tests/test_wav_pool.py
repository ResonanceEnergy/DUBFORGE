"""Tests for engine.wav_pool — Session 190."""
import pytest
from engine.wav_pool import WavPool


class TestWavPool:
    def test_create(self):
        wp = WavPool()
        assert isinstance(wp, WavPool)
