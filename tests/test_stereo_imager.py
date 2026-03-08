"""Tests for engine.stereo_imager — Stereo Imaging."""

import tempfile
import unittest

import numpy as np

from engine.stereo_imager import (
    ALL_STEREO_BANKS,
    StereoPreset,
    apply_haas,
    apply_mid_side,
    apply_stereo_imaging,
    freq_split_stereo_bank,
    haas_stereo_bank,
    mid_side_stereo_bank,
    phase_stereo_bank,
    psychoacoustic_stereo_bank,
    write_stereo_imager_manifest,
)


class TestStereoPreset(unittest.TestCase):
    def test_defaults(self):
        p = StereoPreset("test", "haas")
        self.assertAlmostEqual(p.width, 1.0)
        self.assertAlmostEqual(p.delay_ms, 10.0)
        self.assertAlmostEqual(p.mix, 1.0)

    def test_custom(self):
        p = StereoPreset("t", "mid_side", width=1.5)
        self.assertAlmostEqual(p.width, 1.5)


class TestProcessors(unittest.TestCase):
    def _make_mono(self, n=4410):
        return np.sin(np.linspace(0, 10, n))

    def _assert_stereo(self, result, n=4410):
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (n, 2))

    def test_haas(self):
        p = StereoPreset("t", "haas", delay_ms=5.0)
        result = apply_haas(self._make_mono(), p, sample_rate=4410)
        self._assert_stereo(result)

    def test_mid_side(self):
        p = StereoPreset("t", "mid_side", width=1.5)
        result = apply_mid_side(self._make_mono(), p, sample_rate=4410)
        self._assert_stereo(result)

    def test_mid_side_mono(self):
        """Width=0 should produce mono."""
        p = StereoPreset("t", "mid_side", width=0.0)
        result = apply_mid_side(self._make_mono(), p, sample_rate=4410)
        # L and R should be identical when width=0
        np.testing.assert_allclose(result[:, 0], result[:, 1], atol=1e-10)


class TestRouter(unittest.TestCase):
    def test_routes_all_types(self):
        signal = np.sin(np.linspace(0, 10, 4410))
        for itype in ["haas", "mid_side", "frequency_split", "phase", "psychoacoustic"]:
            p = StereoPreset("t", itype)
            result = apply_stereo_imaging(signal, p, sample_rate=4410)
            self.assertIsInstance(result, np.ndarray)
            self.assertEqual(result.shape[0], 4410)
            self.assertEqual(result.shape[1], 2)

    def test_invalid_type(self):
        p = StereoPreset("t", "nonexistent")
        with self.assertRaises(ValueError):
            apply_stereo_imaging(np.zeros(100), p)


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [haas_stereo_bank, mid_side_stereo_bank,
                        freq_split_stereo_bank, phase_stereo_bank,
                        psychoacoustic_stereo_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.presets), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_STEREO_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_stereo_imager_manifest(td)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
