"""Tests for engine.ab_tester — A/B Tester (Phase 4)."""

import json
from pathlib import Path

import numpy as np
import pytest

from engine.ab_tester import (
    ALL_AB_BANKS,
    ABBank,
    ABPreset,
    ABResult,
    compare_composite,
    compare_loudness,
    compare_phi_ratio,
    compare_spectral,
    compare_temporal,
    export_ab_results,
    run_ab_test,
    write_ab_manifest,
)

SR = 44100


def _sine(freq=440.0, dur=0.5):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2.0 * np.pi * freq * t)


# ── dataclass tests ──────────────────────────────────────────────────────

def test_ab_result_defaults():
    r = ABResult(winner="A")
    assert r.winner == "A"
    assert r.score_a == 0.0
    assert r.detail == {}


def test_ab_result_custom():
    r = ABResult(winner="B", score_a=0.4, score_b=0.6, metric="test",
                 detail={"k": "v"})
    assert r.winner == "B"
    assert r.metric == "test"


def test_ab_preset_defaults():
    p = ABPreset(name="t", comparison_type="spectral")
    assert p.fft_size == 4096
    assert p.duration == 0.5
    assert p.freq_a == 432.0
    assert p.freq_b == 440.0


def test_ab_bank_dataclass():
    b = ABBank(name="test_bank", presets=[
        ABPreset(name="a", comparison_type="spectral"),
    ])
    assert len(b.presets) == 1


# ── comparison function tests ───────────────────────────────────────────

def test_compare_spectral_returns_result():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="spectral")
    r = compare_spectral(sig_a, sig_b, p)
    assert isinstance(r, ABResult)
    assert r.winner in ("A", "B")


def test_compare_temporal_returns_result():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="temporal")
    r = compare_temporal(sig_a, sig_b, p)
    assert isinstance(r, ABResult)
    assert 0.0 <= r.score_a <= 1.0
    assert 0.0 <= r.score_b <= 1.0


def test_compare_phi_ratio_returns_result():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="phi_ratio")
    r = compare_phi_ratio(sig_a, sig_b, p)
    assert isinstance(r, ABResult)


def test_compare_loudness_returns_result():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="loudness")
    r = compare_loudness(sig_a, sig_b, p)
    assert isinstance(r, ABResult)
    assert r.metric == "rms_loudness"


def test_compare_loudness_winner_is_louder():
    sig_a = _sine(432.0, 0.5) * 0.5  # quieter
    sig_b = _sine(440.0, 0.5)         # louder
    p = ABPreset(name="t", comparison_type="loudness")
    r = compare_loudness(sig_a, sig_b, p)
    assert r.winner == "B"


def test_compare_composite_returns_result():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="composite")
    r = compare_composite(sig_a, sig_b, p)
    assert isinstance(r, ABResult)
    assert r.metric == "composite"
    assert isinstance(r.detail, dict)


def test_compare_composite_has_detail_keys():
    sig_a = _sine(432.0, 0.5)
    sig_b = _sine(440.0, 0.5)
    p = ABPreset(name="t", comparison_type="composite")
    r = compare_composite(sig_a, sig_b, p)
    assert "spectral_peaks" in r.detail or len(r.detail) >= 1


# ── router ───────────────────────────────────────────────────────────────

def test_run_ab_test_routes_all_types():
    for ctype in ("spectral", "temporal", "phi_ratio", "loudness", "composite"):
        p = ABPreset(name="t", comparison_type=ctype)
        r = run_ab_test(p)
        assert isinstance(r, ABResult)
        assert r.winner in ("A", "B")


def test_run_ab_test_unknown_comparison():
    p = ABPreset(name="t", comparison_type="nonexistent")
    with pytest.raises(ValueError):
        run_ab_test(p)


def test_run_ab_test_winner_is_a_or_b():
    p = ABPreset(name="t", comparison_type="spectral",
                 freq_a=432.0, freq_b=440.0)
    r = run_ab_test(p)
    assert r.winner in ("A", "B")


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_AB_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_AB_BANKS.values())
    assert total == 20


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_AB_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_ab_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "analysis" / "ab_tester_manifest.json"
    assert json_path.exists()


def test_export_ab_results_creates_files(tmp_path):
    paths = export_ab_results(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) == 20
    for p in paths:
        assert Path(p).exists()
        with open(p) as f:
            data = json.load(f)
        assert "winner" in data
        assert data["winner"] in ("A", "B")


def test_compare_spectral_identical_signals():
    sig = _sine(432.0, 0.5)
    p = ABPreset(name="t", comparison_type="spectral")
    r = compare_spectral(sig, sig, p)
    assert r.winner == "A"  # tie goes to A
    assert r.score_a == r.score_b
