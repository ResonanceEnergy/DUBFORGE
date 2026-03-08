"""Tests for engine.drone_synth — Drone Synthesizer."""

import tempfile
import unittest

import numpy as np

from engine.drone_synth import (
    ALL_DRONE_BANKS,
    DronePreset,
    beating_drone_bank,
    dark_drone_bank,
    evolving_drone_bank,
    harmonic_drone_bank,
    shimmer_drone_bank,
    synthesize_beating_drone,
    synthesize_dark_drone,
    synthesize_drone,
    synthesize_evolving_drone,
    synthesize_harmonic_drone,
    synthesize_shimmer_drone,
    write_drone_manifest,
)


class TestDronePreset(unittest.TestCase):
    """Test DronePreset dataclass."""

    def test_defaults(self):
        p = DronePreset("test", "harmonic")
        self.assertAlmostEqual(p.frequency, 55.0)
        self.assertAlmostEqual(p.duration_s, 8.0)
        self.assertEqual(p.num_voices, 5)
        self.assertAlmostEqual(p.detune_cents, 5.0)
        self.assertAlmostEqual(p.brightness, 0.5)
        self.assertAlmostEqual(p.movement, 0.3)
        self.assertAlmostEqual(p.attack_s, 1.0)
        self.assertAlmostEqual(p.release_s, 2.0)
        self.assertAlmostEqual(p.distortion, 0.0)
        self.assertAlmostEqual(p.reverb_amount, 0.4)

    def test_custom_values(self):
        p = DronePreset("t", "dark", duration_s=4.0, num_voices=8)
        self.assertAlmostEqual(p.duration_s, 4.0)
        self.assertEqual(p.num_voices, 8)


class TestSynthesizers(unittest.TestCase):
    """Test individual drone synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_harmonic_drone(self):
        p = DronePreset("t", "harmonic", duration_s=1.0)
        self._assert_valid(synthesize_harmonic_drone(p))

    def test_beating_drone(self):
        p = DronePreset("t", "beating", duration_s=1.0)
        self._assert_valid(synthesize_beating_drone(p))

    def test_dark_drone(self):
        p = DronePreset("t", "dark", duration_s=1.0)
        self._assert_valid(synthesize_dark_drone(p))

    def test_shimmer_drone(self):
        p = DronePreset("t", "shimmer", duration_s=1.0)
        self._assert_valid(synthesize_shimmer_drone(p))

    def test_evolving_drone(self):
        p = DronePreset("t", "evolving", duration_s=1.0)
        self._assert_valid(synthesize_evolving_drone(p))

    def test_router_all_types(self):
        for dtype in ("harmonic", "beating", "dark", "shimmer", "evolving"):
            p = DronePreset("t", dtype, duration_s=1.0)
            signal = synthesize_drone(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = DronePreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_drone(p)


class TestBanks(unittest.TestCase):
    """Test drone banks."""

    def test_harmonic_drone_bank(self):
        bank = harmonic_drone_bank()
        self.assertEqual(bank.name, "HARMONIC_DRONES")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.drone_type, "harmonic")

    def test_beating_drone_bank(self):
        bank = beating_drone_bank()
        self.assertEqual(bank.name, "BEATING_DRONES")
        self.assertEqual(len(bank.presets), 4)

    def test_dark_drone_bank(self):
        bank = dark_drone_bank()
        self.assertEqual(bank.name, "DARK_DRONES")
        self.assertEqual(len(bank.presets), 4)

    def test_shimmer_drone_bank(self):
        bank = shimmer_drone_bank()
        self.assertEqual(bank.name, "SHIMMER_DRONES")
        self.assertEqual(len(bank.presets), 4)

    def test_evolving_drone_bank(self):
        bank = evolving_drone_bank()
        self.assertEqual(bank.name, "EVOLVING_DRONES")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_DRONE_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_DRONE_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_drone(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_DRONE_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_drone_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
