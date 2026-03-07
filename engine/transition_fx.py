"""
DUBFORGE Engine — Transition FX Generator

Synthesizes transition sound effects for dubstep arrangements:
  - Tape Stop:      decelerating pitch / amplitude (vinyl brake)
  - Tape Start:     accelerating from zero (reverse brake)
  - Reverse Crash:  reversed cymbal swell
  - Gate Chop:      rhythmic gating of noise (buildups)
  - Pitch Dive:     sharp pitch descent
  - Glitch Stutter: repeating buffer fragments
  - Vinyl FX:       crackle, scratch, needle drop

All transitions use phi-ratio curves for natural-sounding sweeps.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/transition_*.wav
    output/analysis/transition_fx_manifest.json

Based on Subtronics production analysis:
  - Tape stops punctuate every major transition
  - Reverse crashes frame build sections
  - Gate chops create tension before drops
  - Glitch stutters accent rhythmic patterns
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

_log = get_logger("dubforge.transition_fx")

DEFAULT_BPM = 150


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TransitionPreset:
    """Settings for a transition FX sound."""
    name: str
    fx_type: str            # tape_stop|tape_start|reverse_crash|gate_chop
    #                         pitch_dive|glitch_stutter|vinyl_fx
    duration_s: float
    start_freq: float = 200.0
    end_freq: float = 50.0
    gate_divisions: int = 8
    stutter_repeats: int = 4
    brightness: float = 0.7
    distortion: float = 0.0
    reverb_amount: float = 0.2


@dataclass
class TransitionBank:
    """Collection of transition presets."""
    name: str
    presets: list[TransitionPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    """Write signal to 16-bit mono WAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    _log.info("Wrote transition WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_tape_stop(preset: TransitionPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tape stop — decelerating playback simulation."""
    n = int(preset.duration_s * sample_rate)

    progress = np.linspace(0, 1, n)
    speed = (1 - progress) ** PHI

    # Pitch follows speed curve
    freq = preset.start_freq * speed + 0.1
    phase = np.cumsum(2 * math.pi * freq / sample_rate)

    # Rich tone (saw-ish via 3 harmonics)
    signal = np.sin(phase) + 0.3 * np.sin(phase * 2) + 0.15 * np.sin(phase * 3)

    # Amplitude follows speed
    signal *= speed

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_tape_start(preset: TransitionPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tape start — accelerating from zero to normal speed."""
    n = int(preset.duration_s * sample_rate)

    progress = np.linspace(0, 1, n)
    speed = progress ** (1 / PHI)

    freq = preset.start_freq * speed + 0.1
    phase = np.cumsum(2 * math.pi * freq / sample_rate)
    signal = np.sin(phase) + 0.3 * np.sin(phase * 2)

    signal *= speed

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_reverse_crash(preset: TransitionPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Reverse crash — noise swell simulating reversed cymbal."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(55)
    noise = rng.normal(0, 1, n)

    # Brightness-controlled filter
    alpha = min(0.99, preset.brightness * 0.3 + 0.1)
    y = 0.0
    signal = np.zeros(n)
    for i in range(n):
        y = y * (1 - alpha) + noise[i] * alpha
        signal[i] = y

    # Reverse envelope: crescendo from silence to peak
    progress = np.linspace(0, 1, n)
    env = progress ** PHI
    signal *= env

    # Tail fade
    tail_len = max(1, int(0.1 * n))
    signal[-tail_len:] *= np.linspace(1, 0, tail_len)

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_gate_chop(preset: TransitionPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Gate chop — rhythmic gating of noise for buildup tension."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(66)
    noise = rng.normal(0, 1, n)

    # Create gate pattern
    divisions = max(preset.gate_divisions, 1)
    samples_per_div = n // divisions

    gate = np.zeros(n)
    for d in range(divisions):
        start = d * samples_per_div
        on_len = int(samples_per_div * 0.5)
        end = min(start + on_len, n)
        gate[start:end] = 1.0

    # Volume ramp (grow louder toward end)
    vol_ramp = np.linspace(0.3, 1.0, n)
    signal = noise * gate * vol_ramp

    # Brightness filter
    alpha = min(0.99, preset.brightness * 0.4 + 0.05)
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_pitch_dive(preset: TransitionPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch dive — sharp frequency descent."""
    n = int(preset.duration_s * sample_rate)

    progress = np.linspace(0, 1, n)
    end_f = max(preset.end_freq, 1)
    freq = preset.start_freq * np.exp(
        -progress * math.log(preset.start_freq / end_f)
    )

    phase = np.cumsum(2 * math.pi * freq / sample_rate)
    signal = np.sin(phase)
    signal += 0.4 * np.sin(phase * 2)

    # Quick decay envelope
    env = np.exp(-progress * 3)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_glitch_stutter(preset: TransitionPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Glitch stutter — repeating buffer fragment with decay."""
    n = int(preset.duration_s * sample_rate)
    repeats = max(preset.stutter_repeats, 2)

    # Generate one grain of sound
    grain_len = max(1, n // repeats)
    t_grain = np.linspace(0, grain_len / sample_rate, grain_len, endpoint=False)
    grain = np.sin(2 * math.pi * preset.start_freq * t_grain)
    grain += 0.3 * np.sin(2 * math.pi * preset.start_freq * 1.5 * t_grain)

    # Short envelope per grain
    release = max(1, int(0.3 * grain_len))
    grain_env = np.ones(grain_len)
    grain_env[-release:] = np.linspace(1, 0, release)
    grain *= grain_env

    # Repeat with decreasing volume
    signal = np.zeros(n)
    for r in range(repeats):
        start = r * grain_len
        end = min(start + grain_len, n)
        length = end - start
        decay = (1 - r / repeats) ** (1 / PHI)
        signal[start:end] = grain[:length] * decay

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_vinyl_fx(preset: TransitionPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Vinyl FX — crackle, scratch, and needle sounds."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(88)

    # Base crackle: sparse impulses
    crackle = np.zeros(n)
    num_pops = max(1, int(preset.brightness * n * 0.005))
    pop_positions = rng.integers(0, n, size=num_pops)
    pop_amplitudes = rng.uniform(0.3, 1.0, size=num_pops)
    for pos, amp in zip(pop_positions, pop_amplitudes):
        crackle[pos] = amp * rng.choice([-1, 1])

    # Filtered rumble
    rumble = rng.normal(0, 0.1, n)
    y = 0.0
    for i in range(n):
        y = y * 0.95 + rumble[i] * 0.05
        rumble[i] = y

    signal = crackle + rumble

    # Envelope
    attack = max(1, int(0.02 * n))
    release = max(1, int(0.1 * n))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    signal *= env

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    return signal


def synthesize_transition(preset: TransitionPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct transition synthesizer."""
    synthesizers = {
        "tape_stop": synthesize_tape_stop,
        "tape_start": synthesize_tape_start,
        "reverse_crash": synthesize_reverse_crash,
        "gate_chop": synthesize_gate_chop,
        "pitch_dive": synthesize_pitch_dive,
        "glitch_stutter": synthesize_glitch_stutter,
        "vinyl_fx": synthesize_vinyl_fx,
    }
    fn = synthesizers.get(preset.fx_type)
    if fn is None:
        raise ValueError(f"Unknown transition fx_type: {preset.fx_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 Subtronics-calibrated transition FX
# ═══════════════════════════════════════════════════════════════════════════

def tape_stop_bank() -> TransitionBank:
    """Tape stop variants — classic vinyl brake effect."""
    return TransitionBank(
        name="TAPE_STOPS",
        presets=[
            TransitionPreset("tape_stop_fast", "tape_stop", duration_s=0.5,
                             start_freq=300, distortion=0.1),
            TransitionPreset("tape_stop_medium", "tape_stop", duration_s=1.0,
                             start_freq=250, distortion=0.05),
            TransitionPreset("tape_stop_slow", "tape_stop", duration_s=2.0,
                             start_freq=200, distortion=0.15),
        ],
    )


def tape_start_bank() -> TransitionBank:
    """Tape start variants — section re-entry effect."""
    return TransitionBank(
        name="TAPE_STARTS",
        presets=[
            TransitionPreset("tape_start_fast", "tape_start", duration_s=0.5,
                             start_freq=300),
            TransitionPreset("tape_start_slow", "tape_start", duration_s=1.5,
                             start_freq=200),
        ],
    )


def reverse_crash_bank() -> TransitionBank:
    """Reverse crash — cymbal swell for builds."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return TransitionBank(
        name="REVERSE_CRASHES",
        presets=[
            TransitionPreset("rev_crash_1bar", "reverse_crash",
                             duration_s=bar_s,
                             brightness=0.8, reverb_amount=0.3),
            TransitionPreset("rev_crash_2bar", "reverse_crash",
                             duration_s=2 * bar_s,
                             brightness=0.7, reverb_amount=0.4),
            TransitionPreset("rev_crash_bright", "reverse_crash",
                             duration_s=bar_s,
                             brightness=1.0, reverb_amount=0.2),
        ],
    )


def gate_chop_bank() -> TransitionBank:
    """Gate chop — rhythmic noise gating for buildups."""
    bar_s = 4 * 60 / DEFAULT_BPM
    return TransitionBank(
        name="GATE_CHOPS",
        presets=[
            TransitionPreset("gate_8th", "gate_chop",
                             duration_s=2 * bar_s,
                             gate_divisions=16, brightness=0.7),
            TransitionPreset("gate_16th", "gate_chop",
                             duration_s=2 * bar_s,
                             gate_divisions=32, brightness=0.8),
            TransitionPreset("gate_triplet", "gate_chop",
                             duration_s=2 * bar_s,
                             gate_divisions=24, brightness=0.6),
        ],
    )


def pitch_dive_bank() -> TransitionBank:
    """Pitch dive variants — sharp frequency drops."""
    return TransitionBank(
        name="PITCH_DIVES",
        presets=[
            TransitionPreset("dive_fast", "pitch_dive", duration_s=0.3,
                             start_freq=800, end_freq=30, distortion=0.2),
            TransitionPreset("dive_medium", "pitch_dive", duration_s=0.6,
                             start_freq=500, end_freq=25, distortion=0.1),
            TransitionPreset("dive_deep", "pitch_dive", duration_s=1.0,
                             start_freq=1200, end_freq=20, distortion=0.3),
        ],
    )


def glitch_stutter_bank() -> TransitionBank:
    """Glitch stutter — repeating buffer fragments."""
    return TransitionBank(
        name="GLITCH_STUTTERS",
        presets=[
            TransitionPreset("glitch_x4", "glitch_stutter", duration_s=0.5,
                             start_freq=400, stutter_repeats=4, distortion=0.2),
            TransitionPreset("glitch_x8", "glitch_stutter", duration_s=0.5,
                             start_freq=600, stutter_repeats=8, distortion=0.3),
            TransitionPreset("glitch_x16", "glitch_stutter", duration_s=0.5,
                             start_freq=300, stutter_repeats=16, distortion=0.4),
        ],
    )


def vinyl_fx_bank() -> TransitionBank:
    """Vinyl FX — crackle, scratch, needle drop sounds."""
    return TransitionBank(
        name="VINYL_FX",
        presets=[
            TransitionPreset("vinyl_crackle", "vinyl_fx", duration_s=2.0,
                             brightness=0.5),
            TransitionPreset("vinyl_scratch", "vinyl_fx", duration_s=0.5,
                             brightness=0.9, distortion=0.1),
            TransitionPreset("vinyl_drop", "vinyl_fx", duration_s=1.0,
                             brightness=0.7),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# v1.9 — 10 new transition presets (3 banks)
# ═══════════════════════════════════════════════════════════════════════════

def long_tape_stop_bank() -> TransitionBank:
    """Extended tape stops — dramatic slow-motion brakes."""
    return TransitionBank(
        name="LONG_TAPE_STOPS",
        presets=[
            TransitionPreset("tape_stop_4bar", "tape_stop", duration_s=4.0,
                             start_freq=350, distortion=0.1),
            TransitionPreset("tape_stop_8bar", "tape_stop", duration_s=8.0,
                             start_freq=400, distortion=0.2),
            TransitionPreset("tape_stop_drag", "tape_stop", duration_s=6.0,
                             start_freq=280, distortion=0.15),
        ],
    )


def extreme_dive_bank() -> TransitionBank:
    """Extreme pitch dives — wide range, heavy distortion."""
    return TransitionBank(
        name="EXTREME_DIVES",
        presets=[
            TransitionPreset("dive_screamer", "pitch_dive", duration_s=0.5,
                             start_freq=2000, end_freq=20, distortion=0.5),
            TransitionPreset("dive_canyon", "pitch_dive", duration_s=1.5,
                             start_freq=1500, end_freq=15, distortion=0.4),
            TransitionPreset("dive_zap", "pitch_dive", duration_s=0.15,
                             start_freq=3000, end_freq=50, distortion=0.6),
            TransitionPreset("dive_rumble", "pitch_dive", duration_s=2.0,
                             start_freq=800, end_freq=10, distortion=0.3),
        ],
    )


def chaos_glitch_bank() -> TransitionBank:
    """Chaos glitch — extreme stutter/gate combinations."""
    return TransitionBank(
        name="CHAOS_GLITCH",
        presets=[
            TransitionPreset("glitch_x32", "glitch_stutter", duration_s=0.5,
                             start_freq=500, stutter_repeats=32, distortion=0.5),
            TransitionPreset("glitch_overdrive", "glitch_stutter", duration_s=1.0,
                             start_freq=800, stutter_repeats=24, distortion=0.7),
            TransitionPreset("glitch_micro", "glitch_stutter", duration_s=0.25,
                             start_freq=1000, stutter_repeats=64, distortion=0.4),
        ],
    )


ALL_TRANSITION_BANKS: dict[str, callable] = {
    "tape_stops":      tape_stop_bank,
    "tape_starts":     tape_start_bank,
    "reverse_crashes": reverse_crash_bank,
    "gate_chops":      gate_chop_bank,
    "pitch_dives":     pitch_dive_bank,
    "glitch_stutters": glitch_stutter_bank,
    "vinyl_fx":        vinyl_fx_bank,
    "long_tape_stops": long_tape_stop_bank,
    "extreme_dives":   extreme_dive_bank,
    "chaos_glitch":    chaos_glitch_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_transition_manifest(
    banks: dict[str, TransitionBank], out_dir: str,
) -> str:
    """Write JSON manifest of all generated transition FX."""
    manifest = {
        "generator": "DUBFORGE Transition FX Generator",
        "sample_rate": SAMPLE_RATE,
        "bpm": DEFAULT_BPM,
        "banks": {},
    }
    for bank_name, bank in banks.items():
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [
                {
                    "name": p.name,
                    "type": p.fx_type,
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "transition_fx_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote transition manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all transition FX WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, TransitionBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_TRANSITION_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_transition(preset)
            path = f"{wav_dir}/transition_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_transition_manifest(banks, analysis_dir)
    _log.info(
        "Transition FX complete — %d WAVs across %d banks",
        total, len(banks),
    )


if __name__ == "__main__":
    main()
