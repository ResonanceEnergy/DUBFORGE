"""Tests for engine.fx_generator — FX Generator (Risers/Impacts/Sub Drops)."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.fx_generator import (
    ALL_FX_BANKS,
    FXPreset,
    impact_presets,
    riser_presets,
    subdrop_presets,
    synthesize_fx,
    synthesize_impact,
    synthesize_riser,
    synthesize_subdrop,
    write_fx_manifest,
)


class TestFXPreset(unittest.TestCase):
    """Test FXPreset dataclass."""

    def test_riser_defaults(self):
        p = FXPreset("test", "riser", 2.0)
        self.assertEqual(p.start_freq, 200.0)
        self.assertEqual(p.end_freq, 12000.0)
        self.assertAlmostEqual(p.reverb_amount, 0.3)

    def test_impact_defaults(self):
        p = FXPreset("test", "impact", 1.0)
        self.assertEqual(p.sub_freq, 50.0)
        self.assertAlmostEqual(p.transient_brightness, 0.8)

    def test_subdrop_defaults(self):
        p = FXPreset("test", "subdrop", 1.0)
        self.assertEqual(p.drop_start_freq, 120.0)
        self.assertEqual(p.drop_end_freq, 25.0)


class TestSynthesizeRiser(unittest.TestCase):
    """Test riser synthesis."""

    def test_produces_signal(self):
        p = FXPreset("r", "riser", 1.0, start_freq=200, end_freq=8000)
        signal = synthesize_riser(p)
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)

    def test_normalized(self):
        p = FXPreset("r", "riser", 0.5)
        signal = synthesize_riser(p)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_duration_affects_length(self):
        short = FXPreset("s", "riser", 0.5)
        long = FXPreset("l", "riser", 2.0)
        s_sig = synthesize_riser(short)
        l_sig = synthesize_riser(long)
        self.assertGreater(len(l_sig), len(s_sig))

    def test_with_distortion(self):
        p = FXPreset("r", "riser", 0.5, distortion=0.5)
        signal = synthesize_riser(p)
        self.assertGreater(len(signal), 0)

    def test_crescendo_shape(self):
        """Riser should get louder toward the end."""
        p = FXPreset("r", "riser", 1.0)
        signal = synthesize_riser(p)
        n = len(signal)
        first_quarter_rms = np.sqrt(np.mean(signal[:n // 4] ** 2))
        last_quarter_rms = np.sqrt(np.mean(signal[3 * n // 4:] ** 2))
        self.assertGreater(last_quarter_rms, first_quarter_rms)


class TestSynthesizeImpact(unittest.TestCase):
    """Test impact synthesis."""

    def test_produces_signal(self):
        p = FXPreset("i", "impact", 1.0)
        signal = synthesize_impact(p)
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)

    def test_normalized(self):
        p = FXPreset("i", "impact", 0.8)
        signal = synthesize_impact(p)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_transient_at_start(self):
        """Impact should have most energy at the beginning."""
        p = FXPreset("i", "impact", 1.5)
        signal = synthesize_impact(p)
        n = len(signal)
        first_rms = np.sqrt(np.mean(signal[:n // 4] ** 2))
        last_rms = np.sqrt(np.mean(signal[3 * n // 4:] ** 2))
        self.assertGreater(first_rms, last_rms)

    def test_with_distortion(self):
        p = FXPreset("i", "impact", 0.5, distortion=0.8)
        signal = synthesize_impact(p)
        self.assertGreater(len(signal), 0)

    def test_different_sub_freq(self):
        low = FXPreset("l", "impact", 1.0, sub_freq=30)
        high = FXPreset("h", "impact", 1.0, sub_freq=80)
        l_sig = synthesize_impact(low)
        h_sig = synthesize_impact(high)
        # Different sub freqs should produce different signals
        self.assertFalse(np.allclose(l_sig, h_sig))


class TestSynthesizeSubdrop(unittest.TestCase):
    """Test sub drop synthesis."""

    def test_produces_signal(self):
        p = FXPreset("sd", "subdrop", 1.0)
        signal = synthesize_subdrop(p)
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)

    def test_normalized(self):
        p = FXPreset("sd", "subdrop", 0.8)
        signal = synthesize_subdrop(p)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_duration(self):
        p = FXPreset("sd", "subdrop", 2.0)
        signal = synthesize_subdrop(p)
        expected_samples = int(2.0 * 44100)
        self.assertEqual(len(signal), expected_samples)

    def test_with_dirty_distortion(self):
        p = FXPreset("sd", "subdrop", 0.5, distortion=0.8)
        signal = synthesize_subdrop(p)
        self.assertGreater(len(signal), 0)


class TestSynthesizeFXRouter(unittest.TestCase):
    """Test the synthesize_fx routing function."""

    def test_routes_riser(self):
        p = FXPreset("r", "riser", 0.5)
        signal = synthesize_fx(p)
        self.assertGreater(len(signal), 0)

    def test_routes_impact(self):
        p = FXPreset("i", "impact", 0.5)
        signal = synthesize_fx(p)
        self.assertGreater(len(signal), 0)

    def test_routes_subdrop(self):
        p = FXPreset("sd", "subdrop", 0.5)
        signal = synthesize_fx(p)
        self.assertGreater(len(signal), 0)

    def test_unknown_type_raises(self):
        p = FXPreset("x", "unknown", 0.5)
        with self.assertRaises(ValueError):
            synthesize_fx(p)


class TestFXBankPresets(unittest.TestCase):
    """Test preset bank generators."""

    def test_riser_presets(self):
        bank = riser_presets()
        self.assertEqual(bank.name, "RISERS")
        self.assertEqual(len(bank.presets), 3)
        for p in bank.presets:
            self.assertEqual(p.fx_type, "riser")

    def test_impact_presets(self):
        bank = impact_presets()
        self.assertEqual(bank.name, "IMPACTS")
        self.assertEqual(len(bank.presets), 3)
        for p in bank.presets:
            self.assertEqual(p.fx_type, "impact")

    def test_subdrop_presets(self):
        bank = subdrop_presets()
        self.assertEqual(bank.name, "SUB_DROPS")
        self.assertEqual(len(bank.presets), 3)
        for p in bank.presets:
            self.assertEqual(p.fx_type, "subdrop")

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_FX_BANKS), 8)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_FX_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_fx(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")


class TestFXManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_FX_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_fx_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 8)

    def test_manifest_structure(self):
        banks = {"risers": riser_presets()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_fx_manifest(banks, tmpdir)
            with open(path) as f:
                data = json.load(f)
            riser_data = data["banks"]["risers"]
            self.assertEqual(riser_data["name"], "RISERS")
            self.assertEqual(riser_data["preset_count"], 3)
            self.assertEqual(len(riser_data["presets"]), 3)


if __name__ == "__main__":
    unittest.main()
