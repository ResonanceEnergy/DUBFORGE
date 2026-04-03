"""DUBFORGE — Vocal TTS Engine.

Neural TTS singing synthesis using edge-tts (Microsoft Edge Neural Voices).
Pitch-corrected via RubberBand R3 (--fine --formant).

Exports:
  - render_singing_vocal_stem_v8(bpm, total_samples) → np.ndarray (mono)
  - SINGING_LYRICS: dict mapping section_bar → list of line tuples
  - generate_line(text, rate, pitch) → np.ndarray
  - _compute_tts_pitch_for_target(midi) → str
  - _detect_pitch_hz(audio) → float
  - _hz_to_midi(hz) → float
  - _rubberband_pitch_and_time(audio, semitones, time_ratio) → np.ndarray
"""
from __future__ import annotations

import asyncio
import math
import os
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from engine.accel import fft, ifft

# ── Constants ────────────────────────────────────────────────────

try:
    from engine.phi_core import SAMPLE_RATE
except ImportError:
    SAMPLE_RATE = 48000

TTS_VOICE = "en-US-AriaNeural"
TTS_RATE = "+0%"
TTS_PITCH = "+0Hz"


# ═══════════════════════════════════════════════════════════════════
# Lyrics mapping: section_start_bar → [(bar_offset, bar_count, text, rate, target_notes)]
# target_notes = list of MIDI note numbers the vocal should hit
# ═══════════════════════════════════════════════════════════════════

SINGING_LYRICS: dict[int, list[tuple]] = {
    # Verse 1 (build, bars 16-23)
    16: [
        (0, 2, "I wrote the words but never sent them", "+0%", [62, 60, 58]),
        (2, 2, "Kept them locked inside my chest", "+0%", [58, 60, 62]),
        (4, 2, "Every night I rehearsed the ending", "-5%", [65, 63, 62]),
        (6, 2, "But the curtain never fell", "-5%", [62, 60, 58]),
    ],
    # Pre-Chorus (bars 24-31 → mapped into build bars)
    24: [
        (0, 2, "And I'm sorry", "+0%", [65, 63]),
        (2, 2, "For every silence that screamed your name", "+0%", [67, 65, 63, 62]),
        (4, 2, "I'm still burning", "+5%", [69, 67]),
        (6, 2, "In the fire of what we became", "+5%", [67, 65, 63]),
    ],
    # Chorus 1 (bars 40-55)
    40: [
        (0, 2, "This is the apology that never came", "+0%", [69, 67, 65, 63]),
        (2, 2, "Words dissolving in the rain", "+0%", [65, 63, 62, 60]),
        (4, 2, "I held it in until it broke me", "+5%", [67, 69, 70, 69]),
        (6, 2, "Now the echoes know my name", "+5%", [69, 67, 65]),
        (8, 2, "This is the apology that never came", "+0%", [69, 67, 65, 63]),
        (10, 2, "Burning letters in the flame", "+0%", [65, 63, 62, 60]),
        (12, 2, "Every word I should have spoken", "+5%", [67, 69, 70, 69]),
        (14, 2, "Echoes fading just the same", "+5%", [67, 65, 63]),
    ],
    # Break / Verse 2 (bars 64-79)
    64: [
        (0, 2, "The midnight hour keeps replaying", "+0%", [62, 60, 58]),
        (2, 2, "Scenes I wrote but never staged", "+0%", [58, 60, 62]),
        (4, 2, "Your silhouette against the doorway", "-5%", [65, 63, 62]),
        (6, 2, "Frozen in a bygone age", "-5%", [62, 60, 58]),
        (8, 2, "And I'm drowning", "+0%", [65, 63]),
        (10, 2, "In the ocean of the things I couldn't say", "+0%", [67, 65, 63, 62]),
        (12, 2, "Still reaching", "+5%", [69, 67]),
        (14, 2, "For a shore that's washed away", "+5%", [67, 65, 63]),
    ],
    # Chorus 2 (bars 96-111)
    96: [
        (0, 2, "This is the apology that never came", "+0%", [69, 67, 65, 63]),
        (2, 2, "Screaming into silent rain", "+0%", [65, 63, 62, 60]),
        (4, 2, "The weight of everything unspoken", "+5%", [67, 69, 70, 69]),
        (6, 2, "Crushing down like tidal waves", "+5%", [69, 67, 65]),
        (8, 2, "This is the apology that never came", "+0%", [69, 67, 65, 63]),
        (10, 2, "I'll carry it until I break", "+0%", [65, 63, 62, 60]),
        (12, 2, "Every wound that time won't cover", "+5%", [67, 69, 70, 69]),
        (14, 2, "Bleeds the truth you couldn't take", "+5%", [67, 65, 63]),
    ],
    # Outro (bars 112-127)
    112: [
        (0, 2, "The apology that never came", "-10%", [62, 60, 58]),
        (4, 4, "Still echoing...", "-15%", [58, 55]),
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════

def _hz_to_midi(hz: float) -> float:
    """Convert frequency in Hz to MIDI note number."""
    if hz <= 0:
        return 0.0
    return 69.0 + 12.0 * math.log2(hz / 440.0)


def _midi_to_hz(midi: float) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def _compute_tts_pitch_for_target(target_midi: float) -> str:
    """Compute edge-tts pitch parameter to aim for target MIDI note.

    Edge TTS pitch format: "{sign}{value}Hz" e.g. "+50Hz" or "-30Hz".
    The neutral speaking pitch for AriaNeural ≈ 200Hz (MIDI ~55).
    """
    neutral_hz = 200.0  # approximate AriaNeural neutral pitch
    neutral_midi = _hz_to_midi(neutral_hz)
    target_hz = _midi_to_hz(target_midi)
    delta_hz = target_hz - neutral_hz
    delta_hz = max(-150, min(150, delta_hz))  # clamp to safe range
    sign = "+" if delta_hz >= 0 else ""
    return f"{sign}{int(delta_hz)}Hz"


def _detect_pitch_hz(audio: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """Simple autocorrelation pitch detector."""
    if len(audio) < 512:
        return 0.0

    # Use a central window
    center = len(audio) // 2
    window_size = min(4096, len(audio))
    start = max(0, center - window_size // 2)
    segment = audio[start:start + window_size].astype(np.float64)

    # Normalize
    segment = segment - np.mean(segment)
    if np.max(np.abs(segment)) < 1e-6:
        return 0.0

    # Autocorrelation via FFT
    n = len(segment)
    fft = fft(segment, n=2*n)
    autocorr = ifft(fft * np.conj(fft))[:n]
    autocorr = autocorr / (autocorr[0] + 1e-12)

    # Find first peak after lag corresponding to max plausible freq
    min_lag = int(sr / 800)  # 800Hz max
    max_lag = int(sr / 50)   # 50Hz min

    if max_lag >= n:
        max_lag = n - 1
    if min_lag >= max_lag:
        return 0.0

    search = autocorr[min_lag:max_lag]
    if len(search) == 0:
        return 0.0

    peak_idx = np.argmax(search) + min_lag
    if autocorr[peak_idx] < 0.2:
        return 0.0

    return float(sr / peak_idx)


def _read_wav(path: str) -> np.ndarray:
    """Read a WAV file as float64 mono."""
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        raw = wf.readframes(n)
        sw = wf.getsampwidth()
        ch = wf.getnchannels()
        sr_file = wf.getframerate()

    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sw == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) / 128.0 - 1.0
    else:
        # 24-bit
        arr = []
        for i in range(0, len(raw), 3):
            val = int.from_bytes(raw[i:i+3], "little", signed=True)
            arr.append(val / (2**23))
        data = np.array(arr, dtype=np.float64)

    if ch == 2:
        data = (data[0::2] + data[1::2]) * 0.5

    # Resample if needed
    if sr_file != SAMPLE_RATE and len(data) > 0:
        try:
            from scipy.signal import resample
            new_len = int(len(data) * SAMPLE_RATE / sr_file)
            data = resample(data, new_len)
        except ImportError:
            pass

    return data


def _write_wav_temp(audio: np.ndarray, sr: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(audio, dtype=np.float64) if not isinstance(audio, np.ndarray) else audio
    write_wav(str(audio), _s, sample_rate=sr)
    return str(audio)




def _rubberband_pitch_and_time(audio: np.ndarray, semitones: float,
                                time_ratio: float,
                                sr: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch-shift and time-stretch using RubberBand CLI.

    Falls back to scipy resampling if rubberband is not available.
    """
    if len(audio) == 0:
        return audio

    in_path = _write_wav_temp(audio, sr)
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        cmd = [
            "rubberband",
            "--fine", "--formant",
            "--pitch", str(semitones),
            "--time", str(time_ratio),
            in_path, out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode == 0 and os.path.exists(out_path):
            return _read_wav(out_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    finally:
        for p in (in_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    # Fallback: resampling-based pitch shift (no time stretch)
    if abs(semitones) > 0.01:
        try:
            from scipy.signal import resample
            factor = 2.0 ** (semitones / 12.0)
            new_len = int(len(audio) / factor)
            if new_len > 0:
                return resample(audio, new_len)
        except ImportError:
            pass

    return audio


def generate_line(text: str, rate: str = "+0%",
                  pitch: str = "+0Hz") -> np.ndarray:
    """Generate a single TTS line using edge-tts.

    Returns mono float64 audio at SAMPLE_RATE.
    """
    try:
        import edge_tts
    except ImportError:
        # Return silence if edge-tts not installed
        return np.zeros(SAMPLE_RATE, dtype=np.float64)

    fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        # Run edge-tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=TTS_VOICE,
            rate=rate,
            pitch=pitch,
        )
        # edge-tts is async, so we need an event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(communicate.save(mp3_path))
        finally:
            loop.close()

        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
            return np.zeros(SAMPLE_RATE, dtype=np.float64)

        # Convert MP3 → WAV using ffmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", str(SAMPLE_RATE),
             "-ac", "1", "-sample_fmt", "s16", wav_path],
            capture_output=True, timeout=30,
        )

        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
            return _read_wav(wav_path)

    except Exception:
        pass
    finally:
        for p in (mp3_path, wav_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    return np.zeros(SAMPLE_RATE, dtype=np.float64)


# ═══════════════════════════════════════════════════════════════════
# Main render function
# ═══════════════════════════════════════════════════════════════════

def render_singing_vocal_stem_v8(bpm: float, total_samples: int) -> np.ndarray:
    """Render the full singing vocal stem.

    Renders all lyric lines from SINGING_LYRICS, pitch-corrects via
    RubberBand, and places them at the correct bar positions.

    Returns mono float64 array of length total_samples.
    """
    bar_dur = 4 * 60.0 / bpm
    bar_samps = int(bar_dur * SAMPLE_RATE)

    output = np.zeros(total_samples, dtype=np.float64)

    for section_bar, lines in SINGING_LYRICS.items():
        for bar_off, bar_count, text, rate, target_notes in lines:
            offset = (section_bar + bar_off) * bar_samps
            if offset >= total_samples:
                continue

            target_samps = bar_count * bar_samps

            # Average target MIDI note for this line
            avg_target = sum(target_notes) / len(target_notes)
            tts_pitch = _compute_tts_pitch_for_target(avg_target)

            try:
                raw = generate_line(text, rate=rate, pitch=tts_pitch)
                if len(raw) == 0:
                    continue

                # Detect actual pitch
                detected_hz = _detect_pitch_hz(raw)
                if detected_hz <= 0:
                    tts_offset = float(tts_pitch.replace("Hz", "").replace("+", ""))
                    detected_hz = 200.0 + tts_offset
                    detected_hz = max(80.0, detected_hz)

                detected_midi = _hz_to_midi(detected_hz)

                # Remaining pitch correction
                remaining_semi = avg_target - detected_midi
                remaining_semi = max(-12.0, min(12.0, remaining_semi))

                # Time ratio to fit target duration
                time_ratio = target_samps / len(raw)
                time_ratio = max(0.5, min(2.0, time_ratio))

                # Apply pitch + time correction
                sung = _rubberband_pitch_and_time(raw, remaining_semi, time_ratio)

                # Trim/pad to target length
                if len(sung) >= target_samps:
                    sung = sung[:target_samps]
                else:
                    padded = np.zeros(target_samps, dtype=np.float64)
                    padded[:len(sung)] = sung
                    sung = padded

                # Fade in/out (10ms)
                fade = int(0.010 * SAMPLE_RATE)
                if len(sung) > 2 * fade:
                    sung[:fade] *= np.linspace(0, 1, fade)
                    sung[-fade:] *= np.linspace(1, 0, fade)

                end = min(offset + len(sung), total_samples)
                output[offset:end] += sung[:end - offset]

            except Exception as e:
                print(f"    ⚠ Vocal line failed: '{text[:30]}': {e}")

    return output
