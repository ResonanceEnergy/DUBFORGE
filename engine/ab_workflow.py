"""
DUBFORGE Engine — A/B Sound Design Workflow

Enhanced A/B comparison workflow that wraps the core ab_tester.py
with session management, multi-round comparison chains, and automated
winner selection using phi-coherence scoring.

Unlike ab_tester.py (which does single-pair comparisons), this module
manages full A/B SESSION workflows:
    1. Generate N candidates
    2. Run tournament-bracket comparisons
    3. Track scoring across multiple metrics
    4. Select final winner
    5. Export comparison report

Used in Phase 1 Stage 4G for sound design iteration,
and in Phase 4 for VIP variant selection.

Modes:
    bracket        — Tournament bracket: pairs off N candidates, winners advance
    round_robin    — Every candidate vs every other, highest total score wins
    elimination    — Weakest eliminated each round until one remains
    golden_split   — Split candidates at PHI boundary, compare halves
    blind_vote     — Randomized order, composite score only (no bias)

Banks: 5 modes × 4 presets = 20 presets
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.ab_tester import (
    ABResult,
    compare_spectral,
    compare_temporal,
    compare_phi_ratio,
    compare_loudness,
    compare_composite,
    ABPreset,
)
from engine.accel import fft, write_wav

_log = get_logger("dubforge.ab_workflow")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ABWorkflowPreset:
    name: str
    mode: str  # bracket | round_robin | elimination | golden_split | blind_vote
    num_candidates: int = 8
    comparison_metric: str = "composite"
    fft_size: int = 4096
    # Candidate generation
    base_freq: float = 65.0  # bass fundamental
    freq_spread: float = 1.0  # spread multiplier for candidate variation
    harmonics: int = 8
    duration: float = 1.0
    # Session
    num_rounds: int = 0  # 0 = auto (log2 for bracket, N-1 for elimination)


@dataclass
class ABWorkflowBank:
    name: str
    presets: list[ABWorkflowPreset] = field(default_factory=list)


@dataclass
class CandidateScore:
    """Score tracking for a single candidate."""
    index: int
    wins: int = 0
    losses: int = 0
    total_score: float = 0.0
    eliminated: bool = False


@dataclass
class ABWorkflowResult:
    name: str
    mode: str
    winner_index: int
    winner_audio: np.ndarray
    scores: list[CandidateScore]
    rounds: list[dict]  # round-by-round results
    num_comparisons: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# CANDIDATE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def _generate_candidates(preset: ABWorkflowPreset,
                         sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate N sound candidates with varied parameters."""
    candidates = []
    n = int(preset.duration * sr)
    t = np.linspace(0, preset.duration, n, endpoint=False)

    for i in range(preset.num_candidates):
        # Vary frequency using phi spiral
        freq = preset.base_freq * (PHI ** (i * preset.freq_spread / preset.num_candidates))
        # Vary harmonics
        harm = max(1, preset.harmonics + (i % 5) - 2)
        # Generate signal
        sig = np.zeros(n)
        for h in range(1, harm + 1):
            amp = 1.0 / (h ** PHI)
            phase_offset = (i * h * PHI) % (2 * math.pi)
            sig += amp * np.sin(2 * math.pi * freq * h * t + phase_offset)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        candidates.append(sig)

    return candidates


def _compare_pair(sig_a: np.ndarray, sig_b: np.ndarray,
                  metric: str, fft_size: int) -> ABResult:
    """Compare two signals using the specified metric."""
    dummy_preset = ABPreset(
        name="_workflow", comparison_type=metric, fft_size=fft_size)
    comparators = {
        "spectral": compare_spectral,
        "temporal": compare_temporal,
        "phi_ratio": compare_phi_ratio,
        "loudness": compare_loudness,
        "composite": compare_composite,
    }
    fn = comparators.get(metric, compare_composite)
    return fn(sig_a, sig_b, dummy_preset)


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW ENGINES
# ═══════════════════════════════════════════════════════════════════════════

def workflow_bracket(candidates: list[np.ndarray],
                     preset: ABWorkflowPreset) -> ABWorkflowResult:
    """Tournament bracket — pairs compete, winners advance."""
    n = len(candidates)
    scores = [CandidateScore(index=i) for i in range(n)]
    rounds = []
    active = list(range(n))
    total_comparisons = 0

    round_num = 0
    while len(active) > 1:
        round_results = []
        next_round = []
        for i in range(0, len(active) - 1, 2):
            a_idx, b_idx = active[i], active[i + 1]
            result = _compare_pair(
                candidates[a_idx], candidates[b_idx],
                preset.comparison_metric, preset.fft_size)
            total_comparisons += 1
            if result.winner == "A":
                scores[a_idx].wins += 1
                scores[a_idx].total_score += result.score_a
                scores[b_idx].losses += 1
                scores[b_idx].eliminated = True
                next_round.append(a_idx)
            else:
                scores[b_idx].wins += 1
                scores[b_idx].total_score += result.score_b
                scores[a_idx].losses += 1
                scores[a_idx].eliminated = True
                next_round.append(b_idx)
            round_results.append({
                "a": a_idx, "b": b_idx, "winner": result.winner,
                "score_a": result.score_a, "score_b": result.score_b
            })
        # Odd candidate gets bye
        if len(active) % 2:
            bye_idx = active[-1]
            next_round.append(bye_idx)
            round_results.append({"bye": bye_idx})
        rounds.append({"round": round_num, "matches": round_results})
        active = next_round
        round_num += 1

    winner = active[0] if active else 0
    return ABWorkflowResult(
        name=preset.name, mode="bracket", winner_index=winner,
        winner_audio=candidates[winner], scores=scores, rounds=rounds,
        num_comparisons=total_comparisons)


def workflow_round_robin(candidates: list[np.ndarray],
                         preset: ABWorkflowPreset) -> ABWorkflowResult:
    """Every candidate vs every other. Highest total score wins."""
    n = len(candidates)
    scores = [CandidateScore(index=i) for i in range(n)]
    rounds = []
    total_comparisons = 0

    for i in range(n):
        for j in range(i + 1, n):
            result = _compare_pair(
                candidates[i], candidates[j],
                preset.comparison_metric, preset.fft_size)
            total_comparisons += 1
            if result.winner == "A":
                scores[i].wins += 1
                scores[i].total_score += result.score_a
                scores[j].losses += 1
            else:
                scores[j].wins += 1
                scores[j].total_score += result.score_b
                scores[i].losses += 1
            rounds.append({
                "a": i, "b": j, "winner": result.winner,
                "score_a": result.score_a, "score_b": result.score_b
            })

    winner = max(range(n), key=lambda k: scores[k].total_score)
    return ABWorkflowResult(
        name=preset.name, mode="round_robin", winner_index=winner,
        winner_audio=candidates[winner], scores=scores,
        rounds=[{"round": 0, "matches": rounds}],
        num_comparisons=total_comparisons)


def workflow_elimination(candidates: list[np.ndarray],
                         preset: ABWorkflowPreset) -> ABWorkflowResult:
    """Weakest eliminated each round until one remains."""
    n = len(candidates)
    scores = [CandidateScore(index=i) for i in range(n)]
    rounds = []
    active = list(range(n))
    total_comparisons = 0
    round_num = 0

    while len(active) > 1:
        # Score everyone against each other this round
        round_scores = {idx: 0.0 for idx in active}
        round_matches = []
        for i, a_idx in enumerate(active):
            for b_idx in active[i + 1:]:
                result = _compare_pair(
                    candidates[a_idx], candidates[b_idx],
                    preset.comparison_metric, preset.fft_size)
                total_comparisons += 1
                if result.winner == "A":
                    round_scores[a_idx] += result.score_a
                    scores[a_idx].wins += 1
                    scores[b_idx].losses += 1
                else:
                    round_scores[b_idx] += result.score_b
                    scores[b_idx].wins += 1
                    scores[a_idx].losses += 1
                round_matches.append({
                    "a": a_idx, "b": b_idx, "winner": result.winner})
        # Eliminate weakest
        weakest = min(active, key=lambda k: round_scores[k])
        scores[weakest].eliminated = True
        active.remove(weakest)
        rounds.append({
            "round": round_num, "eliminated": weakest,
            "matches": round_matches
        })
        round_num += 1

    winner = active[0] if active else 0
    return ABWorkflowResult(
        name=preset.name, mode="elimination", winner_index=winner,
        winner_audio=candidates[winner], scores=scores, rounds=rounds,
        num_comparisons=total_comparisons)


def workflow_golden_split(candidates: list[np.ndarray],
                          preset: ABWorkflowPreset) -> ABWorkflowResult:
    """Split at PHI ratio, compare group averages, recurse on better half."""
    n = len(candidates)
    scores = [CandidateScore(index=i) for i in range(n)]
    rounds = []
    active = list(range(n))
    total_comparisons = 0
    round_num = 0

    while len(active) > 1:
        split = max(1, int(len(active) * (1.0 / PHI)))
        group_a = active[:split]
        group_b = active[split:]
        # Compare representative pairs across groups
        round_matches = []
        score_a_total = 0.0
        score_b_total = 0.0
        pairs = min(len(group_a), len(group_b))
        for i in range(pairs):
            a_idx, b_idx = group_a[i], group_b[i]
            result = _compare_pair(
                candidates[a_idx], candidates[b_idx],
                preset.comparison_metric, preset.fft_size)
            total_comparisons += 1
            if result.winner == "A":
                score_a_total += result.score_a
                scores[a_idx].wins += 1
            else:
                score_b_total += result.score_b
                scores[b_idx].wins += 1
            round_matches.append({
                "a": a_idx, "b": b_idx, "winner": result.winner})
        # Keep better group
        if score_a_total >= score_b_total:
            for idx in group_b:
                scores[idx].eliminated = True
            active = group_a
        else:
            for idx in group_a:
                scores[idx].eliminated = True
            active = group_b
        rounds.append({
            "round": round_num, "split": split,
            "kept": "A" if score_a_total >= score_b_total else "B",
            "matches": round_matches
        })
        round_num += 1

    winner = active[0] if active else 0
    return ABWorkflowResult(
        name=preset.name, mode="golden_split", winner_index=winner,
        winner_audio=candidates[winner], scores=scores, rounds=rounds,
        num_comparisons=total_comparisons)


def workflow_blind_vote(candidates: list[np.ndarray],
                        preset: ABWorkflowPreset) -> ABWorkflowResult:
    """Randomized blind comparison using composite scoring only."""
    n = len(candidates)
    scores = [CandidateScore(index=i) for i in range(n)]
    rng = np.random.default_rng(42)
    total_comparisons = 0
    matches = []

    # Create randomized pair schedule
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(pairs)

    for a_idx, b_idx in pairs:
        result = _compare_pair(
            candidates[a_idx], candidates[b_idx], "composite", preset.fft_size)
        total_comparisons += 1
        if result.winner == "A":
            scores[a_idx].wins += 1
            scores[a_idx].total_score += result.score_a
            scores[b_idx].losses += 1
        else:
            scores[b_idx].wins += 1
            scores[b_idx].total_score += result.score_b
            scores[a_idx].losses += 1
        matches.append({
            "a": a_idx, "b": b_idx, "winner": result.winner,
            "score_a": result.score_a, "score_b": result.score_b
        })

    winner = max(range(n), key=lambda k: scores[k].total_score)
    return ABWorkflowResult(
        name=preset.name, mode="blind_vote", winner_index=winner,
        winner_audio=candidates[winner], scores=scores,
        rounds=[{"round": 0, "matches": matches}],
        num_comparisons=total_comparisons)


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

WORKFLOW_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "bracket": workflow_bracket,
    "round_robin": workflow_round_robin,
    "elimination": workflow_elimination,
    "golden_split": workflow_golden_split,
    "blind_vote": workflow_blind_vote,
}


def run_ab_workflow(preset: ABWorkflowPreset,
                    candidates: list[np.ndarray] | None = None) -> ABWorkflowResult:
    """Run full A/B workflow session."""
    if candidates is None:
        candidates = _generate_candidates(preset)
    fn = WORKFLOW_FUNCTIONS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown A/B workflow mode: {preset.mode}")
    _log.info("AB workflow '%s' mode=%s candidates=%d",
              preset.name, preset.mode, len(candidates))
    return fn(candidates, preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def bracket_bank() -> ABWorkflowBank:
    return ABWorkflowBank("bracket", [
        ABWorkflowPreset("bracket_bass_8", "bracket", num_candidates=8, base_freq=65),
        ABWorkflowPreset("bracket_mid_16", "bracket", num_candidates=16, base_freq=220),
        ABWorkflowPreset("bracket_spectral", "bracket", num_candidates=8,
                         comparison_metric="spectral"),
        ABWorkflowPreset("bracket_phi", "bracket", num_candidates=8,
                         comparison_metric="phi_ratio"),
    ])


def round_robin_bank() -> ABWorkflowBank:
    return ABWorkflowBank("round_robin", [
        ABWorkflowPreset("rr_bass_4", "round_robin", num_candidates=4, base_freq=65),
        ABWorkflowPreset("rr_wide_6", "round_robin", num_candidates=6, freq_spread=2.0),
        ABWorkflowPreset("rr_harmonics", "round_robin", num_candidates=4, harmonics=16),
        ABWorkflowPreset("rr_long", "round_robin", num_candidates=4, duration=3.0),
    ])


def elimination_bank() -> ABWorkflowBank:
    return ABWorkflowBank("elimination", [
        ABWorkflowPreset("elim_8", "elimination", num_candidates=8),
        ABWorkflowPreset("elim_6_phi", "elimination", num_candidates=6,
                         comparison_metric="phi_ratio"),
        ABWorkflowPreset("elim_12_full", "elimination", num_candidates=12),
        ABWorkflowPreset("elim_temporal", "elimination", num_candidates=8,
                         comparison_metric="temporal"),
    ])


def golden_split_bank() -> ABWorkflowBank:
    return ABWorkflowBank("golden_split", [
        ABWorkflowPreset("golden_8", "golden_split", num_candidates=8),
        ABWorkflowPreset("golden_13_fib", "golden_split", num_candidates=13),
        ABWorkflowPreset("golden_bass", "golden_split", num_candidates=8, base_freq=40),
        ABWorkflowPreset("golden_wide", "golden_split", num_candidates=8, freq_spread=3.0),
    ])


def blind_vote_bank() -> ABWorkflowBank:
    return ABWorkflowBank("blind_vote", [
        ABWorkflowPreset("blind_8", "blind_vote", num_candidates=8),
        ABWorkflowPreset("blind_4_fast", "blind_vote", num_candidates=4),
        ABWorkflowPreset("blind_harmonics", "blind_vote", num_candidates=8, harmonics=12),
        ABWorkflowPreset("blind_deep_bass", "blind_vote", num_candidates=6, base_freq=32),
    ])


ALL_AB_WORKFLOW_BANKS = [
    bracket_bank, round_robin_bank, elimination_bank,
    golden_split_bank, blind_vote_bank,
]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_ab_workflow(result: ABWorkflowResult,
                       output_dir: str = "output/ab_workflow") -> dict[str, str]:
    """Export workflow results: winner WAV + full report JSON."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    wav_path = out / f"{result.name}_winner.wav"
    write_wav(str(wav_path), result.winner_audio, SAMPLE_RATE)

    report_path = out / f"{result.name}_report.json"
    report = {
        "name": result.name,
        "mode": result.mode,
        "winner_index": result.winner_index,
        "num_comparisons": result.num_comparisons,
        "scores": [
            {"index": s.index, "wins": s.wins, "losses": s.losses,
             "total_score": round(s.total_score, 4), "eliminated": s.eliminated}
            for s in result.scores
        ],
        "rounds": result.rounds,
    }
    report_path.write_text(json.dumps(report, indent=2))
    return {"wav": str(wav_path), "report": str(report_path)}
