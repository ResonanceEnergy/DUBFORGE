"""Tests for engine.sidechain — Sidechain Compression / Ducking Engine."""

import tempfile
import unittest

import numpy as np

from engine.sidechain import (
    ALL_SIDECHAIN_BANKS,
    SidechainPreset,
    apply_sidechain,
    bounce_sidechain_bank,
    generate_bounce_envelope,
    generate_hard_cut_envelope,
    generate_phi_curve_envelope,
    generate_pump_envelope,
    generate_sidechain,
    generate_smooth_envelope,
    hard_cut_sidechain_bank,
    phi_curve_sidechain_bank,
    pump_sidechain_bank,
    smooth_sidechain_bank,
    write_sidechain_manifest,
)


class TestSidechainPreset(unittest.TestCase):
    def test_defaults(self):
        p = SidechainPreset("test", "pump")
        self.assertEqual(p.shape, "pump")
        self.assertAlmostEqual(p.attack_ms, 0.5)
        self.assertAlmostEqual(p.release_ms, 150.0)
        self.assertAlmostEqual(p.depth, 1.0)
        self.assertAlmostEqual(p.mix, 1.0)
        self.assertAlmostEqual(p.bpm, 150.0)

    def test_custom(self):
        p = SidechainPreset("t", "hard_cut", release_ms=80.0, depth=0.7)
        self.assertAlmostEqual(p.release_ms, 80.0)
        self.assertAlmostEqual(p.depth, 0.7)


class TestEnvelopeGenerators(unittest.TestCase):
    def _assert_valid_env(self, env):
        self.assertIsInstance(env, np.ndarray)
        self.assertGreater(len(env), 0)
        self.assertTrue(np.all(env >= -1e-6))
        self.assertTrue(np.all(env <= 1.0 + 1e-6))

    def test_pump(self):
        p = SidechainPreset("t", "pump", depth=0.9)
        env = generate_pump_envelope(p, duration_s=1.0, sample_rate=4410)
        self._assert_valid_env(env)

    def test_hard_cut(self):
        p = SidechainPreset("t", "hard_cut", depth=1.0)
        env = generate_hard_cut_envelope(p, duration_s=1.0, sample_rate=4410)
        self._assert_valid_env(env)

    def test_smooth(self):
        p = SidechainPreset("t", "smooth", depth=0.5)
        env = generate_smooth_envelope(p, duration_s=1.0, sample_rate=4410)
        self._assert_valid_env(env)

    def test_bounce(self):
        p = SidechainPreset("t", "bounce", depth=0.8, retrigger_rate=2.0)
        env = generate_bounce_envelope(p, duration_s=1.0, sample_rate=4410)
        self._assert_valid_env(env)

    def test_phi_curve(self):
        p = SidechainPreset("t", "phi_curve", depth=0.9)
        env = generate_phi_curve_envelope(p, duration_s=1.0, sample_rate=4410)
        self._assert_valid_env(env)


class TestRouter(unittest.TestCase):
    def test_routes_all_shapes(self):
        for shape in ["pump", "hard_cut", "smooth", "bounce", "phi_curve"]:
            p = SidechainPreset("t", shape)
            env = generate_sidechain(p, duration_s=0.5, sample_rate=4410)
            self.assertIsInstance(env, np.ndarray)
            self.assertGreater(len(env), 0)

    def test_invalid_shape(self):
        p = SidechainPreset("t", "nonexistent")
        with self.assertRaises(ValueError):
            generate_sidechain(p)


class TestApplySidechain(unittest.TestCase):
    def test_apply_to_signal(self):
        signal = np.ones(4410)
        p = SidechainPreset("t", "pump", depth=1.0)
        result = apply_sidechain(signal, p, sample_rate=4410)
        self.assertEqual(len(result), len(signal))
        # Should have some ducking
        self.assertLess(np.min(result), 1.0)


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        banks = [
            pump_sidechain_bank,
            hard_cut_sidechain_bank,
            smooth_sidechain_bank,
            bounce_sidechain_bank,
            phi_curve_sidechain_bank,
        ]
        for bank_fn in banks:
            bank = bank_fn()
            self.assertGreater(len(bank.presets), 0)
            for p in bank.presets:
                self.assertTrue(len(p.name) > 0)

    def test_registry(self):
        self.assertEqual(len(ALL_SIDECHAIN_BANKS), 5)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_sidechain_manifest(td)
            self.assertIn("banks", manifest)
            self.assertEqual(len(manifest["banks"]), 5)
            total = sum(b["preset_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
