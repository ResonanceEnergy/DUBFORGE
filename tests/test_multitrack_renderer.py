"""Tests for engine.multitrack_renderer — Session 197."""
import pytest
from engine.multitrack_renderer import MultiTrackRenderer


class TestMultiTrackRenderer:
    def test_create(self):
        mtr = MultiTrackRenderer()
        assert isinstance(mtr, MultiTrackRenderer)
