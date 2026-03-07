"""Tests for engine.arp_synth — Arp Synth Pattern Generator."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.arp_synth import (
    ALL_ARP_BANKS,
    ArpSynthBank,
    ArpSynthPreset,
    acid_arp_bank,
    fm_arp_bank,
    pluck_arp_bank,
    pulse_arp_bank,
    saw_arp_bank,
    synthesize_acid_arp,
    synthesize_arp,
    synthesize_fm_arp,
    synthesize_pluck_arp,
    synthesize_pulse_arp,
    synthesize_saw_arp,
    write_arp_manifest,
)


class TestArpSynthPreset(unittest.TestCase):
    """Test ArpSynthPreset dataclass."""

    def test_defaults(self):
        p = ArpSynthPreset("test", "pulse")
        self.assertEqual(p.name, "test")
        self.assertEqual(p.arp_type, "pulse")
        self.assertAlmostEqual(p.base_freq, 220.0)
        self.assertAlmostEqual(p.duration_s, 4.0)
        self.assertEqual(p.step_count, 8)
        self.assertAlmostEqual(p.attack_s, 0.005)

    def test_custom_values(self):
        p = ArpSynthPreset("custom", "fm", base_freq=440.0,
                           duration_s=2.0, fm_depth=3.0, octave_range=3)
        self.assertAlmostEqual(p.base_freq, 440.0)
        self.assertAlmostEqual(p.fm_depth, 3.0)
        self.assertEqual(p.octave_range, 3)


class TestSynthesizers(unittest.TestCase):
    """Test individual arp synthesizers produce valid signals."""

    def _assert_valid(self, signal, preset):
        self.assertIsInstance(signal, np.ndarray)
        expected_len = int(preset.duration_s * 44100)
        # Arp synth uses step-based synthesis; length may differ slightly
        self.assertAlmostEqual(len(signal), expected_len, delta=expected_len * 0.01)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)
        self.assertGreater(np.max(np.abs(signal)), 0.01)

    def test_pulse_arp(self):
        p = ArpSynthPreset("t", "pulse", duration_s=0.5)
        self._assert_valid(synthesize_pulse_arp(p), p)

    def test_saw_arp(self):
        p = ArpSynthPreset("t", "saw", duration_s=0.5)
        self._assert_valid(synthesize_saw_arp(p), p)

    def test_fm_arp(self):
        p = ArpSynthPreset("t", "fm", duration_s=0.5,
                           fm_ratio=2.0, fm_depth=2.0)
        self._assert_valid(synthesize_fm_arp(p), p)

    def test_pluck_arp(self):
        p = ArpSynthPreset("t", "pluck", duration_s=0.5)
        self._assert_valid(synthesize_pluck_arp(p), p)

    def test_acid_arp(self):
        p = ArpSynthPreset("t", "acid", duration_s=0.5,
                           distortion=0.3)
        self._assert_valid(synthesize_acid_arp(p), p)

    def test_distortion_parameter(self):
        p = ArpSynthPreset("t", "pulse", duration_s=0.3, distortion=0.8)
        signal = synthesize_pulse_arp(p)
        self._assert_valid(signal, p)

    def test_router_all_types(self):
        for arp_type in ("pulse", "saw", "fm", "pluck", "acid"):
            p = ArpSynthPreset("t", arp_type, duration_s=0.3)
            signal = synthesize_arp(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = ArpSynthPreset("t", "invalid_type")
        with self.assertRaises(ValueError):
            synthesize_arp(p)


class TestBanks(unittest.TestCase):
    """Test arp preset banks."""

    def test_pulse_arp_bank(self):
        bank = pulse_arp_bank()
        self.assertEqual(bank.name, "PULSE_ARPS")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.arp_type, "pulse")

    def test_saw_arp_bank(self):
        bank = saw_arp_bank()
        self.assertEqual(bank.name, "SAW_ARPS")
        self.assertEqual(len(bank.presets), 4)

    def test_fm_arp_bank(self):
        bank = fm_arp_bank()
        self.assertEqual(bank.name, "FM_ARPS")
        self.assertEqual(len(bank.presets), 4)

    def test_pluck_arp_bank(self):
        bank = pluck_arp_bank()
        self.assertEqual(bank.name, "PLUCK_ARPS")
        self.assertEqual(len(bank.presets), 4)

    def test_acid_arp_bank(self):
        bank = acid_arp_bank()
        self.assertEqual(bank.name, "ACID_ARPS")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_ARP_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_ARP_BANKS.items():
            bank = gen_fn()
            self.assertIsInstance(bank, ArpSynthBank)
            for preset in bank.presets:
                signal = synthesize_arp(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_ARP_BANKS.values())
        self.assertEqual(total, 20)

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_ARP_BANKS.items():
            bank = fn()
            self.assertEqual(len(bank.presets), 4, f"{name} bank")


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = write_arp_manifest(tmpdir)
            manifest_path = os.path.join(tmpdir, "analysis",
                                         "arp_synth_manifest.json")
            self.assertTrue(os.path.exists(manifest_path))
            with open(manifest_path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
