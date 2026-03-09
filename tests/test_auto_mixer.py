"""Tests for engine.auto_mixer — Session 165."""
import math
import pytest
from engine.auto_mixer import (
    auto_gain_stage, TrackInfo, measure_rms, measure_peak,
    db_from_linear, linear_from_db, apply_gain, normalize,
)

SR = 44100


class TestAutoMixer:
    def test_measure_rms(self):
        signal = [0.5] * 1000
        rms = measure_rms(signal)
        assert rms > 0

    def test_measure_peak(self):
        signal = [0.3, -0.8, 0.5]
        p = measure_peak(signal)
        assert abs(p - 0.8) < 0.01

    def test_db_conversion(self):
        db = db_from_linear(1.0)
        assert abs(db) < 0.01
        lin = linear_from_db(0.0)
        assert abs(lin - 1.0) < 0.01

    def test_apply_gain(self):
        signal = [0.5, -0.5]
        result = apply_gain(signal, -6.0)
        assert all(abs(r) < abs(s) for r, s in zip(result, signal))

    def test_normalize(self):
        signal = [0.3, -0.5, 0.2]
        result = normalize(signal, -3.0)
        assert len(result) == len(signal)

    def test_auto_gain_stage(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        tracks = [TrackInfo(name="kick", signal=signal, element_type="kick")]
        result = auto_gain_stage(tracks)
        assert result.headroom_db > 0
