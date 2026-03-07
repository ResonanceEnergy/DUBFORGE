"""Tests for engine.pad_synth — Pad & Atmosphere Synthesizer."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.pad_synth import (
    ALL_PAD_BANKS,
    PadPreset,
    choir_pad_bank,
    dark_pad_bank,
    evolving_pad_bank,
    glass_pad_bank,
    granular_pad_bank,
    lush_pad_bank,
    shimmer_pad_bank,
    synthesize_choir_pad,
    synthesize_dark_pad,
    synthesize_evolving_pad,
    synthesize_glass_pad,
    synthesize_granular_pad,
    synthesize_lush_pad,
    synthesize_pad,
    synthesize_shimmer_pad,
    synthesize_warm_pad,
    warm_pad_bank,
    write_pad_manifest,
)


class TestPadPreset(unittest.TestCase):
    """Test PadPreset dataclass."""

    def test_defaults(self):
        p = PadPreset("test", "lush", 220.0)
        self.assertEqual(p.duration_s, 4.0)
        self.assertAlmostEqual(p.attack_s, 0.5)
        self.assertAlmostEqual(p.release_s, 1.0)
        self.assertEqual(p.detune_cents, 10.0)

    def test_custom_values(self):
        p = PadPreset("t", "dark", 110.0, duration_s=6.0,
                       brightness=0.3, lfo_rate=0.5)
        self.assertAlmostEqual(p.duration_s, 6.0)
        self.assertAlmostEqual(p.brightness, 0.3)


class TestSynthesizers(unittest.TestCase):
    """Test individual pad synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_lush_pad(self):
        p = PadPreset("t", "lush", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_lush_pad(p))

    def test_dark_pad(self):
        p = PadPreset("t", "dark", 110.0, duration_s=0.5)
        self._assert_valid(synthesize_dark_pad(p))

    def test_shimmer_pad(self):
        p = PadPreset("t", "shimmer", 330.0, duration_s=0.5)
        self._assert_valid(synthesize_shimmer_pad(p))

    def test_evolving_pad(self):
        p = PadPreset("t", "evolving", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_evolving_pad(p))

    def test_choir_pad(self):
        p = PadPreset("t", "choir", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_choir_pad(p))

    def test_glass_pad(self):
        p = PadPreset("t", "glass", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_glass_pad(p))

    def test_warm_pad(self):
        p = PadPreset("t", "warm", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_warm_pad(p))

    def test_granular_pad(self):
        p = PadPreset("t", "granular", 220.0, duration_s=0.5)
        self._assert_valid(synthesize_granular_pad(p))

    def test_router_all_types(self):
        for ptype in ("lush", "dark", "shimmer", "evolving", "choir",
                      "glass", "warm", "granular"):
            p = PadPreset("t", ptype, 220.0, duration_s=0.3)
            signal = synthesize_pad(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = PadPreset("t", "laser", 220.0)
        with self.assertRaises(ValueError):
            synthesize_pad(p)


class TestBanks(unittest.TestCase):
    """Test preset banks."""

    def test_lush_pad_bank(self):
        bank = lush_pad_bank()
        self.assertEqual(bank.name, "LUSH_PADS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.pad_type, "lush")

    def test_dark_pad_bank(self):
        bank = dark_pad_bank()
        self.assertEqual(bank.name, "DARK_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_shimmer_pad_bank(self):
        bank = shimmer_pad_bank()
        self.assertEqual(bank.name, "SHIMMER_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_evolving_pad_bank(self):
        bank = evolving_pad_bank()
        self.assertEqual(bank.name, "EVOLVING_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_choir_pad_bank(self):
        bank = choir_pad_bank()
        self.assertEqual(bank.name, "CHOIR_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_glass_pad_bank(self):
        bank = glass_pad_bank()
        self.assertEqual(bank.name, "GLASS_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_warm_pad_bank(self):
        bank = warm_pad_bank()
        self.assertEqual(bank.name, "WARM_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_granular_pad_bank(self):
        bank = granular_pad_bank()
        self.assertEqual(bank.name, "GRANULAR_PADS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_PAD_BANKS), 8)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_PAD_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_pad(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_32(self):
        total = sum(len(fn().presets) for fn in ALL_PAD_BANKS.values())
        self.assertEqual(total, 32)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_PAD_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_pad_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 8)


if __name__ == "__main__":
    unittest.main()
