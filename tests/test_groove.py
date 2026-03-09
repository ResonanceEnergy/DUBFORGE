"""Tests for engine.groove — Session 227."""
import pytest
from engine.groove import GrooveEngine, NoteEvent


class TestGroove:
    def test_create(self):
        ge = GrooveEngine()
        assert isinstance(ge, GrooveEngine)

    def test_quantize(self):
        ge = GrooveEngine()
        events = [
            NoteEvent(time=0.1, duration=0.2, pitch=60),
            NoteEvent(time=0.6, duration=0.2, pitch=64),
        ]
        result = ge.quantize(events, grid=0.25)
        assert len(result) == 2

    def test_humanize(self):
        ge = GrooveEngine()
        events = [
            NoteEvent(time=0.0, duration=0.2, pitch=60),
            NoteEvent(time=0.5, duration=0.2, pitch=64),
        ]
        result = ge.humanize(events, timing_ms=10)
        assert len(result) == 2
