"""Tests for engine.granular_synth — Granular Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.granular_synth import (
    ALL_GRANULAR_BANKS,
    GranularPreset,
    cloud_bank,
    freeze_bank,
    scatter_bank,
    shimmer_bank,
    stretch_bank,
    synthesize_cloud,
    synthesize_freeze,
    synthesize_granular,
    synthesize_scatter,
    synthesize_shimmer,
    synthesize_stretch,
    write_granular_manifest,
)


class TestGranularPreset(unittest.TestCase):
    """Test GranularPreset dataclass."""

    def test_defaults(self):
        p = GranularPreset("test", "cloud")
        self.assertAlmostEqual(p.duration_s, 4.0)
        self.assertAlmostEqual(p.grain_size_ms, 50.0)
        self.assertAlmostEqual(p.grain_density, 0.7)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = GranularPreset("t", "scatter", duration_s=2.0, grain_size_ms=25.0)
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.grain_size_ms, 25.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual granular synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_cloud(self):
        p = GranularPreset("t", "cloud", duration_s=0.5)
        self._assert_valid(synthesize_cloud(p))

    def test_scatter(self):
        p = GranularPreset("t", "scatter", duration_s=0.5)
        self._assert_valid(synthesize_scatter(p))

    def test_stretch(self):
        p = GranularPreset("t", "stretch", duration_s=0.5)
        self._assert_valid(synthesize_stretch(p))

    def test_freeze(self):
        p = GranularPreset("t", "freeze", duration_s=0.5)
        self._assert_valid(synthesize_freeze(p))

    def test_shimmer(self):
        p = GranularPreset("t", "shimmer", duration_s=0.5)
        self._assert_valid(synthesize_shimmer(p))

    def test_router_all_types(self):
        for gtype in ("cloud", "scatter", "stretch", "freeze", "shimmer"):
            p = GranularPreset("t", gtype, duration_s=0.3)
            signal = synthesize_granular(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = GranularPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_granular(p)


class TestBanks(unittest.TestCase):
    """Test granular banks."""

    def test_cloud_bank(self):
        bank = cloud_bank()
        self.assertEqual(bank.name, "CLOUD_GRAINS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.grain_type, "cloud")

    def test_scatter_bank(self):
        bank = scatter_bank()
        self.assertEqual(bank.name, "SCATTER_GRAINS")
        self.assertEqual(len(bank.presets), 4)

    def test_stretch_bank(self):
        bank = stretch_bank()
        self.assertEqual(bank.name, "STRETCH_GRAINS")
        self.assertEqual(len(bank.presets), 4)

    def test_freeze_bank(self):
        bank = freeze_bank()
        self.assertEqual(bank.name, "FREEZE_GRAINS")
        self.assertEqual(len(bank.presets), 4)

    def test_shimmer_bank(self):
        bank = shimmer_bank()
        self.assertEqual(bank.name, "SHIMMER_GRAINS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_GRANULAR_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_GRANULAR_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_granular(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_GRANULAR_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_granular_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
