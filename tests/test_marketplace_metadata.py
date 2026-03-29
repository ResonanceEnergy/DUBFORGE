"""Tests for engine.marketplace_metadata — Splice/Loopcloud Metadata."""

import json
import tempfile
import unittest
from pathlib import Path

from engine.marketplace_metadata import (
    GENRE_TAGS,
    INSTRUMENT_TAGS,
    MOOD_TAGS,
    PackMetadata,
    SampleMetadata,
    auto_tag_sample,
    build_pack_metadata,
    export_marketplace_metadata,
)


class TestSampleMetadata(unittest.TestCase):
    """Test SampleMetadata dataclass."""

    def test_to_splice_dict(self):
        m = SampleMetadata(
            filename="kick_001.wav",
            category="drums",
            subcategory="kicks",
            bpm=140,
            key="F",
            tags=["Dubstep"],
            instrument_tags=["Kick"],
        )
        d = m.to_splice_dict()
        self.assertEqual(d["filename"], "kick_001.wav")
        self.assertIn("Kick", d["tags"])
        # one_shot → bpm is None in Splice format
        self.assertIsNone(d["bpm"])

    def test_to_loopcloud_dict(self):
        m = SampleMetadata(
            filename="bass_sub_001.wav",
            category="bass",
            subcategory="sub_bass",
            bpm=140,
            key="F",
            tags=["Bass", "Sub Bass"],
        )
        d = m.to_loopcloud_dict()
        self.assertIn("category", d)
        self.assertIn("tags", d)
        self.assertEqual(d["bpm"], 140)


class TestAutoTagSample(unittest.TestCase):
    """Test auto-tag inference from filenames."""

    def test_kick_detection(self):
        m = auto_tag_sample("drums_kicks_001.wav", "drums", "kicks", 140, "F")
        self.assertIn("Kick", m.instrument_tags)

    def test_bass_sub_detection(self):
        m = auto_tag_sample("bass_sub_001.wav", "bass", "sub_bass", 140, "F")
        self.assertIn("Sub Bass", m.instrument_tags)

    def test_riser_detection(self):
        m = auto_tag_sample("fx_riser_001.wav", "fx", "risers", 140, "F")
        self.assertIn("Riser", m.instrument_tags)

    def test_always_has_dubstep_tag(self):
        m = auto_tag_sample("anything.wav", "misc", "misc", 140, "F")
        self.assertIn("Dubstep", m.tags)


class TestPackMetadata(unittest.TestCase):
    """Test PackMetadata dataclass."""

    def test_to_dict(self):
        pm = PackMetadata(
            name="DUBFORGE Test",
            author="DUBFORGE",
            version="1.0",
            bpm=140,
            key="F",
        )
        d = pm.to_dict()
        self.assertEqual(d["pack"]["name"], "DUBFORGE Test")
        self.assertEqual(d["pack"]["total_samples"], 0)


class TestBuildPackMetadata(unittest.TestCase):
    """Test scanning a directory for pack metadata."""

    def test_build_from_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            pm = build_pack_metadata(td, "test", 140, "F")
            self.assertEqual(len(pm.samples), 0)

    def test_build_with_wav_files(self):
        with tempfile.TemporaryDirectory() as td:
            # Create fake wav files
            for name in ["kick_001.wav", "snare_001.wav"]:
                (Path(td) / name).write_bytes(b"\x00" * 100)
            pm = build_pack_metadata(td, "test", 140, "F")
            self.assertEqual(len(pm.samples), 2)


class TestExportMarketplaceMetadata(unittest.TestCase):
    """Test full metadata export."""

    def test_export_creates_json_files(self):
        with tempfile.TemporaryDirectory() as td:
            pack_dir = Path(td) / "sample_packs"
            pack_dir.mkdir()
            (pack_dir / "test.wav").write_bytes(b"\x00" * 100)
            result = export_marketplace_metadata(str(pack_dir), "TEST", td)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["total_samples"], 1)
            # Should create marketplace directory with JSON files
            market_dir = Path(td) / "marketplace"
            self.assertTrue(market_dir.exists())


class TestConstants(unittest.TestCase):
    """Test module-level constants."""

    def test_genre_tags_not_empty(self):
        self.assertGreater(len(GENRE_TAGS), 0)

    def test_instrument_tags_has_drums(self):
        self.assertIn("drums", INSTRUMENT_TAGS)

    def test_mood_tags_not_empty(self):
        self.assertGreater(len(MOOD_TAGS), 0)


if __name__ == "__main__":
    unittest.main()
