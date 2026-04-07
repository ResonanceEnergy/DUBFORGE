"""
DUBFORGE Engine — Spectral Resynthesis

FFT analysis → phi-filtered reconstruction. Import any signal → DUBFORGE wavetable.
Analyzes spectral content and reconstructs using phi-harmonic filtering.

Types:
    additive     — reconstruct from detected harmonics only
    subtractive  — remove non-phi-related partials
    phi_filter   — keep only phi-ratio harmonics
    spectral_env — preserve spectral envelope, replace fine structure
    hybrid       — blend original + phi-filtered reconstruction

Banks: 5 types × 4 presets = 20 presets
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import fft, ifft, convolve, write_wav
FRAME_SIZE = 2048


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ResynthPreset:
    """Configuration for spectral resynthesis."""
    name: str
    resynth_type: str  # additive, subtractive, phi_filter, spectral_env, hybrid
    fft_size: int = 4096
    num_harmonics: int = 32
    phi_tolerance: float = 0.05
    env_smoothing: float = 0.1
    blend: float = 0.5
    num_output_frames: int = 16
    frame_size: int = FRAME_SIZE


@dataclass
class ResynthBank:
    name: str
    presets: list[ResynthPreset]


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_spectrum(signal: np.ndarray, preset: ResynthPreset,
                     sr: int = SAMPLE_RATE) -> dict:
    """Analyze spectral content of a signal."""
    n = min(len(signal), preset.fft_size)
    windowed = signal[:n] * np.hanning(n)
    spectrum = fft(windowed)
    magnitudes = np.abs(spectrum)
    phases = np.angle(spectrum)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)

    # Find peaks
    peaks = []
    for i in range(1, len(magnitudes) - 1):
        if magnitudes[i] > magnitudes[i - 1] and magnitudes[i] > magnitudes[i + 1]:
            if magnitudes[i] > np.max(magnitudes) * 0.01:
                peaks.append({
                    "bin": i,
                    "freq": float(freqs[i]),
                    "mag": float(magnitudes[i]),
                    "phase": float(phases[i]),
                })

    peaks.sort(key=lambda p: p["mag"], reverse=True)
    peaks = peaks[:preset.num_harmonics]

    return {
        "magnitudes": magnitudes,
        "phases": phases,
        "freqs": freqs,
        "peaks": peaks,
        "fundamental": peaks[0]["freq"] if peaks else 0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# RESYNTHESIS ENGINES
# ═══════════════════════════════════════════════════════════════════════════

def resynth_additive(signal: np.ndarray, preset: ResynthPreset,
                     sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Reconstruct from detected harmonics only."""
    analysis = analyze_spectrum(signal, preset, sr)
    frames: list[np.ndarray] = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)

    for fi in range(preset.num_output_frames):
        frame = np.zeros(preset.frame_size)
        morph = fi / max(preset.num_output_frames - 1, 1)
        for peak in analysis["peaks"]:
            freq_ratio = peak["freq"] / max(analysis["fundamental"], 1.0)
            amp = peak["mag"] / max(analysis["magnitudes"].max(), 1e-10)
            amp *= 1.0 - morph * 0.3  # Evolve amplitude
            frame += amp * np.sin(freq_ratio * t + peak["phase"] + morph * PHI)
        peak_val = np.max(np.abs(frame))
        if peak_val > 0:
            frame = frame / peak_val
        frames.append(frame)
    return frames


def resynth_subtractive(signal: np.ndarray, preset: ResynthPreset,
                        sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Remove non-phi-related partials."""
    analysis = analyze_spectrum(signal, preset, sr)
    frames: list[np.ndarray] = []

    for fi in range(preset.num_output_frames):
        n = min(len(signal), preset.fft_size)
        spectrum = fft(signal[:n] * np.hanning(n))
        freqs = analysis["freqs"]
        fundamental = max(analysis["fundamental"], 20.0)

        # Keep only phi-related partials
        for i in range(len(spectrum)):
            if freqs[i] < 20:
                continue
            ratio = freqs[i] / fundamental
            is_phi = False
            for p in range(5):
                target = PHI ** p
                if abs(ratio - target) < preset.phi_tolerance * target:
                    is_phi = True
                    break
                target = round(ratio)
                if target > 0 and abs(ratio - target) < 0.1:
                    is_phi = True
                    break
            if not is_phi:
                morph_factor = fi / max(preset.num_output_frames - 1, 1)
                spectrum[i] *= (1 - morph_factor * 0.8)

        recon = ifft(spectrum, n=preset.frame_size)
        peak_val = np.max(np.abs(recon))
        if peak_val > 0:
            recon = recon / peak_val
        frames.append(recon)
    return frames


def resynth_phi_filter(signal: np.ndarray, preset: ResynthPreset,
                       sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Keep only phi-ratio harmonics."""
    analysis = analyze_spectrum(signal, preset, sr)
    fundamental = max(analysis["fundamental"], 20.0)
    frames: list[np.ndarray] = []
    t = np.linspace(0, 2 * np.pi, preset.frame_size, endpoint=False)

    phi_ratios = [PHI ** p for p in range(8)]

    for fi in range(preset.num_output_frames):
        frame = np.zeros(preset.frame_size)
        morph = fi / max(preset.num_output_frames - 1, 1)
        for ratio in phi_ratios:
            freq = fundamental * ratio
            if freq > sr / 2:
                break
            # Find closest peak
            amp = 0.5 / (1 + ratio * 0.3)
            frame += amp * np.sin(ratio * t + morph * np.pi * PHI)
        peak_val = np.max(np.abs(frame))
        if peak_val > 0:
            frame = frame / peak_val
        frames.append(frame)
    return frames


def resynth_spectral_env(signal: np.ndarray, preset: ResynthPreset,
                         sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Preserve spectral envelope, replace fine structure."""
    n = min(len(signal), preset.fft_size)
    spectrum = fft(signal[:n] * np.hanning(n))
    mag = np.abs(spectrum)

    # Spectral envelope via smoothing
    k = max(1, int(len(mag) * preset.env_smoothing))
    envelope = convolve(mag, np.ones(k) / k, mode="same")

    frames: list[np.ndarray] = []

    for fi in range(preset.num_output_frames):
        # Generate new fine structure using phi harmonics
        morph = fi / max(preset.num_output_frames - 1, 1)
        new_fft = np.zeros(len(envelope), dtype=complex)
        for i in range(len(envelope)):
            phase = morph * 2 * np.pi * PHI * i / len(envelope)
            new_fft[i] = envelope[i] * np.exp(1j * phase)
        frame = ifft(new_fft, n=preset.frame_size)
        peak_val = np.max(np.abs(frame))
        if peak_val > 0:
            frame = frame / peak_val
        frames.append(frame)
    return frames


def resynth_hybrid(signal: np.ndarray, preset: ResynthPreset,
                   sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Blend original + phi-filtered reconstruction."""
    original = resynth_additive(signal, preset, sr)
    phi_filtered = resynth_phi_filter(signal, preset, sr)
    frames: list[np.ndarray] = []
    for orig, phi in zip(original, phi_filtered):
        blend = orig * (1 - preset.blend) + phi * preset.blend
        peak_val = np.max(np.abs(blend))
        if peak_val > 0:
            blend = blend / peak_val
        frames.append(blend)
    return frames


RESYNTH_ENGINES = {
    "additive": resynth_additive,
    "subtractive": resynth_subtractive,
    "phi_filter": resynth_phi_filter,
    "spectral_env": resynth_spectral_env,
    "hybrid": resynth_hybrid,
}


def resynthesize(signal: np.ndarray, preset: ResynthPreset,
                 sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Run resynthesis engine."""
    fn = RESYNTH_ENGINES.get(preset.resynth_type, resynth_additive)
    return fn(signal, preset, sr)


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    write_wav(str(path), samples, sample_rate=sample_rate)


def _test_signal(duration_s: float = 1.0, freq: float = 200.0,
                 sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a test signal for resynthesis."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.5 * np.sin(2 * np.pi * freq * PHI * t)
    sig += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * 0.8


def export_resynth_wavetables(output_dir: str = "output") -> list[str]:
    """Render all resynthesis presets and export as .wav wavetables."""
    out = Path(output_dir) / "wavetables" / "resynthesis"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    source = _test_signal()

    for bank_name, bank_fn in ALL_RESYNTH_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            frames = resynthesize(source, preset)
            audio = np.concatenate(frames)
            fname = f"resynth_{preset.name}.wav"
            _write_wav(out / fname, audio)
            paths.append(str(out / fname))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def additive_resynth_bank() -> ResynthBank:
    return ResynthBank("additive", [
        ResynthPreset("add_standard", "additive"),
        ResynthPreset("add_rich", "additive", num_harmonics=64),
        ResynthPreset("add_sparse", "additive", num_harmonics=8),
        ResynthPreset("add_phi", "additive", num_harmonics=int(32 * PHI)),
    ])


def subtractive_resynth_bank() -> ResynthBank:
    return ResynthBank("subtractive", [
        ResynthPreset("sub_standard", "subtractive"),
        ResynthPreset("sub_tight", "subtractive", phi_tolerance=0.02),
        ResynthPreset("sub_loose", "subtractive", phi_tolerance=0.1),
        ResynthPreset("sub_phi", "subtractive", phi_tolerance=1.0 / PHI * 0.08),
    ])


def phi_filter_resynth_bank() -> ResynthBank:
    return ResynthBank("phi_filter", [
        ResynthPreset("phi_standard", "phi_filter"),
        ResynthPreset("phi_deep", "phi_filter", num_output_frames=32),
        ResynthPreset("phi_bright", "phi_filter", fft_size=8192),
        ResynthPreset("phi_warm", "phi_filter", num_harmonics=16),
    ])


def spectral_env_resynth_bank() -> ResynthBank:
    return ResynthBank("spectral_env", [
        ResynthPreset("env_smooth", "spectral_env", env_smoothing=0.1),
        ResynthPreset("env_sharp", "spectral_env", env_smoothing=0.02),
        ResynthPreset("env_wide", "spectral_env", env_smoothing=0.3),
        ResynthPreset("env_phi", "spectral_env", env_smoothing=1.0 / PHI * 0.15),
    ])


def hybrid_resynth_bank() -> ResynthBank:
    return ResynthBank("hybrid", [
        ResynthPreset("hyb_balanced", "hybrid", blend=0.5),
        ResynthPreset("hyb_original", "hybrid", blend=0.2),
        ResynthPreset("hyb_phi_heavy", "hybrid", blend=0.8),
        ResynthPreset("hyb_phi_exact", "hybrid", blend=1.0 / PHI),
    ])


ALL_RESYNTH_BANKS: dict[str, callable] = {
    "additive": additive_resynth_bank,
    "subtractive": subtractive_resynth_bank,
    "phi_filter": phi_filter_resynth_bank,
    "spectral_env": spectral_env_resynth_bank,
    "hybrid": hybrid_resynth_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_resynth_manifest(output_dir: str = "output") -> dict:
    """Write spectral resynthesis manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_RESYNTH_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }
    path = out / "spectral_resynthesis_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_resynth_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_resynth_wavetables()
    print(f"Spectral Resynthesis: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
