"""
DUBFORGE Engine — Sample Slicer

Slices audio files into segments using onset detection, beat-grid snapping,
and transient analysis.  Works with WAV files via soundfile.

Outputs:
    output/slices/*.wav   — Individual sliced segments
    output/slices/slice_manifest.json — Metadata for all slices
"""

from __future__ import annotations

import json
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import FIBONACCI
from engine.log import get_logger

_log = get_logger("dubforge.sample_slicer")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_RATE = 44100
HOP_SIZE = 512
ONSET_THRESHOLD = 0.3     # spectral flux threshold (0-1)
MIN_SLICE_MS = 50         # minimum slice length in ms
CROSSFADE_MS = 5          # crossfade length in ms


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SlicePoint:
    """A detected onset / slice boundary."""
    sample_idx: int
    time_s: float
    strength: float       # onset strength 0-1
    label: str = ""


@dataclass
class SliceSegment:
    """A sliced audio segment."""
    index: int
    start_sample: int
    end_sample: int
    start_time: float
    end_time: float
    duration_ms: float
    file_path: str = ""


@dataclass
class SliceResult:
    """Result of a slice operation."""
    source_file: str
    sample_rate: int
    total_samples: int
    total_duration_s: float
    onset_count: int
    segments: list[SliceSegment] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# ONSET DETECTION (pure NumPy — no librosa required)
# ═══════════════════════════════════════════════════════════════════════════

def _spectral_flux(audio: np.ndarray, hop: int = HOP_SIZE,
                   frame_size: int = 2048) -> np.ndarray:
    """Compute spectral flux onset function."""
    n_frames = (len(audio) - frame_size) // hop + 1
    if n_frames < 2:
        return np.array([0.0])

    flux = np.zeros(n_frames)
    window = np.hanning(frame_size)

    prev_spectrum = np.zeros(frame_size // 2 + 1)
    for i in range(n_frames):
        start = i * hop
        frame = audio[start: start + frame_size] * window
        spectrum = np.abs(np.fft.rfft(frame))
        # Half-wave rectified difference
        diff = spectrum - prev_spectrum
        flux[i] = np.sum(np.maximum(0, diff))
        prev_spectrum = spectrum.copy()

    # Normalize
    peak = np.max(flux)
    if peak > 0:
        flux /= peak
    return flux


def _pick_peaks(flux: np.ndarray, threshold: float = ONSET_THRESHOLD,
                min_distance: int = 5) -> list[int]:
    """Pick onset peaks above threshold with minimum distance."""
    peaks = []
    for i in range(1, len(flux) - 1):
        if flux[i] > threshold and flux[i] > flux[i - 1] and flux[i] >= flux[i + 1]:
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    return peaks


def detect_onsets(audio: np.ndarray, sr: int = SAMPLE_RATE,
                  threshold: float = ONSET_THRESHOLD,
                  hop: int = HOP_SIZE) -> list[SlicePoint]:
    """Detect onsets in audio using spectral flux."""
    if len(audio) == 0:
        return []

    # Mono conversion
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    flux = _spectral_flux(audio, hop=hop)
    min_dist = max(1, int(MIN_SLICE_MS * sr / (1000 * hop)))
    peak_frames = _pick_peaks(flux, threshold=threshold, min_distance=min_dist)

    onsets = []
    for frame_idx in peak_frames:
        sample_idx = frame_idx * hop
        time_s = sample_idx / sr
        strength = float(flux[frame_idx])
        onsets.append(SlicePoint(sample_idx=sample_idx, time_s=time_s,
                                 strength=strength))

    _log.info("Detected %d onsets in %.2fs audio", len(onsets), len(audio) / sr)
    return onsets


# ═══════════════════════════════════════════════════════════════════════════
# BEAT-GRID SNAPPING
# ═══════════════════════════════════════════════════════════════════════════

def snap_to_grid(onsets: list[SlicePoint], bpm: float,
                 sr: int = SAMPLE_RATE,
                 divisions: int = 16) -> list[SlicePoint]:
    """Quantize onset positions to nearest beat subdivision."""
    if not onsets or bpm <= 0:
        return onsets

    beat_samples = int(sr * 60.0 / bpm)
    subdiv_samples = beat_samples // divisions

    snapped = []
    for onset in onsets:
        grid_pos = round(onset.sample_idx / subdiv_samples) * subdiv_samples
        snapped.append(SlicePoint(
            sample_idx=grid_pos,
            time_s=grid_pos / sr,
            strength=onset.strength,
            label=onset.label,
        ))

    # Remove duplicates
    seen = set()
    unique = []
    for s in snapped:
        if s.sample_idx not in seen:
            seen.add(s.sample_idx)
            unique.append(s)
    return unique


# ═══════════════════════════════════════════════════════════════════════════
# FIBONACCI SLICING
# ═══════════════════════════════════════════════════════════════════════════

def fibonacci_slice_points(total_samples: int,
                           sr: int = SAMPLE_RATE) -> list[SlicePoint]:
    """Generate slice points at Fibonacci-ratio positions."""
    max_fib = max(FIBONACCI)
    points = []
    for f in FIBONACCI:
        if f > 0:
            pos = int((f / max_fib) * total_samples)
            if 0 < pos < total_samples:
                points.append(SlicePoint(
                    sample_idx=pos,
                    time_s=pos / sr,
                    strength=1.0,
                    label=f"fib_{f}",
                ))
    return sorted(points, key=lambda p: p.sample_idx)


# ═══════════════════════════════════════════════════════════════════════════
# SLICING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def _apply_crossfade(audio: np.ndarray, fade_samples: int) -> np.ndarray:
    """Apply fade-in and fade-out to a slice."""
    if len(audio) <= fade_samples * 2:
        return audio
    result = audio.copy()
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    if result.ndim == 1:
        result[:fade_samples] *= fade_in
        result[-fade_samples:] *= fade_out
    else:
        result[:fade_samples] *= fade_in[:, np.newaxis]
        result[-fade_samples:] *= fade_out[:, np.newaxis]
    return result


def slice_audio(audio: np.ndarray, onsets: list[SlicePoint],
                sr: int = SAMPLE_RATE,
                crossfade_ms: float = CROSSFADE_MS) -> list[tuple[SliceSegment, np.ndarray]]:
    """Slice audio at onset points, returning segments with audio data."""
    if len(audio) == 0:
        return []

    fade_samples = int(crossfade_ms * sr / 1000)
    total = len(audio) if audio.ndim == 1 else audio.shape[0]

    # Add boundaries
    boundaries = [0]
    for onset in sorted(onsets, key=lambda o: o.sample_idx):
        if onset.sample_idx > 0 and onset.sample_idx < total:
            boundaries.append(onset.sample_idx)
    boundaries.append(total)
    boundaries = sorted(set(boundaries))

    segments = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        if end - start < int(MIN_SLICE_MS * sr / 1000):
            continue

        chunk = audio[start:end] if audio.ndim == 1 else audio[start:end]
        chunk = _apply_crossfade(chunk.astype(np.float64), fade_samples)

        seg = SliceSegment(
            index=len(segments),
            start_sample=start,
            end_sample=end,
            start_time=start / sr,
            end_time=end / sr,
            duration_ms=((end - start) / sr) * 1000,
        )
        segments.append((seg, chunk))

    return segments


# ═══════════════════════════════════════════════════════════════════════════
# FILE I/O (uses soundfile if available, falls back to raw WAV)
# ═══════════════════════════════════════════════════════════════════════════

def read_audio(path: str) -> tuple[np.ndarray, int]:
    """Read a WAV file, returns (audio_array, sample_rate)."""
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype="float64")
        return audio, sr
    except ImportError:
        pass

    # Fallback: parse raw PCM WAV
    with open(path, "rb") as f:
        riff = f.read(4)
        if riff != b"RIFF":
            raise ValueError(f"Not a WAV file: {path}")
        f.read(4)  # file size
        wave = f.read(4)
        if wave != b"WAVE":
            raise ValueError(f"Not a WAV file: {path}")

        fmt_found = False
        n_channels = 1
        sr = 44100
        bits_per_sample = 16
        data = b""

        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            chunk_size = struct.unpack("<I", f.read(4))[0]
            if chunk_id == b"fmt ":
                fmt_data = f.read(chunk_size)
                n_channels = struct.unpack("<H", fmt_data[2:4])[0]
                sr = struct.unpack("<I", fmt_data[4:8])[0]
                bits_per_sample = struct.unpack("<H", fmt_data[14:16])[0]
                fmt_found = True
            elif chunk_id == b"data":
                data = f.read(chunk_size)
            else:
                f.read(chunk_size)

        if not fmt_found:
            raise ValueError(f"No fmt chunk in WAV: {path}")

        if bits_per_sample == 16:
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32768.0
        elif bits_per_sample == 32:
            samples = np.frombuffer(data, dtype=np.int32).astype(np.float64) / 2147483648.0
        else:
            raise ValueError(f"Unsupported bit depth: {bits_per_sample}")

        if n_channels > 1:
            samples = samples.reshape(-1, n_channels)

        return samples, sr


def write_audio(path: str, audio: np.ndarray, sr: int = SAMPLE_RATE) -> str:
    """Write audio to WAV file."""
    try:
        import soundfile as sf
        sf.write(path, audio, sr)
        return path
    except ImportError:
        pass

    # Fallback: write raw PCM WAV
    from engine.phi_core import write_wav
    if audio.ndim == 1:
        frames = audio.reshape(1, -1)
    else:
        frames = audio.T if audio.shape[1] <= audio.shape[0] else audio
    write_wav(path, frames, sample_rate=sr)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL API
# ═══════════════════════════════════════════════════════════════════════════

def slice_file(input_path: str, output_dir: str = "output/slices",
               mode: str = "onset", bpm: float = 150.0,
               threshold: float = ONSET_THRESHOLD) -> SliceResult:
    """
    Slice an audio file and write segments to disk.

    Args:
        input_path:  Path to input WAV file
        output_dir:  Output directory for sliced files
        mode:        "onset" | "fibonacci" | "beat_grid"
        bpm:         BPM for beat-grid mode
        threshold:   Onset detection threshold

    Returns:
        SliceResult with metadata and segment info
    """
    audio, sr = read_audio(input_path)
    total = len(audio) if audio.ndim == 1 else audio.shape[0]

    if mode == "fibonacci":
        onsets = fibonacci_slice_points(total, sr)
    elif mode == "beat_grid":
        onsets = detect_onsets(audio, sr, threshold=threshold)
        onsets = snap_to_grid(onsets, bpm, sr)
    else:
        onsets = detect_onsets(audio, sr, threshold=threshold)

    segments = slice_audio(audio, onsets, sr)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    source_stem = Path(input_path).stem

    result = SliceResult(
        source_file=input_path,
        sample_rate=sr,
        total_samples=total,
        total_duration_s=total / sr,
        onset_count=len(onsets),
    )

    for seg, chunk in segments:
        filename = f"{source_stem}_slice_{seg.index:03d}.wav"
        filepath = str(out_path / filename)
        write_audio(filepath, chunk, sr)
        seg.file_path = filepath
        result.segments.append(seg)

    _log.info("Sliced %s → %d segments", source_stem, len(result.segments))
    return result


def write_slice_manifest(result: SliceResult,
                         output_dir: str = "output/slices") -> str:
    """Write slice metadata to JSON."""
    manifest = {
        "generator": "DUBFORGE Sample Slicer",
        "source_file": result.source_file,
        "sample_rate": result.sample_rate,
        "total_samples": result.total_samples,
        "total_duration_s": result.total_duration_s,
        "onset_count": result.onset_count,
        "segments": [asdict(s) for s in result.segments],
    }
    path = Path(output_dir) / "slice_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# DEMO / MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Slice any wavetable files found in output/wavetables/."""
    wt_dir = Path("output/wavetables")
    out_dir = Path("output/slices")
    wav_files = list(wt_dir.glob("*.wav")) if wt_dir.exists() else []

    if not wav_files:
        print("  No WAV files found in output/wavetables/ — skipping slicer demo.")
        print("  (Run phi_core or growl_resampler first to generate wavetables.)")
        return

    for wav in wav_files:
        print(f"  Slicing {wav.name}...")
        result = slice_file(str(wav), str(out_dir), mode="fibonacci")
        write_slice_manifest(result, str(out_dir))
        for seg in result.segments:
            print(f"    → slice_{seg.index:03d}  "
                  f"{seg.duration_ms:.0f}ms  "
                  f"[{seg.start_time:.3f}s–{seg.end_time:.3f}s]")

    print(f"Sample Slicer complete — {len(wav_files)} files processed.")


if __name__ == "__main__":
    main()
