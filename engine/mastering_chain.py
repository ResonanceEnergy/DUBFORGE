"""
DUBFORGE Engine — Mastering Chain

A pure-Python / NumPy mastering chain for loudness normalization,
EQ, compression, limiting, and stereo widening.

Uses pyloudnorm for LUFS metering when available, otherwise
approximates integrated loudness from RMS.

Outputs:
    output/masters/*.wav   — Mastered audio files
    output/masters/master_report.json — Mastering chain report
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)

_log = get_logger("dubforge.mastering_chain")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_RATE = 48000
TARGET_LUFS = -14.0           # Streaming target (Spotify / Apple Music)
TRUE_PEAK_CEILING_DB = -1.0   # True-peak limiter ceiling
LOOKAHEAD_MS = 5.0            # Limiter lookahead


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MasterSettings:
    """Mastering chain configuration."""
    target_lufs: float = TARGET_LUFS
    ceiling_db: float = TRUE_PEAK_CEILING_DB
    eq_low_shelf_db: float = 0.0         # Low-shelf gain (< 100 Hz)
    eq_low_shelf_freq: float = 100.0
    eq_high_shelf_db: float = 0.0        # High-shelf gain (> 8k Hz)
    eq_high_shelf_freq: float = 8000.0
    eq_mid_boost_db: float = 0.0         # Parametric mid-band
    eq_mid_freq: float = 2500.0
    eq_mid_q: float = 1.0
    compression_threshold_db: float = -12.0
    compression_ratio: float = 3.0
    compression_attack_ms: float = 10.0
    compression_release_ms: float = 100.0
    multiband_threshold_db: float = -12.0   # Multiband comp threshold (was hardcoded)
    multiband_ratio: float = 3.0            # Multiband comp ratio (was hardcoded)
    stereo_width: float = 1.0            # 1.0 = unchanged, >1 = wider
    limiter_enabled: bool = True


@dataclass
class MasterReport:
    """Analysis report of a mastering pass."""
    input_file: str = ""
    output_file: str = ""
    input_peak_db: float = 0.0
    output_peak_db: float = 0.0
    input_rms_db: float = 0.0
    output_rms_db: float = 0.0
    input_lufs: float = 0.0
    output_lufs: float = 0.0
    gain_applied_db: float = 0.0
    settings: MasterSettings = field(default_factory=MasterSettings)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 20.0)


def linear_to_db(lin: float) -> float:
    if lin <= 0:
        return -120.0
    return 20.0 * np.log10(lin)


def peak_db(audio: np.ndarray) -> float:
    return linear_to_db(np.max(np.abs(audio)))


def rms_db(audio: np.ndarray) -> float:
    rms = np.sqrt(np.mean(audio ** 2))
    return linear_to_db(rms)


def estimate_lufs(audio: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """
    Estimate integrated loudness in LUFS.
    Uses pyloudnorm if available, otherwise approximates from RMS.
    """
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        if audio.ndim == 1:
            audio_stereo = np.column_stack([audio, audio])
        else:
            audio_stereo = audio
        return meter.integrated_loudness(audio_stereo)
    except ImportError:
        pass

    # Approximation: LUFS ≈ RMS_dB - 0.691 (K-weighted approx for bass-heavy)
    return rms_db(audio) - 0.691


# ═══════════════════════════════════════════════════════════════════════════
# EQ (Biquad)
# ═══════════════════════════════════════════════════════════════════════════

def _biquad_filter(audio: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Apply a 2nd-order IIR (biquad) filter sample-by-sample."""
    if audio.ndim == 1:
        return _biquad_mono(audio, b, a)
    else:
        result = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            result[:, ch] = _biquad_mono(audio[:, ch], b, a)
        return result


def _biquad_mono(x: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Mono biquad using direct form II transposed."""
    y = np.zeros(len(x))
    z1, z2 = 0.0, 0.0
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]
    for i in range(len(x)):
        inp = x[i]
        out = b0 * inp + z1
        z1 = b1 * inp - a1 * out + z2
        z2 = b2 * inp - a2 * out
        y[i] = out
    return y


def low_shelf(audio: np.ndarray, freq: float, gain_db: float,
              sr: int = SAMPLE_RATE) -> np.ndarray:
    """Low-shelf biquad filter."""
    if abs(gain_db) < 0.01:
        return audio
    A = db_to_linear(gain_db / 2.0)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * np.sqrt(A))

    cos_w0 = np.cos(w0)
    a0 = (A + 1) + (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha
    b = np.array([
        A * ((A + 1) - (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha) / a0,
        2 * A * ((A - 1) - (A + 1) * cos_w0) / a0,
        A * ((A + 1) - (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha) / a0,
    ])
    a = np.array([
        1.0,
        -2 * ((A - 1) + (A + 1) * cos_w0) / a0,
        ((A + 1) + (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha) / a0,
    ])
    return _biquad_filter(audio, b, a)


def high_shelf(audio: np.ndarray, freq: float, gain_db: float,
               sr: int = SAMPLE_RATE) -> np.ndarray:
    """High-shelf biquad filter."""
    if abs(gain_db) < 0.01:
        return audio
    A = db_to_linear(gain_db / 2.0)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * np.sqrt(A))

    cos_w0 = np.cos(w0)
    a0 = (A + 1) - (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha
    b = np.array([
        A * ((A + 1) + (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha) / a0,
        -2 * A * ((A - 1) + (A + 1) * cos_w0) / a0,
        A * ((A + 1) + (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha) / a0,
    ])
    a = np.array([
        1.0,
        2 * ((A - 1) - (A + 1) * cos_w0) / a0,
        ((A + 1) - (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha) / a0,
    ])
    return _biquad_filter(audio, b, a)


def peaking_eq(audio: np.ndarray, freq: float, gain_db: float,
               q: float = 1.0, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Parametric peaking EQ biquad."""
    if abs(gain_db) < 0.01:
        return audio
    A = db_to_linear(gain_db / 2.0)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)

    cos_w0 = np.cos(w0)
    a0 = 1 + alpha / A
    b = np.array([
        (1 + alpha * A) / a0,
        -2 * cos_w0 / a0,
        (1 - alpha * A) / a0,
    ])
    a = np.array([
        1.0,
        -2 * cos_w0 / a0,
        (1 - alpha / A) / a0,
    ])
    return _biquad_filter(audio, b, a)


def highpass(audio: np.ndarray, freq: float, q: float = 0.707,
             sr: int = SAMPLE_RATE) -> np.ndarray:
    """2nd-order Butterworth highpass biquad — removes sub rumble."""
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)
    a0 = 1 + alpha
    b = np.array([
        ((1 + cos_w0) / 2) / a0,
        -(1 + cos_w0) / a0,
        ((1 + cos_w0) / 2) / a0,
    ])
    a = np.array([
        1.0,
        -2 * cos_w0 / a0,
        (1 - alpha) / a0,
    ])
    return _biquad_filter(audio, b, a)


def apply_eq(audio: np.ndarray, settings: MasterSettings,
             sr: int = SAMPLE_RATE) -> np.ndarray:
    """Apply the full EQ chain: HPF → shelves → parametric."""
    # Highpass at 45 Hz — F1=43.65Hz, this catches the fundamental
    out = highpass(audio, 45.0, q=0.707, sr=sr)
    out = low_shelf(out, settings.eq_low_shelf_freq, settings.eq_low_shelf_db, sr)
    out = high_shelf(out, settings.eq_high_shelf_freq, settings.eq_high_shelf_db, sr)
    out = peaking_eq(out, settings.eq_mid_freq, settings.eq_mid_boost_db, settings.eq_mid_q, sr)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# DYNAMICS: COMPRESSOR
# ═══════════════════════════════════════════════════════════════════════════

def compress(audio: np.ndarray, settings: MasterSettings,
             sr: int = SAMPLE_RATE) -> np.ndarray:
    """Apply dynamic range compression."""
    threshold_lin = db_to_linear(settings.compression_threshold_db)
    ratio = settings.compression_ratio
    attack_coeff = np.exp(-1.0 / (settings.compression_attack_ms * sr / 1000))
    release_coeff = np.exp(-1.0 / (settings.compression_release_ms * sr / 1000))

    if audio.ndim == 1:
        mono = audio
    else:
        mono = np.mean(audio, axis=1)

    envelope = np.zeros(len(mono))
    env = 0.0
    for i in range(len(mono)):
        level = abs(mono[i])
        if level > env:
            env = attack_coeff * env + (1 - attack_coeff) * level
        else:
            env = release_coeff * env + (1 - release_coeff) * level
        envelope[i] = max(env, 1e-10)

    gain = np.ones_like(envelope)
    mask = envelope > threshold_lin
    gain[mask] = (threshold_lin / envelope[mask]) ** (1 - 1 / ratio)

    if audio.ndim == 1:
        return audio * gain
    else:
        return audio * gain[:, np.newaxis]


# ═══════════════════════════════════════════════════════════════════════════
# LIMITER
# ═══════════════════════════════════════════════════════════════════════════

def limit(audio: np.ndarray, ceiling_db: float = TRUE_PEAK_CEILING_DB,
          lookahead_ms: float = LOOKAHEAD_MS,
          sr: int = SAMPLE_RATE) -> np.ndarray:
    """Brickwall true-peak limiter (vectorized)."""
    ceiling_lin = db_to_linear(ceiling_db)
    lookahead = int(lookahead_ms * sr / 1000)

    if audio.ndim == 1:
        abs_audio = np.abs(audio)
    else:
        abs_audio = np.max(np.abs(audio), axis=1)

    # Vectorized peak envelope with lookahead (rolling max)
    peak_env = np.copy(abs_audio)
    for shift in range(1, lookahead):
        shifted = np.empty_like(abs_audio)
        shifted[:-shift] = abs_audio[shift:]
        shifted[-shift:] = 0.0
        np.maximum(peak_env, shifted, out=peak_env)

    gain = np.where(
        peak_env > ceiling_lin,
        ceiling_lin / np.maximum(peak_env, 1e-10),
        1.0,
    )

    # Smooth gain (attack/release)
    smoothed = np.ones_like(gain)
    coeff = 0.9995
    smoothed[0] = gain[0]
    for i in range(1, len(gain)):
        if gain[i] < smoothed[i - 1]:
            smoothed[i] = gain[i]  # instant attack
        else:
            smoothed[i] = coeff * smoothed[i - 1] + (1 - coeff) * gain[i]

    if audio.ndim == 1:
        return audio * smoothed
    else:
        return audio * smoothed[:, np.newaxis]


# ═══════════════════════════════════════════════════════════════════════════
# STEREO WIDTH
# ═══════════════════════════════════════════════════════════════════════════

def stereo_widen(audio: np.ndarray, width: float = 1.0) -> np.ndarray:
    """Adjust stereo width using mid/side processing."""
    if audio.ndim == 1 or width == 1.0:
        return audio
    if audio.shape[1] < 2:
        return audio

    left = audio[:, 0]
    right = audio[:, 1]

    mid = (left + right) / 2.0
    side = (left - right) / 2.0

    # Phi-weighted width
    side *= width

    result = np.column_stack([mid + side, mid - side])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# LOUDNESS NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def loudness_normalize(audio: np.ndarray, target_lufs: float = TARGET_LUFS,
                       sr: int = SAMPLE_RATE) -> tuple[np.ndarray, float]:
    """Normalize audio to target LUFS. Returns (normalized, gain_db)."""
    current_lufs = estimate_lufs(audio, sr)
    if current_lufs <= -120:
        return audio, 0.0
    gain_db = target_lufs - current_lufs
    gain_lin = db_to_linear(gain_db)
    return audio * gain_lin, gain_db


# ═══════════════════════════════════════════════════════════════════════════
# MASTERING CHAIN
# ═══════════════════════════════════════════════════════════════════════════

def master(audio: np.ndarray, sr: int = SAMPLE_RATE,
           settings: MasterSettings | None = None) -> tuple[np.ndarray, MasterReport]:
    """
    Run the full mastering chain:
        EQ → Multiband Compress → Compress → Stereo Width →
        Loudness Normalize → Soft Clip → Limit

    Returns (mastered_audio, report).
    """
    from engine.dsp_core import multiband_compress, soft_clip

    if settings is None:
        settings = MasterSettings()

    report = MasterReport(settings=settings)
    report.input_peak_db = peak_db(audio)
    report.input_rms_db = rms_db(audio)
    report.input_lufs = estimate_lufs(audio, sr)

    # 1. EQ
    out = apply_eq(audio.astype(np.float64), settings, sr)

    # 2. Multiband compression (essential for dubstep — glue + control)
    if out.ndim == 2:
        for ch in range(out.shape[1]):
            out[:, ch] = multiband_compress(
                out[:, ch], sr,
                low_xover=120.0, high_xover=4000.0,
                threshold_db=settings.multiband_threshold_db,
                ratio=settings.multiband_ratio
            )
    else:
        out = multiband_compress(
            out, sr,
            low_xover=120.0, high_xover=4000.0,
            threshold_db=settings.multiband_threshold_db,
            ratio=settings.multiband_ratio
        )

    # 3. Bus compression
    out = compress(out, settings, sr)

    # 4. Stereo width
    out = stereo_widen(out, settings.stereo_width)

    # 5. Loudness normalize
    out, gain = loudness_normalize(out, settings.target_lufs, sr)
    report.gain_applied_db = gain

    # 6. Soft clip before limiter (catches transients, adds warmth)
    out = soft_clip(out)

    # 7. Limit
    if settings.limiter_enabled:
        out = limit(out, settings.ceiling_db, sr=sr)

    report.output_peak_db = peak_db(out)
    report.output_rms_db = rms_db(out)
    report.output_lufs = estimate_lufs(out, sr)

    _log.info("Mastered: %.1f LUFS → %.1f LUFS (gain: %.1f dB)",
              report.input_lufs, report.output_lufs, report.gain_applied_db)

    # TurboQuant compress mastered output
    flat = out.flatten().tolist()
    tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(flat)))
    compress_audio_buffer(
        flat, "mastered_output", tq_cfg,
        sample_rate=sr, label="master",
    )

    return out, report


# ═══════════════════════════════════════════════════════════════════════════
# FILE-LEVEL API
# ═══════════════════════════════════════════════════════════════════════════

def master_file(input_path: str, output_path: str | None = None,
                settings: MasterSettings | None = None) -> MasterReport:
    """Master a WAV file and write the result."""
    from engine.sample_slicer import read_audio, write_audio

    audio, sr = read_audio(input_path)
    mastered, report = master(audio, sr, settings)

    if output_path is None:
        stem = Path(input_path).stem
        output_path = f"output/masters/{stem}_mastered.wav"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    write_audio(output_path, mastered, sr)

    report.input_file = input_path
    report.output_file = output_path
    _log.info("Mastered file: %s → %s", input_path, output_path)
    return report


def write_master_report(reports: list[MasterReport],
                        output_dir: str = "output/masters") -> str:
    """Write mastering chain report to JSON."""
    data = {
        "generator": "DUBFORGE Mastering Chain",
        "target_lufs": TARGET_LUFS,
        "ceiling_db": TRUE_PEAK_CEILING_DB,
        "files": [asdict(r) for r in reports],
    }
    path = Path(output_dir) / "master_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# DUBSTEP PRESETS
# ═══════════════════════════════════════════════════════════════════════════

def dubstep_master_settings() -> MasterSettings:
    """Aggressive dubstep mastering preset.

    EQ philosophy: sub should be CONTROLLED, not boosted.
    Reference standard shows ~4% sub, ~21% bass, ~22% mid.
    Low shelf is a gentle CUT to tame sub bleed.
    Mid peaking adds presence that competes with bass.
    """
    return MasterSettings(
        target_lufs=-10.0,
        ceiling_db=-0.3,
        eq_low_shelf_db=-2.5,      # Stronger sub taming
        eq_low_shelf_freq=80.0,
        eq_high_shelf_db=2.5,      # More air + brightness
        eq_high_shelf_freq=10000.0,
        eq_mid_boost_db=1.5,       # Moderate mid presence
        eq_mid_freq=2500.0,        # Presence band
        eq_mid_q=0.8,
        compression_threshold_db=-8.0,
        compression_ratio=4.0,
        compression_attack_ms=5.0,
        compression_release_ms=60.0,
        stereo_width=1.0 + 1.0 / PHI,  # Phi-wide
        limiter_enabled=True,
    )


def streaming_master_settings() -> MasterSettings:
    """Standard streaming-friendly mastering preset."""
    return MasterSettings(
        target_lufs=-14.0,
        ceiling_db=-1.0,
        eq_low_shelf_db=0.5,
        eq_low_shelf_freq=100.0,
        eq_high_shelf_db=0.5,
        eq_high_shelf_freq=8000.0,
        compression_threshold_db=-15.0,
        compression_ratio=2.5,
        compression_attack_ms=15.0,
        compression_release_ms=150.0,
        stereo_width=1.0,
        limiter_enabled=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Master any wavetable WAV files found in output/wavetables/."""
    wt_dir = Path("output/wavetables")
    out_dir = Path("output/masters")
    wav_files = list(wt_dir.glob("*.wav")) if wt_dir.exists() else []

    if not wav_files:
        print("  No WAV files found in output/wavetables/ — skipping mastering demo.")
        print("  (Run phi_core or growl_resampler first to generate wavetables.)")
        return

    reports = []
    for wav in wav_files:
        print(f"  Mastering {wav.name}...")
        report = master_file(str(wav), settings=dubstep_master_settings())
        reports.append(report)
        print(f"    {report.input_lufs:.1f} LUFS → {report.output_lufs:.1f} LUFS  "
              f"(peak: {report.output_peak_db:.1f} dB)")

    if reports:
        write_master_report(reports, str(out_dir))
        print("  master_report.json")

    print(f"Mastering Chain complete — {len(reports)} files mastered.")


if __name__ == "__main__":
    main()
