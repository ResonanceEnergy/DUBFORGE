"""Tests for engine.riser_synth — Riser Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.riser_synth import (
    ALL_RISER_BANKS,
    RiserPreset,
    filter_sweep_bank,
    harmonic_build_bank,
    noise_sweep_bank,
    pitch_rise_bank,
    reverse_swell_bank,
    synthesize_filter_sweep,
    synthesize_harmonic_build,
    synthesize_noise_sweep,
    synthesize_pitch_rise,
    synthesize_reverse_swell,
    synthesize_riser,
    write_riser_manifest,
)


class TestRiserPreset(unittest.TestCase):
    """Test RiserPreset dataclass."""

    def test_defaults(self):
        p = RiserPreset("test", "noise_sweep")
        self.assertAlmostEqual(p.duration_s, 4.0)
        self.assertAlmostEqual(p.start_freq, 100.0)
        self.assertAlmostEqual(p.end_freq, 4000.0)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = RiserPreset("t", "pitch_rise", duration_s=2.0, intensity=0.5)
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.intensity, 0.5)


class TestSynthesizers(unittest.TestCase):
    """Test individual riser synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_noise_sweep(self):
        p = RiserPreset("t", "noise_sweep", duration_s=0.5)
        self._assert_valid(synthesize_noise_sweep(p))

    def test_pitch_rise(self):
        p = RiserPreset("t", "pitch_rise", duration_s=0.5)
        self._assert_valid(synthesize_pitch_rise(p))

    def test_filter_sweep(self):
        p = RiserPreset("t", "filter_sweep", duration_s=0.5)
        self._assert_valid(synthesize_filter_sweep(p))

    def test_harmonic_build(self):
        p = RiserPreset("t", "harmonic_build", duration_s=0.5)
        self._assert_valid(synthesize_harmonic_build(p))

    def test_reverse_swell(self):
        p = RiserPreset("t", "reverse_swell", duration_s=0.5)
        self._assert_valid(synthesize_reverse_swell(p))

    def test_router_all_types(self):
        for rtype in ("noise_sweep", "pitch_rise", "filter_sweep",
                      "harmonic_build", "reverse_swell"):
            p = RiserPreset("t", rtype, duration_s=0.3)
            signal = synthesize_riser(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = RiserPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_riser(p)


class TestBanks(unittest.TestCase):
    """Test riser banks."""

    def test_noise_sweep_bank(self):
        bank = noise_sweep_bank()
        self.assertEqual(bank.name, "NOISE_SWEEPS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.riser_type, "noise_sweep")

    def test_pitch_rise_bank(self):
        bank = pitch_rise_bank()
        self.assertEqual(bank.name, "PITCH_RISES")
        self.assertEqual(len(bank.presets), 4)

    def test_filter_sweep_bank(self):
        bank = filter_sweep_bank()
        self.assertEqual(bank.name, "FILTER_SWEEPS")
        self.assertEqual(len(bank.presets), 4)

    def test_harmonic_build_bank(self):
        bank = harmonic_build_bank()
        self.assertEqual(bank.name, "HARMONIC_BUILDS")
        self.assertEqual(len(bank.presets), 4)

    def test_reverse_swell_bank(self):
        bank = reverse_swell_bank()
        self.assertEqual(bank.name, "REVERSE_SWELLS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_RISER_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_RISER_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_riser(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_RISER_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_riser_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
