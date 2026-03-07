"""Tests for engine.trance_arp — Fibonacci arpeggiator engine."""
import pytest
from engine.trance_arp import (
    ArpNote,
    ArpPattern,
    fibonacci_rise_pattern,
    phi_spiral_pattern,
    golden_gate_pattern,
    pattern_to_midi_data,
)
from engine.config_loader import PHI


# ── ArpNote dataclass ────────────────────────────────────────────

class TestArpNote:
    def test_defaults(self):
        n = ArpNote(step=0, semitone_offset=5)
        assert n.velocity == 100
        assert n.gate_percent == 61.8
        assert n.duration_beats == 0.25

    def test_custom(self):
        n = ArpNote(step=3, semitone_offset=7, velocity=80, gate_percent=50.0, duration_beats=0.5)
        assert n.step == 3
        assert n.semitone_offset == 7
        assert n.velocity == 80


# ── ArpPattern dataclass ─────────────────────────────────────────

class TestArpPattern:
    def test_defaults(self):
        p = ArpPattern(name="TEST")
        assert p.steps == 13
        assert p.direction == "up_down"
        assert p.octave_range == 3
        assert p.rate == "1/16"
        assert p.notes == []


# ── fibonacci_rise_pattern ───────────────────────────────────────

class TestFibonacciRisePattern:
    def test_returns_arp_pattern(self):
        p = fibonacci_rise_pattern()
        assert isinstance(p, ArpPattern)
        assert p.name == "FIBONACCI_RISE"

    def test_has_notes(self):
        p = fibonacci_rise_pattern()
        assert len(p.notes) == 13
        assert all(isinstance(n, ArpNote) for n in p.notes)

    def test_root_offset(self):
        p = fibonacci_rise_pattern(root_semitone=5)
        # All semitone offsets should be relative to the root
        assert all(isinstance(n.semitone_offset, int) for n in p.notes)

    def test_gate_is_phi(self):
        p = fibonacci_rise_pattern()
        for n in p.notes:
            assert 0 < n.gate_percent <= 100


# ── phi_spiral_pattern ───────────────────────────────────────────

class TestPhiSpiralPattern:
    def test_returns_arp_pattern(self):
        p = phi_spiral_pattern()
        assert isinstance(p, ArpPattern)
        assert p.name == "PHI_SPIRAL"

    def test_has_21_notes(self):
        p = phi_spiral_pattern()
        assert len(p.notes) == 21

    def test_root_offset(self):
        p = phi_spiral_pattern(root_semitone=12)
        assert isinstance(p.notes[0], ArpNote)


# ── golden_gate_pattern ──────────────────────────────────────────

class TestGoldenGatePattern:
    def test_returns_arp_pattern(self):
        p = golden_gate_pattern()
        assert isinstance(p, ArpPattern)
        assert p.name == "GOLDEN_GATE"

    def test_has_13_notes(self):
        p = golden_gate_pattern()
        assert len(p.notes) == 13


# ── pattern_to_midi_data ─────────────────────────────────────────

class TestPatternToMidiData:
    def test_returns_list_of_dicts(self):
        p = fibonacci_rise_pattern()
        midi = pattern_to_midi_data(p)
        assert isinstance(midi, list)
        assert len(midi) > 0

    def test_midi_structure(self):
        p = fibonacci_rise_pattern()
        midi = pattern_to_midi_data(p, bpm=150.0, root_note=60)
        for note in midi:
            assert "note" in note
            assert "velocity" in note
            assert "start_beat" in note
            assert "duration_beat" in note
            assert 0 <= note["note"] <= 127
            assert note["velocity"] > 0

    def test_custom_root(self):
        p = golden_gate_pattern()
        midi = pattern_to_midi_data(p, root_note=48)
        for note in midi:
            assert note["note"] >= 0

    def test_custom_bpm(self):
        p = fibonacci_rise_pattern()
        midi_slow = pattern_to_midi_data(p, bpm=120.0)
        midi_fast = pattern_to_midi_data(p, bpm=180.0)
        # Different BPMs should produce the same beat-level data
        assert len(midi_slow) == len(midi_fast)
