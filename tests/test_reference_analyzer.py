"""Tests for engine.reference_analyzer — Session 166."""
import pytest
from engine.reference_analyzer import (
    TrackProfile, profile_from_signal, compare_to_reference,
    list_references, comparison_text,
)


class TestReferenceAnalyzer:
    def test_list_references(self):
        refs = list_references()
        assert isinstance(refs, list)
        assert len(refs) > 0

    def test_profile_from_signal(self):
        signal = [0.3] * 1000
        p = profile_from_signal(signal, "test")
        assert isinstance(p, TrackProfile)
        assert p.name == "test"

    def test_compare(self):
        signal = [0.3] * 1000
        p = profile_from_signal(signal, "test")
        refs = list_references()
        comp = compare_to_reference(p, refs[0])
        assert comp.overall_match >= 0
