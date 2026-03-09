"""Tests for engine.tempo_sync — Session 174."""
import pytest
from engine.tempo_sync import (
    BeatGrid, detect_bpm, beat_delay_ms, phi_delay_ms,
    create_click_track, time_stretch_factor,
)


class TestTempoSync:
    def test_beat_grid(self):
        g = BeatGrid(bpm=140)
        assert g.beat_duration_s > 0
        assert g.bar_duration_s > 0

    def test_beat_delay(self):
        ms = beat_delay_ms(140, 1)
        assert ms > 0

    def test_phi_delay(self):
        ms = phi_delay_ms(140)
        assert ms > 0

    def test_time_stretch(self):
        f = time_stretch_factor(140, 170)
        assert f > 1.0

    def test_click_track(self):
        click = create_click_track(140, 2.0)
        assert len(click) > 0
