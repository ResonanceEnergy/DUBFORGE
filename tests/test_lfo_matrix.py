"""Tests for engine.lfo_matrix — LFO Modulation Matrix."""

import tempfile
import unittest

import numpy as np

from engine.lfo_matrix import (
    ALL_LFO_BANKS,
    LFOPreset,
    apply_lfo,
    generate_lfo,
    generate_sample_hold_lfo,
    generate_saw_lfo,
    generate_sine_lfo,
    generate_square_lfo,
    generate_triangle_lfo,
    sample_hold_lfo_bank,
    saw_lfo_bank,
    sine_lfo_bank,
    square_lfo_bank,
    triangle_lfo_bank,
    write_lfo_matrix_manifest,
)


class TestLFOPreset(unittest.TestCase):
    def test_defaults(self):
        p = LFOPreset("test", "sine")
        self.assertAlmostEqual(p.rate_hz, 1.0)
        self.assertAlmostEqual(p.depth, 1.0)
        self.assertEqual(p.polarity, "bipolar")

    def test_bpm_sync(self):
        p = LFOPreset("t", "sine", sync_bpm=150.0, sync_division=2.0)
        self.assertAlmostEqual(p.sync_bpm, 150.0)


class TestWaveformGenerators(unittest.TestCase):
    def _assert_valid_bipolar(self, signal, depth=1.0):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(signal), depth + 1e-6)
        self.assertGreaterEqual(np.min(signal), -depth - 1e-6)

    def test_sine(self):
        p = LFOPreset("t", "sine", rate_hz=2.0, depth=1.0)
        s = generate_sine_lfo(p, 1.0, sample_rate=4410)
        self._assert_valid_bipolar(s)

    def test_triangle(self):
        p = LFOPreset("t", "triangle", rate_hz=2.0, depth=1.0)
        s = generate_triangle_lfo(p, 1.0, sample_rate=4410)
        self._assert_valid_bipolar(s)

    def test_saw(self):
        p = LFOPreset("t", "saw", rate_hz=2.0, depth=1.0)
        s = generate_saw_lfo(p, 1.0, sample_rate=4410)
        self._assert_valid_bipolar(s)

    def test_square(self):
        p = LFOPreset("t", "square", rate_hz=2.0, depth=1.0)
        s = generate_square_lfo(p, 1.0, sample_rate=4410)
        self._assert_valid_bipolar(s)
        # Square wave should only have +1 and -1 values (scaled by depth)
        unique = np.unique(s)
        self.assertLessEqual(len(unique), 2)

    def test_sample_hold(self):
        p = LFOPreset("t", "sample_hold", rate_hz=4.0, depth=1.0)
        s = generate_sample_hold_lfo(p, 1.0, sample_rate=4410)
        self._assert_valid_bipolar(s)

    def test_unipolar(self):
        p = LFOPreset("t", "sine", rate_hz=2.0, depth=1.0, polarity="unipolar")
        s = generate_sine_lfo(p, 1.0, sample_rate=4410)
        self.assertTrue(np.all(s >= -1e-6))


class TestRouter(unittest.TestCase):
    def test_routes_all_types(self):
        for ltype in ["sine", "triangle", "saw", "square", "sample_hold"]:
            p = LFOPreset("t", ltype, rate_hz=2.0)
            s = generate_lfo(p, 0.5, sample_rate=4410)
            self.assertIsInstance(s, np.ndarray)
            self.assertGreater(len(s), 0)

    def test_invalid_type(self):
        p = LFOPreset("t", "nonexistent")
        with self.assertRaises(ValueError):
            generate_lfo(p, 1.0)


class TestApplyLFO(unittest.TestCase):
    def test_apply_to_signal(self):
        signal = np.ones(4410)
        p = LFOPreset("t", "sine", rate_hz=2.0, depth=1.0)
        result = apply_lfo(signal, p, param_range=(0.0, 1.0), sample_rate=4410)
        self.assertEqual(len(result), len(signal))


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [sine_lfo_bank, triangle_lfo_bank, saw_lfo_bank,
                        square_lfo_bank, sample_hold_lfo_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.presets), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_LFO_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_lfo_matrix_manifest(td)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
