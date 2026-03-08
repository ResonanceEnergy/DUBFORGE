"""Tests for engine.multiband_distortion — Multiband Distortion."""

import tempfile
import unittest

import numpy as np

from engine.multiband_distortion import (
    ALL_MULTIBAND_DIST_BANKS,
    MultibandDistPreset,
    aggressive_distortion_bank,
    apply_multiband_distortion,
    digital_distortion_bank,
    tape_distortion_bank,
    tube_distortion_bank,
    warm_distortion_bank,
    write_multiband_distortion_manifest,
)


class TestMultibandDistPreset(unittest.TestCase):
    def test_defaults(self):
        p = MultibandDistPreset("test", "warm")
        self.assertAlmostEqual(p.low_drive, 0.3)
        self.assertAlmostEqual(p.mid_drive, 0.5)
        self.assertAlmostEqual(p.high_drive, 0.4)
        self.assertAlmostEqual(p.crossover_low, 200.0)
        self.assertAlmostEqual(p.crossover_high, 2000.0)

    def test_custom(self):
        p = MultibandDistPreset("t", "aggressive", low_drive=0.9, mid_drive=1.0)
        self.assertAlmostEqual(p.low_drive, 0.9)


class TestProcessing(unittest.TestCase):
    def _make_signal(self, n=4410):
        t = np.linspace(0, 1, n)
        return np.sin(2 * np.pi * 100 * t) * 0.5

    def test_warm(self):
        p = MultibandDistPreset("t", "warm")
        result = apply_multiband_distortion(self._make_signal(), p, sample_rate=4410)
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), 4410)

    def test_aggressive(self):
        p = MultibandDistPreset("t", "aggressive", low_drive=0.8, mid_drive=0.9)
        result = apply_multiband_distortion(self._make_signal(), p, sample_rate=4410)
        self.assertEqual(len(result), 4410)

    def test_digital(self):
        p = MultibandDistPreset("t", "digital", bit_depth=8, sample_reduce=4)
        result = apply_multiband_distortion(self._make_signal(), p, sample_rate=4410)
        self.assertEqual(len(result), 4410)

    def test_tube(self):
        p = MultibandDistPreset("t", "tube")
        result = apply_multiband_distortion(self._make_signal(), p, sample_rate=4410)
        self.assertEqual(len(result), 4410)

    def test_tape(self):
        p = MultibandDistPreset("t", "tape")
        result = apply_multiband_distortion(self._make_signal(), p, sample_rate=4410)
        self.assertEqual(len(result), 4410)

    def test_zero_drive(self):
        p = MultibandDistPreset("t", "warm", low_drive=0.0, mid_drive=0.0, high_drive=0.0)
        signal = self._make_signal()
        result = apply_multiband_distortion(signal, p, sample_rate=4410)
        self.assertEqual(len(result), len(signal))

    def test_mix_zero(self):
        p = MultibandDistPreset("t", "aggressive", mix=0.0)
        signal = self._make_signal()
        result = apply_multiband_distortion(signal, p, sample_rate=4410)
        np.testing.assert_allclose(result, signal, atol=1e-6)


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [warm_distortion_bank, aggressive_distortion_bank,
                        digital_distortion_bank, tube_distortion_bank,
                        tape_distortion_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.presets), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_MULTIBAND_DIST_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_multiband_distortion_manifest(td)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
