"""Tests for engine.batch_renderer — 20 tests."""


from engine.batch_renderer import (
    ALL_BATCH_BANKS,
    BatchPreset,
    BatchResult,
    export_batch_renders,
    render_batch,
    write_batch_manifest,
)


class TestBatchPreset:
    def test_defaults(self):
        p = BatchPreset("test", "all")
        assert p.duration_s == 1.0
        assert p.normalize is True

    def test_custom(self):
        p = BatchPreset("test", "synths", duration_s=3.0, base_freq=55.0)
        assert p.duration_s == 3.0
        assert p.base_freq == 55.0


class TestRenderBatch:
    def test_renders_4_variants(self, tmp_path):
        p = BatchPreset("test", "all", duration_s=0.1)
        results = render_batch(p, str(tmp_path))
        assert len(results) == 4

    def test_result_fields(self, tmp_path):
        p = BatchPreset("test", "all", duration_s=0.1)
        results = render_batch(p, str(tmp_path))
        for r in results:
            assert isinstance(r, BatchResult)
            assert r.wav_path.endswith(".wav")
            assert r.peak_db < 0  # should be below 0 dBFS

    def test_different_modes(self, tmp_path):
        for mode in ["all", "synths", "fx", "pipeline", "quick"]:
            p = BatchPreset(f"test_{mode}", mode, duration_s=0.1)
            results = render_batch(p, str(tmp_path))
            assert len(results) == 4

    def test_normalized(self, tmp_path):
        p = BatchPreset("test", "all", duration_s=0.1, normalize=True)
        results = render_batch(p, str(tmp_path))
        assert all(r.peak_db <= 0 for r in results)


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_BATCH_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_BATCH_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4

    def test_all_render_bank(self):
        bank = ALL_BATCH_BANKS["all"]()
        assert bank.name == "all"

    def test_synths_render_bank(self):
        bank = ALL_BATCH_BANKS["synths"]()
        assert bank.name == "synths"

    def test_fx_render_bank(self):
        bank = ALL_BATCH_BANKS["fx"]()
        assert bank.name == "fx"

    def test_pipeline_render_bank(self):
        bank = ALL_BATCH_BANKS["pipeline"]()
        assert bank.name == "pipeline"

    def test_quick_render_bank(self):
        bank = ALL_BATCH_BANKS["quick"]()
        assert bank.name == "quick"


import pytest as _pytest


@_pytest.fixture(scope="class")
def exported_paths(tmp_path_factory):
    """Render all banks once (no compression) and share across TestExport."""
    out = tmp_path_factory.mktemp("export")
    return export_batch_renders(str(out), compress=False)


class TestExport:
    def test_export_creates_wavs(self, exported_paths):
        assert len(exported_paths) == 80  # 5 banks × 4 presets × 4 variants
        for p in exported_paths:
            assert p.endswith(".wav")

    def test_export_wav_valid(self, exported_paths):
        import wave as wave_mod
        with wave_mod.open(exported_paths[0], "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100

    def test_export_nonzero(self, exported_paths):
        import struct
        import wave as wave_mod
        with wave_mod.open(exported_paths[0], "r") as wf:
            frames = wf.readframes(wf.getnframes())
            samples = struct.unpack(f"<{wf.getnframes()}h", frames)
            assert any(s != 0 for s in samples)


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_batch_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
