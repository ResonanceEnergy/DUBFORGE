"""
DUBFORGE Engine — DSP Core Module

Professional-grade DSP primitives shared across all synthesis engines:
  - State Variable Filter (SVF): 12 dB/oct LP/HP/BP/Notch with resonance
  - 2× Oversampling: anti-alias wrapper for distortion operations
  - Bandlimited oscillators: saw, square, pulse (PolyBLEP)
  - Waveshaping distortions: tube, tape, foldback, bitcrush
  - Schroeder reverb: multi-tap diffuse reverb
  - Stereo chorus: multi-voice detuned modulation

These replace the single-pole 6 dB/oct filters and aliased oscillators
that were producing thin, lifeless "basic sine wave" output.
"""

from __future__ import annotations

import math

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_RATE = 48000
from engine.config_loader import PHI
TWO_PI = 2.0 * math.pi


# ═══════════════════════════════════════════════════════════════════════════
# STATE VARIABLE FILTER (SVF) — 12 dB/oct, resonance 0–1
# ═══════════════════════════════════════════════════════════════════════════

def svf_lowpass(signal: np.ndarray, cutoff_hz: float | np.ndarray,
                resonance: float = 0.0,
                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """2-pole State Variable Filter — lowpass mode (12 dB/oct).
    
    cutoff_hz can be a float (static) or np.ndarray (per-sample modulation).
    resonance: 0.0 = no resonance, 1.0 = self-oscillation.
    """
    return _svf_process(signal, cutoff_hz, resonance, sample_rate, mode='lp')


def svf_highpass(signal: np.ndarray, cutoff_hz: float | np.ndarray,
                 resonance: float = 0.0,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """2-pole SVF — highpass mode (12 dB/oct)."""
    return _svf_process(signal, cutoff_hz, resonance, sample_rate, mode='hp')


def svf_bandpass(signal: np.ndarray, cutoff_hz: float | np.ndarray,
                 resonance: float = 0.0,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """2-pole SVF — bandpass mode (6 dB/oct slopes)."""
    return _svf_process(signal, cutoff_hz, resonance, sample_rate, mode='bp')


def svf_notch(signal: np.ndarray, cutoff_hz: float | np.ndarray,
              resonance: float = 0.0,
              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """2-pole SVF — notch mode."""
    return _svf_process(signal, cutoff_hz, resonance, sample_rate, mode='notch')


def _svf_process(signal: np.ndarray, cutoff_hz: float | np.ndarray,
                 resonance: float, sample_rate: int,
                 mode: str = 'lp') -> np.ndarray:
    """Internal SVF processor using Chamberlin topology.
    
    G = 2*sin(pi*fc/fs)  (valid up to ~fs/6, use clamping)
    Q_damp = 2 - 2*resonance (resonance 0=no reso, 1=self-osc)
    """
    n = len(signal)
    out = np.zeros(n)
    
    # State variables
    ic1eq = 0.0  # integrator state 1 (bandpass)
    ic2eq = 0.0  # integrator state 2 (lowpass)
    
    # Precompute cutoff array if static
    static_cutoff = isinstance(cutoff_hz, (int, float))
    if static_cutoff:
        g = 2.0 * math.sin(math.pi * min(cutoff_hz, sample_rate * 0.45) / sample_rate)
        g = min(g, 1.0)  # stability clamp
        q_damp = max(0.05, 2.0 - 2.0 * min(resonance, 0.98))
    
    for i in range(n):
        if not static_cutoff:
            fc = min(float(cutoff_hz[i]), sample_rate * 0.45)
            g = 2.0 * math.sin(math.pi * fc / sample_rate)
            g = min(g, 1.0)  # stability clamp
            q_damp = max(0.05, 2.0 - 2.0 * min(resonance, 0.98))
        
        # Chamberlin SVF
        hp = signal[i] - ic2eq - q_damp * ic1eq
        bp = g * hp + ic1eq
        lp = g * bp + ic2eq
        notch = hp + lp
        
        # Safety: reset on NaN/inf
        if not math.isfinite(lp) or not math.isfinite(bp):
            ic1eq = 0.0
            ic2eq = 0.0
            out[i] = 0.0
            continue
        
        ic1eq = bp
        ic2eq = lp
        
        if mode == 'lp':
            out[i] = lp
        elif mode == 'hp':
            out[i] = hp
        elif mode == 'bp':
            out[i] = bp
        else:  # notch
            out[i] = notch
    
    return out


def svf_lowpass_24(signal: np.ndarray, cutoff_hz: float | np.ndarray,
                   resonance: float = 0.0,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """4-pole (24 dB/oct) lowpass — cascaded SVF pair.
    
    For aggressive dubstep filtering (ladder-style rolloff).
    """
    stage1 = svf_lowpass(signal, cutoff_hz, resonance * 0.7, sample_rate)
    stage2 = svf_lowpass(stage1, cutoff_hz, resonance * 0.5, sample_rate)
    return stage2


# ═══════════════════════════════════════════════════════════════════════════
# MULTIBAND SPLIT (proper SVF-based crossover)
# ═══════════════════════════════════════════════════════════════════════════

def multiband_split(signal: np.ndarray, 
                    low_freq: float = 200.0, 
                    high_freq: float = 4000.0,
                    sample_rate: int = SAMPLE_RATE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split signal into low/mid/high bands using SVF crossovers."""
    low = svf_lowpass(signal, low_freq, 0.0, sample_rate)
    high = svf_highpass(signal, high_freq, 0.0, sample_rate)
    mid = signal - low - high
    return low, mid, high


# ═══════════════════════════════════════════════════════════════════════════
# 2× OVERSAMPLING (anti-alias for distortion)
# ═══════════════════════════════════════════════════════════════════════════

def oversample_2x(signal: np.ndarray) -> np.ndarray:
    """Upsample 2× with linear interpolation."""
    n = len(signal)
    up = np.zeros(n * 2)
    up[0::2] = signal
    up[1::2] = np.concatenate([
        (signal[:-1] + signal[1:]) / 2.0,
        [signal[-1]]
    ])
    return up


def downsample_2x(signal: np.ndarray) -> np.ndarray:
    """Downsample 2× with simple averaging anti-alias filter."""
    n = len(signal) // 2
    # Moving average of adjacent samples before decimation
    filtered = (signal[0::2][:n] + signal[1::2][:n]) / 2.0
    return filtered


def oversampled_distort(signal: np.ndarray, 
                        distort_fn,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply distortion with 2× oversampling to prevent aliasing.
    
    distort_fn: callable that takes np.ndarray and returns np.ndarray
    """
    up = oversample_2x(signal)
    # Anti-alias before distortion
    up = svf_lowpass(up, sample_rate * 0.9, 0.0, sample_rate * 2)
    # Apply distortion at 2× rate
    distorted = distort_fn(up)
    # Anti-alias filter before decimation
    distorted = svf_lowpass(distorted, sample_rate * 0.45, 0.0, sample_rate * 2)
    return downsample_2x(distorted)


# ═══════════════════════════════════════════════════════════════════════════
# BANDLIMITED OSCILLATORS (PolyBLEP anti-aliasing)
# ═══════════════════════════════════════════════════════════════════════════

def _polyblep(t: float, dt: float) -> float:
    """PolyBLEP residual for anti-aliased discontinuities.
    
    t: phase position relative to discontinuity (0 or 1)
    dt: phase increment per sample (freq/sr)
    """
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


def osc_saw(freq: float, duration_s: float,
            sample_rate: int = SAMPLE_RATE,
            phase_offset: float = 0.0) -> np.ndarray:
    """Bandlimited sawtooth oscillator using PolyBLEP.
    
    Much richer than naive harmonic summation — true saw spectrum
    with anti-aliased transitions.
    """
    n = int(duration_s * sample_rate)
    out = np.zeros(n)
    dt = freq / sample_rate
    phase = phase_offset
    
    for i in range(n):
        # Naive saw: 2*phase - 1
        saw = 2.0 * phase - 1.0
        # Apply PolyBLEP at the discontinuity (phase wraps at 1.0)
        saw -= _polyblep(phase, dt)
        out[i] = saw
        
        phase += dt
        if phase >= 1.0:
            phase -= 1.0
    
    return out


def osc_square(freq: float, duration_s: float,
               sample_rate: int = SAMPLE_RATE,
               pulse_width: float = 0.5,
               phase_offset: float = 0.0,
               duty: float | None = None) -> np.ndarray:
    """Bandlimited square/pulse oscillator using PolyBLEP.
    
    pulse_width / duty: 0.5 = square, other values = PWM.
    """
    if duty is not None:
        pulse_width = duty
    n = int(duration_s * sample_rate)
    out = np.zeros(n)
    dt = freq / sample_rate
    phase = phase_offset
    
    for i in range(n):
        # Naive square
        sq = 1.0 if phase < pulse_width else -1.0
        # PolyBLEP at rising edge (phase=0)
        sq += _polyblep(phase, dt)
        # PolyBLEP at falling edge (phase=pulse_width)
        pw_phase = phase - pulse_width
        if pw_phase < 0:
            pw_phase += 1.0
        sq -= _polyblep(pw_phase, dt)
        out[i] = sq
        
        phase += dt
        if phase >= 1.0:
            phase -= 1.0
    
    return out


def osc_saw_np(freq: float | np.ndarray, duration_or_samples,
               sample_rate: int = SAMPLE_RATE,
               phase_offset: float = 0.0) -> np.ndarray:
    """Vectorized bandlimited saw via additive synthesis (numpy).
    
    Uses enough harmonics to fill the spectrum without aliasing.
    Faster than sample-by-sample PolyBLEP for long signals.
    
    duration_or_samples: if float < 100, treated as duration in seconds;
                         if int or float >= 100, treated as sample count.
    """
    if isinstance(duration_or_samples, float) and duration_or_samples < 100:
        n_samples = int(duration_or_samples * sample_rate)
    else:
        n_samples = int(duration_or_samples)
    if isinstance(freq, (int, float)):
        freq_val = float(freq)
        n_harmonics = max(1, min(80, int(sample_rate / 2 / max(freq_val, 20))))
        t = np.arange(n_samples) / sample_rate
        signal = np.zeros(n_samples)
        for k in range(1, n_harmonics + 1):
            phase = TWO_PI * freq_val * k * t + phase_offset * k
            signal += ((-1.0) ** (k + 1)) * np.sin(phase) / k
        return signal * (2.0 / math.pi)
    else:
        # Frequency modulation — phase accumulation
        dt = 1.0 / sample_rate
        phase = np.zeros(n_samples)
        phase[0] = phase_offset
        for i in range(1, n_samples):
            phase[i] = phase[i-1] + TWO_PI * float(freq[i]) * dt
        # Use 20 harmonics for modulated case
        signal = np.zeros(n_samples)
        for k in range(1, 21):
            signal += ((-1.0) ** (k + 1)) * np.sin(phase * k) / k
        return signal * (2.0 / math.pi)


# ═══════════════════════════════════════════════════════════════════════════
# WAVESHAPING DISTORTIONS
# ═══════════════════════════════════════════════════════════════════════════

def distort_tube(signal: np.ndarray, drive: float = 2.0) -> np.ndarray:
    """Asymmetric tube saturation — adds even + odd harmonics.
    
    Unlike symmetric tanh, this produces a richer, more musical
    distortion with both even and odd harmonic content.
    """
    driven = np.clip(signal * drive, -20.0, 20.0)
    # Asymmetric waveshaper: different curve for positive vs negative
    pos = np.where(driven > 0, 1.0 - np.exp(-driven), 0.0)
    neg = np.where(driven <= 0, -(1.0 - np.exp(driven)), 0.0)
    return pos + neg


def distort_tape(signal: np.ndarray, drive: float = 1.5) -> np.ndarray:
    """Tape saturation — soft compression with gentle harmonics.
    
    Smoother than tanh, preserves low-frequency energy better.
    """
    driven = signal * drive
    return np.sign(driven) * np.log1p(np.abs(driven)) / np.log1p(drive)


def distort_foldback(signal: np.ndarray, threshold: float = 0.6) -> np.ndarray:
    """Wavefolder distortion — folds signal at threshold boundaries.
    
    Creates complex inharmonic content, essential for dubstep growls.
    Vectorized implementation.
    """
    out = signal.copy()
    # Iterative folding (max 8 iterations stays in range)
    for _ in range(8):
        above = out > threshold
        below = out < -threshold
        if not (above.any() or below.any()):
            break
        out = np.where(above, 2 * threshold - out, out)
        out = np.where(below, -2 * threshold - out, out)
    return out


def distort_bitcrush(signal: np.ndarray, bits: int = 8) -> np.ndarray:
    """Bit reduction — lo-fi digital grit. Vectorized."""
    levels = 2 ** bits
    return np.round(signal * levels) / levels


def distort_clipper(signal: np.ndarray, threshold: float = 0.8) -> np.ndarray:
    """Hard clipper with soft-knee — gritty but controlled distortion."""
    knee = threshold * 0.1
    soft_region = (np.abs(signal) > (threshold - knee)) & (np.abs(signal) < threshold)
    clipped = np.clip(signal, -threshold, threshold)
    # Soft knee blending
    if knee > 0:
        t = (np.abs(signal) - (threshold - knee)) / (2 * knee)
        t = np.clip(t, 0, 1)
        blend = t * t * (3 - 2 * t)  # smoothstep
        clipped = np.where(soft_region, 
                          signal * (1 - blend) + clipped * blend, 
                          clipped)
    return clipped


# ═══════════════════════════════════════════════════════════════════════════
# OVERSAMPLED DISTORTION PRESETS
# ═══════════════════════════════════════════════════════════════════════════

def saturate_warm(signal: np.ndarray, drive: float = 2.0,
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Warm analog saturation with 2× oversampling."""
    return oversampled_distort(signal, lambda s: distort_tube(s, drive), sample_rate)


def saturate_aggressive(signal: np.ndarray, drive: float = 3.0,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Aggressive distortion (foldback + tube) with 2× oversampling."""
    def _aggressive(s):
        folded = distort_foldback(s, 0.7)
        return distort_tube(folded, drive)
    return oversampled_distort(signal, _aggressive, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# SCHROEDER REVERB (diffuse algorithmic reverb)
# ═══════════════════════════════════════════════════════════════════════════

def reverb_schroeder(signal: np.ndarray, sample_rate: int = SAMPLE_RATE,
                     decay: float = 0.5,
                     mix: float = 0.3) -> np.ndarray:
    """4-comb + 2-allpass Schroeder reverb.
    
    decay: 0.0 = dry, 1.0 = very long tail
    mix: wet/dry balance (0 = dry, 1 = full wet)
    """
    n = len(signal)
    
    # Comb filter delays (prime-ish sample counts for density)
    comb_delays = [int(d * sample_rate / 1000) for d in [29.7, 37.1, 41.1, 43.7]]
    comb_gains = [decay ** (d / max(comb_delays)) for d in comb_delays]
    
    # Allpass delays
    ap_delays = [int(d * sample_rate / 1000) for d in [5.0, 1.7]]
    ap_gain = 0.7
    
    # Process combs in parallel
    wet = np.zeros(n)
    for delay, gain in zip(comb_delays, comb_gains):
        buf = np.zeros(n + delay)
        for i in range(n):
            buf[i + delay] = signal[i] + gain * buf[i]
        wet += buf[delay:delay + n]
    wet /= len(comb_delays)
    
    # Process allpasses in series
    for delay in ap_delays:
        buf_in = wet.copy()
        buf_out = np.zeros(n)
        buf = np.zeros(delay)
        buf_idx = 0
        for i in range(n):
            delayed = buf[buf_idx]
            buf[buf_idx] = buf_in[i] + ap_gain * delayed
            buf_out[i] = delayed - ap_gain * buf[buf_idx]
            buf_idx = (buf_idx + 1) % delay
        wet = buf_out
    
    return signal * (1.0 - mix) + wet * mix


# ═══════════════════════════════════════════════════════════════════════════
# STEREO CHORUS
# ═══════════════════════════════════════════════════════════════════════════

def chorus(signal: np.ndarray, sample_rate: int = SAMPLE_RATE,
           depth: float = 0.003, rate: float = 0.5,
           voices: int = 3, mix: float = 0.5) -> np.ndarray:
    """Multi-voice chorus for thickening.
    
    depth: in seconds (e.g. 0.003 = 3ms)
    rate: LFO rate in Hz
    """
    n = len(signal)
    depth_samples = depth * sample_rate
    # Pre-delay buffer
    max_delay = int(depth_samples * 2) + 2
    padded = np.concatenate([np.zeros(max_delay), signal])
    
    wet = np.zeros(n)
    for v in range(voices):
        # Each voice has different LFO phase
        lfo_phase = v * TWO_PI / voices
        t = np.arange(n) / sample_rate
        delay = max_delay + depth_samples * np.sin(TWO_PI * rate * t + lfo_phase)
        
        # Linear interpolation from delay line
        for i in range(n):
            d = delay[i]
            idx = max_delay + i - d
            idx_int = int(idx)
            frac = idx - idx_int
            if 0 <= idx_int < len(padded) - 1:
                wet[i] += padded[idx_int] * (1 - frac) + padded[idx_int + 1] * frac
    
    wet /= voices
    return signal * (1.0 - mix) + wet * mix


# ═══════════════════════════════════════════════════════════════════════════
# MULTIBAND COMPRESSION
# ═══════════════════════════════════════════════════════════════════════════

def multiband_compress(signal: np.ndarray,
                       sample_rate: int = SAMPLE_RATE,
                       low_xover: float = 200.0,
                       high_xover: float = 4000.0,
                       threshold_db: float = -12.0,
                       ratio: float = 4.0,
                       attack_ms: float = 5.0,
                       release_ms: float = 50.0) -> np.ndarray:
    """3-band multiband compressor.
    
    Essential for dubstep: independent control of sub/mid/high dynamics.
    """
    low, mid, high = multiband_split(signal, low_xover, high_xover, sample_rate)
    
    # Sub gets TIGHTER compression (lower threshold), highs gentler
    low_c = _compress_band(low, threshold_db - 4, ratio * 1.5, attack_ms, release_ms, sample_rate)
    mid_c = _compress_band(mid, threshold_db, ratio, attack_ms, release_ms, sample_rate)
    high_c = _compress_band(high, threshold_db + 2, ratio * 0.8, attack_ms, release_ms, sample_rate)
    
    return low_c + mid_c + high_c


def _compress_band(signal: np.ndarray, threshold_db: float, ratio: float,
                   attack_ms: float, release_ms: float,
                   sample_rate: int) -> np.ndarray:
    """Single-band RMS compressor."""
    threshold_lin = 10.0 ** (threshold_db / 20.0)
    attack_coeff = math.exp(-1.0 / (attack_ms * sample_rate / 1000.0))
    release_coeff = math.exp(-1.0 / (release_ms * sample_rate / 1000.0))
    
    n = len(signal)
    envelope = np.zeros(n)
    env = 0.0
    
    for i in range(n):
        level = abs(signal[i])
        if level > env:
            env = attack_coeff * env + (1 - attack_coeff) * level
        else:
            env = release_coeff * env + (1 - release_coeff) * level
        envelope[i] = max(env, 1e-10)
    
    gain = np.ones(n)
    mask = envelope > threshold_lin
    gain[mask] = (threshold_lin / envelope[mask]) ** (1.0 - 1.0 / ratio)
    
    return signal * gain


# ═══════════════════════════════════════════════════════════════════════════
# NOISE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def white_noise(n_samples: int, amplitude: float = 1.0) -> np.ndarray:
    """White noise generator."""
    return np.random.uniform(-amplitude, amplitude, n_samples)


def pink_noise(n_samples: int, amplitude: float = 1.0) -> np.ndarray:
    """Pink noise (1/f) via Voss-McCartney algorithm."""
    # Simple 1/f approximation: filter white noise
    white = white_noise(n_samples, amplitude)
    # Cascade of 6 first-order filters
    b = [0.02109238, 0.07113478, 0.06837280, 0.04174757, 0.00549791]
    pink = white.copy()
    state = [0.0] * 5
    for i in range(n_samples):
        for j in range(5):
            state[j] = state[j] * (1 - b[j]) + pink[i] * b[j]
        pink[i] = sum(state) + pink[i] * 0.5362
    # Normalize
    peak = np.max(np.abs(pink))
    if peak > 0:
        pink *= amplitude / peak
    return pink


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════

def normalize(signal: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """Normalize signal to given peak level."""
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        return signal * (peak / max_val)
    return signal


def dc_block(signal: np.ndarray, coeff: float = 0.995) -> np.ndarray:
    """DC offset removal filter."""
    out = np.zeros_like(signal)
    xm1 = 0.0
    ym1 = 0.0
    for i in range(len(signal)):
        out[i] = signal[i] - xm1 + coeff * ym1
        xm1 = signal[i]
        ym1 = out[i]
    return out


def crossfade(a: np.ndarray, b: np.ndarray, 
              position: float | np.ndarray) -> np.ndarray:
    """Equal-power crossfade between two signals.
    
    position: 0.0 = 100% a, 1.0 = 100% b
    """
    if isinstance(position, (int, float)):
        ga = math.cos(position * math.pi / 2)
        gb = math.sin(position * math.pi / 2)
    else:
        ga = np.cos(position * math.pi / 2)
        gb = np.sin(position * math.pi / 2)
    return a * ga + b * gb


def soft_clip(signal: np.ndarray, threshold: float = 0.9) -> np.ndarray:
    """Soft clipper — essential pre-limiter stage.
    
    Smoothly limits signal approaching threshold using cubic curve.
    """
    out = signal.copy()
    above = np.abs(signal) > threshold
    # Cubic soft-clip in the region above threshold
    if above.any():
        x = np.clip(signal[above] / threshold, -1.5, 1.5)
        out[above] = threshold * (1.5 * x - 0.5 * x ** 3) / 1.0
    return np.clip(out, -1.0, 1.0)
