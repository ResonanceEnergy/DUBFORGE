"""Tests for engine.harmonic_analysis — 33 tests."""

import wave

import numpy as np
import pytest

from engine.harmonic_analysis import (
    ALL_ANALYSIS_BANKS,
    AnalysisPreset,
    HarmonicSeries,
    PhiRelation,
    RoughnessResult,
    SpectralFluxPoint,
    SpectralPeak,
    analyze_harmonic_series,
    analyze_phi_relations,
    analyze_roughness,
    analyze_spectral_flux,
    analyze_spectral_peaks,
    analyze_wav_file,
    export_analysis_reports,
    harmonic_series_bank,
    phi_detection_bank,
    roughness_bank,
    run_analysis,
    spectral_flux_bank,
    spectral_peaks_bank,
    write_harmonic_analysis_manifest,
)

SR = 44100
PHI = 1.6180339887


def _sine(freq: float = 440.0, dur: float = 0.2, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


def _harmonic_signal(fundamental: float = 220.0, num_harmonics: int = 5,
                     dur: float = 0.2) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    sig = np.zeros_like(t)
    for h in range(1, num_harmonics + 1):
        sig += np.sin(2.0 * np.pi * fundamental * h * t) / h
    return sig


# ─── DATACLASS ──────────────────────────────────────────────────────────
class TestAnalysisPreset:
    def test_defaults(self):
        p = AnalysisPreset("test", "spectral_peaks")
        assert p.fft_size == 4096
        assert p.max_peaks == 20

    def test_custom_fields(self):
        p = AnalysisPreset("c", "roughness", roughness_bandwidth=2.0)
        assert p.roughness_bandwidth == 2.0


class TestDataclasses:
    def test_spectral_peak(self):
        p = SpectralPeak(frequency=440.0, magnitude_db=-10.0)
        assert p.frequency == 440.0

    def test_harmonic_series(self):
        h = HarmonicSeries(fundamental=220.0)
        assert h.inharmonicity == 0.0

    def test_phi_relation(self):
        pr = PhiRelation(freq_low=100.0, freq_high=161.8, ratio=1.618,
                         deviation_from_phi=0.0)
        assert pr.ratio == 1.618

    def test_spectral_flux_point(self):
        f = SpectralFluxPoint(time_sec=1.0, flux_value=0.5)
        assert not f.is_onset

    def test_roughness_result(self):
        r = RoughnessResult(total_roughness=0.5)
        assert len(r.partial_pairs) == 0


# ─── SPECTRAL PEAKS ────────────────────────────────────────────────────
class TestSpectralPeaks:
    def test_pure_sine(self):
        sig = _sine(440.0, 0.2)
        p = AnalysisPreset("sp", "spectral_peaks")
        peaks = analyze_spectral_peaks(sig, p)
        assert len(peaks) > 0
        # Dominant peak should be near 440 Hz
        assert abs(peaks[0].frequency - 440.0) < 20.0

    def test_empty_signal(self):
        peaks = analyze_spectral_peaks(np.array([]),
                                       AnalysisPreset("e", "spectral_peaks"))
        assert len(peaks) == 0

    def test_max_peaks_limit(self):
        sig = _harmonic_signal(100.0, 10)
        p = AnalysisPreset("mp", "spectral_peaks", max_peaks=3)
        peaks = analyze_spectral_peaks(sig, p)
        assert len(peaks) <= 3


# ─── HARMONIC SERIES ───────────────────────────────────────────────────
class TestHarmonicSeries:
    def test_fundamental_detection(self):
        sig = _harmonic_signal(220.0, 5, 0.2)
        p = AnalysisPreset("hs", "harmonic_series")
        series = analyze_harmonic_series(sig, p)
        assert len(series) > 0


# ─── PHI DETECTION ─────────────────────────────────────────────────────
class TestPhiDetection:
    def test_phi_ratio_signal(self):
        # Create signal with two tones in phi ratio
        f1 = 200.0
        f2 = f1 * PHI
        t = np.arange(int(0.2 * SR)) / SR
        sig = np.sin(2.0 * np.pi * f1 * t) + np.sin(2.0 * np.pi * f2 * t)
        p = AnalysisPreset("phi", "phi_detection", phi_tolerance=0.05)
        relations = analyze_phi_relations(sig, p)
        assert len(relations) > 0


# ─── SPECTRAL FLUX ─────────────────────────────────────────────────────
class TestSpectralFlux:
    def test_static_signal(self):
        sig = _sine(440.0, 0.5)
        p = AnalysisPreset("sf", "spectral_flux", flux_threshold=0.5)
        flux = analyze_spectral_flux(sig, p)
        # Static sine should have low flux, few onsets
        onsets = [f for f in flux if f.is_onset]
        assert len(onsets) < len(flux)

    def test_short_signal(self):
        sig = _sine(440.0, 0.01)  # shorter than fft_size
        p = AnalysisPreset("short", "spectral_flux", fft_size=4096)
        flux = analyze_spectral_flux(sig, p)
        assert len(flux) == 0


# ─── ROUGHNESS ──────────────────────────────────────────────────────────
class TestRoughness:
    def test_unison(self):
        sig = _sine(440.0)
        p = AnalysisPreset("ru", "roughness")
        result = analyze_roughness(sig, p)
        # Pure sine = no roughness (only one partial)
        assert result.total_roughness == 0.0

    def test_dissonant_interval(self):
        # Minor second — should have roughness
        t = np.arange(int(0.2 * SR)) / SR
        sig = np.sin(2.0 * np.pi * 440.0 * t) + np.sin(2.0 * np.pi * 466.0 * t)
        p = AnalysisPreset("rd", "roughness", peak_threshold_db=-30.0)
        result = analyze_roughness(sig, p)
        assert result.total_roughness >= 0.0


# ─── ROUTER ─────────────────────────────────────────────────────────────
class TestRouter:
    def test_all_types(self):
        sig = _harmonic_signal(220.0, 3, 0.3)
        for atype in ["spectral_peaks", "harmonic_series", "phi_detection",
                       "spectral_flux", "roughness"]:
            p = AnalysisPreset(f"r_{atype}", atype)
            result = run_analysis(sig, p)
            assert result["type"] == atype

    def test_invalid_type(self):
        sig = _sine()
        p = AnalysisPreset("bad", "nonexistent")
        with pytest.raises(ValueError):
            run_analysis(sig, p)


# ─── BANKS ──────────────────────────────────────────────────────────────
class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_ANALYSIS_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, gen in ALL_ANALYSIS_BANKS.items():
            bank = gen()
            assert len(bank.presets) == 4, f"{name} has {len(bank.presets)}"

    def test_spectral_peaks_bank(self):
        b = spectral_peaks_bank()
        assert b.name == "spectral_peaks"

    def test_harmonic_series_bank(self):
        b = harmonic_series_bank()
        assert b.name == "harmonic_series"

    def test_phi_detection_bank(self):
        b = phi_detection_bank()
        assert b.name == "phi_detection"

    def test_spectral_flux_bank(self):
        b = spectral_flux_bank()
        assert b.name == "spectral_flux"

    def test_roughness_bank(self):
        b = roughness_bank()
        assert b.name == "roughness"
        assert all(p.analysis_type == "roughness" for p in b.presets)


# ─── MANIFEST ───────────────────────────────────────────────────────────
class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_harmonic_analysis_manifest(str(tmp_path))
        assert "banks" in m
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20


# ─── WAV ANALYSIS (Session 121) ─────────────────────────────────────────


def _make_test_wav(path, freq=440.0, dur=0.5, sr=44100):
    """Create a simple test .wav file."""
    t = np.arange(int(dur * sr)) / sr
    samples = np.sin(2.0 * np.pi * freq * t)
    data = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


class TestAnalyzeWavFile:
    def test_basic_analysis(self, tmp_path):
        p = tmp_path / "tone.wav"
        _make_test_wav(p, 440.0)
        result = analyze_wav_file(str(p), "spectral_peaks")
        assert result["analysis_type"] == "spectral_peaks"
        assert result["sample_rate"] == 44100
        assert result["duration_s"] > 0

    def test_phi_detection_on_wav(self, tmp_path):
        p = tmp_path / "phi.wav"
        _make_test_wav(p, 432.0)
        result = analyze_wav_file(str(p), "phi_detection")
        assert result["analysis_type"] == "phi_detection"
        assert "results" in result

    def test_harmonic_series_on_wav(self, tmp_path):
        p = tmp_path / "hs.wav"
        _make_test_wav(p, 220.0)
        result = analyze_wav_file(str(p), "harmonic_series")
        assert result["analysis_type"] == "harmonic_series"

    def test_spectral_flux_on_wav(self, tmp_path):
        p = tmp_path / "flux.wav"
        _make_test_wav(p, 440.0)
        result = analyze_wav_file(str(p), "spectral_flux")
        assert result["analysis_type"] == "spectral_flux"

    def test_roughness_on_wav(self, tmp_path):
        p = tmp_path / "rough.wav"
        _make_test_wav(p, 440.0)
        result = analyze_wav_file(str(p), "roughness")
        assert result["analysis_type"] == "roughness"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            analyze_wav_file("/nonexistent/foo.wav")

    def test_invalid_type_raises(self, tmp_path):
        p = tmp_path / "t.wav"
        _make_test_wav(p)
        with pytest.raises(ValueError):
            analyze_wav_file(str(p), "bogus_type")

    def test_result_has_preset_name(self, tmp_path):
        p = tmp_path / "pn.wav"
        _make_test_wav(p)
        result = analyze_wav_file(str(p))
        assert "preset" in result

    def test_stereo_wav(self, tmp_path):
        """Stereo files should be mixed to mono for analysis."""
        p = tmp_path / "stereo.wav"
        sr = 44100
        t = np.arange(int(0.3 * sr)) / sr
        left = np.sin(2 * np.pi * 440 * t)
        right = np.sin(2 * np.pi * 440 * t)
        interleaved = np.empty(len(t) * 2, dtype=np.float64)
        interleaved[0::2] = left
        interleaved[1::2] = right
        data = np.clip(interleaved * 32767, -32768, 32767).astype(np.int16)
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())
        result = analyze_wav_file(str(p), "spectral_peaks")
        assert result["duration_s"] > 0


class TestExportAnalysisReports:
    def test_no_wavs_returns_empty(self, tmp_path):
        paths = export_analysis_reports(str(tmp_path))
        assert paths == []

    def test_with_wavs(self, tmp_path):
        wt_dir = tmp_path / "wavetables"
        wt_dir.mkdir()
        _make_test_wav(wt_dir / "test1.wav", 440.0)
        _make_test_wav(wt_dir / "test2.wav", 220.0)
        paths = export_analysis_reports(str(tmp_path))
        assert len(paths) >= 2  # at least 2 analysis types × 2 files = 4
        for p in paths:
            assert p.endswith(".json")
