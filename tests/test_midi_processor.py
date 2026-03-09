"""Tests for engine.midi_processor — Session 175."""
import pytest
from engine.midi_processor import (
    MIDINote, MIDITrack, quantize, humanize,
    transpose, reverse, create_arpeggio, detect_chords,
)


class TestMIDIProcessor:
    def _track(self):
        notes = [
            MIDINote(note=60, velocity=100, start_tick=0, duration_ticks=480),
            MIDINote(note=64, velocity=90, start_tick=480, duration_ticks=480),
            MIDINote(note=67, velocity=80, start_tick=960, duration_ticks=480),
        ]
        return MIDITrack(name="test", notes=notes)

    def test_quantize(self):
        t = self._track()
        q = quantize(t, 480)
        assert len(q.notes) == 3

    def test_humanize(self):
        t = self._track()
        h = humanize(t)
        assert len(h.notes) == 3

    def test_transpose(self):
        t = self._track()
        tr = transpose(t, 3)
        assert tr.notes[0].note == 63

    def test_reverse(self):
        t = self._track()
        r = reverse(t)
        assert len(r.notes) == 3

    def test_arpeggio(self):
        arp = create_arpeggio([60, 64, 67])
        assert len(arp.notes) > 0

    def test_detect_chords(self):
        notes = [
            MIDINote(note=60, velocity=100, start_tick=0, duration_ticks=480),
            MIDINote(note=64, velocity=100, start_tick=0, duration_ticks=480),
            MIDINote(note=67, velocity=100, start_tick=0, duration_ticks=480),
        ]
        t = MIDITrack(name="test", notes=notes)
        chords = detect_chords(t)
        assert isinstance(chords, list)
