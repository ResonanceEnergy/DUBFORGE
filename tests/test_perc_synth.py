"""Tests for engine.perc_synth — Percussion One-Shot Synthesizer."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.perc_synth import (
    ALL_PERC_BANKS,
    PercPreset,
    clap_bank,
    hat_bank,
    kick_bank,
    rim_bank,
    snare_bank,
    synthesize_clap,
    synthesize_hat,
    synthesize_kick,
    synthesize_perc,
    synthesize_rim,
    synthesize_snare,
    write_perc_manifest,
)


class TestPercPreset(unittest.TestCase):
    """Test PercPreset dataclass."""

    def test_defaults(self):
        p = PercPreset("test", "kick")
        self.assertAlmostEqual(p.duration_s, 0.3)
        self.assertAlmostEqual(p.decay_s, 0.15)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = PercPreset("t", "snare", duration_s=0.5, distortion=0.8)
        self.assertAlmostEqual(p.distortion, 0.8)
        self.assertAlmostEqual(p.duration_s, 0.5)


class TestSynthesizers(unittest.TestCase):
    """Test individual percussion synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_kick(self):
        p = PercPreset("t", "kick", duration_s=0.2)
        self._assert_valid(synthesize_kick(p))

    def test_snare(self):
        p = PercPreset("t", "snare", duration_s=0.2)
        self._assert_valid(synthesize_snare(p))

    def test_clap(self):
        p = PercPreset("t", "clap", duration_s=0.2)
        self._assert_valid(synthesize_clap(p))

    def test_hat(self):
        p = PercPreset("t", "hat", duration_s=0.2)
        self._assert_valid(synthesize_hat(p))

    def test_rim(self):
        p = PercPreset("t", "rim", duration_s=0.2)
        self._assert_valid(synthesize_rim(p))

    def test_router_all_types(self):
        for ptype in ("kick", "snare", "clap", "hat", "rim"):
            p = PercPreset("t", ptype, duration_s=0.15)
            signal = synthesize_perc(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = PercPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_perc(p)


class TestBanks(unittest.TestCase):
    """Test preset banks."""

    def test_kick_bank(self):
        bank = kick_bank()
        self.assertEqual(bank.name, "KICKS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.perc_type, "kick")

    def test_snare_bank(self):
        bank = snare_bank()
        self.assertEqual(bank.name, "SNARES")
        self.assertEqual(len(bank.presets), 4)

    def test_clap_bank(self):
        bank = clap_bank()
        self.assertEqual(bank.name, "CLAPS")
        self.assertEqual(len(bank.presets), 4)

    def test_hat_bank(self):
        bank = hat_bank()
        self.assertEqual(bank.name, "HATS")
        self.assertEqual(len(bank.presets), 4)

    def test_rim_bank(self):
        bank = rim_bank()
        self.assertEqual(bank.name, "RIMS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_PERC_BANKS), 10)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_PERC_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_perc(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_28(self):
        total = sum(len(fn().presets) for fn in ALL_PERC_BANKS.values())
        self.assertEqual(total, 40)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_PERC_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_perc_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 10)


if __name__ == "__main__":
    unittest.main()
