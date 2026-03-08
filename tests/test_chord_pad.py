"""Tests for engine.chord_pad — Chord Pad Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.chord_pad import (
    ALL_CHORD_PAD_BANKS,
    ChordPadPreset,
    dim_pad_bank,
    major7_pad_bank,
    minor7_pad_bank,
    power_pad_bank,
    sus4_pad_bank,
    synthesize_chord_pad,
    synthesize_dim_pad,
    synthesize_major7_pad,
    synthesize_minor7_pad,
    synthesize_power_pad,
    synthesize_sus4_pad,
    write_chord_pad_manifest,
)


class TestChordPadPreset(unittest.TestCase):
    """Test ChordPadPreset dataclass."""

    def test_defaults(self):
        p = ChordPadPreset("test", "minor7")
        self.assertAlmostEqual(p.duration_s, 5.0)
        self.assertAlmostEqual(p.detune_cents, 8.0)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = ChordPadPreset("t", "sus4", duration_s=3.0, brightness=0.8)
        self.assertAlmostEqual(p.duration_s, 3.0)
        self.assertAlmostEqual(p.brightness, 0.8)


class TestSynthesizers(unittest.TestCase):
    """Test individual chord pad synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_minor7(self):
        p = ChordPadPreset("t", "minor7", duration_s=0.5)
        self._assert_valid(synthesize_minor7_pad(p))

    def test_major7(self):
        p = ChordPadPreset("t", "major7", duration_s=0.5)
        self._assert_valid(synthesize_major7_pad(p))

    def test_sus4(self):
        p = ChordPadPreset("t", "sus4", duration_s=0.5)
        self._assert_valid(synthesize_sus4_pad(p))

    def test_dim(self):
        p = ChordPadPreset("t", "dim", duration_s=0.5)
        self._assert_valid(synthesize_dim_pad(p))

    def test_power(self):
        p = ChordPadPreset("t", "power", duration_s=0.5)
        self._assert_valid(synthesize_power_pad(p))

    def test_router_all_types(self):
        for ctype in ("minor7", "major7", "sus4", "dim", "power"):
            p = ChordPadPreset("t", ctype, duration_s=0.3)
            signal = synthesize_chord_pad(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = ChordPadPreset("t", "augmented")
        with self.assertRaises(ValueError):
            synthesize_chord_pad(p)


class TestBanks(unittest.TestCase):
    """Test chord pad banks."""

    def test_minor7_pad_bank(self):
        bank = minor7_pad_bank()
        self.assertEqual(bank.name, "MINOR7_PADS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.chord_type, "minor7")

    def test_major7_pad_bank(self):
        bank = major7_pad_bank()
        self.assertEqual(bank.name, "MAJOR7_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_sus4_pad_bank(self):
        bank = sus4_pad_bank()
        self.assertEqual(bank.name, "SUS4_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_dim_pad_bank(self):
        bank = dim_pad_bank()
        self.assertEqual(bank.name, "DIM_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_power_pad_bank(self):
        bank = power_pad_bank()
        self.assertEqual(bank.name, "POWER_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_CHORD_PAD_BANKS), 8)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_CHORD_PAD_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_chord_pad(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_32(self):
        total = sum(len(fn().presets) for fn in ALL_CHORD_PAD_BANKS.values())
        self.assertEqual(total, 32)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_chord_pad_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 8)


if __name__ == "__main__":
    unittest.main()
