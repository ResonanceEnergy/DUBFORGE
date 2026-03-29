"""Tests for engine.ableton_rack_builder — .adg Drum Rack Export."""

import gzip
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from engine.ableton_rack_builder import (
    build_adg_xml,
    export_128_rack_adg,
    write_adg,
)
from engine.dojo import RackCategory, RackZone, build_128_rack


class TestBuildAdgXml(unittest.TestCase):
    """Test XML generation for Drum Rack."""

    def _zone_dict(self, **kw):
        return {"note_start": 36, "note_end": 36,
                "category": "KICKS", "sample_slot": 0, "label": "Kick 1", **kw}

    def _cat_dict(self, **kw):
        return {"name": "KICKS", "zone_count": 1,
                "note_range_start": 36, "note_range_end": 36,
                "color": "#444444", "description": "Kicks", **kw}

    def test_returns_bytes(self):
        xml = build_adg_xml([self._zone_dict()], [self._cat_dict()], "TEST")
        self.assertIsInstance(xml, bytes)

    def test_valid_xml(self):
        xml = build_adg_xml([self._zone_dict()], [self._cat_dict()], "TEST")
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "Ableton")

    def test_drum_branches_match_zones(self):
        zones = [
            self._zone_dict(note_start=36, note_end=36, category="KICKS", label="Kick 1"),
            self._zone_dict(note_start=37, note_end=37, category="SNARES", label="Snare 1"),
        ]
        cats = [
            self._cat_dict(name="KICKS"),
            self._cat_dict(name="SNARES", note_range_start=37, note_range_end=37),
        ]
        xml = build_adg_xml(zones, cats, "TEST")
        root = ET.fromstring(xml)
        branches = root.findall(".//DrumBranch")
        self.assertEqual(len(branches), 2)


class TestWriteAdg(unittest.TestCase):
    """Test writing gzipped .adg files."""

    def test_write_creates_file(self):
        xml = b"<Ableton/>"
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "test.adg")
            write_adg(path, xml)
            self.assertTrue(Path(path).exists())
            # Verify it's gzipped
            with gzip.open(path, "rb") as f:
                content = f.read()
            self.assertEqual(content, xml)


class TestExport128RackAdg(unittest.TestCase):
    """Test full 128 Rack export."""

    def test_export_creates_files(self):
        with tempfile.TemporaryDirectory() as td:
            paths = export_128_rack_adg(td)
            self.assertIsInstance(paths, list)
            self.assertGreater(len(paths), 0)

    def test_main_rack_exists(self):
        with tempfile.TemporaryDirectory() as td:
            paths = export_128_rack_adg(td)
            names = [Path(p).name for p in paths]
            self.assertIn("DUBFORGE_128_Rack.adg", names)

    def test_zone_map_json(self):
        with tempfile.TemporaryDirectory() as td:
            export_128_rack_adg(td)
            zm = Path(td) / "ableton" / "drum_racks" / "zone_map.json"
            self.assertTrue(zm.exists())
            data = json.loads(zm.read_text())
            self.assertIsInstance(data, dict)
            self.assertEqual(data["total_zones"], 128)


class TestRack128Data(unittest.TestCase):
    """Test build_128_rack data from dojo module."""

    def test_rack_has_zones(self):
        rack = build_128_rack()
        self.assertGreater(len(rack["zones"]), 0)

    def test_rack_has_128_zones(self):
        rack = build_128_rack()
        self.assertEqual(rack["total_zones"], 128)

    def test_rack_has_categories(self):
        rack = build_128_rack()
        self.assertGreater(len(rack["categories"]), 0)


if __name__ == "__main__":
    unittest.main()
