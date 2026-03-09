"""Tests for engine.clip_manager — Session 223."""
import pytest
from engine.clip_manager import ClipManager, AudioClip


class TestClipManager:
    def test_create(self):
        cm = ClipManager()
        assert isinstance(cm, ClipManager)

    def test_add_clip(self):
        cm = ClipManager()
        cm.add_clip("test", [0.5] * 1000)
        assert len(cm.clips) >= 1

    def test_search(self):
        cm = ClipManager()
        cm.add_clip("kick_01", [0.5] * 1000)
        results = cm.search_clips(name_contains="kick")
        assert len(results) >= 1
