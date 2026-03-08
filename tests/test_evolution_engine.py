"""Tests for engine.evolution_engine — Evolution Engine (Phase 4)."""

import json
from pathlib import Path

import pytest

from engine.evolution_engine import (
    ALL_EVOLUTION_BANKS,
    EvolutionBank,
    EvolutionEntry,
    EvolutionLog,
    EvolutionPreset,
    export_evolution_logs,
    run_evolution,
    track_diversity,
    track_param_drift,
    track_phi_convergence,
    track_score_climb,
    track_stability,
    write_evolution_manifest,
)

# ── dataclass tests ──────────────────────────────────────────────────────

def test_entry_defaults():
    e = EvolutionEntry(generation=0)
    assert e.generation == 0
    assert e.score == 0.0
    assert e.params == {}


def test_entry_custom():
    e = EvolutionEntry(generation=5, params={"freq": 432}, score=0.8, notes="good")
    assert e.generation == 5
    assert e.score == 0.8
    assert e.notes == "good"


def test_log_best_entry_empty():
    log = EvolutionLog(name="test")
    assert log.best_entry() is None


def test_log_best_entry():
    log = EvolutionLog(name="test", entries=[
        EvolutionEntry(0, score=0.3),
        EvolutionEntry(1, score=0.9),
        EvolutionEntry(2, score=0.5),
    ])
    assert log.best_entry().score == 0.9


def test_log_trend():
    log = EvolutionLog(name="test", entries=[
        EvolutionEntry(0, score=0.1),
        EvolutionEntry(1, score=0.4),
        EvolutionEntry(2, score=0.7),
    ])
    assert log.trend() == [0.1, 0.4, 0.7]


def test_preset_defaults():
    p = EvolutionPreset(name="t", tracker_type="param_drift")
    assert p.generations == 10
    assert p.mutation_rate == 0.1
    assert p.population_size == 8


# ── tracker function tests ──────────────────────────────────────────────

def test_track_param_drift_returns_log():
    p = EvolutionPreset(name="t", tracker_type="param_drift", generations=5)
    log = track_param_drift(p)
    assert isinstance(log, EvolutionLog)
    assert len(log.entries) == 5


def test_track_phi_convergence_returns_log():
    p = EvolutionPreset(name="t", tracker_type="phi_convergence", generations=5)
    log = track_phi_convergence(p)
    assert isinstance(log, EvolutionLog)
    assert len(log.entries) == 5


def test_track_score_climb_returns_log():
    p = EvolutionPreset(name="t", tracker_type="score_climb", generations=5)
    log = track_score_climb(p)
    assert isinstance(log, EvolutionLog)
    assert len(log.entries) == 5


def test_track_diversity_returns_log():
    p = EvolutionPreset(name="t", tracker_type="diversity", generations=4)
    log = track_diversity(p)
    assert isinstance(log, EvolutionLog)
    assert len(log.entries) == 4


def test_track_stability_returns_log():
    p = EvolutionPreset(name="t", tracker_type="stability", generations=6)
    log = track_stability(p)
    assert isinstance(log, EvolutionLog)
    assert len(log.entries) == 6


def test_tracker_entries_have_scores():
    p = EvolutionPreset(name="t", tracker_type="param_drift", generations=3)
    log = track_param_drift(p)
    for entry in log.entries:
        assert isinstance(entry.score, float)


# ── router ───────────────────────────────────────────────────────────────

def test_run_evolution_routes_correctly():
    for tracker_type in ("param_drift", "phi_convergence", "score_climb",
                         "diversity", "stability"):
        p = EvolutionPreset(name="t", tracker_type=tracker_type, generations=3)
        log = run_evolution(p)
        assert isinstance(log, EvolutionLog)
        assert len(log.entries) == 3


def test_run_evolution_unknown_tracker():
    p = EvolutionPreset(name="t", tracker_type="unknown")
    with pytest.raises(ValueError):
        run_evolution(p)


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_EVOLUTION_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_EVOLUTION_BANKS.values())
    assert total == 20


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_EVOLUTION_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_evolution_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "analysis" / "evolution_manifest.json"
    assert json_path.exists()


def test_export_evolution_logs_creates_files(tmp_path):
    paths = export_evolution_logs(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) == 20  # 5 banks × 4 presets
    for p in paths:
        assert Path(p).exists()
        with open(p) as f:
            data = json.load(f)
        assert "entries" in data
        assert "best_score" in data


def test_bank_dataclass():
    b = EvolutionBank(name="test", presets=[
        EvolutionPreset(name="a", tracker_type="param_drift"),
    ])
    assert len(b.presets) == 1
    assert b.name == "test"
