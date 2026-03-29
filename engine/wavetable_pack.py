"""
DUBFORGE Engine — Wavetable Pack Generator

Create wavetable PACKS by sweeping synthesis parameters at phi-stepped
intervals across the growl_resampler and phi_core generators.

Pack types:
    fm_ratio_sweep      — 20 wavetables varying FM mod:carrier ratio
    harmonic_sweep      — 20 wavetables varying partial count
    morph_pack          — 20 wavetables varying morph position
    growl_vowel_pack    — 5 vowels × 4 drive levels = 20 tables
    combined_sweep      — FM × harmonic × drive combined sweep

Each wavetable is a Serum-compatible .wav (2048 samples × N frames).
"""

import json
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.growl_resampler import (
    bit_reduce,
    comb_filter,
    formant_filter,
    frequency_shift,
    generate_fm_source,
    generate_saw_source,
    growl_resample_pipeline,
    waveshape_distortion,
)
from engine.phi_core import (
    DEFAULT_FRAMES,
    SAMPLE_RATE,
    WAVETABLE_SIZE,
    generate_frame,
    morph_frames,
    phi_amplitude_curve,
    phi_harmonic_series,
    write_wav as write_serum_wav,
)
from engine.turboquant import (
    CompressedWavetable,
    TurboQuantConfig,
    compress_wavetable,
)


# ═══════════════════════════════════════════════════════════════════════════
# FM RATIO SWEEP — vary mod:carrier from 1.0 to PHI^4
# ═══════════════════════════════════════════════════════════════════════════

def generate_fm_ratio_sweep(n_tables: int = 20,
                            n_frames: int = 64) -> list[tuple[str, list[np.ndarray]]]:
    """Generate wavetables sweeping FM ratio from 1.0 to PHI^4."""
    tables = []
    for i in range(n_tables):
        ratio = 1.0 + (PHI ** 4 - 1.0) * (i / (n_tables - 1))
        depth = 2.0 + i * 0.5
        source = generate_fm_source(
            size=WAVETABLE_SIZE, fm_ratio=ratio, fm_depth=depth)
        frames = growl_resample_pipeline(source, n_output_frames=n_frames)
        name = f"DUBFORGE_FM_R{ratio:.2f}"
        tables.append((name, frames))
    return tables


# ═══════════════════════════════════════════════════════════════════════════
# HARMONIC SWEEP — vary partial count from 3 to 34 (Fibonacci steps)
# ═══════════════════════════════════════════════════════════════════════════

_FIB_PARTIAL_COUNTS = [3, 5, 8, 13, 21, 34]


def generate_harmonic_sweep(n_tables: int = 20,
                            n_frames: int = 64) -> list[tuple[str, list[np.ndarray]]]:
    """Generate wavetables sweeping harmonic count at phi-spaced intervals."""
    tables = []
    fundamental = 55.0  # A1

    for i in range(n_tables):
        progress = i / (n_tables - 1)
        # Interpolate partial count across Fibonacci values
        n_partials = int(3 + progress * 31)  # 3 to 34
        partials = phi_harmonic_series(fundamental, n_partials)
        amps = phi_amplitude_curve(n_partials, decay=1.0 - progress * 0.3)

        # Build frames with progressive drive
        frames = []
        for f_idx in range(n_frames):
            f_progress = f_idx / (n_frames - 1)
            # Shift amplitudes over frames for movement
            shifted_amps = [a * (1.0 + f_progress * 0.5 * (j % 2))
                            for j, a in enumerate(amps)]
            frame = generate_frame(partials, shifted_amps, WAVETABLE_SIZE)
            # Apply progressive waveshaping
            drive = 0.3 + f_progress * 2.0
            frame = np.tanh(frame * drive)
            peak = np.max(np.abs(frame))
            if peak > 0:
                frame = frame / peak * 0.95
            frames.append(frame)

        name = f"DUBFORGE_HARM_{n_partials:02d}"
        tables.append((name, frames))
    return tables


# ═══════════════════════════════════════════════════════════════════════════
# MORPH PACK — morph between source waveforms
# ═══════════════════════════════════════════════════════════════════════════

def generate_morph_pack(n_tables: int = 20,
                        n_frames: int = 64) -> list[tuple[str, list[np.ndarray]]]:
    """Generate wavetables morphing between saw→FM→growl source shapes."""
    # Create the 3 source frames
    saw = generate_saw_source(WAVETABLE_SIZE)
    fm_lo = generate_fm_source(WAVETABLE_SIZE, fm_ratio=PHI, fm_depth=2.0)
    fm_hi = generate_fm_source(WAVETABLE_SIZE, fm_ratio=PHI ** 2, fm_depth=5.0)

    tables = []
    for i in range(n_tables):
        progress = i / (n_tables - 1)

        # Blend source: 0→0.5 = saw→fm_lo, 0.5→1.0 = fm_lo→fm_hi
        if progress < 0.5:
            t = progress * 2.0
            source = saw * (1.0 - t) + fm_lo * t
        else:
            t = (progress - 0.5) * 2.0
            source = fm_lo * (1.0 - t) + fm_hi * t

        # Run through growl pipeline
        frames = growl_resample_pipeline(source, n_output_frames=n_frames)
        name = f"DUBFORGE_MORPH_{i:02d}"
        tables.append((name, frames))
    return tables


# ═══════════════════════════════════════════════════════════════════════════
# GROWL VOWEL PACK — 5 vowels × 4 drive levels
# ═══════════════════════════════════════════════════════════════════════════

_VOWELS = ["A", "E", "I", "O", "U"]
_DRIVE_LEVELS = [0.3, 0.618, 1.0, 2.0]


def generate_growl_vowel_pack(
    n_frames: int = 64,
) -> list[tuple[str, list[np.ndarray]]]:
    """Generate wavetables with formant filtering at different vowels and drives."""
    tables = []
    source = generate_fm_source(WAVETABLE_SIZE, fm_ratio=PHI, fm_depth=3.0)

    for vowel in _VOWELS:
        for drive in _DRIVE_LEVELS:
            frames = []
            for f_idx in range(n_frames):
                progress = f_idx / (n_frames - 1)
                frame = source.copy()
                # Apply formant
                frame = formant_filter(frame, vowel=vowel,
                                       depth=0.3 + progress * 0.5)
                # Apply drive
                frame = waveshape_distortion(frame, drive=drive,
                                             mix=0.5 + progress * 0.4)
                # Comb for metallic character
                frame = comb_filter(frame, delay_ms=2.618,
                                    feedback=progress * 0.5)
                peak = np.max(np.abs(frame))
                if peak > 0:
                    frame = frame / peak * 0.95
                frames.append(frame)

            drive_label = f"{drive:.1f}".replace(".", "p")
            name = f"DUBFORGE_VOWEL_{vowel}_{drive_label}"
            tables.append((name, frames))
    return tables


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_wavetable_pack(pack_name: str,
                          tables: list[tuple[str, list[np.ndarray]]],
                          output_dir: str = "output") -> list[str]:
    """Write a pack of wavetables to disk."""
    out = Path(output_dir) / "wavetable_packs" / pack_name
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for name, frames in tables:
        path = out / f"{name}.wav"
        write_serum_wav(str(path), frames)
        paths.append(str(path))
        # TQ sidecar
        float_frames = [f.tolist() for f in frames]
        cw = compress_wavetable(float_frames, TurboQuantConfig(), name=name)
        tq_path = out / f"{name}.tq"
        import pickle
        tq_path.write_bytes(pickle.dumps(cw))

    # Manifest
    manifest = {
        "pack": pack_name,
        "tables": len(tables),
        "frames_per_table": len(tables[0][1]) if tables else 0,
        "frame_size": WAVETABLE_SIZE,
        "sample_rate": SAMPLE_RATE,
        "phi": PHI,
        "files": [Path(p).name for p in paths],
    }
    with open(out / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return paths


def export_all_wavetable_packs(output_dir: str = "output") -> list[str]:
    """Generate and export all wavetable packs."""
    all_paths: list[str] = []

    print("\n═══ Wavetable Pack Generator ═══")

    print("  [1/4] FM Ratio Sweep (20 tables)...")
    fm_tables = generate_fm_ratio_sweep()
    all_paths.extend(export_wavetable_pack("FM_Ratio_Sweep", fm_tables, output_dir))

    print("  [2/4] Harmonic Sweep (20 tables)...")
    harm_tables = generate_harmonic_sweep()
    all_paths.extend(export_wavetable_pack("Harmonic_Sweep", harm_tables, output_dir))

    print("  [3/4] Morph Pack (20 tables)...")
    morph_tables = generate_morph_pack()
    all_paths.extend(export_wavetable_pack("Morph_Pack", morph_tables, output_dir))

    print("  [4/4] Growl Vowel Pack (20 tables)...")
    vowel_tables = generate_growl_vowel_pack()
    all_paths.extend(export_wavetable_pack("Growl_Vowel", vowel_tables, output_dir))

    print(f"  ✓ {len(all_paths)} wavetables across 4 packs")
    return all_paths


def main() -> None:
    paths = export_all_wavetable_packs()
    print(f"Wavetable Pack Generator: {len(paths)} .wav files")


if __name__ == "__main__":
    main()
