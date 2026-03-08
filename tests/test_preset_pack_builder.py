"""Tests for engine.preset_pack_builder — 20 tests."""

import json

from engine.preset_pack_builder import (
    ALL_PRESET_PACK_BANKS,
    PresetPackEntry,
    PresetPackPreset,
    build_preset_pack,
    export_all_preset_packs,
    write_fxp,
    write_preset_pack_manifest,
)


class TestPresetPackEntry:
    def test_defaults(self):
        e = PresetPackEntry("test", "bass")
        assert e.osc_type == "saw"
        assert e.num_voices == 1
        assert e.filter_cutoff == 1.0

    def test_custom(self):
        e = PresetPackEntry("test", "lead", "square", 5, 0.2)
        assert e.osc_type == "square"
        assert e.num_voices == 5


class TestWriteFxp:
    def test_creates_file(self, tmp_path):
        e = PresetPackEntry("test_preset", "bass")
        path = tmp_path / "test.fxp"
        result = write_fxp(e, path)
        assert path.exists()
        assert result == str(path)

    def test_fxp_header(self, tmp_path):
        e = PresetPackEntry("test_preset", "bass")
        path = tmp_path / "test.fxp"
        write_fxp(e, path)
        with open(path, "rb") as f:
            magic = f.read(4)
            assert magic == b'CcnK'

    def test_fxp_contains_name(self, tmp_path):
        e = PresetPackEntry("MyPreset", "lead")
        path = tmp_path / "test.fxp"
        write_fxp(e, path)
        data = path.read_bytes()
        assert b"MyPreset" in data


class TestBuildPresetPack:
    def test_bass_pack(self, tmp_path):
        p = PresetPackPreset("test_bass", "bass")
        paths = build_preset_pack(p, str(tmp_path))
        assert len(paths) == 4
        for path in paths:
            assert path.endswith(".fxp")

    def test_lead_pack(self, tmp_path):
        p = PresetPackPreset("test_lead", "lead")
        paths = build_preset_pack(p, str(tmp_path))
        assert len(paths) == 4

    def test_pad_pack(self, tmp_path):
        p = PresetPackPreset("test_pad", "pad")
        paths = build_preset_pack(p, str(tmp_path))
        assert len(paths) == 4

    def test_manifest_created(self, tmp_path):
        p = PresetPackPreset("test_pack", "bass")
        build_preset_pack(p, str(tmp_path))
        manifest_path = tmp_path / "presets" / "bass" / "test_pack" / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["num_presets"] == 4

    def test_custom_entries(self, tmp_path):
        entries = [
            PresetPackEntry("Custom1", "bass"),
            PresetPackEntry("Custom2", "bass"),
        ]
        p = PresetPackPreset("custom_test", "bass", entries)
        paths = build_preset_pack(p, str(tmp_path))
        assert len(paths) == 2


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_PRESET_PACK_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_PRESET_PACK_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4

    def test_bass_bank(self):
        bank = ALL_PRESET_PACK_BANKS["bass"]()
        assert bank.name == "bass"

    def test_lead_bank(self):
        bank = ALL_PRESET_PACK_BANKS["lead"]()
        assert bank.name == "lead"

    def test_pad_bank(self):
        bank = ALL_PRESET_PACK_BANKS["pad"]()
        assert bank.name == "pad"


class TestExport:
    def test_export_all(self, tmp_path):
        paths = export_all_preset_packs(str(tmp_path))
        assert len(paths) > 0
        for p in paths:
            assert p.endswith(".fxp")


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_preset_pack_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
