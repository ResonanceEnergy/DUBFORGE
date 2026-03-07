"""Tests for engine.ambient_texture — Ambient Texture Generator."""

import json
import os
import tempfile
import unittest

import numpy as np

from engine.ambient_texture import (
    ALL_TEXTURE_BANKS,
    TexturePreset,
    ocean_texture_bank,
    rain_texture_bank,
    space_texture_bank,
    static_texture_bank,
    synthesize_ocean,
    synthesize_rain,
    synthesize_space,
    synthesize_static,
    synthesize_texture,
    synthesize_wind,
    wind_texture_bank,
    write_texture_manifest,
)


class TestTexturePreset(unittest.TestCase):
    """Test TexturePreset dataclass."""

    def test_defaults(self):
        p = TexturePreset("test", "rain")
        self.assertAlmostEqual(p.duration_s, 6.0)
        self.assertAlmostEqual(p.brightness, 0.5)
        self.assertAlmostEqual(p.distortion, 0.0)

    def test_custom_values(self):
        p = TexturePreset("t", "wind", duration_s=8.0, depth=0.9)
        self.assertAlmostEqual(p.duration_s, 8.0)
        self.assertAlmostEqual(p.depth, 0.9)


class TestSynthesizers(unittest.TestCase):
    """Test individual texture synthesizers produce valid signals."""

    def _assert_valid(self, signal):
        self.assertIsInstance(signal, np.ndarray)
        self.assertGreater(len(signal), 0)
        self.assertLessEqual(np.max(np.abs(signal)), 1.0 + 1e-6)

    def test_rain(self):
        p = TexturePreset("t", "rain", duration_s=0.5)
        self._assert_valid(synthesize_rain(p))

    def test_wind(self):
        p = TexturePreset("t", "wind", duration_s=0.5)
        self._assert_valid(synthesize_wind(p))

    def test_space(self):
        p = TexturePreset("t", "space", duration_s=0.5)
        self._assert_valid(synthesize_space(p))

    def test_static(self):
        p = TexturePreset("t", "static", duration_s=0.5)
        self._assert_valid(synthesize_static(p))

    def test_ocean(self):
        p = TexturePreset("t", "ocean", duration_s=0.5)
        self._assert_valid(synthesize_ocean(p))

    def test_router_all_types(self):
        for ttype in ("rain", "wind", "space", "static", "ocean"):
            p = TexturePreset("t", ttype, duration_s=0.3)
            signal = synthesize_texture(p)
            self.assertGreater(len(signal), 0)

    def test_router_unknown(self):
        p = TexturePreset("t", "laser")
        with self.assertRaises(ValueError):
            synthesize_texture(p)


class TestBanks(unittest.TestCase):
    """Test texture banks."""

    def test_rain_texture_bank(self):
        bank = rain_texture_bank()
        self.assertEqual(bank.name, "RAIN_TEXTURES")
        self.assertEqual(len(bank.presets), 4)
        for p in bank.presets:
            self.assertEqual(p.texture_type, "rain")

    def test_wind_texture_bank(self):
        bank = wind_texture_bank()
        self.assertEqual(bank.name, "WIND_TEXTURES")
        self.assertEqual(len(bank.presets), 4)

    def test_space_texture_bank(self):
        bank = space_texture_bank()
        self.assertEqual(bank.name, "SPACE_TEXTURES")
        self.assertEqual(len(bank.presets), 4)

    def test_static_texture_bank(self):
        bank = static_texture_bank()
        self.assertEqual(bank.name, "STATIC_TEXTURES")
        self.assertEqual(len(bank.presets), 4)

    def test_ocean_texture_bank(self):
        bank = ocean_texture_bank()
        self.assertEqual(bank.name, "OCEAN_TEXTURES")
        self.assertEqual(len(bank.presets), 4)

    def test_all_banks_registered(self):
        self.assertEqual(len(ALL_TEXTURE_BANKS), 5)

    def test_all_banks_synthesize(self):
        for bank_name, gen_fn in ALL_TEXTURE_BANKS.items():
            bank = gen_fn()
            for preset in bank.presets:
                signal = synthesize_texture(preset)
                self.assertGreater(len(signal), 0,
                                   f"Failed: {bank_name}/{preset.name}")

    def test_total_presets_is_20(self):
        total = sum(len(fn().presets) for fn in ALL_TEXTURE_BANKS.values())
        self.assertEqual(total, 20)


class TestManifest(unittest.TestCase):
    """Test manifest writing."""

    def test_writes_json(self):
        banks = {n: fn() for n, fn in ALL_TEXTURE_BANKS.items()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_texture_manifest(banks, tmpdir)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("banks", data)
            self.assertEqual(len(data["banks"]), 5)


if __name__ == "__main__":
    unittest.main()
