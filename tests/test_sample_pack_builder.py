"""Tests for engine.sample_pack_builder — 20 tests."""

import json

from engine.sample_pack_builder import (
    ALL_PACK_BANKS,
    PackPreset,
    build_sample_pack,
    export_all_packs,
    write_pack_manifest,
)


class TestPackPreset:
    def test_defaults(self):
        p = PackPreset("test", "drums")
        assert p.num_samples == 8
        assert p.normalize is True

    def test_custom(self):
        p = PackPreset("test", "bass", num_samples=4, duration_s=2.0)
        assert p.num_samples == 4


class TestBuildSamplePack:
    def test_drum_pack(self, tmp_path):
        p = PackPreset("test_kicks", "drums", num_samples=4)
        paths = build_sample_pack(p, str(tmp_path))
        assert len(paths) == 4
        for path in paths:
            assert path.endswith(".wav")

    def test_bass_pack(self, tmp_path):
        p = PackPreset("test_bass", "bass", num_samples=3)
        paths = build_sample_pack(p, str(tmp_path))
        assert len(paths) == 3

    def test_synth_pack(self, tmp_path):
        p = PackPreset("test_synths", "synths", num_samples=4)
        paths = build_sample_pack(p, str(tmp_path))
        assert len(paths) == 4

    def test_fx_pack(self, tmp_path):
        p = PackPreset("test_fx", "fx", num_samples=3)
        paths = build_sample_pack(p, str(tmp_path))
        assert len(paths) == 3

    def test_stems_pack(self, tmp_path):
        p = PackPreset("test_stems", "stems", num_samples=2)
        paths = build_sample_pack(p, str(tmp_path))
        assert len(paths) == 2

    def test_manifest_created(self, tmp_path):
        p = PackPreset("test_pack", "drums", num_samples=2)
        build_sample_pack(p, str(tmp_path))
        manifest_path = tmp_path / "sample_packs" / "drums" / "test_pack" / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["num_samples"] == 2

    def test_readme_created(self, tmp_path):
        p = PackPreset("test_pack", "drums", num_samples=2, include_readme=True)
        build_sample_pack(p, str(tmp_path))
        readme = tmp_path / "sample_packs" / "drums" / "test_pack" / "README.md"
        assert readme.exists()

    def test_normalized_output(self, tmp_path):
        import struct
        import wave as wave_mod
        p = PackPreset("test_norm", "bass", num_samples=1, normalize=True)
        paths = build_sample_pack(p, str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            frames = wf.readframes(wf.getnframes())
            samples = struct.unpack(f"<{wf.getnframes()}h", frames)
            peak = max(abs(s) for s in samples)
            assert peak > 0
            assert peak <= 32767


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_PACK_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_PACK_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4

    def test_drums_bank(self):
        bank = ALL_PACK_BANKS["drums"]()
        assert bank.name == "drums"

    def test_bass_bank(self):
        bank = ALL_PACK_BANKS["bass"]()
        assert bank.name == "bass"

    def test_synths_bank(self):
        bank = ALL_PACK_BANKS["synths"]()
        assert bank.name == "synths"

    def test_fx_bank(self):
        bank = ALL_PACK_BANKS["fx"]()
        assert bank.name == "fx"


class TestExport:
    def test_export_all(self, tmp_path):
        paths = export_all_packs(str(tmp_path))
        assert len(paths) > 0
        for p in paths:
            assert p.endswith(".wav")


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_pack_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
