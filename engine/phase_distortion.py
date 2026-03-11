"""
DUBFORGE — Phase Distortion Synthesis Engine  (Session 161)

CZ-style phase distortion synthesis — reshapes waveforms by
manipulating the phase function instead of the amplitude.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000


@dataclass
class PDPatch:
    """Phase distortion patch."""
    name: str = "PD"
    distortion: float = 0.8  # 0=sine, 1=max distortion
    pd_type: str = "sawtooth"  # sawtooth, square, pulse, resonant
    attack: float = 0.01
    decay: float = 0.3
    sustain: float = 0.5
    release: float = 0.3
    pd_envelope: float = 1.0  # Envelope modulation of distortion
    master_gain: float = 0.8


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


def _pd_sawtooth(phase: float, d: float) -> float:
    """Phase distortion → sawtooth-like."""
    # Remap phase: compress first half, expand second
    t = phase / (2 * math.pi)  # 0 to 1
    if t < d:
        mapped = t / (2 * d) if d > 0 else 0.5
    else:
        mapped = 0.5 + (t - d) / (2 * (1 - d)) if d < 1 else 0.5
    return math.sin(2 * math.pi * mapped)


def _pd_square(phase: float, d: float) -> float:
    """Phase distortion → square-like."""
    t = phase / (2 * math.pi)
    # Two compressed half-cycles
    pw = 0.5 * d + 0.25  # Pulse width
    if t < pw:
        mapped = t / (2 * pw) if pw > 0 else 0.25
    else:
        mapped = 0.5 + (t - pw) / (2 * (1 - pw)) if pw < 1 else 0.75
    return math.sin(2 * math.pi * mapped)


def _pd_pulse(phase: float, d: float) -> float:
    """Phase distortion → narrow pulse."""
    t = phase / (2 * math.pi)
    width = max(0.01, 0.5 * (1 - d))
    if t < width:
        mapped = t / (2 * width)
    else:
        mapped = 0.5 + (t - width) / (2 * (1 - width))
    return math.sin(2 * math.pi * mapped)


def _pd_resonant(phase: float, d: float) -> float:
    """Phase distortion → resonant peak (like CZ resonance)."""
    t = phase / (2 * math.pi)
    # Window function creates resonant peak
    n_cycles = 1 + int(d * 7)  # 1 to 8 cycles within one period
    window = math.sin(math.pi * t)  # Half-sine window
    return window * math.sin(2 * math.pi * n_cycles * t)


PD_ALGORITHMS: dict[str, callable] = {
    "sawtooth": _pd_sawtooth,
    "square": _pd_square,
    "pulse": _pd_pulse,
    "resonant": _pd_resonant,
}


def render_pd(patch: PDPatch, freq: float = 440.0,
              duration: float = 2.0,
              sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render phase distortion synthesis."""
    n = int(duration * sample_rate)
    signal = [0.0] * n
    dt = 1.0 / sample_rate
    pd_fn = PD_ALGORITHMS.get(patch.pd_type, _pd_sawtooth)

    for i in range(n):
        t = i * dt
        phase = (2 * math.pi * freq * t) % (2 * math.pi)

        # Envelope
        env = _adsr(t, duration, patch.attack, patch.decay,
                    patch.sustain, patch.release)

        # Modulate distortion with envelope
        d = patch.distortion * (1.0 - patch.pd_envelope +
                                 patch.pd_envelope * env)
        d = max(0.01, min(0.99, d))

        signal[i] = pd_fn(phase, d) * env * patch.master_gain

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


# Presets
PD_PRESETS: dict[str, PDPatch] = {
    "cz_saw": PDPatch("CZ Saw", 0.8, "sawtooth", 0.01, 0.3, 0.5, 0.3, 0.8),
    "cz_square": PDPatch("CZ Square", 0.7, "square", 0.01, 0.2, 0.6, 0.3,
                          0.6),
    "thin_pulse": PDPatch("Thin Pulse", 0.9, "pulse", 0.005, 0.1, 0.4, 0.2,
                           0.9),
    "resonant": PDPatch("Resonant", 0.6, "resonant", 0.01, 0.4, 0.3, 0.5,
                         0.7),
    "phi_pd": PDPatch("PHI PD", 1.0 / PHI, "sawtooth", 0.01, 0.2,
                       1.0 / PHI, 0.3, 0.8),
    "bass_pd": PDPatch("Bass PD", 0.5, "sawtooth", 0.005, 0.1, 0.7, 0.2,
                        0.5, master_gain=0.9),
    "pad_pd": PDPatch("Pad PD", 0.3, "resonant", 0.5, 0.5, 0.6, 1.0, 0.3,
                       master_gain=0.7),
}


def render_preset(name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = PD_PRESETS.get(name, PD_PRESETS["cz_saw"])
    signal = render_pd(patch, freq, duration)
    path = os.path.join(output_dir, f"pd_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Phase Distortion Synthesis Engine")
    for name, patch in PD_PRESETS.items():
        sig = render_pd(patch, A4_432, 0.5)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name} ({patch.pd_type}): d={patch.distortion:.2f}, "
              f"peak={peak:.4f}")
    path = render_preset("phi_pd", A4_432, 2.0)
    print(f"  Rendered: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
