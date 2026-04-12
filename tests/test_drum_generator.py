"""Tests for engine.drum_generator — Drum & Percussion Generator (v2.8.0)."""

import os
import tempfile
import unittest

import mido
import numpy as np

from engine.drum_generator import (
    ALL_DRUM_PATTERNS,
    DRUM_CHANNEL,
    DRUM_KIT,
    GM_DRUMS,
    SAMPLE_RATE,
    TICKS_PER_BEAT,
    DrumHit,
    DrumPattern,
    _env_exp_decay,
    _env_phi_transient,
    _write_oneshot_wav,
    export_drum_oneshots,
    fibonacci_accent_pattern,
    generate_breakbeat,
    generate_dubstep_build,
    generate_dubstep_drop,
    generate_fibonacci_fill,
    generate_halftime_groove,
    generate_intro_minimal,
    generate_riddim_minimal,
    generate_snare_roll_32nd,
    generate_tom_cascade_fill,
    generate_triplet_hat_groove,
    pattern_to_midi_track,
    phi_velocity,
    synth_clap,
    synth_crash,
    synth_hat_closed,
    synth_hat_open,
    synth_kick,
    synth_rim,
    synth_snare,
    synth_tom,
    write_drum_manifest,
    write_drum_midi,
    write_full_drum_arrangement,
)


class TestDrumHit(unittest.TestCase):
    """Test DrumHit dataclass."""

    def test_defaults(self):
        h = DrumHit(note=36, beat=0.0)
        self.assertEqual(h.velocity, 100)
        self.assertAlmostEqual(h.duration, 0.1)

    def test_custom_values(self):
        h = DrumHit(note=38, beat=2.0, velocity=120, duration=0.5)
        self.assertEqual(h.note, 38)
        self.assertAlmostEqual(h.beat, 2.0)
        self.assertEqual(h.velocity, 120)


class TestDrumPattern(unittest.TestCase):
    """Test DrumPattern dataclass."""

    def test_total_beats(self):
        p = DrumPattern(name="test", bars=4)
        self.assertEqual(p.total_beats, 16)

    def test_total_beats_custom_time_sig(self):
        p = DrumPattern(name="test", bars=2, time_sig=(3, 4))
        self.assertEqual(p.total_beats, 6)

    def test_empty_hits(self):
        p = DrumPattern(name="test")
        self.assertEqual(len(p.hits), 0)


class TestPhiVelocity(unittest.TestCase):
    """Test phi_velocity function."""

    def test_on_beat(self):
        v = phi_velocity(100, 0.0)
        self.assertEqual(v, 100)

    def test_off_beat_lower(self):
        v = phi_velocity(100, 0.5)
        self.assertLess(v, 100)
        self.assertGreater(v, 0)

    def test_ghost_notes(self):
        v = phi_velocity(100, 0.25)
        self.assertLess(v, phi_velocity(100, 0.5))

    def test_clamps_to_range(self):
        v = phi_velocity(127, 0.0, swing=5.0)
        self.assertLessEqual(v, 127)
        self.assertGreaterEqual(v, 1)


class TestFibonacciAccentPattern(unittest.TestCase):
    """Test fibonacci_accent_pattern."""

    def test_length(self):
        pattern = fibonacci_accent_pattern(16)
        self.assertEqual(len(pattern), 16)

    def test_accents_higher(self):
        pattern = fibonacci_accent_pattern(16, base_vel=80)
        self.assertTrue(any(v > 80 for v in pattern))
        self.assertTrue(all(v <= 127 for v in pattern))


class TestGMDrums(unittest.TestCase):
    """Test GM drum map."""

    def test_kick_note(self):
        self.assertEqual(GM_DRUMS["kick"], 36)

    def test_snare_note(self):
        self.assertEqual(GM_DRUMS["snare"], 38)

    def test_hat_closed(self):
        self.assertEqual(GM_DRUMS["hat_closed"], 42)

    def test_all_unique(self):
        values = list(GM_DRUMS.values())
        self.assertEqual(len(values), len(set(values)))


class TestPatternGenerators(unittest.TestCase):
    """Test all pattern generator functions."""

    def test_dubstep_drop(self):
        p = generate_dubstep_drop(4)
        self.assertEqual(p.name, "DUBSTEP_DROP")
        self.assertEqual(p.bars, 4)
        self.assertGreater(len(p.hits), 0)

    def test_dubstep_build(self):
        p = generate_dubstep_build(8)
        self.assertEqual(p.name, "DUBSTEP_BUILD")
        self.assertEqual(p.bars, 8)
        self.assertGreater(len(p.hits), 0)

    def test_halftime_groove(self):
        p = generate_halftime_groove(4)
        self.assertEqual(p.name, "HALFTIME_GROOVE")
        self.assertGreater(len(p.hits), 0)

    def test_fibonacci_fill(self):
        p = generate_fibonacci_fill(1)
        self.assertEqual(p.name, "FIBONACCI_FILL")
        self.assertGreater(len(p.hits), 0)

    def test_breakbeat(self):
        p = generate_breakbeat(4)
        self.assertEqual(p.name, "BREAKBEAT")
        self.assertGreater(len(p.hits), 0)

    def test_intro_minimal(self):
        p = generate_intro_minimal(8)
        self.assertEqual(p.name, "INTRO_MINIMAL")
        self.assertGreater(len(p.hits), 0)

    def test_snare_roll_32nd(self):
        p = generate_snare_roll_32nd(2)
        self.assertEqual(p.name, "SNARE_ROLL_32ND")
        self.assertEqual(p.bars, 2)
        self.assertGreater(len(p.hits), 0)
        # Should have many hits (32nd notes = 8 per beat * 8 beats = 64+ snares)
        snare_hits = [h for h in p.hits if h.note == GM_DRUMS["snare"]]
        self.assertGreaterEqual(len(snare_hits), 60)

    def test_snare_roll_velocity_crescendo(self):
        p = generate_snare_roll_32nd(2)
        snare_hits = [h for h in p.hits if h.note == GM_DRUMS["snare"]]
        # First hit should be quieter than last
        self.assertLess(snare_hits[0].velocity, snare_hits[-1].velocity)

    def test_tom_cascade_fill(self):
        p = generate_tom_cascade_fill(1)
        self.assertEqual(p.name, "TOM_CASCADE_FILL")
        self.assertEqual(p.bars, 1)
        self.assertGreater(len(p.hits), 0)
        # Should contain all three tom notes
        notes_used = {h.note for h in p.hits}
        self.assertIn(GM_DRUMS["tom_high"], notes_used)
        self.assertIn(GM_DRUMS["tom_mid"], notes_used)
        self.assertIn(GM_DRUMS["tom_low"], notes_used)

    def test_riddim_minimal(self):
        p = generate_riddim_minimal(4)
        self.assertEqual(p.name, "RIDDIM_MINIMAL")
        self.assertEqual(p.bars, 4)
        self.assertGreater(len(p.hits), 0)
        # Should be sparse — fewer hits than dubstep_drop
        drop = generate_dubstep_drop(4)
        self.assertLess(len(p.hits), len(drop.hits))

    def test_triplet_hat_groove(self):
        p = generate_triplet_hat_groove(4)
        self.assertEqual(p.name, "TRIPLET_HAT_GROOVE")
        self.assertEqual(p.bars, 4)
        self.assertGreater(len(p.hits), 0)
        # Should have triplet hats (12 per bar × 4 bars = 48 + kick/snare)
        hat_hits = [h for h in p.hits
                    if h.note in (GM_DRUMS["hat_closed"], GM_DRUMS["hat_open"])]
        self.assertGreaterEqual(len(hat_hits), 40)

    def test_all_patterns_registered(self):
        self.assertEqual(len(ALL_DRUM_PATTERNS), 142)
        for name, fn in ALL_DRUM_PATTERNS.items():
            p = fn()
            self.assertIsInstance(p, DrumPattern)
            self.assertGreater(len(p.hits), 0)

    def test_single_bar_works(self):
        """All generators should work with bars=1."""
        for name, fn in ALL_DRUM_PATTERNS.items():
            p = fn(bars=1)
            self.assertEqual(p.bars, 1)


class TestPatternToMidiTrack(unittest.TestCase):
    """Test MIDI track conversion."""

    def test_produces_track(self):
        p = generate_dubstep_drop(1)
        track = pattern_to_midi_track(p)
        self.assertIsInstance(track, mido.MidiTrack)
        self.assertGreater(len(track), 0)

    def test_has_track_name(self):
        p = generate_dubstep_drop(1)
        track = pattern_to_midi_track(p)
        names = [m for m in track if m.type == "track_name"]
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0].name, "DUBSTEP_DROP")

    def test_has_tempo(self):
        p = generate_dubstep_drop(1)
        track = pattern_to_midi_track(p, bpm=140.0)
        tempos = [m for m in track if m.type == "set_tempo"]
        self.assertEqual(len(tempos), 1)

    def test_channel_is_drums(self):
        p = generate_dubstep_drop(1)
        track = pattern_to_midi_track(p)
        note_msgs = [m for m in track if m.type in ("note_on", "note_off")]
        for msg in note_msgs:
            self.assertEqual(msg.channel, DRUM_CHANNEL)

    def test_has_end_of_track(self):
        p = generate_dubstep_drop(1)
        track = pattern_to_midi_track(p)
        self.assertEqual(track[-1].type, "end_of_track")  # type: ignore[union-attr]


class TestWriteDrumMidi(unittest.TestCase):
    """Test MIDI file writing."""

    def test_write_creates_file(self):
        p = generate_dubstep_drop(2)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_drums.mid")
            result = write_drum_midi(p, path)
            self.assertTrue(os.path.exists(result))

    def test_written_file_is_valid_midi(self):
        p = generate_halftime_groove(1)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mid")
            write_drum_midi(p, path)
            mid = mido.MidiFile(path)
            self.assertEqual(mid.ticks_per_beat, TICKS_PER_BEAT)

    def test_custom_bpm(self):
        p = generate_dubstep_drop(1)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mid")
            write_drum_midi(p, path, bpm=140.0)
            mid = mido.MidiFile(path)
            tempos = [m for track in mid.tracks for m in track if m.type == "set_tempo"]
            self.assertEqual(len(tempos), 1)


class TestWriteFullArrangement(unittest.TestCase):
    """Test full drum arrangement writing."""

    def test_multi_track_file(self):
        patterns = {name: fn() for name, fn in ALL_DRUM_PATTERNS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "full.mid")
            write_full_drum_arrangement(patterns, path)
            mid = mido.MidiFile(path)
            self.assertEqual(mid.type, 1)
            self.assertGreater(len(mid.tracks), 1)

    def test_creates_parent_dirs(self):
        patterns = {"dubstep_drop": generate_dubstep_drop()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "test.mid")
            write_full_drum_arrangement(patterns, path)
            self.assertTrue(os.path.exists(path))


class TestWriteDrumManifest(unittest.TestCase):
    """Test manifest generation."""

    def test_writes_json(self):
        patterns = {"drop": generate_dubstep_drop()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_drum_manifest(patterns, tmpdir)
            self.assertTrue(os.path.exists(path))
            import json
            with open(path) as f:
                data = json.load(f)
            self.assertIn("patterns", data)
            self.assertIn("drop", data["patterns"])


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO SYNTHESIS TESTS (v2.8.0)
# ═══════════════════════════════════════════════════════════════════════════


class TestEnvelopes(unittest.TestCase):
    """Test envelope generators."""

    def test_exp_decay_shape(self):
        env = _env_exp_decay(5000, decay_ms=100)
        self.assertEqual(len(env), 5000)
        self.assertAlmostEqual(env[0], 1.0, places=2)
        # Should decay toward 0 at the end
        self.assertLess(env[4409], 0.01)

    def test_exp_decay_all_positive(self):
        env = _env_exp_decay(500, decay_ms=50)
        self.assertTrue(np.all(env >= 0))

    def test_phi_transient_attack_then_decay(self):
        env = _env_phi_transient(2000, attack_ms=5, decay_ms=50)
        self.assertEqual(len(env), 2000)
        # Peak should be near the attack/decay boundary
        peak_idx = np.argmax(env)
        self.assertGreater(peak_idx, 0)

    def test_phi_transient_non_negative(self):
        env = _env_phi_transient(1000, attack_ms=2, decay_ms=100)
        self.assertTrue(np.all(env >= 0))


class TestSynthKick(unittest.TestCase):
    """Test kick drum synthesis."""

    def test_returns_array(self):
        audio = synth_kick()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_duration(self):
        audio = synth_kick(decay_ms=300)
        expected_samples = int(300 * SAMPLE_RATE / 1000)
        self.assertEqual(len(audio), expected_samples)

    def test_finite_values(self):
        audio = synth_kick()
        self.assertTrue(np.all(np.isfinite(audio)))

    def test_drive_affects_output(self):
        clean = synth_kick(drive=0.0)
        driven = synth_kick(drive=0.8)
        self.assertFalse(np.allclose(clean, driven))

    def test_custom_freq(self):
        audio = synth_kick(freq=40.0, punch_freq=180.0)
        self.assertGreater(len(audio), 0)


class TestSynthSnare(unittest.TestCase):
    """Test snare drum synthesis."""

    def test_returns_array(self):
        audio = synth_snare()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_noise_mix_range(self):
        pure_tone = synth_snare(noise_mix=0.0)
        pure_noise = synth_snare(noise_mix=1.0)
        self.assertFalse(np.allclose(pure_tone, pure_noise))

    def test_duration(self):
        audio = synth_snare(decay_ms=200)
        expected = int(200 * SAMPLE_RATE / 1000)
        self.assertEqual(len(audio), expected)


class TestSynthHats(unittest.TestCase):
    """Test hi-hat synthesis."""

    def test_closed_hat(self):
        audio = synth_hat_closed()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_open_hat(self):
        audio = synth_hat_open()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_open_longer_than_closed(self):
        closed = synth_hat_closed()
        opened = synth_hat_open()
        self.assertGreater(len(opened), len(closed))

    def test_finite(self):
        self.assertTrue(np.all(np.isfinite(synth_hat_closed())))
        self.assertTrue(np.all(np.isfinite(synth_hat_open())))


class TestSynthClap(unittest.TestCase):
    """Test clap synthesis."""

    def test_returns_array(self):
        audio = synth_clap()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_layers_parameter(self):
        two = synth_clap(n_layers=2)
        five = synth_clap(n_layers=5)
        self.assertFalse(np.allclose(two, five))

    def test_finite(self):
        self.assertTrue(np.all(np.isfinite(synth_clap())))


class TestSynthTom(unittest.TestCase):
    """Test tom synthesis."""

    def test_low_tom(self):
        audio = synth_tom(freq=80.0)
        self.assertGreater(len(audio), 0)

    def test_mid_tom(self):
        audio = synth_tom(freq=120.0)
        self.assertGreater(len(audio), 0)

    def test_high_tom(self):
        audio = synth_tom(freq=180.0)
        self.assertGreater(len(audio), 0)

    def test_different_freqs_differ(self):
        low = synth_tom(freq=80.0, decay_ms=200)
        high = synth_tom(freq=180.0, decay_ms=200)
        self.assertFalse(np.allclose(low, high))


class TestSynthRim(unittest.TestCase):
    """Test rim shot synthesis."""

    def test_returns_array(self):
        audio = synth_rim()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_short_duration(self):
        audio = synth_rim(decay_ms=50)
        expected = int(50 * SAMPLE_RATE / 1000)
        self.assertEqual(len(audio), expected)


class TestSynthCrash(unittest.TestCase):
    """Test crash cymbal synthesis."""

    def test_returns_array(self):
        audio = synth_crash()
        self.assertIsInstance(audio, np.ndarray)
        self.assertGreater(len(audio), 0)

    def test_long_decay(self):
        audio = synth_crash(decay_ms=1500)
        # Should be ~1.5 seconds
        self.assertGreater(len(audio), SAMPLE_RATE)

    def test_finite(self):
        self.assertTrue(np.all(np.isfinite(synth_crash())))


class TestDrumKit(unittest.TestCase):
    """Test DRUM_KIT dictionary and all presets."""

    def test_all_entries_callable(self):
        for name, (synth_fn, kwargs) in DRUM_KIT.items():
            audio = synth_fn(**kwargs)
            self.assertIsInstance(audio, np.ndarray, f"Failed for {name}")
            self.assertGreater(len(audio), 0, f"Empty audio for {name}")

    def test_kit_size(self):
        self.assertEqual(len(DRUM_KIT), 16)

    def test_all_finite(self):
        for name, (synth_fn, kwargs) in DRUM_KIT.items():
            audio = synth_fn(**kwargs)
            self.assertTrue(np.all(np.isfinite(audio)), f"Non-finite in {name}")


class TestWriteOneshotWav(unittest.TestCase):
    """Test WAV file writer."""

    def test_writes_file(self):
        audio = synth_kick()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_kick.wav")
            result = _write_oneshot_wav(path, audio)
            self.assertTrue(os.path.exists(result))
            self.assertTrue(result.endswith(".wav"))

    def test_file_size_reasonable(self):
        audio = synth_kick(decay_ms=300)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "kick.wav")
            _write_oneshot_wav(path, audio)
            size = os.path.getsize(path)
            # 300ms × 44100 × 2 bytes ≈ 26460, plus header
            self.assertGreater(size, 20000)

    def test_creates_parent_dirs(self):
        audio = synth_snare()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "snare.wav")
            result = _write_oneshot_wav(path, audio)
            self.assertTrue(os.path.exists(result))


class TestExportDrumOneshots(unittest.TestCase):
    """Test bulk drum one-shot export."""

    def test_exports_all_kit_pieces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_drum_oneshots(out_dir=tmpdir)
            self.assertEqual(len(paths), len(DRUM_KIT))
            for path in paths:
                self.assertTrue(os.path.exists(path))
                self.assertTrue(path.endswith(".wav"))

    def test_filenames_uppercase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_drum_oneshots(out_dir=tmpdir)
            for path in paths:
                basename = os.path.basename(path)
                self.assertTrue(basename.startswith("DRUM_"))


if __name__ == "__main__":
    unittest.main()
