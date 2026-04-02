"""DUBFORGE — QA Validator.

Validates rendered audio against quality gates.
Used by _v9_stem_master and _v9_stem_postprocess for pass/fail decisions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class QAGate:
    """Single quality gate result."""
    name: str
    passed: bool
    value: float = 0.0
    threshold: float = 0.0
    description: str = ""


@dataclass
class QAResult:
    """Result of a full QA validation run."""
    passed: bool
    gates: list[QAGate] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        status = "PASS" if self.passed else "FAIL"
        lines.append(f"QA Validation: {status}")
        lines.append(f"  Gates: {sum(1 for g in self.gates if g.passed)}/{len(self.gates)} passed")
        for gate in self.gates:
            mark = "✓" if gate.passed else "✗"
            lines.append(f"  {mark} {gate.name}: {gate.value:.4f} "
                         f"(threshold: {gate.threshold:.4f}) {gate.description}")
        return "\n".join(lines)


def validate_render(left: np.ndarray, right: np.ndarray,
                    sr: int = 48000, has_vocals: bool = False) -> QAResult:
    """Validate a stereo render against quality gates.

    Gates:
    - Peak level: must be below 0dBFS (< 1.0)
    - DC offset: must be < 0.01
    - Silence ratio: must be < 50% (not mostly silent)
    - Stereo correlation: must be > -0.5 (not phase-inverted)
    - Crest factor: must be > 3dB (not over-compressed)
    - Noise floor: must be < -40dB in silent sections
    """
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    n = min(len(left), len(right))
    if n == 0:
        return QAResult(passed=False, gates=[
            QAGate("non_empty", False, 0, 1, "Audio is empty")
        ])

    left = left[:n]
    right = right[:n]

    gates = []

    # Gate 1: Peak level
    peak_l = float(np.max(np.abs(left)))
    peak_r = float(np.max(np.abs(right)))
    peak = max(peak_l, peak_r)
    gates.append(QAGate(
        "peak_level", peak < 1.0, peak, 1.0,
        "Peak must be below 0dBFS"
    ))

    # Gate 2: DC offset
    dc_l = abs(float(np.mean(left)))
    dc_r = abs(float(np.mean(right)))
    dc = max(dc_l, dc_r)
    gates.append(QAGate(
        "dc_offset", dc < 0.01, dc, 0.01,
        "DC offset must be < 0.01"
    ))

    # Gate 3: Silence ratio
    silence_thresh = 1e-5
    silence_l = float(np.mean(np.abs(left) < silence_thresh))
    silence_r = float(np.mean(np.abs(right) < silence_thresh))
    silence = max(silence_l, silence_r)
    gates.append(QAGate(
        "silence_ratio", silence < 0.50, silence, 0.50,
        "Audio must not be >50% silent"
    ))

    # Gate 4: Stereo correlation
    if peak > 0:
        # Pearson correlation
        l_norm = left - np.mean(left)
        r_norm = right - np.mean(right)
        denom = np.sqrt(np.sum(l_norm**2) * np.sum(r_norm**2))
        if denom > 0:
            corr = float(np.sum(l_norm * r_norm) / denom)
        else:
            corr = 1.0
    else:
        corr = 1.0
    gates.append(QAGate(
        "stereo_correlation", corr > -0.5, corr, -0.5,
        "Stereo correlation must be > -0.5 (not phase-inverted)"
    ))

    # Gate 5: Crest factor (peak/RMS ratio in dB)
    rms_l = float(np.sqrt(np.mean(left**2)))
    rms_r = float(np.sqrt(np.mean(right**2)))
    rms = max(rms_l, rms_r)
    if rms > 0:
        crest_db = 20 * np.log10(peak / rms)
    else:
        crest_db = 60.0  # effectively infinite crest (silence)
    gates.append(QAGate(
        "crest_factor", crest_db > 3.0, crest_db, 3.0,
        "Crest factor must be > 3dB (not over-compressed)"
    ))

    # Gate 6: Noise floor in silent sections
    # Find sections below -40dB
    rms_window = sr // 10  # 100ms windows
    if n > rms_window * 2:
        num_windows = n // rms_window
        rms_values = []
        for w in range(num_windows):
            start = w * rms_window
            end = start + rms_window
            w_rms = float(np.sqrt(np.mean(left[start:end]**2 + right[start:end]**2)))
            rms_values.append(w_rms)
        rms_values.sort()
        # Lowest 10% of windows = noise floor estimate
        floor_idx = max(1, len(rms_values) // 10)
        noise_floor = np.mean(rms_values[:floor_idx])
        noise_floor_db = 20 * np.log10(max(noise_floor, 1e-12))
        gates.append(QAGate(
            "noise_floor", noise_floor_db < -40.0, noise_floor_db, -40.0,
            "Noise floor must be < -40dB"
        ))

    all_passed = all(g.passed for g in gates)
    return QAResult(passed=all_passed, gates=gates)
