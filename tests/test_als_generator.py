"""Tests for engine.als_generator — Ableton Live Set (.als) Generator."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

import gzip
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from engine.als_generator import (
    ALL_ALS_TEMPLATES,
    ALSProject,
    ALSScene,
    ALSTrack,
    build_als_xml,
    dubstep_weapon_session,
    emotive_melodic_session,
    hybrid_fractal_session,
    write_als,
    write_als_json,
)


class TestALSTrack(unittest.TestCase):
    """Test ALSTrack dataclass."""

    def test_defaults(self):
        t = ALSTrack(name="Test")
        self.assertEqual(t.track_type, "midi")
        self.assertEqual(t.volume_db, 0.0)
        self.assertFalse(t.mute)
        self.assertFalse(t.solo)

    def test_custom_track(self):
        t = ALSTrack(name="Bass", track_type="audio", color=5, volume_db=-3.0)
        self.assertEqual(t.track_type, "audio")
        self.assertEqual(t.color, 5)


class TestALSScene(unittest.TestCase):
    """Test ALSScene dataclass."""

    def test_defaults(self):
        s = ALSScene(name="DROP")
        self.assertEqual(s.tempo, 150.0)

    def test_custom(self):
        s = ALSScene(name="INTRO", tempo=140.0, time_sig=(3, 4))
        self.assertEqual(s.time_sig, (3, 4))


class TestALSProject(unittest.TestCase):
    """Test ALSProject dataclass."""

    def test_empty_project(self):
        p = ALSProject(name="Test")
        self.assertEqual(len(p.tracks), 0)
        self.assertEqual(len(p.scenes), 0)
        self.assertEqual(p.bpm, 150.0)


class TestBuildALSXML(unittest.TestCase):
    """Test XML generation."""

    def test_produces_element(self):
        project = ALSProject(name="Test", bpm=150.0)
        root = build_als_xml(project)
        self.assertIsInstance(root, ET.Element)
        self.assertEqual(root.tag, "Ableton")

    def test_has_live_set(self):
        project = ALSProject(name="Test")
        root = build_als_xml(project)
        live_set = root.find("LiveSet")
        self.assertIsNotNone(live_set)

    def test_has_transport(self):
        project = ALSProject(name="Test", bpm=140.0)
        root = build_als_xml(project)
        transport = root.find("LiveSet/Transport")
        self.assertIsNotNone(transport)

    def test_tracks_in_xml(self):
        project = ALSProject(
            name="Test",
            tracks=[
                ALSTrack(name="MIDI_1", track_type="midi"),
                ALSTrack(name="AUDIO_1", track_type="audio"),
            ],
        )
        root = build_als_xml(project)
        tracks = root.find("LiveSet/Tracks")
        self.assertIsNotNone(tracks)
        midi_tracks = tracks.findall("MidiTrack")
        audio_tracks = tracks.findall("AudioTrack")
        self.assertEqual(len(midi_tracks), 1)
        self.assertEqual(len(audio_tracks), 1)

    def test_scenes_in_xml(self):
        project = ALSProject(
            name="Test",
            scenes=[ALSScene(name="A"), ALSScene(name="B")],
        )
        root = build_als_xml(project)
        scenes = root.find("LiveSet/Scenes")
        self.assertIsNotNone(scenes)
        self.assertEqual(len(scenes.findall("Scene")), 2)

    def test_return_track(self):
        project = ALSProject(
            name="Test",
            tracks=[ALSTrack(name="VERB", track_type="return")],
        )
        root = build_als_xml(project)
        returns = root.find("LiveSet/Tracks").findall("ReturnTrack")
        self.assertEqual(len(returns), 1)


class TestWriteALS(unittest.TestCase):
    """Test .als file writing."""

    def test_creates_gzip_file(self):
        project = ALSProject(name="Test", bpm=150.0,
                              tracks=[ALSTrack(name="T1")])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.als")
            result = write_als(project, path)
            self.assertTrue(os.path.exists(result))
            # Verify it's valid gzip
            with gzip.open(result, "rb") as f:
                data = f.read()
            self.assertIn(b"Ableton", data)

    def test_xml_is_parseable(self):
        project = dubstep_weapon_session()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "weapon.als")
            write_als(project, path)
            with gzip.open(path, "rb") as f:
                data = f.read()
            root = ET.fromstring(data)
            self.assertEqual(root.tag, "Ableton")

    def test_creates_parent_dirs(self):
        project = ALSProject(name="Test")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "test.als")
            write_als(project, path)
            self.assertTrue(os.path.exists(path))


class TestWriteALSJson(unittest.TestCase):
    """Test JSON structure output."""

    def test_writes_json(self):
        project = ALSProject(name="Test", bpm=140.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            result = write_als_json(project, path)
            self.assertTrue(os.path.exists(result))
            import json
            with open(result) as f:
                data = json.load(f)
            self.assertEqual(data["name"], "Test")
            self.assertEqual(data["bpm"], 140.0)


class TestSessionTemplates(unittest.TestCase):
    """Test all session template generators."""

    def test_weapon_session(self):
        p = dubstep_weapon_session()
        self.assertEqual(p.name, "DUBFORGE_WEAPON")
        self.assertEqual(p.bpm, 150.0)
        self.assertGreater(len(p.tracks), 0)
        self.assertGreater(len(p.scenes), 0)

    def test_emotive_session(self):
        p = emotive_melodic_session()
        self.assertEqual(p.name, "DUBFORGE_EMOTIVE")
        self.assertEqual(p.bpm, 140.0)

    def test_hybrid_fractal_session(self):
        p = hybrid_fractal_session()
        self.assertEqual(p.name, "DUBFORGE_HYBRID_FRACTAL")
        self.assertGreater(len(p.tracks), 10)

    def test_all_templates_registered(self):
        self.assertEqual(len(ALL_ALS_TEMPLATES), 3)
        for name, fn in ALL_ALS_TEMPLATES.items():
            p = fn()
            self.assertIsInstance(p, ALSProject)
            self.assertGreater(len(p.tracks), 0)

    def test_all_templates_write(self):
        """All templates should produce valid .als files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, fn in ALL_ALS_TEMPLATES.items():
                project = fn()
                path = os.path.join(tmpdir, f"{name}.als")
                write_als(project, path)
                self.assertTrue(os.path.exists(path))


class TestHybridPhiLevels(unittest.TestCase):
    """Test that hybrid fractal template uses phi-ratio track levels."""

    def test_volume_decay(self):
        p = hybrid_fractal_session()
        # Non-return tracks should have decreasing volumes
        main_tracks = [t for t in p.tracks if t.track_type != "return"]
        volumes = [t.volume_db for t in main_tracks]
        # First track should be loudest (0 dB)
        self.assertAlmostEqual(volumes[0], 0.0, places=1)
        # Volumes should generally decrease
        self.assertLess(volumes[-1], volumes[0])


class TestAutoPopulateStems(unittest.TestCase):
    """Test stem auto-population for Session 118."""

    def test_auto_populate_returns_path(self):
        from engine.als_generator import auto_populate_stems
        with tempfile.TemporaryDirectory() as tmpdir:
            project = dubstep_weapon_session()
            result = auto_populate_stems(project, stem_dir=tmpdir, output_dir=tmpdir)
            self.assertTrue(result.endswith(".als"))

    def test_auto_populate_creates_file(self):
        from engine.als_generator import auto_populate_stems
        with tempfile.TemporaryDirectory() as tmpdir:
            project = dubstep_weapon_session()
            result = auto_populate_stems(project, stem_dir=tmpdir, output_dir=tmpdir)
            self.assertTrue(os.path.exists(result))

    def test_auto_populate_enriched_name(self):
        from engine.als_generator import auto_populate_stems
        with tempfile.TemporaryDirectory() as tmpdir:
            project = dubstep_weapon_session()
            result = auto_populate_stems(project, stem_dir=tmpdir, output_dir=tmpdir)
            self.assertIn("STEMS", os.path.basename(result))

    def test_auto_populate_with_wav_files(self):
        import wave

        import numpy as np

        from engine.als_generator import auto_populate_stems
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy wav in stem_dir
            stem_dir = os.path.join(tmpdir, "stems")
            os.makedirs(stem_dir)
            wav_path = os.path.join(stem_dir, "bass_test.wav")
            sr = 44100
            data = np.zeros(sr, dtype=np.int16)
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(data.tobytes())
            project = dubstep_weapon_session()
            out_dir = os.path.join(tmpdir, "out")
            result = auto_populate_stems(project, stem_dir=stem_dir, output_dir=out_dir)
            self.assertTrue(os.path.exists(result))


class TestExportAllALS(unittest.TestCase):
    """Test export_all_als function."""

    def test_export_all_returns_paths(self):
        from engine.als_generator import export_all_als
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_all_als(tmpdir)
            self.assertIsInstance(paths, list)
            self.assertGreater(len(paths), 0)

    def test_export_all_creates_files(self):
        from engine.als_generator import export_all_als
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_all_als(tmpdir)
            for p in paths:
                self.assertTrue(os.path.exists(p))

    def test_export_all_includes_stems(self):
        from engine.als_generator import export_all_als
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_all_als(tmpdir)
            stem_paths = [p for p in paths if "STEMS" in os.path.basename(p)]
            self.assertGreater(len(stem_paths), 0)


if __name__ == "__main__":
    unittest.main()
