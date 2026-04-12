"""
DUBFORGE Engine — VIP Generator (Fractals → Antifractals)

Full VIP generation pipeline that extends vip_pack.py with:
    1. Analyze original track/sound → extract fractal structure
    2. Apply phi-ratio mutations (Fractals)
    3. Invert/mirror mutations (Antifractals)
    4. A/B compare variants
    5. Select winners → build VIP pack

The Fractals → Antifractals workflow:
    FRACTAL:      Apply PHI-scaled changes (×1.618 / ÷1.618)
    ANTIFRACTAL:  Invert the fractal changes (mirror transform)
    Each original produces 2 variants, best is selected by A/B comparison.

VIP Generation Rule:
    Change 61.8% (PHI ratio), keep 38.2% — maintains recognition + freshness.

Modes:
    pitch_fractal   — Pitch mutations along phi ratio + mirror
    spectral_fractal — Spectral shape shift + inverse
    rhythm_fractal  — Time-domain stutter/stretch patterns + inverse
    harmonic_fractal — Harmonic content mutation + inverse
    full_fractal    — Combined multi-parameter fractal transform

Banks: 5 modes × 4 presets = 20 presets
"""

from __future__ import annotations
from typing import Any, Callable

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE
from engine.accel import fft, ifft, write_wav
from engine.ab_tester import compare_composite, ABPreset

_log = get_logger("dubforge.vip_generator")

PHI_KEEP = 1.0 / PHI      # 0.618 — fraction to CHANGE
PHI_HOLD = 1.0 - PHI_KEEP  # 0.382 — fraction to KEEP


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VIPGenPreset:
    name: str
    mode: str  # pitch_fractal | spectral_fractal | rhythm_fractal | harmonic_fractal | full_fractal
    duration_s: float = 2.0
    base_freq: float = 65.0
    harmonics: int = 8
    # Mutation intensity
    fractal_depth: float = 1.0  # multiplier on mutation amount
    # Generation
    candidates_per_variant: int = 4
    fft_size: int = 4096


@dataclass
class VIPGenBank:
    name: str
    presets: list[VIPGenPreset] = field(default_factory=list)


@dataclass
class VIPVariant:
    """A single VIP variant (fractal or antifractal)."""
    name: str
    variant_type: str  # "fractal" or "antifractal"
    audio: np.ndarray
    mutations: list[str]


@dataclass
class VIPGenResult:
    name: str
    mode: str
    original: np.ndarray
    fractal: VIPVariant
    antifractal: VIPVariant
    winner: str  # "fractal" or "antifractal"
    winner_audio: np.ndarray
    score_fractal: float
    score_antifractal: float


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def _generate_source(freq: float, harmonics: int, duration_s: float,
                     sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a bass/synth source signal."""
    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n, endpoint=False)
    sig = np.zeros(n)
    for h in range(1, harmonics + 1):
        amp = 1.0 / (h ** PHI)
        sig += amp * np.sin(2 * math.pi * freq * h * t)
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig /= peak
    return sig


def _normalize(sig: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(sig))
    return sig / peak * 0.95 if peak > 0 else sig


# ═══════════════════════════════════════════════════════════════════════════
# FRACTAL / ANTIFRACTAL TRANSFORMS
# ═══════════════════════════════════════════════════════════════════════════

def _pitch_shift(sig: np.ndarray, semitones: float,
                 sr: int = SAMPLE_RATE) -> np.ndarray:
    """Simple pitch shift via resampling."""
    ratio = 2.0 ** (semitones / 12.0)
    n = len(sig)
    new_len = max(2, int(n / ratio))
    indices = np.linspace(0, n - 1, new_len)
    shifted = np.interp(indices, np.arange(n), sig)
    # Fit back to original length
    if len(shifted) < n:
        out = np.zeros(n)
        out[:len(shifted)] = shifted
        return out
    return shifted[:n]


def pitch_fractal(original: np.ndarray, preset: VIPGenPreset,
                  sr: int = SAMPLE_RATE) -> tuple[VIPVariant, VIPVariant]:
    """Pitch mutation: fractal = ×PHI semitones, antifractal = ÷PHI semitones."""
    shift = PHI * preset.fractal_depth
    fractal_audio = _pitch_shift(original, shift, sr)
    anti_audio = _pitch_shift(original, -shift, sr)
    return (
        VIPVariant(f"{preset.name}_pitch_frac", "fractal", _normalize(fractal_audio),
                   [f"pitch +{shift:.2f}st"]),
        VIPVariant(f"{preset.name}_pitch_anti", "antifractal", _normalize(anti_audio),
                   [f"pitch -{shift:.2f}st"]),
    )


def spectral_fractal(original: np.ndarray, preset: VIPGenPreset,
                      sr: int = SAMPLE_RATE) -> tuple[VIPVariant, VIPVariant]:
    """Spectral shape mutation: boost/cut harmonics at phi-ratio positions."""
    n = len(original)
    spec = fft(original)
    n_spec = len(spec)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)

    # Fractal: boost harmonics at phi positions
    frac_spec = spec.copy()
    anti_spec = spec.copy()
    for k in range(1, 8):
        target_freq = preset.base_freq * (PHI ** k)
        if target_freq > sr / 2:
            break
        # Find nearest bin
        bin_idx = int(target_freq / (sr / n))
        spread = max(1, int(n / sr * 50))
        lo = max(0, bin_idx - spread)
        hi = min(n_spec, bin_idx + spread)
        boost = 1.0 + preset.fractal_depth * 0.5
        # Fractal boosts, antifractal cuts
        frac_spec[lo:hi] *= boost
        anti_spec[lo:hi] *= 1.0 / boost

    frac_audio = ifft(frac_spec, n=n)
    anti_audio = ifft(anti_spec, n=n)
    return (
        VIPVariant(f"{preset.name}_spec_frac", "fractal", _normalize(frac_audio),
                   ["spectral boost at phi harmonics"]),
        VIPVariant(f"{preset.name}_spec_anti", "antifractal", _normalize(anti_audio),
                   ["spectral cut at phi harmonics"]),
    )


def rhythm_fractal(original: np.ndarray, preset: VIPGenPreset,
                   sr: int = SAMPLE_RATE) -> tuple[VIPVariant, VIPVariant]:
    """Time-domain stutter/stretch at phi intervals."""
    n = len(original)
    # Fractal: stutter (repeat PHI-positioned segment)
    phi_pos = int(n * (1.0 / PHI))
    segment_len = max(256, int(n * 0.1))

    # Fractal variant: stutter the phi-positioned segment
    frac = original.copy()
    start = max(0, phi_pos - segment_len // 2)
    end = min(n, start + segment_len)
    seg = original[start:end]
    # Repeat segment in second half
    paste_start = int(n * PHI_KEEP)
    paste_end = min(n, paste_start + len(seg))
    frac[paste_start:paste_end] = seg[:paste_end - paste_start]

    # Antifractal: silence at phi position, extend rest
    anti = original.copy()
    anti[start:end] *= np.linspace(1, 0, end - start)  # fade out the phi segment

    return (
        VIPVariant(f"{preset.name}_rhythm_frac", "fractal", _normalize(frac),
                   [f"stutter at phi_pos={phi_pos}"]),
        VIPVariant(f"{preset.name}_rhythm_anti", "antifractal", _normalize(anti),
                   [f"fade at phi_pos={phi_pos}"]),
    )


def harmonic_fractal(original: np.ndarray, preset: VIPGenPreset,
                     sr: int = SAMPLE_RATE) -> tuple[VIPVariant, VIPVariant]:
    """Harmonic content mutation: add/remove harmonic layers."""
    n = len(original)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)

    # Fractal: add upper phi-spaced harmonics
    extra = np.zeros(n)
    for k in range(1, 5):
        freq = preset.base_freq * (PHI ** (k + preset.harmonics / PHI))
        if freq > sr / 2:
            break
        amp = 0.3 / (k ** PHI) * preset.fractal_depth
        extra += amp * np.sin(2 * math.pi * freq * t)

    frac_audio = original + extra
    # Antifractal: subtract (shelve out upper harmonics via lowpass)
    anti_audio = original.copy()
    spec = fft(anti_audio)
    cutoff_bin = max(1, int(preset.base_freq * PHI ** 3 / (sr / n)))
    if cutoff_bin < len(spec):
        rolloff = np.ones(len(spec))
        for i in range(cutoff_bin, len(spec)):
            rolloff[i] = max(0, 1.0 - (i - cutoff_bin) / max(len(spec) - cutoff_bin, 1))
        spec *= rolloff
    anti_audio = ifft(spec, n=n)

    return (
        VIPVariant(f"{preset.name}_harm_frac", "fractal", _normalize(frac_audio),
                   ["added phi-spaced upper harmonics"]),
        VIPVariant(f"{preset.name}_harm_anti", "antifractal", _normalize(anti_audio),
                   ["lowpass shelved upper harmonics"]),
    )


def full_fractal(original: np.ndarray, preset: VIPGenPreset,
                 sr: int = SAMPLE_RATE) -> tuple[VIPVariant, VIPVariant]:
    """Combined: pitch + spectral + harmonic transform."""
    n = len(original)
    # Fractal: chain all transforms at reduced intensity
    mild_preset = VIPGenPreset(
        name=preset.name, mode=preset.mode, duration_s=preset.duration_s,
        base_freq=preset.base_freq, harmonics=preset.harmonics,
        fractal_depth=preset.fractal_depth * 0.5, fft_size=preset.fft_size)

    # Pitch
    pitch_frac, _ = pitch_fractal(original, mild_preset, sr)
    # Spectral on top of pitched
    spec_frac, _ = spectral_fractal(pitch_frac.audio, mild_preset, sr)
    frac_audio = spec_frac.audio

    # Antifractal: inverse chain
    _, pitch_anti = pitch_fractal(original, mild_preset, sr)
    _, spec_anti = spectral_fractal(pitch_anti.audio, mild_preset, sr)
    anti_audio = spec_anti.audio

    return (
        VIPVariant(f"{preset.name}_full_frac", "fractal", _normalize(frac_audio),
                   ["pitch+spectral fractal chain"]),
        VIPVariant(f"{preset.name}_full_anti", "antifractal", _normalize(anti_audio),
                   ["pitch+spectral antifractal chain"]),
    )


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

VIP_GENERATORS: dict[str, Callable[..., Any]] = {
    "pitch_fractal": pitch_fractal,
    "spectral_fractal": spectral_fractal,
    "rhythm_fractal": rhythm_fractal,
    "harmonic_fractal": harmonic_fractal,
    "full_fractal": full_fractal,
}


def run_vip_generation(preset: VIPGenPreset,
                       source: np.ndarray | None = None) -> VIPGenResult:
    """
    Full VIP generation pipeline:
    1. Generate or accept source
    2. Create fractal + antifractal variants
    3. A/B compare both against original
    4. Select winner
    """
    if source is None:
        source = _generate_source(preset.base_freq, preset.harmonics, preset.duration_s)

    fn = VIP_GENERATORS.get(preset.mode)
    if fn is None:
        raise ValueError(f"Unknown VIP gen mode: {preset.mode}")

    fractal, antifractal = fn(source, preset)

    # A/B compare both variants against each other
    ab_preset = ABPreset(
        name="_vip_ab", comparison_type="composite", fft_size=preset.fft_size)
    result = compare_composite(fractal.audio, antifractal.audio, ab_preset)

    if result.winner == "A":
        winner_type = "fractal"
        winner_audio = fractal.audio
    else:
        winner_type = "antifractal"
        winner_audio = antifractal.audio

    _log.info("VIP '%s' mode=%s winner=%s (f=%.4f af=%.4f)",
              preset.name, preset.mode, winner_type,
              result.score_a, result.score_b)

    return VIPGenResult(
        name=preset.name, mode=preset.mode, original=source,
        fractal=fractal, antifractal=antifractal,
        winner=winner_type, winner_audio=winner_audio,
        score_fractal=result.score_a, score_antifractal=result.score_b,
    )


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def pitch_fractal_bank() -> VIPGenBank:
    return VIPGenBank("pitch_fractal", [
        VIPGenPreset("bass_pitch_vip", "pitch_fractal", base_freq=65),
        VIPGenPreset("mid_pitch_vip", "pitch_fractal", base_freq=220),
        VIPGenPreset("deep_pitch_vip", "pitch_fractal", base_freq=32, fractal_depth=2.0),
        VIPGenPreset("subtle_pitch_vip", "pitch_fractal", fractal_depth=0.5),
    ])


def spectral_fractal_bank() -> VIPGenBank:
    return VIPGenBank("spectral_fractal", [
        VIPGenPreset("bass_spectral_vip", "spectral_fractal", base_freq=65),
        VIPGenPreset("bright_spectral_vip", "spectral_fractal", harmonics=16),
        VIPGenPreset("deep_spectral_vip", "spectral_fractal", base_freq=32,
                     fractal_depth=1.5),
        VIPGenPreset("subtle_spectral_vip", "spectral_fractal", fractal_depth=0.3),
    ])


def rhythm_fractal_bank() -> VIPGenBank:
    return VIPGenBank("rhythm_fractal", [
        VIPGenPreset("stutter_rhythm_vip", "rhythm_fractal"),
        VIPGenPreset("long_rhythm_vip", "rhythm_fractal", duration_s=4.0),
        VIPGenPreset("fast_rhythm_vip", "rhythm_fractal", duration_s=0.5),
        VIPGenPreset("deep_rhythm_vip", "rhythm_fractal", base_freq=40, fractal_depth=1.5),
    ])


def harmonic_fractal_bank() -> VIPGenBank:
    return VIPGenBank("harmonic_fractal", [
        VIPGenPreset("add_harmonics_vip", "harmonic_fractal", harmonics=8),
        VIPGenPreset("rich_harmonics_vip", "harmonic_fractal", harmonics=16),
        VIPGenPreset("sub_harmonics_vip", "harmonic_fractal", base_freq=32, harmonics=4),
        VIPGenPreset("bright_harmonics_vip", "harmonic_fractal", base_freq=220),
    ])


def full_fractal_bank() -> VIPGenBank:
    return VIPGenBank("full_fractal", [
        VIPGenPreset("full_bass_vip", "full_fractal", base_freq=65),
        VIPGenPreset("full_mid_vip", "full_fractal", base_freq=220),
        VIPGenPreset("full_deep_vip", "full_fractal", base_freq=32, fractal_depth=2.0),
        VIPGenPreset("full_subtle_vip", "full_fractal", fractal_depth=0.3),
    ])


ALL_VIP_GEN_BANKS = [
    pitch_fractal_bank, spectral_fractal_bank, rhythm_fractal_bank,
    harmonic_fractal_bank, full_fractal_bank,
]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_vip_results(results: list[VIPGenResult],
                       output_dir: str = "output/vip_gen") -> list[str]:
    """Export VIP generation results."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for r in results:
        # Winner
        winner_path = out / f"{r.name}_winner_{r.winner}.wav"
        write_wav(str(winner_path), r.winner_audio, SAMPLE_RATE)
        paths.append(str(winner_path))
        # Both variants
        frac_path = out / f"{r.name}_fractal.wav"
        write_wav(str(frac_path), r.fractal.audio, SAMPLE_RATE)
        paths.append(str(frac_path))
        anti_path = out / f"{r.name}_antifractal.wav"
        write_wav(str(anti_path), r.antifractal.audio, SAMPLE_RATE)
        paths.append(str(anti_path))
    return paths


def write_vip_manifest(results: list[VIPGenResult],
                       output_dir: str = "output/analysis") -> str:
    """Write manifest of VIP generation results."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "vip_generator_manifest.json"
    data = [{
        "name": r.name,
        "mode": r.mode,
        "winner": r.winner,
        "score_fractal": round(r.score_fractal, 4),
        "score_antifractal": round(r.score_antifractal, 4),
        "fractal_mutations": r.fractal.mutations,
        "antifractal_mutations": r.antifractal.mutations,
    } for r in results]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
