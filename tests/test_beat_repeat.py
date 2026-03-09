"""Tests for engine.beat_repeat — Session 164."""
import math
import pytest
from engine.beat_repeat import (
    apply_beat_repeat, grid_to_samples, BeatRepeatPatch, BEAT_REPEAT_PRESETS,
)

SR = 44100


class TestBeatRepeat:
    def test_grid_to_samples(self):
        s = grid_to_samples("1/4", 140)
        assert s > 0

    def test_apply(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        patch = BeatRepeatPatch(name="test")
        result = apply_beat_repeat(signal, patch, 140)
        assert len(result) > 0

    def test_presets(self):
        assert len(BEAT_REPEAT_PRESETS) >= 2
