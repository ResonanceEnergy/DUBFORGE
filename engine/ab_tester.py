"""
DUBFORGE — A/B Tester  (Session 126 · v3.7.0)

Render two patch variants, compare spectral profiles,
pick the more phi-coherent one.

5 comparison types × 4 presets = 20 presets.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import fft, ifft
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ABResult:
    """Result of an A/B comparison."""
    winner: str           # "A" or "B"
    score_a: float = 0.0
    score_b: float = 0.0
    metric: str = ""
    detail: dict = field(default_factory=dict)


@dataclass
class ABPreset:
    name: str
    comparison_type: str  # spectral | temporal | phi_ratio | loudness | composite
    fft_size: int = 4096
    duration: float = 0.5
    freq_a: float = 432.0
    freq_b: float = 440.0
    harmonics_a: int = 5
    harmonics_b: int = 5


@dataclass
class ABBank:
    name: str
    presets: list[ABPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _gen_signal(freq: float, harmonics: int, dur: float) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    sig = np.zeros_like(t)
    for h in range(1, harmonics + 1):
        sig += np.sin(2 * np.pi * freq * h * t) / (h ** PHI)
    return sig / (np.max(np.abs(sig)) + 1e-12)


# ═══════════════════════════════════════════════════════════════════════════
# COMPARISON FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def compare_spectral(sig_a: np.ndarray, sig_b: np.ndarray, preset: ABPreset) -> ABResult:
    """Compare spectral richness (number of significant peaks)."""
    def _count_peaks(sig):
        spec = np.abs(fft(sig[:preset.fft_size] * np.hanning(min(len(sig), preset.fft_size))))
        threshold = np.max(spec) * 0.05
        peaks = sum(1 for i in range(1, len(spec) - 1)
                    if spec[i] > spec[i - 1] and spec[i] > spec[i + 1] and spec[i] > threshold)
        return float(peaks)

    score_a = _count_peaks(sig_a)
    score_b = _count_peaks(sig_b)
    # Normalize
    mx = max(score_a, score_b, 1)
    return ABResult(
        winner="A" if score_a >= score_b else "B",
        score_a=score_a / mx,
        score_b=score_b / mx,
        metric="spectral_peaks",
    )


def compare_temporal(sig_a: np.ndarray, sig_b: np.ndarray, preset: ABPreset) -> ABResult:
    """Compare temporal dynamics (crest factor)."""
    def _crest(sig):
        rms = float(np.sqrt(np.mean(sig ** 2))) + 1e-12
        peak = float(np.max(np.abs(sig)))
        return peak / rms

    cf_a = _crest(sig_a)
    cf_b = _crest(sig_b)
    # Higher crest = more dynamic
    mx = max(cf_a, cf_b, 1)
    return ABResult(
        winner="A" if cf_a >= cf_b else "B",
        score_a=min(cf_a / mx, 1.0),
        score_b=min(cf_b / mx, 1.0),
        metric="crest_factor",
    )


def compare_phi_ratio(sig_a: np.ndarray, sig_b: np.ndarray, preset: ABPreset) -> ABResult:
    """Compare phi-ratio coherence between spectral peaks."""
    def _phi_score(sig):
        spec = np.abs(fft(sig[:preset.fft_size]))
        freqs = np.fft.rfftfreq(preset.fft_size, 1.0 / SAMPLE_RATE)
        threshold = np.max(spec) * 0.05
        peak_freqs = freqs[[i for i in range(1, len(spec) - 1)
                            if spec[i] > spec[i - 1] and spec[i] > spec[i + 1]
                            and spec[i] > threshold]]
        if len(peak_freqs) < 2:
            return 0.0
        phi_count = 0
        total = 0
        for i in range(len(peak_freqs)):
            for j in range(i + 1, len(peak_freqs)):
                ratio = peak_freqs[j] / peak_freqs[i]
                if abs(ratio - PHI) / PHI < 0.05:
                    phi_count += 1
                total += 1
        return phi_count / max(total, 1)

    sa = _phi_score(sig_a)
    sb = _phi_score(sig_b)
    return ABResult(
        winner="A" if sa >= sb else "B",
        score_a=sa, score_b=sb,
        metric="phi_ratio",
    )


def compare_loudness(sig_a: np.ndarray, sig_b: np.ndarray, preset: ABPreset) -> ABResult:
    """Compare perceived loudness (RMS)."""
    rms_a = float(np.sqrt(np.mean(sig_a ** 2)))
    rms_b = float(np.sqrt(np.mean(sig_b ** 2)))
    mx = max(rms_a, rms_b, 1e-12)
    return ABResult(
        winner="A" if rms_a >= rms_b else "B",
        score_a=rms_a / mx, score_b=rms_b / mx,
        metric="rms_loudness",
    )


def compare_composite(sig_a: np.ndarray, sig_b: np.ndarray, preset: ABPreset) -> ABResult:
    """Weighted composite of all comparisons."""
    results = [
        compare_spectral(sig_a, sig_b, preset),
        compare_temporal(sig_a, sig_b, preset),
        compare_phi_ratio(sig_a, sig_b, preset),
        compare_loudness(sig_a, sig_b, preset),
    ]
    weights = [0.3, 0.2, 0.35, 0.15]
    total_a = sum(w * r.score_a for w, r in zip(weights, results))
    total_b = sum(w * r.score_b for w, r in zip(weights, results))
    return ABResult(
        winner="A" if total_a >= total_b else "B",
        score_a=round(total_a, 4), score_b=round(total_b, 4),
        metric="composite",
        detail={r.metric: {"A": r.score_a, "B": r.score_b} for r in results},
    )


COMPARISON_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "spectral": compare_spectral,
    "temporal": compare_temporal,
    "phi_ratio": compare_phi_ratio,
    "loudness": compare_loudness,
    "composite": compare_composite,
}


def run_ab_test(preset: ABPreset) -> ABResult:
    """Run an A/B test given a preset."""
    sig_a = _gen_signal(preset.freq_a, preset.harmonics_a, preset.duration)
    sig_b = _gen_signal(preset.freq_b, preset.harmonics_b, preset.duration)
    fn = COMPARISON_FUNCTIONS.get(preset.comparison_type)
    if fn is None:
        raise ValueError(f"Unknown comparison: {preset.comparison_type}")
    return fn(sig_a, sig_b, preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def spectral_ab_bank() -> ABBank:
    return ABBank("spectral", [
        ABPreset("spec_432v440", "spectral", freq_a=432, freq_b=440),
        ABPreset("spec_rich", "spectral", freq_a=432, freq_b=432, harmonics_a=8, harmonics_b=3),
        ABPreset("spec_octave", "spectral", freq_a=220, freq_b=440),
        ABPreset("spec_phi", "spectral", freq_a=432, freq_b=432 * PHI),
    ])


def temporal_ab_bank() -> ABBank:
    return ABBank("temporal", [
        ABPreset("temp_short", "temporal", duration=0.2),
        ABPreset("temp_long", "temporal", duration=1.0),
        ABPreset("temp_432v440", "temporal", freq_a=432, freq_b=440),
        ABPreset("temp_bass", "temporal", freq_a=55, freq_b=65),
    ])


def phi_ratio_ab_bank() -> ABBank:
    return ABBank("phi_ratio", [
        ABPreset("phi_432v440", "phi_ratio", freq_a=432, freq_b=440),
        ABPreset("phi_rich", "phi_ratio", harmonics_a=8, harmonics_b=4),
        ABPreset("phi_bass", "phi_ratio", freq_a=55, freq_b=55 * PHI),
        ABPreset("phi_lead", "phi_ratio", freq_a=880, freq_b=880 * PHI),
    ])


def loudness_ab_bank() -> ABBank:
    return ABBank("loudness", [
        ABPreset("loud_432v440", "loudness", freq_a=432, freq_b=440),
        ABPreset("loud_harm", "loudness", harmonics_a=8, harmonics_b=2),
        ABPreset("loud_bass", "loudness", freq_a=55, freq_b=110),
        ABPreset("loud_mid", "loudness", freq_a=500, freq_b=1000),
    ])


def composite_ab_bank() -> ABBank:
    return ABBank("composite", [
        ABPreset("comp_432v440", "composite", freq_a=432, freq_b=440),
        ABPreset("comp_phi", "composite", freq_a=432, freq_b=432 * PHI),
        ABPreset("comp_rich", "composite", harmonics_a=8, harmonics_b=3),
        ABPreset("comp_bass", "composite", freq_a=55, freq_b=55 * PHI),
    ])


ALL_AB_BANKS: dict[str, Callable[..., Any]] = {
    "spectral": spectral_ab_bank,
    "temporal": temporal_ab_bank,
    "phi_ratio": phi_ratio_ab_bank,
    "loudness": loudness_ab_bank,
    "composite": composite_ab_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def export_ab_results(output_dir: str = "output") -> list[str]:
    """Run all A/B tests and export results as JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for bank_name, gen_fn in ALL_AB_BANKS.items():
        bank = gen_fn()
        for preset in bank.presets:
            result = run_ab_test(preset)
            data = {
                "preset": preset.name,
                "comparison": preset.comparison_type,
                "winner": result.winner,
                "score_a": result.score_a,
                "score_b": result.score_b,
                "metric": result.metric,
                "detail": result.detail,
                "freq_a": preset.freq_a,
                "freq_b": preset.freq_b,
            }
            fpath = out / f"ab_{preset.name}.json"
            with open(fpath, "w") as f:
                json.dump(data, f, indent=2)
            paths.append(str(fpath))

    return paths


def write_ab_manifest(output_dir: str = "output") -> dict:
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "ab_tester", "banks": {}}
    for name, gen_fn in ALL_AB_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "ab_tester_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_ab_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    results = export_ab_results()
    print(f"A/B Tester: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(results)} test results")


if __name__ == "__main__":
    main()
