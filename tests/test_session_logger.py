"""Tests for engine.session_logger — Session 230."""
import pytest
from engine.session_logger import SessionLogger


class TestSessionLogger:
    def test_create(self):
        sl = SessionLogger()
        assert isinstance(sl, SessionLogger)

    def test_log_render(self):
        sl = SessionLogger()
        sl.log_render("sub_bass", "output.wav", duration_s=0.5)
        stats = sl.get_stats()
        assert stats.renders >= 1

    def test_log_module(self):
        sl = SessionLogger()
        sl.log_module("wobble_bass")
        rankings = sl.module_rankings()
        assert isinstance(rankings, list)

    def test_search(self):
        sl = SessionLogger()
        sl.log_render("test_module", "output.wav", duration_s=0.3)
        results = sl.search("test")
        assert len(results) >= 1
