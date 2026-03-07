"""
DUBFORGE Engine — PHI CORE Wavetable Generator

Generates Serum-compatible wavetables using phi-spaced additive partials.
Based on Dan Winter's Planck x phi fractal mathematics doctrine.

Outputs:
    output/wavetables/DUBFORGE_PHI_CORE.wav
    output/wavetables/DUBFORGE_PHI_CORE_v2_WOOK.wav
"""

import numpy as np
import struct
import os
import math as _math
from pathlib import Path

from engine.config_loader import PHI, FIBONACCI, A4_432, A4_440

# --- Constants -----------------------------------------------------------

SAMPLE_RATE = 44100
WAVETABLE_SIZE = 2048      # Serum standard single-cycle length
DEFAULT_FRAMES = 256       # Serum max wavetable frames


# --- Helpers --------------------------------------------------------------

def phi_harmonic_series(fundamental: float, n_partials: int) -> list[float]:
    """Generate a harmonic series where each partial is fundamental * phi^k."""
    return [fundamental * (PHI ** k) for k in range(n_partials)]


def fibonacci_harmonic_series(fundamental: float) -> list[float]:
    """Generate partials at Fibonacci-integer multiples of fundamental."""
    return [fundamental * f for f in FIBONACCI if fundamental * f < SAMPLE_RATE / 2]


def generate_frame(partials: list[float], amplitudes: list[float],
                   size: int = WAVETABLE_SIZE) -> np.ndarray:
    """Render one wavetable frame from partials + amplitudes."""
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)
    frame = np.zeros(size, dtype=np.float64)
    for freq, amp in zip(partials, amplitudes):
        # Normalize freq to single-cycle: partial index relative to fundamental
        frame += amp * np.sin(freq * t)
    # Normalize to [-1, 1]
    peak = np.max(np.abs(frame))
    if peak > 0:
        frame /= peak
    return frame


def phi_amplitude_curve(n: int, decay: float = 1.0) -> list[float]:
    """Amplitude envelope: 1 / phi^(k * decay) for each partial."""
    return [1.0 / (PHI ** (k * decay)) for k in range(n)]


def morph_frames(frame_a: np.ndarray, frame_b: np.ndarray,
                 steps: int) -> list[np.ndarray]:
    """Fractal-weighted interpolation between two frames."""
    frames = []
    for i in range(steps):
        # phi-weighted morph position (non-linear)
        t_linear = i / max(steps - 1, 1)
        t_phi = t_linear ** PHI  # fractal curve
        blended = (1 - t_phi) * frame_a + t_phi * frame_b
        peak = np.max(np.abs(blended))
        if peak > 0:
            blended /= peak
        frames.append(blended)
    return frames


# --- Frequency / MIDI utilities -------------------------------------------

def midi_to_freq(midi_note: int, a4: float = A4_440) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return a4 * (2.0 ** ((midi_note - 69) / 12.0))


def freq_to_midi(freq: float, a4: float = A4_440) -> int:
    """Convert frequency in Hz to nearest MIDI note number."""
    if freq <= 0:
        return 0
    return round(69 + 12.0 * _math.log2(freq / a4))


# --- WAV Writer (16-bit PCM, Serum compatible) ----------------------------

def write_wav(path: str, frames: list[np.ndarray], sample_rate: int = SAMPLE_RATE):
    """Write a multi-frame wavetable as a single WAV file (Serum-ready)."""
    all_samples = np.concatenate(frames)
    # 16-bit PCM
    pcm = (all_samples * 32767).astype(np.int16)
    num_samples = len(pcm)
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    file_size = 36 + data_size

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', file_size))
        f.write(b'WAVE')
        # fmt chunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))        # chunk size
        f.write(struct.pack('<H', 1))         # PCM
        f.write(struct.pack('<H', 1))         # mono
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * 2))  # byte rate
        f.write(struct.pack('<H', 2))         # block align
        f.write(struct.pack('<H', 16))        # bits per sample
        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(pcm.tobytes())

    # Write Serum clm marker (wavetable size hint)
    # Serum looks for "clm " chunk with frame size
    # Re-open and append
    with open(path, 'r+b') as f:
        f.seek(0, 2)  # end of file
        clm_data = f"<!>{WAVETABLE_SIZE} 0".encode('ascii')
        f.write(b'clm ')
        f.write(struct.pack('<I', len(clm_data)))
        f.write(clm_data)
        # Update RIFF size
        new_file_size = f.tell() - 8
        f.seek(4)
        f.write(struct.pack('<I', new_file_size))


# --- Wavetable Generators ------------------------------------------------

def generate_phi_core_v1(n_frames: int = DEFAULT_FRAMES) -> list[np.ndarray]:
    """
    PHI CORE v1: Clean phi-partial wavetable.
    Morphs from pure sine through increasing phi-harmonic density.
    """
    frames = []
    max_partials = 13  # Fibonacci count

    for i in range(n_frames):
        progress = i / max(n_frames - 1, 1)
        # Number of active partials grows with frame index
        n_active = max(1, int(progress * max_partials) + 1)

        partials = list(range(1, n_active + 1))  # integer partial indices
        # Weight by phi decay
        amps = phi_amplitude_curve(n_active, decay=1.0 - progress * 0.5)

        t = np.linspace(0, 2 * np.pi, WAVETABLE_SIZE, endpoint=False)
        frame = np.zeros(WAVETABLE_SIZE, dtype=np.float64)

        for p, a in zip(partials, amps):
            # phi-shifted partials: actual ratio is p * phi^(progress)
            ratio = p * (PHI ** (progress * 0.5))
            frame += a * np.sin(ratio * t)

        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak
        frames.append(frame)

    return frames


def generate_phi_core_v2_wook(n_frames: int = DEFAULT_FRAMES) -> list[np.ndarray]:
    """
    PHI CORE v2 — WOOK EDITION: Deeper, dirtier, more fractal density.
    Adds sub-harmonic folding + distortion saturation curve.
    """
    frames = []
    max_partials = 21  # more partials for wook grit

    for i in range(n_frames):
        progress = i / max(n_frames - 1, 1)
        n_active = max(1, int(progress * max_partials) + 1)

        t = np.linspace(0, 2 * np.pi, WAVETABLE_SIZE, endpoint=False)
        frame = np.zeros(WAVETABLE_SIZE, dtype=np.float64)

        for k in range(n_active):
            # Fibonacci-weighted partial frequency
            fib_idx = k % len(FIBONACCI)
            ratio = FIBONACCI[fib_idx] * (PHI ** (progress * 0.8))
            amp = 1.0 / (PHI ** (k * 0.6))

            # Sub-harmonic folding for wook depth
            if k % 3 == 0:
                ratio *= 0.5  # octave down fold

            frame += amp * np.sin(ratio * t)

        # Soft-clip saturation (wook grit)
        frame = np.tanh(frame * (1.0 + progress * 2.0))

        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak
        frames.append(frame)

    return frames


# --- Main -----------------------------------------------------------------

def main() -> None:
    out_dir = Path('output/wavetables')
    out_dir.mkdir(parents=True, exist_ok=True)

    print('Generating PHI CORE v1...')
    v1_frames = generate_phi_core_v1()
    v1_path = str(out_dir / 'DUBFORGE_PHI_CORE.wav')
    write_wav(v1_path, v1_frames)
    print(f'  -> {v1_path}  ({len(v1_frames)} frames x {WAVETABLE_SIZE} samples)')

    print('Generating PHI CORE v2 — WOOK EDITION...')
    v2_frames = generate_phi_core_v2_wook()
    v2_path = str(out_dir / 'DUBFORGE_PHI_CORE_v2_WOOK.wav')
    write_wav(v2_path, v2_frames)
    print(f'  -> {v2_path}  ({len(v2_frames)} frames x {WAVETABLE_SIZE} samples)')

    print('Done.')


if __name__ == '__main__':
    main()
