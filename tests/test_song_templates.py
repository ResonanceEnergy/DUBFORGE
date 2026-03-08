"""Tests for engine.song_templates — Song Templates."""

import tempfile
import unittest

from engine.song_templates import (
    ALL_SONG_TEMPLATE_BANKS,
    SongSection,
    SongTemplate,
    emotive_template_bank,
    experimental_template_bank,
    hybrid_template_bank,
    weapon_template_bank,
    write_song_templates_manifest,
)


class TestSongSection(unittest.TestCase):
    def test_defaults(self):
        s = SongSection("intro", 8)
        self.assertEqual(s.bars, 8)
        self.assertEqual(s.beats, 32)
        self.assertAlmostEqual(s.energy, 0.5)

    def test_custom(self):
        s = SongSection("drop", 16, "Full weapon drop", 1.0)
        self.assertEqual(s.bars, 16)
        self.assertAlmostEqual(s.energy, 1.0)


class TestSongTemplate(unittest.TestCase):
    def test_properties(self):
        t = SongTemplate(
            name="TEST",
            category="weapon",
            bpm=150.0,
            sections=[
                SongSection("intro", 8, energy=0.1),
                SongSection("drop", 16, energy=1.0),
                SongSection("outro", 8, energy=0.1),
            ],
        )
        self.assertEqual(t.total_bars, 32)
        self.assertGreater(t.duration_s, 0)
        self.assertGreater(t.golden_bar, 0)
        self.assertLessEqual(t.golden_bar, t.total_bars)


class TestWeaponTemplates(unittest.TestCase):
    def test_weapon_bank(self):
        bank = weapon_template_bank()
        self.assertEqual(len(bank.templates), 5)
        for t in bank.templates:
            self.assertEqual(t.category, "weapon")
            self.assertGreater(t.total_bars, 0)
            self.assertGreater(len(t.sections), 0)


class TestEmotiveTemplates(unittest.TestCase):
    def test_emotive_bank(self):
        bank = emotive_template_bank()
        self.assertEqual(len(bank.templates), 5)
        for t in bank.templates:
            self.assertEqual(t.category, "emotive")


class TestHybridTemplates(unittest.TestCase):
    def test_hybrid_bank(self):
        bank = hybrid_template_bank()
        self.assertEqual(len(bank.templates), 5)
        for t in bank.templates:
            self.assertEqual(t.category, "hybrid")


class TestExperimentalTemplates(unittest.TestCase):
    def test_experimental_bank(self):
        bank = experimental_template_bank()
        self.assertEqual(len(bank.templates), 5)
        for t in bank.templates:
            self.assertEqual(t.category, "experimental")

    def test_fibonacci_bars(self):
        """Fibonacci template should have bar counts from the sequence."""
        bank = experimental_template_bank()
        fib_template = bank.templates[0]  # first is fibonacci
        bars = [s.bars for s in fib_template.sections]
        # Should include Fibonacci numbers
        fib_set = {1, 2, 3, 5, 8, 13}
        for b in bars:
            self.assertIn(b, fib_set | {4, 16, 21, 6, 10, 12, 7, 17},
                          f"Bar count {b} not in expected set")


class TestRegistry(unittest.TestCase):
    def test_registry(self):
        self.assertEqual(len(ALL_SONG_TEMPLATE_BANKS), 4)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_song_templates_manifest(td)
            self.assertEqual(len(manifest["banks"]), 4)
            total = sum(b["template_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 20)


if __name__ == "__main__":
    unittest.main()
