"""Tests for engine.pluck_synth — Pluck One-Shot Synthesizer."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.pluck_synth import (
    ALL_PLUCK_BANKS,
    PluckBank,
    PluckPreset,
    bell_pluck_bank,
    harp_pluck_bank,
    key_pluck_bank,
    marimba_pluck_bank,
    string_pluck_bank,
    synthesize_bell_pluck,
    synthesize_harp_pluck,
    synthesize_key_pluck,
    synthesize_marimba_pluck,
    synthesize_pluck,
    synthesize_string_pluck,
    write_pluck_manifest,
)


class TestPluckPreset(unittest.TestCase):
    """Test PluckPreset dataclass."""

    def test_defaults(self):
        p = PluckPreset("test", "string")
        self.assertEqual(p.name, "test")
        self.assertEqual(p.pluck_type, "string")
        self.assertAlmostEqual(p.frequency, 220.0)
        self.assertAlmostEqual(p.duration_s, 1.5)
        self.assertAlmostEqual(p.attack_s, 0.001)
        self.assertAlmostEqual(p.brightness, 0.7)

    def test_custom_values(self):
        p = PluckPreset("custom", "bell", frequency=440.0,
                        duration_s=2.0, damping=0.8, distortion=0.3)
        self.assertAlmostEqual(p.frequency, 440.0)
        self.assertAlmostEqual(p.damping, 0.8)
        self.assertAlmostEqual(p.distortion, 0.3)


class TestSynthesizers(unittest.TestCase):
    """Test individual pluck synthesizers produce valid signals."""

    def _assert_valid(self, signal, preset):
        self.assertIsInstance(signal, np.ndarray)
        expected_len = int(preset.duration_s * 44100)
        self.assertEqual(len(signal), expected_len)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)
        self.assertGreater(np.max(np.abs(signal)), 0.01)

    def test_string_pluck(self):
        p = PluckPreset("t", "string", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_string_pluck(p), p)

    def test_bell_pluck(self):
        p = PluckPreset("t", "bell", 440.0, duration_s=0.5)
        self._assert_valid(synthesize_bell_pluck(p), p)

    def test_key_pluck(self):
        p = PluckPreset("t", "key", 330.0, duration_s=0.5)
        self._assert_valid(synthesize_key_pluck(p), p)

    def test_harp_pluck(self):
        p = PluckPreset("t", "harp", 261.63, duration_s=0.5)
        self._assert_valid(synthesize_harp_pluck(p), p)

    def test_marimba_pluck(self):
        p = PluckPreset("t", "marimba", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_marimba_pluck(p), p)

    def test_distortion_parameter(self):
        p = PluckPreset("t", "string", 220.0, duration_s=0.3, distortion=0.8)
        signal = synthesize_string_pluck(p)
        self._assert_valid(signal, p)

    def test_router_all_types(self):
        for pluck_type in ("string", "bell", "key", "harp", "marimba"):
            p = PluckPreset("t", pluck_type, duration_s=0.3)
            signal = synthesize_pluck(p)
            self.assertEqual(len(signal), int(0.3 * 44100))

    def test_router_unknown(self):
        p = PluckPreset("t", "invalid_type")
        with self.assertRaises(ValueError):
            synthesize_pluck(p)


class TestBanks(unittest.TestCase):
    """Test pluck preset banks."""

    def test_string_pluck_bank(self):
        bank = string_pluck_bank()
        self.assertEqual(bank.name, "STRING_PLUCKS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.pluck_type, "string")

    def test_bell_pluck_bank(self):
        bank = bell_pluck_bank()
        self.assertEqual(bank.name, "BELL_PLUCKS")
        self.assertEqual(len(bank.presets), 4)

    def test_key_pluck_bank(self):
        bank = key_pluck_bank()
        self.assertEqual(bank.name, "KEY_PLUCKS")
        self.assertEqual(len(bank.presets), 4)

    def test_harp_pluck_bank(self):
        bank = harp_pluck_bank()
        self.assertEqual(bank.name, "HARP_PLUCKS")
        self.assertEqual(len(bank.presets), 4)

    def test_marimba_pluck_bank(self):
        bank = marimba_pluck_bank()
        self.assertEqual(bank.name, "MARIMBA_PLUCKS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_PLUCK_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_PLUCK_BANKS.items():
            bank = gen_fn()
            self.assertIsInstance(bank, PluckBank)
            for preset in bank.presets:
                signal = synthesize_pluck(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_PLUCK_BANKS.values())
        self.assertEqual(total, 20)

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_PLUCK_BANKS.items():
            bank = fn()
            self.assertEqual(len(bank.presets), 4, f"{name} bank")


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = write_pluck_manifest(tmpdir)
            manifest_path = os.path.join(tmpdir, "analysis",
                                         "pluck_synth_manifest.json")
            self.assertTrue(os.path.exists(manifest_path))
            with open(manifest_path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
