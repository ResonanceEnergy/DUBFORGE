"""
DUBFORGE Engine — Render Pipeline

End-to-end audio render chain: synth → FX → sidechain → stereo → master.
One call renders a complete stem from a patch definition.

Pipeline stages:
    generate   — synthesize base audio from synth params
    distort    — apply multiband distortion
    sidechain  — apply sidechain ducking envelope
    stereo     — apply stereo imaging
    master     — apply mastering chain (EQ + compression + limiting)

Banks: 5 pipeline types × 4 presets = 20 presets
"""

import time
import wave
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI, A4_432
from engine.accel import write_wav
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineStage:
    """Single processing stage in the render pipeline."""
    name: str
    stage_type: str  # generate, distort, sidechain, stereo, master
    params: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PipelinePreset:
    """Complete pipeline configuration."""
    name: str
    pipeline_type: str  # bass, lead, pad, perc, full
    stages: list[PipelineStage] = field(default_factory=list)
    sample_rate: int = SAMPLE_RATE
    duration_s: float = 2.0
    base_freq: float = 55.0
    gain_db: float = 0.0


@dataclass
class PipelineBank:
    name: str
    presets: list[PipelinePreset]


# ═══════════════════════════════════════════════════════════════════════════
# STAGE PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

def _generate_tone(preset: PipelinePreset, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a base tone using the preset parameters."""
    n = int(sr * preset.duration_s)
    t = np.linspace(0, preset.duration_s, n, endpoint=False)
    freq = preset.base_freq

    if preset.pipeline_type == "bass":
        sig = np.sin(2 * np.pi * freq * t)
        sig += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        sig += 0.3 * np.sin(2 * np.pi * freq * 3 * t)
    elif preset.pipeline_type == "lead":
        # Saw approximation
        sig = np.zeros(n)
        for k in range(1, 8):
            sig += ((-1) ** (k + 1)) * np.sin(2 * np.pi * freq * k * t) / k
        sig *= 0.5
    elif preset.pipeline_type == "pad":
        sig = np.sin(2 * np.pi * freq * t)
        sig += 0.7 * np.sin(2 * np.pi * freq * PHI * t)
        sig += 0.4 * np.sin(2 * np.pi * freq * PHI ** 2 * t)
        sig *= 0.4
    elif preset.pipeline_type == "perc":
        env = np.exp(-t * 20)
        noise = np.random.default_rng(42).normal(0, 1, n)
        sig = env * (0.6 * np.sin(2 * np.pi * freq * t * np.exp(-t * 5)) + 0.4 * noise)
    else:  # full
        sig = np.sin(2 * np.pi * freq * t)
        sig += 0.618 * np.sin(2 * np.pi * freq * PHI * t)

    # Apply gain
    gain = 10 ** (preset.gain_db / 20)
    return np.clip(sig * gain, -1, 1)


def _apply_distortion_stage(signal: np.ndarray, params: dict) -> np.ndarray:
    """Soft-clip distortion stage."""
    drive = params.get("drive", 0.5)
    driven = signal * (1 + drive * 5)
    return np.tanh(driven)


def _apply_sidechain_stage(signal: np.ndarray, params: dict,
                           sr: int = SAMPLE_RATE) -> np.ndarray:
    """Apply sidechain pump envelope."""
    depth = params.get("depth", 0.7)
    rate_hz = params.get("rate_hz", 2.0)
    n = len(signal)
    t = np.arange(n) / sr
    # Half-sine pump
    envelope = 1.0 - depth * np.abs(np.sin(np.pi * rate_hz * t))
    return signal * envelope


def _apply_stereo_stage(signal: np.ndarray, params: dict,
                        sr: int = SAMPLE_RATE) -> np.ndarray:
    """Apply Haas-effect stereo widening. Returns (n,2)."""
    delay_ms = params.get("delay_ms", 10.0 / PHI)
    width = params.get("width", 0.8)
    delay_samples = int(delay_ms * sr / 1000)
    left = signal.copy()
    right = np.zeros_like(signal)
    if delay_samples < len(signal):
        right[delay_samples:] = signal[:-delay_samples] * width
        right[:delay_samples] = signal[:delay_samples] * 0.3
    else:
        right = signal * 0.5
    return np.column_stack([left, right])


def _apply_master_stage(signal: np.ndarray, params: dict) -> np.ndarray:
    """Simple mastering: soft-clip limiting + gain."""
    ceiling = params.get("ceiling", 0.95)
    makeup_db = params.get("makeup_db", 2.0)
    gain = 10 ** (makeup_db / 20)
    out = signal * gain
    return np.tanh(out / ceiling) * ceiling


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def run_pipeline(preset: PipelinePreset,
                 sr: int = SAMPLE_RATE) -> np.ndarray:
    """Run the full render pipeline, returning audio (mono or stereo)."""
    audio = _generate_tone(preset, sr)

    for stage in preset.stages:
        if not stage.enabled:
            continue
        if stage.stage_type == "distort":
            if audio.ndim == 2:
                audio = np.column_stack([
                    _apply_distortion_stage(audio[:, 0], stage.params),
                    _apply_distortion_stage(audio[:, 1], stage.params),
                ])
            else:
                audio = _apply_distortion_stage(audio, stage.params)
        elif stage.stage_type == "sidechain":
            if audio.ndim == 2:
                env = _apply_sidechain_stage(audio[:, 0], stage.params, sr)
                sc_env = env / (audio[:, 0] + 1e-10)
                audio = audio * sc_env[:, np.newaxis]
            else:
                audio = _apply_sidechain_stage(audio, stage.params, sr)
        elif stage.stage_type == "stereo":
            if audio.ndim == 1:
                audio = _apply_stereo_stage(audio, stage.params, sr)
        elif stage.stage_type == "master":
            if audio.ndim == 2:
                for ch in range(2):
                    audio[:, ch] = _apply_master_stage(audio[:, ch], stage.params)
            else:
                audio = _apply_master_stage(audio, stage.params)

    return np.clip(audio, -1, 1)


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(samples, dtype=np.float64) if not isinstance(samples, np.ndarray) else samples
    write_wav(str(path), _s, sample_rate=sample_rate)



# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def _bass_stages() -> list[PipelineStage]:
    return [
        PipelineStage("distort", "distort", {"drive": 0.4}),
        PipelineStage("sidechain", "sidechain", {"depth": 0.6, "rate_hz": 2.0}),
        PipelineStage("master", "master", {"ceiling": 0.95}),
    ]


def _lead_stages() -> list[PipelineStage]:
    return [
        PipelineStage("distort", "distort", {"drive": 0.3}),
        PipelineStage("stereo", "stereo", {"delay_ms": 8.0, "width": 0.7}),
        PipelineStage("master", "master", {"ceiling": 0.9, "makeup_db": 3.0}),
    ]


def _pad_stages() -> list[PipelineStage]:
    return [
        PipelineStage("stereo", "stereo", {"delay_ms": 15.0, "width": 1.0}),
        PipelineStage("master", "master", {"ceiling": 0.85}),
    ]


def _perc_stages() -> list[PipelineStage]:
    return [
        PipelineStage("distort", "distort", {"drive": 0.2}),
        PipelineStage("master", "master", {"ceiling": 0.95, "makeup_db": 4.0}),
    ]


def _full_stages() -> list[PipelineStage]:
    return [
        PipelineStage("distort", "distort", {"drive": 0.5}),
        PipelineStage("sidechain", "sidechain", {"depth": 0.7, "rate_hz": 2.5}),
        PipelineStage("stereo", "stereo", {"delay_ms": 10.0 / PHI}),
        PipelineStage("master", "master", {"ceiling": 0.92, "makeup_db": 2.5}),
    ]


STAGE_FACTORIES = {
    "bass": _bass_stages,
    "lead": _lead_stages,
    "pad": _pad_stages,
    "perc": _perc_stages,
    "full": _full_stages,
}


def bass_pipeline_bank() -> PipelineBank:
    return PipelineBank("bass", [
        PipelinePreset("bass_sub", "bass", _bass_stages(), base_freq=40.0),
        PipelinePreset("bass_mid", "bass", _bass_stages(), base_freq=80.0),
        PipelinePreset("bass_high", "bass", _bass_stages(), base_freq=120.0, gain_db=2.0),
        PipelinePreset("bass_phi", "bass", _bass_stages(), base_freq=55.0 * PHI),
    ])


def lead_pipeline_bank() -> PipelineBank:
    return PipelineBank("lead", [
        PipelinePreset("lead_bright", "lead", _lead_stages(), base_freq=A4_432 / 2),  # A3=216
        PipelinePreset("lead_mid", "lead", _lead_stages(), base_freq=A4_432 * 0.75),  # ~324
        PipelinePreset("lead_high", "lead", _lead_stages(), base_freq=A4_432, gain_db=-2.0),
        PipelinePreset("lead_phi", "lead", _lead_stages(), base_freq=(A4_432 / 2) * PHI),
    ])


def pad_pipeline_bank() -> PipelineBank:
    return PipelineBank("pad", [
        PipelinePreset("pad_warm", "pad", _pad_stages(), base_freq=110.0, duration_s=4.0),
        PipelinePreset("pad_airy", "pad", _pad_stages(), base_freq=220.0, duration_s=3.0),
        PipelinePreset("pad_dark", "pad", _pad_stages(), base_freq=55.0, duration_s=5.0),
        PipelinePreset("pad_phi", "pad", _pad_stages(), base_freq=110.0 / PHI, duration_s=3.0),
    ])


def perc_pipeline_bank() -> PipelineBank:
    return PipelineBank("perc", [
        PipelinePreset("perc_snap", "perc", _perc_stages(), base_freq=1000.0, duration_s=0.5),
        PipelinePreset("perc_thud", "perc", _perc_stages(), base_freq=200.0, duration_s=0.8),
        PipelinePreset("perc_click", "perc", _perc_stages(), base_freq=2000.0, duration_s=0.3),
        PipelinePreset("perc_phi", "perc", _perc_stages(), base_freq=618.0, duration_s=0.5),
    ])


def full_pipeline_bank() -> PipelineBank:
    return PipelineBank("full", [
        PipelinePreset("full_weapon", "full", _full_stages(), base_freq=55.0),
        PipelinePreset("full_melodic", "full", _full_stages(), base_freq=110.0, gain_db=-1.0),
        PipelinePreset("full_heavy", "full", _full_stages(), base_freq=40.0, gain_db=3.0),
        PipelinePreset("full_phi", "full", _full_stages(), base_freq=55.0 * PHI),
    ])


ALL_PIPELINE_BANKS: dict[str, callable] = {
    "bass": bass_pipeline_bank,
    "lead": lead_pipeline_bank,
    "pad": pad_pipeline_bank,
    "perc": perc_pipeline_bank,
    "full": full_pipeline_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_pipeline_stems(output_dir: str = "output") -> list[str]:
    """Render all pipeline presets to .wav stems."""
    out = Path(output_dir) / "wavetables" / "pipeline"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for bank_name, bank_fn in ALL_PIPELINE_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            audio = run_pipeline(preset)
            fname = f"pipe_{preset.name}.wav"
            _write_wav(out / fname, audio)
            paths.append(str(out / fname))
    return paths


def _render_single_stem(args: tuple[str, str, str]) -> str:
    """Worker function for parallel stem rendering."""
    bank_name, preset_name, output_dir = args
    out = Path(output_dir) / "wavetables" / "pipeline"
    out.mkdir(parents=True, exist_ok=True)
    bank = ALL_PIPELINE_BANKS[bank_name]()
    for preset in bank.presets:
        if preset.name == preset_name:
            audio = run_pipeline(preset)
            fname = f"pipe_{preset.name}.wav"
            _write_wav(out / fname, audio)
            return str(out / fname)
    return ""


def export_pipeline_stems_parallel(
    output_dir: str = "output",
    workers: int | None = None,
    progress_callback=None,
) -> list[str]:
    """Render all pipeline presets in parallel across CPU cores."""
    from engine.config_loader import WORKERS_COMPUTE
    if workers is None:
        workers = WORKERS_COMPUTE

    jobs: list[tuple[str, str, str]] = []
    for bank_name, bank_fn in ALL_PIPELINE_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            jobs.append((bank_name, preset.name, output_dir))

    total = len(jobs)
    paths: list[str] = []

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_render_single_stem, job): job for job in jobs}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            _, preset_name, _ = futures[future]
            try:
                path = future.result()
                if path:
                    paths.append(path)
            except Exception:
                pass
            if progress_callback:
                progress_callback(completed, total, preset_name)

    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_pipeline_manifest(output_dir: str = "output") -> dict:
    """Write pipeline manifest JSON."""
    import json

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_PIPELINE_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "render_pipeline_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_pipeline_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    t0 = time.perf_counter()
    wavs = export_pipeline_stems_parallel(
        progress_callback=lambda done, tot, name: print(f"  [{done}/{tot}] {name}")
    )
    elapsed = time.perf_counter() - t0
    print(f"Render Pipeline: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
