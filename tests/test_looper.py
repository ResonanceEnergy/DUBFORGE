"""Tests for engine.looper — Session 168."""
import math
import pytest
from engine.looper import Looper, LoopState, generate_loop_signal

SR = 44100


class TestLooper:
    def test_create(self):
        l = Looper(4)
        assert isinstance(l, Looper)

    def test_record(self):
        l = Looper(4)
        signal = [0.5] * SR
        assert l.record(0, signal) is True

    def test_play_stop(self):
        l = Looper(4)
        l.record(0, [0.5] * SR)
        assert l.play(0) is True
        assert l.stop(0) is True

    def test_overdub(self):
        l = Looper(4)
        l.record(0, [0.5] * SR)
        assert l.overdub(0, [0.3] * SR) is True

    def test_undo(self):
        l = Looper(4)
        l.record(0, [0.5] * SR)
        l.overdub(0, [0.3] * SR)
        assert l.undo(0) is True

    def test_mixed_signal(self):
        l = Looper(4)
        l.record(0, [0.5] * SR)
        mixed = l.get_mixed_signal(0)
        assert len(mixed) > 0

    def test_generate_loop_signal(self):
        signal = generate_loop_signal(440, 0.5)
        assert len(signal) > 0
