"""
DUBFORGE — FM Synthesis Engine  (Session 156)

Frequency Modulation synthesis with operator stacks,
feedback loops, and PHI-ratio harmonics.
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
class FMOperator:
    """A single FM operator."""
    freq_ratio: float = 1.0
    amplitude: float = 1.0
    mod_index: float = 1.0
    feedback: float = 0.0
    phase: float = 0.0
    envelope: tuple[float, float, float, float] = (0.01, 0.1, 0.7, 0.3)
    # (attack, decay, sustain_level, release)


@dataclass
class FMPatch:
    """FM synthesis patch with multiple operators."""
    name: str = "FM Patch"
    operators: list[FMOperator] = field(default_factory=list)
    algorithm: int = 0  # 0=serial, 1=parallel, 2=mixed
    master_gain: float = 0.8

    def __post_init__(self):
        if not self.operators:
            self.operators = [
                FMOperator(1.0, 1.0, 2.0),
                FMOperator(PHI, 0.5, 1.5),
            ]


def _adsr_envelope(t: float, dur: float,
                    attack: float, decay: float,
                    sustain: float, release: float) -> float:
    """ADSR envelope generator."""
    rel_start = dur - release
    if t < attack:
        return t / attack if attack > 0 else 1.0
    elif t < attack + decay:
        return 1.0 - (1.0 - sustain) * ((t - attack) / decay)
    elif t < rel_start:
        return sustain
    elif t < dur:
        return sustain * (1.0 - (t - rel_start) / release)
    return 0.0


def render_fm(patch: FMPatch, freq: float = 440.0,
              duration: float = 2.0,
              sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render FM synthesis to signal."""
    n_samples = int(duration * sample_rate)
    signal = [0.0] * n_samples
    ops = patch.operators
    n_ops = len(ops)

    if n_ops == 0:
        return signal

    # Pre-compute phase increments
    dt = 1.0 / sample_rate
    prev_out = [0.0] * n_ops

    for i in range(n_samples):
        t = i * dt

        if patch.algorithm == 0:
            # Serial: each op modulates the next
            mod = 0.0
            for j in range(n_ops - 1, -1, -1):
                op = ops[j]
                env = _adsr_envelope(
                    t, duration,
                    op.envelope[0], op.envelope[1],
                    op.envelope[2], op.envelope[3],
                )
                phase = 2.0 * math.pi * freq * op.freq_ratio * t
                fb = op.feedback * prev_out[j]
                val = env * op.amplitude * math.sin(
                    phase + op.mod_index * mod + fb
                )
                prev_out[j] = val
                mod = val

            signal[i] = mod * patch.master_gain

        elif patch.algorithm == 1:
            # Parallel: all ops added together
            total = 0.0
            for j, op in enumerate(ops):
                env = _adsr_envelope(
                    t, duration,
                    op.envelope[0], op.envelope[1],
                    op.envelope[2], op.envelope[3],
                )
                phase = 2.0 * math.pi * freq * op.freq_ratio * t
                fb = op.feedback * prev_out[j]
                val = env * op.amplitude * math.sin(phase + fb)
                prev_out[j] = val
                total += val
            signal[i] = total / n_ops * patch.master_gain

        else:
            # Mixed: first half modulates, second half parallel
            mid = n_ops // 2
            mod = 0.0
            for j in range(mid - 1, -1, -1):
                op = ops[j]
                env = _adsr_envelope(
                    t, duration,
                    op.envelope[0], op.envelope[1],
                    op.envelope[2], op.envelope[3],
                )
                phase = 2.0 * math.pi * freq * op.freq_ratio * t
                fb = op.feedback * prev_out[j]
                val = env * op.amplitude * math.sin(
                    phase + op.mod_index * mod + fb
                )
                prev_out[j] = val
                mod = val

            parallel = 0.0
            p_count = n_ops - mid
            for j in range(mid, n_ops):
                op = ops[j]
                env = _adsr_envelope(
                    t, duration,
                    op.envelope[0], op.envelope[1],
                    op.envelope[2], op.envelope[3],
                )
                phase = 2.0 * math.pi * freq * op.freq_ratio * t
                fb = op.feedback * prev_out[j]
                val = env * op.amplitude * math.sin(
                    phase + mod * op.mod_index + fb
                )
                prev_out[j] = val
                parallel += val

            signal[i] = (mod + parallel / max(p_count, 1)) / 2 * \
                patch.master_gain

    return signal


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    """Write signal to WAV file."""
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


# Preset FM patches
FM_PRESETS: dict[str, FMPatch] = {
    "electric_piano": FMPatch(
        name="Electric Piano",
        operators=[
            FMOperator(1.0, 1.0, 3.5, 0.0, 0.0, (0.001, 0.3, 0.0, 0.5)),
            FMOperator(1.0, 0.7, 2.0, 0.0, 0.0, (0.001, 0.1, 0.4, 0.3)),
        ],
        algorithm=0, master_gain=0.7,
    ),
    "metallic_bass": FMPatch(
        name="Metallic Bass",
        operators=[
            FMOperator(1.0, 1.0, 5.0, 0.3, 0.0, (0.005, 0.2, 0.3, 0.2)),
            FMOperator(PHI, 0.8, 3.0, 0.0, 0.0, (0.001, 0.1, 0.5, 0.3)),
            FMOperator(3.0, 0.3, 1.0, 0.0, 0.0, (0.001, 0.05, 0.0, 0.1)),
        ],
        algorithm=0, master_gain=0.8,
    ),
    "phi_bell": FMPatch(
        name="PHI Bell",
        operators=[
            FMOperator(1.0, 1.0, 4.0, 0.0, 0.0, (0.001, 0.5, 0.0, 1.0)),
            FMOperator(PHI, 0.6, 2.5, 0.0, 0.0, (0.001, 0.3, 0.0, 0.8)),
            FMOperator(PHI * PHI, 0.3, 1.5, 0.0, 0.0,
                       (0.001, 0.2, 0.0, 0.6)),
        ],
        algorithm=2, master_gain=0.6,
    ),
    "growl": FMPatch(
        name="Growl",
        operators=[
            FMOperator(1.0, 1.0, 8.0, 0.5, 0.0, (0.01, 0.05, 0.8, 0.2)),
            FMOperator(2.0, 0.9, 6.0, 0.3, 0.0, (0.01, 0.1, 0.7, 0.2)),
            FMOperator(3.0, 0.4, 3.0, 0.0, 0.0, (0.001, 0.05, 0.5, 0.1)),
        ],
        algorithm=0, master_gain=0.7,
    ),
    "pad_atmosphere": FMPatch(
        name="Pad Atmosphere",
        operators=[
            FMOperator(1.0, 1.0, 1.5, 0.0, 0.0, (0.5, 0.5, 0.7, 1.0)),
            FMOperator(2.0, 0.3, 0.8, 0.0, 0.0, (0.3, 0.3, 0.5, 0.8)),
            FMOperator(PHI, 0.2, 0.5, 0.0, 0.0, (0.8, 0.2, 0.6, 1.2)),
        ],
        algorithm=1, master_gain=0.6,
    ),
}


def render_preset(preset_name: str, freq: float = A4_432,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    """Render a preset FM patch to WAV."""
    patch = FM_PRESETS.get(preset_name)
    if not patch:
        patch = FM_PRESETS["phi_bell"]
    signal = render_fm(patch, freq, duration)
    path = os.path.join(output_dir, f"fm_{preset_name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("FM Synthesis Engine")
    for name, patch in FM_PRESETS.items():
        signal = render_fm(patch, A4_432, 1.0)
        peak = max(abs(s) for s in signal) if signal else 0
        print(f"  {name}: {len(signal)} samples, peak={peak:.4f}")
    path = render_preset("phi_bell", A4_432, 2.0)
    print(f"  Rendered: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
