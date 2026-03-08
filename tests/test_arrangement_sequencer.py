"""Tests for engine.arrangement_sequencer — Arrangement Sequencer."""

import tempfile
import unittest

from engine.arrangement_sequencer import (
    ALL_ARRANGEMENT_BANKS,
    ArrangementTemplate,
    SectionDef,
    arrangement_duration_s,
    arrangement_energy_curve,
    arrangement_total_bars,
    build_arrangement,
    build_emotive_template,
    build_fibonacci_template,
    build_hybrid_template,
    build_weapon_template,
    emotive_arrangement_bank,
    fibonacci_arrangement_bank,
    golden_section_check,
    hybrid_arrangement_bank,
    weapon_arrangement_bank,
    write_arrangement_sequencer_manifest,
)


class TestSectionDef(unittest.TestCase):
    def test_defaults(self):
        s = SectionDef("intro")
        self.assertEqual(s.bars, 8)
        self.assertAlmostEqual(s.intensity, 0.5)
        self.assertEqual(s.elements, [])

    def test_custom(self):
        s = SectionDef("drop", 16, ["drums", "bass"], 1.0)
        self.assertEqual(s.bars, 16)
        self.assertAlmostEqual(s.intensity, 1.0)
        self.assertEqual(len(s.elements), 2)


class TestTemplateBuilders(unittest.TestCase):
    def test_weapon(self):
        t = build_weapon_template()
        self.assertEqual(t.template_type, "weapon")
        self.assertGreater(len(t.sections), 0)
        self.assertGreater(arrangement_total_bars(t), 0)

    def test_emotive(self):
        t = build_emotive_template()
        self.assertEqual(t.template_type, "emotive")
        self.assertGreater(arrangement_total_bars(t), 0)

    def test_hybrid(self):
        t = build_hybrid_template()
        self.assertEqual(t.template_type, "hybrid")

    def test_fibonacci(self):
        t = build_fibonacci_template()
        self.assertEqual(t.template_type, "fibonacci")


class TestAnalysis(unittest.TestCase):
    def test_total_bars(self):
        t = build_weapon_template()
        total = arrangement_total_bars(t)
        self.assertGreater(total, 40)  # weapon should be substantial

    def test_duration(self):
        t = build_weapon_template(bpm=150.0)
        dur = arrangement_duration_s(t)
        self.assertGreater(dur, 0)

    def test_energy_curve(self):
        t = build_weapon_template()
        curve = arrangement_energy_curve(t)
        self.assertGreater(len(curve), 0)
        for point in curve:
            self.assertIn("section", point)
            self.assertIn("intensity", point)

    def test_golden_section_check(self):
        t = build_weapon_template()
        result = golden_section_check(t)
        self.assertIn("total_bars", result)
        self.assertIn("golden_bar", result)
        self.assertIn("aligned", result)


class TestRouter(unittest.TestCase):
    def test_build_all_types(self):
        for ttype in ["weapon", "emotive", "hybrid", "fibonacci"]:
            t = build_arrangement(ttype)
            self.assertIsInstance(t, ArrangementTemplate)
            self.assertGreater(len(t.sections), 0)

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            build_arrangement("nonexistent")


class TestBanks(unittest.TestCase):
    def test_all_banks(self):
        for bank_fn in [weapon_arrangement_bank, emotive_arrangement_bank,
                        hybrid_arrangement_bank, fibonacci_arrangement_bank]:
            bank = bank_fn()
            self.assertEqual(len(bank.templates), 4)

    def test_registry(self):
        self.assertEqual(len(ALL_ARRANGEMENT_BANKS), 4)


class TestManifest(unittest.TestCase):
    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = write_arrangement_sequencer_manifest(td)
            self.assertEqual(len(manifest["banks"]), 4)
            total = sum(b["template_count"] for b in manifest["banks"].values())
            self.assertEqual(total, 16)


if __name__ == "__main__":
    unittest.main()
