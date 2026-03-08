"""Tests for engine.phi_analyzer — Phi Analyzer (Phase 4)."""

import wave
from pathlib import Path

import numpy as np
import pytest

from engine.phi_analyzer import (
    ALL_PHI_ANALYZER_BANKS,
    PhiAnalyzerBank,
    PhiAnalyzerPreset,
    PhiScore,
    analyze_phi_coherence,
    analyze_wav_phi,
    export_phi_scores,
    measure_harmonic_phi,
    measure_phase_coherence,
    measure_spectral_decay,
    measure_temporal_phi,
    write_phi_analyzer_manifest,
)

SR = 44100


def _sine(freq=440.0, dur=0.5):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2.0 * np.pi * freq * t)


def _make_wav(path, freq=440.0, dur=0.5):
    t = np.arange(int(dur * SR)) / SR
    samples = np.sin(2.0 * np.pi * freq * t)
    data = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())


# ── dataclass tests ──────────────────────────────────────────────────────

def test_phi_score_defaults():
    s = PhiScore()
    assert s.harmonic_phi == 0.0
    assert s.composite == 0.0


def test_phi_score_as_dict():
    s = PhiScore(harmonic_phi=0.12345, temporal_phi=0.6789,
                 spectral_decay=0.333, phase_coherence=0.999,
                 composite=0.555)
    d = s.as_dict()
    assert isinstance(d, dict)
    assert d["harmonic_phi"] == 0.1235  # rounded to 4 dp
    assert "composite" in d


def test_preset_defaults():
    p = PhiAnalyzerPreset(name="t")
    assert p.fft_size == 4096
    assert p.hop_size == 512
    assert p.phi_tolerance == 0.02


def test_preset_custom():
    p = PhiAnalyzerPreset(name="custom", fft_size=8192, min_freq=50.0)
    assert p.fft_size == 8192
    assert p.min_freq == 50.0


def test_bank_dataclass():
    b = PhiAnalyzerBank(name="test_bank", presets=[
        PhiAnalyzerPreset(name="a"),
        PhiAnalyzerPreset(name="b"),
    ])
    assert len(b.presets) == 2
    assert b.name == "test_bank"


# ── measurement function tests ──────────────────────────────────────────

def test_measure_harmonic_phi_returns_float():
    sig = _sine(440.0, 0.5)
    p = PhiAnalyzerPreset(name="t")
    result = measure_harmonic_phi(sig, p)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_measure_harmonic_phi_short_signal():
    sig = _sine(440.0, 0.01)
    p = PhiAnalyzerPreset(name="t")
    result = measure_harmonic_phi(sig, p)
    assert isinstance(result, float)


def test_measure_temporal_phi_returns_float():
    sig = _sine(440.0, 0.5)
    p = PhiAnalyzerPreset(name="t")
    result = measure_temporal_phi(sig, p)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_measure_spectral_decay_returns_float():
    sig = _sine(440.0, 0.5)
    p = PhiAnalyzerPreset(name="t")
    result = measure_spectral_decay(sig, p)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_measure_phase_coherence_returns_float():
    sig = _sine(440.0, 0.5)
    p = PhiAnalyzerPreset(name="t")
    result = measure_phase_coherence(sig, p)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


# ── composite analysis ──────────────────────────────────────────────────

def test_analyze_phi_coherence_returns_phi_score():
    sig = _sine(432.0, 0.5)
    score = analyze_phi_coherence(sig)
    assert isinstance(score, PhiScore)
    assert 0.0 <= score.composite <= 1.0


def test_analyze_phi_coherence_custom_preset():
    sig = _sine(432.0, 0.5)
    p = PhiAnalyzerPreset(name="custom", fft_size=8192)
    score = analyze_phi_coherence(sig, p)
    assert isinstance(score, PhiScore)


def test_analyze_phi_coherence_all_fields_populated():
    sig = _sine(432.0, 0.5)
    score = analyze_phi_coherence(sig)
    d = score.as_dict()
    for key in ("harmonic_phi", "temporal_phi", "spectral_decay",
                "phase_coherence", "composite"):
        assert key in d


# ── wav file analysis ────────────────────────────────────────────────────

def test_analyze_wav_phi_returns_score(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav, 432.0, 0.5)
    score = analyze_wav_phi(str(wav))
    assert isinstance(score, PhiScore)
    assert 0.0 <= score.composite <= 1.0


def test_analyze_wav_phi_missing_file():
    with pytest.raises(FileNotFoundError):
        analyze_wav_phi("/nonexistent/file.wav")


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_PHI_ANALYZER_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_PHI_ANALYZER_BANKS.values())
    assert total == 20


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_PHI_ANALYZER_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_phi_analyzer_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "analysis" / "phi_analyzer_manifest.json"
    assert json_path.exists()


def test_export_phi_scores_runs(tmp_path):
    # Create a wavetables dir with a wav so export has something to score
    wt = tmp_path / "wavetables"
    wt.mkdir()
    _make_wav(wt / "tone.wav", 432.0, 0.3)
    paths = export_phi_scores(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) >= 1
    assert all(Path(p).exists() for p in paths)
