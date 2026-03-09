"""
DUBFORGE — Karplus-Strong Engine  (Session 186)

Physical modeling string synthesis using Karplus-Strong
with extensions: damping, detuning, and PHI harmonics.
"""

import math
import os
import random
import struct
import wave
from dataclasses import dataclass

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 44100


@dataclass
class KarplusStrongPatch:
    """Parameters for Karplus-Strong synthesis."""
    frequency: float = 110.0
    duration: float = 2.0
    damping: float = 0.5
    brightness: float = 0.5
    stretch: float = 0.0
    pluck_position: float = 0.5
    feedback: float = 0.998
    noise_mix: float = 1.0
    pickup_position: float = 0.25

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "duration": self.duration,
            "damping": self.damping,
            "brightness": self.brightness,
            "stretch": self.stretch,
            "pluck_position": self.pluck_position,
        }


def render_ks(patch: KarplusStrongPatch | None = None,
              sample_rate: int = SAMPLE_RATE,
              seed: int = 42) -> list[float]:
    """Render Karplus-Strong synthesis."""
    p = patch or KarplusStrongPatch()
    rng = random.Random(seed)

    n_samples = int(p.duration * sample_rate)
    freq = max(20, min(p.frequency, sample_rate / 2))
    period = sample_rate / freq
    delay_length = int(period)

    if delay_length < 2:
        delay_length = 2

    # Initialize delay line with noise burst
    delay_line = [0.0] * delay_length
    for i in range(delay_length):
        # Pluck position affects initial excitation
        pos = i / delay_length
        pluck_env = 1.0 - abs(2 * pos - 1) ** (1.0 / max(p.pluck_position, 0.01))
        noise = rng.uniform(-1, 1) * p.noise_mix
        delay_line[i] = noise * pluck_env

    # Synthesis
    signal: list[float] = []
    write_pos = 0

    # Damping filter coefficient
    _damp = 0.3 + p.damping * 0.4
    bright = p.brightness
    prev = 0.0

    for _ in range(n_samples):
        # Read from delay line
        read_pos = (write_pos - delay_length) % delay_length
        read_pos2 = (read_pos + 1) % delay_length

        # Fractional delay interpolation
        frac = period - int(period)
        sample = delay_line[read_pos] * (1 - frac) + delay_line[read_pos2] * frac

        # Pickup position (comb filter effect)
        pickup_delay = int(delay_length * p.pickup_position)
        pickup_pos = (write_pos - pickup_delay) % delay_length
        sample = sample * 0.7 + delay_line[pickup_pos] * 0.3

        # One-pole lowpass (brightness)
        filtered = bright * sample + (1.0 - bright) * prev
        prev = filtered

        # Stiffness / stretch
        if p.stretch > 0:
            stretch_delay = int(delay_length * (1 + p.stretch * 0.1))
            sd_pos = (write_pos - stretch_delay) % delay_length
            filtered = filtered * 0.8 + delay_line[sd_pos] * 0.2 * p.stretch

        # Write back with feedback
        delay_line[write_pos % delay_length] = filtered * p.feedback

        signal.append(filtered)
        write_pos = (write_pos + 1) % delay_length

    return signal


def render_ks_chord(notes: list[float], duration: float = 2.0,
                     damping: float = 0.5,
                     sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render a chord using Karplus-Strong."""
    n_samples = int(duration * sample_rate)
    mixed = [0.0] * n_samples

    for freq in notes:
        patch = KarplusStrongPatch(
            frequency=freq,
            duration=duration,
            damping=damping,
        )
        sig = render_ks(patch, sample_rate)
        for i in range(min(len(sig), n_samples)):
            mixed[i] += sig[i] / len(notes)

    return mixed


def phi_string(root_freq: float = 110.0, n_strings: int = 5,
               duration: float = 3.0,
               sample_rate: int = SAMPLE_RATE) -> list[float]:
    """PHI-spaced string resonance."""
    n_samples = int(duration * sample_rate)
    mixed = [0.0] * n_samples

    for i in range(n_strings):
        freq = root_freq * (PHI ** (i * 0.5))
        patch = KarplusStrongPatch(
            frequency=freq,
            duration=duration,
            damping=0.3 + i * 0.1,
            brightness=0.7 - i * 0.1,
        )
        sig = render_ks(patch, sample_rate, seed=42 + i)
        for j in range(min(len(sig), n_samples)):
            mixed[j] += sig[j] / n_strings

    return mixed


# Presets
KS_PRESETS: dict[str, KarplusStrongPatch] = {
    "guitar": KarplusStrongPatch(
        frequency=110.0, duration=2.0, damping=0.4,
        brightness=0.6, pluck_position=0.3,
    ),
    "bass": KarplusStrongPatch(
        frequency=55.0, duration=3.0, damping=0.6,
        brightness=0.3, pluck_position=0.5,
    ),
    "harp": KarplusStrongPatch(
        frequency=440.0, duration=4.0, damping=0.2,
        brightness=0.8, pluck_position=0.15,
    ),
    "sitar": KarplusStrongPatch(
        frequency=220.0, duration=3.0, damping=0.3,
        brightness=0.7, stretch=0.3, pluck_position=0.1,
    ),
    "bell": KarplusStrongPatch(
        frequency=880.0, duration=5.0, damping=0.1,
        brightness=0.9, stretch=0.5, feedback=0.999,
    ),
    "phi_string": KarplusStrongPatch(
        frequency=A4_432 / PHI, duration=3.0, damping=0.35,
        brightness=0.618, pluck_position=1.0 / PHI,
    ),
}


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


def main() -> None:
    print("Karplus-Strong Engine")

    for name, preset in KS_PRESETS.items():
        sig = render_ks(preset)
        rms = math.sqrt(sum(x * x for x in sig) / len(sig))
        print(f"  {name:>12}: {preset.frequency:.0f} Hz, "
              f"RMS={20 * math.log10(max(rms, 1e-10)):.1f} dB")

    # PHI string
    phi_sig = phi_string(80.0, 5, 2.0)
    path = _write_wav("output/wavetables/phi_string_ks.wav", phi_sig)
    print(f"\n  PHI string: {path}")

    # Chord
    chord = render_ks_chord([110.0, 138.59, 164.81], 2.0)
    path = _write_wav("output/wavetables/ks_chord.wav", chord)
    print(f"  Chord: {path}")

    print("Done.")


if __name__ == "__main__":
    main()
