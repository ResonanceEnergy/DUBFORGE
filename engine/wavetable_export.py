"""
DUBFORGE Engine — Serum 2 Wavetable Exporter

Export DUBFORGE-generated wavetables as Serum 2-compatible .wav files
with the 'clm ' marker chunk that Serum uses to identify wavetable frame count.

Workflow order:
  Phase 1 Stage 4G (SYNTH FACTORY) → after wavetable generation, before preset build.
  Exports wavetables into Serum 2's user wavetable directory for drag-and-drop use.

Serum wavetable format:
  - Standard WAV (16-bit PCM or 32-bit float)
  - 2048 samples per frame
  - 'clm ' chunk indicates frame count: "<!>2048 <frame_count>"
  - Frames concatenated sequentially in the data chunk
  - Serum scans WT position (0-1) across frames

Banks: 5 export types × 4 presets = 20 presets
"""

from __future__ import annotations
from typing import Any, Callable

import json
import struct
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

_log = get_logger("dubforge.wavetable_export")

# Serum constants
SERUM_FRAME_SIZE = 2048
SERUM_CLM_MARKER = b"clm "
SERUM_WT_DIR = Path("/Library/Audio/Presets/Xfer Records/Serum 2 Presets/Tables/User")
DUBFORGE_WT_DIR = SERUM_WT_DIR / "DUBFORGE"
LOCAL_WT_DIR = Path("output/wavetables/serum2")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WavetableExportPreset:
    """Configuration for a wavetable export."""
    name: str
    export_type: str  # harmonic_sweep | fm_morph | fractal | formant_cycle | resample_chain
    num_frames: int = 64
    frame_size: int = SERUM_FRAME_SIZE
    bit_depth: int = 16  # 16 or 32
    install_to_serum: bool = False  # copy to Serum's user dir
    base_frequency: float = 55.0
    harmonics: int = 16
    morph_amount: float = 1.0


@dataclass
class WavetableExportBank:
    name: str
    presets: list[WavetableExportPreset] = field(default_factory=list)


@dataclass
class WavetableExportResult:
    name: str
    path: str
    num_frames: int
    frame_size: int
    installed: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# FRAME GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _generate_harmonic_sweep_frames(preset: WavetableExportPreset) -> list[np.ndarray]:
    """Sweep harmonic count from 1 to N across frames."""
    frames = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)
    for i in range(preset.num_frames):
        progress = i / max(preset.num_frames - 1, 1)
        max_harmonic = max(1, int(1 + progress * preset.harmonics))
        sig = np.zeros(preset.frame_size)
        for k in range(1, max_harmonic + 1):
            amplitude = 1.0 / (k ** (1 + progress * 0.5))
            sig += amplitude * np.sin(k * t)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        frames.append(sig)
    return frames


def _generate_fm_morph_frames(preset: WavetableExportPreset) -> list[np.ndarray]:
    """FM synthesis with morphing mod depth across frames."""
    frames = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)
    for i in range(preset.num_frames):
        progress = i / max(preset.num_frames - 1, 1)
        mod_depth = progress * preset.morph_amount * 8.0
        fm_ratio = 1.0 + progress * (PHI - 1)
        modulator = np.sin(fm_ratio * t) * mod_depth
        sig = np.sin(t + modulator)
        # Add sub harmonics
        sig += 0.3 * np.sin(0.5 * t + modulator * 0.5)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        frames.append(sig)
    return frames


def _generate_fractal_frames(preset: WavetableExportPreset) -> list[np.ndarray]:
    """Self-similar fractal waveforms using Fibonacci harmonic series."""
    frames = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    for i in range(preset.num_frames):
        progress = i / max(preset.num_frames - 1, 1)
        sig = np.zeros(preset.frame_size)
        num_partials = max(2, int(3 + progress * len(fib)))
        for k_idx in range(min(num_partials, len(fib))):
            k = fib[k_idx]
            amp = 1.0 / (k ** PHI) * (1 - progress * 0.3)
            phase = k_idx * PHI * progress
            sig += amp * np.sin(k * t + phase)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        frames.append(sig)
    return frames


def _generate_formant_cycle_frames(preset: WavetableExportPreset) -> list[np.ndarray]:
    """Cycle through vowel formants across frames."""
    frames = []
    vowels = [
        [(730, 120), (1090, 150), (2440, 200)],  # A
        [(660, 110), (1720, 170), (2410, 200)],   # E
        [(390, 80), (1990, 180), (2550, 210)],     # I
        [(570, 100), (840, 130), (2410, 200)],     # O
        [(440, 90), (1020, 140), (2240, 190)],     # U
    ]
    freqs_hz = np.fft.rfftfreq(preset.frame_size, d=1.0 / 44100)
    for i in range(preset.num_frames):
        progress = i / max(preset.num_frames - 1, 1)
        # Interpolate between vowels
        vowel_pos = progress * (len(vowels) - 1)
        v_idx = int(vowel_pos)
        v_frac = vowel_pos - v_idx
        v_a = vowels[min(v_idx, len(vowels) - 1)]
        v_b = vowels[min(v_idx + 1, len(vowels) - 1)]
        # Build source (saw)
        t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)
        sig = np.zeros(preset.frame_size)
        for k in range(1, 20):
            sig += ((-1) ** (k + 1)) * np.sin(k * t) / k
        # Apply blended formant
        spectrum = np.fft.rfft(sig)
        response = np.ones(len(spectrum))
        for j in range(3):
            ca, ba = v_a[j] if j < len(v_a) else (1000, 100)
            cb, bb = v_b[j] if j < len(v_b) else (1000, 100)
            center = ca * (1 - v_frac) + cb * v_frac
            bw = ba * (1 - v_frac) + bb * v_frac
            response += 3.0 * np.exp(-0.5 * ((freqs_hz - center) / max(bw, 1)) ** 2)
        spectrum *= response
        sig = np.fft.irfft(spectrum, n=preset.frame_size)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        frames.append(sig)
    return frames


def _generate_resample_chain_frames(preset: WavetableExportPreset) -> list[np.ndarray]:
    """Generate frames by progressively distorting a source across the table."""
    frames = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)
    base = np.sin(t) + 0.5 * np.sin(2 * t) + 0.25 * np.sin(3 * t)
    base /= np.max(np.abs(base))
    for i in range(preset.num_frames):
        progress = i / max(preset.num_frames - 1, 1)
        sig = base.copy()
        # Progressive distortion
        drive = 1.0 + progress * 8.0 * preset.morph_amount
        sig = np.tanh(sig * drive)
        # Bit reduction at higher positions
        if progress > 0.5:
            bits = max(4, int(16 - (progress - 0.5) * 20))
            levels = 2 ** bits
            sig = np.round(sig * levels) / levels
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig /= peak
        frames.append(sig)
    return frames


FRAME_GENERATORS: dict[str, Callable[..., Any]] = {
    "harmonic_sweep": _generate_harmonic_sweep_frames,
    "fm_morph": _generate_fm_morph_frames,
    "fractal": _generate_fractal_frames,
    "formant_cycle": _generate_formant_cycle_frames,
    "resample_chain": _generate_resample_chain_frames,
}


# ═══════════════════════════════════════════════════════════════════════════
# SERUM WAV WRITER (with clm chunk)
# ═══════════════════════════════════════════════════════════════════════════

def write_serum_wavetable(frames: list[np.ndarray], path: str | Path,
                          bit_depth: int = 16) -> str:
    """
    Write a Serum-compatible wavetable .wav file with 'clm ' marker chunk.

    The clm chunk tells Serum how many frames are in the wavetable.
    Format: standard WAV with an extra RIFF chunk named 'clm '.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    num_frames = len(frames)
    frame_size = len(frames[0]) if frames else SERUM_FRAME_SIZE

    # Concatenate all frames
    audio = np.concatenate(frames)

    if bit_depth == 32:
        # 32-bit float WAV
        sample_width = 4
        audio_bytes = (audio.astype(np.float32)).tobytes()
    else:
        # 16-bit PCM
        sample_width = 2
        audio_int = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        audio_bytes = audio_int.tobytes()

    # Build the 'clm ' chunk data
    # Serum expects: "<!>{frame_size} {num_frames}\0" as ASCII
    clm_data = f"<!>{frame_size} {num_frames}\x00".encode("ascii")

    # Write WAV manually to include the clm chunk
    n_channels = 1
    sample_rate = 44100
    data_size = len(audio_bytes)
    fmt_chunk_size = 16
    clm_chunk_size = len(clm_data)

    # RIFF header size = 4 (WAVE) + (8 + fmt_chunk) + (8 + data_chunk) + (8 + clm_chunk)
    riff_size = 4 + (8 + fmt_chunk_size) + (8 + data_size) + (8 + clm_chunk_size)

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", riff_size))
        f.write(b"WAVE")

        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", fmt_chunk_size))
        audio_format = 3 if bit_depth == 32 else 1  # 3=float, 1=PCM
        f.write(struct.pack("<HHIIHH",
                            audio_format, n_channels, sample_rate,
                            sample_rate * n_channels * sample_width,
                            n_channels * sample_width, bit_depth))

        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(audio_bytes)

        # clm chunk (Serum wavetable marker)
        f.write(SERUM_CLM_MARKER)
        f.write(struct.pack("<I", clm_chunk_size))
        f.write(clm_data)

    _log.info("Wrote Serum wavetable: %s (%d frames × %d samples)", path, num_frames, frame_size)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def export_wavetable(preset: WavetableExportPreset,
                     custom_frames: list[np.ndarray] | None = None) -> WavetableExportResult:
    """Generate and export a single wavetable."""
    if custom_frames is not None:
        frames = custom_frames
    else:
        gen_fn = FRAME_GENERATORS.get(preset.export_type)
        if gen_fn is None:
            raise ValueError(f"Unknown export type: {preset.export_type}")
        frames = gen_fn(preset)

    # Ensure all frames are correct size
    sized_frames = []
    for frame in frames:
        if len(frame) != preset.frame_size:
            resized = np.zeros(preset.frame_size)
            min_len = min(len(frame), preset.frame_size)
            resized[:min_len] = frame[:min_len]
            sized_frames.append(resized)
        else:
            sized_frames.append(frame)

    # Write to local output
    local_path = LOCAL_WT_DIR / f"{preset.name}.wav"
    write_serum_wavetable(sized_frames, local_path, preset.bit_depth)

    # Optionally install to Serum directory
    installed = False
    if preset.install_to_serum:
        try:
            DUBFORGE_WT_DIR.mkdir(parents=True, exist_ok=True)
            serum_path = DUBFORGE_WT_DIR / f"{preset.name}.wav"
            write_serum_wavetable(sized_frames, serum_path, preset.bit_depth)
            installed = True
            _log.info("Installed to Serum: %s", serum_path)
        except OSError as e:
            _log.warning("Could not install to Serum dir: %s", e)

    return WavetableExportResult(
        name=preset.name,
        path=str(local_path),
        num_frames=len(sized_frames),
        frame_size=preset.frame_size,
        installed=installed,
    )


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def harmonic_sweep_bank() -> WavetableExportBank:
    return WavetableExportBank("harmonic_sweep", [
        WavetableExportPreset("DF_HARM_BRIGHT", "harmonic_sweep", harmonics=32),
        WavetableExportPreset("DF_HARM_DARK", "harmonic_sweep", harmonics=8),
        WavetableExportPreset("DF_HARM_WIDE", "harmonic_sweep", num_frames=128, harmonics=24),
        WavetableExportPreset("DF_HARM_TIGHT", "harmonic_sweep", num_frames=16, harmonics=16),
    ])


def fm_morph_bank() -> WavetableExportBank:
    return WavetableExportBank("fm_morph", [
        WavetableExportPreset("DF_FM_GENTLE", "fm_morph", morph_amount=0.5),
        WavetableExportPreset("DF_FM_AGGRESSIVE", "fm_morph", morph_amount=2.0),
        WavetableExportPreset("DF_FM_PHI", "fm_morph", morph_amount=PHI),
        WavetableExportPreset("DF_FM_DEEP", "fm_morph", num_frames=128, morph_amount=1.5),
    ])


def fractal_bank() -> WavetableExportBank:
    return WavetableExportBank("fractal", [
        WavetableExportPreset("DF_FRAC_GOLDEN", "fractal"),
        WavetableExportPreset("DF_FRAC_DENSE", "fractal", num_frames=128),
        WavetableExportPreset("DF_FRAC_SPARSE", "fractal", num_frames=16),
        WavetableExportPreset("DF_FRAC_HIRES", "fractal", bit_depth=32),
    ])


def formant_bank() -> WavetableExportBank:
    return WavetableExportBank("formant_cycle", [
        WavetableExportPreset("DF_VOWEL_CYCLE", "formant_cycle"),
        WavetableExportPreset("DF_VOWEL_WIDE", "formant_cycle", num_frames=128),
        WavetableExportPreset("DF_VOWEL_TIGHT", "formant_cycle", num_frames=16),
        WavetableExportPreset("DF_VOWEL_HIRES", "formant_cycle", bit_depth=32),
    ])


def resample_chain_bank_export() -> WavetableExportBank:
    return WavetableExportBank("resample_chain", [
        WavetableExportPreset("DF_RESAMP_MILD", "resample_chain", morph_amount=0.5),
        WavetableExportPreset("DF_RESAMP_HEAVY", "resample_chain", morph_amount=2.0),
        WavetableExportPreset("DF_RESAMP_BITCRUSH", "resample_chain", morph_amount=1.5),
        WavetableExportPreset("DF_RESAMP_LONG", "resample_chain", num_frames=128),
    ])


ALL_WT_EXPORT_BANKS = [
    harmonic_sweep_bank, fm_morph_bank, fractal_bank, formant_bank,
    resample_chain_bank_export,
]


def export_all_banks(install: bool = False) -> list[WavetableExportResult]:
    """Export all wavetable banks."""
    results = []
    for bank_fn in ALL_WT_EXPORT_BANKS:
        bank = bank_fn()
        for preset in bank.presets:
            preset.install_to_serum = install
            result = export_wavetable(preset)
            results.append(result)
    return results


def write_export_manifest(results: list[WavetableExportResult],
                          output_dir: str = "output/analysis") -> str:
    """Write JSON manifest of exported wavetables."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "wavetable_export_manifest.json"
    data = [
        {"name": r.name, "path": r.path, "frames": r.num_frames,
         "frame_size": r.frame_size, "installed": r.installed}
        for r in results
    ]
    path.write_text(json.dumps(data, indent=2))
    return str(path)
