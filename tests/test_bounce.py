"""Tests for engine.bounce — Session 222."""
import os
import pytest
from engine.bounce import BounceEngine


class TestBounce:
    def test_create(self):
        be = BounceEngine()
        assert isinstance(be, BounceEngine)

    def test_bounce(self, output_dir):
        be = BounceEngine()
        signal = [0.5] * 44100
        path = str(output_dir / "test_bounce.wav")
        result = be.bounce(signal, path)
        assert os.path.exists(path)
        assert result.sample_count > 0
