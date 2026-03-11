"""
DUBFORGE — Additive Synthesis Engine  (Session 157)

Build sounds from individual sine harmonics with per-partial
envelopes, PHI-spaced partials, and spectral morphing.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI
A4_432 = 432.0
SAMPLE_RATE = 48000


@dataclass
class Partial:
    """A single harmonic partial."""
    harmonic: float = 1.0  # Frequency multiplier
    amplitude: float = 1.0
    phase: float = 0.0
    attack: float = 0.01
    decay: float = 0.1
    sustain: float = 0.7
    release: float = 0.3
    detune_cents: float = 0.0


@dataclass
class AdditivePatch:
    """Additive synthesis patch."""
    name: str = "Additive Patch"
    partials: list[Partial] = field(default_factory=list)
    master_gain: float = 0.8

    def __post_init__(self):
        if not self.partials:
            # Default: first 8 harmonics with 1/n rolloff
            self.partials = [
                Partial(
                    harmonic=float(i),
                    amplitude=1.0 / i,
                    phase=0.0,
                    attack=0.01 * i,
                    decay=0.1,
                    sustain=max(0.1, 0.8 - 0.1 * i),
                    release=0.3,
                )
                for i in range(1, 9)
            ]


def _adsr(t: float, dur: float, a: float, d: float,
          s: float, r: float) -> float:
    """ADSR envelope."""
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


def render_additive(patch: AdditivePatch, freq: float = 440.0,
                     duration: float = 2.0,
                     sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render additive synthesis."""
    n = int(duration * sample_rate)
    signal = [0.0] * n
    dt = 1.0 / sample_rate
    nyquist = sample_rate / 2.0

    for partial in patch.partials:
        # Detune in cents
        detune_ratio = 2.0 ** (partial.detune_cents / 1200.0)
        p_freq = freq * partial.harmonic * detune_ratio

        # Skip if above Nyquist
        if p_freq >= nyquist:
            continue

        omega = 2.0 * math.pi * p_freq
        for i in range(n):
            t = i * dt
            env = _adsr(t, duration, partial.attack, partial.decay,
                        partial.sustain, partial.release)
            signal[i] += (partial.amplitude * env *
                          math.sin(omega * t + partial.phase))

    # Normalize
    peak = max(abs(s) for s in signal) if signal else 1.0
    if peak > 0:
        scale = patch.master_gain / peak
        signal = [s * scale for s in signal]

    return signal


def phi_partials(n_partials: int = 8,
                  base_amp: float = 1.0) -> list[Partial]:
    """Generate PHI-spaced partials."""
    partials = []
    for i in range(n_partials):
        ratio = PHI ** i
        amp = base_amp / (i + 1)
        partials.append(Partial(
            harmonic=ratio,
            amplitude=amp,
            attack=0.01 * (i + 1),
            decay=0.2,
            sustain=max(0.1, 0.7 - 0.08 * i),
            release=0.3 + 0.1 * i,
        ))
    return partials


def harmonic_partials(n_harmonics: int = 16,
                       rolloff: str = "natural") -> list[Partial]:
    """Generate standard harmonic partials."""
    partials = []
    for i in range(1, n_harmonics + 1):
        if rolloff == "natural":
            amp = 1.0 / i
        elif rolloff == "square":
            amp = 1.0 / i if i % 2 == 1 else 0.0
        elif rolloff == "sawtooth":
            amp = 1.0 / i
        elif rolloff == "triangle":
            amp = (1.0 / (i * i)) if i % 2 == 1 else 0.0
        else:
            amp = 1.0 / i

        if amp > 0:
            partials.append(Partial(
                harmonic=float(i),
                amplitude=amp,
            ))
    return partials


def morph_patches(patch_a: AdditivePatch, patch_b: AdditivePatch,
                   blend: float = 0.5) -> AdditivePatch:
    """Morph between two additive patches."""
    inv = 1.0 - blend
    n = max(len(patch_a.partials), len(patch_b.partials))
    partials = []

    for i in range(n):
        a = patch_a.partials[i] if i < len(patch_a.partials) else Partial()
        b = patch_b.partials[i] if i < len(patch_b.partials) else Partial()

        partials.append(Partial(
            harmonic=a.harmonic * inv + b.harmonic * blend,
            amplitude=a.amplitude * inv + b.amplitude * blend,
            phase=a.phase * inv + b.phase * blend,
            attack=a.attack * inv + b.attack * blend,
            decay=a.decay * inv + b.decay * blend,
            sustain=a.sustain * inv + b.sustain * blend,
            release=a.release * inv + b.release * blend,
            detune_cents=a.detune_cents * inv + b.detune_cents * blend,
        ))

    return AdditivePatch(
        name=f"Morph({patch_a.name},{patch_b.name},{blend:.2f})",
        partials=partials,
        master_gain=patch_a.master_gain * inv + patch_b.master_gain * blend,
    )


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


# Preset patches
ADDITIVE_PRESETS: dict[str, AdditivePatch] = {
    "organ": AdditivePatch(
        name="Organ",
        partials=harmonic_partials(8, "natural"),
    ),
    "hollow": AdditivePatch(
        name="Hollow",
        partials=harmonic_partials(8, "square"),
    ),
    "bright_saw": AdditivePatch(
        name="Bright Saw",
        partials=harmonic_partials(16, "sawtooth"),
    ),
    "soft_triangle": AdditivePatch(
        name="Soft Triangle",
        partials=harmonic_partials(8, "triangle"),
    ),
    "phi_bell": AdditivePatch(
        name="PHI Bell",
        partials=phi_partials(8),
    ),
    "phi_pad": AdditivePatch(
        name="PHI Pad",
        partials=[
            Partial(PHI ** i, 1.0 / (i + 1), 0.0,
                    0.5, 0.3, 0.6, 1.0, i * 3.0)
            for i in range(6)
        ],
    ),
}


def render_preset(name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = ADDITIVE_PRESETS.get(name, ADDITIVE_PRESETS["organ"])
    signal = render_additive(patch, freq, duration)
    path = os.path.join(output_dir, f"additive_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Additive Synthesis Engine")
    for name, patch in ADDITIVE_PRESETS.items():
        sig = render_additive(patch, A4_432, 0.5)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: {len(patch.partials)} partials, "
              f"{len(sig)} samples, peak={peak:.4f}")

    # Morph test
    a = ADDITIVE_PRESETS["organ"]
    b = ADDITIVE_PRESETS["phi_bell"]
    morphed = morph_patches(a, b, 0.5)
    sig = render_additive(morphed, A4_432, 0.5)
    print(f"  morph: {len(sig)} samples")
    print("Done.")


if __name__ == "__main__":
    main()
