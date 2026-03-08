"""Tests for engine.wavetable_morph — 20 tests."""

import numpy as np

from engine.wavetable_morph import (
    ALL_MORPH_BANKS,
    MorphPreset,
    export_morph_wavetables,
    morph_formant,
    morph_fractal,
    morph_granular,
    morph_phi_spline,
    morph_spectral,
    morph_wavetable,
    write_morph_manifest,
)

FRAME_SIZE = 2048


def _source_frames(n=4):
    t = np.linspace(0, 2 * np.pi, FRAME_SIZE, endpoint=False)
    return [np.sin(k * t) for k in range(1, n + 1)]


class TestMorphPreset:
    def test_defaults(self):
        p = MorphPreset("test", "phi_spline")
        assert p.num_frames == 16
        assert p.frame_size == FRAME_SIZE


class TestPhiSpline:
    def test_output_count(self):
        frames = _source_frames()
        p = MorphPreset("test", "phi_spline", 16)
        result = morph_phi_spline(frames, p)
        assert len(result) == 16

    def test_frame_size(self):
        frames = _source_frames()
        p = MorphPreset("test", "phi_spline", 8)
        result = morph_phi_spline(frames, p)
        assert all(len(f) == FRAME_SIZE for f in result)


class TestFractal:
    def test_output_count(self):
        frames = _source_frames()
        p = MorphPreset("test", "fractal", 12)
        result = morph_fractal(frames, p)
        assert len(result) == 12

    def test_normalized(self):
        frames = _source_frames()
        p = MorphPreset("test", "fractal", 8)
        result = morph_fractal(frames, p)
        for f in result:
            assert np.max(np.abs(f)) <= 1.0 + 1e-6


class TestSpectral:
    def test_output_count(self):
        frames = _source_frames()
        p = MorphPreset("test", "spectral", 16)
        result = morph_spectral(frames, p)
        assert len(result) == 16

    def test_frame_size(self):
        frames = _source_frames()
        p = MorphPreset("test", "spectral", 8)
        result = morph_spectral(frames, p)
        assert all(len(f) == FRAME_SIZE for f in result)


class TestFormant:
    def test_output_count(self):
        frames = _source_frames()
        p = MorphPreset("test", "formant", 16)
        result = morph_formant(frames, p)
        assert len(result) == 16


class TestGranular:
    def test_output_count(self):
        frames = _source_frames()
        p = MorphPreset("test", "granular", 12, grain_size=256)
        result = morph_granular(frames, p)
        assert len(result) == 12


class TestRouter:
    def test_routes_all_types(self):
        frames = _source_frames(2)
        for morph_type in ["phi_spline", "fractal", "spectral", "formant", "granular"]:
            p = MorphPreset("test", morph_type, 4)
            result = morph_wavetable(frames, p)
            assert len(result) == 4, f"Failed for {morph_type}"


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_MORPH_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_MORPH_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4, f"{name} has {len(bank.presets)} presets"


class TestExport:
    def test_export_creates_wav(self, tmp_path):
        paths = export_morph_wavetables(str(tmp_path))
        assert len(paths) == 20
        for p in paths:
            assert p.endswith(".wav")

    def test_export_wav_valid(self, tmp_path):
        import wave as wave_mod
        paths = export_morph_wavetables(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2

    def test_export_wav_nonzero(self, tmp_path):
        import struct
        import wave as wave_mod
        paths = export_morph_wavetables(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            frames = wf.readframes(min(wf.getnframes(), 1000))
            n = len(frames) // 2
            samples = struct.unpack(f"<{n}h", frames)
            assert any(s != 0 for s in samples)


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_morph_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
