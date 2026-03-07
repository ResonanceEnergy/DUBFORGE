"""
DUBFORGE Engine — Arp Synth

Synthesizes arpeggiated synth patterns from scratch:
  - Pulse:    square-wave arp with filter sweep
  - Saw:      supersaw arp with detuned voices
  - FM:       FM synthesis arp with evolving modulation
  - Pluck:    short pluck arp with resonant filter
  - Acid:     303-style acid arp with squelchy filter

All arps use phi-ratio timing and Fibonacci structure.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/arp_synth_*.wav
    output/analysis/arp_synth_manifest.json
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

_log = get_logger("dubforge.arp_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ArpSynthPreset:
    """Settings for a single arp synth pattern."""
    name: str
    arp_type: str            # pulse | saw | fm | pluck | acid
    base_freq: float = 220.0  # Hz root note
    duration_s: float = 4.0
    step_count: int = 8      # notes per bar
    attack_s: float = 0.005
    decay_s: float = 0.1
    sustain: float = 0.6
    release_s: float = 0.05
    filter_cutoff: float = 0.6  # 0..1
    resonance: float = 0.3
    detune_cents: float = 0.0
    fm_ratio: float = 2.0
    fm_depth: float = 0.0
    distortion: float = 0.0
    octave_range: int = 2    # how many octaves the arp spans


@dataclass
class ArpSynthBank:
    """Collection of arp synth presets."""
    name: str
    presets: list[ArpSynthPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIS HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _note_envelope(n: int, preset: ArpSynthPreset,
                   sample_rate: int) -> np.ndarray:
    """Build ADSR envelope for a single arp note."""
    env = np.zeros(n)
    a = max(1, min(int(preset.attack_s * sample_rate), n // 4))
    d = max(1, min(int(preset.decay_s * sample_rate), n // 4))
    r = max(1, min(int(preset.release_s * sample_rate), n // 4))
    s_len = max(0, n - a - d - r)

    env[:a] = np.linspace(0, 1, a)
    env[a:a + d] = np.linspace(1, preset.sustain, d)
    env[a + d:a + d + s_len] = preset.sustain
    env[a + d + s_len:] = np.linspace(preset.sustain, 0, r)
    return env


def _phi_arp_pattern(step_count: int, octave_range: int,
                     base_freq: float) -> list[float]:
    """Generate phi-ratio arp note pattern."""
    # Fibonacci-inspired interval steps
    fib_intervals = [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19, 20, 24]
    freqs = []
    for i in range(step_count):
        idx = i % len(fib_intervals)
        semitones = fib_intervals[idx]
        # Wrap within octave range
        max_semitones = octave_range * 12
        semitones = semitones % max_semitones
        freq = base_freq * (2.0 ** (semitones / 12.0))
        freqs.append(freq)
    return freqs


def _soft_clip(signal: np.ndarray, drive: float) -> np.ndarray:
    """Apply soft saturation."""
    if drive <= 0:
        return signal
    gain = 1.0 + drive * 4.0
    return np.tanh(signal * gain) / np.tanh(gain)


# ═══════════════════════════════════════════════════════════════════════════
# ARP SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_pulse_arp(preset: ArpSynthPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pulse-wave arp with filter sweep."""
    freqs = _phi_arp_pattern(preset.step_count, preset.octave_range,
                             preset.base_freq)
    note_samples = int(preset.duration_s * sample_rate / preset.step_count)
    segments = []
    for i, freq in enumerate(freqs):
        t = np.arange(note_samples) / sample_rate
        # Pulse wave (variable duty cycle)
        duty = 0.3 + 0.2 * math.sin(2 * math.pi * i / preset.step_count)
        phase = (freq * t) % 1.0
        osc = np.where(phase < duty, 1.0, -1.0)
        # Simple filter: smooth based on cutoff
        cutoff_freq = preset.filter_cutoff * 8000
        k = max(1, int(sample_rate / max(cutoff_freq, 100)))
        kernel = np.ones(k) / k
        osc = np.convolve(osc, kernel, mode="same")
        env = _note_envelope(note_samples, preset, sample_rate)
        segments.append(osc * env)
    signal = np.concatenate(segments)
    signal = _soft_clip(signal, preset.distortion)
    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_saw_arp(preset: ArpSynthPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Supersaw arp with detuned voices."""
    freqs = _phi_arp_pattern(preset.step_count, preset.octave_range,
                             preset.base_freq)
    note_samples = int(preset.duration_s * sample_rate / preset.step_count)
    detune_hz = preset.detune_cents * 0.06  # rough cents to Hz
    segments = []
    for freq in freqs:
        t = np.arange(note_samples) / sample_rate
        # 5 detuned saw voices
        osc = np.zeros(note_samples)
        for v in range(-2, 3):
            f = freq + v * detune_hz
            osc += 2.0 * ((f * t) % 1.0) - 1.0
        osc /= 5.0
        env = _note_envelope(note_samples, preset, sample_rate)
        segments.append(osc * env)
    signal = np.concatenate(segments)
    signal = _soft_clip(signal, preset.distortion)
    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_fm_arp(preset: ArpSynthPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM synthesis arp with evolving modulation."""
    freqs = _phi_arp_pattern(preset.step_count, preset.octave_range,
                             preset.base_freq)
    note_samples = int(preset.duration_s * sample_rate / preset.step_count)
    segments = []
    for i, freq in enumerate(freqs):
        t = np.arange(note_samples) / sample_rate
        # Evolving FM depth
        depth = preset.fm_depth * (1.0 + 0.5 * math.sin(
            2 * math.pi * i / preset.step_count * PHI
        ))
        mod = depth * np.sin(2 * math.pi * freq * preset.fm_ratio * t)
        osc = np.sin(2 * math.pi * freq * t + mod)
        env = _note_envelope(note_samples, preset, sample_rate)
        segments.append(osc * env)
    signal = np.concatenate(segments)
    signal = _soft_clip(signal, preset.distortion)
    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_pluck_arp(preset: ArpSynthPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Short pluck arp with resonant decay."""
    freqs = _phi_arp_pattern(preset.step_count, preset.octave_range,
                             preset.base_freq)
    note_samples = int(preset.duration_s * sample_rate / preset.step_count)
    segments = []
    for freq in freqs:
        t = np.arange(note_samples) / sample_rate
        # Rich harmonic content
        osc = (np.sin(2 * math.pi * freq * t)
               + 0.5 * np.sin(2 * math.pi * freq * 2 * t)
               + 0.25 * np.sin(2 * math.pi * freq * 3 * t))
        # Fast decay (pluck-like)
        pluck_env = np.exp(-t / max(0.01, preset.decay_s * 0.5))
        # Decaying brightness
        k = max(1, int(sample_rate / max(freq * 4 * preset.filter_cutoff, 100)))
        kernel = np.ones(k) / k
        osc = np.convolve(osc, kernel, mode="same")
        segments.append(osc * pluck_env)
    signal = np.concatenate(segments)
    signal = _soft_clip(signal, preset.distortion)
    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_acid_arp(preset: ArpSynthPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """303-style acid arp with squelchy filter."""
    freqs = _phi_arp_pattern(preset.step_count, preset.octave_range,
                             preset.base_freq)
    note_samples = int(preset.duration_s * sample_rate / preset.step_count)
    segments = []
    for i, freq in enumerate(freqs):
        t = np.arange(note_samples) / sample_rate
        # Saw wave
        osc = 2.0 * ((freq * t) % 1.0) - 1.0
        # Envelope-following filter (decaying cutoff)
        cutoff_sweep = np.exp(-t / max(0.01, preset.decay_s))
        cutoff_freq = 200 + cutoff_sweep * preset.filter_cutoff * 6000
        # Simple per-sample filter approximation
        k_arr = np.clip(sample_rate / cutoff_freq, 1, 100).astype(int)
        # Use average filter size for simplicity
        avg_k = max(1, int(np.mean(k_arr)))
        kernel = np.ones(avg_k) / avg_k
        osc = np.convolve(osc, kernel, mode="same")
        # Resonance boost
        if preset.resonance > 0:
            osc += preset.resonance * 0.5 * np.sin(
                2 * math.pi * np.mean(cutoff_freq) * t
            )
        env = _note_envelope(note_samples, preset, sample_rate)
        segments.append(osc * env)
    signal = np.concatenate(segments)
    signal = _soft_clip(signal, preset.distortion)
    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_arp(preset: ArpSynthPreset,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct arp synthesizer."""
    synthesizers = {
        "pulse": synthesize_pulse_arp,
        "saw": synthesize_saw_arp,
        "fm": synthesize_fm_arp,
        "pluck": synthesize_pluck_arp,
        "acid": synthesize_acid_arp,
    }
    fn = synthesizers.get(preset.arp_type)
    if fn is None:
        raise ValueError(f"Unknown arp_type: {preset.arp_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 variants = 20 presets
# ═══════════════════════════════════════════════════════════════════════════

def pulse_arp_bank() -> ArpSynthBank:
    """Pulse-wave arp patterns — 4 presets."""
    return ArpSynthBank(
        name="PULSE_ARPS",
        presets=[
            ArpSynthPreset("pulse_arp_A3", "pulse", 220.0,
                           duration_s=4.0, step_count=8,
                           filter_cutoff=0.6, distortion=0.1),
            ArpSynthPreset("pulse_arp_C4", "pulse", 261.63,
                           duration_s=4.0, step_count=16,
                           filter_cutoff=0.7, distortion=0.05),
            ArpSynthPreset("pulse_arp_E3", "pulse", 164.81,
                           duration_s=4.0, step_count=8,
                           filter_cutoff=0.5, distortion=0.15),
            ArpSynthPreset("pulse_arp_G3", "pulse", 196.00,
                           duration_s=4.0, step_count=12,
                           filter_cutoff=0.8, distortion=0.0),
        ],
    )


def saw_arp_bank() -> ArpSynthBank:
    """Supersaw arp patterns — 4 presets."""
    return ArpSynthBank(
        name="SAW_ARPS",
        presets=[
            ArpSynthPreset("saw_arp_A3", "saw", 220.0,
                           duration_s=4.0, step_count=8,
                           detune_cents=15.0, distortion=0.05),
            ArpSynthPreset("saw_arp_C4", "saw", 261.63,
                           duration_s=4.0, step_count=16,
                           detune_cents=20.0, distortion=0.1),
            ArpSynthPreset("saw_arp_E3", "saw", 164.81,
                           duration_s=4.0, step_count=8,
                           detune_cents=10.0, distortion=0.0),
            ArpSynthPreset("saw_arp_G3", "saw", 196.00,
                           duration_s=4.0, step_count=12,
                           detune_cents=25.0, distortion=0.08),
        ],
    )


def fm_arp_bank() -> ArpSynthBank:
    """FM synthesis arp patterns — 4 presets."""
    return ArpSynthBank(
        name="FM_ARPS",
        presets=[
            ArpSynthPreset("fm_arp_A3", "fm", 220.0,
                           duration_s=4.0, step_count=8,
                           fm_ratio=2.0, fm_depth=3.0),
            ArpSynthPreset("fm_arp_C4", "fm", 261.63,
                           duration_s=4.0, step_count=16,
                           fm_ratio=1.5, fm_depth=2.0),
            ArpSynthPreset("fm_arp_E3", "fm", 164.81,
                           duration_s=4.0, step_count=8,
                           fm_ratio=3.0, fm_depth=4.0, distortion=0.1),
            ArpSynthPreset("fm_arp_G3", "fm", 196.00,
                           duration_s=4.0, step_count=12,
                           fm_ratio=PHI, fm_depth=2.5),
        ],
    )


def pluck_arp_bank() -> ArpSynthBank:
    """Pluck arp patterns — 4 presets."""
    return ArpSynthBank(
        name="PLUCK_ARPS",
        presets=[
            ArpSynthPreset("pluck_arp_A3", "pluck", 220.0,
                           duration_s=4.0, step_count=8,
                           decay_s=0.08, filter_cutoff=0.7),
            ArpSynthPreset("pluck_arp_C4", "pluck", 261.63,
                           duration_s=4.0, step_count=16,
                           decay_s=0.05, filter_cutoff=0.8),
            ArpSynthPreset("pluck_arp_E3", "pluck", 164.81,
                           duration_s=4.0, step_count=8,
                           decay_s=0.1, filter_cutoff=0.5),
            ArpSynthPreset("pluck_arp_G3", "pluck", 196.00,
                           duration_s=4.0, step_count=12,
                           decay_s=0.06, filter_cutoff=0.9),
        ],
    )


def acid_arp_bank() -> ArpSynthBank:
    """Acid arp patterns — 4 presets."""
    return ArpSynthBank(
        name="ACID_ARPS",
        presets=[
            ArpSynthPreset("acid_arp_A2", "acid", 110.0,
                           duration_s=4.0, step_count=8,
                           filter_cutoff=0.7, resonance=0.6,
                           distortion=0.2),
            ArpSynthPreset("acid_arp_C3", "acid", 130.81,
                           duration_s=4.0, step_count=16,
                           filter_cutoff=0.8, resonance=0.5,
                           distortion=0.15),
            ArpSynthPreset("acid_arp_E2", "acid", 82.41,
                           duration_s=4.0, step_count=8,
                           filter_cutoff=0.6, resonance=0.7,
                           distortion=0.3),
            ArpSynthPreset("acid_arp_G2", "acid", 98.00,
                           duration_s=4.0, step_count=12,
                           filter_cutoff=0.9, resonance=0.4,
                           distortion=0.1),
        ],
    )


ALL_ARP_BANKS: dict[str, callable] = {
    "pulse": pulse_arp_bank,
    "saw":   saw_arp_bank,
    "fm":    fm_arp_bank,
    "pluck": pluck_arp_bank,
    "acid":  acid_arp_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def write_arp_manifest(output_dir: str = "output") -> dict:
    """Synthesize all arp presets and write manifest JSON."""
    out = Path(output_dir)
    wav_dir = out / "wavetables"
    manifest: dict = {"module": "arp_synth", "banks": {}}

    for bank_key, bank_fn in ALL_ARP_BANKS.items():
        bank = bank_fn()
        entries = []
        for preset in bank.presets:
            audio = synthesize_arp(preset)
            fname = f"arp_synth_{preset.name}.wav"
            _write_wav(wav_dir / fname, audio)
            entries.append({
                "name": preset.name,
                "arp_type": preset.arp_type,
                "base_freq": preset.base_freq,
                "duration_s": preset.duration_s,
                "step_count": preset.step_count,
                "file": fname,
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = entries

    manifest_path = out / "analysis" / "arp_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    _log.info("Arp synth manifest → %s", manifest_path)
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all arp synth patterns."""
    _log.info("═══ DUBFORGE Arp Synth Generator ═══")
    manifest = write_arp_manifest()
    total = sum(len(v) for v in manifest["banks"].values())
    _log.info("Generated %d arp presets across %d banks",
              total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
