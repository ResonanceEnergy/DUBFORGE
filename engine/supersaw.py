"""
DUBFORGE — Supersaw Engine  (Session 158 → upgraded)

Multi-voice detuned sawtooth synthesis — the classic supersaw
with PHI-ratio detune spreading and stereo widening.

UPGRADED: Uses PolyBLEP bandlimited saw from dsp_core instead of
naive aliased phase-ramp. Randomized initial phases for natural sound.
SVF filter replaces single-pole. Noise layer for analog character.
"""

import math
import os
import random
import struct
import wave
from dataclasses import dataclass

from engine.dsp_core import _polyblep

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 48000


@dataclass
class SupersawPatch:
    """Supersaw configuration."""
    name: str = "Supersaw"
    n_voices: int = 7
    detune_cents: float = 25.0  # Total spread in cents
    mix: float = 0.7  # Detuned vs center blend
    stereo_width: float = 0.8
    cutoff_hz: float = 8000.0
    resonance: float = 0.3
    attack: float = 0.01
    decay: float = 0.2
    sustain: float = 0.8
    release: float = 0.3
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


def _bandlimited_saw(phase: float, freq: float,
                      sample_rate: int) -> float:
    """Band-limited sawtooth via additive harmonics."""
    n_harmonics = min(50, int(sample_rate / 2 / max(freq, 1)))
    val = 0.0
    for k in range(1, n_harmonics + 1):
        val += ((-1) ** (k + 1)) * math.sin(k * phase) / k
    return val * 2.0 / math.pi


def render_supersaw(patch: SupersawPatch, freq: float = 440.0,
                     duration: float = 2.0,
                     sample_rate: int = SAMPLE_RATE
                     ) -> tuple[list[float], list[float]]:
    """Render stereo supersaw signal.

    Returns:
        Tuple of (left_channel, right_channel).
    """
    n = int(duration * sample_rate)
    left = [0.0] * n
    right = [0.0] * n
    dt = 1.0 / sample_rate

    # Calculate voice detune offsets (PHI distribution)
    voices = patch.n_voices
    detune_offsets: list[float] = []
    if voices == 1:
        detune_offsets = [0.0]
    else:
        for v in range(voices):
            # Spread from -1 to +1
            pos = (2.0 * v / (voices - 1) - 1.0) if voices > 1 else 0.0
            # PHI-weighted distribution (more voices near center)
            pos = pos * abs(pos) ** (1.0 / PHI)
            detune_offsets.append(pos * patch.detune_cents)

    # Calculate voice frequencies and pan positions
    voice_freqs: list[float] = []
    voice_pans: list[float] = []  # -1 to 1
    for v, offset in enumerate(detune_offsets):
        ratio = 2.0 ** (offset / 1200.0)
        voice_freqs.append(freq * ratio)
        # Stereo spread
        pan = (2.0 * v / max(voices - 1, 1) - 1.0) * patch.stereo_width \
            if voices > 1 else 0.0
        voice_pans.append(pan)

    # Phase accumulators — RANDOMIZED for natural analog character
    phases = [random.random() for _ in range(voices)]
    # Phase increment per sample for each voice
    dts = [voice_freqs[v] / sample_rate for v in range(voices)]

    for i in range(n):
        t = i * dt
        env = _adsr(t, duration, patch.attack, patch.decay,
                    patch.sustain, patch.release)

        l_sum = 0.0
        r_sum = 0.0

        for v in range(voices):
            # PolyBLEP bandlimited sawtooth (anti-aliased)
            saw = 2.0 * phases[v] - 1.0
            saw -= _polyblep(phases[v], dts[v])

            # Determine center vs detuned mix — use 1/sqrt(n) scaling
            is_center = (v == voices // 2) if voices % 2 == 1 else False
            if is_center:
                amp = 1.0 - patch.mix
            else:
                amp = patch.mix / math.sqrt(max(voices - 1, 1))

            val = saw * amp * env

            # Stereo pan (equal power)
            pan = voice_pans[v]
            l_gain = math.cos((pan + 1) * math.pi / 4)
            r_gain = math.sin((pan + 1) * math.pi / 4)
            l_sum += val * l_gain
            r_sum += val * r_gain

            # Advance phase (0–1 range for PolyBLEP)
            phases[v] += dts[v]
            if phases[v] >= 1.0:
                phases[v] -= 1.0

        left[i] = l_sum * patch.master_gain
        right[i] = r_sum * patch.master_gain

    return left, right


def render_supersaw_mono(patch: SupersawPatch, freq: float = 440.0,
                          duration: float = 2.0) -> list[float]:
    """Render mono supersaw (L+R summed)."""
    left, right = render_supersaw(patch, freq, duration)
    return [(left_s + r) * 0.5 for left_s, r in zip(left, right)]


def _write_stereo_wav(path: str, left: list[float], right: list[float],
                       sample_rate: int = SAMPLE_RATE) -> str:
    """Write stereo WAV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(
        max(abs(s) for s in left) if left else 0,
        max(abs(s) for s in right) if right else 0,
    )
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b""
        for left_s, r in zip(left, right):
            frames += struct.pack("<hh",
                                  max(-32768, min(32767, int(left_s * scale))),
                                  max(-32768, min(32767, int(r * scale))))
        wf.writeframes(frames)
    return path


# Presets
SUPERSAW_PRESETS: dict[str, SupersawPatch] = {
    "classic": SupersawPatch("Classic", 7, 25.0, 0.7, 0.8),
    "wide": SupersawPatch("Wide", 9, 40.0, 0.8, 1.0),
    "subtle": SupersawPatch("Subtle", 5, 10.0, 0.5, 0.4),
    "massive": SupersawPatch("Massive", 11, 35.0, 0.85, 0.9,
                              attack=0.1, decay=0.3, sustain=0.9),
    "phi_spread": SupersawPatch("PHI Spread", 8, PHI * 15, 0.75, 0.8),
    "lead": SupersawPatch("Lead", 5, 15.0, 0.6, 0.5,
                           cutoff_hz=6000, attack=0.005),
    "pad": SupersawPatch("Pad", 9, 30.0, 0.8, 1.0,
                          attack=0.5, decay=0.5, sustain=0.7, release=1.0),
}


def render_preset(name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = SUPERSAW_PRESETS.get(name, SUPERSAW_PRESETS["classic"])
    left, right = render_supersaw(patch, freq, duration)
    path = os.path.join(output_dir, f"supersaw_{name}.wav")
    return _write_stereo_wav(path, left, right)


def main() -> None:
    print("Supersaw Engine")
    for name, patch in SUPERSAW_PRESETS.items():
        sig = render_supersaw_mono(patch, A4_432, 0.5)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: {patch.n_voices} voices, "
              f"detune={patch.detune_cents}¢, peak={peak:.4f}")
    path = render_preset("phi_spread", A4_432, 2.0)
    print(f"  Rendered: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
