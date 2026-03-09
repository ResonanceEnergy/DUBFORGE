"""Tests for engine.mix_assistant — Session 153."""
import pytest
from engine.mix_assistant import (
    MixElement, MixSuggestion, analyze_mix, mix_analysis_text,
    analyze_levels, detect_conflicts,
)


class TestMixAssistant:
    def test_analyze_levels(self):
        elements = [
            MixElement(name="kick", element_type="kick", rms_db=-10),
            MixElement(name="sub", element_type="sub_bass", rms_db=-8),
        ]
        suggestions = analyze_levels(elements)
        assert isinstance(suggestions, list)

    def test_detect_conflicts(self):
        elements = [
            MixElement(name="a", freq_range=(20, 200)),
            MixElement(name="b", freq_range=(30, 180)),
        ]
        conflicts = detect_conflicts(elements)
        assert isinstance(conflicts, list)

    def test_analyze_mix(self):
        elements = [MixElement(name="kick", element_type="kick")]
        analysis = analyze_mix(elements)
        assert analysis.overall_score >= 0

    def test_mix_analysis_text(self):
        elements = [MixElement(name="kick")]
        analysis = analyze_mix(elements)
        text = mix_analysis_text(analysis)
        assert isinstance(text, str)
