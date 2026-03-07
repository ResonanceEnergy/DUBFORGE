"""Tests for engine.fxp_writer — FXP / VST2 Preset Writer."""

import os
import tempfile
import unittest

from engine.fxp_writer import (
    ALL_PRESETS,
    FXB_REGULAR,
    FXP_MAGIC,
    FXP_OPAQUE,
    FXP_REGULAR,
    FXPBank,
    FXPPreset,
    VSTParam,
    dubstep_growl_preset,
    dubstep_lead_preset,
    dubstep_pad_preset,
    dubstep_sub_preset,
    read_fxp,
    write_fxb,
    write_fxp,
    write_preset_manifest,
)


class TestVSTParam(unittest.TestCase):
    """Test VSTParam dataclass."""

    def test_creation(self):
        p = VSTParam(index=0, name="cutoff", value=0.5)
        self.assertEqual(p.index, 0)
        self.assertAlmostEqual(p.value, 0.5)
        self.assertEqual(p.display, "")

    def test_display(self):
        p = VSTParam(index=1, name="reso", value=0.3, display="30%")
        self.assertEqual(p.display, "30%")


class TestFXPPreset(unittest.TestCase):
    """Test FXPPreset dataclass."""

    def test_defaults(self):
        p = FXPPreset(name="Test")
        self.assertEqual(p.plugin_id, "DubF")
        self.assertFalse(p.is_opaque)
        self.assertEqual(len(p.params), 0)

    def test_opaque(self):
        p = FXPPreset(name="Test", chunk_data=b"\x00\x01\x02")
        self.assertTrue(p.is_opaque)

    def test_name_max_length(self):
        """Preset name should be encodeable."""
        p = FXPPreset(name="A" * 28)
        self.assertEqual(len(p.name), 28)


class TestFXPBank(unittest.TestCase):
    """Test FXPBank dataclass."""

    def test_empty_bank(self):
        b = FXPBank(name="TestBank")
        self.assertEqual(len(b.presets), 0)


class TestWriteFXP(unittest.TestCase):
    """Test FXP file writing."""

    def test_writes_file(self):
        preset = FXPPreset(
            name="Test",
            params=[VSTParam(0, "p0", 0.5), VSTParam(1, "p1", 0.7)],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            result = write_fxp(preset, path)
            self.assertTrue(os.path.exists(result))

    def test_file_has_magic(self):
        preset = FXPPreset(name="Test", params=[VSTParam(0, "p", 0.5)])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            write_fxp(preset, path)
            with open(path, "rb") as f:
                magic = f.read(4)
            self.assertEqual(magic, FXP_MAGIC)

    def test_regular_format_marker(self):
        preset = FXPPreset(name="Test", params=[VSTParam(0, "p", 0.5)])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            write_fxp(preset, path)
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[8:12], FXP_REGULAR)

    def test_opaque_format_marker(self):
        preset = FXPPreset(name="Test", chunk_data=b"\x01\x02\x03\x04")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            write_fxp(preset, path)
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[8:12], FXP_OPAQUE)

    def test_creates_parent_dirs(self):
        preset = FXPPreset(name="Test", params=[VSTParam(0, "p", 0.5)])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "test.fxp")
            write_fxp(preset, path)
            self.assertTrue(os.path.exists(path))


class TestReadFXP(unittest.TestCase):
    """Test FXP file reading (roundtrip)."""

    def test_roundtrip_regular(self):
        original = FXPPreset(
            name="RoundTrip",
            plugin_id="DubF",
            params=[
                VSTParam(0, "p0", 0.25),
                VSTParam(1, "p1", 0.75),
                VSTParam(2, "p2", 1.0),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            write_fxp(original, path)
            loaded = read_fxp(path)
            self.assertEqual(loaded.name, "RoundTrip")
            self.assertEqual(loaded.plugin_id, "DubF")
            self.assertEqual(len(loaded.params), 3)
            self.assertAlmostEqual(loaded.params[0].value, 0.25, places=4)
            self.assertAlmostEqual(loaded.params[1].value, 0.75, places=4)
            self.assertAlmostEqual(loaded.params[2].value, 1.0, places=4)

    def test_roundtrip_opaque(self):
        chunk = b"\xDE\xAD\xBE\xEF" * 10
        original = FXPPreset(name="Opaque", chunk_data=chunk)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxp")
            write_fxp(original, path)
            loaded = read_fxp(path)
            self.assertEqual(loaded.name, "Opaque")
            self.assertTrue(loaded.is_opaque)
            self.assertEqual(loaded.chunk_data, chunk)

    def test_invalid_file_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.fxp")
            with open(path, "wb") as f:
                f.write(b"NOT_FXP_DATA")
            with self.assertRaises(ValueError):
                read_fxp(path)


class TestWriteFXB(unittest.TestCase):
    """Test FXB bank writing."""

    def test_writes_bank(self):
        presets = [
            FXPPreset(name=f"P{i}", params=[VSTParam(0, "p", i * 0.25)])
            for i in range(4)
        ]
        bank = FXPBank(name="TestBank", presets=presets)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxb")
            result = write_fxb(bank, path)
            self.assertTrue(os.path.exists(result))

    def test_bank_has_magic(self):
        presets = [FXPPreset(name="P", params=[VSTParam(0, "p", 0.5)])]
        bank = FXPBank(name="Bank", presets=presets)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxb")
            write_fxb(bank, path)
            with open(path, "rb") as f:
                magic = f.read(4)
            self.assertEqual(magic, FXP_MAGIC)

    def test_bank_format_marker(self):
        presets = [FXPPreset(name="P", params=[VSTParam(0, "p", 0.5)])]
        bank = FXPBank(name="Bank", presets=presets)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxb")
            write_fxb(bank, path)
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[8:12], FXB_REGULAR)

    def test_empty_bank_raises(self):
        bank = FXPBank(name="Empty")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.fxb")
            with self.assertRaises(ValueError):
                write_fxb(bank, path)


class TestPresetManifest(unittest.TestCase):
    """Test preset manifest generation."""

    def test_writes_json(self):
        presets = {"sub": dubstep_sub_preset()}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_preset_manifest(presets, tmpdir)
            self.assertTrue(os.path.exists(path))
            import json
            with open(path) as f:
                data = json.load(f)
            self.assertIn("presets", data)
            self.assertIn("sub", data["presets"])


class TestDubstepPresets(unittest.TestCase):
    """Test all dubstep synth presets."""

    def test_sub_preset(self):
        p = dubstep_sub_preset()
        self.assertEqual(p.name, "DUBFORGE_SUB")
        self.assertGreater(len(p.params), 0)
        self.assertFalse(p.is_opaque)

    def test_growl_preset(self):
        p = dubstep_growl_preset()
        self.assertEqual(p.name, "DUBFORGE_GROWL")
        self.assertGreater(len(p.params), 15)

    def test_lead_preset(self):
        p = dubstep_lead_preset()
        self.assertEqual(p.name, "DUBFORGE_LEAD")

    def test_pad_preset(self):
        p = dubstep_pad_preset()
        self.assertEqual(p.name, "DUBFORGE_PAD")

    def test_all_presets_registered(self):
        self.assertEqual(len(ALL_PRESETS), 4)
        for name, fn in ALL_PRESETS.items():
            p = fn()
            self.assertIsInstance(p, FXPPreset)
            self.assertGreater(len(p.params), 0)

    def test_all_params_in_range(self):
        """All preset parameter values should be 0.0-1.0."""
        for name, fn in ALL_PRESETS.items():
            p = fn()
            for param in p.params:
                self.assertGreaterEqual(param.value, 0.0,
                                        f"{name}:{param.name} < 0")
                self.assertLessEqual(param.value, 1.0,
                                     f"{name}:{param.name} > 1")

    def test_all_presets_write(self):
        """All presets should produce valid .fxp files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, fn in ALL_PRESETS.items():
                preset = fn()
                path = os.path.join(tmpdir, f"{name}.fxp")
                write_fxp(preset, path)
                self.assertTrue(os.path.exists(path))
                # Verify roundtrip
                loaded = read_fxp(path)
                self.assertEqual(loaded.name, preset.name)
                self.assertEqual(len(loaded.params), len(preset.params))


if __name__ == "__main__":
    unittest.main()
