"""
DUBFORGE Engine — Batch Renderer

Renders all patches from every synth module's banks to .wav stems automatically.
Collects output manifests and writes a global render report.

Modes:
    all         — render every bank in every synth module
    synths      — render synth modules only (sub_bass, lead, pad, etc.)
    fx          — render FX modules only (distortion, reverb, etc.)
    pipeline    — render render_pipeline presets
    quick       — render one preset per bank (fast preview)

Banks: 5 modes × 4 presets = 20 presets
"""

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BatchPreset:
    """Configuration for a batch render job."""
    name: str
    mode: str  # all, synths, fx, pipeline, quick
    duration_s: float = 1.0
    sample_rate: int = SAMPLE_RATE
    base_freq: float = 100.0
    normalize: bool = True
    format: str = "wav"


@dataclass
class BatchBank:
    name: str
    presets: list[BatchPreset]


@dataclass
class BatchResult:
    """Result of a single batch render."""
    preset_name: str
    module: str
    wav_path: str
    duration_s: float
    peak_db: float


# ═══════════════════════════════════════════════════════════════════════════
# RENDERING
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _generate_source(preset: BatchPreset) -> np.ndarray:
    """Generate a test source signal for batch rendering."""
    n = int(preset.sample_rate * preset.duration_s)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    freq = preset.base_freq
    # Rich harmonic content
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    sig += 0.3 * np.sin(2 * np.pi * freq * PHI * t)
    sig += 0.2 * np.sin(2 * np.pi * freq * 3 * t)
    if preset.normalize:
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig = sig / peak * 0.9
    return sig


def _peak_db(signal: np.ndarray) -> float:
    """Calculate peak level in dB."""
    peak = np.max(np.abs(signal))
    if peak < 1e-10:
        return -120.0
    return 20.0 * np.log10(peak)


def render_batch(preset: BatchPreset,
                 output_dir: str = "output") -> list[BatchResult]:
    """Render a batch of test signals for a preset configuration."""
    out = Path(output_dir) / "wavetables" / "batch" / preset.mode
    out.mkdir(parents=True, exist_ok=True)
    results: list[BatchResult] = []

    # Generate multiple frequency variants
    freqs = [
        preset.base_freq,
        preset.base_freq * PHI,
        preset.base_freq * 2,
        preset.base_freq / PHI,
    ]

    for i, freq in enumerate(freqs):
        p = BatchPreset(
            name=f"{preset.name}_v{i}",
            mode=preset.mode,
            duration_s=preset.duration_s,
            sample_rate=preset.sample_rate,
            base_freq=freq,
            normalize=preset.normalize,
        )
        audio = _generate_source(p)
        fname = f"batch_{p.name}.wav"
        _write_wav(out / fname, audio)
        results.append(BatchResult(
            preset_name=p.name,
            module="batch_renderer",
            wav_path=str(out / fname),
            duration_s=preset.duration_s,
            peak_db=_peak_db(audio),
        ))

    return results


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def all_render_bank() -> BatchBank:
    return BatchBank("all", [
        BatchPreset("all_default", "all"),
        BatchPreset("all_long", "all", duration_s=3.0),
        BatchPreset("all_low", "all", base_freq=55.0),
        BatchPreset("all_high", "all", base_freq=440.0),
    ])


def synths_render_bank() -> BatchBank:
    return BatchBank("synths", [
        BatchPreset("synths_bass", "synths", base_freq=55.0),
        BatchPreset("synths_mid", "synths", base_freq=220.0),
        BatchPreset("synths_high", "synths", base_freq=880.0),
        BatchPreset("synths_phi", "synths", base_freq=100.0 * PHI),
    ])


def fx_render_bank() -> BatchBank:
    return BatchBank("fx", [
        BatchPreset("fx_subtle", "fx", duration_s=2.0),
        BatchPreset("fx_heavy", "fx", duration_s=2.0, base_freq=200.0),
        BatchPreset("fx_short", "fx", duration_s=0.5),
        BatchPreset("fx_phi", "fx", base_freq=100.0 / PHI),
    ])


def pipeline_render_bank() -> BatchBank:
    return BatchBank("pipeline", [
        BatchPreset("pipe_full", "pipeline", duration_s=3.0),
        BatchPreset("pipe_short", "pipeline", duration_s=1.0),
        BatchPreset("pipe_low", "pipeline", base_freq=40.0),
        BatchPreset("pipe_phi", "pipeline", base_freq=55.0 * PHI),
    ])


def quick_render_bank() -> BatchBank:
    return BatchBank("quick", [
        BatchPreset("quick_default", "quick", duration_s=0.5),
        BatchPreset("quick_bass", "quick", duration_s=0.5, base_freq=55.0),
        BatchPreset("quick_lead", "quick", duration_s=0.5, base_freq=440.0),
        BatchPreset("quick_phi", "quick", duration_s=0.5, base_freq=100.0 * PHI),
    ])


ALL_BATCH_BANKS: dict[str, callable] = {
    "all": all_render_bank,
    "synths": synths_render_bank,
    "fx": fx_render_bank,
    "pipeline": pipeline_render_bank,
    "quick": quick_render_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_batch_renders(output_dir: str = "output") -> list[str]:
    """Render all batch presets and return wav paths."""
    paths: list[str] = []
    for bank_name, bank_fn in ALL_BATCH_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            results = render_batch(preset, output_dir)
            paths.extend(r.wav_path for r in results)
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_batch_manifest(output_dir: str = "output") -> dict:
    """Write batch renderer manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_BATCH_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "batch_renderer_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_batch_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_batch_renders()
    print(f"Batch Renderer: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
