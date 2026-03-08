"""Tests for engine.impact_hit — Impact Hit Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.impact_hit import (
    ALL_IMPACT_BANKS,
    ImpactPreset,
    cinematic_hit_bank,
    distorted_impact_bank,
    metal_crash_bank,
    reverse_hit_bank,
    sub_boom_bank,
    synthesize_cinematic_hit,
    synthesize_distorted_impact,
    synthesize_impact,
    synthesize_metal_crash,
    synthesize_reverse_hit,
    synthesize_sub_boom,
    write_impact_manifest,
)


class TestImpactPreset(unittest.TestCase):
    """Test ImpactPreset dataclass."""

    def test_defaults(self):
        p = ImpactPreset("test", "sub_boom")
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.frequency, 50.0)
        self.assertAlmostEqual(p.decay_s, 1.5)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = ImpactPreset("t", "metal_crash", duration_s=1.0, intensity=0.5)
        self.assertAlmostEqual(p.duration_s, 1.0)
        self.assertAlmostEqual(p.intensity, 0.5)


class TestSynthesizers(unittest.TestCase):
    """Test individual impact synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_sub_boom(self):
        p = ImpactPreset("t", "sub_boom", duration_s=0.5)
        self._assert_valid(synthesize_sub_boom(p))

    def test_metal_crash(self):
        p = ImpactPreset("t", "metal_crash", duration_s=0.5)
        self._assert_valid(synthesize_metal_crash(p))

    def test_cinematic_hit(self):
        p = ImpactPreset("t", "cinematic_hit", duration_s=0.5)
        self._assert_valid(synthesize_cinematic_hit(p))

    def test_distorted_impact(self):
        p = ImpactPreset("t", "distorted_impact", duration_s=0.5)
        self._assert_valid(synthesize_distorted_impact(p))

    def test_reverse_hit(self):
        p = ImpactPreset("t", "reverse_hit", duration_s=0.5)
        self._assert_valid(synthesize_reverse_hit(p))

    def test_router_all_types(self):
        for itype in ("sub_boom", "metal_crash", "cinematic_hit",
                      "distorted_impact", "reverse_hit"):
            p = ImpactPreset("t", itype, duration_s=0.3)
            signal = synthesize_impact(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = ImpactPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_impact(p)


class TestBanks(unittest.TestCase):
    """Test impact banks."""

    def test_sub_boom_bank(self):
        bank = sub_boom_bank()
        self.assertEqual(bank.name, "SUB_BOOMS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.impact_type, "sub_boom")

    def test_metal_crash_bank(self):
        bank = metal_crash_bank()
        self.assertEqual(bank.name, "METAL_CRASHES")
        self.assertEqual(len(bank.presets), 4)

    def test_cinematic_hit_bank(self):
        bank = cinematic_hit_bank()
        self.assertEqual(bank.name, "CINEMATIC_HITS")
        self.assertEqual(len(bank.presets), 4)

    def test_distorted_impact_bank(self):
        bank = distorted_impact_bank()
        self.assertEqual(bank.name, "DISTORTED_IMPACTS")
        self.assertEqual(len(bank.presets), 4)

    def test_reverse_hit_bank(self):
        bank = reverse_hit_bank()
        self.assertEqual(bank.name, "REVERSE_HITS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_IMPACT_BANKS), 8)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_IMPACT_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_impact(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_32(self):
        total = sum(len(fn().presets) for fn in ALL_IMPACT_BANKS.values())
        self.assertEqual(total, 32)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_impact_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 8)


if __name__ == "__main__":
    unittest.main()
