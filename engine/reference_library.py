"""
DUBFORGE -- Reference Library Analyzer

Scan a folder of reference tracks (SoundCloud likes, professional releases),
run deep audio analysis on each, build per-track profiles, aggregate into
a "reference standard", and provide comparison scoring for DUBFORGE renders.

Usage (CLI):
    python -m engine.reference_library scan            # analyze all tracks
    python -m engine.reference_library scan --force     # re-analyze everything
    python -m engine.reference_library compare output/galatcia_rising.wav
    python -m engine.reference_library report           # print aggregate stats
    python -m engine.reference_library list             # list analyzed tracks

Usage (API):
    from engine.reference_library import ReferenceLibrary
    lib = ReferenceLibrary()
    lib.scan()
    score = lib.compare("output/my_track.wav")
"""

import json
import logging
import math
import os
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.fft import rfft, rfftfreq

from engine.reference_analyzer import (
    ReferenceAnalysis, analyze_reference, compare_to_benchmark,
    QualityScore,
)

_log = logging.getLogger("dubforge.reference_library")

SAMPLE_RATE = 48000

# ═══════════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_REFERENCE_DIR = Path("output/taste/downloads")
DEFAULT_LIBRARY_DIR = Path("output/reference_library")


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SpectralBalance:
    """6-band spectral energy distribution (0-1 each, sum ~1.0)."""
    sub: float = 0.0        # 20-60 Hz
    bass: float = 0.0       # 60-250 Hz
    low_mid: float = 0.0    # 250-500 Hz
    mid: float = 0.0        # 500-2000 Hz
    high_mid: float = 0.0   # 2000-6000 Hz
    high: float = 0.0       # 6000-20000 Hz


@dataclass
class SectionEnergy:
    """Energy profile for a track section."""
    name: str = ""
    start_pct: float = 0.0
    end_pct: float = 0.0
    rms_db: float = -96.0
    peak_db: float = -96.0
    spectral: SpectralBalance = field(default_factory=SpectralBalance)


@dataclass
class TrackAnalysis:
    """Complete analysis of a single reference track."""
    # Identity
    filename: str = ""
    path: str = ""

    # Basic
    duration_s: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    bit_depth: int = 0

    # Loudness
    peak_db: float = -96.0
    rms_db: float = -96.0
    lufs_estimate: float = -96.0
    crest_factor_db: float = 0.0
    dynamic_range_db: float = 0.0

    # Spectral (full track)
    spectral: SpectralBalance = field(default_factory=SpectralBalance)
    spectral_centroid_hz: float = 0.0
    spectral_rolloff_hz: float = 0.0

    # Spectral (drop section -- 30-50% of track)
    spectral_drop: SpectralBalance = field(default_factory=SpectralBalance)

    # Stereo
    stereo_width: float = 0.0          # 0=mono, 1=full stereo
    stereo_correlation: float = 1.0    # 1=mono, 0=uncorrelated, -1=out of phase

    # Energy curve (10 segments)
    energy_curve: list[float] = field(default_factory=list)

    # Section contrast
    intro_rms_db: float = -96.0
    drop_rms_db: float = -96.0
    breakdown_rms_db: float = -96.0
    intro_drop_contrast_db: float = 0.0

    # Rhythm
    estimated_bpm: float = 0.0
    sidechain_pump_count: int = 0

    # Perceived loudness (A-weighted)
    a_weighted_rms_db: float = -96.0

    # Deep DNA analysis (from reference_analyzer)
    dna: ReferenceAnalysis | None = None

    def to_dict(self) -> dict:
        d = _dataclass_to_dict(self)
        if self.dna is not None:
            d["dna"] = self.dna.to_dict()
        return d


@dataclass
class ReferenceStandard:
    """Aggregate statistics across all analyzed reference tracks."""
    track_count: int = 0

    # Loudness (median / p10 / p90)
    lufs_median: float = 0.0
    lufs_p10: float = 0.0
    lufs_p90: float = 0.0
    peak_db_median: float = 0.0
    rms_db_median: float = 0.0
    crest_factor_median: float = 0.0
    dynamic_range_median: float = 0.0

    # Spectral balance (median)
    spectral_sub_median: float = 0.0
    spectral_bass_median: float = 0.0
    spectral_low_mid_median: float = 0.0
    spectral_mid_median: float = 0.0
    spectral_high_mid_median: float = 0.0
    spectral_high_median: float = 0.0

    # Spectral drop section (median)
    spectral_drop_sub_median: float = 0.0
    spectral_drop_bass_median: float = 0.0
    spectral_drop_low_mid_median: float = 0.0
    spectral_drop_mid_median: float = 0.0
    spectral_drop_high_mid_median: float = 0.0
    spectral_drop_high_median: float = 0.0

    # Stereo (median)
    stereo_width_median: float = 0.0
    stereo_correlation_median: float = 0.0

    # Contrast
    intro_drop_contrast_median: float = 0.0

    # Duration
    duration_median: float = 0.0
    bpm_median: float = 0.0

    # ── Style DNA medians (session 168) ──
    style_aggression_median: float = 0.0
    style_darkness_median: float = 0.0
    style_energy_median: float = 0.0
    style_danceability_median: float = 0.0
    style_density_median: float = 0.0
    style_brightness_median: float = 0.0
    style_bass_dominance_median: float = 0.0

    # ── Sound Design DNA medians ──
    sd_attack_sharpness_median: float = 0.0
    sd_modulation_depth_median: float = 0.0
    sd_texture_density_median: float = 0.0
    sd_spectral_movement_median: float = 0.0
    sd_inharmonicity_median: float = 0.0
    sd_noise_content_median: float = 0.0

    # ── Mixing DNA medians ──
    mix_headroom_median: float = 0.0
    mix_freq_balance_median: float = 0.0
    mix_mud_ratio_median: float = 0.0
    mix_harshness_ratio_median: float = 0.0
    mix_air_ratio_median: float = 0.0
    mix_phase_low_median: float = 0.0
    mix_separation_median: float = 0.0

    # ── Mastering DNA medians ──
    master_true_peak_median: float = 0.0
    master_limiting_transparency_median: float = 0.0
    master_loudness_consistency_median: float = 0.0
    master_streaming_penalty_median: float = 0.0
    master_dynamic_complexity_median: float = 0.0

    def to_dict(self) -> dict:
        return _dataclass_to_dict(self)


@dataclass
class ComparisonResult:
    """Result of comparing a DUBFORGE render to the reference standard."""
    track_name: str = ""
    overall_score: float = 0.0      # 0-100

    # Per-metric scores (0-1 each)
    loudness_score: float = 0.0
    spectral_score: float = 0.0
    dynamics_score: float = 0.0
    stereo_score: float = 0.0
    contrast_score: float = 0.0

    # Issues and suggestions
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)

    # Raw values vs reference
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return _dataclass_to_dict(self)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _dataclass_to_dict(obj: Any) -> dict:
    """Recursively convert dataclass to dict with rounding."""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for k, v in obj.__dataclass_fields__.items():
            val = getattr(obj, k)
            result[k] = _dataclass_to_dict(val)
        return result
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def _db(val: float) -> float:
    return 20.0 * math.log10(max(abs(val), 1e-10))


def _a_weight(f: float) -> float:
    """A-weighting magnitude at frequency f (Hz)."""
    if f < 1.0:
        return 0.0
    f2 = f * f
    num = 12194.0**2 * f2**2
    den = ((f2 + 20.6**2)
           * math.sqrt((f2 + 107.7**2) * (f2 + 737.9**2))
           * (f2 + 12194.0**2))
    if den < 1e-30:
        return 0.0
    ra = num / den
    return 20.0 * math.log10(max(ra, 1e-10)) + 2.0


# ═══════════════════════════════════════════════════════════════════════════
# WAV LOADER (supports 16, 24, 32-bit)
# ═══════════════════════════════════════════════════════════════════════════

def load_wav_stereo(path: str) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Load WAV file, return (left, right, sample_rate) as float64 arrays.
    Handles 16-bit, 24-bit, and 32-bit WAV files.
    Mono files return identical L and R.
    """
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        n = wf.getnframes()
        raw = wf.readframes(n)

    if sw == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
        samples /= 32768.0
    elif sw == 3:
        # 24-bit: vectorized decode
        raw_bytes = np.frombuffer(raw, dtype=np.uint8)
        n_samples = len(raw_bytes) // 3
        raw_bytes = raw_bytes[:n_samples * 3].reshape(-1, 3)
        padded = np.zeros((n_samples, 4), dtype=np.uint8)
        padded[:, 0] = raw_bytes[:, 0]
        padded[:, 1] = raw_bytes[:, 1]
        padded[:, 2] = raw_bytes[:, 2]
        int_vals = padded.view(np.int32).flatten()
        int_vals = (int_vals << 8) >> 8
        samples = int_vals.astype(np.float64) / 8388607.0
    elif sw == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
        samples /= 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sw}")

    if ch >= 2:
        left = samples[0::ch]
        right = samples[1::ch]
    else:
        left = samples
        right = samples.copy()

    return left, right, sr


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def _spectral_balance(mono: np.ndarray, sr: int,
                      fft_size: int = 8192) -> SpectralBalance:
    """Compute 6-band spectral balance via FFT."""
    # Use center portion of signal, windowed
    n = len(mono)
    if n < fft_size:
        fft_size = n

    # Average multiple windows for stability
    hop = fft_size // 2
    num_windows = max(1, (n - fft_size) // hop)
    num_windows = min(num_windows, 32)  # cap at 32 windows

    window = np.hanning(fft_size)
    bands = {"sub": 0.0, "bass": 0.0, "low_mid": 0.0,
             "mid": 0.0, "high_mid": 0.0, "high": 0.0}

    freqs = rfftfreq(fft_size, 1.0 / sr)

    for i in range(num_windows):
        start = i * hop
        chunk = mono[start:start + fft_size]
        if len(chunk) < fft_size:
            break
        spectrum = np.abs(rfft(chunk * window))
        power = spectrum ** 2

        bands["sub"] += float(np.sum(power[(freqs >= 20) & (freqs < 60)]))
        bands["bass"] += float(np.sum(power[(freqs >= 60) & (freqs < 250)]))
        bands["low_mid"] += float(np.sum(power[(freqs >= 250) & (freqs < 500)]))
        bands["mid"] += float(np.sum(power[(freqs >= 500) & (freqs < 2000)]))
        bands["high_mid"] += float(np.sum(power[(freqs >= 2000) & (freqs < 6000)]))
        bands["high"] += float(np.sum(power[(freqs >= 6000) & (freqs <= 20000)]))

    total = sum(bands.values())
    if total > 0:
        for k in bands:
            bands[k] /= total

    return SpectralBalance(**bands)


def _spectral_centroid(mono: np.ndarray, sr: int,
                       fft_size: int = 8192) -> float:
    """Compute spectral centroid in Hz (sampled from track center)."""
    center = len(mono) // 2
    half = min(fft_size // 2, center)
    chunk = mono[center - half:center + half]
    n = len(chunk)
    if n < 64:
        return 0.0
    window = np.hanning(n)
    spectrum = np.abs(rfft(chunk * window))
    freqs = rfftfreq(n, 1.0 / sr)
    total = np.sum(spectrum)
    if total < 1e-10:
        return 0.0
    return float(np.sum(freqs * spectrum) / total)


def _spectral_rolloff(mono: np.ndarray, sr: int,
                      fft_size: int = 8192,
                      threshold: float = 0.95) -> float:
    """Frequency below which `threshold` fraction of energy lies."""
    center = len(mono) // 2
    half = min(fft_size // 2, center)
    chunk = mono[center - half:center + half]
    n = len(chunk)
    if n < 64:
        return 0.0
    window = np.hanning(n)
    spectrum = np.abs(rfft(chunk * window))
    power = spectrum ** 2
    cumulative = np.cumsum(power)
    total = cumulative[-1]
    if total < 1e-10:
        return 0.0
    freqs = rfftfreq(n, 1.0 / sr)
    idx = np.searchsorted(cumulative, threshold * total)
    return float(freqs[min(idx, len(freqs) - 1)])


def _stereo_analysis(left: np.ndarray,
                     right: np.ndarray) -> tuple[float, float]:
    """
    Compute stereo width and correlation.
    Width: ratio of side energy to total (0=mono, 1=full stereo)
    Correlation: Pearson correlation between L and R
    """
    n = min(len(left), len(right))
    L = left[:n]
    R = right[:n]

    mid = (L + R) * 0.5
    side = (L - R) * 0.5

    mid_energy = float(np.mean(mid ** 2))
    side_energy = float(np.mean(side ** 2))
    total_energy = mid_energy + side_energy

    width = side_energy / total_energy if total_energy > 1e-10 else 0.0

    # Pearson correlation
    l_mean = np.mean(L)
    r_mean = np.mean(R)
    l_std = np.std(L)
    r_std = np.std(R)
    if l_std < 1e-10 or r_std < 1e-10:
        correlation = 1.0
    else:
        correlation = float(
            np.mean((L - l_mean) * (R - r_mean)) / (l_std * r_std)
        )

    return width, correlation


def _energy_curve(mono: np.ndarray, n_segments: int = 10) -> list[float]:
    """Compute RMS in dB for n_segments equal slices."""
    chunk_size = len(mono) // n_segments
    if chunk_size < 1:
        return [_db(0.001)] * n_segments

    curve = []
    for i in range(n_segments):
        chunk = mono[i * chunk_size:(i + 1) * chunk_size]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        curve.append(_db(rms))
    return curve


def _dynamic_range(mono: np.ndarray, block_ms: int = 100,
                   sr: int = 48000) -> float:
    """Dynamic range = difference between loudest and quietest 100ms blocks."""
    block_size = int(sr * block_ms / 1000)
    n_blocks = len(mono) // block_size
    if n_blocks < 2:
        return 0.0

    rms_blocks = []
    for i in range(n_blocks):
        block = mono[i * block_size:(i + 1) * block_size]
        rms = float(np.sqrt(np.mean(block ** 2)))
        if rms > 1e-10:
            rms_blocks.append(_db(rms))

    if len(rms_blocks) < 2:
        return 0.0

    # Use 5th-95th percentile to exclude silence/glitches
    rms_blocks.sort()
    p5 = rms_blocks[max(0, len(rms_blocks) // 20)]
    p95 = rms_blocks[min(len(rms_blocks) - 1, len(rms_blocks) * 19 // 20)]
    return p95 - p5


def _estimate_bpm(mono: np.ndarray, sr: int,
                  max_seconds: float = 60.0) -> float:
    """
    Simple BPM estimation via onset detection autocorrelation.
    Returns estimated BPM (focused on 120-180 range for dubstep/bass music).
    Uses center 60s of track max to keep computation fast.
    """
    # Use center portion (up to max_seconds) for speed
    max_samples = int(sr * max_seconds)
    if len(mono) > max_samples:
        start = (len(mono) - max_samples) // 2
        mono = mono[start:start + max_samples]

    # Downsample for speed
    ds_factor = max(1, sr // 4000)
    ds = mono[::ds_factor]
    ds_sr = sr / ds_factor

    # Onset strength via spectral flux
    frame_size = int(ds_sr * 0.02)  # 20ms frames
    hop = frame_size // 2
    n_frames = (len(ds) - frame_size) // hop

    if n_frames < 10:
        return 0.0

    prev_spec = np.zeros(frame_size // 2 + 1)
    onsets = []
    for i in range(n_frames):
        frame = ds[i * hop:i * hop + frame_size]
        spec = np.abs(rfft(frame * np.hanning(len(frame))))
        flux = np.sum(np.maximum(0, spec - prev_spec))
        onsets.append(flux)
        prev_spec = spec

    onsets = np.array(onsets)
    onsets -= np.mean(onsets)

    # FFT-based autocorrelation (O(n log n) instead of O(n^2))
    n = len(onsets)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2
    onset_fft = rfft(onsets, fft_size)
    corr = np.fft.irfft(onset_fft * np.conj(onset_fft), fft_size)[:n]

    # Search 120-180 BPM range (dubstep/bass music)
    min_lag = int(60.0 / 180.0 * ds_sr / hop)
    max_lag = int(60.0 / 120.0 * ds_sr / hop)

    min_lag = max(1, min(min_lag, len(corr) - 1))
    max_lag = min(max_lag, len(corr) - 1)

    if min_lag >= max_lag:
        return 0.0

    search = corr[min_lag:max_lag + 1]
    best_lag = min_lag + int(np.argmax(search))

    if best_lag < 1:
        return 0.0

    bpm = 60.0 / (best_lag * hop / ds_sr)
    return round(bpm, 1)


def _sidechain_pump_count(mono: np.ndarray, sr: int) -> int:
    """
    Count sidechain pump events in the drop section (30-60% of track).
    A pump = >6 dB dip followed by recovery within 200ms.
    """
    drop_start = int(len(mono) * 0.30)
    drop_end = int(len(mono) * 0.60)
    drop = mono[drop_start:drop_end]

    # Envelope follower (RMS in 10ms blocks)
    block_size = int(sr * 0.010)
    n_blocks = len(drop) // block_size
    if n_blocks < 4:
        return 0

    envelope = []
    for i in range(n_blocks):
        block = drop[i * block_size:(i + 1) * block_size]
        rms = float(np.sqrt(np.mean(block ** 2)))
        envelope.append(rms)

    envelope = np.array(envelope)
    if np.max(envelope) < 1e-10:
        return 0

    # Normalize envelope
    envelope /= np.max(envelope)

    # Detect dips > 6 dB (factor of 0.5)
    pumps = 0
    i = 0
    while i < len(envelope) - 2:
        if envelope[i] > 0.3 and envelope[i + 1] < envelope[i] * 0.5:
            # Found a dip -- check recovery
            for j in range(i + 2, min(i + 20, len(envelope))):
                if envelope[j] > envelope[i] * 0.7:
                    pumps += 1
                    i = j
                    break
        i += 1

    return pumps


def _a_weighted_rms(mono: np.ndarray, sr: int,
                    fft_size: int = 8192) -> float:
    """Compute A-weighted RMS in dB."""
    n = min(len(mono), fft_size * 16)
    if n < fft_size:
        return _db(float(np.sqrt(np.mean(mono ** 2))))

    # Process in windows
    hop = fft_size // 2
    total_weighted_energy = 0.0
    count = 0
    window = np.hanning(fft_size)

    for start in range(0, n - fft_size, hop):
        chunk = mono[start:start + fft_size]
        spectrum = np.abs(rfft(chunk * window))
        freqs = rfftfreq(fft_size, 1.0 / sr)

        # Apply A-weighting
        for i, f in enumerate(freqs):
            if f > 0:
                a_db = _a_weight(f)
                a_lin = 10.0 ** (a_db / 20.0)
                total_weighted_energy += (spectrum[i] * a_lin) ** 2
                count += 1

    if count < 1:
        return -96.0
    avg_power = total_weighted_energy / count
    return _db(math.sqrt(avg_power))


# ═══════════════════════════════════════════════════════════════════════════
# FULL TRACK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_track(path: str,
                  max_duration_s: float = 600.0) -> TrackAnalysis:
    """Run complete analysis on a single WAV file.
    Files longer than max_duration_s are center-cropped before analysis.
    """
    _log.info("Analyzing: %s", os.path.basename(path))

    left, right, sr = load_wav_stereo(path)

    # Record true duration before any cropping
    true_duration = len(left) / sr

    # Cap at max_duration_s (center-crop long files like DJ mixes)
    max_samples = int(sr * max_duration_s)
    if len(left) > max_samples:
        start = (len(left) - max_samples) // 2
        left = left[start:start + max_samples]
        right = right[start:start + max_samples]

    mono = (left + right) * 0.5
    n = len(mono)

    result = TrackAnalysis()
    result.filename = os.path.basename(path)
    result.path = str(path)
    result.duration_s = true_duration
    result.sample_rate = sr
    result.channels = 2 if not np.array_equal(left, right) else 1

    # Bit depth from file
    with wave.open(path, "rb") as wf:
        result.bit_depth = wf.getsampwidth() * 8

    # Loudness
    all_samples = np.concatenate([left, right])
    result.peak_db = _db(float(np.max(np.abs(all_samples))))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    result.rms_db = _db(rms)
    result.lufs_estimate = result.rms_db - 0.7  # K-weight approximation
    result.crest_factor_db = result.peak_db - result.rms_db
    result.dynamic_range_db = _dynamic_range(mono, sr=sr)

    # Spectral (full track)
    result.spectral = _spectral_balance(mono, sr)
    result.spectral_centroid_hz = _spectral_centroid(mono, sr)
    result.spectral_rolloff_hz = _spectral_rolloff(mono, sr)

    # Spectral (drop section 30-50%)
    drop_start = int(n * 0.30)
    drop_end = int(n * 0.50)
    drop_mono = mono[drop_start:drop_end]
    if len(drop_mono) > 1024:
        result.spectral_drop = _spectral_balance(drop_mono, sr)

    # Stereo
    result.stereo_width, result.stereo_correlation = _stereo_analysis(
        left, right
    )

    # Energy curve
    result.energy_curve = _energy_curve(mono)

    # Section contrast (coarse: intro=0-10%, drop=30-50%, breakdown=55-65%)
    intro = mono[:int(n * 0.10)]
    drop = mono[int(n * 0.30):int(n * 0.50)]
    breakdown = mono[int(n * 0.55):int(n * 0.65)]

    result.intro_rms_db = _db(float(np.sqrt(np.mean(intro ** 2))))
    result.drop_rms_db = _db(float(np.sqrt(np.mean(drop ** 2))))
    result.breakdown_rms_db = _db(float(np.sqrt(np.mean(breakdown ** 2))))
    result.intro_drop_contrast_db = result.drop_rms_db - result.intro_rms_db

    # Rhythm
    result.estimated_bpm = _estimate_bpm(mono, sr)
    result.sidechain_pump_count = _sidechain_pump_count(mono, sr)

    # A-weighted loudness
    result.a_weighted_rms_db = _a_weighted_rms(mono, sr)

    # Deep DNA analysis
    try:
        result.dna = analyze_reference(path)
    except Exception:
        _log.debug("DNA analysis failed for %s", path, exc_info=True)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# REFERENCE LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

class ReferenceLibrary:
    """
    Manages the reference track library: scan, store, aggregate, compare.
    """

    def __init__(self,
                 reference_dir: str | Path = DEFAULT_REFERENCE_DIR,
                 library_dir: str | Path = DEFAULT_LIBRARY_DIR):
        self.reference_dir = Path(reference_dir)
        self.library_dir = Path(library_dir)
        self.profiles_dir = self.library_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._standard: ReferenceStandard | None = None

    # ── Scan ──────────────────────────────────────────────────────────

    def scan(self, force: bool = False) -> int:
        """
        Analyze all WAV files in reference_dir. Skip already-analyzed
        unless force=True. Returns count of newly analyzed tracks.
        """
        if not self.reference_dir.exists():
            _log.warning("Reference dir not found: %s", self.reference_dir)
            return 0

        wav_files = sorted(self.reference_dir.glob("*.wav"))
        if not wav_files:
            _log.warning("No WAV files in %s", self.reference_dir)
            return 0

        analyzed = 0
        total = len(wav_files)
        print(f"\n  Scanning {total} reference tracks in {self.reference_dir}")
        print(f"  Output: {self.library_dir}\n")

        for i, wav_path in enumerate(wav_files, 1):
            profile_path = self.profiles_dir / f"{wav_path.stem}.json"

            if profile_path.exists() and not force:
                print(f"  [{i}/{total}] SKIP {wav_path.name} (already analyzed)")
                continue

            try:
                print(f"  [{i}/{total}] Analyzing {wav_path.name}...", end="",
                      flush=True)
                analysis = analyze_track(str(wav_path))
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(analysis.to_dict(), f, indent=2)
                dna_tag = ""
                if analysis.dna is not None:
                    q = analysis.dna.quality.overall
                    dna_tag = f" | Q={q:.0f}/100"
                    if analysis.dna.harmonic.key:
                        dna_tag += f" | {analysis.dna.harmonic.key}"
                print(f"  {analysis.duration_s:.0f}s | "
                      f"{analysis.lufs_estimate:.1f} LUFS | "
                      f"BPM ~{analysis.estimated_bpm:.0f}{dna_tag}")
                analyzed += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                _log.exception("Failed to analyze %s", wav_path.name)

        # Rebuild aggregate
        self._build_standard()

        print(f"\n  Done: {analyzed} new, {total} total reference tracks")
        return analyzed

    # ── Load profiles ──────────────────────────────────────────────────

    def _load_all_profiles(self) -> list[dict]:
        """Load all profile JSON files."""
        profiles = []
        for p in sorted(self.profiles_dir.glob("*.json")):
            with open(p, "r", encoding="utf-8") as f:
                profiles.append(json.load(f))
        return profiles

    # ── Aggregate standard ────────────────────────────────────────────

    def _build_standard(self) -> None:
        """Build aggregate reference standard from all profiles."""
        profiles = self._load_all_profiles()
        if not profiles:
            return

        std = ReferenceStandard()
        std.track_count = len(profiles)

        def _pct(values: list[float], p: int) -> float:
            if not values:
                return 0.0
            s = sorted(values)
            idx = int(len(s) * p / 100)
            return s[min(idx, len(s) - 1)]

        def _median(values: list[float]) -> float:
            return _pct(values, 50)

        # Collect arrays
        lufs = [p.get("lufs_estimate", -20) for p in profiles]
        peaks = [p.get("peak_db", -1) for p in profiles]
        rms = [p.get("rms_db", -14) for p in profiles]
        crests = [p.get("crest_factor_db", 8) for p in profiles]
        drs = [p.get("dynamic_range_db", 6) for p in profiles]
        durations = [p.get("duration_s", 180) for p in profiles]
        bpms = [p.get("estimated_bpm", 0) for p in profiles
                if p.get("estimated_bpm", 0) > 0]
        widths = [p.get("stereo_width", 0.3) for p in profiles]
        corrs = [p.get("stereo_correlation", 0.8) for p in profiles]

        contrasts = [p.get("intro_drop_contrast_db", 0) for p in profiles]

        # Spectral full
        sp_sub = [p.get("spectral", {}).get("sub", 0) for p in profiles]
        sp_bass = [p.get("spectral", {}).get("bass", 0) for p in profiles]
        sp_lm = [p.get("spectral", {}).get("low_mid", 0) for p in profiles]
        sp_mid = [p.get("spectral", {}).get("mid", 0) for p in profiles]
        sp_hm = [p.get("spectral", {}).get("high_mid", 0) for p in profiles]
        sp_high = [p.get("spectral", {}).get("high", 0) for p in profiles]

        # Spectral drop
        spd_sub = [p.get("spectral_drop", {}).get("sub", 0)
                   for p in profiles]
        spd_bass = [p.get("spectral_drop", {}).get("bass", 0)
                    for p in profiles]
        spd_lm = [p.get("spectral_drop", {}).get("low_mid", 0)
                  for p in profiles]
        spd_mid = [p.get("spectral_drop", {}).get("mid", 0)
                   for p in profiles]
        spd_hm = [p.get("spectral_drop", {}).get("high_mid", 0)
                  for p in profiles]
        spd_high = [p.get("spectral_drop", {}).get("high", 0)
                    for p in profiles]

        # Fill standard
        std.lufs_median = _median(lufs)
        std.lufs_p10 = _pct(lufs, 10)
        std.lufs_p90 = _pct(lufs, 90)
        std.peak_db_median = _median(peaks)
        std.rms_db_median = _median(rms)
        std.crest_factor_median = _median(crests)
        std.dynamic_range_median = _median(drs)

        std.spectral_sub_median = _median(sp_sub)
        std.spectral_bass_median = _median(sp_bass)
        std.spectral_low_mid_median = _median(sp_lm)
        std.spectral_mid_median = _median(sp_mid)
        std.spectral_high_mid_median = _median(sp_hm)
        std.spectral_high_median = _median(sp_high)

        std.spectral_drop_sub_median = _median(spd_sub)
        std.spectral_drop_bass_median = _median(spd_bass)
        std.spectral_drop_low_mid_median = _median(spd_lm)
        std.spectral_drop_mid_median = _median(spd_mid)
        std.spectral_drop_high_mid_median = _median(spd_hm)
        std.spectral_drop_high_median = _median(spd_high)

        std.stereo_width_median = _median(widths)
        std.stereo_correlation_median = _median(corrs)
        std.intro_drop_contrast_median = _median(contrasts)
        std.duration_median = _median(durations)
        std.bpm_median = _median(bpms) if bpms else 0.0

        # ── New DNA medians (session 168) ──
        def _dna_vals(cat: str, key: str) -> list[float]:
            """Extract numeric values from dna.{cat}.{key} across profiles."""
            vals = []
            for p in profiles:
                dna = p.get("dna", {})
                v = dna.get(cat, {}).get(key)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            return vals

        # Style
        std.style_aggression_median = _median(_dna_vals("style", "aggression"))
        std.style_darkness_median = _median(_dna_vals("style", "darkness"))
        std.style_energy_median = _median(_dna_vals("style", "energy_level"))
        std.style_danceability_median = _median(
            _dna_vals("style", "danceability"))
        std.style_density_median = _median(_dna_vals("style", "density"))
        std.style_brightness_median = _median(_dna_vals("style", "brightness"))
        std.style_bass_dominance_median = _median(
            _dna_vals("style", "bass_dominance"))

        # Sound Design
        std.sd_attack_sharpness_median = _median(
            _dna_vals("sound_design", "attack_sharpness"))
        std.sd_modulation_depth_median = _median(
            _dna_vals("sound_design", "modulation_depth"))
        std.sd_texture_density_median = _median(
            _dna_vals("sound_design", "texture_density"))
        std.sd_spectral_movement_median = _median(
            _dna_vals("sound_design", "spectral_movement"))
        std.sd_inharmonicity_median = _median(
            _dna_vals("sound_design", "inharmonicity"))
        std.sd_noise_content_median = _median(
            _dna_vals("sound_design", "noise_content"))

        # Mixing
        std.mix_headroom_median = _median(_dna_vals("mixing", "headroom_db"))
        std.mix_freq_balance_median = _median(
            _dna_vals("mixing", "frequency_balance_score"))
        std.mix_mud_ratio_median = _median(_dna_vals("mixing", "mud_ratio"))
        std.mix_harshness_ratio_median = _median(
            _dna_vals("mixing", "harshness_ratio"))
        std.mix_air_ratio_median = _median(_dna_vals("mixing", "air_ratio"))
        std.mix_phase_low_median = _median(_dna_vals("mixing", "phase_low"))
        std.mix_separation_median = _median(
            _dna_vals("mixing", "separation_score"))

        # Mastering
        std.master_true_peak_median = _median(
            _dna_vals("mastering", "true_peak_db"))
        std.master_limiting_transparency_median = _median(
            _dna_vals("mastering", "limiting_transparency"))
        std.master_loudness_consistency_median = _median(
            _dna_vals("mastering", "loudness_consistency"))
        std.master_streaming_penalty_median = _median(
            _dna_vals("mastering", "streaming_loudness_penalty"))
        std.master_dynamic_complexity_median = _median(
            _dna_vals("mastering", "dynamic_complexity"))

        self._standard = std

        # Save to disk
        std_path = self.library_dir / "reference_standard.json"
        with open(std_path, "w", encoding="utf-8") as f:
            json.dump(std.to_dict(), f, indent=2)
        print(f"\n  Reference standard saved: {std_path}")
        self._print_standard(std)

    def _print_standard(self, std: ReferenceStandard) -> None:
        """Print the reference standard summary."""
        print(f"""
  ══════════════════════════════════════════════
   REFERENCE STANDARD ({std.track_count} tracks)
  ══════════════════════════════════════════════
   Loudness:
     LUFS median: {std.lufs_median:.1f}  (p10: {std.lufs_p10:.1f}, p90: {std.lufs_p90:.1f})
     Peak median: {std.peak_db_median:.1f} dB
     RMS median:  {std.rms_db_median:.1f} dB
     Crest:       {std.crest_factor_median:.1f} dB
     Dynamic:     {std.dynamic_range_median:.1f} dB

   Spectral Balance (full track):
     Sub (20-60):      {std.spectral_sub_median:.1%}
     Bass (60-250):    {std.spectral_bass_median:.1%}
     Low-Mid (250-500):{std.spectral_low_mid_median:.1%}
     Mid (500-2k):     {std.spectral_mid_median:.1%}
     High-Mid (2-6k):  {std.spectral_high_mid_median:.1%}
     High (6-20k):     {std.spectral_high_median:.1%}

   Spectral Balance (drop section):
     Sub:   {std.spectral_drop_sub_median:.1%}
     Bass:  {std.spectral_drop_bass_median:.1%}
     Lo-M:  {std.spectral_drop_low_mid_median:.1%}
     Mid:   {std.spectral_drop_mid_median:.1%}
     Hi-M:  {std.spectral_drop_high_mid_median:.1%}
     High:  {std.spectral_drop_high_median:.1%}

   Stereo:
     Width:       {std.stereo_width_median:.3f}
     Correlation: {std.stereo_correlation_median:.3f}

   Structure:
     Duration:    {std.duration_median:.0f}s ({int(std.duration_median // 60)}:{int(std.duration_median % 60):02d})
     BPM:         {std.bpm_median:.0f}
     Intro->Drop: +{std.intro_drop_contrast_median:.1f} dB

   Style (median):
     Energy:      {std.style_energy_median:.3f}
     Aggression:  {std.style_aggression_median:.3f}
     Darkness:    {std.style_darkness_median:.3f}
     Danceability:{std.style_danceability_median:.3f}
     Bass Dom:    {std.style_bass_dominance_median:.3f}

   Sound Design (median):
     Attack:      {std.sd_attack_sharpness_median:.3f}
     Modulation:  {std.sd_modulation_depth_median:.3f}
     Texture:     {std.sd_texture_density_median:.3f}
     Movement:    {std.sd_spectral_movement_median:.3f}

   Mixing (median):
     Headroom:    {std.mix_headroom_median:.1f} dB
     Freq Balance:{std.mix_freq_balance_median:.3f}
     Mud Ratio:   {std.mix_mud_ratio_median:.3f}
     Phase (low): {std.mix_phase_low_median:.3f}
     Separation:  {std.mix_separation_median:.3f}

   Mastering (median):
     True Peak:   {std.master_true_peak_median:.1f} dBTP
     Transparency:{std.master_limiting_transparency_median:.3f}
     Consistency: {std.master_loudness_consistency_median:.2f}
     Stream Pen.: {std.master_streaming_penalty_median:.1f} dB
     Dyn Complex: {std.master_dynamic_complexity_median:.3f}
  ══════════════════════════════════════════════""")

    # ── Get standard ──────────────────────────────────────────────────

    def get_standard(self) -> ReferenceStandard:
        """Load or compute the reference standard."""
        if self._standard is not None:
            return self._standard

        std_path = self.library_dir / "reference_standard.json"
        if std_path.exists():
            with open(std_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            std = ReferenceStandard()
            for k, v in data.items():
                if hasattr(std, k):
                    setattr(std, k, v)
            self._standard = std
            return std

        # Build from profiles
        self._build_standard()
        if self._standard is None:
            return ReferenceStandard()
        return self._standard

    # ── Compare ──────────────────────────────────────────────────────

    def compare(self, track_path: str) -> ComparisonResult:
        """
        Compare a DUBFORGE render to the reference standard.
        Returns a scored ComparisonResult.
        """
        std = self.get_standard()
        if std.track_count == 0:
            return ComparisonResult(
                track_name=os.path.basename(track_path),
                issues=["No reference library. Run scan first."]
            )

        analysis = analyze_track(track_path)
        result = ComparisonResult()
        result.track_name = analysis.filename

        # ── Loudness score ──
        lufs_diff = abs(analysis.lufs_estimate - std.lufs_median)
        lufs_score = max(0.0, 1.0 - lufs_diff / 8.0)
        result.loudness_score = lufs_score

        if analysis.lufs_estimate < std.lufs_p10 - 3:
            result.issues.append(
                f"Too quiet: {analysis.lufs_estimate:.1f} LUFS "
                f"(ref median: {std.lufs_median:.1f})")
        elif analysis.lufs_estimate > std.lufs_p90 + 2:
            result.issues.append(
                f"Too loud / over-compressed: {analysis.lufs_estimate:.1f} LUFS "
                f"(ref median: {std.lufs_median:.1f})")
        else:
            result.strengths.append(
                f"Loudness on target: {analysis.lufs_estimate:.1f} LUFS")

        if analysis.peak_db > -0.1:
            result.issues.append(
                f"Clipping risk: peak at {analysis.peak_db:.1f} dB")

        # ── Spectral score ──
        sp = analysis.spectral
        ref_sp = [std.spectral_sub_median, std.spectral_bass_median,
                  std.spectral_low_mid_median, std.spectral_mid_median,
                  std.spectral_high_mid_median, std.spectral_high_median]
        your_sp = [sp.sub, sp.bass, sp.low_mid, sp.mid, sp.high_mid, sp.high]
        band_names = ["Sub", "Bass", "Low-Mid", "Mid", "High-Mid", "High"]

        sp_diffs = [abs(y - r) for y, r in zip(your_sp, ref_sp)]
        spectral_score = max(0.0, 1.0 - sum(sp_diffs) / 0.5)
        result.spectral_score = spectral_score

        for name, yours, ref, diff in zip(band_names, your_sp, ref_sp,
                                          sp_diffs):
            if diff > 0.08:
                direction = "high" if yours > ref else "low"
                result.issues.append(
                    f"{name} band {direction}: {yours:.1%} vs ref {ref:.1%}")
            elif diff < 0.03:
                result.strengths.append(
                    f"{name} band balanced: {yours:.1%}")

        # ── Dynamics score ──
        dr_diff = abs(analysis.dynamic_range_db - std.dynamic_range_median)
        dynamics_score = max(0.0, 1.0 - dr_diff / 10.0)
        result.dynamics_score = dynamics_score

        if analysis.crest_factor_db < std.crest_factor_median - 3:
            result.issues.append(
                f"Over-compressed: crest {analysis.crest_factor_db:.1f} dB "
                f"(ref: {std.crest_factor_median:.1f})")
        elif analysis.crest_factor_db > std.crest_factor_median + 5:
            result.issues.append(
                f"Under-compressed: crest {analysis.crest_factor_db:.1f} dB "
                f"(ref: {std.crest_factor_median:.1f})")

        # ── Stereo score ──
        w_diff = abs(analysis.stereo_width - std.stereo_width_median)
        stereo_score = max(0.0, 1.0 - w_diff / 0.3)
        result.stereo_score = stereo_score

        if analysis.stereo_width < std.stereo_width_median * 0.5:
            result.issues.append(
                f"Too narrow: width {analysis.stereo_width:.3f} "
                f"(ref: {std.stereo_width_median:.3f})")
        elif analysis.stereo_width > std.stereo_width_median * 2.0:
            result.issues.append(
                f"Too wide: width {analysis.stereo_width:.3f} "
                f"(ref: {std.stereo_width_median:.3f})")
        else:
            result.strengths.append(
                f"Stereo width balanced: {analysis.stereo_width:.3f}")

        # ── Contrast score ──
        c_diff = abs(analysis.intro_drop_contrast_db
                     - std.intro_drop_contrast_median)
        contrast_score = max(0.0, 1.0 - c_diff / 12.0)
        result.contrast_score = contrast_score

        if analysis.intro_drop_contrast_db < 3.0:
            result.issues.append(
                f"Weak intro→drop contrast: {analysis.intro_drop_contrast_db:.1f} dB "
                f"(ref: {std.intro_drop_contrast_median:.1f})")
        else:
            result.strengths.append(
                f"Good section contrast: +{analysis.intro_drop_contrast_db:.1f} dB")

        # ── Overall score (weighted) ──
        result.overall_score = (
            lufs_score * 25.0
            + spectral_score * 30.0
            + dynamics_score * 15.0
            + stereo_score * 15.0
            + contrast_score * 15.0
        )

        # ── Details dict for downstream use ──
        result.details = {
            "your_lufs": round(analysis.lufs_estimate, 1),
            "ref_lufs_median": round(std.lufs_median, 1),
            "your_peak_db": round(analysis.peak_db, 1),
            "your_rms_db": round(analysis.rms_db, 1),
            "your_crest_db": round(analysis.crest_factor_db, 1),
            "your_dynamic_range_db": round(analysis.dynamic_range_db, 1),
            "your_stereo_width": round(analysis.stereo_width, 4),
            "your_bpm": round(analysis.estimated_bpm, 1),
            "your_duration_s": round(analysis.duration_s, 1),
            "your_spectral": {
                "sub": round(sp.sub, 4),
                "bass": round(sp.bass, 4),
                "low_mid": round(sp.low_mid, 4),
                "mid": round(sp.mid, 4),
                "high_mid": round(sp.high_mid, 4),
                "high": round(sp.high, 4),
            },
            "ref_spectral": {
                "sub": round(std.spectral_sub_median, 4),
                "bass": round(std.spectral_bass_median, 4),
                "low_mid": round(std.spectral_low_mid_median, 4),
                "mid": round(std.spectral_mid_median, 4),
                "high_mid": round(std.spectral_high_mid_median, 4),
                "high": round(std.spectral_high_median, 4),
            },
        }

        return result

    def compare_and_print(self, track_path: str) -> ComparisonResult:
        """Compare and print formatted results."""
        result = self.compare(track_path)
        self._print_comparison(result)
        return result

    def _print_comparison(self, result: ComparisonResult) -> None:
        """Print comparison result."""
        grade = "A+" if result.overall_score >= 90 else \
                "A" if result.overall_score >= 80 else \
                "B" if result.overall_score >= 70 else \
                "C" if result.overall_score >= 60 else \
                "D" if result.overall_score >= 50 else "F"

        print(f"""
  ══════════════════════════════════════════════
   REFERENCE COMPARISON: {result.track_name}
  ══════════════════════════════════════════════
   Overall Score: {result.overall_score:.0f}/100 ({grade})

   Loudness:  {result.loudness_score:.0%}
   Spectral:  {result.spectral_score:.0%}
   Dynamics:  {result.dynamics_score:.0%}
   Stereo:    {result.stereo_score:.0%}
   Contrast:  {result.contrast_score:.0%}""")

        if result.strengths:
            print("\n   Strengths:")
            for s in result.strengths:
                print(f"     + {s}")

        if result.issues:
            print("\n   Issues:")
            for issue in result.issues:
                print(f"     - {issue}")

        d = result.details
        print(f"""
   Your Track:
     LUFS: {d.get('your_lufs', '?')} | Peak: {d.get('your_peak_db', '?')} dB
     RMS: {d.get('your_rms_db', '?')} dB | Crest: {d.get('your_crest_db', '?')} dB
     Width: {d.get('your_stereo_width', '?')} | BPM: {d.get('your_bpm', '?')}
     Duration: {d.get('your_duration_s', 0):.0f}s
  ══════════════════════════════════════════════""")

    # ── List ──────────────────────────────────────────────────────────

    def list_tracks(self) -> list[str]:
        """List all analyzed track names."""
        return sorted(p.stem for p in self.profiles_dir.glob("*.json"))

    def report(self) -> None:
        """Print the reference standard."""
        std = self.get_standard()
        if std.track_count == 0:
            print("  No reference library. Run scan first.")
            return
        self._print_standard(std)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """CLI entry point."""
    args = sys.argv[1:]
    lib = ReferenceLibrary()

    if not args or args[0] == "help":
        print("""
  DUBFORGE Reference Library Analyzer
  ────────────────────────────────────
  Commands:
    scan [--force]              Analyze all reference tracks
    compare <path.wav>          Score a track vs reference standard
    report                      Print aggregate reference standard
    list                        List analyzed tracks
    analyze <path.wav>          Deep-analyze a single file (print JSON)
        """)
        return

    cmd = args[0]

    if cmd == "scan":
        force = "--force" in args
        lib.scan(force=force)

    elif cmd == "compare":
        if len(args) < 2:
            print("  Usage: compare <path.wav>")
            return
        lib.compare_and_print(args[1])

    elif cmd == "report":
        lib.report()

    elif cmd == "list":
        tracks = lib.list_tracks()
        print(f"\n  {len(tracks)} analyzed tracks:")
        for t in tracks:
            print(f"    {t}")

    elif cmd == "analyze":
        if len(args) < 2:
            print("  Usage: analyze <path.wav>")
            return
        analysis = analyze_track(args[1])
        print(json.dumps(analysis.to_dict(), indent=2))

    else:
        print(f"  Unknown command: {cmd}")


if __name__ == "__main__":
    main()
