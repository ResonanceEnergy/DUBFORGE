"""Tests for engine.glitch_engine — Glitch Engine."""

import tempfile
import unittest

import numpy as np

from engine.glitch_engine import (
    ALL_GLITCH_BANKS,
    GlitchPreset,
    bitcrush_glitch_bank,
    buffer_glitch_bank,
    granular_glitch_bank,
    stutter_glitch_bank,
    synthesize_bitcrush,
    synthesize_buffer_glitch,
    synthesize_glitch,
    synthesize_granular_glitch,
    synthesize_stutter,
    synthesize_tape_stop,
    tape_stop_glitch_bank,
    write_glitch_manifest,
)


class TestGlitchPreset(unittest.TestCase):
    """Test GlitchPreset dataclass."""

    def test_defaults(self):
        p = GlitchPreset("test", "stutter")
        self.assertAlmostEqual(p.frequency, 200.0)
        self.assertAlmostEqual(p.duration_s, 2.0)
        self.assertAlmostEqual(p.rate, 8.0)
        self.assertAlmostEqual(p.depth, 0.8)
        self.assertAlmostEqual(p.mix, 1.0)
        self.assertAlmostEqual(p.attack_s, 0.005)
        self.assertAlmostEqual(p.release_s, 0.1)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = GlitchPreset("t", "bitcrush", duration_s=1.0, rate=16.0)
        self.assertAlmostEqual(p.duration_s, 1.0)
        self.assertAlmostEqual(p.rate, 16.0)


class TestSynthesizers(unittest.TestCase):
    """Test individual glitch synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_stutter(self):
        p = GlitchPreset("t", "stutter", duration_s=0.5)
        self._assert_valid(synthesize_stutter(p))

    def test_bitcrush(self):
        p = GlitchPreset("t", "bitcrush", duration_s=0.5)
        self._assert_valid(synthesize_bitcrush(p))

    def test_tape_stop(self):
        p = GlitchPreset("t", "tape_stop", duration_s=0.5)
        self._assert_valid(synthesize_tape_stop(p))

    def test_granular_glitch(self):
        p = GlitchPreset("t", "granular_glitch", duration_s=0.5)
        self._assert_valid(synthesize_granular_glitch(p))

    def test_buffer_glitch(self):
        p = GlitchPreset("t", "buffer_glitch", duration_s=0.5)
        self._assert_valid(synthesize_buffer_glitch(p))

    def test_router_all_types(self):
        for gtype in ("stutter", "bitcrush", "tape_stop", "granular_glitch", "buffer_glitch"):
            p = GlitchPreset("t", gtype, duration_s=0.3)
            signal = synthesize_glitch(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = GlitchPreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_glitch(p)


class TestBanks(unittest.TestCase):
    """Test glitch banks."""

    def test_stutter_glitch_bank(self):
        bank = stutter_glitch_bank()
        self.assertEqual(bank.name, "STUTTER_GLITCHES")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.glitch_type, "stutter")

    def test_bitcrush_glitch_bank(self):
        bank = bitcrush_glitch_bank()
        self.assertEqual(bank.name, "BITCRUSH_GLITCHES")
        self.assertEqual(len(bank.presets), 4)

    def test_tape_stop_glitch_bank(self):
        bank = tape_stop_glitch_bank()
        self.assertEqual(bank.name, "TAPE_STOP_GLITCHES")
        self.assertEqual(len(bank.presets), 4)

    def test_granular_glitch_bank(self):
        bank = granular_glitch_bank()
        self.assertEqual(bank.name, "GRANULAR_GLITCHES")
        self.assertEqual(len(bank.presets), 4)

    def test_buffer_glitch_bank(self):
        bank = buffer_glitch_bank()
        self.assertEqual(bank.name, "BUFFER_GLITCHES")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_GLITCH_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_GLITCH_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_glitch(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_GLITCH_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_glitch_manifest(tmpdir)
            self.assertIn("banks", result)
            self.assertEqual(len(result["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
