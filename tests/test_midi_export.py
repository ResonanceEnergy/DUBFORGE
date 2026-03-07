"""Tests for engine.midi_export — MIDI file generation."""

import json
import unittest
from pathlib import Path

import mido

from engine.midi_export import (
    DEFAULT_BPM,
    GM_PROGRAMS,
    TICKS_PER_BEAT,
    NoteEvent,
    arp_pattern_to_events,
    events_to_track,
    export_arp_midi,
    export_clip_midi,
    export_full_arrangement,
    export_progression_midi,
    midi_clip_to_events,
    progression_to_events,
    raw_midi_events_to_events,
    write_manifest,
    write_midi_file,
    write_single_track_midi,
)


class TestNoteEvent(unittest.TestCase):
    """Test the NoteEvent dataclass."""

    def test_defaults(self):
        e = NoteEvent(pitch=60, start_beat=0.0, duration_beats=1.0)
        self.assertEqual(e.velocity, 100)
        self.assertEqual(e.channel, 0)

    def test_start_ticks(self):
        e = NoteEvent(pitch=60, start_beat=2.0, duration_beats=1.0)
        self.assertEqual(e.start_ticks(480), 960)

    def test_duration_ticks(self):
        e = NoteEvent(pitch=60, start_beat=0.0, duration_beats=0.5)
        self.assertEqual(e.duration_ticks(480), 240)

    def test_duration_ticks_minimum_one(self):
        e = NoteEvent(pitch=60, start_beat=0.0, duration_beats=0.0)
        self.assertEqual(e.duration_ticks(480), 1)

    def test_pitch_preserved(self):
        e = NoteEvent(pitch=127, start_beat=0.0, duration_beats=1.0, velocity=64)
        self.assertEqual(e.pitch, 127)
        self.assertEqual(e.velocity, 64)


class TestProgressionToEvents(unittest.TestCase):
    """Test conversion from ChordProgression to NoteEvents."""

    def _make_prog(self):
        from engine.chord_progression import build_progression
        return build_progression(
            name="TEST",
            key="A",
            scale_type="minor",
            roman_sequence=["i", "VI", "VII", "i"],
            bpm=150,
        )

    def test_returns_list_of_note_events(self):
        prog = self._make_prog()
        events = progression_to_events(prog)
        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(e, NoteEvent) for e in events))

    def test_event_count_matches_chord_notes(self):
        prog = self._make_prog()
        events = progression_to_events(prog)
        expected = sum(len(c["midi_notes"]) for c in prog.chords)
        self.assertEqual(len(events), expected)

    def test_timing_is_sequential(self):
        prog = self._make_prog()
        events = progression_to_events(prog)
        starts = sorted(set(e.start_beat for e in events))
        self.assertEqual(starts[0], 0.0)
        self.assertTrue(len(starts) > 1)

    def test_velocity_override(self):
        prog = self._make_prog()
        events = progression_to_events(prog, velocity=80)
        self.assertTrue(all(e.velocity == 80 for e in events))

    def test_handles_dict_form(self):
        """Works with dict representation (from asdict/JSON)."""
        from dataclasses import asdict
        prog = self._make_prog()
        d = asdict(prog)
        events = progression_to_events(d)
        self.assertTrue(len(events) > 0)


class TestArpPatternToEvents(unittest.TestCase):
    """Test conversion from ArpPattern to NoteEvents."""

    def _make_pattern(self):
        from engine.trance_arp import fibonacci_rise_pattern
        return fibonacci_rise_pattern()

    def test_returns_note_events(self):
        pattern = self._make_pattern()
        events = arp_pattern_to_events(pattern, root_note=60)
        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(e, NoteEvent) for e in events))

    def test_event_count_matches_pattern_notes(self):
        pattern = self._make_pattern()
        events = arp_pattern_to_events(pattern, root_note=60)
        self.assertEqual(len(events), len(pattern.notes))

    def test_root_note_offset(self):
        pattern = self._make_pattern()
        events60 = arp_pattern_to_events(pattern, root_note=60)
        events48 = arp_pattern_to_events(pattern, root_note=48)
        # All pitches should be 12 lower
        for e60, e48 in zip(events60, events48):
            self.assertEqual(e60.pitch - e48.pitch, 12)

    def test_timing_is_sequential(self):
        pattern = self._make_pattern()
        events = arp_pattern_to_events(pattern, root_note=60)
        for i in range(1, len(events)):
            self.assertGreater(events[i].start_beat, events[i - 1].start_beat)

    def test_midi_range_clamped(self):
        pattern = self._make_pattern()
        events = arp_pattern_to_events(pattern, root_note=120)
        for e in events:
            self.assertGreaterEqual(e.pitch, 0)
            self.assertLessEqual(e.pitch, 127)


class TestMidiClipToEvents(unittest.TestCase):
    """Test conversion from Ableton MIDIClip to NoteEvents."""

    def test_converts_clip(self):
        from engine.ableton_live import generate_sub_bass_clip
        clip = generate_sub_bass_clip(root_note=33, bars=4)
        events = midi_clip_to_events(clip)
        self.assertTrue(len(events) > 0)
        self.assertTrue(all(isinstance(e, NoteEvent) for e in events))

    def test_pitch_preserved(self):
        from engine.ableton_live import generate_sub_bass_clip
        clip = generate_sub_bass_clip(root_note=33, bars=4)
        events = midi_clip_to_events(clip)
        self.assertTrue(all(e.pitch == 33 for e in events))

    def test_mid_bass_clip(self):
        from engine.ableton_live import generate_mid_bass_clip
        clip = generate_mid_bass_clip(root_note=45, bars=4)
        events = midi_clip_to_events(clip)
        self.assertTrue(len(events) > 0)


class TestRawMidiEventsToEvents(unittest.TestCase):
    """Test conversion from existing MIDI event dicts."""

    def test_chord_progression_format(self):
        raw = [
            {"tick": 0, "midi": 60, "velocity": 100, "duration_ticks": 480},
            {"tick": 480, "midi": 64, "velocity": 90, "duration_ticks": 480},
        ]
        events = raw_midi_events_to_events(raw, source="chord_progression")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].pitch, 60)
        self.assertAlmostEqual(events[0].start_beat, 0.0)
        self.assertAlmostEqual(events[1].start_beat, 1.0)

    def test_trance_arp_format(self):
        raw = [
            {"note": 57, "velocity": 100, "start_beat": 0.0, "duration_beat": 0.25},
            {"note": 60, "velocity": 80, "start_beat": 0.25, "duration_beat": 0.25},
        ]
        events = raw_midi_events_to_events(raw, source="trance_arp")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].pitch, 57)
        self.assertEqual(events[1].pitch, 60)


class TestEventsToTrack(unittest.TestCase):
    """Test NoteEvent list → mido MidiTrack conversion."""

    def _sample_events(self):
        return [
            NoteEvent(pitch=60, start_beat=0.0, duration_beats=1.0, velocity=100),
            NoteEvent(pitch=64, start_beat=1.0, duration_beats=1.0, velocity=90),
            NoteEvent(pitch=67, start_beat=2.0, duration_beats=1.0, velocity=80),
        ]

    def test_returns_midi_track(self):
        track = events_to_track(self._sample_events())
        self.assertIsInstance(track, mido.MidiTrack)

    def test_track_has_correct_note_count(self):
        track = events_to_track(self._sample_events())
        note_ons = [m for m in track if m.type == 'note_on']
        note_offs = [m for m in track if m.type == 'note_off']
        self.assertEqual(len(note_ons), 3)
        self.assertEqual(len(note_offs), 3)

    def test_track_name_set(self):
        track = events_to_track(self._sample_events(), track_name="MY_TRACK")
        name_msgs = [m for m in track if m.type == 'track_name']
        self.assertEqual(len(name_msgs), 1)
        self.assertEqual(name_msgs[0].name, "MY_TRACK")

    def test_program_change_included(self):
        track = events_to_track(self._sample_events(), program=38)
        pc_msgs = [m for m in track if m.type == 'program_change']
        self.assertEqual(len(pc_msgs), 1)
        self.assertEqual(pc_msgs[0].program, 38)

    def test_end_of_track_present(self):
        track = events_to_track(self._sample_events())
        last = track[-1]
        self.assertEqual(last.type, 'end_of_track')

    def test_delta_times_are_non_negative(self):
        track = events_to_track(self._sample_events())
        for msg in track:
            self.assertGreaterEqual(msg.time, 0)


class TestWriteMidiFile(unittest.TestCase):
    """Test MIDI file writing."""

    def _sample_events(self):
        return [
            NoteEvent(pitch=60, start_beat=0.0, duration_beats=1.0),
            NoteEvent(pitch=64, start_beat=1.0, duration_beats=1.0),
        ]

    def test_creates_file(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = write_midi_file(
                tracks=[("TEST", self._sample_events())],
                path=Path(td) / "test.mid",
                bpm=150,
            )
            self.assertTrue(path.exists())
            self.assertTrue(path.stat().st_size > 0)

    def test_multi_track(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tracks = [
                ("BASS", [NoteEvent(33, 0.0, 4.0)]),
                ("LEAD", [NoteEvent(60, 0.0, 1.0), NoteEvent(64, 1.0, 1.0)]),
            ]
            path = write_midi_file(tracks, Path(td) / "multi.mid", bpm=150)
            mid = mido.MidiFile(str(path))
            # 1 tempo track + 2 note tracks
            self.assertEqual(len(mid.tracks), 3)

    def test_file_is_valid_midi(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = write_midi_file(
                [("T", self._sample_events())],
                Path(td) / "valid.mid", bpm=120,
            )
            mid = mido.MidiFile(str(path))
            self.assertEqual(mid.type, 1)
            self.assertEqual(mid.ticks_per_beat, TICKS_PER_BEAT)

    def test_tempo_set_correctly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = write_midi_file(
                [("T", self._sample_events())],
                Path(td) / "tempo.mid", bpm=140,
            )
            mid = mido.MidiFile(str(path))
            tempo_msgs = [m for t in mid.tracks for m in t if m.type == 'set_tempo']
            self.assertEqual(len(tempo_msgs), 1)
            self.assertAlmostEqual(mido.tempo2bpm(tempo_msgs[0].tempo), 140.0, places=1)

    def test_single_track_convenience(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = write_single_track_midi(
                self._sample_events(),
                Path(td) / "single.mid",
                track_name="SOLO",
                bpm=150,
            )
            mid = mido.MidiFile(str(path))
            self.assertEqual(len(mid.tracks), 2)  # tempo + 1 note track


class TestExportProgressionMidi(unittest.TestCase):
    """Test high-level chord progression MIDI export."""

    def test_exports_weapon_dark(self):
        import tempfile

        from engine.chord_progression import ALL_PRESETS
        with tempfile.TemporaryDirectory() as td:
            prog = ALL_PRESETS["WEAPON_DARK"]()
            path = export_progression_midi(prog, out_dir=td)
            self.assertTrue(path.exists())
            mid = mido.MidiFile(str(path))
            note_ons = [m for t in mid.tracks for m in t if m.type == 'note_on']
            self.assertTrue(len(note_ons) > 0)

    def test_exports_all_presets(self):
        import tempfile

        from engine.chord_progression import ALL_PRESETS
        with tempfile.TemporaryDirectory() as td:
            for name, fn in ALL_PRESETS.items():
                prog = fn()
                path = export_progression_midi(prog, out_dir=td)
                self.assertTrue(path.exists(), f"{name} MIDI not created")

    def test_filename_contains_preset_name(self):
        import tempfile

        from engine.chord_progression import ALL_PRESETS
        with tempfile.TemporaryDirectory() as td:
            prog = ALL_PRESETS["EMOTIVE_RISE"]()
            path = export_progression_midi(prog, out_dir=td)
            self.assertIn("EMOTIVE_RISE", path.name)


class TestExportArpMidi(unittest.TestCase):
    """Test high-level arp pattern MIDI export."""

    def test_exports_fibonacci_rise(self):
        import tempfile

        from engine.trance_arp import fibonacci_rise_pattern
        with tempfile.TemporaryDirectory() as td:
            pattern = fibonacci_rise_pattern()
            path = export_arp_midi(pattern, out_dir=td, root_note=60, bpm=150)
            self.assertTrue(path.exists())
            mid = mido.MidiFile(str(path))
            note_ons = [m for t in mid.tracks for m in t if m.type == 'note_on']
            self.assertEqual(len(note_ons), 13)  # 13 Fibonacci steps

    def test_exports_all_patterns(self):
        import tempfile

        from engine.trance_arp import (
            fibonacci_rise_pattern,
            golden_gate_pattern,
            phi_spiral_pattern,
        )
        patterns = [fibonacci_rise_pattern(), phi_spiral_pattern(), golden_gate_pattern()]
        with tempfile.TemporaryDirectory() as td:
            for p in patterns:
                path = export_arp_midi(p, out_dir=td)
                self.assertTrue(path.exists(), f"{p.name} MIDI not created")


class TestExportClipMidi(unittest.TestCase):
    """Test Ableton clip → MIDI export."""

    def test_exports_sub_bass_clip(self):
        import tempfile

        from engine.ableton_live import generate_sub_bass_clip
        with tempfile.TemporaryDirectory() as td:
            clip = generate_sub_bass_clip(root_note=33, bars=4)
            path = export_clip_midi(clip, out_dir=td, bpm=150)
            self.assertTrue(path.exists())

    def test_exports_arp_clip(self):
        import tempfile

        from engine.ableton_live import generate_arp_clip
        with tempfile.TemporaryDirectory() as td:
            clip = generate_arp_clip(root_note=57, scale="minor", bars=4)
            path = export_clip_midi(clip, out_dir=td, bpm=150)
            self.assertTrue(path.exists())
            mid = mido.MidiFile(str(path))
            self.assertTrue(mid.length > 0)


class TestExportFullArrangement(unittest.TestCase):
    """Test full multi-track arrangement MIDI export."""

    def test_creates_multi_track_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = export_full_arrangement(out_dir=td, bpm=150, root_note=57)
            self.assertTrue(path.exists())
            mid = mido.MidiFile(str(path))
            # 1 tempo track + 6 note tracks
            self.assertEqual(len(mid.tracks), 7)

    def test_all_tracks_have_notes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = export_full_arrangement(out_dir=td, bpm=150)
            mid = mido.MidiFile(str(path))
            for i, track in enumerate(mid.tracks):
                if i == 0:
                    continue  # tempo track
                note_ons = [m for m in track if m.type == 'note_on']
                self.assertTrue(
                    len(note_ons) > 0,
                    f"Track {i} ({track.name}) has no notes",
                )

    def test_track_names_correct(self):
        import tempfile
        expected = {"DUBFORGE", "SUB_BASS", "MID_BASS", "ARP",
                    "CHORD_PROG", "FIB_ARP", "CHORD_STAB"}
        with tempfile.TemporaryDirectory() as td:
            path = export_full_arrangement(out_dir=td, bpm=150)
            mid = mido.MidiFile(str(path))
            names = {t.name for t in mid.tracks}
            self.assertEqual(names, expected)


class TestWriteManifest(unittest.TestCase):
    """Test JSON manifest sidecar writing."""

    def test_creates_json_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            midi_path = Path(td) / "test.mid"
            midi_path.touch()
            manifest_path = write_manifest(midi_path, {"type": "test", "bpm": 150})
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest_path.suffix, ".json")

    def test_manifest_content(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            midi_path = Path(td) / "test.mid"
            midi_path.touch()
            manifest_path = write_manifest(midi_path, {"type": "test", "key": "Am"})
            with open(manifest_path) as f:
                data = json.load(f)
            self.assertEqual(data["dubforge_module"], "MIDI_EXPORT")
            self.assertEqual(data["midi_file"], "test.mid")
            self.assertEqual(data["type"], "test")
            self.assertEqual(data["key"], "Am")
            self.assertEqual(data["ticks_per_beat"], TICKS_PER_BEAT)


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_ticks_per_beat(self):
        self.assertEqual(TICKS_PER_BEAT, 480)

    def test_default_bpm(self):
        self.assertEqual(DEFAULT_BPM, 150)

    def test_gm_programs_has_required_keys(self):
        required = {"sub_bass", "mid_bass", "lead", "pad", "arp", "chord", "strings"}
        self.assertTrue(required.issubset(GM_PROGRAMS.keys()))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and robustness."""

    def test_empty_events(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = write_single_track_midi(
                [], Path(td) / "empty.mid", track_name="EMPTY",
            )
            self.assertTrue(path.exists())
            mid = mido.MidiFile(str(path))
            self.assertEqual(len(mid.tracks), 2)

    def test_single_note(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            events = [NoteEvent(pitch=60, start_beat=0.0, duration_beats=4.0)]
            path = write_single_track_midi(
                events, Path(td) / "single.mid",
            )
            mid = mido.MidiFile(str(path))
            note_ons = [m for t in mid.tracks for m in t if m.type == 'note_on']
            self.assertEqual(len(note_ons), 1)

    def test_simultaneous_notes(self):
        """Multiple notes at the same time (chord)."""
        events = [
            NoteEvent(pitch=60, start_beat=0.0, duration_beats=2.0),
            NoteEvent(pitch=64, start_beat=0.0, duration_beats=2.0),
            NoteEvent(pitch=67, start_beat=0.0, duration_beats=2.0),
        ]
        track = events_to_track(events)
        note_ons = [m for m in track if m.type == 'note_on']
        self.assertEqual(len(note_ons), 3)
        # First note_on should have time=0 (delta from start)
        # They should all be close together
        total_delta = sum(m.time for m in track if m.type == 'note_on')
        self.assertEqual(total_delta, 0)  # all at beat 0

    def test_pitch_clamping(self):
        """Pitches outside 0-127 should be clamped."""
        events = progression_to_events({
            'chords': [{'midi_notes': [-5, 200], 'duration_beats': 4.0}]
        })
        self.assertEqual(events[0].pitch, 0)
        self.assertEqual(events[1].pitch, 127)


if __name__ == "__main__":
    unittest.main()
