# pyright: basic
"""
DUBFORGE — Stem Separator Engine  (Session 182 + Demucs Integration)

Two separation backends:
  1. Demucs (ML-based, GPU-accelerated) — high-quality source separation
  2. Spectral filtering (built-in) — fast, zero-dependency fallback
"""

import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.accel import write_wav
from engine.config_loader import PHI

log = logging.getLogger(__name__)
SAMPLE_RATE = 48000

# ---------------------------------------------------------------------------
# Optional: Demucs (ML-based source separation)
# ---------------------------------------------------------------------------
try:
    import torch as _torch  # type: ignore[import-unresolved]
    import torchaudio as _torchaudio  # type: ignore[import-unresolved]

    HAS_TORCH = True
except ModuleNotFoundError:
    _torch: Any = None
    _torchaudio: Any = None
    HAS_TORCH = False

try:
    from demucs.apply import apply_model as _demucs_apply  # type: ignore[import-unresolved]
    from demucs.pretrained import get_model as _demucs_get_model  # type: ignore[import-unresolved]

    HAS_DEMUCS = True
except ModuleNotFoundError:
    HAS_DEMUCS = False
SAMPLE_RATE = 48000


@dataclass
class Stem:
    """A separated audio stem."""
    name: str
    signal: list[float]
    low_hz: float = 0.0
    high_hz: float = 22050.0

    @property
    def duration_s(self) -> float:
        return len(self.signal) / SAMPLE_RATE

    @property
    def rms(self) -> float:
        if not self.signal:
            return 0.0
        return math.sqrt(sum(x * x for x in self.signal) / len(self.signal))

    @property
    def peak(self) -> float:
        return max(abs(x) for x in self.signal) if self.signal else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "samples": len(self.signal),
            "duration_s": round(self.duration_s, 2),
            "rms_db": round(20 * math.log10(max(self.rms, 1e-10)), 1),
            "peak_db": round(20 * math.log10(max(self.peak, 1e-10)), 1),
            "range_hz": f"{self.low_hz:.0f}-{self.high_hz:.0f}",
        }


@dataclass
class StemSet:
    """A complete set of separated stems."""
    stems: list[Stem] = field(default_factory=list)
    source_samples: int = 0

    def get_stem(self, name: str) -> Stem | None:
        for s in self.stems:
            if s.name == name:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "stem_count": len(self.stems),
            "source_samples": self.source_samples,
            "stems": [s.to_dict() for s in self.stems],
        }


def _biquad_filter(signal: list[float], cutoff: float,
                    filter_type: str = "lowpass",
                    q: float = 0.707,
                    sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply a biquad filter."""
    w0 = 2 * math.pi * min(cutoff, sample_rate * 0.49) / sample_rate
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)

    if filter_type == "highpass":
        b0 = (1 + cos_w0) / 2
        b1 = -(1 + cos_w0)
        b2 = (1 + cos_w0) / 2
    elif filter_type == "bandpass":
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
    else:
        b0 = (1 - cos_w0) / 2
        b1 = 1 - cos_w0
        b2 = (1 - cos_w0) / 2

    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha

    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0

    x1 = x2 = y1 = y2 = 0.0
    result: list[float] = []

    for x in signal:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2 = x1
        x1 = x
        y2 = y1
        y1 = y
        result.append(y)

    return result


def _extract_transients(signal: list[float],
                         sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Extract transient content from signal."""
    fast_env = 0.0
    slow_env = 0.0
    fast_coeff = math.exp(-1.0 / (0.001 * sample_rate))
    slow_coeff = math.exp(-1.0 / (0.05 * sample_rate))

    result: list[float] = []
    for x in signal:
        level = abs(x)
        fast_env = fast_coeff * fast_env + (1 - fast_coeff) * level
        slow_env = slow_coeff * slow_env + (1 - slow_coeff) * level

        if fast_env > slow_env * 1.5:
            result.append(x)
        else:
            result.append(x * 0.1)

    return result


def separate_stems(signal: list[float],
                    n_bands: int = 4,
                    sample_rate: int = SAMPLE_RATE) -> StemSet:
    """Separate signal into frequency-band stems."""
    if not signal:
        return StemSet()

    stems: list[Stem] = []

    if n_bands == 3:
        crossovers = [200.0, 2000.0]
        names = ["Bass", "Mid", "High"]
    elif n_bands >= 4:
        crossovers = [80.0, 400.0, 4000.0]
        names = ["Sub", "Bass", "Mid", "High"]
    else:
        crossovers = [500.0]
        names = ["Low", "High"]

    # Apply cascaded filters for each band
    _prev_hp = signal
    for i in range(len(crossovers)):
        if i == 0:
            # First band: lowpass
            lp = _biquad_filter(signal, crossovers[0], "lowpass", 0.707, sample_rate)
            # Apply twice for steeper slope
            lp = _biquad_filter(lp, crossovers[0], "lowpass", 0.707, sample_rate)
            stems.append(Stem(names[0], lp, 0.0, crossovers[0]))
        else:
            # Middle bands: bandpass
            bp = _biquad_filter(signal, crossovers[i - 1], "highpass", 0.707, sample_rate)
            bp = _biquad_filter(bp, crossovers[i], "lowpass", 0.707, sample_rate)
            stems.append(Stem(names[i], bp, crossovers[i - 1], crossovers[i]))

    # Last band: highpass above last crossover
    hp = _biquad_filter(signal, crossovers[-1], "highpass", 0.707, sample_rate)
    hp = _biquad_filter(hp, crossovers[-1], "highpass", 0.707, sample_rate)
    stems.append(Stem(names[-1], hp, crossovers[-1], sample_rate / 2))

    return StemSet(stems=stems, source_samples=len(signal))


def separate_with_transients(signal: list[float],
                              sample_rate: int = SAMPLE_RATE) -> StemSet:
    """Separate into frequency bands plus transient stem."""
    stem_set = separate_stems(signal, 4, sample_rate)

    # Extract transients
    transients = _extract_transients(signal, sample_rate)
    stem_set.stems.append(Stem("Transients", transients, 0.0, sample_rate / 2))

    return stem_set


def phi_separate(signal: list[float],
                  sample_rate: int = SAMPLE_RATE) -> StemSet:
    """Separate using PHI-ratio crossover frequencies."""
    # Base frequency: 80Hz, then multiply by PHI
    base = 80.0
    crossovers = [base, base * PHI, base * PHI * PHI, base * (PHI ** 3)]
    # ~80, 129, 209, 338 Hz... too low. Use PHI^n from A4_432
    crossovers = [
        80.0,
        80.0 * PHI ** 2,   # ~209 Hz
        80.0 * PHI ** 4,   # ~549 Hz
        80.0 * PHI ** 6,   # ~1443 Hz
    ]
    names = ["Sub", "Bass", "Low Mid", "High Mid", "High"]

    stems: list[Stem] = []
    for i, cross in enumerate(crossovers):
        if i == 0:
            lp = _biquad_filter(signal, cross, "lowpass", 0.707, sample_rate)
            stems.append(Stem(names[0], lp, 0, cross))
        else:
            bp = _biquad_filter(signal, crossovers[i - 1], "highpass", 0.707, sample_rate)
            bp = _biquad_filter(bp, cross, "lowpass", 0.707, sample_rate)
            stems.append(Stem(names[i], bp, crossovers[i - 1], cross))

    hp = _biquad_filter(signal, crossovers[-1], "highpass", 0.707, sample_rate)
    stems.append(Stem(names[-1], hp, crossovers[-1], sample_rate / 2))

    return StemSet(stems=stems, source_samples=len(signal))


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s, sample_rate=sample_rate)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# Demucs ML-based separation
# ═══════════════════════════════════════════════════════════════════════════

# Demucs stem names → DUBFORGE stem names
_DEMUCS_STEM_MAP = {
    "drums": "Drums",
    "bass": "Bass",
    "vocals": "Vocals",
    "other": "Other",
}

# Frequency ranges for Demucs stems (approximate, for metadata)
_DEMUCS_FREQ_RANGES = {
    "Drums": (20.0, 16000.0),
    "Bass": (20.0, 500.0),
    "Vocals": (80.0, 12000.0),
    "Other": (100.0, 20000.0),
}


def separate_demucs(wav_path: str | Path,
                    model_name: str = "htdemucs",
                    device: str | None = None,
                    shifts: int = 1) -> StemSet:
    """
    Separate audio into stems using Demucs (ML-based).

    Args:
        wav_path: Path to the WAV file to separate.
        model_name: Demucs model name. Options:
            - "htdemucs" (default, fast, good quality)
            - "htdemucs_ft" (fine-tuned, 4x slower, best quality)
            - "htdemucs_6s" (6-stem: drums/bass/vocals/guitar/piano/other)
        device: "cpu", "mps" (Apple Silicon), or "cuda". Auto-detected if None.
        shifts: Number of random shifts for TTA (more = better but slower).

    Returns:
        StemSet with separated stems (Drums, Bass, Vocals, Other).

    Raises:
        RuntimeError: If Demucs/PyTorch is not installed.
    """
    if not HAS_DEMUCS or not HAS_TORCH:
        raise RuntimeError(
            "Demucs requires PyTorch + demucs. Install with:\n"
            "  pip install demucs torch torchaudio"
        )

    wav_path = Path(wav_path)
    if not wav_path.exists():
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    # Auto-detect device
    if device is None:
        if _torch.backends.mps.is_available():
            device = "mps"
        elif _torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    log.info("Demucs: model=%s, device=%s, shifts=%d", model_name, device, shifts)

    # Load model
    model = _demucs_get_model(model_name)
    model.to(_torch.device(device))

    # Load audio
    waveform, sr = _torchaudio.load(str(wav_path))

    # Resample to model sample rate if needed
    if sr != model.samplerate:
        waveform = _torchaudio.functional.resample(waveform, sr, model.samplerate)
        sr = model.samplerate

    # Ensure stereo (Demucs expects 2 channels)
    if waveform.shape[0] == 1:
        waveform = waveform.repeat(2, 1)
    elif waveform.shape[0] > 2:
        waveform = waveform[:2]

    # Apply model: shape (sources, channels, samples)
    ref = waveform.mean(0)
    waveform = (waveform - ref.mean()) / ref.std()
    with _torch.no_grad():
        sources = _demucs_apply(
            model,
            waveform.unsqueeze(0).to(device),
            shifts=shifts,
        )
    sources = sources * ref.std() + ref.mean()
    sources = sources.squeeze(0).cpu()

    # Convert to StemSet
    stems: list[Stem] = []
    source_names = model.sources  # e.g. ["drums", "bass", "other", "vocals"]

    for idx, src_name in enumerate(source_names):
        stem_name = _DEMUCS_STEM_MAP.get(src_name, src_name.title())
        # Mix to mono, convert to list[float]
        mono = sources[idx].mean(dim=0).numpy().astype(np.float64)
        lo, hi = _DEMUCS_FREQ_RANGES.get(stem_name or src_name, (20.0, 20000.0))
        stems.append(Stem(
            name=stem_name or src_name,
            signal=mono.tolist(),
            low_hz=lo,
            high_hz=hi,
        ))

    total_samples = int(waveform.shape[1])
    log.info("Demucs: separated into %d stems (%d samples)", len(stems), total_samples)

    return StemSet(stems=stems, source_samples=total_samples)


def separate_demucs_to_files(wav_path: str | Path,
                             output_dir: str | Path = "output/stems_demucs",
                             model_name: str = "htdemucs",
                             device: str | None = None) -> dict[str, Path]:
    """
    Separate with Demucs and export each stem as a WAV file.

    Returns:
        Dict mapping stem name → output WAV path.
    """
    stem_set = separate_demucs(wav_path, model_name=model_name, device=device)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result: dict[str, Path] = {}
    # Use model sample rate (typically 44100 for htdemucs)
    sr = 44100  # Demucs default
    for stem in stem_set.stems:
        fname = stem.name.lower().replace(" ", "_") + ".wav"
        fpath = out / fname
        _write_wav(str(fpath), stem.signal, sample_rate=sr)
        result[stem.name] = fpath
        log.info("  Exported: %s → %s", stem.name, fpath)

    return result


def auto_separate(wav_path: str | Path | None = None,
                  signal: list[float] | None = None,
                  sample_rate: int = SAMPLE_RATE,
                  prefer_ml: bool = True) -> StemSet:
    """
    Auto-select best separation method.

    Uses Demucs if available and prefer_ml=True, otherwise falls back
    to spectral filtering.

    Args:
        wav_path: Path to WAV file (required for Demucs).
        signal: Audio signal as list (for spectral fallback).
        sample_rate: Sample rate for spectral fallback.
        prefer_ml: If True, prefer Demucs over spectral.

    Returns:
        StemSet with separated stems.
    """
    if prefer_ml and HAS_DEMUCS and HAS_TORCH and wav_path is not None:
        try:
            return separate_demucs(wav_path)
        except Exception as e:
            log.warning("Demucs failed (%s), falling back to spectral", e)

    if signal is not None:
        return separate_with_transients(signal, sample_rate)

    # If no signal and no file, try loading wav
    if wav_path is not None:
        import wave as _wave
        with _wave.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
            n = wf.getnframes()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(n)
        if sw == 2:
            arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        else:
            arr = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
        if ch > 1:
            arr = arr.reshape(-1, ch).mean(axis=1)
        return separate_with_transients(arr.tolist(), sr)

    return StemSet()



def export_stems(stem_set: StemSet, output_dir: str = "output/stems",
                  sample_rate: int = SAMPLE_RATE) -> list[str]:
    """Export all stems as WAV files."""
    paths: list[str] = []
    for stem in stem_set.stems:
        if stem.signal:
            path = os.path.join(output_dir, f"{stem.name.lower().replace(' ', '_')}.wav")
            _write_wav(path, stem.signal, sample_rate)
            paths.append(path)
    return paths


def main() -> None:
    print("Stem Separator Engine")

    # Test signal: bass + mid + high transient
    signal: list[float] = []
    for i in range(SAMPLE_RATE * 2):
        t = i / SAMPLE_RATE
        bass = math.sin(2 * math.pi * 60 * t) * 0.5
        mid = math.sin(2 * math.pi * 1000 * t) * 0.2
        high = math.sin(2 * math.pi * 8000 * t) * 0.1
        click = 0.8 * math.exp(-((t % 0.5) * 20)) if (t % 0.5) < 0.01 else 0.0
        signal.append(bass + mid + high + click)

    # 4-band separation
    stems = separate_stems(signal, 4)
    print(f"  4-band separation: {len(stems.stems)} stems")
    for stem in stems.stems:
        info = stem.to_dict()
        print(f"    {info['name']:>10}: {info['range_hz']}, "
              f"RMS={info['rms_db']:.1f} dB")

    # With transients
    stems_t = separate_with_transients(signal)
    print(f"\n  With transients: {len(stems_t.stems)} stems")

    # PHI separation
    phi_stems = phi_separate(signal)
    print(f"\n  PHI separation: {len(phi_stems.stems)} stems")
    for stem in phi_stems.stems:
        info = stem.to_dict()
        print(f"    {info['name']:>10}: {info['range_hz']}")

    print("Done.")


if __name__ == "__main__":
    main()
