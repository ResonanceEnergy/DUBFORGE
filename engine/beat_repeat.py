"""
DUBFORGE — Beat Repeat / Stutter Engine  (Session 164)

Rhythmic beat repeat, stutter, and glitch effects with
PHI-ratio timing and probability-driven variations.
"""

import math
import os
import random
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI
from engine.accel import write_wav
SAMPLE_RATE = 48000


@dataclass
class BeatRepeatPatch:
    """Beat repeat configuration."""
    name: str = "Beat Repeat"
    grid: str = "1/8"  # Musical grid division
    repeats: int = 4
    decay: float = 0.0  # Volume decay per repeat (0=none)
    pitch_shift: float = 0.0  # Semitones per repeat
    reverse_probability: float = 0.0
    gate: float = 1.0  # 0=very short, 1=full length
    mix: float = 1.0
    probability: float = 1.0  # Trigger probability
    random_seed: int = 42


# Grid divisions in beats
GRID_VALUES: dict[str, float] = {
    "1/1": 4.0,
    "1/2": 2.0,
    "1/4": 1.0,
    "1/8": 0.5,
    "1/16": 0.25,
    "1/32": 0.125,
    "1/3": 1.0 / 3.0,
    "1/6": 1.0 / 6.0,
    "1/12": 1.0 / 12.0,
    "phi": 1.0 / PHI,
}


def grid_to_samples(grid: str, bpm: float,
                     sample_rate: int = SAMPLE_RATE) -> int:
    """Convert grid division to sample count."""
    beats = GRID_VALUES.get(grid, 0.5)
    seconds = beats * 60.0 / bpm
    return max(1, int(seconds * sample_rate))


def apply_beat_repeat(signal: list[float], patch: BeatRepeatPatch,
                       bpm: float = 140.0,
                       sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply beat repeat effect to a signal."""
    n = len(signal)
    if n == 0:
        return []

    slice_len = grid_to_samples(patch.grid, bpm, sample_rate)
    gate_len = max(1, int(slice_len * patch.gate))
    output = list(signal)  # Copy
    rng = random.Random(patch.random_seed)

    pos = 0
    while pos < n:
        # Check probability
        if rng.random() > patch.probability:
            pos += slice_len
            continue

        # Extract slice
        end = min(pos + slice_len, n)
        slice_data = signal[pos:end]

        for rep in range(patch.repeats):
            write_pos = pos + rep * slice_len
            if write_pos >= n:
                break

            # Apply decay
            amp = (1.0 - patch.decay) ** rep if patch.decay > 0 else 1.0

            # Apply pitch shift (simple resampling)
            if patch.pitch_shift != 0:
                ratio = 2.0 ** (patch.pitch_shift * rep / 12.0)
                resampled = []
                for j in range(gate_len):
                    src_idx = j * ratio
                    src_i = int(src_idx)
                    frac = src_idx - src_i
                    if src_i + 1 < len(slice_data):
                        val = slice_data[src_i] * (1 - frac) + \
                              slice_data[src_i + 1] * frac
                    elif src_i < len(slice_data):
                        val = slice_data[src_i]
                    else:
                        val = 0.0
                    resampled.append(val)
                rep_data = resampled
            else:
                rep_data = slice_data[:gate_len]

            # Reverse probability
            if patch.reverse_probability > 0 and \
                    rng.random() < patch.reverse_probability:
                rep_data = list(reversed(rep_data))

            # Write to output
            for j, val in enumerate(rep_data):
                idx = write_pos + j
                if idx < n:
                    output[idx] = val * amp * patch.mix + \
                                  signal[idx] * (1 - patch.mix)

        pos += slice_len * patch.repeats

    return output


def generate_stutter(freq: float = 110.0, duration: float = 2.0,
                      patch: BeatRepeatPatch | None = None,
                      bpm: float = 140.0,
                      sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate a stuttered tone."""
    if patch is None:
        patch = BeatRepeatPatch()

    n = int(duration * sample_rate)
    dt = 1.0 / sample_rate

    # Source: simple bass tone
    source = [0.0] * n
    for i in range(n):
        t = i * dt
        env = math.exp(-t * 1.5)
        source[i] = env * (
            math.sin(2 * math.pi * freq * t) * 0.6 +
            math.sin(2 * math.pi * freq * 2 * t) * 0.3 +
            math.sin(2 * math.pi * freq * 3 * t) * 0.1
        )

    return apply_beat_repeat(source, patch, bpm, sample_rate)


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(signal, dtype=np.float64) if not isinstance(signal, np.ndarray) else signal
    write_wav(str(path), _s, sample_rate=sample_rate)
    return str(path)



BEAT_REPEAT_PRESETS: dict[str, BeatRepeatPatch] = {
    "classic": BeatRepeatPatch("Classic", "1/8", 4, 0.0),
    "stutter": BeatRepeatPatch("Stutter", "1/16", 8, 0.1),
    "decay": BeatRepeatPatch("Decay", "1/8", 6, 0.2),
    "pitched": BeatRepeatPatch("Pitched", "1/8", 4, 0.0, 2.0),
    "reverse": BeatRepeatPatch("Reverse", "1/8", 4, 0.0, 0.0, 0.5),
    "glitch": BeatRepeatPatch("Glitch", "1/32", 16, 0.15, 1.0, 0.3,
                               0.5, 1.0, 0.7),
    "phi_repeat": BeatRepeatPatch("PHI Repeat", "phi", int(PHI * 3),
                                   1.0 / PHI),
    "halftime": BeatRepeatPatch("Halftime", "1/4", 2, 0.0, 0.0,
                                 0.0, 1.0),
}


def render_preset(name: str, freq: float = 110.0,
                   duration: float = 2.0, bpm: float = 140.0,
                   output_dir: str = "output/drums") -> str:
    patch = BEAT_REPEAT_PRESETS.get(name, BEAT_REPEAT_PRESETS["classic"])
    signal = generate_stutter(freq, duration, patch, bpm)
    path = os.path.join(output_dir, f"beat_repeat_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Beat Repeat / Stutter Engine")
    for name, patch in BEAT_REPEAT_PRESETS.items():
        sig = generate_stutter(110, 1.0, patch, 140)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: grid={patch.grid}, reps={patch.repeats}, "
              f"peak={peak:.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
