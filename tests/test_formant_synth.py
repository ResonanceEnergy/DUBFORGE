"""Tests for engine.formant_synth — Formant Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.formant_synth import (
    ALL_FORMANT_BANKS,
    FormantPreset,
    ah_formant_bank,
    ee_formant_bank,
    morph_formant_bank,
    oh_formant_bank,
    oo_formant_bank,
    synthesize_ah_formant,
    synthesize_ee_formant,
    synthesize_formant,
    synthesize_morph_formant,
    synthesize_oh_formant,
    synthesize_oo_formant,
    write_formant_manifest,
)


class TestFormantPreset(unittest.TestCase):
    """Test FormantPreset dataclass."""

    def test_defaults(self):
        p = FormantPreset("test", "ah")
        self.assertAlmostEqual(p.frequency, 110.0)
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.formant1, 800.0)
        self.assertAlmostEqual(p.formant2, 1200.0)
        self.assertAlmostEqual(p.bandwidth, 100.0)
        self.assertAlmostEqual(p.brightness, 0.6)
        self.assertAlmostEqual(p.attack_s, 0.05)
        self.assertAlmostEqual(p.release_s, 0.3)
        self.assertAlmostEqual(p.distortion, 0.0)
        self.assertAlmostEqual(p.vibrato_rate, 0.0)

    def test_custom_values(self):
        p = FormantPreset("t", "ee", duration_s=1.0, formant1=900.0)
        self.assertAlmostEqual(p.duration_s, 1.0)
        self.assertAlmostEqual(p.formant1, 900.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual formant synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_ah_formant(self):
        p = FormantPreset("t", "ah", duration_s=0.5)
        self._assert_valid(synthesize_ah_formant(p))

    def test_ee_formant(self):
        p = FormantPreset("t", "ee", duration_s=0.5)
        self._assert_valid(synthesize_ee_formant(p))

    def test_oh_formant(self):
        p = FormantPreset("t", "oh", duration_s=0.5)
        self._assert_valid(synthesize_oh_formant(p))

    def test_oo_formant(self):
        p = FormantPreset("t", "oo", duration_s=0.5)
        self._assert_valid(synthesize_oo_formant(p))

    def test_morph_formant(self):
        p = FormantPreset("t", "morph", duration_s=0.5)
        self._assert_valid(synthesize_morph_formant(p))

    def test_router_all_types(self):
        for ftype in ("ah", "ee", "oh", "oo", "morph"):
            p = FormantPreset("t", ftype, duration_s=0.3)
            signal = synthesize_formant(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = FormantPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_formant(p)


class TestBanks(unittest.TestCase):
    """Test formant banks."""

    def test_ah_formant_bank(self):
        bank = ah_formant_bank()
        self.assertEqual(bank.name, "AH_FORMANTS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.formant_type, "ah")

    def test_ee_formant_bank(self):
        bank = ee_formant_bank()
        self.assertEqual(bank.name, "EE_FORMANTS")
        self.assertEqual(len(bank.presets), 4)

    def test_oh_formant_bank(self):
        bank = oh_formant_bank()
        self.assertEqual(bank.name, "OH_FORMANTS")
        self.assertEqual(len(bank.presets), 4)

    def test_oo_formant_bank(self):
        bank = oo_formant_bank()
        self.assertEqual(bank.name, "OO_FORMANTS")
        self.assertEqual(len(bank.presets), 4)

    def test_morph_formant_bank(self):
        bank = morph_formant_bank()
        self.assertEqual(bank.name, "MORPH_FORMANTS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_FORMANT_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_FORMANT_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_formant(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_FORMANT_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_formant_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
