"""
DUBFORGE Engine — Unified Acceleration Facade

Single import for all accelerated DSP operations.
Routes to MLX GPU, Apple vDSP, or numpy depending on availability.

Usage:
    from engine.accel import fft, ifft, convolve, rms, peak, write_wav
"""

from engine.accelerate_gpu import (
    fft_rfft as fft,
    fft_irfft as ifft,
    batch_fft,
    batch_ifft,
    convolve_fast as convolve,
    additive_synth,
    elementwise_sin,
    elementwise_tanh,
    elementwise_exp,
    matmul,
    HAS_MLX,
)
from engine.accelerate_vdsp import (
    vdsp_rms as rms,
    vdsp_peak as peak,
    vdsp_normalize as normalize,
    biquad_lowpass,
    biquad_highpass,
    biquad_bandpass,
    HAS_VDSP,
)
from engine.audio_mmap import (
    write_wav_fast as write_wav,
    mmap_read_wav as read_wav,
    get_audio_pool,
)

__all__ = [
    "fft", "ifft", "batch_fft", "batch_ifft",
    "convolve", "additive_synth",
    "elementwise_sin", "elementwise_tanh", "elementwise_exp",
    "matmul",
    "rms", "peak", "normalize",
    "biquad_lowpass", "biquad_highpass", "biquad_bandpass",
    "write_wav", "read_wav", "get_audio_pool",
    "HAS_MLX", "HAS_VDSP",
]
