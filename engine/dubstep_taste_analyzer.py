"""
DUBFORGE Engine — Dubstep Taste Analyzer

Per-stem feature extraction engine calibrated to Producer Dojo / ill.Gates
techniques and DUBFORGE builder parameters. Analyzes reference tracks to
build a personal "taste prototype" that guides generation.

Features extracted per stem:
    - BPM, half-time groove detection
    - Sub RMS / golden zone (40-110 Hz) match
    - Wobble rate (LFO speed from spectral flux autocorrelation)
    - Volume modulation fidelity (ill.Gates 80/20 Sound Design)
    - Modulation depth
    - Transient sharpness (attack quality)
    - Clipping headroom (dB below 0 dBFS)
    - Group gain staging balance
    - Resample chaos score (spectral complexity)
    - 128s compatibility score (Simpler readiness)
    - Drop conversion potential
    - Dynamic range
    - Spectral centroid mean
    - Hybrid vector (scalar features + perceptual embedding)

Stems: sub, bass, drums, mids_growls, atmos_fx

Outputs:
    output/taste/stem_analysis.json
    output/taste/prototypes.json
    output/taste/taste_report.md

Dependencies (optional — gracefully degrades):
    librosa, numpy, soundfile — for actual audio analysis
    Without them, only metadata-based analysis is available.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from engine.config_loader import FIBONACCI, PHI, get_config_value
from engine.log import get_logger

_log = get_logger("dubforge.taste_analyzer")

# ═══════════════════════════════════════════════════════════════════════════
# OPTIONAL IMPORTS — graceful degradation
# ═══════════════════════════════════════════════════════════════════════════

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    HAS_NUMPY = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    librosa = None  # type: ignore[assignment]
    HAS_LIBROSA = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    HAS_SOUNDFILE = False

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_RATE = 48000
STEM_TYPES = ("sub", "bass", "drums", "mids_growls", "atmos_fx")

# ill.Gates / Producer Dojo calibration
GOLDEN_BASS_LOW_HZ = 40.0
GOLDEN_BASS_HIGH_HZ = 110.0
HARD_CLIP_CEILING_DB = -3.0
VOLUME_MOD_WEIGHT = 0.80       # 80/20 rule: volume modulation > filter LFOs
FILTER_MOD_WEIGHT = 0.20

# Dubstep BPM ranges
DUBSTEP_BPM_MIN = 130
DUBSTEP_BPM_MAX = 155
HALFTIME_BPM_MIN = 65
HALFTIME_BPM_MAX = 77

# Feature vector dimension (scalar features count)
N_SCALAR_FEATURES = 15

# Perceptual embedding dim (when available)
EMBEDDING_DIM = 512   # OpenL3/CLAP size


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StemFeatures:
    """Feature extraction result for a single stem."""
    stem_type: str = ""
    source_file: str = ""

    # Tempo
    bpm: float = 0.0
    half_time_groove: bool = False

    # Spectral / tonal
    sub_rms_db: float = -96.0
    golden_zone_match: float = 0.0        # 0-1, energy in 40-110 Hz vs total
    spectral_centroid_mean: float = 0.0   # Hz

    # Modulation (ill.Gates 80/20)
    wobble_rate_hz: float = 0.0           # dominant LFO rate
    volume_mod_fidelity: float = 0.0      # 0-1, how much modulation is volume-based
    mod_depth: float = 0.0                # 0-1, overall modulation intensity

    # Dynamics
    transient_sharpness: float = 0.0      # 0-1, attack quality
    clipping_headroom_db: float = 0.0     # dB below 0 dBFS at peak
    dynamic_range_db: float = 0.0         # peak-to-RMS in dB

    # Dojo / resampling
    group_gain_staging_balance: float = 0.0  # 0-1, how balanced levels are
    resample_chaos_score: float = 0.0        # 0-1, spectral complexity
    simpler_128s_compatibility: float = 0.0  # 0-1, suitability for 128s rack
    drop_conversion_potential: float = 0.0   # 0-1, energy transition quality

    # Embedding (filled when OpenL3/CLAP available)
    embedding: list[float] = field(default_factory=list)

    @property
    def scalar_vector(self) -> list[float]:
        """Return the 15-dim scalar feature vector."""
        return [
            self.bpm,
            float(self.half_time_groove),
            self.sub_rms_db,
            self.golden_zone_match,
            self.spectral_centroid_mean,
            self.wobble_rate_hz,
            self.volume_mod_fidelity,
            self.mod_depth,
            self.transient_sharpness,
            self.clipping_headroom_db,
            self.dynamic_range_db,
            self.group_gain_staging_balance,
            self.resample_chaos_score,
            self.simpler_128s_compatibility,
            self.drop_conversion_potential,
        ]

    @property
    def hybrid_vector(self) -> list[float]:
        """Scalar features + perceptual embedding (if available)."""
        return self.scalar_vector + self.embedding

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scalar_vector"] = self.scalar_vector
        d["hybrid_vector_dim"] = len(self.hybrid_vector)
        return d


@dataclass
class TrackAnalysis:
    """Full analysis of one reference track (all stems)."""
    track_name: str = ""
    source_url: str = ""
    stems: dict[str, StemFeatures] = field(default_factory=dict)
    overall_bpm: float = 0.0
    overall_energy: float = 0.0
    banger_score: float = 0.0     # 0-100, computed from all features
    thumbs: Optional[str] = None  # "up" | "down" | None (user feedback)

    def to_dict(self) -> dict:
        return {
            "track_name": self.track_name,
            "source_url": self.source_url,
            "overall_bpm": round(self.overall_bpm, 1),
            "overall_energy": round(self.overall_energy, 3),
            "banger_score": round(self.banger_score, 1),
            "thumbs": self.thumbs,
            "stems": {k: v.to_dict() for k, v in self.stems.items()},
        }


@dataclass
class TastePrototype:
    """Averaged feature vector per stem type — your personal taste fingerprint."""
    stem_type: str = ""
    mean_vector: list[float] = field(default_factory=list)
    std_vector: list[float] = field(default_factory=list)
    sample_count: int = 0

    def to_dict(self) -> dict:
        return {
            "stem_type": self.stem_type,
            "mean_vector": [round(v, 6) for v in self.mean_vector],
            "std_vector": [round(v, 6) for v in self.std_vector],
            "sample_count": self.sample_count,
            "vector_dim": len(self.mean_vector),
        }


@dataclass
class TasteProfile:
    """Complete taste profile built from multiple reference tracks."""
    prototypes: dict[str, TastePrototype] = field(default_factory=dict)
    track_count: int = 0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0

    def to_dict(self) -> dict:
        return {
            "track_count": self.track_count,
            "thumbs_up_count": self.thumbs_up_count,
            "thumbs_down_count": self.thumbs_down_count,
            "prototypes": {k: v.to_dict() for k, v in self.prototypes.items()},
        }


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION — per-stem analysis
# ═══════════════════════════════════════════════════════════════════════════

def _require_audio_deps() -> None:
    """Raise ImportError if core audio deps are missing."""
    missing = []
    if not HAS_NUMPY:
        missing.append("numpy")
    if not HAS_LIBROSA:
        missing.append("librosa")
    if not HAS_SOUNDFILE:
        missing.append("soundfile")
    if missing:
        raise ImportError(
            f"Audio analysis requires: {', '.join(missing)}. "
            f"Install with: pip install {' '.join(missing)}"
        )


def _load_audio(filepath: str, sr: int = SAMPLE_RATE) -> tuple:
    """Load audio file, return (signal_mono, sample_rate)."""
    _require_audio_deps()
    y, loaded_sr = librosa.load(filepath, sr=sr, mono=True)
    return y, loaded_sr


def estimate_wobble_rate(y, sr: int = SAMPLE_RATE) -> float:
    """
    Estimate dominant LFO / wobble rate via spectral flux autocorrelation.

    Measures how quickly the spectral content is oscillating — the hallmark
    of dubstep wobble bass.

    Returns rate in Hz (typically 0.5–8 Hz for dubstep).
    """
    _require_audio_deps()
    # Spectral flux
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    flux = np.sqrt(np.mean(np.diff(S, axis=1) ** 2, axis=0))

    if len(flux) < 4:
        return 0.0

    # Autocorrelation of flux
    flux_centered = flux - np.mean(flux)
    corr = np.correlate(flux_centered, flux_centered, mode='full')
    corr = corr[len(corr) // 2:]  # keep positive lags only

    if len(corr) < 3:
        return 0.0

    # Normalize
    if corr[0] > 0:
        corr = corr / corr[0]

    # Find first peak after zero-crossing (skip lag 0)
    min_lag = 2   # skip trivially short
    max_lag = min(len(corr), int(sr / 512 * 4))  # up to 4 seconds

    search = corr[min_lag:max_lag]
    if len(search) < 2:
        return 0.0

    peak_idx = int(np.argmax(search)) + min_lag
    if peak_idx <= 0:
        return 0.0

    # Convert lag to Hz
    hop_rate = sr / 512  # frames per second
    wobble_hz = hop_rate / peak_idx
    return float(wobble_hz)


def _compute_golden_zone_match(y, sr: int = SAMPLE_RATE) -> float:
    """
    Compute fraction of energy in the golden bass zone (40-110 Hz).

    ill.Gates: "The golden zone is where sub-bass lives. If you're not
    dominating 40-110 Hz, you're not making dubstep."
    """
    _require_audio_deps()
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

    # Energy in golden zone
    mask_golden = (freqs >= GOLDEN_BASS_LOW_HZ) & (freqs <= GOLDEN_BASS_HIGH_HZ)
    golden_energy = float(np.sum(S[mask_golden, :] ** 2))
    total_energy = float(np.sum(S ** 2))

    if total_energy < 1e-10:
        return 0.0
    return golden_energy / total_energy


def _compute_volume_mod_fidelity(y, sr: int = SAMPLE_RATE) -> float:
    """
    Measure how much of the perceived modulation comes from volume changes
    vs. spectral/filter changes.

    ill.Gates 80/20: Volume modulation is more impactful than filter sweeps.
    Score > 0.5 means volume modulation dominates — the Dojo way.
    """
    _require_audio_deps()
    hop = 512
    # RMS envelope
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    # Spectral centroid (proxy for filter movement)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]

    if len(rms) < 4 or len(centroid) < 4:
        return 0.5

    # Variance of each — normalized
    rms_var = float(np.var(rms / (np.max(rms) + 1e-10)))
    cent_var = float(np.var(centroid / (np.max(centroid) + 1e-10)))

    total = rms_var + cent_var
    if total < 1e-10:
        return 0.5
    return rms_var / total


def _compute_transient_sharpness(y, sr: int = SAMPLE_RATE) -> float:
    """
    Measure transient attack quality via onset strength envelope.

    Sharp transients → high sharpness → punchy drums, crisp chops.
    """
    _require_audio_deps()
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if len(onset_env) < 2:
        return 0.0
    # Ratio of peak onset to mean — higher = sharper transients
    peak = float(np.max(onset_env))
    mean = float(np.mean(onset_env))
    if mean < 1e-10:
        return 0.0
    ratio = peak / mean
    # Normalize to 0-1 (empirical: ratios above 10 are very sharp)
    return min(ratio / 10.0, 1.0)


def _compute_resample_chaos_score(y, sr: int = SAMPLE_RATE) -> float:
    """
    Spectral complexity / chaos metric.

    High chaos → lots of spectral variation → resampling-heavy design.
    ill.Gates: "Mudpies = resample until unrecognizable, then resample again."
    """
    _require_audio_deps()
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    # Spectral flatness per frame (Wiener entropy)
    flatness = librosa.feature.spectral_flatness(S=S)[0]
    # Spectral flux (frame-to-frame change)
    flux = np.sqrt(np.mean(np.diff(S, axis=1) ** 2, axis=0))

    # Combine: mean flatness + normalized flux variance
    mean_flat = float(np.mean(flatness))
    flux_var = float(np.var(flux / (np.max(flux) + 1e-10)))

    return min((mean_flat + flux_var) / 1.0, 1.0)


def _compute_128s_compatibility(y, sr: int = SAMPLE_RATE) -> float:
    """
    How suitable is this audio for ill.Gates' 128s technique?

    128s = chop a sample into 128 equal slices and map to a Simpler rack.
    Best with: sustaining tones, moderate dynamics, clean transients.
    """
    _require_audio_deps()
    duration = len(y) / sr
    if duration < 0.5:
        return 0.0

    # Check if slicing into 128 parts gives usable slice length
    slice_dur = duration / 128
    # Sweet spot: 10ms-200ms per slice
    if 0.01 <= slice_dur <= 0.2:
        dur_score = 1.0
    elif slice_dur < 0.01:
        dur_score = slice_dur / 0.01
    else:
        dur_score = max(0.0, 1.0 - (slice_dur - 0.2) / 0.8)

    # Spectral consistency (low variance = easier to slice)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=256))
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
    cent_cv = float(np.std(centroid) / (np.mean(centroid) + 1e-10))
    consistency_score = max(0.0, 1.0 - cent_cv)

    return (dur_score * 0.4 + consistency_score * 0.6)


def extract_features(filepath: str,
                     stem_type: str = "unknown",
                     sr: int = SAMPLE_RATE) -> StemFeatures:
    """
    Extract full DUBFORGE feature set from an audio file.

    This is the core analysis function — calibrated to Producer Dojo
    philosophy and the DUBFORGE builder's parameter space.

    Args:
        filepath: Path to audio file (WAV, FLAC, MP3, etc.)
        stem_type: One of STEM_TYPES or "unknown"
        sr: Target sample rate

    Returns:
        StemFeatures with all scalar features populated.
    """
    _require_audio_deps()
    _log.info(f"Extracting features: {filepath} (stem: {stem_type})")

    y, loaded_sr = _load_audio(filepath, sr=sr)

    if len(y) < sr:  # less than 1 second
        _log.warning(f"Very short audio: {len(y)} samples")

    feats = StemFeatures(stem_type=stem_type, source_file=filepath)

    # --- BPM ---
    tempo_result = librosa.beat.beat_track(y=y, sr=sr)
    # librosa 0.10+ returns tempo as ndarray(shape=(1,)); use .flat[0] to handle
    # both 0-d and 1-d arrays regardless of numpy/librosa version
    _bpm_raw = tempo_result[0]
    feats.bpm = float(_bpm_raw.flat[0]) if hasattr(_bpm_raw, 'flat') else float(_bpm_raw)
    feats.half_time_groove = HALFTIME_BPM_MIN <= feats.bpm <= HALFTIME_BPM_MAX

    # --- Sub RMS ---
    # Bandpass around sub frequencies using STFT
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    sub_mask = freqs <= 80
    sub_energy = np.mean(S[sub_mask, :] ** 2)
    feats.sub_rms_db = float(10 * np.log10(max(sub_energy, 1e-10)))

    # --- Golden zone ---
    feats.golden_zone_match = _compute_golden_zone_match(y, sr)

    # --- Spectral centroid ---
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    feats.spectral_centroid_mean = float(np.mean(centroid))

    # --- Wobble rate ---
    feats.wobble_rate_hz = estimate_wobble_rate(y, sr)

    # --- Volume modulation fidelity ---
    feats.volume_mod_fidelity = _compute_volume_mod_fidelity(y, sr)

    # --- Modulation depth (overall envelope variance) ---
    rms_env = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    if len(rms_env) > 1 and np.max(rms_env) > 1e-10:
        feats.mod_depth = float(np.std(rms_env) / np.max(rms_env))
    else:
        feats.mod_depth = 0.0

    # --- Transient sharpness ---
    feats.transient_sharpness = _compute_transient_sharpness(y, sr)

    # --- Clipping headroom ---
    peak = float(np.max(np.abs(y)))
    feats.clipping_headroom_db = float(20 * np.log10(max(peak, 1e-10)))

    # --- Dynamic range ---
    rms_val = float(np.sqrt(np.mean(y ** 2)))
    peak_db = 20 * math.log10(max(peak, 1e-10))
    rms_db = 20 * math.log10(max(rms_val, 1e-10))
    feats.dynamic_range_db = peak_db - rms_db

    # --- Gain staging balance ---
    # How close is peak to the Dojo ceiling (-3 dBFS)?
    diff_from_ceiling = abs(peak_db - HARD_CLIP_CEILING_DB)
    feats.group_gain_staging_balance = max(0.0, 1.0 - diff_from_ceiling / 12.0)

    # --- Resample chaos score ---
    feats.resample_chaos_score = _compute_resample_chaos_score(y, sr)

    # --- 128s compatibility ---
    feats.simpler_128s_compatibility = _compute_128s_compatibility(y, sr)

    # --- Drop conversion potential ---
    # Energy ramp in latter half vs first half
    mid = len(y) // 2
    first_rms = float(np.sqrt(np.mean(y[:mid] ** 2)))
    second_rms = float(np.sqrt(np.mean(y[mid:] ** 2)))
    if first_rms > 1e-10:
        energy_ratio = second_rms / first_rms
        feats.drop_conversion_potential = min(energy_ratio / 2.0, 1.0)
    else:
        feats.drop_conversion_potential = 0.0

    _log.info(f"  BPM={feats.bpm:.1f} golden={feats.golden_zone_match:.3f} "
              f"wobble={feats.wobble_rate_hz:.2f}Hz chaos={feats.resample_chaos_score:.3f}")

    return feats


def extract_embedding(filepath: str, sr: int = SAMPLE_RATE) -> list[float]:
    """
    Extract a perceptual embedding vector using OpenL3 (if available).

    Falls back to zero-vector if OpenL3 not installed.
    """
    try:
        import openl3
        y, _ = _load_audio(filepath, sr=sr)
        emb, _ = openl3.get_audio_embedding(
            y, sr, embedding_size=EMBEDDING_DIM,
            content_type="music", input_repr="mel128",
        )
        # Average across time frames
        return [float(x) for x in np.mean(emb, axis=0)]
    except ImportError:
        _log.debug("OpenL3 not available — returning zero embedding")
        return [0.0] * EMBEDDING_DIM
    except Exception as e:
        _log.warning(f"Embedding extraction failed: {e}")
        return [0.0] * EMBEDDING_DIM


# ═══════════════════════════════════════════════════════════════════════════
# BANGER SCORE — composite taste evaluation
# ═══════════════════════════════════════════════════════════════════════════

def compute_banger_score(stems: dict[str, StemFeatures]) -> float:
    """
    Compute a 0-100 "banger score" from all stem features.

    Weighted formula calibrated to DUBFORGE dubstep philosophy:
    - Sub presence (golden zone)       = 25%
    - Dynamics / drop potential         = 20%
    - Modulation quality (80/20 rule)   = 20%
    - Transient punch                   = 15%
    - Chaos / complexity                = 10%
    - Gain staging                      = 10%
    """
    if not stems:
        return 0.0

    # Aggregate across stems
    all_feats = list(stems.values())

    def _avg(attr: str) -> float:
        vals = [getattr(f, attr, 0.0) for f in all_feats]
        return sum(vals) / len(vals) if vals else 0.0

    # Sub presence — only from sub/bass stems
    sub_stems = [f for f in all_feats if f.stem_type in ("sub", "bass")]
    golden = (sum(f.golden_zone_match for f in sub_stems) / len(sub_stems)
              if sub_stems else 0.0)

    score = (
        golden * 25.0
        + _avg("drop_conversion_potential") * 20.0
        + _avg("volume_mod_fidelity") * 20.0
        + _avg("transient_sharpness") * 15.0
        + _avg("resample_chaos_score") * 10.0
        + _avg("group_gain_staging_balance") * 10.0
    )
    return min(max(score, 0.0), 100.0)


# ═══════════════════════════════════════════════════════════════════════════
# PROTOTYPE BUILDING — average taste fingerprint per stem type
# ═══════════════════════════════════════════════════════════════════════════

def build_prototypes(analyses: list[TrackAnalysis],
                     thumbs_filter: Optional[str] = None) -> TasteProfile:
    """
    Build averaged prototype vectors per stem type from reference analyses.

    Args:
        analyses: List of analyzed reference tracks
        thumbs_filter: If "up", only use thumbs-up tracks. If None, use all.

    Returns:
        TasteProfile with one TastePrototype per stem type.
    """
    _require_audio_deps()

    profile = TasteProfile(track_count=len(analyses))

    # Filter by thumbs
    filtered = analyses
    if thumbs_filter == "up":
        filtered = [a for a in analyses if a.thumbs == "up"]
    elif thumbs_filter == "down":
        filtered = [a for a in analyses if a.thumbs == "down"]

    profile.thumbs_up_count = sum(1 for a in analyses if a.thumbs == "up")
    profile.thumbs_down_count = sum(1 for a in analyses if a.thumbs == "down")

    for stem_type in STEM_TYPES:
        vectors = []
        for analysis in filtered:
            if stem_type in analysis.stems:
                vec = analysis.stems[stem_type].hybrid_vector
                vectors.append(vec)

        if not vectors:
            continue

        # Pad to same length
        max_len = max(len(v) for v in vectors)
        padded = [v + [0.0] * (max_len - len(v)) for v in vectors]
        arr = np.array(padded, dtype=np.float64)

        proto = TastePrototype(
            stem_type=stem_type,
            mean_vector=[float(x) for x in np.mean(arr, axis=0)],
            std_vector=[float(x) for x in np.std(arr, axis=0)],
            sample_count=len(vectors),
        )
        profile.prototypes[stem_type] = proto

    return profile


def score_against_prototype(features: StemFeatures,
                            prototype: TastePrototype) -> float:
    """
    Score a stem against a taste prototype (0-100 similarity).

    Uses cosine similarity on hybrid vectors.
    """
    _require_audio_deps()
    vec = features.hybrid_vector
    proto = prototype.mean_vector

    # Align lengths
    min_len = min(len(vec), len(proto))
    if min_len == 0:
        return 0.0

    a = np.array(vec[:min_len], dtype=np.float64)
    b = np.array(proto[:min_len], dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0

    cosine_sim = float(np.dot(a, b) / (norm_a * norm_b))
    # Map from [-1, 1] to [0, 100]
    return max(0.0, min(100.0, (cosine_sim + 1.0) * 50.0))


# ═══════════════════════════════════════════════════════════════════════════
# FULL TRACK ANALYSIS — orchestrates stem separation + per-stem extraction
# ═══════════════════════════════════════════════════════════════════════════

def analyze_track(audio_path: str,
                  stem_dir: Optional[str] = None,
                  track_name: str = "",
                  source_url: str = "",
                  extract_embeddings: bool = False) -> TrackAnalysis:
    """
    Analyze a full track — expects either pre-separated stems or a stem directory.

    If stem_dir is provided, looks for files matching stem type names.
    Otherwise, analyzes the full mix as a single "mix" stem.

    Args:
        audio_path: Path to full mix audio (used if stems not found)
        stem_dir: Directory containing separated stems (sub.wav, bass.wav, etc.)
        track_name: Display name for the track
        source_url: Source URL (SoundCloud, etc.)
        extract_embeddings: Whether to compute OpenL3 embeddings (slow)

    Returns:
        TrackAnalysis with features for each found stem.
    """
    _require_audio_deps()

    if not track_name:
        track_name = Path(audio_path).stem

    analysis = TrackAnalysis(
        track_name=track_name,
        source_url=source_url,
    )

    stems_found = {}

    if stem_dir and os.path.isdir(stem_dir):
        # Look for separated stems
        stem_dir_path = Path(stem_dir)
        for stem_type in STEM_TYPES:
            # Try various naming conventions
            candidates = [
                stem_dir_path / f"{stem_type}.wav",
                stem_dir_path / f"{stem_type}.flac",
                stem_dir_path / f"{stem_type}.mp3",
            ]
            # Also try demucs naming: vocals.wav, drums.wav, bass.wav, other.wav
            demucs_map = {
                "sub": "bass",     # demucs "bass" maps to our "sub"
                "bass": "bass",    # both can use demucs bass
                "drums": "drums",
                "mids_growls": "other",
                "atmos_fx": "vocals",  # atmospheric content often in vocals stem
            }
            if stem_type in demucs_map:
                demucs_name = demucs_map[stem_type]
                candidates.append(stem_dir_path / f"{demucs_name}.wav")
                candidates.append(stem_dir_path / f"{demucs_name}.flac")

            for candidate in candidates:
                if candidate.exists():
                    stems_found[stem_type] = str(candidate)
                    break

    if not stems_found:
        # Analyze full mix as single stem
        stems_found["mix"] = audio_path
        _log.info(f"No separated stems found — analyzing full mix")

    # Extract features for each stem
    for stem_type, stem_path in stems_found.items():
        feats = extract_features(stem_path, stem_type=stem_type)
        if extract_embeddings:
            feats.embedding = extract_embedding(stem_path)
        analysis.stems[stem_type] = feats

    # Overall metrics
    all_bpm = [f.bpm for f in analysis.stems.values() if f.bpm > 0]
    analysis.overall_bpm = sum(all_bpm) / len(all_bpm) if all_bpm else 0.0

    all_energy = [f.golden_zone_match + f.mod_depth + f.transient_sharpness
                  for f in analysis.stems.values()]
    analysis.overall_energy = sum(all_energy) / len(all_energy) if all_energy else 0.0

    analysis.banger_score = compute_banger_score(analysis.stems)

    _log.info(f"Track analysis complete: {track_name} — "
              f"banger_score={analysis.banger_score:.1f}")

    return analysis


# ═══════════════════════════════════════════════════════════════════════════
# M4L DEVICE SUGGESTIONS — based on stem features
# ═══════════════════════════════════════════════════════════════════════════

M4L_RECOMMENDATIONS: dict[str, dict] = {
    "LFO Tool": {
        "trigger": lambda f: f.wobble_rate_hz > 1.0,
        "reason": "Wobble detected — route LFO Tool to volume/filter for live control",
        "routing": "LFO → Volume (80%) + Filter Cutoff (20%)",
    },
    "Envelope Follower": {
        "trigger": lambda f: f.transient_sharpness > 0.5,
        "reason": "Strong transients — use Envelope Follower for sidechain-style pumping",
        "routing": "Env Follow → Compressor Threshold on adjacent bus",
    },
    "Shaper": {
        "trigger": lambda f: f.mod_depth > 0.4,
        "reason": "High modulation depth — Shaper adds waveshaping for extra harmonics",
        "routing": "Shaper after distortion, before filter",
    },
    "Drift": {
        "trigger": lambda f: f.resample_chaos_score > 0.3,
        "reason": "Chaotic spectrum — Drift adds organic modulation instability",
        "routing": "Drift → Pitch + Filter Cutoff",
    },
    "Expression Control": {
        "trigger": lambda f: f.volume_mod_fidelity > 0.6,
        "reason": "Volume-centric modulation — Expression Control for MIDI mapping",
        "routing": "CC1 (Mod Wheel) → Rack Macro 1 (Volume Mod Depth)",
    },
    "Convolution Reverb Pro": {
        "trigger": lambda f: f.stem_type == "atmos_fx",
        "reason": "Atmospheric stem — Convolution Reverb Pro for spatial depth",
        "routing": "Send bus, 100% wet, decay matched to arrangement section length",
    },
}


def generate_m4l_suggestions(features: StemFeatures) -> list[dict]:
    """Generate Max for Live device suggestions based on stem features."""
    suggestions = []
    for device_name, config in M4L_RECOMMENDATIONS.items():
        if config["trigger"](features):
            suggestions.append({
                "device": device_name,
                "stem_type": features.stem_type,
                "reason": config["reason"],
                "routing": config["routing"],
            })
    return suggestions


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT — JSON database output
# ═══════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "taste"


def export_analysis(analysis: TrackAnalysis, output_dir: Optional[Path] = None) -> Path:
    """Export a single track analysis to JSON."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in analysis.track_name)
    filepath = out / f"{safe_name}_analysis.json"
    filepath.write_text(json.dumps(analysis.to_dict(), indent=2), encoding="utf-8")
    _log.info(f"Exported analysis: {filepath}")
    return filepath


def export_prototypes(profile: TasteProfile, output_dir: Optional[Path] = None) -> Path:
    """Export taste prototypes to JSON."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    filepath = out / "prototypes.json"
    filepath.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    _log.info(f"Exported prototypes: {filepath}")
    return filepath


def export_taste_report(analyses: list[TrackAnalysis],
                        profile: TasteProfile,
                        output_dir: Optional[Path] = None) -> Path:
    """Export a human-readable Markdown taste report."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    lines = [
        "# DUBFORGE — Taste Profile Report\n",
        f"**Tracks analyzed:** {profile.track_count}",
        f"**Thumbs up:** {profile.thumbs_up_count}  |  "
        f"**Thumbs down:** {profile.thumbs_down_count}\n",
        "## Prototype Vectors\n",
    ]

    for stem_type, proto in profile.prototypes.items():
        lines.append(f"### {stem_type} (n={proto.sample_count})")
        lines.append(f"- Vector dim: {proto.vector_dim}")
        # Show first 15 (scalar) features with names
        scalar_names = [
            "bpm", "half_time", "sub_rms_db", "golden_zone", "centroid",
            "wobble_hz", "vol_mod_fidelity", "mod_depth", "transient_sharp",
            "clip_headroom_db", "dyn_range_db", "gain_staging", "chaos",
            "128s_compat", "drop_potential",
        ]
        for i, name in enumerate(scalar_names):
            if i < len(proto.mean_vector):
                lines.append(f"  - {name}: **{proto.mean_vector[i]:.3f}** "
                             f"(±{proto.std_vector[i]:.3f})")
        lines.append("")

    lines.append("## Track Rankings\n")
    ranked = sorted(analyses, key=lambda a: a.banger_score, reverse=True)
    for i, a in enumerate(ranked):
        thumb = {"up": "👍", "down": "👎"}.get(a.thumbs, "—")
        lines.append(f"{i+1}. **{a.track_name}** — "
                     f"Score: {a.banger_score:.1f} | BPM: {a.overall_bpm:.0f} | {thumb}")

    filepath = out / "taste_report.md"
    filepath.write_text("\n".join(lines), encoding="utf-8")
    _log.info(f"Exported taste report: {filepath}")
    return filepath


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST — for engine __init__ exports
# ═══════════════════════════════════════════════════════════════════════════

def write_taste_manifest(output_dir: Optional[Path] = None) -> Path:
    """Write module manifest for discovery."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "module": "dubstep_taste_analyzer",
        "version": "1.0.0",
        "stem_types": list(STEM_TYPES),
        "scalar_features": N_SCALAR_FEATURES,
        "embedding_dim": EMBEDDING_DIM,
        "requires": ["numpy", "librosa", "soundfile"],
        "optional": ["openl3"],
    }
    filepath = out / "taste_manifest.json"
    filepath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return filepath
