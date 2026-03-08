"""Tests for engine.render_pipeline — 20 tests."""

import numpy as np

from engine.render_pipeline import (
    ALL_PIPELINE_BANKS,
    PipelinePreset,
    PipelineStage,
    _apply_distortion_stage,
    _apply_master_stage,
    _apply_sidechain_stage,
    _apply_stereo_stage,
    _generate_tone,
    export_pipeline_stems,
    run_pipeline,
    write_pipeline_manifest,
)


class TestPipelinePreset:
    def test_defaults(self):
        p = PipelinePreset("test", "bass")
        assert p.duration_s == 2.0
        assert p.base_freq == 55.0

    def test_custom(self):
        p = PipelinePreset("test", "lead", base_freq=440.0, gain_db=-3.0)
        assert p.base_freq == 440.0
        assert p.gain_db == -3.0


class TestGenerateTone:
    def test_bass_tone(self):
        p = PipelinePreset("test", "bass", duration_s=0.1)
        audio = _generate_tone(p)
        assert len(audio) > 0
        assert np.max(np.abs(audio)) <= 1.0

    def test_lead_tone(self):
        p = PipelinePreset("test", "lead", duration_s=0.1)
        audio = _generate_tone(p)
        assert len(audio) > 0

    def test_pad_tone(self):
        p = PipelinePreset("test", "pad", duration_s=0.1)
        audio = _generate_tone(p)
        assert len(audio) > 0

    def test_perc_tone(self):
        p = PipelinePreset("test", "perc", duration_s=0.1)
        audio = _generate_tone(p)
        assert len(audio) > 0

    def test_full_tone(self):
        p = PipelinePreset("test", "full", duration_s=0.1)
        audio = _generate_tone(p)
        assert len(audio) > 0


class TestStageProcessors:
    def test_distortion(self):
        sig = np.sin(np.linspace(0, 2 * np.pi, 1000))
        out = _apply_distortion_stage(sig, {"drive": 0.5})
        assert len(out) == len(sig)
        assert np.max(np.abs(out)) <= 1.0

    def test_sidechain(self):
        sig = np.ones(44100) * 0.5
        out = _apply_sidechain_stage(sig, {"depth": 0.7})
        assert len(out) == len(sig)
        assert np.min(out) < 0.5

    def test_stereo(self):
        sig = np.sin(np.linspace(0, 2 * np.pi, 1000))
        out = _apply_stereo_stage(sig, {"delay_ms": 5.0})
        assert out.shape == (1000, 2)

    def test_master(self):
        sig = np.ones(1000) * 0.8
        out = _apply_master_stage(sig, {"ceiling": 0.9})
        assert np.max(np.abs(out)) <= 1.0


class TestRunPipeline:
    def test_full_pipeline(self):
        stages = [
            PipelineStage("dist", "distort", {"drive": 0.3}),
            PipelineStage("sc", "sidechain", {"depth": 0.5}),
            PipelineStage("st", "stereo", {"delay_ms": 8.0}),
            PipelineStage("master", "master", {"ceiling": 0.9}),
        ]
        p = PipelinePreset("test", "bass", stages, duration_s=0.5)
        audio = run_pipeline(p)
        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_disabled_stage(self):
        stages = [
            PipelineStage("dist", "distort", {"drive": 0.5}, enabled=False),
        ]
        p = PipelinePreset("test", "bass", stages, duration_s=0.1)
        audio = run_pipeline(p)
        assert audio.ndim == 1


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_PIPELINE_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_PIPELINE_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4, f"{name} bank has {len(bank.presets)} presets"


class TestExport:
    def test_export_creates_wav(self, tmp_path):
        paths = export_pipeline_stems(str(tmp_path))
        assert len(paths) == 20
        for p in paths:
            assert p.endswith(".wav")

    def test_export_wav_valid(self, tmp_path):
        import wave as wave_mod
        paths = export_pipeline_stems(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100
            assert wf.getnframes() > 0


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_pipeline_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
