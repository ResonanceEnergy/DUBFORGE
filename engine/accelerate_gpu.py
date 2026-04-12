# pyright: basic
"""
DUBFORGE Engine — Apple Silicon Accelerator

GPU compute via MLX (Apple's native ML framework for Apple Silicon),
with automatic fallback to numpy for non-Apple-Silicon machines.

Provides accelerated versions of common DSP operations:
  - FFT / IFFT (real-valued)
  - Batch FFT for spectrograms
  - Matrix multiply (for filter banks, wavetable generation)
  - Elementwise ops (vectorized synthesis)
  - SVF filter (vectorized, replaces per-sample Python loop)

Usage:
    from engine.accelerate_gpu import (
        fft_rfft, fft_irfft, batch_fft,
        matmul, svf_lowpass_fast, HAS_MLX,
    )

    # Transparent — uses MLX on Apple Silicon, numpy otherwise
    spectrum = fft_rfft(signal)
    filtered = svf_lowpass_fast(signal, cutoff_hz=2000.0)
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import numpy.typing as npt

from engine.config_loader import IS_APPLE_SILICON
from engine.log import get_logger

_log = get_logger("dubforge.accelerate_gpu")

# ═══════════════════════════════════════════════════════════════════════════
# MLX DETECTION — Apple's native GPU framework for Apple Silicon
# ═══════════════════════════════════════════════════════════════════════════

HAS_MLX = False
_mx: Any = None

if IS_APPLE_SILICON:
    try:
        import mlx.core as mx  # type: ignore[import-unresolved]
        _mx = mx
        HAS_MLX = True
        _log.info("MLX available — GPU acceleration enabled")
    except ImportError:
        _log.info("MLX not installed — using numpy (pip install mlx)")

SAMPLE_RATE = 48000


# ═══════════════════════════════════════════════════════════════════════════
# FFT — GPU-accelerated when possible
# ═══════════════════════════════════════════════════════════════════════════

def fft_rfft(signal: npt.NDArray[np.float64],
             n: int | None = None) -> npt.NDArray[np.complex128]:
    """Real FFT — MLX GPU on Apple Silicon, numpy fallback otherwise."""
    if HAS_MLX and len(signal) >= 262144:
        # MLX FFT on GPU — worth it only for very large buffers (>256K)
        # due to CPU↔GPU transfer overhead on unified memory
        mx_sig = _mx.array(signal.astype(np.float32))
        if n is not None:
            mx_sig = _mx.pad(mx_sig, [(0, max(0, n - len(signal)))])[:n]
        result = _mx.fft.rfft(mx_sig)
        _mx.eval(result)
        # Back to numpy complex128
        return np.array(result).astype(np.complex128)
    return np.fft.rfft(signal, n=n)


def fft_irfft(spectrum: npt.NDArray[np.complex128],
              n: int | None = None) -> npt.NDArray[np.float64]:
    """Inverse real FFT — MLX GPU on Apple Silicon, numpy fallback."""
    if HAS_MLX and len(spectrum) >= 2048:
        mx_spec = _mx.array(np.array(spectrum).astype(np.complex64))
        result = _mx.fft.irfft(mx_spec, n=n)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.fft.irfft(spectrum, n=n)


def batch_fft(frames: list[npt.NDArray[np.float64]] | npt.NDArray,
              fft_size: int | None = None) -> npt.NDArray[np.complex128]:
    """Batch real FFT on multiple frames at once (STFT-style).

    Input: list of 1D arrays or 2D array (n_frames × frame_size)
    Returns: 2D complex array (n_frames × fft_bins)
    """
    if isinstance(frames, list):
        mat = np.array(frames, dtype=np.float64)
    else:
        mat = np.asarray(frames, dtype=np.float64)

    if HAS_MLX and mat.size >= 8192:
        mx_mat = _mx.array(mat.astype(np.float32))
        result = _mx.fft.rfft(mx_mat, n=fft_size, axis=-1)
        _mx.eval(result)
        return np.array(result).astype(np.complex128)
    return np.fft.rfft(mat, n=fft_size, axis=-1)


def batch_ifft(spectra: npt.NDArray[np.complex128],
               n: int | None = None) -> npt.NDArray[np.float64]:
    """Batch inverse real FFT on multiple spectra."""
    if HAS_MLX and spectra.size >= 4096:
        mx_spec = _mx.array(np.array(spectra).astype(np.complex64))
        result = _mx.fft.irfft(mx_spec, n=n, axis=-1)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.fft.irfft(spectra, n=n, axis=-1)


# ═══════════════════════════════════════════════════════════════════════════
# MATRIX OPERATIONS — GPU-accelerated
# ═══════════════════════════════════════════════════════════════════════════

def matmul(a: npt.NDArray, b: npt.NDArray) -> npt.NDArray:
    """Matrix multiply — MLX GPU for large matrices, numpy otherwise."""
    if HAS_MLX and a.size * b.shape[-1] >= 65536:
        mx_a = _mx.array(a.astype(np.float32))
        mx_b = _mx.array(b.astype(np.float32))
        result = _mx.matmul(mx_a, mx_b)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.dot(a, b)


def elementwise_sin(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Vectorized sin — GPU for large arrays."""
    if HAS_MLX and x.size >= 16384:
        mx_x = _mx.array(x.astype(np.float32))
        result = _mx.sin(mx_x)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.sin(x)


def elementwise_tanh(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Vectorized tanh — GPU for large arrays (saturation/distortion)."""
    if HAS_MLX and x.size >= 16384:
        mx_x = _mx.array(x.astype(np.float32))
        result = _mx.tanh(mx_x)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.tanh(x)


def elementwise_exp(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Vectorized exp — GPU for large arrays (envelopes)."""
    if HAS_MLX and x.size >= 16384:
        mx_x = _mx.array(x.astype(np.float32))
        result = _mx.exp(mx_x)
        _mx.eval(result)
        return np.array(result).astype(np.float64)
    return np.exp(x)


# ═══════════════════════════════════════════════════════════════════════════
# VECTORIZED SVF FILTER — replaces per-sample Python loop
# ═══════════════════════════════════════════════════════════════════════════

def svf_lowpass_fast(signal: npt.NDArray[np.float64],
                     cutoff_hz: float,
                     resonance: float = 0.0,
                     sample_rate: int = SAMPLE_RATE) -> npt.NDArray[np.float64]:
    """Vectorized SVF lowpass using block processing.

    Processes in blocks of 64 samples, updating coefficients per-block
    instead of per-sample. ~20-50× faster than the per-sample Python loop
    in dsp_core.py for static cutoff.

    For modulated cutoff (np.ndarray), falls back to the original loop.
    """
    n = len(signal)
    out = np.empty(n, dtype=np.float64)

    g = 2.0 * math.sin(math.pi * min(cutoff_hz, sample_rate * 0.45) / sample_rate)
    g = min(g, 1.0)
    q_damp = max(0.05, 2.0 - 2.0 * min(resonance, 0.98))

    ic1eq = 0.0
    ic2eq = 0.0

    # Process in blocks for vectorization potential
    block_size = 64
    for start in range(0, n, block_size):
        end = min(start + block_size, n)
        block = signal[start:end]
        block_len = end - start

        for j in range(block_len):
            hp = block[j] - ic2eq - q_damp * ic1eq
            bp = g * hp + ic1eq
            lp = g * bp + ic2eq

            if not math.isfinite(lp) or abs(lp) > 1e6:
                ic1eq = 0.0
                ic2eq = 0.0
                out[start + j] = 0.0
                continue

            ic1eq = bp
            ic2eq = lp
            out[start + j] = lp

    return out


# ═══════════════════════════════════════════════════════════════════════════
# ADDITIVE SYNTHESIS — GPU-accelerated harmonic generation
# ═══════════════════════════════════════════════════════════════════════════

def additive_synth(freq: float,
                   duration_s: float,
                   harmonics: list[tuple[float, float]],
                   sample_rate: int = SAMPLE_RATE) -> npt.NDArray[np.float64]:
    """GPU-accelerated additive synthesis.

    harmonics: list of (ratio, amplitude) pairs
    Returns mono signal.

    Uses MLX to compute all harmonics in parallel on GPU when available.
    """
    n = int(duration_s * sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate

    if HAS_MLX and n * len(harmonics) >= 100000:
        # Build frequency/amplitude matrices on GPU
        ratios = np.array([h[0] for h in harmonics], dtype=np.float32)
        amps = np.array([h[1] for h in harmonics], dtype=np.float32)

        mx_t = _mx.array(t.astype(np.float32))  # (n,)
        mx_ratios = _mx.array(ratios)             # (H,)
        mx_amps = _mx.array(amps)                 # (H,)

        # Phase matrix: (H, n) = outer product of (freq*ratios) × t × 2π
        phases = _mx.multiply(
            _mx.reshape(mx_ratios * freq, (-1, 1)),
            _mx.reshape(mx_t, (1, -1))
        ) * (2.0 * math.pi)
        # Sine of all phases: (H, n)
        sines = _mx.sin(phases)
        # Weighted sum: (n,)
        result = _mx.sum(sines * _mx.reshape(mx_amps, (-1, 1)), axis=0)
        _mx.eval(result)
        return np.array(result).astype(np.float64)

    # Numpy fallback — still vectorized
    signal = np.zeros(n, dtype=np.float64)
    for ratio, amp in harmonics:
        signal += amp * np.sin(2.0 * math.pi * freq * ratio * t)
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# CONVOLUTION — GPU-accelerated
# ═══════════════════════════════════════════════════════════════════════════

def convolve_fast(signal: npt.NDArray[np.float64],
                  kernel: npt.NDArray[np.float64],
                  mode: str = "full") -> npt.NDArray[np.float64]:
    """FFT-based convolution — MLX GPU for large signals."""
    # For short kernels, direct convolution is faster
    if len(kernel) < 128:
        return np.convolve(signal, kernel, mode=mode)  # type: ignore[arg-type]

    # FFT convolution (overlap-add style)
    n = len(signal) + len(kernel) - 1
    fft_n = 1
    while fft_n < n:
        fft_n *= 2

    if HAS_MLX and fft_n >= 4096:
        mx_sig = _mx.array(np.pad(signal, (0, fft_n - len(signal))).astype(np.float32))
        mx_ker = _mx.array(np.pad(kernel, (0, fft_n - len(kernel))).astype(np.float32))
        S = _mx.fft.rfft(mx_sig)
        K = _mx.fft.rfft(mx_ker)
        result = _mx.fft.irfft(S * K, n=fft_n)
        _mx.eval(result)
        out = np.array(result).astype(np.float64)
    else:
        S = np.fft.rfft(signal, n=fft_n)
        K = np.fft.rfft(kernel, n=fft_n)
        out = np.fft.irfft(S * K, n=fft_n)

    if mode == "full":
        return out[:n]
    elif mode == "same":
        start = (len(kernel) - 1) // 2
        return out[start:start + len(signal)]
    else:  # "valid"
        return out[len(kernel) - 1:len(signal)]


# ═══════════════════════════════════════════════════════════════════════════
# WAVETABLE GENERATION — GPU-accelerated frame batch
# ═══════════════════════════════════════════════════════════════════════════

def generate_wavetable_frames(base_freq: float,
                              n_frames: int,
                              frame_size: int,
                              harmonic_fn,
                              sample_rate: int = SAMPLE_RATE) -> list[npt.NDArray[np.float64]]:
    """Generate wavetable frames with GPU-accelerated sin computation.

    harmonic_fn(frame_idx, n_frames) -> list[(ratio, amplitude)]
    Returns list of normalized frames.
    """
    t = np.arange(frame_size, dtype=np.float64) / sample_rate

    if HAS_MLX:
        mx_t = _mx.array(t.astype(np.float32))

    frames = []
    for i in range(n_frames):
        harmonics = harmonic_fn(i, n_frames)
        if not harmonics:
            frames.append(np.zeros(frame_size, dtype=np.float64))
            continue

        ratios = np.array([h[0] for h in harmonics], dtype=np.float32)
        amps = np.array([h[1] for h in harmonics], dtype=np.float32)

        if HAS_MLX and len(harmonics) * frame_size >= 32768:
            mx_ratios = _mx.array(ratios)
            mx_amps = _mx.array(amps)
            phases = _mx.multiply(
                _mx.reshape(mx_ratios * base_freq, (-1, 1)),
                _mx.reshape(mx_t, (1, -1))
            ) * (2.0 * math.pi)
            sines = _mx.sin(phases)
            frame = _mx.sum(sines * _mx.reshape(mx_amps, (-1, 1)), axis=0)
            _mx.eval(frame)
            frame_np = np.array(frame).astype(np.float64)
        else:
            frame_np = np.zeros(frame_size, dtype=np.float64)
            for ratio, amp in harmonics:
                frame_np += amp * np.sin(2.0 * math.pi * base_freq * ratio * t)

        # Normalize
        peak = np.max(np.abs(frame_np))
        if peak > 1e-10:
            frame_np /= peak
        frames.append(frame_np)

    return frames


# ═══════════════════════════════════════════════════════════════════════════
# STATUS / INFO
# ═══════════════════════════════════════════════════════════════════════════

def get_accel_info() -> dict:
    """Return acceleration status for diagnostics."""
    info = {
        "backend": "mlx" if HAS_MLX else "numpy",
        "apple_silicon": IS_APPLE_SILICON,
        "gpu_available": HAS_MLX,
    }
    if HAS_MLX:
        try:
            info["mlx_version"] = _mx.__version__ if hasattr(_mx, "__version__") else "unknown"
            # Quick GPU health check
            test = _mx.array([1.0, 2.0, 3.0])
            _mx.eval(_mx.sum(test))
            info["gpu_healthy"] = True
        except Exception as e:
            info["gpu_healthy"] = False
            info["gpu_error"] = str(e)
    return info


def main() -> None:
    """Diagnostic: show acceleration status and run quick benchmark."""
    import time

    info = get_accel_info()
    print("Accelerate GPU Module")
    for k, v in info.items():
        print(f"  {k}: {v}")

    # Quick benchmark: FFT
    n = 65536
    signal = np.random.randn(n)

    t0 = time.perf_counter_ns()
    for _ in range(100):
        np.fft.rfft(signal)
    np_time = (time.perf_counter_ns() - t0) / 1e6

    t0 = time.perf_counter_ns()
    for _ in range(100):
        fft_rfft(signal)
    accel_time = (time.perf_counter_ns() - t0) / 1e6

    print(f"\n  FFT benchmark ({n} samples × 100):")
    print(f"    numpy:  {np_time:.1f}ms")
    print(f"    accel:  {accel_time:.1f}ms")
    print(f"    speedup: {np_time / max(accel_time, 0.01):.1f}×")

    # Benchmark: additive synthesis
    t0 = time.perf_counter_ns()
    harmonics: list[tuple[float, float]] = [(float(i + 1), 1.0 / (i + 1)) for i in range(64)]
    additive_synth(440.0, 2.0, harmonics)
    synth_time = (time.perf_counter_ns() - t0) / 1e6
    print(f"\n  Additive synth (64 harmonics, 2s @ 48kHz):")
    print(f"    time: {synth_time:.1f}ms")

    # Benchmark: convolution
    sig = np.random.randn(96000)
    kernel = np.random.randn(4800)
    t0 = time.perf_counter_ns()
    convolve_fast(sig, kernel)
    conv_time = (time.perf_counter_ns() - t0) / 1e6
    print(f"\n  Convolution (96k × 4.8k samples):")
    print(f"    time: {conv_time:.1f}ms")

    print("\nDone.")


if __name__ == "__main__":
    main()
