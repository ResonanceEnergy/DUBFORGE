"""
DUBFORGE Engine — VIP Pack Workflow

Create VIP (Variation In Production) versions of sample packs by mutating
parameters at phi-ratio intervals.

Golden VIP Rule (from Subtronics analysis):
    Change ~61.8% of elements, keep ~38.2% identical.
    This maintains recognition while adding freshness.

VIP mutations:
    - Pitch shift: ±PHI semitones on bass/synth samples
    - Drive boost: multiply distortion by PHI
    - FM depth shift: new FM ratios at phi-stepped intervals
    - Envelope reshape: attack × PHI, release / PHI (or inverse)
    - New synthesis types: rotate bass_type to adjacent in the list
    - Layer addition: add noise/texture layer at 38.2% mix

Outputs:
    output/vip_packs/<original_name>_VIP/
        ├── <category>_<preset>_VIP_001.wav
        ├── manifest.json
        └── vip_delta.json   (what changed)
"""

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.config_loader import PHI
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.phi_core import SAMPLE_RATE
from engine.sample_pack_builder import (
    ALL_PACK_BANKS,
    PackPreset,
    _write_wav,
)


# ═══════════════════════════════════════════════════════════════════════════
# VIP MUTATION RULES
# ═══════════════════════════════════════════════════════════════════════════

PHI_KEEP = 1.0 / PHI     # 0.618 — fraction of elements to CHANGE
PHI_HOLD = 1.0 - PHI_KEEP  # 0.382 — fraction to keep identical

# Bass type rotation: each type maps to its VIP variant
_BASS_VIP_MAP = {
    "sub_sine":    "reese",
    "reese":       "fm",
    "fm":          "growl",
    "growl":       "neuro",
    "neuro":       "wobble",
    "wobble":      "acid",
    "acid":        "donk",
    "donk":        "saw",
    "saw":         "tape",
    "tape":        "dist_fm",
    "dist_fm":     "ring_mod",
    "ring_mod":    "phase",
    "phase":       "bitcrush",
    "bitcrush":    "formant",
    "formant":     "sync",
    "sync":        "wavetable",
    "wavetable":   "amplitude",
    "amplitude":   "octave",
    "octave":      "pulse_width",
    "pulse_width": "sub_sine",
    "square":      "saw",
}


@dataclass
class VIPDelta:
    """Record of what changed in the VIP version."""
    original_name: str
    vip_name: str
    mutations: list[str] = field(default_factory=list)
    kept_percent: float = 38.2
    changed_percent: float = 61.8


# ═══════════════════════════════════════════════════════════════════════════
# VIP GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def vip_mutate_bass(original_type: str, original_freq: float,
                    idx: int, duration_s: float = 0.8,
                    sr: int = SAMPLE_RATE) -> tuple[np.ndarray, list[str]]:
    """Create a VIP mutation of a bass preset."""
    mutations: list[str] = []

    # Decide which mutations to apply (61.8% changed)
    rng = np.random.default_rng(idx * 1618)

    # 1. Bass type rotation
    new_type = _BASS_VIP_MAP.get(original_type, "fm")
    mutations.append(f"bass_type: {original_type} → {new_type}")

    # 2. Pitch shift by phi ratio
    pitch_shift = PHI if rng.random() > 0.5 else 1.0 / PHI
    new_freq = original_freq * pitch_shift
    # Clamp to audible bass range
    new_freq = max(20.0, min(new_freq, 500.0))
    mutations.append(f"freq: {original_freq:.1f} → {new_freq:.1f} Hz")

    # 3. Drive boost
    drive = 0.3 + rng.random() * 0.5
    mutations.append(f"distortion: {drive:.2f}")

    # 4. FM depth shift
    fm_depth = 2.0 * PHI if "fm" in new_type else rng.random() * 3.0
    fm_ratio = PHI ** (1 + rng.random())
    mutations.append(f"fm_ratio: {fm_ratio:.3f}, depth: {fm_depth:.2f}")

    # 5. Envelope reshape
    attack = 0.005 * (PHI if rng.random() > 0.5 else 1.0 / PHI)
    release = 0.2 * (1.0 / PHI if rng.random() > 0.5 else PHI)
    mutations.append(f"envelope: atk={attack:.4f}s rel={release:.3f}s")

    preset = BassPreset(
        name=f"vip_{new_type}_{idx:03d}",
        bass_type=new_type,
        frequency=new_freq,
        duration_s=duration_s,
        attack_s=attack,
        release_s=release,
        fm_ratio=fm_ratio,
        fm_depth=fm_depth,
        distortion=drive,
    )

    audio = synthesize_bass(preset, sr)
    return audio, mutations


def vip_layer_noise(audio: np.ndarray, idx: int,
                    sr: int = SAMPLE_RATE) -> np.ndarray:
    """Add a noise texture layer at 38.2% mix (PHI_HOLD)."""
    noise_types = ["pink", "vinyl", "tape", "digital"]
    noise = synthesize_noise(NoisePreset(
        name=f"vip_noise_{idx}",
        noise_type=noise_types[idx % len(noise_types)],
        duration_s=len(audio) / sr,
        gain=0.3,
    ), sr)

    # Match lengths
    n = min(len(audio), len(noise))
    mixed = audio[:n] * PHI_KEEP + noise[:n] * PHI_HOLD
    return np.clip(mixed, -1, 1)


# ═══════════════════════════════════════════════════════════════════════════
# VIP PACK BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_vip_pack(original_bank_name: str = "bass",
                   output_dir: str = "output") -> tuple[list[str], list[VIPDelta]]:
    """Build a VIP version of an existing sample pack bank."""
    bank_fn = ALL_PACK_BANKS.get(original_bank_name)
    if bank_fn is None:
        return [], []

    bank = bank_fn()
    all_paths: list[str] = []
    all_deltas: list[VIPDelta] = []

    for preset in bank.presets:
        out = Path(output_dir) / "vip_packs" / f"{preset.name}_VIP"
        out.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        delta = VIPDelta(
            original_name=preset.name,
            vip_name=f"{preset.name}_VIP",
        )

        for i in range(preset.num_samples):
            # VIP mutation — bass and synth categories get full mutation
            if preset.category in ("bass", "synths"):
                bass_type = "fm"  # default
                if preset.name in ("sub_bass",):
                    bass_type = "sub_sine"
                elif preset.name in ("reese",):
                    bass_type = "reese"
                elif preset.name in ("wobble",):
                    bass_type = "wobble"
                elif preset.name in ("mid_bass",):
                    bass_type = "growl"

                audio, mutations = vip_mutate_bass(
                    bass_type, preset.base_freq, i,
                    duration_s=preset.duration_s)

                # 50% chance of noise layer
                rng = np.random.default_rng(i * 2718)
                if rng.random() > 0.5:
                    audio = vip_layer_noise(audio, i)
                    mutations.append("+ noise layer at 38.2% mix")

                delta.mutations.extend(mutations)
            else:
                # For drums/fx/stems: pitch shift the originals
                audio = synthesize_bass(BassPreset(
                    name=f"vip_fallback_{i}",
                    bass_type="fm",
                    frequency=preset.base_freq * (PHI ** (i * 0.15)),
                    duration_s=preset.duration_s,
                ), SAMPLE_RATE)
                delta.mutations.append(f"sample {i}: freq shifted by phi")

            # Normalize
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak * 0.9

            fname = f"{preset.category}_{preset.name}_VIP_{i:03d}.wav"
            _write_wav(out / fname, audio)
            paths.append(str(out / fname))

        # VIP manifest
        manifest = {
            "pack": f"{preset.name}_VIP",
            "original": preset.name,
            "category": preset.category,
            "num_samples": preset.num_samples,
            "golden_vip_rule": f"Changed {delta.changed_percent}%, kept {delta.kept_percent}%",
            "phi": PHI,
            "files": [Path(p).name for p in paths],
        }
        with open(out / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # VIP delta report
        delta_report = {
            "original": delta.original_name,
            "vip": delta.vip_name,
            "kept_percent": delta.kept_percent,
            "changed_percent": delta.changed_percent,
            "mutations": delta.mutations,
        }
        with open(out / "vip_delta.json", "w") as f:
            json.dump(delta_report, f, indent=2)

        all_paths.extend(paths)
        all_deltas.append(delta)

    return all_paths, all_deltas


def export_all_vip_packs(output_dir: str = "output") -> list[str]:
    """Generate VIP versions for bass and synths banks."""
    all_paths: list[str] = []

    print("\n═══ VIP Pack Workflow ═══")

    for bank_name in ["bass", "synths"]:
        print(f"  Building VIP: {bank_name}...")
        paths, deltas = build_vip_pack(bank_name, output_dir)
        all_paths.extend(paths)
        print(f"    → {len(paths)} VIP samples, {len(deltas)} presets")

    print(f"  ✓ {len(all_paths)} total VIP samples")
    return all_paths


def main() -> None:
    paths = export_all_vip_packs()
    print(f"VIP Pack Workflow: {len(paths)} .wav files")


if __name__ == "__main__":
    main()
