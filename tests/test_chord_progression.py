"""Tests for engine.chord_progression — chord building and progressions."""

from engine.chord_progression import (
    ALL_PRESETS,
    build_chord,
)


class TestBuildChord:
    def test_returns_list(self):
        # root_midi is int, returns list[Note]
        chord = build_chord(60, "major")
        assert isinstance(chord, list)
        assert len(chord) > 0

    def test_minor_chord(self):
        chord = build_chord(60, "minor")
        assert len(chord) >= 3


class TestPresets:
    def test_all_presets_is_dict(self):
        assert isinstance(ALL_PRESETS, dict)
        assert len(ALL_PRESETS) > 0

    def test_each_preset_callable(self):
        for name, factory in ALL_PRESETS.items():
            result = factory()
            assert result is not None, f"Preset {name} returned None"
