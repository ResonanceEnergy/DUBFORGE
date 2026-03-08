"""Tests for engine.spectral_resynthesis — 20 tests."""

import numpy as np

from engine.spectral_resynthesis import (
    ALL_RESYNTH_BANKS,
    ResynthPreset,
    analyze_spectrum,
    export_resynth_wavetables,
    resynth_additive,
    resynth_hybrid,
    resynth_phi_filter,
    resynth_spectral_env,
    resynth_subtractive,
    resynthesize,
    write_resynth_manifest,
)

SR = 44100
PHI = 1.6180339887


def _test_signal(freq=200.0, dur=0.5):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * 0.8


class TestResynthPreset:
    def test_defaults(self):
        p = ResynthPreset("test", "additive")
        assert p.num_harmonics == 32
        assert p.num_output_frames == 16


class TestAnalyzeSpectrum:
    def test_finds_peaks(self):
        sig = _test_signal()
        p = ResynthPreset("test", "additive")
        result = analyze_spectrum(sig, p)
        assert len(result["peaks"]) > 0
        assert result["fundamental"] > 0

    def test_peak_frequencies(self):
        sig = _test_signal(200.0)
        p = ResynthPreset("test", "additive")
        result = analyze_spectrum(sig, p)
        # Should detect ~200 Hz fundamental
        assert 150 < result["fundamental"] < 250


class TestAdditive:
    def test_output_frames(self):
        sig = _test_signal()
        p = ResynthPreset("test", "additive", num_output_frames=8)
        frames = resynth_additive(sig, p)
        assert len(frames) == 8

    def test_normalized(self):
        sig = _test_signal()
        p = ResynthPreset("test", "additive", num_output_frames=4)
        frames = resynth_additive(sig, p)
        for f in frames:
            assert np.max(np.abs(f)) <= 1.0 + 1e-6


class TestSubtractive:
    def test_output_frames(self):
        sig = _test_signal()
        p = ResynthPreset("test", "subtractive", num_output_frames=8)
        frames = resynth_subtractive(sig, p)
        assert len(frames) == 8


class TestPhiFilter:
    def test_output_frames(self):
        sig = _test_signal()
        p = ResynthPreset("test", "phi_filter", num_output_frames=8)
        frames = resynth_phi_filter(sig, p)
        assert len(frames) == 8


class TestSpectralEnv:
    def test_output_frames(self):
        sig = _test_signal()
        p = ResynthPreset("test", "spectral_env", num_output_frames=8)
        frames = resynth_spectral_env(sig, p)
        assert len(frames) == 8


class TestHybrid:
    def test_output_frames(self):
        sig = _test_signal()
        p = ResynthPreset("test", "hybrid", num_output_frames=8)
        frames = resynth_hybrid(sig, p)
        assert len(frames) == 8


class TestRouter:
    def test_routes_all_types(self):
        sig = _test_signal()
        for rtype in ["additive", "subtractive", "phi_filter", "spectral_env", "hybrid"]:
            p = ResynthPreset("test", rtype, num_output_frames=4)
            frames = resynthesize(sig, p)
            assert len(frames) == 4, f"Failed for {rtype}"


class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_RESYNTH_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, fn in ALL_RESYNTH_BANKS.items():
            bank = fn()
            assert len(bank.presets) == 4


class TestExport:
    def test_export_creates_wav(self, tmp_path):
        paths = export_resynth_wavetables(str(tmp_path))
        assert len(paths) == 20
        for p in paths:
            assert p.endswith(".wav")

    def test_export_wav_valid(self, tmp_path):
        import wave as wave_mod
        paths = export_resynth_wavetables(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2


class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_resynth_manifest(str(tmp_path))
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
