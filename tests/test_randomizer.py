"""Tests for engine.randomizer — Session 205."""
import pytest
from engine.randomizer import RandomizerEngine


class TestRandomizer:
    def test_create(self):
        r = RandomizerEngine(seed=42)
        assert isinstance(r, RandomizerEngine)

    def test_deterministic(self):
        a = RandomizerEngine(seed=42)
        b = RandomizerEngine(seed=42)
        va = a.randomize("wobble_bass")
        vb = b.randomize("wobble_bass")
        assert va == vb
