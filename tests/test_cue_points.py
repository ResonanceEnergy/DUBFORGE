"""Tests for engine.cue_points — Session 200."""
import pytest
from engine.cue_points import CuePointManager, CuePoint


class TestCuePoints:
    def test_create(self):
        cm = CuePointManager()
        assert isinstance(cm, CuePointManager)

    def test_add_cue(self):
        cm = CuePointManager()
        cm.create_map("test.wav", duration=120.0, bpm=140.0)
        cue = cm.add_cue("test.wav", position=30.0, label="drop")
        assert isinstance(cue, CuePoint)
        assert cue.position == 30.0
