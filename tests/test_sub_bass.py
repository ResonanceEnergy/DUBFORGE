"""Tests for engine.sub_bass — Sub-Bass One-Shot Synthesizer."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine.sub_bass import (
    ALL_SUB_BASS_BANKS,
    SubBassBank,
    SubBassPreset,
    deep_sine_bank,
    fifth_bank,
    harmonic_bank,
    octave_bank,
    pulse_sub_bank,
    rumble_bank,
    synthesize_deep_sine,
    synthesize_fifth,
    synthesize_harmonic,
    synthesize_octave,
    synthesize_pulse_sub,
    synthesize_rumble,
    synthesize_sub_bass,
    synthesize_triangle_sub,
    triangle_sub_bank,
    write_sub_bass_manifest,
)


class TestSubBassPreset(unittest.TestCase):
    """SubBassPreset dataclass tests."""

    def test_defaults(self):
        p = SubBassPreset("test", "deep_sine")
        self.assertEqual(p.name, "test")
        self.assertEqual(p.sub_type, "deep_sine")
        self.assertAlmostEqual(p.frequency, 40.0)
        self.assertAlmostEqual(p.duration_s, 1.5)
        self.assertAlmostEqual(p.drive, 0.0)

    def test_custom_values(self):
        p = SubBassPreset("custom", "rumble", frequency=55.0,
                          duration_s=2.0, drive=0.3, lfo_rate=1.618)
        self.assertAlmostEqual(p.frequency, 55.0)
        self.assertAlmostEqual(p.drive, 0.3)


class TestSubBassSynthesizers(unittest.TestCase):
    """Individual synthesizer function tests."""

    def _check_audio(self, audio: np.ndarray, preset: SubBassPreset):
        expected_len = int(preset.duration_s * 44100)
        self.assertEqual(len(audio), expected_len)
        self.assertLessEqual(np.max(np.abs(audio)), 1.0 + 1e-6)
        self.assertGreater(np.max(np.abs(audio)), 0.01)

    def test_deep_sine(self):
        p = SubBassPreset("t", "deep_sine", 41.2, duration_s=0.5)
        audio = synthesize_deep_sine(p)
        self._check_audio(audio, p)

    def test_octave(self):
        p = SubBassPreset("t", "octave", 55.0, duration_s=0.5)
        audio = synthesize_octave(p)
        self._check_audio(audio, p)

    def test_fifth(self):
        p = SubBassPreset("t", "fifth", 43.65, duration_s=0.5)
        audio = synthesize_fifth(p)
        self._check_audio(audio, p)

    def test_harmonic(self):
        p = SubBassPreset("t", "harmonic", 41.2, duration_s=0.5)
        audio = synthesize_harmonic(p)
        self._check_audio(audio, p)

    def test_rumble(self):
        p = SubBassPreset("t", "rumble", 40.0, duration_s=0.5,
                          lfo_rate=1.618, lfo_depth=0.3)
        audio = synthesize_rumble(p)
        self._check_audio(audio, p)

    def test_pulse_sub(self):
        p = SubBassPreset("t", "pulse", 41.2, duration_s=0.5)
        audio = synthesize_pulse_sub(p)
        self._check_audio(audio, p)

    def test_triangle_sub(self):
        p = SubBassPreset("t", "triangle", 41.2, duration_s=0.5)
        audio = synthesize_triangle_sub(p)
        self._check_audio(audio, p)

    def test_drive_saturation(self):
        p = SubBassPreset("t", "deep_sine", 41.2, duration_s=0.3, drive=0.8)
        audio = synthesize_deep_sine(p)
        self._check_audio(audio, p)


class TestSubBassRouter(unittest.TestCase):
    """Router dispatch tests."""

    def test_routes_all_types(self):
        for sub_type in ("deep_sine", "octave", "fifth", "harmonic", "rumble",
                        "pulse", "triangle"):
            p = SubBassPreset("t", sub_type, 41.2, duration_s=0.3)
            audio = synthesize_sub_bass(p)
            self.assertEqual(len(audio), int(0.3 * 44100))

    def test_unknown_type_raises(self):
        p = SubBassPreset("t", "invalid_type")
        with self.assertRaises(ValueError):
            synthesize_sub_bass(p)


class TestSubBassBanks(unittest.TestCase):
    """Bank function tests."""

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_SUB_BASS_BANKS), 9)

    def test_total_presets(self):
        total = sum(len(fn().presets) for fn in ALL_SUB_BASS_BANKS.values())
        self.assertEqual(total, 36)

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_SUB_BASS_BANKS.items():
            bank = fn()
            self.assertEqual(len(bank.presets), 4, f"{name} bank")
            self.assertIsInstance(bank, SubBassBank)

    def test_bank_functions(self):
        for fn in (deep_sine_bank, octave_bank, fifth_bank,
                   harmonic_bank, rumble_bank, pulse_sub_bank,
                   triangle_sub_bank):
            bank = fn()
            self.assertEqual(len(bank.presets), 4)
            for preset in bank.presets:
                audio = synthesize_sub_bass(preset)
                self.assertGreater(len(audio), 0)

    def test_manifest_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = write_sub_bass_manifest(tmp)
            self.assertEqual(len(manifest["banks"]), 9)
            manifest_path = Path(tmp) / "analysis" / "sub_bass_manifest.json"
            self.assertTrue(manifest_path.exists())
            data = json.loads(manifest_path.read_text())
            self.assertEqual(data["module"], "sub_bass")


if __name__ == "__main__":
    unittest.main()
