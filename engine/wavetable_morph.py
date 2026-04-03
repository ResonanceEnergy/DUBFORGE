"""
DUBFORGE Engine — Wavetable Morph

Fractal interpolation between wavetable frames using phi-curve morphing.
Not simple linear crossfade — uses golden-ratio spline for organic transitions.

Types:
    phi_spline   — golden-ratio weighted spline interpolation
    fractal      — self-similar fractal interpolation
    spectral     — FFT-domain morphing (magnitude + phase)
    formant      — formant-preserving morph
    granular     — grain-cloud crossfade morph

Banks: 5 types × 4 presets = 20 presets
"""

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import fft, ifft, convolve, write_wav
from engine.turboquant import (
    CompressedWavetable,
    TurboQuantConfig,
    compress_wavetable,
    decompress_wavetable,
)
FRAME_SIZE = 2048


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MorphPreset:
    """Configuration for wavetable morphing."""
    name: str
    morph_type: str  # phi_spline, fractal, spectral, formant, granular
    num_frames: int = 16
    frame_size: int = FRAME_SIZE
    morph_curve: float = PHI  # curve exponent
    spectral_smooth: float = 0.1
    formant_shift: float = 0.0
    grain_size: int = 256


@dataclass
class MorphBank:
    name: str
    presets: list[MorphPreset]


# ═══════════════════════════════════════════════════════════════════════════
# FRAME GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _generate_source_frames(num_frames: int = 4,
                            frame_size: int = FRAME_SIZE) -> list[np.ndarray]:
    """Generate source wavetable frames with different harmonic content."""
    frames: list[np.ndarray] = []
    t = np.linspace(0, 2 * np.pi, frame_size, endpoint=False)
    for i in range(num_frames):
        sig = np.zeros(frame_size)
        harmonics = 1 + i * 3
        for k in range(1, harmonics + 1):
            amplitude = 1.0 / (k ** (1 + i * 0.3))
            sig += amplitude * np.sin(k * t + i * PHI)
        peak = np.max(np.abs(sig))
        if peak > 0:
            sig = sig / peak
        frames.append(sig)
    return frames


# ═══════════════════════════════════════════════════════════════════════════
# MORPH ALGORITHMS
# ═══════════════════════════════════════════════════════════════════════════

def morph_phi_spline(frames: list[np.ndarray], preset: MorphPreset) -> list[np.ndarray]:
    """Phi-weighted spline interpolation between frames."""
    if len(frames) < 2:
        return frames * preset.num_frames
    result: list[np.ndarray] = []
    for i in range(preset.num_frames):
        pos = i / max(preset.num_frames - 1, 1) * (len(frames) - 1)
        idx = int(pos)
        frac = pos - idx
        # Phi curve: smoother transitions at boundaries
        frac = frac ** (1.0 / preset.morph_curve) if frac > 0 else 0.0
        a = frames[min(idx, len(frames) - 1)]
        b = frames[min(idx + 1, len(frames) - 1)]
        result.append(a * (1 - frac) + b * frac)
    return result


def morph_fractal(frames: list[np.ndarray], preset: MorphPreset) -> list[np.ndarray]:
    """Self-similar fractal interpolation."""
    if len(frames) < 2:
        return frames * preset.num_frames
    result: list[np.ndarray] = []
    for i in range(preset.num_frames):
        pos = i / max(preset.num_frames - 1, 1) * (len(frames) - 1)
        idx = int(pos)
        frac = pos - idx
        a = frames[min(idx, len(frames) - 1)]
        b = frames[min(idx + 1, len(frames) - 1)]
        # Fractal detail: add self-similar noise at phi-scaled levels
        blend = a * (1 - frac) + b * frac
        for level in range(3):
            scale = 1.0 / (PHI ** (level + 1))
            detail = np.roll(blend, int(len(blend) * scale * frac)) - blend
            blend += detail * scale * 0.3
        peak = np.max(np.abs(blend))
        if peak > 0:
            blend = blend / peak
        result.append(blend)
    return result


def morph_spectral(frames: list[np.ndarray], preset: MorphPreset) -> list[np.ndarray]:
    """FFT-domain morphing of magnitude and phase."""
    if len(frames) < 2:
        return frames * preset.num_frames
    ffts = [fft(f) for f in frames]
    mags = [np.abs(f) for f in ffts]
    phases = [np.angle(f) for f in ffts]
    result: list[np.ndarray] = []

    for i in range(preset.num_frames):
        pos = i / max(preset.num_frames - 1, 1) * (len(frames) - 1)
        idx = int(pos)
        frac = pos - idx
        ma = mags[min(idx, len(mags) - 1)]
        mb = mags[min(idx + 1, len(mags) - 1)]
        pa = phases[min(idx, len(phases) - 1)]
        pb = phases[min(idx + 1, len(phases) - 1)]
        mag = ma * (1 - frac) + mb * frac
        # Smooth spectral transitions
        if preset.spectral_smooth > 0:
            k = max(1, int(len(mag) * preset.spectral_smooth))
            mag = convolve(mag, np.ones(k) / k, mode="same")
        phase = pa * (1 - frac) + pb * frac
        frame = ifft(mag * np.exp(1j * phase), n=preset.frame_size)
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame = frame / peak
        result.append(frame)
    return result


def morph_formant(frames: list[np.ndarray], preset: MorphPreset) -> list[np.ndarray]:
    """Formant-preserving morph using spectral envelope interpolation."""
    if len(frames) < 2:
        return frames * preset.num_frames
    result: list[np.ndarray] = []
    for i in range(preset.num_frames):
        pos = i / max(preset.num_frames - 1, 1) * (len(frames) - 1)
        idx = int(pos)
        frac = pos - idx
        a = frames[min(idx, len(frames) - 1)]
        b = frames[min(idx + 1, len(frames) - 1)]
        # Extract spectral envelopes
        fft_a = fft(a)
        fft_b = fft(b)
        env_a = np.abs(fft_a)
        env_b = np.abs(fft_b)
        # Interpolate envelope
        env_blend = env_a * (1 - frac) + env_b * frac
        # Apply shift
        if abs(preset.formant_shift) > 0.01:
            shift = int(len(env_blend) * preset.formant_shift * 0.1)
            env_blend = np.roll(env_blend, shift)
        # Use phase from source A
        phase = np.angle(fft_a) * (1 - frac) + np.angle(fft_b) * frac
        frame = ifft(env_blend * np.exp(1j * phase), n=preset.frame_size)
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame = frame / peak
        result.append(frame)
    return result


def morph_granular(frames: list[np.ndarray], preset: MorphPreset) -> list[np.ndarray]:
    """Grain-cloud crossfade morph."""
    if len(frames) < 2:
        return frames * preset.num_frames
    result: list[np.ndarray] = []
    gs = min(preset.grain_size, preset.frame_size)
    rng = np.random.default_rng(42)

    for i in range(preset.num_frames):
        pos = i / max(preset.num_frames - 1, 1) * (len(frames) - 1)
        idx = int(pos)
        frac = pos - idx
        a = frames[min(idx, len(frames) - 1)]
        b = frames[min(idx + 1, len(frames) - 1)]
        frame = np.zeros(preset.frame_size)
        num_grains = preset.frame_size // gs
        for g in range(num_grains):
            start = g * gs
            end = start + gs
            if rng.random() > frac:
                frame[start:end] = a[start:end]
            else:
                frame[start:end] = b[start:end]
        # Smooth grain boundaries
        window = np.hanning(gs // 4)
        half = len(window) // 2
        for g in range(1, num_grains):
            boundary = g * gs
            low = max(0, boundary - half)
            high = min(len(frame), boundary + half)
            actual_len = high - low
            if actual_len > 0:
                win = np.hanning(actual_len)
                frame[low:high] *= win
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame = frame / peak
        result.append(frame)
    return result


MORPH_ENGINES = {
    "phi_spline": morph_phi_spline,
    "fractal": morph_fractal,
    "spectral": morph_spectral,
    "formant": morph_formant,
    "granular": morph_granular,
}


def morph_wavetable(frames: list[np.ndarray],
                    preset: MorphPreset) -> list[np.ndarray]:
    """Apply morphing algorithm to source frames."""
    fn = MORPH_ENGINES.get(preset.morph_type, morph_phi_spline)
    return fn(frames, preset)


# ═══════════════════════════════════════════════════════════════════════════
# TURBOQUANT COMPRESSION
# ═══════════════════════════════════════════════════════════════════════════


def tq_compress_morph(
    frames: list[np.ndarray],
    name: str,
    config: TurboQuantConfig | None = None,
) -> CompressedWavetable:
    """TQ-compress morphed wavetable frames."""
    float_frames = [f.tolist() for f in frames]
    return compress_wavetable(float_frames, config or TurboQuantConfig(), name=name)


def tq_decompress_morph(
    compressed: CompressedWavetable,
    config: TurboQuantConfig | None = None,
) -> list[np.ndarray]:
    """Decompress TQ-compressed wavetable back to frames."""
    float_frames = decompress_wavetable(compressed, config or TurboQuantConfig())
    return [np.array(f) for f in float_frames]


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    write_wav(str(path), samples, sample_rate=sample_rate)


def export_morph_wavetables(output_dir: str = "output") -> list[str]:
    """Render all morph presets to concatenated wavetable .wav."""
    out = Path(output_dir) / "wavetables" / "morphs"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    source_frames = _generate_source_frames(4)

    for bank_name, bank_fn in ALL_MORPH_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            morphed = morph_wavetable(source_frames, preset)
            # Concatenate frames into single wav
            audio = np.concatenate(morphed)
            fname = f"morph_{preset.name}.wav"
            _write_wav(out / fname, audio)
            paths.append(str(out / fname))
            # TQ sidecar
            cw = tq_compress_morph(morphed, preset.name)
            tq_path = out / f"morph_{preset.name}.tq"
            import pickle
            tq_path.write_bytes(pickle.dumps(cw))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def phi_spline_morph_bank() -> MorphBank:
    return MorphBank("phi_spline", [
        MorphPreset("phi_smooth", "phi_spline", 16),
        MorphPreset("phi_fine", "phi_spline", 32),
        MorphPreset("phi_coarse", "phi_spline", 8),
        MorphPreset("phi_ultra", "phi_spline", 64, morph_curve=PHI ** 2),
    ])


def fractal_morph_bank() -> MorphBank:
    return MorphBank("fractal", [
        MorphPreset("frac_standard", "fractal", 16),
        MorphPreset("frac_dense", "fractal", 32),
        MorphPreset("frac_sparse", "fractal", 8),
        MorphPreset("frac_deep", "fractal", 16, morph_curve=PHI ** 3),
    ])


def spectral_morph_bank() -> MorphBank:
    return MorphBank("spectral", [
        MorphPreset("spec_smooth", "spectral", 16, spectral_smooth=0.1),
        MorphPreset("spec_sharp", "spectral", 16, spectral_smooth=0.01),
        MorphPreset("spec_wide", "spectral", 32, spectral_smooth=0.2),
        MorphPreset("spec_phi", "spectral", 16, spectral_smooth=1.0 / PHI * 0.2),
    ])


def formant_morph_bank() -> MorphBank:
    return MorphBank("formant", [
        MorphPreset("fmt_neutral", "formant", 16),
        MorphPreset("fmt_shift_up", "formant", 16, formant_shift=0.3),
        MorphPreset("fmt_shift_down", "formant", 16, formant_shift=-0.3),
        MorphPreset("fmt_phi", "formant", 16, formant_shift=1.0 / PHI * 0.2),
    ])


def granular_morph_bank() -> MorphBank:
    return MorphBank("granular", [
        MorphPreset("grain_standard", "granular", 16, grain_size=256),
        MorphPreset("grain_fine", "granular", 16, grain_size=64),
        MorphPreset("grain_coarse", "granular", 16, grain_size=512),
        MorphPreset("grain_phi", "granular", 16, grain_size=int(FRAME_SIZE / PHI)),
    ])


ALL_MORPH_BANKS: dict[str, callable] = {
    "phi_spline": phi_spline_morph_bank,
    "fractal": fractal_morph_bank,
    "spectral": spectral_morph_bank,
    "formant": formant_morph_bank,
    "granular": granular_morph_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_morph_manifest(output_dir: str = "output") -> dict:
    """Write wavetable morph manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_MORPH_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }
    path = out / "wavetable_morph_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_morph_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_morph_wavetables()
    print(f"Wavetable Morph: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
