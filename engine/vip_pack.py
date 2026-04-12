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
from engine.accel import fft, ifft
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


# ═══════════════════════════════════════════════════════════════════════════
# v7.0.0 — VIP Generation Mode (Fractals → Antifractals)
# ═══════════════════════════════════════════════════════════════════════════
# Full VIP version creation workflow:
#   1. Take existing DUBFORGE output (stems, samples, wavetables)
#   2. Apply the Golden VIP Rule: change 61.8%, keep 38.2%
#   3. Mutate bass textures via VIP rotation map
#   4. Rearrange arrangement energy curve (inverse RCO)
#   5. Shift harmonic content (new key signature or modal interchange)
#   6. Apply fractal → antifractal processing (invert timbral qualities)
#   7. A/B comparison between original and VIP

@dataclass
class VIPTrackConfig:
    """Configuration for full VIP track generation."""
    original_name: str
    vip_name: str = ""
    # Mutation controls
    key_shift_semitones: int = 0       # shift root key (0=same, 5=fourth, 7=fifth)
    bpm_shift: float = 0.0            # BPM offset (e.g. +5 or -3)
    energy_invert: bool = False        # invert energy curve (drops↔builds)
    bass_rotation: bool = True         # rotate bass types via VIP map
    wavetable_morph_offset: float = 0.0  # offset morph position (0-1)
    fx_chain_swap: bool = True         # swap FX chain parameters
    arrangement_shuffle: bool = False  # shuffle section order
    # Fractal → Antifractal
    antifractal_mode: bool = True      # apply antifractal processing
    antifractal_depth: float = PHI_KEEP  # depth of antifractal transform (0.618)


@dataclass
class VIPTrackResult:
    """Result of a full VIP track generation."""
    config: VIPTrackConfig
    stem_mutations: dict[str, list[str]]  # stem_name -> list of mutations
    total_changed_percent: float
    total_kept_percent: float
    wav_paths: list[str]
    delta_report: dict


def _antifractal_process(signal: np.ndarray, depth: float = 0.618) -> np.ndarray:
    """Antifractal transform — invert timbral qualities.

    Swaps spectral character: bright↔dark, transient↔sustained, clean↔distorted.
    Based on Subtronics' Fractals→Antifractals remix technique.
    """
    n = len(signal)
    if n < 64:
        return signal

    # Mirror spectral content around midpoint frequency
    spectrum = fft(signal)
    mid_bin = len(spectrum) // 2
    reversed_spec = np.zeros_like(spectrum)
    for i in range(len(spectrum)):
        mirror_i = len(spectrum) - 1 - i
        if 0 <= mirror_i < len(spectrum):
            reversed_spec[i] = spectrum[mirror_i]

    # Blend original and mirrored based on depth
    blended = spectrum * (1 - depth) + reversed_spec * depth
    result = ifft(blended, n=n)

    # Normalize
    peak = np.max(np.abs(result))
    if peak > 0:
        result = result / peak
    return np.real(result)


def _energy_curve_invert(stems: dict[str, np.ndarray],
                         sample_rate: int = SAMPLE_RATE) -> dict[str, np.ndarray]:
    """Invert energy curve — swap dynamics (loud↔quiet sections)."""
    inverted = {}
    for name, signal in stems.items():
        n = len(signal)
        # Compute amplitude envelope
        chunk = max(1, int(sample_rate * 0.1))  # 100ms chunks
        num_chunks = n // chunk
        if num_chunks < 2:
            inverted[name] = signal
            continue
        # Build envelope
        env = np.ones(n)
        for i in range(num_chunks):
            start = i * chunk
            end = min(start + chunk, n)
            rms = float(np.sqrt(np.mean(signal[start:end] ** 2))) + 1e-12
            env[start:end] = rms
        # Invert: loud sections become quiet, quiet become loud
        max_env = np.max(env) + 1e-12
        inv_env = (max_env - env) / max_env + 0.1  # keep minimum at 10%
        inverted[name] = signal * inv_env / np.max(np.abs(inv_env))
    return inverted


def _pitch_shift_stem(signal: np.ndarray, semitones: int,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Simple pitch shift via resampling."""
    if semitones == 0:
        return signal
    ratio = 2.0 ** (semitones / 12.0)
    n_out = int(len(signal) / ratio)
    return np.interp(
        np.linspace(0, len(signal) - 1, n_out),
        np.arange(len(signal)),
        signal,
    )


def generate_vip_track(
    stems: dict[str, np.ndarray],
    config: VIPTrackConfig,
    output_dir: str = "output",
    sample_rate: int = SAMPLE_RATE,
) -> VIPTrackResult:
    """Generate a complete VIP version of a track from its stems.

    Implements the Subtronics Fractals→Antifractals workflow:
    1. Keep 38.2% of elements identical (Golden VIP Rule)
    2. Mutate 61.8% through bass rotation, key shift, energy inversion
    3. Apply antifractal processing for timbral mirroring
    4. Export mutated stems

    Args:
        stems: Dict mapping stem_name -> numpy signal array
        config: VIP generation configuration
        output_dir: Base output directory
        sample_rate: Audio sample rate

    Returns:
        VIPTrackResult with mutated stems and delta report
    """
    if not config.vip_name:
        config.vip_name = f"{config.original_name}_VIP"

    vip_dir = Path(output_dir) / "vip_tracks" / config.vip_name
    vip_dir.mkdir(parents=True, exist_ok=True)

    stem_mutations: dict[str, list[str]] = {}
    wav_paths: list[str] = []
    rng = np.random.default_rng(1618)

    # Decide which stems to mutate (61.8%) and keep (38.2%)
    stem_names = sorted(stems.keys())
    n_mutate = max(1, int(len(stem_names) * PHI_KEEP))
    mutate_set = set(rng.choice(stem_names, size=n_mutate, replace=False))
    keep_set = set(stem_names) - mutate_set

    # Process each stem
    vip_stems: dict[str, np.ndarray] = {}
    for name in stem_names:
        signal = stems[name].copy()
        mutations: list[str] = []

        if name in keep_set:
            mutations.append("KEPT (38.2% identity)")
            vip_stems[name] = signal
        else:
            # 1. Key shift
            if config.key_shift_semitones != 0:
                signal = _pitch_shift_stem(signal, config.key_shift_semitones,
                                           sample_rate)
                mutations.append(f"key_shift: {config.key_shift_semitones:+d} semitones")

            # 2. Antifractal processing
            if config.antifractal_mode:
                signal = _antifractal_process(signal, config.antifractal_depth)
                mutations.append(f"antifractal: depth={config.antifractal_depth:.3f}")

            # 3. Bass rotation (for bass stems)
            bass_stems = {"sub_bass", "mid_bass", "neuro", "wobble", "riddim"}
            if config.bass_rotation and name in bass_stems:
                # Apply VIP mutation via bass type rotation
                audio, bass_mutations = vip_mutate_bass(
                    "fm", 55.0, int(rng.integers(0, 1000)),
                    duration_s=len(signal) / sample_rate,
                    sr=sample_rate)
                # Mix: 61.8% mutated + 38.2% original
                n = min(len(signal), len(audio))
                signal = signal[:n] * PHI_HOLD + audio[:n] * PHI_KEEP
                mutations.extend([f"bass_rotate: {m}" for m in bass_mutations[:2]])

            # 4. FX chain swap (subtle character change)
            if config.fx_chain_swap:
                # Apply random waveshaping
                drive = rng.uniform(0.1, 0.5)
                signal = np.tanh(signal * (1 + drive * 3))
                mutations.append(f"fx_swap: drive={drive:.2f}")

            vip_stems[name] = signal

        stem_mutations[name] = mutations

    # 5. Energy inversion (applied to full stem set)
    if config.energy_invert:
        vip_stems = _energy_curve_invert(vip_stems, sample_rate)
        for name in mutate_set:
            stem_mutations[name].append("energy_curve: inverted")

    # Export all VIP stems
    for name, signal in vip_stems.items():
        # Normalize
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal / peak * 0.9

        wav_path = vip_dir / f"{config.vip_name}_{name}.wav"
        _write_wav(wav_path, signal)
        wav_paths.append(str(wav_path))

    # Calculate actual mutation percentages
    total_mutated = len(mutate_set)
    total_kept = len(keep_set)
    changed_pct = round(total_mutated / max(len(stem_names), 1) * 100, 1)
    kept_pct = round(total_kept / max(len(stem_names), 1) * 100, 1)

    # Delta report
    delta_report = {
        "original": config.original_name,
        "vip": config.vip_name,
        "golden_vip_rule": f"Changed {changed_pct}%, kept {kept_pct}%",
        "stems_mutated": list(mutate_set),
        "stems_kept": list(keep_set),
        "mutations": stem_mutations,
        "config": {
            "key_shift": config.key_shift_semitones,
            "bpm_shift": config.bpm_shift,
            "energy_invert": config.energy_invert,
            "antifractal_mode": config.antifractal_mode,
            "antifractal_depth": config.antifractal_depth,
        },
    }
    with open(vip_dir / "vip_delta.json", "w") as f:
        json.dump(delta_report, f, indent=2)

    return VIPTrackResult(
        config=config,
        stem_mutations=stem_mutations,
        total_changed_percent=changed_pct,
        total_kept_percent=kept_pct,
        wav_paths=wav_paths,
        delta_report=delta_report,
    )


def print_vip_report(result: VIPTrackResult) -> None:
    """Pretty-print a VIP generation report."""
    print(f"\n═══ VIP Generation: {result.config.vip_name} ═══")
    print(f"  Golden Rule: {result.total_changed_percent}% changed, "
          f"{result.total_kept_percent}% kept")
    for stem, mutations in result.stem_mutations.items():
        prefix = "  ✓" if "KEPT" in mutations[0] else "  ⚡"
        print(f"{prefix} {stem}: {', '.join(mutations)}")
    print(f"  → {len(result.wav_paths)} VIP stems exported")


def main() -> None:
    paths = export_all_vip_packs()
    print(f"VIP Pack Workflow: {len(paths)} .wav files")


if __name__ == "__main__":
    main()
