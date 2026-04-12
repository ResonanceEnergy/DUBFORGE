"""
DUBFORGE — Sound Palette  (Session 130)

Define a "palette" of timbres (warm, cold, metallic, organic)
mapped to phi-harmonic profiles. Each palette generates test tones
as .wav files.

5 palette types × 4 presets = 20 presets.
"""

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import write_wav
PHI_INV = 1.0 / PHI


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PaletteColor:
    """A single timbre in the palette."""
    name: str
    fundamental: float = 432.0
    harmonics: list[float] = field(default_factory=lambda: [1.0, 0.5, 0.25])
    harmonic_ratios: list[float] = field(default_factory=lambda: [1.0, 2.0, 3.0])
    filter_cutoff: float = 0.8
    attack: float = 0.01
    decay: float = 0.3
    brightness: float = 0.5   # 0 = dark, 1 = bright


@dataclass
class PalettePreset:
    name: str
    palette_type: str  # warm | cold | metallic | organic | hybrid
    num_colors: int = 5
    base_freq: float = 432.0
    phi_spacing: bool = True


@dataclass
class PaletteBank:
    name: str
    presets: list[PalettePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# PALETTE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _generate_warm_color(idx: int, base_freq: float, phi_spacing: bool) -> PaletteColor:
    freq = base_freq * (PHI ** idx if phi_spacing else (idx + 1))
    return PaletteColor(
        name=f"warm_{idx}",
        fundamental=freq,
        harmonics=[1.0 / (h ** 1.5) for h in range(1, 7)],
        harmonic_ratios=[float(h) for h in range(1, 7)],
        filter_cutoff=0.5 + 0.1 * idx,
        attack=0.02, decay=0.5,
        brightness=0.3 + 0.05 * idx,
    )


def _generate_cold_color(idx: int, base_freq: float, phi_spacing: bool) -> PaletteColor:
    freq = base_freq * (PHI ** idx if phi_spacing else (idx + 1))
    return PaletteColor(
        name=f"cold_{idx}",
        fundamental=freq,
        harmonics=[1.0 / (h ** 0.8) for h in range(1, 9)],
        harmonic_ratios=[float(h) for h in range(1, 9)],
        filter_cutoff=0.8, attack=0.005, decay=0.2,
        brightness=0.7 + 0.05 * idx,
    )


def _generate_metallic_color(idx: int, base_freq: float, phi_spacing: bool) -> PaletteColor:
    freq = base_freq * (PHI ** idx if phi_spacing else (idx + 1))
    # Inharmonic ratios for metallic quality
    ratios = [1.0, 1.414, 2.236, 3.162, 4.123, 5.099]
    return PaletteColor(
        name=f"metallic_{idx}",
        fundamental=freq,
        harmonics=[1.0 / (h ** 0.5) for h in range(1, 7)],
        harmonic_ratios=ratios,
        filter_cutoff=0.9, attack=0.001, decay=0.8,
        brightness=0.85,
    )


def _generate_organic_color(idx: int, base_freq: float, phi_spacing: bool) -> PaletteColor:
    freq = base_freq * (PHI ** idx if phi_spacing else (idx + 1))
    # Phi-ratio harmonics
    ratios = [PHI ** i for i in range(6)]
    return PaletteColor(
        name=f"organic_{idx}",
        fundamental=freq,
        harmonics=[1.0 / (PHI ** i) for i in range(6)],
        harmonic_ratios=ratios,
        filter_cutoff=0.6, attack=0.03, decay=0.6,
        brightness=0.4,
    )


def _generate_hybrid_color(idx: int, base_freq: float, phi_spacing: bool) -> PaletteColor:
    freq = base_freq * (PHI ** idx if phi_spacing else (idx + 1))
    # Mix of harmonic and inharmonic
    ratios = [1.0, PHI, 2.0, PHI * 2, 3.0, PHI * 3]
    return PaletteColor(
        name=f"hybrid_{idx}",
        fundamental=freq,
        harmonics=[1.0 / (h ** 1.0) for h in range(1, 7)],
        harmonic_ratios=ratios,
        filter_cutoff=0.7, attack=0.01, decay=0.4,
        brightness=0.55,
    )


PALETTE_GENERATORS: dict[str, Callable[..., Any]] = {
    "warm": _generate_warm_color,
    "cold": _generate_cold_color,
    "metallic": _generate_metallic_color,
    "organic": _generate_organic_color,
    "hybrid": _generate_hybrid_color,
}


def generate_palette(preset: PalettePreset) -> list[PaletteColor]:
    """Generate a palette of colors for the given preset."""
    gen_fn = PALETTE_GENERATORS.get(preset.palette_type)
    if gen_fn is None:
        raise ValueError(f"Unknown palette type: {preset.palette_type}")
    return [gen_fn(i, preset.base_freq, preset.phi_spacing) for i in range(preset.num_colors)]


def render_palette_tone(color: PaletteColor, duration: float = 0.5) -> np.ndarray:
    """Render a single palette color as a waveform."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    sig = np.zeros(n)
    for amp, ratio in zip(color.harmonics, color.harmonic_ratios):
        freq = color.fundamental * ratio
        if freq > SAMPLE_RATE / 2:
            break
        sig += amp * np.sin(2 * np.pi * freq * t)

    # Apply envelope
    attack_n = int(color.attack * SAMPLE_RATE)
    decay_n = int(color.decay * SAMPLE_RATE)
    env = np.ones(n)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0, 1, attack_n)
    if decay_n > 0 and n > attack_n:
        decay_start = max(attack_n, n - decay_n)
        env[decay_start:] = np.linspace(1, 0, n - decay_start)

    sig *= env

    # Brightness filter (simple low-pass approximation)
    if color.brightness < 0.9:
        cutoff_freq = color.brightness * SAMPLE_RATE / 2
        # Very simple single-pole filter
        rc = 1.0 / (2.0 * np.pi * max(cutoff_freq, 1))
        dt = 1.0 / SAMPLE_RATE
        alpha = dt / (rc + dt)
        filtered = np.zeros_like(sig)
        filtered[0] = sig[0]
        for i in range(1, len(sig)):
            filtered[i] = filtered[i - 1] + alpha * (sig[i] - filtered[i - 1])
        sig = filtered

    # Normalize
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig = sig / peak * 0.9

    return sig


def _write_wav(path: str, signal: np.ndarray) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s)



# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def warm_bank() -> PaletteBank:
    return PaletteBank("warm", [
        PalettePreset("warm_phi", "warm", 5, 432.0, True),
        PalettePreset("warm_harmonic", "warm", 5, 432.0, False),
        PalettePreset("warm_bass", "warm", 4, 55.0, True),
        PalettePreset("warm_rich", "warm", 8, 432.0, True),
    ])


def cold_bank() -> PaletteBank:
    return PaletteBank("cold", [
        PalettePreset("cold_phi", "cold", 5, 432.0, True),
        PalettePreset("cold_bright", "cold", 5, 880.0, True),
        PalettePreset("cold_bass", "cold", 4, 110.0, False),
        PalettePreset("cold_wide", "cold", 8, 432.0, True),
    ])


def metallic_bank() -> PaletteBank:
    return PaletteBank("metallic", [
        PalettePreset("metal_phi", "metallic", 5, 432.0, True),
        PalettePreset("metal_bell", "metallic", 6, 880.0, True),
        PalettePreset("metal_dark", "metallic", 4, 220.0, False),
        PalettePreset("metal_rich", "metallic", 8, 432.0, True),
    ])


def organic_bank() -> PaletteBank:
    return PaletteBank("organic", [
        PalettePreset("org_phi", "organic", 5, 432.0, True),
        PalettePreset("org_earth", "organic", 5, 136.1, True),
        PalettePreset("org_breath", "organic", 4, 220.0, False),
        PalettePreset("org_deep", "organic", 6, 55.0, True),
    ])


def hybrid_palette_bank() -> PaletteBank:
    return PaletteBank("hybrid", [
        PalettePreset("hyb_phi", "hybrid", 5, 432.0, True),
        PalettePreset("hyb_complex", "hybrid", 8, 432.0, True),
        PalettePreset("hyb_bass", "hybrid", 4, 55.0, False),
        PalettePreset("hyb_bright", "hybrid", 5, 880.0, True),
    ])


ALL_PALETTE_BANKS: dict[str, Callable[..., Any]] = {
    "warm": warm_bank,
    "cold": cold_bank,
    "metallic": metallic_bank,
    "organic": organic_bank,
    "hybrid": hybrid_palette_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def export_palette_tones(output_dir: str = "output") -> list[str]:
    """Generate all palette tones as .wav files."""
    out = Path(output_dir) / "wavetables" / "palettes"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for bank_name, gen_fn in ALL_PALETTE_BANKS.items():
        bank = gen_fn()
        for preset in bank.presets:
            palette = generate_palette(preset)
            for color in palette:
                sig = render_palette_tone(color, 0.5)
                fpath = str(out / f"palette_{preset.name}_{color.name}.wav")
                _write_wav(fpath, sig)
                paths.append(fpath)

    return paths


def write_palette_manifest(output_dir: str = "output") -> dict:
    out = Path(output_dir) / "wavetables" / "palettes"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "sound_palette", "banks": {}}
    for name, gen_fn in ALL_PALETTE_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "sound_palette_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_palette_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    tones = export_palette_tones()
    print(f"Sound Palette: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(tones)} palette tones")


if __name__ == "__main__":
    main()
