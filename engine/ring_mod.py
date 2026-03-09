"""
DUBFORGE — Ring Modulation Engine  (Session 160)

Ring modulation, amplitude modulation, and frequency-domain
multiplication with PHI-ratio carrier frequencies.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 48000


@dataclass
class RingModPatch:
    """Ring modulation configuration."""
    name: str = "Ring Mod"
    carrier_freq: float = 440.0
    carrier_type: str = "sine"  # sine, square, triangle, saw
    mod_depth: float = 1.0  # 0=AM, 1=RM
    mix: float = 1.0
    pre_gain: float = 1.0
    post_gain: float = 0.8


def _oscillator(phase: float, wave_type: str) -> float:
    """Generate oscillator sample."""
    if wave_type == "sine":
        return math.sin(phase)
    elif wave_type == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    elif wave_type == "triangle":
        p = (phase % (2 * math.pi)) / (2 * math.pi)
        return 4.0 * abs(p - 0.5) - 1.0
    elif wave_type == "saw":
        p = (phase % (2 * math.pi)) / (2 * math.pi)
        return 2.0 * p - 1.0
    return math.sin(phase)


def ring_modulate(signal: list[float], patch: RingModPatch,
                   sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply ring modulation to a signal."""
    n = len(signal)
    output = [0.0] * n
    dt = 1.0 / sample_rate

    for i in range(n):
        phase = 2.0 * math.pi * patch.carrier_freq * i * dt
        carrier = _oscillator(phase, patch.carrier_type)

        # Ring mod: multiply directly
        # AM: carrier = (1 + depth * carrier) / 2
        if patch.mod_depth >= 1.0:
            mod = carrier
        else:
            mod = 1.0 - patch.mod_depth + patch.mod_depth * carrier

        wet = signal[i] * patch.pre_gain * mod
        output[i] = (wet * patch.mix +
                      signal[i] * (1 - patch.mix)) * patch.post_gain

    return output


def generate_ring_mod(freq: float = 220.0, carrier_freq: float = 440.0,
                       duration: float = 2.0,
                       patch: RingModPatch | None = None,
                       sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate a ring-modulated tone."""
    if patch is None:
        patch = RingModPatch(carrier_freq=carrier_freq)
    else:
        patch.carrier_freq = carrier_freq

    n = int(duration * sample_rate)
    dt = 1.0 / sample_rate

    # Source: sine wave
    source = [math.sin(2 * math.pi * freq * i * dt) for i in range(n)]
    return ring_modulate(source, patch, sample_rate)


def phi_ring_mod(freq: float = 220.0, duration: float = 2.0,
                  sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Ring modulation with PHI-ratio carrier."""
    carrier = freq * PHI
    patch = RingModPatch(
        name="PHI Ring",
        carrier_freq=carrier,
        carrier_type="sine",
        mod_depth=1.0,
    )
    return generate_ring_mod(freq, carrier, duration, patch, sample_rate)


def multi_ring_mod(signal: list[float],
                    carriers: list[float],
                    sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply multiple ring modulation stages."""
    result = list(signal)
    for freq in carriers:
        patch = RingModPatch(carrier_freq=freq)
        result = ring_modulate(result, patch, sample_rate)
    return result


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
RING_MOD_PRESETS: dict[str, RingModPatch] = {
    "classic": RingModPatch("Classic", 440.0, "sine", 1.0),
    "subtle_am": RingModPatch("Subtle AM", 440.0, "sine", 0.3),
    "metallic": RingModPatch("Metallic", 1200.0, "sine", 1.0),
    "harsh": RingModPatch("Harsh", 666.0, "square", 1.0),
    "phi_ratio": RingModPatch("PHI Ratio", A4_432 * PHI, "sine", 1.0),
    "tremolo": RingModPatch("Tremolo", 6.0, "sine", 0.5),
    "robot": RingModPatch("Robot", 150.0, "square", 0.8),
}


def render_preset(name: str, freq: float = 220.0,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = RING_MOD_PRESETS.get(name, RING_MOD_PRESETS["classic"])
    signal = generate_ring_mod(freq, patch.carrier_freq, duration, patch)
    path = os.path.join(output_dir, f"ringmod_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Ring Modulation Engine")
    for name, patch in RING_MOD_PRESETS.items():
        sig = generate_ring_mod(220, patch.carrier_freq, 0.5, patch)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: carrier={patch.carrier_freq:.1f}Hz "
              f"({patch.carrier_type}), depth={patch.mod_depth}, "
              f"peak={peak:.4f}")

    # PHI ring mod
    sig = phi_ring_mod(220, 0.5)
    peak = max(abs(s) for s in sig) if sig else 0
    print(f"  PHI ring: carrier={220 * PHI:.1f}Hz, peak={peak:.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
