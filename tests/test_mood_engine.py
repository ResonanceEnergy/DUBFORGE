"""Tests for engine.mood_engine — Session 155."""
import pytest
from engine.mood_engine import (
    resolve_mood, get_mood_suggestion, blend_moods,
    mood_suggestion_text, list_moods, MoodSuggestion,
)


class TestMoodEngine:
    def test_resolve_mood(self):
        m = resolve_mood("aggressive")
        assert m == "aggressive"

    def test_resolve_alias(self):
        m = resolve_mood("angry")
        assert isinstance(m, str)
        assert m != ""

    def test_get_suggestion(self):
        s = get_mood_suggestion("dark")
        assert isinstance(s, MoodSuggestion)
        assert s.mood == "dark"

    def test_blend_moods(self):
        s = blend_moods("dark", "euphoric", 0.5)
        assert isinstance(s, MoodSuggestion)

    def test_list_moods(self):
        moods = list_moods()
        assert len(moods) >= 10
        assert "dark" in moods

    def test_to_dict(self):
        s = get_mood_suggestion("heavy")
        d = s.to_dict()
        assert "mood" in d
        assert "bpm" in d
