"""Tests for engine.performance_recorder — Session 170."""
import pytest
from engine.performance_recorder import (
    PerformanceRecorder, PerformanceEvent, PerformanceRecording,
)


class TestPerformanceRecorder:
    def test_create(self):
        r = PerformanceRecorder()
        assert not r.is_recording

    def test_record(self):
        r = PerformanceRecorder()
        r.start_recording("test")
        assert r.is_recording
        e = r.record_event("param", "volume", 0.8)
        assert isinstance(e, PerformanceEvent)
        rec = r.stop_recording()
        assert isinstance(rec, PerformanceRecording)
        assert len(rec.events) >= 1

    def test_record_param(self):
        r = PerformanceRecorder()
        r.start_recording("test")
        e = r.record_param("volume", 0.5)
        assert e is not None
        r.stop_recording()

    def test_list_recordings(self):
        r = PerformanceRecorder()
        recs = r.list_recordings()
        assert isinstance(recs, list)

    def test_save_load(self, tmp_path):
        r = PerformanceRecorder()
        r.start_recording("test")
        r.record_event("param", "vol", 0.5)
        rec = r.stop_recording()
        path = str(tmp_path / "rec.json")
        r.save_to_file(rec, path)
        loaded = r.load_from_file(path)
        assert loaded is not None
