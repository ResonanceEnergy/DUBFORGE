"""Tests for engine.vip_pack — VIP Pack Workflow."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine.vip_pack import (
    VIPDelta,
    build_vip_pack,
    export_all_vip_packs,
    vip_layer_noise,
    vip_mutate_bass,
)


class TestVIPMutateBass(unittest.TestCase):
    """Test bass mutation for VIP variants."""

    def test_returns_audio_and_mutations(self):
        audio, mutations = vip_mutate_bass("sub_sine", 55.0, idx=0)
        self.assertIsInstance(audio, np.ndarray)
        self.assertIsInstance(mutations, list)
        self.assertGreater(len(mutations), 0)

    def test_type_rotation(self):
        _, mutations = vip_mutate_bass("sub_sine", 55.0, idx=0)
        # Should rotate sub_sine → reese
        type_mut = [m for m in mutations if "bass_type" in m]
        self.assertEqual(len(type_mut), 1)
        self.assertIn("reese", type_mut[0])

    def test_frequency_shift(self):
        _, mutations = vip_mutate_bass("fm", 100.0, idx=1)
        freq_mut = [m for m in mutations if "freq" in m]
        self.assertEqual(len(freq_mut), 1)
        # Frequency should have changed
        self.assertNotIn("100.0 → 100.0", freq_mut[0])

    def test_different_idx_different_results(self):
        audio1, _ = vip_mutate_bass("growl", 80.0, idx=0)
        audio2, _ = vip_mutate_bass("growl", 80.0, idx=1)
        # Different seeds should yield different audio
        self.assertFalse(np.array_equal(audio1, audio2))


class TestVIPLayerNoise(unittest.TestCase):
    """Test noise layering for VIP samples."""

    def test_output_same_length_or_shorter(self):
        audio = np.random.randn(44100).astype(np.float64)
        result = vip_layer_noise(audio, idx=0)
        self.assertLessEqual(len(result), len(audio))

    def test_output_clamped(self):
        audio = np.ones(44100, dtype=np.float64) * 2.0  # Exceeds range
        result = vip_layer_noise(audio, idx=0)
        self.assertTrue(np.all(result >= -1.0))
        self.assertTrue(np.all(result <= 1.0))


class TestVIPDelta(unittest.TestCase):
    """Test VIPDelta dataclass."""

    def test_defaults(self):
        d = VIPDelta(original_name="test", vip_name="test_VIP")
        self.assertAlmostEqual(d.kept_percent, 38.2)
        self.assertAlmostEqual(d.changed_percent, 61.8)
        self.assertEqual(len(d.mutations), 0)


class TestBuildVIPPack(unittest.TestCase):
    """Test VIP pack building from existing banks."""

    def test_bass_bank_produces_output(self):
        with tempfile.TemporaryDirectory() as td:
            paths, deltas = build_vip_pack("bass", td)
            self.assertIsInstance(paths, list)
            self.assertGreater(len(paths), 0)
            self.assertGreater(len(deltas), 0)

    def test_unknown_bank_returns_empty(self):
        paths, deltas = build_vip_pack("nonexistent_bank")
        self.assertEqual(len(paths), 0)
        self.assertEqual(len(deltas), 0)

    def test_creates_manifest_and_delta(self):
        with tempfile.TemporaryDirectory() as td:
            paths, deltas = build_vip_pack("bass", td)
            vip_dir = Path(td) / "vip_packs"
            self.assertTrue(vip_dir.exists())
            # Check at least one manifest
            manifests = list(vip_dir.rglob("manifest.json"))
            self.assertGreater(len(manifests), 0)
            # Check at least one delta
            delta_files = list(vip_dir.rglob("vip_delta.json"))
            self.assertGreater(len(delta_files), 0)

    def test_manifest_has_golden_rule(self):
        with tempfile.TemporaryDirectory() as td:
            build_vip_pack("bass", td)
            manifests = list(Path(td).rglob("manifest.json"))
            data = json.loads(manifests[0].read_text())
            self.assertIn("golden_vip_rule", data)
            self.assertIn("61.8", data["golden_vip_rule"])


class TestExportAllVIPPacks(unittest.TestCase):
    """Test full VIP export pipeline."""

    def test_export_all(self):
        with tempfile.TemporaryDirectory() as td:
            paths = export_all_vip_packs(td)
            self.assertIsInstance(paths, list)
            self.assertGreater(len(paths), 0)


if __name__ == "__main__":
    unittest.main()
