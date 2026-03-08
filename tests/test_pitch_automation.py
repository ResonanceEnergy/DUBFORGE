"""Tests for engine.pitch_automation — Pitch Automation."""

import tempfile
import unittest

import numpy as np

from engine.pitch_automation import (
    ALL_PITCH_AUTO_BANKS,
    PitchAutoPreset,
    dive_pitch_bank,
    generate_dive_curve,
    generate_glide_curve,
    generate_pitch_automation,
    generate_rise_curve,
    generate_staircase_curve,
    generate_wobble_curve,
    glide_pitch_bank,
    rise_pitch_bank,
    staircase_pitch_bank,
    wobble_pitch_bank,
    write_pitch_automation_manifest,
)


class TestPitchAutoPreset(unittest.TestCase):
    def test_defaults(self):
        p = PitchAutoPreset("test", "dive")
        self.assertAlmostEqual(p.start_semitones, 0.0)
        self.assertAlmostEqual(p.end_semitones, -12.0)
        self.assertAlmostEqual(p.duration_s, 1.0)

    def test_custom(self):
        p = PitchAutoPreset("t", "rise", start_semitones=-24, end_semitones=0)
        self.assertAlmostEqual(p.start_semitones, -24.0)


class TestCurveGenerators(unittest.TestCase):
    def _assert_valid(self, curve, expected_len):
        self.assertIsInstance(curve, np.ndarray)
        self.assertEqual(len(curve), expected_len)

    def test_dive(self):
        p = PitchAutoPreset("t", "dive", duration_s=1.0)
        c = generate_dive_curve(p, sample_rate=4410)
        self._assert_valid(c, 4410)
        # Should start at 0 and end near -12
        self.assertAlmostEqual(c[0], 0.0, places=1)
        self.assertAlmostEqual(c[-1], -12.0, places=1)

    def test_rise(self):
        p = PitchAutoPreset("t", "rise", start_semitones=-12, end_semitones=0, duration_s=0.5)
        c = generate_rise_curve(p, sample_rate=4410)
        self._assert_valid(c, 2205)

    def test_wobble(self):
        p = PitchAutoPreset("t", "wobble", rate_hz=4.0, depth_semitones=3.0, duration_s=0.5)
        c = generate_wobble_curve(p, sample_rate=4410)
        self._assert_valid(c, 2205)

    def test_staircase(self):
        p = PitchAutoPreset("t", "staircase", steps=4, duration_s=1.0)
        c = generate_staircase_curve(p, sample_rate=4410)
        self._assert_valid(c, 4410)
        # Should have discrete steps
        unique = len(np.unique(np.round(c, 2)))
        self.assertGreaterEqual(unique, 2)

    def test_glide(self):
        p = PitchAutoPreset("t", "glide", duration_s=0.5)
        c = generate_glide_curve(p, sample_rate=4410)
        self._assert_valid(c, 2205)


class TestRouter(unittest.TestCase):
    def test_routes_all_types(self):
        for atype in ["dive", "rise", "wobble", "staircase", "glide"]:
            p = PitchAutoPreset("t", atype, duration_s=0.3)
            c = generate_pitch_automation(p, sample_rate=4410)
            self.assertIsInstance(c, np.ndarray)
            self.assertGreater(len(c), 0)

    def test_invalid_type(self):
        p = PitchAutoPreset("t", "nonexistent")
        with self.assertRaises(ValueError):
            generate_pitch_automation(p)


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [dive_pitch_bank, rise_pitch_bank,
                        wobble_pitch_bank, staircase_pitch_bank, glide_pitch_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.presets), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_PITCH_AUTO_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_pitch_automation_manifest(td)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
