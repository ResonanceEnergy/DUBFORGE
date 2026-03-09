"""Tests for engine.genre_detector — Session 154."""
import pytest
from engine.genre_detector import (
    detect_genre_from_params, GenreResult, SpectralFeatures, classify_genre,
)


class TestGenreDetector:
    def test_detect_dubstep(self):
        result = detect_genre_from_params(bpm=140, sub_energy=0.8, bass_energy=0.9)
        assert isinstance(result, GenreResult)
        assert result.primary_genre != ""

    def test_detect_dnb(self):
        result = detect_genre_from_params(bpm=174, sub_energy=0.5, bass_energy=0.6)
        assert isinstance(result, GenreResult)

    def test_classify_features(self):
        f = SpectralFeatures(bpm=140, sub_energy=0.7, bass_energy=0.8,
                             mid_energy=0.5, high_energy=0.3,
                             dynamics_range_db=12.0, rms_db=-10,
                             peak_db=-3, halftime_detected=True,
                             zero_crossing_rate=0.1)
        result = classify_genre(f)
        assert len(result.matches) > 0

    def test_to_dict(self):
        result = detect_genre_from_params()
        d = result.to_dict()
        assert "primary_genre" in d
