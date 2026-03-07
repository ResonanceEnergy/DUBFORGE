"""Tests for engine.noise_generator — Noise Texture Generator."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine.noise_generator import (
    ALL_NOISE_BANKS,
    NoiseBank,
    NoisePreset,
    brown_noise_bank,
    pink_noise_bank,
    synthesize_brown,
    synthesize_noise,
    synthesize_pink,
    synthesize_tape,
    synthesize_vinyl,
    synthesize_white,
    tape_noise_bank,
    vinyl_noise_bank,
    white_noise_bank,
    write_noise_manifest,
)


class TestNoisePreset(unittest.TestCase):
    """NoisePreset dataclass tests."""

    def test_defaults(self):
        p = NoisePreset("test", "white")
        self.assertEqual(p.name, "test")
        self.assertEqual(p.noise_type, "white")
        self.assertAlmostEqual(p.duration_s, 4.0)
        self.assertAlmostEqual(p.brightness, 0.5)
        self.assertAlmostEqual(p.gain, 0.8)

    def test_custom_values(self):
        p = NoisePreset("custom", "vinyl", duration_s=2.0,
                        density=0.8, modulation=0.5)
        self.assertAlmostEqual(p.density, 0.8)


class TestNoiseSynthesizers(unittest.TestCase):
    """Individual noise synthesizer tests."""

    def _check_audio(self, audio: np.ndarray, preset: NoisePreset):
        expected_len = int(preset.duration_s * 44100)
        self.assertEqual(len(audio), expected_len)
        self.assertLessEqual(np.max(np.abs(audio)), 1.0 + 1e-6)
        self.assertGreater(np.max(np.abs(audio)), 0.01)

    def test_white(self):
        p = NoisePreset("t", "white", duration_s=0.5)
        self._check_audio(synthesize_white(p), p)

    def test_white_dark(self):
        p = NoisePreset("t", "white", duration_s=0.5, brightness=0.2)
        self._check_audio(synthesize_white(p), p)

    def test_pink(self):
        p = NoisePreset("t", "pink", duration_s=0.5)
        self._check_audio(synthesize_pink(p), p)

    def test_brown(self):
        p = NoisePreset("t", "brown", duration_s=0.5)
        self._check_audio(synthesize_brown(p), p)

    def test_vinyl(self):
        p = NoisePreset("t", "vinyl", duration_s=0.5, density=0.5)
        self._check_audio(synthesize_vinyl(p), p)

    def test_tape(self):
        p = NoisePreset("t", "tape", duration_s=0.5, density=0.5)
        self._check_audio(synthesize_tape(p), p)

    def test_tape_high_density(self):
        p = NoisePreset("t", "tape", duration_s=0.5, density=0.8)
        self._check_audio(synthesize_tape(p), p)

    def test_modulated_noise(self):
        p = NoisePreset("t", "white", duration_s=0.5,
                        modulation=0.5, mod_rate=1.618)
        self._check_audio(synthesize_white(p), p)


class TestNoiseRouter(unittest.TestCase):
    """Router dispatch tests."""

    def test_routes_all_types(self):
        for noise_type in ("white", "pink", "brown", "vinyl", "tape"):
            p = NoisePreset("t", noise_type, duration_s=0.3)
            audio = synthesize_noise(p)
            self.assertEqual(len(audio), int(0.3 * 44100))

    def test_unknown_type_raises(self):
        p = NoisePreset("t", "invalid_type")
        with self.assertRaises(ValueError):
            synthesize_noise(p)


class TestNoiseBanks(unittest.TestCase):
    """Bank function tests."""

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_NOISE_BANKS), 5)

    def test_total_presets(self):
        total = sum(len(fn().presets) for fn in ALL_NOISE_BANKS.values())
        self.assertEqual(total, 20)

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_NOISE_BANKS.items():
            bank = fn()
            self.assertEqual(len(bank.presets), 4, f"{name} bank")
            self.assertIsInstance(bank, NoiseBank)

    def test_bank_functions(self):
        for fn in (white_noise_bank, pink_noise_bank, brown_noise_bank,
                   vinyl_noise_bank, tape_noise_bank):
            bank = fn()
            self.assertEqual(len(bank.presets), 4)
            for preset in bank.presets:
                audio = synthesize_noise(preset)
                self.assertGreater(len(audio), 0)

    def test_manifest_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = write_noise_manifest(tmp)
            self.assertEqual(len(manifest["banks"]), 5)
            manifest_path = Path(tmp) / "analysis" / "noise_manifest.json"
            self.assertTrue(manifest_path.exists())
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["module"], "noise_generator")


if __name__ == "__main__":
    unittest.main()
