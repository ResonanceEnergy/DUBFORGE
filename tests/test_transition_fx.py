"""Tests for engine.transition_fx — Transition FX Generator."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.transition_fx import (
    ALL_TRANSITION_BANKS,
    TransitionPreset,
    gate_chop_bank,
    glitch_stutter_bank,
    pitch_dive_bank,
    reverse_crash_bank,
    synthesize_gate_chop,
    synthesize_glitch_stutter,
    synthesize_pitch_dive,
    synthesize_reverse_crash,
    synthesize_tape_start,
    synthesize_tape_stop,
    synthesize_transition,
    synthesize_vinyl_fx,
    tape_start_bank,
    tape_stop_bank,
    vinyl_fx_bank,
    write_transition_manifest,
)


class TestTransitionPreset(unittest.TestCase):
    """Test TransitionPreset dataclass."""

    def test_defaults(self):
        p = TransitionPreset("test", "tape_stop", 1.0)
        self.assertEqual(p.start_freq, 200.0)
        self.assertEqual(p.gate_divisions, 8)
        self.assertEqual(p.stutter_repeats, 4)
        self.assertAlmostEqual(p.brightness, 0.7)

    def test_custom_values(self):
        p = TransitionPreset("t", "gate_chop", 2.0, gate_divisions=32)
        self.assertEqual(p.gate_divisions, 32)


class TestSynthesizers(unittest.TestCase):
    """Test individual transition synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0)

    def test_tape_stop(self):
        p = TransitionPreset("t", "tape_stop", 0.3, start_freq=300)
        self._assert_valid(synthesize_tape_stop(p))

    def test_tape_start(self):
        p = TransitionPreset("t", "tape_start", 0.3, start_freq=300)
        self._assert_valid(synthesize_tape_start(p))

    def test_reverse_crash(self):
        p = TransitionPreset("t", "reverse_crash", 0.3, brightness=0.8)
        self._assert_valid(synthesize_reverse_crash(p))

    def test_gate_chop(self):
        p = TransitionPreset("t", "gate_chop", 0.5, gate_divisions=8)
        self._assert_valid(synthesize_gate_chop(p))

    def test_pitch_dive(self):
        p = TransitionPreset("t", "pitch_dive", 0.3,
                             start_freq=800, end_freq=30)
        self._assert_valid(synthesize_pitch_dive(p))

    def test_glitch_stutter(self):
        p = TransitionPreset("t", "glitch_stutter", 0.3,
                             start_freq=400, stutter_repeats=4)
        self._assert_valid(synthesize_glitch_stutter(p))

    def test_vinyl_fx(self):
        p = TransitionPreset("t", "vinyl_fx", 0.5, brightness=0.7)
        self._assert_valid(synthesize_vinyl_fx(p))

    def test_router_unknown(self):
        p = TransitionPreset("t", "laser_beam", 1.0)
        with self.assertRaises(ValueError):
            synthesize_transition(p)


class TestBanks(unittest.TestCase):
    """Test preset banks."""

    def test_tape_stop_bank(self):
        bank = tape_stop_bank()
        self.assertEqual(bank.name, "TAPE_STOPS")
        self.assertEqual(len(bank.presets), 3)

    def test_tape_start_bank(self):
        bank = tape_start_bank()
        self.assertEqual(bank.name, "TAPE_STARTS")
        self.assertEqual(len(bank.presets), 2)

    def test_reverse_crash_bank(self):
        bank = reverse_crash_bank()
        self.assertEqual(bank.name, "REVERSE_CRASHES")
        self.assertEqual(len(bank.presets), 3)

    def test_gate_chop_bank(self):
        bank = gate_chop_bank()
        self.assertEqual(bank.name, "GATE_CHOPS")
        self.assertEqual(len(bank.presets), 3)

    def test_pitch_dive_bank(self):
        bank = pitch_dive_bank()
        self.assertEqual(bank.name, "PITCH_DIVES")
        self.assertEqual(len(bank.presets), 3)

    def test_glitch_stutter_bank(self):
        bank = glitch_stutter_bank()
        self.assertEqual(bank.name, "GLITCH_STUTTERS")
        self.assertEqual(len(bank.presets), 3)

    def test_vinyl_fx_bank(self):
        bank = vinyl_fx_bank()
        self.assertEqual(bank.name, "VINYL_FX")
        self.assertEqual(len(bank.presets), 3)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_TRANSITION_BANKS), 12)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_TRANSITION_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_transition(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_38(self):
        total = sum(len(fn().presets) for fn in ALL_TRANSITION_BANKS.values())
        self.assertEqual(total, 38)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_TRANSITION_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_transition_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 12)


if __name__ == "__main__":
    unittest.main()
