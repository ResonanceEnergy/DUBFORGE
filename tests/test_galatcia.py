"""Tests for engine.galatcia — GALATCIA Integration."""

import json
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from engine.galatcia import (
    DEFAULT_GALATCIA_ROOT,
    FXP_PREFIX_MAP,
    SAMPLE_CATEGORY_MAP,
    GalatciaCatalog,
    GalatciaPreset,
    GalatciaRack,
    GalatciaSample,
    GalatciaWavetable,
    build_galatcia_manifest,
    build_galatcia_marketplace_metadata,
    catalog_galatcia,
    export_all_galatcia,
    export_galatcia_presets,
    export_galatcia_racks,
    export_galatcia_samples,
    export_galatcia_serumpack,
    export_galatcia_wavetables,
    ingest_fxp_presets,
    read_wav_samples,
    read_wavetable_frames,
)
from engine.fxp_writer import FXP_MAGIC, FXP_REGULAR, FXPPreset


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS — build a fake GALATCIA folder structure for testing
# ═══════════════════════════════════════════════════════════════════════════

def _write_test_wav(path: Path, n_samples: int = 4096,
                    sample_rate: int = 44100, n_channels: int = 1) -> None:
    """Write a minimal 16-bit WAV file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.random.default_rng(42).uniform(-0.5, 0.5, n_samples)
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _write_test_fxp(path: Path, name: str = "TestPreset",
                    n_params: int = 4) -> None:
    """Write a minimal valid .fxp file (regular float-param format)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    plugin_id = struct.pack(">4s", b"DubF")
    plugin_id_int = struct.unpack(">I", plugin_id)[0]

    name_bytes = name.encode("ascii")[:28].ljust(28, b"\x00")
    param_data = b""
    for i in range(n_params):
        param_data += struct.pack(">f", i * 0.25)

    # FXP regular format: magic + size + fxMagic + version +
    # pluginId + fxVersion + numParams + name + params
    body = b""
    body += FXP_REGULAR                        # fxMagic
    body += struct.pack(">I", 1)               # version
    body += struct.pack(">I", plugin_id_int)   # pluginID
    body += struct.pack(">I", 1)               # fxVersion
    body += struct.pack(">I", n_params)        # numParams
    body += name_bytes                         # prgName
    body += param_data                         # params

    data = FXP_MAGIC
    data += struct.pack(">I", len(body))       # size
    data += body

    with open(path, "wb") as f:
        f.write(data)


def _build_fake_galatcia(root: Path) -> None:
    """Create a minimal GALATCIA directory tree for testing."""
    # Presets
    presets_dir = root / "Black Octopus - Brutal Dubstep and Riddim"
    for name in ["BS Growler", "BS Thicc", "LD Spicy",
                 "PAD Haven", "PL Peas", "SFX Laser"]:
        _write_test_fxp(presets_dir / f"{name}.fxp", name)

    # Samples
    samples_dir = root / "Samples"
    for cat, names in [
        ("Drum One Shots/KICKS", ["BODP_Kick_1.wav", "BODP_Kick_2.wav"]),
        ("Drum One Shots/Snares", ["BODP_Snare_1.wav"]),
        ("Drum One Shots/Claps", ["BODP_Clap_1.wav"]),
        ("Drum Loops/Beat Loops", ["BODP_Full_Beat_1.wav"]),
        ("FX/Impacts/Booms", ["BODP_Impact_1.wav"]),
        ("FX/Noise/Rising", ["BODP_Rising_1.wav"]),
        ("FX/Shepard Tones", ["BODP_Shepard_F_1.wav"]),
    ]:
        for fname in names:
            _write_test_wav(samples_dir / cat / fname)

    # Wavetables
    wt_dir = root / "ERB NEURO WT"
    for name in ["Basic Shapes.wav", "bitreduced.wav", "VOX-C1.wav"]:
        _write_test_wav(wt_dir / name, n_samples=2048 * 2)

    # Ableton Racks
    racks_dir = root / "Ableton Racks"
    racks_dir.mkdir(parents=True, exist_ok=True)
    (racks_dir / "Conclusion.adg").write_bytes(b"<fake-adg/>")
    (racks_dir / "Introduction.adg").write_bytes(b"<fake-adg/>")

    # SerumPack (just a dummy file)
    (root / "ERB N DUB NEURO DNB.SerumPack").write_bytes(b"\x00" * 100)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — CATALOG
# ═══════════════════════════════════════════════════════════════════════════

class TestCatalog(unittest.TestCase):
    """Test catalog_galatcia() discovery."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="galatcia_test_")
        cls.root = Path(cls.tmpdir) / "GALATCIA"
        _build_fake_galatcia(cls.root)
        cls.catalog = catalog_galatcia(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_catalog_finds_presets(self):
        self.assertEqual(len(self.catalog.presets), 6)

    def test_preset_categories(self):
        cats = {p.category for p in self.catalog.presets}
        self.assertIn("bass", cats)
        self.assertIn("lead", cats)
        self.assertIn("pad", cats)

    def test_catalog_finds_samples(self):
        self.assertEqual(len(self.catalog.samples), 8)

    def test_sample_categories(self):
        cats = {s.category for s in self.catalog.samples}
        self.assertIn("kicks", cats)
        self.assertIn("snares", cats)
        self.assertIn("impacts", cats)

    def test_catalog_finds_wavetables(self):
        self.assertEqual(len(self.catalog.wavetables), 3)

    def test_catalog_finds_racks(self):
        self.assertEqual(len(self.catalog.racks), 2)

    def test_catalog_finds_serumpack(self):
        self.assertTrue(self.catalog.serumpack_path)

    def test_total_files(self):
        # 6 presets + 8 samples + 3 wavetables + 2 racks + 1 serumpack
        self.assertEqual(self.catalog.total_files, 20)

    def test_summary(self):
        s = self.catalog.summary()
        self.assertEqual(s["presets"], 6)
        self.assertEqual(s["samples"], 8)
        self.assertEqual(s["wavetables"], 3)

    def test_missing_root_returns_empty(self):
        cat = catalog_galatcia(Path("/nonexistent/path"))
        self.assertEqual(cat.total_files, 0)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — WAV READING
# ═══════════════════════════════════════════════════════════════════════════

class TestReadWav(unittest.TestCase):
    """Test read_wav_samples() and read_wavetable_frames()."""

    def test_read_wav_returns_float64(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            path = Path(tf.name)
        try:
            _write_test_wav(path, n_samples=1024)
            audio = read_wav_samples(path)
            self.assertEqual(audio.dtype, np.float64)
            self.assertEqual(len(audio), 1024)
        finally:
            path.unlink(missing_ok=True)

    def test_read_wav_normalized(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            path = Path(tf.name)
        try:
            _write_test_wav(path, n_samples=512)
            audio = read_wav_samples(path)
            self.assertLessEqual(np.max(np.abs(audio)), 1.0)
        finally:
            path.unlink(missing_ok=True)

    def test_read_stereo_collapses_to_mono(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            path = Path(tf.name)
        try:
            _write_test_wav(path, n_samples=1024, n_channels=2)
            audio = read_wav_samples(path)
            self.assertEqual(len(audio), 512)  # 1024 frames / 2 ch → mono
        finally:
            path.unlink(missing_ok=True)

    def test_read_wavetable_frames_splits(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            path = Path(tf.name)
        try:
            _write_test_wav(path, n_samples=2048 * 4)
            frames = read_wavetable_frames(path, frame_size=2048)
            self.assertEqual(len(frames), 4)
            for f in frames:
                self.assertEqual(len(f), 2048)
        finally:
            path.unlink(missing_ok=True)

    def test_short_wav_pads_to_one_frame(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            path = Path(tf.name)
        try:
            _write_test_wav(path, n_samples=512)
            frames = read_wavetable_frames(path, frame_size=2048)
            self.assertEqual(len(frames), 1)
            self.assertEqual(len(frames[0]), 2048)
        finally:
            path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — FXP INGEST
# ═══════════════════════════════════════════════════════════════════════════

class TestIngestFxp(unittest.TestCase):
    """Test ingest_fxp_presets() parsing."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="galatcia_fxp_test_")
        cls.root = Path(cls.tmpdir) / "GALATCIA"
        _build_fake_galatcia(cls.root)
        cls.catalog = catalog_galatcia(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_groups_by_category(self):
        grouped = ingest_fxp_presets(self.catalog)
        self.assertIn("bass", grouped)
        self.assertEqual(len(grouped["bass"]), 2)

    def test_parsed_preset_has_params(self):
        grouped = ingest_fxp_presets(self.catalog)
        preset = grouped["bass"][0]
        self.assertIsInstance(preset, FXPPreset)
        self.assertEqual(len(preset.params), 4)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — EXPORT
# ═══════════════════════════════════════════════════════════════════════════

class TestExport(unittest.TestCase):
    """Test all export functions."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="galatcia_export_test_")
        cls.root = Path(cls.tmpdir) / "GALATCIA"
        cls.out = Path(cls.tmpdir) / "output"
        _build_fake_galatcia(cls.root)
        cls.catalog = catalog_galatcia(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_export_samples(self):
        paths = export_galatcia_samples(self.catalog, str(self.out))
        self.assertEqual(len(paths), 8)
        for p in paths:
            self.assertTrue(Path(p).exists())

    def test_export_wavetables(self):
        paths = export_galatcia_wavetables(self.catalog, str(self.out))
        self.assertEqual(len(paths), 3)

    def test_export_presets(self):
        paths = export_galatcia_presets(self.catalog, str(self.out))
        self.assertEqual(len(paths), 6)

    def test_export_racks(self):
        paths = export_galatcia_racks(self.catalog, str(self.out))
        self.assertEqual(len(paths), 2)

    def test_export_serumpack(self):
        path = export_galatcia_serumpack(self.catalog, str(self.out))
        self.assertTrue(path)
        self.assertTrue(Path(path).exists())

    def test_export_samples_categorized(self):
        export_galatcia_samples(self.catalog, str(self.out))
        cat_dirs = list(
            (self.out / "galatcia" / "samples").iterdir()
        )
        cat_names = {d.name for d in cat_dirs if d.is_dir()}
        self.assertIn("kicks", cat_names)
        self.assertIn("snares", cat_names)

    def test_export_presets_by_category(self):
        export_galatcia_presets(self.catalog, str(self.out))
        cat_dirs = list(
            (self.out / "galatcia" / "presets").iterdir()
        )
        cat_names = {d.name for d in cat_dirs if d.is_dir()}
        self.assertIn("bass", cat_names)
        self.assertIn("lead", cat_names)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

class TestManifest(unittest.TestCase):
    """Test manifest and marketplace metadata generation."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="galatcia_manifest_test_")
        cls.root = Path(cls.tmpdir) / "GALATCIA"
        cls.out = Path(cls.tmpdir) / "output"
        _build_fake_galatcia(cls.root)
        cls.catalog = catalog_galatcia(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_manifest_structure(self):
        m = build_galatcia_manifest(self.catalog, str(self.out))
        self.assertIn("collections", m)
        self.assertIn("black_octopus_brutal_dubstep", m["collections"])
        self.assertIn("erb_neuro_wt", m["collections"])
        self.assertIn("samples", m["collections"])
        self.assertIn("ableton_racks", m["collections"])

    def test_manifest_preset_counts(self):
        m = build_galatcia_manifest(self.catalog, str(self.out))
        bo = m["collections"]["black_octopus_brutal_dubstep"]
        self.assertEqual(bo["presets"], 6)
        self.assertIn("bass", bo["categories"])
        self.assertEqual(bo["categories"]["bass"], 2)

    def test_manifest_writes_json(self):
        build_galatcia_manifest(self.catalog, str(self.out))
        json_path = self.out / "galatcia" / "galatcia_manifest.json"
        self.assertTrue(json_path.exists())
        data = json.loads(json_path.read_text())
        self.assertIn("phi", data)

    def test_marketplace_metadata(self):
        m = build_galatcia_marketplace_metadata(self.catalog, str(self.out))
        self.assertEqual(m["name"], "DUBFORGE \u00d7 GALATCIA")
        self.assertEqual(len(m["samples"]), 8)

    def test_marketplace_writes_json(self):
        build_galatcia_marketplace_metadata(self.catalog, str(self.out))
        json_path = self.out / "galatcia" / "splice_metadata.json"
        self.assertTrue(json_path.exists())


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipeline(unittest.TestCase):
    """Test export_all_galatcia() end-to-end."""

    def test_full_pipeline(self):
        with tempfile.TemporaryDirectory(prefix="galatcia_full_") as tmpdir:
            root = Path(tmpdir) / "GALATCIA"
            out = Path(tmpdir) / "output"
            _build_fake_galatcia(root)
            result = export_all_galatcia(
                galatcia_root=root,
                output_dir=str(out),
            )
            self.assertEqual(result["samples_exported"], 8)
            self.assertEqual(result["wavetables_exported"], 3)
            self.assertEqual(result["presets_exported"], 6)
            self.assertEqual(result["racks_exported"], 2)
            self.assertTrue(result["serumpack_exported"])
            self.assertEqual(result["total_files"], 20)

    def test_missing_folder_returns_error(self):
        result = export_all_galatcia(
            galatcia_root="/nonexistent/galatcia",
            output_dir="/tmp/galatcia_test_out",
        )
        self.assertIn("error", result)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

class TestDataModel(unittest.TestCase):
    """Test dataclass fields and constants."""

    def test_fxp_prefix_map_covers_all(self):
        expected = {"BS", "LD", "PAD", "PL", "SFX", "SYN"}
        self.assertEqual(set(FXP_PREFIX_MAP.keys()), expected)

    def test_sample_category_map_has_entries(self):
        self.assertGreater(len(SAMPLE_CATEGORY_MAP), 10)

    def test_galatcia_catalog_summary(self):
        cat = GalatciaCatalog(root="/test")
        cat.presets = [GalatciaPreset("a", "a.fxp", "BS", "bass")]
        cat.samples = [GalatciaSample("x.wav", "kicks", "KICKS")]
        s = cat.summary()
        self.assertEqual(s["presets"], 1)
        self.assertEqual(s["samples"], 1)
        self.assertEqual(s["total_files"], 2)

    def test_default_root_is_path(self):
        self.assertIsInstance(DEFAULT_GALATCIA_ROOT, Path)


if __name__ == "__main__":
    unittest.main()
