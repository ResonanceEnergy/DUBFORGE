"""Tests for engine.markov_melody — Session 171."""
import pytest
from engine.markov_melody import MarkovMelody, Melody, MelodyNote, render_melody


class TestMarkovMelody:
    def test_generate(self):
        mm = MarkovMelody(key="C", scale="minor")
        melody = mm.generate(16)
        assert isinstance(melody, Melody)
        assert len(melody.notes) == 16

    def test_melody_note(self):
        n = MelodyNote(midi_note=60, duration_beats=1.0)
        assert n.freq > 0

    def test_render(self):
        mm = MarkovMelody()
        melody = mm.generate(8)
        samples = render_melody(melody)
        assert len(samples) > 0

    def test_total_beats(self):
        mm = MarkovMelody()
        melody = mm.generate(4)
        assert melody.total_beats > 0
