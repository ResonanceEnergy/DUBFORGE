"""Tests for engine.bass_oneshot — Bass One-Shot Generator."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.bass_oneshot import (
    ALL_BASS_BANKS,
    BassPreset,
    fm_bass_bank,
    growl_bass_bank,
    reese_bank,
    square_bass_bank,
    sub_sine_bank,
    synthesize_bass,
    synthesize_fm_bass,
    synthesize_growl_bass,
    synthesize_reese,
    synthesize_square_bass,
    synthesize_sub_sine,
    write_bass_manifest,
)


class TestBassPreset(unittest.TestCase):
    """Test BassPreset dataclass."""

    def test_defaults(self):
        p = BassPreset("test", "sub_sine", 65.41)
        self.assertEqual(p.duration_s, 0.8)
        self.assertAlmostEqual(p.attack_s, 0.005)
        self.assertAlmostEqual(p.release_s, 0.2)
        self.assertEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = BassPreset("t", "growl", 65.41, distortion=0.8, fm_depth=2.0)
        self.assertAlmostEqual(p.distortion, 0.8)
        self.assertAlmostEqual(p.fm_depth, 2.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual bass synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_sub_sine(self):
        p = BassPreset("t", "sub_sine", 65.41, duration_s=0.2)
        self._assert_valid(synthesize_sub_sine(p))

    def test_reese(self):
        p = BassPreset("t", "reese", 65.41, duration_s=0.2, detune_cents=15)
        self._assert_valid(synthesize_reese(p))

    def test_fm(self):
        p = BassPreset("t", "fm", 65.41, duration_s=0.2,
                        fm_ratio=2.0, fm_depth=3.0)
        self._assert_valid(synthesize_fm_bass(p))

    def test_square(self):
        p = BassPreset("t", "square", 65.41, duration_s=0.2,
                        filter_cutoff=0.7)
        self._assert_valid(synthesize_square_bass(p))

    def test_growl(self):
        p = BassPreset("t", "growl", 65.41, duration_s=0.2, distortion=0.6)
        self._assert_valid(synthesize_growl_bass(p))

    def test_router_unknown(self):
        p = BassPreset("t", "laser", 100.0)
        with self.assertRaises(ValueError):
            synthesize_bass(p)


class TestBanks(unittest.TestCase):
    """Test preset banks."""

    def test_sub_sine_bank(self):
        bank = sub_sine_bank()
        self.assertEqual(bank.name, "SUB_SINE")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.bass_type, "sub_sine")

    def test_reese_bank(self):
        bank = reese_bank()
        self.assertEqual(bank.name, "REESE")
        self.assertEqual(len(bank.presets), 4)

    def test_fm_bass_bank(self):
        bank = fm_bass_bank()
        self.assertEqual(bank.name, "FM_BASS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertGreater(p.fm_depth, 0)

    def test_square_bass_bank(self):
        bank = square_bass_bank()
        self.assertEqual(bank.name, "SQUARE_BASS")
        self.assertEqual(len(bank.presets), 4)

    def test_growl_bass_bank(self):
        bank = growl_bass_bank()
        self.assertEqual(bank.name, "GROWL_BASS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertGreater(p.distortion, 0)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_BASS_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_BASS_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_bass(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_BASS_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_BASS_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_bass_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
