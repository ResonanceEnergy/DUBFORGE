"""Tests for engine.vocal_chop — Vocal Chop Synthesizer."""

import json
import os
import tempfile
import unittest
import wave

import numpy as np

from engine.vocal_chop import (
    ALL_CHOP_BANKS,
    CHOP_NOTES,
    VOWEL_FORMANTS,
    VocalChop,
    drop_shout_chops,
    drop_vowel_chops,
    formant_filter,
    stutter_chops,
    synthesize_chop,
    write_chop_manifest,
    write_chop_midi_pattern,
    write_chop_wav,
)


class TestVowelFormants(unittest.TestCase):
    """Test formant data constants."""

    def test_five_vowels(self):
        self.assertEqual(len(VOWEL_FORMANTS), 5)
        for vowel in ("ah", "oh", "eh", "ee", "oo"):
            self.assertIn(vowel, VOWEL_FORMANTS)

    def test_three_formants_each(self):
        for vowel, formants in VOWEL_FORMANTS.items():
            self.assertEqual(len(formants), 3, f"{vowel} should have 3 formants")

    def test_formant_frequencies_positive(self):
        for vowel, formants in VOWEL_FORMANTS.items():
            for freq, bw in formants:
                self.assertGreater(freq, 0)
                self.assertGreater(bw, 0)


class TestChopNotes(unittest.TestCase):
    """Test note frequency map."""

    def test_has_common_notes(self):
        for note in ("C3", "A3", "C4"):
            self.assertIn(note, CHOP_NOTES)

    def test_frequencies_positive(self):
        for note, freq in CHOP_NOTES.items():
            self.assertGreater(freq, 0)

    def test_c4_higher_than_c3(self):
        self.assertGreater(CHOP_NOTES["C4"], CHOP_NOTES["C3"])


class TestVocalChopDataclass(unittest.TestCase):
    """Test VocalChop dataclass."""

    def test_defaults(self):
        c = VocalChop("test", "ah", "C3")
        self.assertAlmostEqual(c.duration_s, 0.25)
        self.assertEqual(c.stutter_count, 0)
        self.assertAlmostEqual(c.distortion, 0.0)

    def test_custom_values(self):
        c = VocalChop("x", "ee", "C4", 0.5, distortion=0.8, stutter_count=8)
        self.assertEqual(c.vowel, "ee")
        self.assertEqual(c.stutter_count, 8)


class TestFormantFilter(unittest.TestCase):
    """Test formant filtering."""

    def test_output_shape(self):
        signal = np.random.randn(4096)
        result = formant_filter(signal, "ah")
        self.assertEqual(len(result), len(signal))

    def test_normalized(self):
        signal = np.random.randn(4096)
        result = formant_filter(signal, "oh")
        self.assertLessEqual(np.max(np.abs(result)), 1.001)

    def test_all_vowels(self):
        signal = np.random.randn(2048)
        for vowel in VOWEL_FORMANTS:
            result = formant_filter(signal, vowel)
            self.assertEqual(len(result), len(signal))

    def test_formant_shift(self):
        signal = np.random.randn(4096)
        normal = formant_filter(signal, "ah", 0.0)
        shifted = formant_filter(signal, "ah", 5.0)
        # Shifted result should differ from normal
        self.assertFalse(np.allclose(normal, shifted))


class TestSynthesizeChop(unittest.TestCase):
    """Test chop synthesis."""

    def test_basic_chop(self):
        c = VocalChop("test", "ah", "C3", 0.2)
        signal = synthesize_chop(c)
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)

    def test_output_normalized(self):
        c = VocalChop("test", "eh", "A3", 0.3, distortion=0.5)
        signal = synthesize_chop(c)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_stutter_chop(self):
        c = VocalChop("stut", "oh", "E3", 0.4, stutter_count=6)
        signal = synthesize_chop(c)
        self.assertGreater(len(signal), 0)

    def test_all_vowels_synthesize(self):
        for vowel in VOWEL_FORMANTS:
            c = VocalChop(f"test_{vowel}", vowel, "C3", 0.15)
            signal = synthesize_chop(c)
            self.assertGreater(len(signal), 100)

    def test_duration_affects_length(self):
        short = VocalChop("s", "ah", "C3", 0.1)
        long = VocalChop("l", "ah", "C3", 0.5)
        s_sig = synthesize_chop(short)
        l_sig = synthesize_chop(long)
        self.assertGreater(len(l_sig), len(s_sig))


class TestWriteChopWav(unittest.TestCase):
    """Test WAV writing."""

    def test_creates_file(self):
        c = VocalChop("test", "ah", "C3", 0.2)
        signal = synthesize_chop(c)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_chop.wav")
            result = write_chop_wav(signal, path)
            self.assertTrue(os.path.exists(result))

    def test_valid_wav(self):
        c = VocalChop("test", "oh", "E3", 0.3)
        signal = synthesize_chop(c)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "chop.wav")
            write_chop_wav(signal, path)
            with wave.open(path, "r") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)

    def test_creates_parent_dirs(self):
        c = VocalChop("test", "ah", "C3", 0.1)
        signal = synthesize_chop(c)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "chop.wav")
            write_chop_wav(signal, path)
            self.assertTrue(os.path.exists(path))


class TestChopBankPresets(unittest.TestCase):
    """Test preset bank generators."""

    def test_drop_vowel_chops(self):
        bank = drop_vowel_chops()
        self.assertEqual(bank.name, "DROP_VOWEL_CHOPS")
        self.assertEqual(len(bank.chops), 5)

    def test_stutter_chops(self):
        bank = stutter_chops()
        self.assertEqual(bank.name, "STUTTER_CHOPS")
        self.assertEqual(len(bank.chops), 4)
        for c in bank.chops:
            self.assertGreater(c.stutter_count, 0)

    def test_drop_shout_chops(self):
        bank = drop_shout_chops()
        self.assertEqual(bank.name, "DROP_SHOUT_CHOPS")
        self.assertEqual(len(bank.chops), 3)
        for c in bank.chops:
            self.assertGreater(c.distortion, 0)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_CHOP_BANKS), 3)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_CHOP_BANKS.items():
            bank = gen_fn()
            for chop in bank.chops:
                signal = synthesize_chop(chop)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{chop.name}")


class TestChopMidiPattern(unittest.TestCase):
    """Test MIDI trigger pattern writing."""

    def test_writes_file(self):
        bank = drop_vowel_chops()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "chops.mid")
            result = write_chop_midi_pattern(bank, path)
            self.assertTrue(os.path.exists(result))

    def test_valid_midi(self):
        import mido
        bank = stutter_chops()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "chops.mid")
            write_chop_midi_pattern(bank, path)
            mid = mido.MidiFile(path)
            self.assertEqual(len(mid.tracks), 1)
            note_ons = [m for m in mid.tracks[0] if m.type == "note_on"]
            self.assertEqual(len(note_ons), len(bank.chops))


class TestChopManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_CHOP_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_chop_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 3)


if __name__ == "__main__":
    unittest.main()
