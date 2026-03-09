"""Tests for engine.auto_arranger — Session 181."""
import pytest
from engine.auto_arranger import generate_arrangement, Arrangement


class TestAutoArranger:
    def test_generate_standard(self):
        arr = generate_arrangement(template="standard", bpm=140.0)
        assert isinstance(arr, Arrangement)
        assert arr.total_bars > 0

    def test_arrangement_to_dict(self):
        arr = generate_arrangement(template="standard", bpm=140.0)
        d = arr.to_dict()
        assert "sections" in d
        assert len(d["sections"]) > 0
