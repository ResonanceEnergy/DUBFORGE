# pyright: basic
"""
DUBFORGE — Beat & Onset Tracker

Beat/downbeat/onset detection for dubstep production analysis.

Backends:
  1. madmom (TU Wien) — state-of-the-art RNN+DBN beat tracking
  2. Native onset detector — zero-dependency fallback using spectral flux

Usage:
    from engine.beat_tracker import track_beats, detect_onsets
    result = track_beats("audio.wav")
    print(result.beats)      # [0.43, 0.86, 1.28, ...]
    print(result.downbeats)  # [0.43, 2.14, 3.85, ...]
    print(result.bpm)        # 140.0
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional: madmom (beat/onset tracking)
# ---------------------------------------------------------------------------
try:
    from madmom.features.beats import (  # type: ignore[import-unresolved]
        DBNBeatTrackingProcessor as _DBNBeatProc,
    )
    from madmom.features.beats import (  # type: ignore[import-unresolved]
        RNNBeatProcessor as _RNNBeatProc,
    )
    from madmom.features.downbeats import (  # type: ignore[import-unresolved]
        DBNDownBeatTrackingProcessor as _DBNDownbeatProc,
    )
    from madmom.features.downbeats import (  # type: ignore[import-unresolved]
        RNNDownBeatProcessor as _RNNDownbeatProc,
    )
    from madmom.features.onsets import (  # type: ignore[import-unresolved]
        OnsetPeakPickingProcessor as _OnsetPeakProc,
    )
    from madmom.features.onsets import (  # type: ignore[import-unresolved]
        RNNOnsetProcessor as _RNNOnsetProc,
    )

    HAS_MADMOM = True
except ModuleNotFoundError:
    HAS_MADMOM = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BeatGrid:
    """Beat tracking result with beat/downbeat positions."""
    beats: list[float] = field(default_factory=list)        # beat times in seconds
    downbeats: list[float] = field(default_factory=list)     # downbeat (bar start) times
    bpm: float = 0.0
    time_signature: tuple[int, int] = (4, 4)
    backend: str = "native"  # "madmom" | "native"
    confidence: float = 0.0

    @property
    def beat_count(self) -> int:
        return len(self.beats)

    @property
    def bar_count(self) -> int:
        return len(self.downbeats)

    def beats_in_range(self, start_s: float, end_s: float) -> list[float]:
        """Get beat times within a time range."""
        return [b for b in self.beats if start_s <= b <= end_s]

    def quantize_time(self, time_s: float, resolution: float = 0.25) -> float:
        """
        Quantize a time to the nearest beat grid position.

        resolution: in beats (0.25 = 16th note, 0.5 = 8th, 1.0 = quarter)
        """
        if not self.beats or self.bpm <= 0:
            return time_s

        beat_dur = 60.0 / self.bpm
        grid_dur = beat_dur * resolution
        return round(time_s / grid_dur) * grid_dur

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_count": self.beat_count,
            "bar_count": self.bar_count,
            "bpm": round(self.bpm, 2),
            "time_signature": list(self.time_signature),
            "backend": self.backend,
            "confidence": round(self.confidence, 3),
            "beats": [round(b, 4) for b in self.beats[:32]],
            "downbeats": [round(d, 4) for d in self.downbeats[:16]],
        }


@dataclass
class OnsetResult:
    """Onset detection result."""
    onsets: list[float] = field(default_factory=list)  # onset times in seconds
    strengths: list[float] = field(default_factory=list)  # onset strengths
    backend: str = "native"

    @property
    def count(self) -> int:
        return len(self.onsets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "backend": self.backend,
            "onsets": [round(o, 4) for o in self.onsets[:64]],
        }


# ═══════════════════════════════════════════════════════════════════════════
# madmom backend
# ═══════════════════════════════════════════════════════════════════════════

def _track_beats_madmom(audio_path: str | Path,
                        fps: int = 100) -> BeatGrid:
    """
    Track beats using madmom's RNN + DBN pipeline.

    madmom uses:
    - RNNBeatProcessor: bidirectional LSTM for beat activation
    - DBNBeatTrackingProcessor: dynamic Bayesian network for sequence decoding
    """
    if not HAS_MADMOM:
        raise RuntimeError("madmom not installed. pip install madmom")

    audio_path = str(audio_path)
    log.info("madmom: tracking beats in %s ...", Path(audio_path).name)

    # Beat tracking
    beat_proc = _DBNBeatProc(fps=fps)
    beat_act = _RNNBeatProc()(audio_path)
    beats = beat_proc(beat_act).tolist()

    # Downbeat tracking
    try:
        downbeat_proc = _DBNDownbeatProc(
            beats_per_bar=[3, 4],  # handle both 3/4 and 4/4
            fps=fps,
        )
        downbeat_act = _RNNDownbeatProc()(audio_path)
        downbeat_result = downbeat_proc(downbeat_act)
        # Result: [(time, beat_position), ...] where beat_position=1 is downbeat
        downbeats = [float(row[0]) for row in downbeat_result if int(row[1]) == 1]
    except Exception as e:
        log.warning("madmom downbeat detection failed: %s", e)
        downbeats = []

    # Estimate BPM from beat intervals
    if len(beats) >= 2:
        intervals = np.diff(beats)
        median_interval = float(np.median(intervals))
        bpm = 60.0 / median_interval if median_interval > 0 else 0.0
    else:
        bpm = 0.0

    # Confidence: how consistent are the beat intervals?
    if len(beats) >= 4:
        intervals = np.diff(beats)
        cv = float(np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else 1.0
        confidence = max(0.0, 1.0 - cv)
    else:
        confidence = 0.0

    log.info("madmom: %d beats, %d downbeats, %.1f BPM (conf=%.2f)",
             len(beats), len(downbeats), bpm, confidence)

    return BeatGrid(
        beats=beats,
        downbeats=downbeats,
        bpm=bpm,
        backend="madmom",
        confidence=confidence,
    )


def _detect_onsets_madmom(audio_path: str | Path) -> OnsetResult:
    """Detect onsets using madmom's RNN onset detector."""
    if not HAS_MADMOM:
        raise RuntimeError("madmom not installed. pip install madmom")

    audio_path = str(audio_path)
    log.info("madmom: detecting onsets in %s ...", Path(audio_path).name)

    act = _RNNOnsetProc()(audio_path)
    picker = _OnsetPeakProc(threshold=0.3, fps=100)
    onsets = picker(act).tolist()

    # Strengths from activation
    strengths = []
    for onset_time in onsets:
        idx = int(onset_time * 100)  # fps=100
        if 0 <= idx < len(act):
            strengths.append(float(act[idx]))
        else:
            strengths.append(0.5)

    log.info("madmom: found %d onsets", len(onsets))
    return OnsetResult(onsets=onsets, strengths=strengths, backend="madmom")


# ═══════════════════════════════════════════════════════════════════════════
# Native spectral flux backend (fallback)
# ═══════════════════════════════════════════════════════════════════════════

def _track_beats_native(samples: np.ndarray, sr: int) -> BeatGrid:
    """
    Track beats using spectral-flux onset detection + autocorrelation BPM.

    Not as accurate as madmom for complex dubstep, but decent for
    straightforward 4/4 with clear kicks.
    """
    hop = sr // 100  # 100 fps
    fft_size = 2048
    n_frames = len(samples) // hop

    # Compute onset strength (spectral flux)
    onset_env: list[float] = []
    prev_spectrum = np.zeros(fft_size // 2 + 1)

    for i in range(n_frames):
        start = i * hop
        end = min(start + fft_size, len(samples))
        if end - start < 256:
            onset_env.append(0.0)
            continue
        chunk = samples[start:end]
        if len(chunk) < fft_size:
            chunk = np.pad(chunk, (0, fft_size - len(chunk)))
        window = np.hanning(fft_size)
        spectrum = np.abs(np.fft.rfft(chunk * window))

        # Half-wave rectified spectral flux
        flux = float(np.sum(np.maximum(spectrum - prev_spectrum, 0)))
        onset_env.append(flux)
        prev_spectrum = spectrum

    onset_arr = np.array(onset_env)

    # Normalize
    mx = onset_arr.max()
    if mx > 0:
        onset_arr = onset_arr / mx

    # Autocorrelation for tempo estimation
    # Search BPM range 60-200
    min_lag = int(100 * 60 / 200)  # fps * 60 / max_bpm
    max_lag = int(100 * 60 / 60)   # fps * 60 / min_bpm
    max_lag = min(max_lag, len(onset_arr) // 2)

    if max_lag > min_lag:
        autocorr = np.correlate(onset_arr, onset_arr, mode="full")
        center = len(autocorr) // 2
        ac = autocorr[center + min_lag:center + max_lag]
        if len(ac) > 0:
            best_lag = int(np.argmax(ac)) + min_lag
            bpm = 60.0 * 100 / best_lag  # fps=100
        else:
            bpm = 140.0
    else:
        bpm = 140.0

    # Generate beat grid from BPM
    beat_interval = 60.0 / bpm
    beats: list[float] = []

    # Find first strong onset as beat 1
    threshold = float(np.percentile(onset_arr[onset_arr > 0], 75)) if np.any(onset_arr > 0) else 0.5
    first_beat = 0.0
    for i, val in enumerate(onset_arr):
        if val > threshold:
            first_beat = i / 100.0  # fps=100
            break

    # Fill beat grid
    t = first_beat
    duration = len(samples) / sr
    while t < duration:
        beats.append(round(t, 4))
        t += beat_interval

    # Downbeats every 4 beats
    downbeats = beats[::4]

    # Confidence from autocorrelation peak strength
    if max_lag > min_lag and len(ac) > 0:
        peak_val = float(ac.max())
        mean_val = float(ac.mean())
        confidence = min(1.0, peak_val / (mean_val + 1e-10) / 10.0)
    else:
        confidence = 0.3

    log.info("Native beat tracker: %.1f BPM, %d beats (conf=%.2f)", bpm, len(beats), confidence)

    return BeatGrid(
        beats=beats,
        downbeats=downbeats,
        bpm=round(bpm, 1),
        backend="native",
        confidence=confidence,
    )


def _detect_onsets_native(samples: np.ndarray, sr: int,
                          threshold: float = 0.3) -> OnsetResult:
    """Detect onsets using spectral flux peak picking."""
    hop = sr // 100
    fft_size = 2048
    n_frames = len(samples) // hop

    onset_env: list[float] = []
    prev_spectrum = np.zeros(fft_size // 2 + 1)

    for i in range(n_frames):
        start = i * hop
        end = min(start + fft_size, len(samples))
        if end - start < 256:
            onset_env.append(0.0)
            continue
        chunk = samples[start:end]
        if len(chunk) < fft_size:
            chunk = np.pad(chunk, (0, fft_size - len(chunk)))
        spectrum = np.abs(np.fft.rfft(chunk * np.hanning(fft_size)))
        flux = float(np.sum(np.maximum(spectrum - prev_spectrum, 0)))
        onset_env.append(flux)
        prev_spectrum = spectrum

    # Normalize
    onset_arr = np.array(onset_env)
    mx = onset_arr.max()
    if mx > 0:
        onset_arr /= mx

    # Peak picking with adaptive threshold
    median_filt = np.convolve(onset_arr, np.ones(7) / 7, mode="same")
    onsets: list[float] = []
    strengths: list[float] = []

    for i in range(2, len(onset_arr) - 2):
        if (onset_arr[i] > onset_arr[i - 1]
                and onset_arr[i] > onset_arr[i + 1]
                and onset_arr[i] > median_filt[i] + threshold
                and onset_arr[i] > threshold):
            onsets.append(round(i / 100.0, 4))
            strengths.append(round(float(onset_arr[i]), 3))

    return OnsetResult(onsets=onsets, strengths=strengths, backend="native")


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def track_beats(audio_path: str | Path | None = None,
                samples: np.ndarray | None = None,
                sr: int = 48000,
                prefer_ml: bool = True,
                ) -> BeatGrid:
    """
    Track beats in audio.

    Uses madmom if available, falls back to native spectral method.

    Args:
        audio_path: Path to audio file (needed for madmom).
        samples: Audio samples as numpy array (for native fallback).
        sr: Sample rate (for native).
        prefer_ml: If True, prefer madmom when available.

    Returns:
        BeatGrid with beat/downbeat positions and BPM.
    """
    if prefer_ml and HAS_MADMOM and audio_path is not None:
        try:
            return _track_beats_madmom(audio_path)
        except Exception as e:
            log.warning("madmom beat tracking failed (%s), falling back to native", e)

    if samples is not None:
        return _track_beats_native(samples, sr)

    # Load from file for native
    if audio_path is not None:
        import struct
        import wave
        with wave.open(str(audio_path), "rb") as wf:
            sr = wf.getframerate()
            n = wf.getnframes()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(n)
        if sw == 2:
            arr = np.array(struct.unpack(f"<{n * ch}h", raw), dtype=np.float64) / 32768.0
        elif sw == 4:
            arr = np.array(struct.unpack(f"<{n * ch}i", raw), dtype=np.float64) / 2147483648.0
        else:
            arr = np.zeros(n, dtype=np.float64)
        if ch > 1:
            arr = arr.reshape(-1, ch).mean(axis=1)
        return _track_beats_native(arr, sr)

    return BeatGrid()


def detect_onsets(audio_path: str | Path | None = None,
                  samples: np.ndarray | None = None,
                  sr: int = 48000,
                  prefer_ml: bool = True,
                  ) -> OnsetResult:
    """
    Detect onsets in audio.

    Uses madmom if available, falls back to spectral flux.
    """
    if prefer_ml and HAS_MADMOM and audio_path is not None:
        try:
            return _detect_onsets_madmom(audio_path)
        except Exception as e:
            log.warning("madmom onset detection failed (%s), falling back to native", e)

    if samples is not None:
        return _detect_onsets_native(samples, sr)

    if audio_path is not None:
        import struct
        import wave
        with wave.open(str(audio_path), "rb") as wf:
            sr = wf.getframerate()
            n = wf.getnframes()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(n)
        if sw == 2:
            arr = np.array(struct.unpack(f"<{n * ch}h", raw), dtype=np.float64) / 32768.0
        elif sw == 4:
            arr = np.array(struct.unpack(f"<{n * ch}i", raw), dtype=np.float64) / 2147483648.0
        else:
            arr = np.zeros(n, dtype=np.float64)
        if ch > 1:
            arr = arr.reshape(-1, ch).mean(axis=1)
        return _detect_onsets_native(arr, sr)

    return OnsetResult()
