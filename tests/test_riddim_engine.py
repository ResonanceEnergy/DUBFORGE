"""Tests for engine.riddim_engine — Riddim Bass Sequencer."""

import tempfile
import unittest

import numpy as np

from engine.riddim_engine import (
    ALL_RIDDIM_BANKS,
    RiddimPreset,
    bounce_riddim_bank,
    generate_riddim,
    generate_riddim_bounce,
    generate_riddim_heavy,
    generate_riddim_minimal,
    generate_riddim_stutter,
    generate_riddim_triplet,
    heavy_riddim_bank,
    minimal_riddim_bank,
    stutter_riddim_bank,
    triplet_riddim_bank,
    write_riddim_manifest,
)


class TestRiddimPreset(unittest.TestCase):
    def test_defaults(self):
        p = RiddimPreset("test", "minimal")
        self.assertAlmostEqual(p.frequency, 55.0)
        self.assertAlmostEqual(p.gap_ratio, 0.3)
        self.assertAlmostEqual(p.distortion, 0.5)
        self.assertAlmostEqual(p.bpm, 150.0)

    def test_custom(self):
        p = RiddimPreset("t", "heavy", gap_ratio=0.1, distortion=0.9)
        self.assertAlmostEqual(p.gap_ratio, 0.1)
        self.assertAlmostEqual(p.distortion, 0.9)


class TestGenerators(unittest.TestCase):
    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)

    def test_minimal(self):
        p = RiddimPreset("t", "minimal", duration_s=0.5)
        self._assert_valid(generate_riddim_minimal(p, sample_rate=4410))

    def test_heavy(self):
        p = RiddimPreset("t", "heavy", duration_s=0.5)
        self._assert_valid(generate_riddim_heavy(p, sample_rate=4410))

    def test_bounce(self):
        p = RiddimPreset("t", "bounce", duration_s=0.5)
        self._assert_valid(generate_riddim_bounce(p, sample_rate=4410))

    def test_stutter(self):
        p = RiddimPreset("t", "stutter", duration_s=0.5, subdivisions=4)
        self._assert_valid(generate_riddim_stutter(p, sample_rate=4410))

    def test_triplet(self):
        p = RiddimPreset("t", "triplet", duration_s=0.5)
        self._assert_valid(generate_riddim_triplet(p, sample_rate=4410))


class TestRouter(unittest.TestCase):
    def test_routes_all_types(self):
        for rtype in ["minimal", "heavy", "bounce", "stutter", "triplet"]:
            p = RiddimPreset("t", rtype, duration_s=0.3)
            sig = generate_riddim(p, sample_rate=4410)
            self.assertIsInstance(sig, np.ndarray)
            self.assertGreater(len(sig), 0)

    def test_invalid_type(self):
        p = RiddimPreset("t", "nonexistent")
        with self.assertRaises(ValueError):
            generate_riddim(p)


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [minimal_riddim_bank, heavy_riddim_bank,
                        bounce_riddim_bank, stutter_riddim_bank, triplet_riddim_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.presets), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_RIDDIM_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_riddim_manifest(td)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
