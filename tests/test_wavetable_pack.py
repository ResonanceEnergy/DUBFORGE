"""Tests for engine.wavetable_pack — Wavetable Pack Generator."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine.wavetable_pack import (
    export_all_wavetable_packs,
    export_wavetable_pack,
    generate_fm_ratio_sweep,
    generate_growl_vowel_pack,
    generate_harmonic_sweep,
    generate_morph_pack,
)


class TestFMRatioSweep(unittest.TestCase):
    """Test FM ratio sweep wavetable generator."""

    def test_returns_list(self):
        tables = generate_fm_ratio_sweep(n_tables=3, n_frames=8)
        self.assertIsInstance(tables, list)
        self.assertEqual(len(tables), 3)

    def test_each_entry_is_name_frames_tuple(self):
        tables = generate_fm_ratio_sweep(n_tables=2, n_frames=4)
        for name, frames in tables:
            self.assertIsInstance(name, str)
            self.assertIsInstance(frames, list)
            self.assertGreater(len(frames), 0)

    def test_frames_are_numpy(self):
        tables = generate_fm_ratio_sweep(n_tables=2, n_frames=4)
        _, frames = tables[0]
        for f in frames:
            self.assertIsInstance(f, np.ndarray)


class TestHarmonicSweep(unittest.TestCase):
    """Test harmonic sweep wavetable generator."""

    def test_returns_list(self):
        tables = generate_harmonic_sweep(n_tables=2, n_frames=4)
        self.assertIsInstance(tables, list)
        self.assertEqual(len(tables), 2)


class TestMorphPack(unittest.TestCase):
    """Test morph pack wavetable generator."""

    def test_returns_list(self):
        tables = generate_morph_pack(n_tables=2, n_frames=4)
        self.assertIsInstance(tables, list)
        self.assertEqual(len(tables), 2)


class TestGrowlVowelPack(unittest.TestCase):
    """Test growl vowel pack generator."""

    def test_returns_20_tables(self):
        tables = generate_growl_vowel_pack(n_frames=4)
        # 5 vowels × 4 drive levels = 20
        self.assertEqual(len(tables), 20)

    def test_names_contain_vowel(self):
        tables = generate_growl_vowel_pack(n_frames=4)
        vowels = {"a", "o", "e", "i", "u"}
        for name, _ in tables:
            lower = name.lower()
            found = any(f"vowel_{v}" in lower for v in vowels)
            self.assertTrue(found, f"Expected vowel letter in name: {name}")


class TestExportWavetablePack(unittest.TestCase):
    """Test export to disk."""

    def test_export_writes_files(self):
        tables = generate_fm_ratio_sweep(n_tables=2, n_frames=4)
        with tempfile.TemporaryDirectory() as td:
            paths = export_wavetable_pack("test_pack", tables, td)
            self.assertGreater(len(paths), 0)
            # Check manifest exists
            manifest = Path(td) / "wavetable_packs" / "test_pack" / "manifest.json"
            self.assertTrue(manifest.exists())
            data = json.loads(manifest.read_text())
            self.assertEqual(data["pack"], "test_pack")


class TestExportAllWavetablePacks(unittest.TestCase):
    """Test full export pipeline."""

    def test_export_all(self):
        with tempfile.TemporaryDirectory() as td:
            paths = export_all_wavetable_packs(td)
            self.assertIsInstance(paths, list)
            self.assertGreater(len(paths), 0)
            # Should have multiple subdirectories
            pack_dir = Path(td) / "wavetable_packs"
            self.assertTrue(pack_dir.exists())


if __name__ == "__main__":
    unittest.main()
