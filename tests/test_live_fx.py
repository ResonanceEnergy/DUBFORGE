"""Tests for engine.live_fx — Session 177."""
import math
import pytest
from engine.live_fx import (
    LiveFilter, LiveDelay, LiveDistortion, LiveChorus, LivePhaser,
    FXChain, create_dubstep_fx_chain,
)

SR = 44100


def _sine(dur=0.1):
    return [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(int(dur * SR))]


class TestLiveFX:
    def test_filter(self):
        f = LiveFilter(cutoff=1000, resonance=0.5)
        result = f.process(_sine())
        assert len(result) > 0

    def test_delay(self):
        d = LiveDelay(delay_ms=100, feedback=0.3)
        result = d.process(_sine())
        assert len(result) > 0

    def test_distortion(self):
        d = LiveDistortion(drive=3.0)
        result = d.process(_sine())
        assert len(result) > 0

    def test_chorus(self):
        c = LiveChorus(rate=1.0, depth=5.0)
        result = c.process(_sine())
        assert len(result) > 0

    def test_phaser(self):
        p = LivePhaser(rate=0.5, depth=0.5)
        result = p.process(_sine())
        assert len(result) > 0

    def test_fx_chain(self):
        chain = create_dubstep_fx_chain(140)
        result = chain.process(_sine())
        assert len(result) > 0
