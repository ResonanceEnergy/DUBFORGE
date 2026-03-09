"""
DUBFORGE — Vector Synthesis Engine  (Session 162)

4-point vector synthesis with joystick-style crossfading
between waveforms, PHI-ratio morph paths and LFO-driven
vector movement.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 44100


@dataclass
class VectorPoint:
    """A waveform at one corner of the vector space."""
    wave_type: str = "sine"  # sine, saw, square, triangle, noise
    harmonics: int = 1
    detune: float = 0.0  # cents
    phase_offset: float = 0.0


@dataclass
class VectorPatch:
    """4-point vector synthesis patch."""
    name: str = "Vector"
    # Corners: A(top-left), B(top-right), C(bot-left), D(bot-right)
    a: VectorPoint = field(default_factory=lambda: VectorPoint("sine"))
    b: VectorPoint = field(default_factory=lambda: VectorPoint("saw"))
    c: VectorPoint = field(default_factory=lambda: VectorPoint("square"))
    d: VectorPoint = field(default_factory=lambda: VectorPoint("triangle"))
    # Vector position (0-1 for X and Y)
    x: float = 0.5
    y: float = 0.5
    # LFO for vector movement
    lfo_x_rate: float = 0.0  # Hz, 0=static
    lfo_y_rate: float = 0.0
    lfo_x_depth: float = 0.5
    lfo_y_depth: float = 0.5
    # Envelope
    attack: float = 0.01
    decay: float = 0.2
    sustain: float = 0.7
    release: float = 0.3
    master_gain: float = 0.8


def _oscillator(phase: float, wave_type: str,
                harmonics: int = 1) -> float:
    """Generate oscillator sample."""
    if wave_type == "sine":
        return math.sin(phase)
    elif wave_type == "saw":
        n = min(harmonics, 32)
        val = 0.0
        for k in range(1, n + 1):
            val += ((-1) ** (k + 1)) * math.sin(k * phase) / k
        return val * 2.0 / math.pi
    elif wave_type == "square":
        n = min(harmonics, 32)
        val = 0.0
        for k in range(1, n * 2, 2):
            val += math.sin(k * phase) / k
        return val * 4.0 / math.pi
    elif wave_type == "triangle":
        n = min(harmonics, 16)
        val = 0.0
        for k in range(n):
            h = 2 * k + 1
            val += ((-1) ** k) * math.sin(h * phase) / (h * h)
        return val * 8.0 / (math.pi * math.pi)
    elif wave_type == "noise":
        # Deterministic hash-based noise
        x = int(phase * 1000) & 0xFFFF
        x = ((x >> 1) ^ (-(x & 1) & 0xB400)) & 0xFFFF
        return (x / 32768.0) - 1.0
    return math.sin(phase)


def _adsr(t: float, dur: float, a: float, d: float,
          s: float, r: float) -> float:
    rel_start = dur - r
    if t < a:
        return t / a if a > 0 else 1.0
    elif t < a + d:
        return 1.0 - (1.0 - s) * ((t - a) / d)
    elif t < rel_start:
        return s
    elif t < dur:
        return s * (1.0 - (t - rel_start) / r)
    return 0.0


def render_vector(patch: VectorPatch, freq: float = 440.0,
                   duration: float = 2.0,
                   sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render vector synthesis."""
    n = int(duration * sample_rate)
    signal = [0.0] * n
    dt = 1.0 / sample_rate

    corners = [patch.a, patch.b, patch.c, patch.d]

    for i in range(n):
        t = i * dt

        # Get vector position with LFO
        x = patch.x
        y = patch.y
        if patch.lfo_x_rate > 0:
            x += math.sin(2 * math.pi * patch.lfo_x_rate * t) * \
                 patch.lfo_x_depth
            x = max(0.0, min(1.0, x))
        if patch.lfo_y_rate > 0:
            y += math.sin(2 * math.pi * patch.lfo_y_rate * t) * \
                 patch.lfo_y_depth
            y = max(0.0, min(1.0, y))

        # Bilinear interpolation weights
        weights = [
            (1 - x) * (1 - y),  # A (top-left)
            x * (1 - y),         # B (top-right)
            (1 - x) * y,         # C (bot-left)
            x * y,               # D (bot-right)
        ]

        # Mix oscillators
        sample = 0.0
        for w, corner in zip(weights, corners):
            if w < 0.001:
                continue
            detune_ratio = 2.0 ** (corner.detune / 1200.0)
            phase = 2 * math.pi * freq * detune_ratio * t + \
                corner.phase_offset
            sample += w * _oscillator(phase, corner.wave_type,
                                       corner.harmonics)

        env = _adsr(t, duration, patch.attack, patch.decay,
                    patch.sustain, patch.release)
        signal[i] = sample * env * patch.master_gain

    return signal


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


VECTOR_PRESETS: dict[str, VectorPatch] = {
    "sweep": VectorPatch(
        "Sweep",
        VectorPoint("sine"), VectorPoint("saw", 8),
        VectorPoint("square", 4), VectorPoint("triangle", 8),
        0.5, 0.5, lfo_x_rate=0.25, lfo_y_rate=0.15,
        lfo_x_depth=0.5, lfo_y_depth=0.5,
    ),
    "phi_morph": VectorPatch(
        "PHI Morph",
        VectorPoint("sine"), VectorPoint("saw", 12),
        VectorPoint("triangle", 6), VectorPoint("square", 8),
        0.5, 0.5,
        lfo_x_rate=1.0 / PHI, lfo_y_rate=1.0 / (PHI * PHI),
        lfo_x_depth=0.5, lfo_y_depth=0.5,
    ),
    "pad": VectorPatch(
        "Pad",
        VectorPoint("sine"), VectorPoint("triangle", 4),
        VectorPoint("sine", 1, 7.0), VectorPoint("triangle", 4, -7.0),
        0.5, 0.5, lfo_x_rate=0.1, lfo_y_rate=0.08,
        attack=0.5, decay=0.5, sustain=0.7, release=1.0,
    ),
    "aggressive": VectorPatch(
        "Aggressive",
        VectorPoint("saw", 16), VectorPoint("square", 8),
        VectorPoint("saw", 12, 15.0), VectorPoint("noise"),
        0.7, 0.3, lfo_x_rate=2.0, lfo_y_rate=1.5,
        lfo_x_depth=0.3, lfo_y_depth=0.2,
    ),
    "evolving": VectorPatch(
        "Evolving",
        VectorPoint("sine"), VectorPoint("saw", 6),
        VectorPoint("square", 3), VectorPoint("triangle", 8),
        0.0, 0.0, lfo_x_rate=0.05, lfo_y_rate=0.03,
        lfo_x_depth=1.0, lfo_y_depth=1.0,
        attack=1.0, release=2.0,
    ),
}


def render_preset(name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = VECTOR_PRESETS.get(name, VECTOR_PRESETS["sweep"])
    signal = render_vector(patch, freq, duration)
    path = os.path.join(output_dir, f"vector_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Vector Synthesis Engine")
    for name, patch in VECTOR_PRESETS.items():
        sig = render_vector(patch, A4_432, 0.5)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: x={patch.x} y={patch.y}, "
              f"lfo_x={patch.lfo_x_rate}Hz, peak={peak:.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
