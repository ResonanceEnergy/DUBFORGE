"""Tests for engine.wobble_bass — Wobble Bass Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.wobble_bass import (
    ALL_WOBBLE_BANKS,
    WobblePreset,
    classic_wobble_bank,
    fast_wobble_bank,
    growl_wobble_bank,
    slow_wobble_bank,
    synthesize_classic_wobble,
    synthesize_fast_wobble,
    synthesize_growl_wobble,
    synthesize_slow_wobble,
    synthesize_vowel_wobble,
    synthesize_wobble,
    vowel_wobble_bank,
    write_wobble_manifest,
)


class TestWobblePreset(unittest.TestCase):
    """Test WobblePreset dataclass."""

    def test_defaults(self):
        p = WobblePreset("test", "classic")
        self.assertAlmostEqual(p.frequency, 55.0)
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.lfo_rate, 4.0)
        self.assertAlmostEqual(p.lfo_depth, 0.8)
        self.assertAlmostEqual(p.filter_cutoff, 0.7)
        self.assertAlmostEqual(p.resonance, 0.5)
        self.assertAlmostEqual(p.attack_s, 0.01)
        self.assertAlmostEqual(p.release_s, 0.2)
        self.assertAlmostEqual(p.distortion, 0.0)
        self.assertAlmostEqual(p.sub_mix, 0.3)

    def test_custom_values(self):
        p = WobblePreset("t", "slow", duration_s=1.0, lfo_rate=2.0)
        self.assertAlmostEqual(p.duration_s, 1.0)
        self.assertAlmostEqual(p.lfo_rate, 2.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual wobble bass synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_classic_wobble(self):
        p = WobblePreset("t", "classic", duration_s=0.5)
        self._assert_valid(synthesize_classic_wobble(p))

    def test_slow_wobble(self):
        p = WobblePreset("t", "slow", duration_s=0.5)
        self._assert_valid(synthesize_slow_wobble(p))

    def test_fast_wobble(self):
        p = WobblePreset("t", "fast", duration_s=0.5)
        self._assert_valid(synthesize_fast_wobble(p))

    def test_vowel_wobble(self):
        p = WobblePreset("t", "vowel", duration_s=0.5)
        self._assert_valid(synthesize_vowel_wobble(p))

    def test_growl_wobble(self):
        p = WobblePreset("t", "growl", duration_s=0.5)
        self._assert_valid(synthesize_growl_wobble(p))

    def test_router_all_types(self):
        for wtype in ("classic", "slow", "fast", "vowel", "growl"):
            p = WobblePreset("t", wtype, duration_s=0.3)
            signal = synthesize_wobble(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = WobblePreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_wobble(p)


class TestBanks(unittest.TestCase):
    """Test wobble bass banks."""

    def test_classic_wobble_bank(self):
        bank = classic_wobble_bank()
        self.assertEqual(bank.name, "CLASSIC_WOBBLES")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.wobble_type, "classic")

    def test_slow_wobble_bank(self):
        bank = slow_wobble_bank()
        self.assertEqual(bank.name, "SLOW_WOBBLES")
        self.assertEqual(len(bank.presets), 4)

    def test_fast_wobble_bank(self):
        bank = fast_wobble_bank()
        self.assertEqual(bank.name, "FAST_WOBBLES")
        self.assertEqual(len(bank.presets), 4)

    def test_vowel_wobble_bank(self):
        bank = vowel_wobble_bank()
        self.assertEqual(bank.name, "VOWEL_WOBBLES")
        self.assertEqual(len(bank.presets), 4)

    def test_growl_wobble_bank(self):
        bank = growl_wobble_bank()
        self.assertEqual(bank.name, "GROWL_WOBBLES")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_WOBBLE_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_WOBBLE_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_wobble(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_WOBBLE_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_wobble_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
