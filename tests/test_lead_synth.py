"""Tests for engine.lead_synth — Lead Sound Synthesizer."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.lead_synth import (
    ALL_LEAD_BANKS,
    LeadPreset,
    acid_lead_bank,
    fm_lead_bank,
    formant_lead_bank,
    pluck_lead_bank,
    pwm_lead_bank,
    saw_lead_bank,
    screech_lead_bank,
    supersaw_lead_bank,
    synthesize_acid_lead,
    synthesize_fm_lead,
    synthesize_formant_lead,
    synthesize_lead,
    synthesize_pluck_lead,
    synthesize_pwm_lead,
    synthesize_saw_lead,
    synthesize_screech_lead,
    synthesize_supersaw_lead,
    write_lead_manifest,
)


class TestLeadPreset(unittest.TestCase):
    """Test LeadPreset dataclass."""

    def test_defaults(self):
        p = LeadPreset("test", "screech", 440.0)
        self.assertEqual(p.duration_s, 0.5)
        self.assertAlmostEqual(p.attack_s, 0.01)
        self.assertAlmostEqual(p.release_s, 0.15)

    def test_custom_values(self):
        p = LeadPreset("t", "pluck", 880.0, duration_s=0.3,
                        distortion=0.5, fm_depth=3.0)
        self.assertAlmostEqual(p.distortion, 0.5)
        self.assertAlmostEqual(p.fm_depth, 3.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual lead synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_screech_lead(self):
        p = LeadPreset("t", "screech", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_screech_lead(p))

    def test_pluck_lead(self):
        p = LeadPreset("t", "pluck", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_pluck_lead(p))

    def test_fm_lead(self):
        p = LeadPreset("t", "fm_lead", 440.0, duration_s=0.2,
                        fm_ratio=2.0, fm_depth=3.0)
        self._assert_valid(synthesize_fm_lead(p))

    def test_supersaw_lead(self):
        p = LeadPreset("t", "supersaw", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_supersaw_lead(p))

    def test_acid_lead(self):
        p = LeadPreset("t", "acid", 440.0, duration_s=0.2,
                        filter_cutoff=0.8, distortion=0.3)
        self._assert_valid(synthesize_acid_lead(p))

    def test_saw_lead(self):
        p = LeadPreset("t", "saw", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_saw_lead(p))

    def test_pwm_lead(self):
        p = LeadPreset("t", "pwm", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_pwm_lead(p))

    def test_formant_lead(self):
        p = LeadPreset("t", "formant", 440.0, duration_s=0.2)
        self._assert_valid(synthesize_formant_lead(p))

    def test_router_all_types(self):
        for ltype in ("screech", "pluck", "fm_lead", "supersaw", "acid",
                      "saw", "pwm", "formant"):
            p = LeadPreset("t", ltype, 440.0, duration_s=0.2)
            signal = synthesize_lead(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = LeadPreset("t", "laser", 440.0)
        with self.assertRaises(ValueError):
            synthesize_lead(p)


class TestBanks(unittest.TestCase):
    """Test preset banks."""

    def test_screech_lead_bank(self):
        bank = screech_lead_bank()
        self.assertEqual(bank.name, "SCREECH_LEADS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.lead_type, "screech")

    def test_pluck_lead_bank(self):
        bank = pluck_lead_bank()
        self.assertEqual(bank.name, "PLUCK_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_fm_lead_bank(self):
        bank = fm_lead_bank()
        self.assertEqual(bank.name, "FM_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_supersaw_lead_bank(self):
        bank = supersaw_lead_bank()
        self.assertEqual(bank.name, "SUPERSAW_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_acid_lead_bank(self):
        bank = acid_lead_bank()
        self.assertEqual(bank.name, "ACID_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_saw_lead_bank(self):
        bank = saw_lead_bank()
        self.assertEqual(bank.name, "SAW_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_pwm_lead_bank(self):
        bank = pwm_lead_bank()
        self.assertEqual(bank.name, "PWM_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_formant_lead_bank(self):
        bank = formant_lead_bank()
        self.assertEqual(bank.name, "FORMANT_LEADS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_LEAD_BANKS), 10)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_LEAD_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_lead(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_40(self):
        total = sum(len(fn().presets) for fn in ALL_LEAD_BANKS.values())
        self.assertEqual(total, 40)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_LEAD_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_lead_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 10)


if __name__ == "__main__":
    unittest.main()
