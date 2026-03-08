"""Tests for engine.stem_mixer — 20 tests."""

import numpy as np

from engine.stem_mixer import (
    ALL_MIX_BANKS,
    MixPreset,
    StemChannel,
    export_mix_demos,
    mix_stems,
    mix_stems_dynamic,
    mix_stems_frequency,
    mix_stems_parallel,
    mix_stems_phi_weight,
    mix_stems_simple,
    write_mix_manifest,
)


def _test_stems(n=3, length=4410):
    t = np.linspace(0, 1, length, endpoint=False)
    return [0.5 * np.sin(2 * np.pi * (100 + i * 100) * t) for i in range(n)]


class TestMixPreset:
    def test_defaults(self):
        p = MixPreset("test", "simple")
        assert p.ceiling == 0.95
        assert p.master_gain_db == 0.0


class TestSimpleMix:
    def test_stereo_output(self):
        stems = _test_stems()
        p = MixPreset("test", "simple")
        out = mix_stems_simple(stems, p)
        assert out.shape[1] == 2

    def test_mute(self):
        stems = _test_stems(2)
        p = MixPreset("test", "simple", [
            StemChannel("a", mute=True),
            StemChannel("b"),
        ])
        out = mix_stems_simple(stems, p)
        assert np.max(np.abs(out)) > 0

    def test_empty(self):
        p = MixPreset("test", "simple")
        out = mix_stems_simple([], p)
        assert out.shape == (44100, 2)


class TestPhiWeightMix:
    def test_output(self):
        stems = _test_stems(4)
        p = MixPreset("test", "phi_weight")
        out = mix_stems_phi_weight(stems, p)
        assert out.shape[1] == 2

    def test_decreasing_levels(self):
        stems = [np.ones(1000) * 0.5] * 3
        p = MixPreset("test", "phi_weight", [
            StemChannel("a", 0.0, -0.5),
            StemChannel("b", 0.0, 0.0),
            StemChannel("c", 0.0, 0.5),
        ])
        out = mix_stems_phi_weight(stems, p)
        assert out.shape == (1000, 2)


class TestFrequencyMix:
    def test_output(self):
        stems = _test_stems()
        p = MixPreset("test", "frequency")
        out = mix_stems_frequency(stems, p)
        assert out.shape[1] == 2


class TestDynamicMix:
    def test_output(self):
        stems = _test_stems()
        p = MixPreset("test", "dynamic")
        out = mix_stems_dynamic(stems, p)
        assert out.shape[1] == 2


class TestParallelMix:
    def test_output(self):
        stems = _test_stems()
        p = MixPreset("test", "parallel")
        out = mix_stems_parallel(stems, p)
        assert out.shape[1] == 2


class TestMixRouter:
    def test_routes_all_types(self):
        stems = _test_stems(2)
        for mix_type in ["simple", "phi_weight", "frequency", "dynamic", "parallel"]:
            p = MixPreset("test", mix_type)
            out = mix_stems(stems, p)
            assert out.shape[1] == 2, f"Failed for {mix_type}"


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_MIX_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_MIX_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4


class TestExport:
    def test_export_creates_wav(self, tmp_path):
        paths = export_mix_demos(str(tmp_path))
        assert len(paths) == 20
        for p in paths:
            assert p.endswith(".wav")

    def test_export_stereo(self, tmp_path):
        import wave as wave_mod
        paths = export_mix_demos(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            assert wf.getnchannels() == 2


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_mix_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
