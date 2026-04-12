# pyright: basic
"""
DUBFORGE — Audio-to-MIDI Engine

ML-powered polyphonic audio → MIDI transcription.

Backends:
  1. Basic Pitch (Spotify) — best for polyphonic audio, uses lightweight CNN
  2. Native spectral peak tracker — zero-dependency fallback

Usage:
    from engine.audio_to_midi import transcribe, transcribe_file
    notes = transcribe_file("audio.wav")
    notes = transcribe(samples, sr=48000)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional: Basic Pitch (Spotify's polyphonic transcription)
# ---------------------------------------------------------------------------
try:
    from basic_pitch.inference import predict as _bp_predict  # type: ignore[import-unresolved]

    HAS_BASIC_PITCH = True
except ModuleNotFoundError:
    HAS_BASIC_PITCH = False

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MidiNote:
    """A single transcribed MIDI note event."""
    pitch: int          # MIDI note number 0-127
    start_s: float      # onset time in seconds
    end_s: float        # offset time in seconds
    velocity: float     # 0.0-1.0 normalized velocity
    confidence: float = 1.0  # transcription confidence

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    @property
    def pitch_hz(self) -> float:
        return 440.0 * (2 ** ((self.pitch - 69) / 12.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pitch": self.pitch,
            "pitch_hz": round(self.pitch_hz, 1),
            "start_s": round(self.start_s, 4),
            "end_s": round(self.end_s, 4),
            "duration_s": round(self.duration_s, 4),
            "velocity": round(self.velocity, 3),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class TranscriptionResult:
    """Complete audio-to-MIDI transcription result."""
    notes: list[MidiNote] = field(default_factory=list)
    backend: str = "native"  # "basic_pitch" | "native"
    duration_s: float = 0.0
    bpm_estimate: float = 0.0

    @property
    def note_count(self) -> int:
        return len(self.notes)

    @property
    def pitch_range(self) -> tuple[int, int]:
        if not self.notes:
            return (0, 0)
        pitches = [n.pitch for n in self.notes]
        return (min(pitches), max(pitches))

    def filter_range(self, low_midi: int = 0, high_midi: int = 127) -> TranscriptionResult:
        """Return a new result filtered to a MIDI pitch range."""
        filtered = [n for n in self.notes if low_midi <= n.pitch <= high_midi]
        return TranscriptionResult(
            notes=filtered,
            backend=self.backend,
            duration_s=self.duration_s,
            bpm_estimate=self.bpm_estimate,
        )

    def to_melody_info_notes(self) -> list[dict[str, Any]]:
        """Convert to MelodyInfo.notes format for reference_intake compatibility."""
        return [
            {
                "pitch_hz": round(n.pitch_hz, 1),
                "midi": n.pitch,
                "start_s": round(n.start_s, 3),
                "duration_s": round(n.duration_s, 3),
                "velocity": round(n.velocity, 3),
            }
            for n in self.notes
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_count": self.note_count,
            "backend": self.backend,
            "duration_s": round(self.duration_s, 2),
            "pitch_range": self.pitch_range,
            "notes": [n.to_dict() for n in self.notes],
        }


# ═══════════════════════════════════════════════════════════════════════════
# Basic Pitch backend
# ═══════════════════════════════════════════════════════════════════════════

def _transcribe_basic_pitch(audio_path: str | Path,
                            onset_threshold: float = 0.5,
                            frame_threshold: float = 0.3,
                            min_note_length_ms: float = 58.0,
                            min_freq: float | None = None,
                            max_freq: float | None = None,
                            ) -> TranscriptionResult:
    """
    Transcribe audio using Basic Pitch (Spotify's polyphonic AMT).

    Basic Pitch uses a lightweight CNN trained on Slakh2100 + MedleyDB.
    Works on full mixes and isolated stems. Best accuracy on stems.
    """
    if not HAS_BASIC_PITCH:
        raise RuntimeError("Basic Pitch not installed. pip install basic-pitch")

    audio_path = Path(audio_path)
    log.info("Basic Pitch: transcribing %s ...", audio_path.name)

    model_output, midi_data, note_events = _bp_predict(
        str(audio_path),
        onset_threshold=onset_threshold,
        frame_threshold=frame_threshold,
        minimum_note_length=min_note_length_ms,
        minimum_frequency=min_freq,
        maximum_frequency=max_freq,
    )

    # note_events: list of (start_time_s, end_time_s, pitch_midi, velocity, [confidence])
    notes: list[MidiNote] = []
    for event in note_events:
        start_s = float(event[0])
        end_s = float(event[1])
        pitch = int(event[2])
        vel = float(event[3]) / 127.0 if event[3] > 1.0 else float(event[3])
        conf = float(event[4]) if len(event) > 4 else 1.0

        if end_s <= start_s:
            continue
        notes.append(MidiNote(
            pitch=pitch,
            start_s=start_s,
            end_s=end_s,
            velocity=min(1.0, max(0.0, vel)),
            confidence=conf,
        ))

    notes.sort(key=lambda n: (n.start_s, n.pitch))
    duration = notes[-1].end_s if notes else 0.0

    log.info("Basic Pitch: found %d notes over %.1fs", len(notes), duration)
    return TranscriptionResult(
        notes=notes,
        backend="basic_pitch",
        duration_s=duration,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Native spectral peak tracker (fallback)
# ═══════════════════════════════════════════════════════════════════════════

def _transcribe_native(samples: np.ndarray, sr: int,
                       min_freq: float = 30.0,
                       max_freq: float = 12000.0,
                       min_rms: float = 0.005,
                       ) -> TranscriptionResult:
    """
    Transcribe audio using spectral peak tracking.

    Upgraded from the original _extract_melody_contour:
    - Multi-peak detection (polyphonic-aware, top N peaks)
    - Parabolic interpolation for sub-bin frequency accuracy
    - Onset detection for note boundary refinement
    """
    hop = sr // 16  # ~16 frames per second for higher resolution
    fft_size = 4096
    n_frames = len(samples) // hop

    # Onset envelope for note boundary detection
    prev_spectrum = None
    onset_env: list[float] = []

    # Per-frame dominant frequencies
    frame_data: list[list[tuple[float, float, float]]] = []  # [(freq, mag, rms), ...]

    for i in range(n_frames):
        start = i * hop
        end = min(start + fft_size, len(samples))
        if end - start < 256:
            frame_data.append([])
            onset_env.append(0.0)
            continue

        chunk = samples[start:end]
        window = np.hanning(len(chunk))
        windowed = chunk * window
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1.0 / sr)
        rms = float(np.sqrt(np.mean(chunk ** 2)))

        # Onset: spectral flux
        if prev_spectrum is not None and len(prev_spectrum) == len(spectrum):
            flux = float(np.sum(np.maximum(spectrum - prev_spectrum, 0)))
            onset_env.append(flux)
        else:
            onset_env.append(0.0)
        prev_spectrum = spectrum.copy()

        if rms < min_rms:
            frame_data.append([])
            continue

        # Mask to frequency range
        mask = (freqs >= min_freq) & (freqs <= max_freq)
        masked = spectrum.copy()
        masked[~mask] = 0

        # Find top peaks (local maxima)
        peaks: list[tuple[float, float]] = []
        for j in range(2, len(masked) - 2):
            if (masked[j] > masked[j - 1] and masked[j] > masked[j + 1]
                    and masked[j] > masked[j - 2] and masked[j] > masked[j + 2]):
                # Parabolic interpolation for better frequency resolution
                alpha = float(masked[j - 1])
                beta = float(masked[j])
                gamma = float(masked[j + 1])
                denom = alpha - 2 * beta + gamma
                if abs(denom) > 1e-10:
                    p = 0.5 * (alpha - gamma) / denom
                else:
                    p = 0.0
                true_freq = float(freqs[j]) + p * (float(freqs[1]) if len(freqs) > 1 else 0)
                true_mag = beta - 0.25 * (alpha - gamma) * p
                if true_freq >= min_freq and true_freq <= max_freq:
                    peaks.append((true_freq, true_mag))

        # Take top 6 peaks by magnitude
        peaks.sort(key=lambda x: x[1], reverse=True)
        frame_data.append([(f, m, rms) for f, m in peaks[:6]])  # type: ignore[misc]

    # Convert peaks to notes via tracking
    notes: list[MidiNote] = []
    active: dict[int, dict] = {}  # midi_note → tracking state

    # Adaptive onset threshold
    onset_arr = np.array(onset_env)
    onset_median = float(np.median(onset_arr[onset_arr > 0])) if np.any(onset_arr > 0) else 1.0
    onset_threshold = onset_median * 2.0

    for i, peaks in enumerate(frame_data):  # type: ignore[assignment]
        time_s = i * hop / sr
        current_pitches: set[int] = set()

        for freq, mag, rms in peaks:  # type: ignore[misc]
            if freq <= 0:
                continue
            midi = int(round(12 * math.log2(freq / 440.0) + 69))
            midi = max(0, min(127, midi))
            current_pitches.add(midi)
            vel = min(1.0, mag / max(100.0, onset_median * 5))

            if midi not in active:
                # New note onset
                active[midi] = {
                    "start_s": time_s,
                    "velocity": vel,
                    "mag_sum": mag,
                    "frame_count": 1,
                }
            else:
                # Continue existing note
                active[midi]["mag_sum"] += mag
                active[midi]["frame_count"] += 1
                active[midi]["velocity"] = max(active[midi]["velocity"], vel)

        # Check for note-offs (pitches no longer active)
        ended = [m for m in active if m not in current_pitches]
        for midi in ended:
            state = active.pop(midi)
            dur = time_s - state["start_s"]
            if dur >= 0.03 and state["frame_count"] >= 2:  # min 30ms, 2+ frames
                notes.append(MidiNote(
                    pitch=midi,
                    start_s=state["start_s"],
                    end_s=time_s,
                    velocity=min(1.0, state["velocity"]),
                ))

        # Force note reset on strong onsets (re-attacks)
        if i < len(onset_env) and onset_env[i] > onset_threshold:
            restart = [m for m in active if m in current_pitches]
            for midi in restart:
                state = active[midi]
                if time_s - state["start_s"] > 0.05:  # don't retrigger too fast
                    dur = time_s - state["start_s"]
                    if dur >= 0.03:
                        notes.append(MidiNote(
                            pitch=midi,
                            start_s=state["start_s"],
                            end_s=time_s,
                            velocity=min(1.0, state["velocity"]),
                        ))
                    active[midi] = {
                        "start_s": time_s,
                        "velocity": min(1.0, state["velocity"]),
                        "mag_sum": 0.0,
                        "frame_count": 1,
                    }

    # Flush remaining active notes
    final_time = len(samples) / sr
    for midi, state in active.items():
        dur = final_time - state["start_s"]
        if dur >= 0.03:
            notes.append(MidiNote(
                pitch=midi,
                start_s=state["start_s"],
                end_s=final_time,
                velocity=min(1.0, state["velocity"]),
            ))

    notes.sort(key=lambda n: (n.start_s, n.pitch))
    log.info("Native transcription: found %d notes", len(notes))

    return TranscriptionResult(
        notes=notes,
        backend="native",
        duration_s=float(len(samples) / sr),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def transcribe_file(audio_path: str | Path,
                    min_freq: float | None = None,
                    max_freq: float | None = None,
                    prefer_ml: bool = True,
                    ) -> TranscriptionResult:
    """
    Transcribe audio file to MIDI notes.

    Uses Basic Pitch if available, otherwise falls back to native.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if prefer_ml and HAS_BASIC_PITCH:
        try:
            return _transcribe_basic_pitch(
                audio_path,
                min_freq=min_freq,
                max_freq=max_freq,
            )
        except Exception as e:
            log.warning("Basic Pitch failed (%s), falling back to native", e)

    # Native fallback — load WAV
    import struct
    import wave

    with wave.open(str(audio_path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64) / 32768.0
    elif sampwidth == 4:
        fmt = f"<{n_frames * n_channels}i"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64) / 2147483648.0
    else:
        samples = np.zeros(n_frames, dtype=np.float64)

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return transcribe(
        samples, sr,
        min_freq=min_freq or 30.0,
        max_freq=max_freq or 12000.0,
    )


def transcribe(samples: np.ndarray, sr: int = 48000,
               min_freq: float = 30.0,
               max_freq: float = 12000.0,
               ) -> TranscriptionResult:
    """
    Transcribe audio samples to MIDI notes (native backend only).

    For Basic Pitch, use transcribe_file() with a file path.
    """
    return _transcribe_native(samples, sr, min_freq=min_freq, max_freq=max_freq)


def transcribe_melody(samples: np.ndarray, sr: int = 48000,
                      bpm: float = 140.0) -> TranscriptionResult:
    """
    Transcribe the melody line (200-6000 Hz range).

    Drop-in replacement for reference_intake._extract_melody_contour().
    """
    return transcribe(samples, sr, min_freq=200.0, max_freq=6000.0)


def transcribe_bass(samples: np.ndarray, sr: int = 48000) -> TranscriptionResult:
    """Transcribe bass content (30-500 Hz range)."""
    return transcribe(samples, sr, min_freq=30.0, max_freq=500.0)
