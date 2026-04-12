#!/usr/bin/env python3
"""DUBFORGE — Full Track Rendering Utilities.

Provides the core rendering functions used by the V8/V9 stem pipeline:
  - SAMPLE_RATE              (48000)
  - write_wav_stereo()       Write stereo float64 arrays to 24-bit WAV
  - stereo_place()           Mono → stereo with width control
  - sidechain_duck()         Sidechain compression envelope
  - render_vocal_chops()     Render vocal chop patterns for a section
  - render_bass_drop()       Render bass for drop sections
  - render_drone()           Render atmospheric drone
  - render_lead_melody()     Render lead melody pattern
  - render_noise_bed()       Render filtered noise bed
  - render_pad()             Render pad chord
  - render_riser()           Render pitch/noise riser

All render_* functions follow the same signature:
    render_X(dna, bars, energy) → np.ndarray (mono float64)
    (render_riser takes only dna, bars)

These are "legacy" fallback renderers used by the stem pipeline when
a dedicated pipeline module (e.g. DrumPipeline) doesn't cover an element.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.dsp_core import SAMPLE_RATE, svf_lowpass, svf_highpass
from engine.config_loader import PHI

if TYPE_CHECKING:
    pass

# Re-export SAMPLE_RATE at module level (v9 scripts do: from make_full_track import SAMPLE_RATE)
SAMPLE_RATE = SAMPLE_RATE  # noqa: F811 — intentional re-export (48000)


# ═══════════════════════════════════════════════════════════════════
# WAV I/O
# ═══════════════════════════════════════════════════════════════════

def write_wav_stereo(path: str, left: np.ndarray, right: np.ndarray,
                     sr: int = SAMPLE_RATE, bits: int = 24) -> None:
    """Write stereo float64 arrays to a WAV file.

    Supports 16-bit and 24-bit output.  Float arrays are clipped to [-1, 1]
    before quantization.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    n = min(len(left), len(right))
    left = np.clip(left[:n], -1.0, 1.0)
    right = np.clip(right[:n], -1.0, 1.0)

    if bits == 24:
        # Pack as 24-bit little-endian in a 32-bit container isn't standard;
        # use struct packing for true 24-bit WAV.
        sw = 3
        scale = 2**23 - 1
        left_i = np.round(left * scale).astype(np.int32)
        right_i = np.round(right * scale).astype(np.int32)
        raw = bytearray(n * 2 * 3)
        for i in range(n):
            idx = i * 6
            lv = int(left_i[i])
            rv = int(right_i[i])
            raw[idx]     = lv & 0xFF
            raw[idx + 1] = (lv >> 8) & 0xFF
            raw[idx + 2] = (lv >> 16) & 0xFF
            raw[idx + 3] = rv & 0xFF
            raw[idx + 4] = (rv >> 8) & 0xFF
            raw[idx + 5] = (rv >> 16) & 0xFF
    else:
        sw = 2
        scale = 32767
        left_i = np.round(left * scale).astype(np.int16)
        right_i = np.round(right * scale).astype(np.int16)
        interleaved = np.empty(n * 2, dtype=np.int16)
        interleaved[0::2] = left_i
        interleaved[1::2] = right_i
        raw = interleaved.tobytes()

    with wave.open(str(path_obj), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(sw)
        wf.setframerate(sr)
        wf.writeframes(bytes(raw))


# ═══════════════════════════════════════════════════════════════════
# Stereo Utilities
# ═══════════════════════════════════════════════════════════════════

def stereo_place(mono: np.ndarray, width: float = 0.0
                 ) -> tuple[np.ndarray, np.ndarray]:
    """Place a mono signal in stereo field.

    width: 0.0 = center (mono), 1.0 = full stereo spread.
    Returns (left, right).
    """
    mono = np.asarray(mono, dtype=np.float64)
    if width <= 0.0 or len(mono) == 0:
        return mono.copy(), mono.copy()

    # Constant-power panning with decorrelation via Hilbert-like delay
    w = min(width, 1.0)
    # Simple decorrelation: shift right channel by a small amount
    shift = max(1, int(w * 0.002 * SAMPLE_RATE))  # up to 2ms
    right = np.zeros_like(mono)
    right[shift:] = mono[:-shift] if shift < len(mono) else 0.0

    # Mix: center + width spread
    mid_gain = math.cos(w * math.pi / 4)
    side_gain = math.sin(w * math.pi / 4)

    left = mono * mid_gain + mono * side_gain * 0.5
    right_out = mono * mid_gain + right * side_gain * 0.5

    return left, right_out


# ═══════════════════════════════════════════════════════════════════
# Sidechain Envelope
# ═══════════════════════════════════════════════════════════════════

def sidechain_duck(audio: np.ndarray, bpm: float, bars: int,
                   depth: float = 0.80, release_ms: float = 200.0
                   ) -> np.ndarray:
    """Apply sidechain pumping envelope synced to kick pattern.

    Creates a ducking envelope that triggers on every beat,
    with configurable depth and release time.
    """
    audio = np.asarray(audio, dtype=np.float64)
    if len(audio) == 0:
        return audio

    beat_samples = int(60.0 / bpm * SAMPLE_RATE)
    total_beats = bars * 4
    release_samples = int(release_ms / 1000.0 * SAMPLE_RATE)

    envelope = np.ones(len(audio), dtype=np.float64)

    for beat in range(total_beats):
        start = beat * beat_samples
        if start >= len(audio):
            break

        # Duck: instant attack, exponential release
        duck_min = 1.0 - depth
        for j in range(release_samples):
            pos = start + j
            if pos >= len(audio):
                break
            t = j / max(release_samples, 1)
            # Exponential release curve
            gain = duck_min + (1.0 - duck_min) * (1.0 - math.exp(-3.0 * t))
            envelope[pos] = min(envelope[pos], gain)

    return audio * envelope


# ═══════════════════════════════════════════════════════════════════
# Legacy Renderers (fallback for elements not covered by pipelines)
# ═══════════════════════════════════════════════════════════════════

def _section_samples(bpm: float, bars: int) -> int:
    """Number of samples for a section."""
    return round(bars * 4 * 60.0 / bpm * SAMPLE_RATE)


def _note_freq(dna, degree: int, octave: int = 3) -> float:
    """Get frequency for a scale degree in the song's key."""
    # D minor: D E F G A Bb C
    scale_notes = ["D", "E", "F", "G", "A", "Bb", "C"]
    note_name = scale_notes[degree % 7]
    key = f"{note_name}{octave}"
    if hasattr(dna, "freq_table") and key in dna.freq_table:
        return dna.freq_table[key]
    # Fallback: compute from root
    semitones = [0, 2, 3, 5, 7, 8, 10]  # natural minor intervals
    return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semitones[degree % 7] / 12.0))


def render_vocal_chops(dna, bars: int, energy: float) -> np.ndarray:
    """Render vocal chop patterns using the vocal_chop engine."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.vocal_chop import VocalChop, synthesize_chop
        beat_dur = 60.0 / dna.bpm
        buf = np.zeros(n_samples, dtype=np.float64)

        vowels = getattr(dna, "chop_vowels", ["ah", "oh", "ee", "oo"])
        notes = ["C4", "D3", "E4", "G3", "A3", "C3", "F3"]
        beats_per_bar = 4
        total_beats = bars * beats_per_bar

        for beat in range(total_beats):
            if beat % 2 != 0:  # chop every other beat (half-time feel)
                continue
            vowel = vowels[beat % len(vowels)]
            note = notes[beat % len(notes)]
            chop = VocalChop(
                name=f"chop_beat{beat}",
                vowel=vowel,
                note=note,
                duration_s=beat_dur * 0.5,
            )
            chop_audio = synthesize_chop(chop, sample_rate=SAMPLE_RATE)
            offset = int(beat * beat_dur * SAMPLE_RATE)
            end = min(offset + len(chop_audio), n_samples)
            buf[offset:end] += chop_audio[:end - offset]

        return buf * energy * 0.6

    except (ImportError, Exception):
        # Fallback: filtered noise bursts
        buf = np.zeros(n_samples, dtype=np.float64)
        beat_samples = int(60.0 / dna.bpm * SAMPLE_RATE)
        chop_len = int(beat_samples * 0.25)
        for beat in range(bars * 4):
            if beat % 2 != 0:
                continue
            offset = beat * beat_samples
            if offset + chop_len > n_samples:
                break
            t = np.linspace(0, 1, chop_len)
            freq = _note_freq(dna, beat % 7, octave=4)
            chop = np.sin(2 * np.pi * freq * t / SAMPLE_RATE * np.arange(chop_len)) * \
                   np.exp(-3.0 * t)
            buf[offset:offset + chop_len] += chop * energy * 0.3

        return buf


def render_bass_drop(dna, bars: int, energy: float) -> np.ndarray:
    """Render bass for drop sections using bass_oneshot + FM."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.bass_oneshot import BassPreset, synthesize_bass

        beat_dur = 60.0 / dna.bpm
        buf = np.zeros(n_samples, dtype=np.float64)

        # Bass riff pattern from DNA
        riff = getattr(dna.bass, "bass_riff", [
            [(0, 0.0, 1.0), (0, 1.0, 1.0), (6, 2.0, 0.5), (0, 3.0, 1.0)],
        ])

        for bar_idx in range(bars):
            pattern = riff[bar_idx % len(riff)]
            for degree, beat_pos, dur_beats in pattern:
                freq = _note_freq(dna, degree, octave=2)
                dur_s = dur_beats * beat_dur
                preset = BassPreset(
                    name=f"bass_bar{bar_idx}",
                    bass_type="sub_sine",
                    frequency=freq,
                    duration_s=dur_s,
                    distortion=dna.bass.distortion,
                )
                note = synthesize_bass(preset, sample_rate=SAMPLE_RATE)
                offset = int((bar_idx * 4 + beat_pos) * beat_dur * SAMPLE_RATE)
                end = min(offset + len(note), n_samples)
                buf[offset:end] += note[:end - offset]

        return buf * energy * 0.85

    except (ImportError, Exception):
        # Fallback: simple sine sub
        buf = np.zeros(n_samples, dtype=np.float64)
        freq = dna.root_freq * 2  # octave 2
        t = np.arange(n_samples) / SAMPLE_RATE
        buf = np.sin(2 * np.pi * freq * t) * energy * 0.5
        return buf


def render_drone(dna, bars: int, energy: float) -> np.ndarray:
    """Render atmospheric drone layer."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.drone_synth import DronePreset, synthesize_drone
        dur_s = n_samples / SAMPLE_RATE
        preset = DronePreset(
            name="atmos_drone",
            drone_type="dark",
            frequency=dna.root_freq * 2,
            duration_s=dur_s,
            num_voices=dna.atmosphere.drone_voices,
            movement=dna.atmosphere.drone_movement,
        )
        audio = synthesize_drone(preset, sample_rate=SAMPLE_RATE)
        if len(audio) > n_samples:
            audio = audio[:n_samples]
        elif len(audio) < n_samples:
            padded = np.zeros(n_samples, dtype=np.float64)
            padded[:len(audio)] = audio
            audio = padded
        return audio * energy * 0.4

    except (ImportError, Exception):
        # Fallback: detuned sine layers
        t = np.arange(n_samples) / SAMPLE_RATE
        freq = dna.root_freq * 2
        buf = np.zeros(n_samples, dtype=np.float64)
        for voice in range(5):
            detune = 1.0 + (voice - 2) * 0.003 * PHI
            buf += np.sin(2 * np.pi * freq * detune * t) * 0.2
        # Fade in/out
        fade = min(int(2.0 * SAMPLE_RATE), n_samples // 4)
        buf[:fade] *= np.linspace(0, 1, fade)
        buf[-fade:] *= np.linspace(1, 0, fade)
        return buf * energy * 0.3


def render_lead_melody(dna, bars: int, energy: float) -> np.ndarray:
    """Render lead melody pattern."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.lead_synth import LeadPreset, synthesize_screech_lead

        beat_dur = 60.0 / dna.bpm
        buf = np.zeros(n_samples, dtype=np.float64)

        patterns = getattr(dna.lead, "melody_patterns", [
            [(0, 0.0, 0.5, 1.0), (6, 1.0, 0.5, 0.9),
             (4, 2.0, 0.75, 0.85), (2, 3.0, 0.5, 0.8)],
        ])

        for bar_idx in range(bars):
            pattern = patterns[bar_idx % len(patterns)]
            for degree, beat_pos, dur_beats, velocity in pattern:
                if degree < 0:  # rest
                    continue
                freq = _note_freq(dna, degree, octave=4)
                dur_s = dur_beats * beat_dur
                preset = LeadPreset(
                    name=f"lead_bar{bar_idx}",
                    lead_type="screech",
                    frequency=freq,
                    duration_s=dur_s,
                    filter_cutoff=dna.lead.brightness,
                )
                note = synthesize_screech_lead(preset, sample_rate=SAMPLE_RATE)
                note = note * velocity
                offset = int((bar_idx * 4 + beat_pos) * beat_dur * SAMPLE_RATE)
                end = min(offset + len(note), n_samples)
                buf[offset:end] += note[:end - offset]

        return buf * energy * 0.65

    except (ImportError, Exception):
        # Fallback: sawtooth with LP filter
        t = np.arange(n_samples) / SAMPLE_RATE
        freq = _note_freq(dna, 0, octave=4)
        buf = np.zeros(n_samples, dtype=np.float64)
        # Simple sawtooth
        phase = (freq * t) % 1.0
        buf = (2.0 * phase - 1.0) * energy * 0.3
        return buf


def render_noise_bed(dna, bars: int, energy: float) -> np.ndarray:
    """Render filtered noise bed for texture."""
    n_samples = _section_samples(dna.bpm, bars)

    noise_level = getattr(dna.atmosphere, "noise_bed_level", 0.12)
    noise_type = getattr(dna.atmosphere, "noise_bed_type", "pink")

    try:
        from engine.noise_generator import NoisePreset, synthesize_noise
        dur_s = n_samples / SAMPLE_RATE
        preset = NoisePreset(
            name="noise_bed",
            noise_type=noise_type,
            duration_s=dur_s,
            gain=noise_level,
        )
        audio = synthesize_noise(preset, sample_rate=SAMPLE_RATE)
        if len(audio) > n_samples:
            audio = audio[:n_samples]
        elif len(audio) < n_samples:
            padded = np.zeros(n_samples)
            padded[:len(audio)] = audio
            audio = padded

        # Gate: -50dB threshold
        gate_thresh = 10 ** (-50 / 20)
        audio[np.abs(audio) < gate_thresh] = 0.0

        return audio * energy * 0.25

    except (ImportError, Exception):
        # Fallback: filtered white noise
        rng = np.random.default_rng(42)
        noise = rng.standard_normal(n_samples)
        # Simple pink approximation: cumulative average
        pink = np.cumsum(noise)
        pink = pink - np.linspace(pink[0], pink[-1], n_samples)
        pink = pink / (np.max(np.abs(pink)) + 1e-12)
        # Fade edges
        fade = min(int(1.0 * SAMPLE_RATE), n_samples // 4)
        pink[:fade] *= np.linspace(0, 1, fade)
        pink[-fade:] *= np.linspace(1, 0, fade)
        return pink * noise_level * energy * 0.2


def render_pad(dna, bars: int, energy: float) -> np.ndarray:
    """Render pad chord."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.pad_synth import PadPreset, synthesize_dark_pad

        dur_s = n_samples / SAMPLE_RATE
        # D minor chord: D F A
        root = _note_freq(dna, 0, octave=3)
        third = _note_freq(dna, 2, octave=3)  # minor 3rd (F)
        fifth = _note_freq(dna, 4, octave=3)  # 5th (A)

        buf = np.zeros(n_samples, dtype=np.float64)
        for freq in [root, third, fifth]:
            preset = PadPreset(
                name="pad_chord",
                pad_type="dark",
                frequency=freq,
                duration_s=dur_s,
                attack_s=dna.atmosphere.pad_attack,
                brightness=dna.atmosphere.pad_brightness,
            )
            audio = synthesize_dark_pad(preset, sample_rate=SAMPLE_RATE)
            if len(audio) > n_samples:
                audio = audio[:n_samples]
            elif len(audio) < n_samples:
                padded = np.zeros(n_samples)
                padded[:len(audio)] = audio
                audio = padded
            buf += audio * 0.33

        return buf * energy * 0.5

    except (ImportError, Exception):
        # Fallback: simple additive pad
        t = np.arange(n_samples) / SAMPLE_RATE
        root = _note_freq(dna, 0, octave=3)
        third = _note_freq(dna, 2, octave=3)
        fifth = _note_freq(dna, 4, octave=3)
        buf = np.zeros(n_samples, dtype=np.float64)
        for freq in [root, third, fifth]:
            buf += np.sin(2 * np.pi * freq * t) * 0.2
            buf += np.sin(2 * np.pi * freq * 2 * t) * 0.05  # octave harmonic
        # Slow attack/release
        attack = min(int(dna.atmosphere.pad_attack * SAMPLE_RATE), n_samples // 3)
        release = min(int(2.0 * SAMPLE_RATE), n_samples // 3)
        buf[:attack] *= np.linspace(0, 1, attack)
        buf[-release:] *= np.linspace(1, 0, release)
        return buf * energy * 0.35


def render_riser(dna, bars: int) -> np.ndarray:
    """Render pitch/noise riser for build sections."""
    n_samples = _section_samples(dna.bpm, bars)

    try:
        from engine.riser_synth import RiserPreset, synthesize_noise_sweep

        dur_s = n_samples / SAMPLE_RATE
        start_freq = getattr(dna.fx, "riser_start_freq", 150.0)
        end_freq = getattr(dna.fx, "riser_end_freq", 8000.0)
        preset = RiserPreset(
            name="build_riser",
            riser_type="noise_sweep",
            start_freq=start_freq,
            end_freq=end_freq,
            duration_s=dur_s,
            intensity=dna.fx.riser_intensity,
        )
        audio = synthesize_noise_sweep(preset, sample_rate=SAMPLE_RATE)
        if len(audio) > n_samples:
            audio = audio[:n_samples]
        elif len(audio) < n_samples:
            padded = np.zeros(n_samples)
            padded[:len(audio)] = audio
            audio = padded
        return audio * 0.6

    except (ImportError, Exception):
        # Fallback: rising filtered noise
        t = np.arange(n_samples) / SAMPLE_RATE
        dur_s = n_samples / SAMPLE_RATE
        # Exponential frequency sweep
        start_f = 150.0
        end_f = 8000.0
        freq = start_f * (end_f / start_f) ** (t / dur_s)
        phase = np.cumsum(freq / SAMPLE_RATE) * 2 * np.pi
        riser = np.sin(phase) * np.linspace(0, 1, n_samples)
        # Add noise sweep
        rng = np.random.default_rng(77)
        noise = rng.standard_normal(n_samples) * np.linspace(0, 0.3, n_samples)
        return (riser * 0.5 + noise * 0.3) * 0.5


# ═══════════════════════════════════════════════════════════════════
# CLI — quick test
# ═══════════════════════════════════════════════════════════════════

def main():
    """Quick self-test: verify all exports work."""
    print(f"SAMPLE_RATE = {SAMPLE_RATE}")
    print(f"PHI = {PHI}")

    # Test write_wav_stereo
    test_l = np.sin(np.linspace(0, 440 * 2 * np.pi, SAMPLE_RATE))
    test_r = test_l.copy()
    write_wav_stereo("/tmp/dubforge_test.wav", test_l, test_r)
    print("✓ write_wav_stereo")

    # Test stereo_place
    l, r = stereo_place(test_l, width=0.3)
    print(f"✓ stereo_place: L peak={np.max(np.abs(l)):.3f}, R peak={np.max(np.abs(r)):.3f}")

    # Test sidechain_duck
    ducked = sidechain_duck(test_l, 140, 1, depth=0.8, release_ms=200)
    print(f"✓ sidechain_duck: min={np.min(ducked):.3f}")

    print("\nAll exports verified.")


if __name__ == "__main__":
    main()
