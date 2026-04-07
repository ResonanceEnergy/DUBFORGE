"""
DUBFORGE — Deep Reference Analyzer  (DNA-level)

Extracts a complete audio DNA fingerprint from any WAV:
spectral DNA (MFCCs, flux, tilt, flatness, rolloff, centroid, band energies),
rhythm DNA (BPM, stability, swing, onset regularity),
harmonic DNA (key detection via Krumhansl-Kessler, chroma entropy, dissonance),
loudness DNA (LUFS estimate, LRA, limiting artifacts, crest factor),
arrangement DNA (section detection, energy contrast, drop count),
stereo DNA (mid/side, freq-dependent width, mono compat),
bass DNA (sub weight, fundamental, harmonics, wobble/modulation rate),
production DNA (transient sharpness, reverb estimate, sidechain depth,
               compression ratio, distortion amount).

Quality scoring against genre benchmarks (dubstep / riddim).
Backward-compatible with Session 166 API:
  TrackProfile, profile_from_signal, compare_to_reference,
  list_references, comparison_text
"""

import math
import wave
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.fft import rfft, rfftfreq


SAMPLE_RATE = 48000

# ═══════════════════════════════════════════════════════════════════════════
# DNA DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class SpectralDNA:
    """Full spectral fingerprint."""
    # 6-band energy (sum ~1.0)
    sub: float = 0.0         # 20-60 Hz
    bass: float = 0.0        # 60-250 Hz
    low_mid: float = 0.0     # 250-500 Hz
    mid: float = 0.0         # 500-2000 Hz
    high_mid: float = 0.0    # 2000-6000 Hz
    high: float = 0.0        # 6000-20000 Hz
    # Spectral shape
    centroid_hz: float = 0.0
    rolloff_hz: float = 0.0
    flatness: float = 0.0       # 0 = tonal, 1 = noise
    flux_mean: float = 0.0      # avg frame-to-frame change
    flux_std: float = 0.0       # variation in flux
    tilt_db_per_oct: float = 0.0  # spectral slope
    # MFCCs (13 coefficients, mean across frames)
    mfcc: list[float] = field(default_factory=list)
    # ── expanded (session 168) ──
    bandwidth_hz: float = 0.0       # spectral bandwidth (spread around centroid)
    contrast: list[float] = field(default_factory=list)  # 6-band peak-valley dB
    zero_crossing_rate: float = 0.0  # temporal ZCR
    spectral_complexity: int = 0     # number of spectral peaks
    high_freq_content: float = 0.0   # HFC energy-weighted high bins
    spectral_spread: float = 0.0     # variance around centroid (Hz²)
    spectral_skewness: float = 0.0   # asymmetry of spectrum
    spectral_kurtosis: float = 0.0   # peakedness of spectrum


@dataclass
class RhythmDNA:
    """Rhythm and tempo fingerprint."""
    bpm: float = 0.0
    bpm_confidence: float = 0.0   # autocorrelation peak strength
    beat_stability: float = 0.0   # variance in inter-beat intervals
    onset_rate: float = 0.0       # onsets per second
    onset_regularity: float = 0.0  # how evenly spaced onsets are (0-1)
    swing_ratio: float = 0.5      # 0.5 = straight, >0.5 = swing
    groove_strength: float = 0.0   # amplitude of periodic pattern


@dataclass
class HarmonicDNA:
    """Key, harmony, and tonality fingerprint."""
    key: str = ""             # e.g. "C minor"
    key_confidence: float = 0.0
    chroma_entropy: float = 0.0   # 0 = single note, high = many notes
    dissonance: float = 0.0       # avg rough-interval ratio
    bass_note_histogram: list[float] = field(default_factory=list)  # 12 bins
    chroma_mean: list[float] = field(default_factory=list)  # 12 bins


@dataclass
class LoudnessDNA:
    """Loudness and dynamics fingerprint."""
    peak_db: float = -96.0
    rms_db: float = -96.0
    lufs_estimate: float = -96.0
    crest_factor_db: float = 0.0
    dynamic_range_db: float = 0.0   # p95-p5 of block RMS
    loudness_range_db: float = 0.0  # LRA (short-term var)
    limiting_artifacts: float = 0.0  # consecutive clipped samples %
    a_weighted_rms_db: float = -96.0


@dataclass
class ArrangementDNA:
    """Song structure fingerprint."""
    duration_s: float = 0.0
    n_sections: int = 0
    section_labels: list[str] = field(default_factory=list)
    section_boundaries_pct: list[float] = field(default_factory=list)
    energy_curve: list[float] = field(default_factory=list)  # 20 points
    drop_count: int = 0
    intro_drop_contrast_db: float = 0.0
    loudest_section_idx: int = 0
    quietest_section_idx: int = 0
    # ── expanded (session 168) ──
    tension_curve: list[float] = field(default_factory=list)  # 20-pt tension
    transition_sharpness: float = 0.0   # avg dB change at boundaries
    energy_arc_type: str = ""           # build-drop / plateau / chaotic
    buildup_effectiveness: float = 0.0  # build→drop contrast ratio
    section_diversity: float = 0.0      # entropy of section labels
    breakdown_depth_db: float = 0.0     # avg dip in breakdowns


@dataclass
class StereoDNA:
    """Stereo image fingerprint."""
    width: float = 0.0           # side/total energy ratio
    correlation: float = 1.0     # Pearson L↔R
    mono_compat: float = 1.0     # mid power / total (1=safe)
    width_low: float = 0.0       # < 250 Hz
    width_mid: float = 0.0       # 250-4000 Hz
    width_high: float = 0.0      # > 4000 Hz


@dataclass
class BassDNA:
    """Sub and bass fingerprint."""
    sub_weight: float = 0.0      # 20-60 Hz fraction of total
    bass_weight: float = 0.0     # 60-250 Hz fraction
    fundamental_hz: float = 0.0  # dominant sub frequency
    harmonic_ratio: float = 0.0  # harmonic / fundamental energy
    wobble_rate_hz: float = 0.0  # detected modulation frequency
    wobble_depth: float = 0.0    # modulation amount (0-1)
    sidechain_pump_count: int = 0


@dataclass
class ProductionDNA:
    """Production technique fingerprint."""
    transient_sharpness: float = 0.0  # attack rise time (0=soft, 1=sharp)
    reverb_amount: float = 0.0        # estimated wet ratio
    sidechain_depth_db: float = 0.0   # avg pump dip
    compression_ratio: float = 1.0    # estimated ratio
    distortion_amount: float = 0.0    # THD estimate (0-1)
    noise_floor_db: float = -96.0     # quietest block RMS
    presence_peak_hz: float = 0.0     # spectral peak in 2-6 kHz


# ═══════════════════════════════════════════════════════════════════════════
# NEW DNA CATEGORIES (Session 168)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class StyleDNA:
    """Musical style and character fingerprint."""
    aggression: float = 0.0        # 0=ambient, 1=brutal
    darkness: float = 0.0          # 0=bright/happy, 1=dark
    energy_level: float = 0.0      # 0=chill, 1=high energy
    danceability: float = 0.0      # 0=ambient, 1=highly danceable
    density: float = 0.0           # 0=sparse, 1=wall-of-sound
    brightness: float = 0.0        # 0=dark, 1=bright
    bass_dominance: float = 0.0    # how bass-heavy the mix is
    rhythm_complexity: float = 0.0  # swing + onset irregularity
    genre_tags: list[str] = field(default_factory=list)


@dataclass
class SoundDesignDNA:
    """Sound design characteristics."""
    attack_sharpness: float = 0.0    # 0=soft pad, 1=instant transient
    decay_character: float = 0.0     # sustain-to-decay ratio
    inharmonicity: float = 0.0       # deviation from harmonic series
    odd_even_ratio: float = 0.0      # odd vs even harmonic energy
    modulation_depth: float = 0.0    # AM/FM/filter modulation depth
    modulation_rate_hz: float = 0.0  # dominant modulation frequency
    texture_density: float = 0.0     # spectral complexity / layers
    formant_presence: float = 0.0    # vocal-like formant energy
    noise_content: float = 0.0       # noise vs tonal ratio
    spectral_movement: float = 0.0   # how much spectrum moves over time


@dataclass
class MixingDNA:
    """Mix engineering quality metrics."""
    headroom_db: float = 0.0            # peak headroom below 0 dBFS
    frequency_balance_score: float = 0.0  # spectral evenness (1=ideal)
    mud_ratio: float = 0.0              # problematic 200-500 Hz buildup
    harshness_ratio: float = 0.0        # problematic 2-5 kHz buildup
    air_ratio: float = 0.0              # useful 8-16 kHz presence
    phase_coherence: float = 0.0        # overall L/R phase correlation
    phase_low: float = 0.0              # phase coherence <250 Hz
    phase_mid: float = 0.0              # phase coherence 250-4000 Hz
    phase_high: float = 0.0             # phase coherence >4000 Hz
    dynamic_range_low: float = 0.0      # DR in bass band (dB)
    dynamic_range_mid: float = 0.0      # DR in mid band (dB)
    dynamic_range_high: float = 0.0     # DR in high band (dB)
    separation_score: float = 0.0       # frequency separation quality
    eq_curve: list[float] = field(default_factory=list)  # 10-band EQ (dB)


@dataclass
class MasteringDNA:
    """Mastering quality assessment."""
    true_peak_db: float = -96.0          # true peak (4x oversampled)
    inter_sample_peak_db: float = -96.0  # inter-sample peak estimate
    clipping_samples: int = 0            # samples at digital ceiling
    saturation_amount: float = 0.0       # detected saturation level
    loudness_consistency: float = 0.0    # short-term LUFS variance
    limiting_transparency: float = 0.0   # 1=transparent, 0=crushed
    stereo_fold_down_loss_db: float = 0.0  # energy loss mono-summed
    false_stereo: bool = False           # detected fake/Haas stereo
    dynamic_complexity: float = 0.0      # complexity of loudness changes
    streaming_loudness_penalty: float = 0.0  # dB penalty at -14 LUFS
    dc_offset: float = 0.0              # DC offset amount
    noise_floor_db: float = -96.0        # mastering noise floor


@dataclass
class QualityScore:
    """How "good" a track is vs genre benchmark."""
    overall: float = 0.0         # 0-100
    spectral_score: float = 0.0
    bass_score: float = 0.0
    loudness_score: float = 0.0
    arrangement_score: float = 0.0
    dynamics_score: float = 0.0
    stereo_score: float = 0.0
    production_score: float = 0.0
    style_score: float = 0.0
    sound_design_score: float = 0.0
    mixing_score: float = 0.0
    mastering_score: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ReferenceAnalysis:
    """Complete DNA analysis of a track."""
    filename: str = ""
    path: str = ""
    sample_rate: int = 0
    channels: int = 0
    bit_depth: int = 0
    spectral: SpectralDNA = field(default_factory=SpectralDNA)
    rhythm: RhythmDNA = field(default_factory=RhythmDNA)
    harmonic: HarmonicDNA = field(default_factory=HarmonicDNA)
    loudness: LoudnessDNA = field(default_factory=LoudnessDNA)
    arrangement: ArrangementDNA = field(default_factory=ArrangementDNA)
    stereo: StereoDNA = field(default_factory=StereoDNA)
    bass: BassDNA = field(default_factory=BassDNA)
    production: ProductionDNA = field(default_factory=ProductionDNA)
    style: StyleDNA = field(default_factory=StyleDNA)
    sound_design: SoundDesignDNA = field(default_factory=SoundDesignDNA)
    mixing: MixingDNA = field(default_factory=MixingDNA)
    mastering: MasteringDNA = field(default_factory=MasteringDNA)
    quality: QualityScore = field(default_factory=QualityScore)

    def to_dict(self) -> dict:
        return _dc_to_dict(self)


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPAT (Session 166 API)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class TrackProfile:
    """Spectral/dynamic profile (backwards compatible)."""
    name: str = ""
    rms_db: float = -14.0
    peak_db: float = -1.0
    crest_factor_db: float = 13.0
    sub_energy: float = 0.0
    bass_energy: float = 0.0
    mid_energy: float = 0.0
    high_energy: float = 0.0
    stereo_width: float = 0.5
    dynamic_range_db: float = 12.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rms_db": round(self.rms_db, 1),
            "peak_db": round(self.peak_db, 1),
            "crest_factor_db": round(self.crest_factor_db, 1),
            "sub_energy": round(self.sub_energy, 3),
            "bass_energy": round(self.bass_energy, 3),
            "mid_energy": round(self.mid_energy, 3),
            "high_energy": round(self.high_energy, 3),
            "stereo_width": round(self.stereo_width, 2),
            "dynamic_range_db": round(self.dynamic_range_db, 1),
        }


REFERENCE_PROFILES: dict[str, TrackProfile] = {
    "subtronics": TrackProfile(
        "Subtronics Reference", -8.0, -0.5, 7.5,
        0.75, 0.85, 0.6, 0.35, 0.4, 8.0,
    ),
    "excision": TrackProfile(
        "Excision Reference", -7.0, -0.3, 6.7,
        0.8, 0.9, 0.55, 0.3, 0.35, 6.0,
    ),
    "skrillex": TrackProfile(
        "Skrillex Reference", -8.5, -0.5, 8.0,
        0.6, 0.8, 0.75, 0.5, 0.5, 10.0,
    ),
    "virtual_riot": TrackProfile(
        "Virtual Riot Reference", -8.0, -0.5, 7.5,
        0.7, 0.85, 0.7, 0.45, 0.5, 9.0,
    ),
    "noisia": TrackProfile(
        "Noisia Reference", -9.0, -0.8, 8.2,
        0.65, 0.75, 0.8, 0.5, 0.6, 11.0,
    ),
    "dubforge_phi": TrackProfile(
        "DUBFORGE PHI Reference", -8.0, -0.5, 7.5,
        0.7, 0.8, 0.65, 0.4, 0.5, 1.618 * 6,
    ),
}


@dataclass
class ComparisonPoint:
    """A single comparison metric."""
    metric: str
    your_value: float
    ref_value: float
    diff: float
    severity: str   # ok, caution, problem
    suggestion: str


@dataclass
class ReferenceComparison:
    """Full comparison result."""
    reference_name: str
    your_profile: TrackProfile
    ref_profile: TrackProfile
    points: list[ComparisonPoint] = field(default_factory=list)
    overall_match: float = 0.0   # 0-100 %

    def to_dict(self) -> dict:
        return {
            "reference": self.reference_name,
            "overall_match": round(self.overall_match, 1),
            "your_profile": self.your_profile.to_dict(),
            "ref_profile": self.ref_profile.to_dict(),
            "points": [
                {
                    "metric": p.metric,
                    "your_value": round(p.your_value, 2),
                    "ref_value": round(p.ref_value, 2),
                    "diff": round(p.diff, 2),
                    "severity": p.severity,
                    "suggestion": p.suggestion,
                }
                for p in self.points
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════
# GENRE BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════

DUBSTEP_BENCHMARK: dict[str, Any] = {
    "bpm_range": (140, 155),
    "lufs_range": (-10.0, -7.0),
    "peak_db_max": -0.3,
    "spectral_balance": {
        "sub": (0.15, 0.40), "bass": (0.15, 0.35),
        "low_mid": (0.08, 0.20), "mid": (0.10, 0.25),
        "high_mid": (0.05, 0.15), "high": (0.02, 0.10),
    },
    "stereo_width": (0.15, 0.50),
    "dynamic_range_db": (4.0, 14.0),
    "intro_drop_contrast_db": (4.0, 20.0),
    "crest_factor_db": (5.0, 12.0),
}

RIDDIM_BENCHMARK: dict[str, Any] = {
    "bpm_range": (140, 155),
    "lufs_range": (-9.0, -6.0),
    "peak_db_max": -0.2,
    "spectral_balance": {
        "sub": (0.20, 0.50), "bass": (0.15, 0.35),
        "low_mid": (0.05, 0.15), "mid": (0.08, 0.20),
        "high_mid": (0.03, 0.12), "high": (0.01, 0.08),
    },
    "stereo_width": (0.10, 0.40),
    "dynamic_range_db": (3.0, 10.0),
    "intro_drop_contrast_db": (5.0, 25.0),
    "crest_factor_db": (4.0, 10.0),
}

GENRE_BENCHMARKS: dict[str, dict[str, Any]] = {
    "dubstep": DUBSTEP_BENCHMARK,
    "riddim": RIDDIM_BENCHMARK,
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _dc_to_dict(obj: Any) -> Any:
    """Recursively convert dataclass to dict with rounding."""
    if hasattr(obj, "__dataclass_fields__"):
        result: dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            result[k] = _dc_to_dict(getattr(obj, k))
        return result
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, list):
        return [_dc_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _dc_to_dict(v) for k, v in obj.items()}
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


def _load_wav(path: str) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Load WAV → (left, right, sample_rate, bit_depth).  16/24/32-bit."""
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
    return left, right, sr, sw * 8


# ═══════════════════════════════════════════════════════════════════════════
# SPECTRAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

_MEL_FILTER_CACHE: dict[tuple[int, int, int], np.ndarray] = {}


def _hz_to_mel(hz: float) -> float:
    return 2595.0 * math.log10(1.0 + hz / 700.0)


def _mel_to_hz(mel: float) -> float:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _mel_filterbank(sr: int, fft_size: int,
                    n_mels: int = 40) -> np.ndarray:
    """Build a mel filterbank matrix [n_mels x (fft_size//2+1)]."""
    key = (sr, fft_size, n_mels)
    if key in _MEL_FILTER_CACHE:
        return _MEL_FILTER_CACHE[key]

    n_fft = fft_size // 2 + 1
    low_mel = _hz_to_mel(20.0)
    high_mel = _hz_to_mel(sr / 2.0)
    mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_points = np.array([_mel_to_hz(m) for m in mel_points])
    bin_points = np.round(hz_points * fft_size / sr).astype(int)
    bin_points = np.clip(bin_points, 0, n_fft - 1)

    fb = np.zeros((n_mels, n_fft))
    for i in range(n_mels):
        left = bin_points[i]
        center = bin_points[i + 1]
        right = bin_points[i + 2]
        if center > left:
            fb[i, left:center] = np.linspace(0, 1, center - left,
                                             endpoint=False)
        if right > center:
            fb[i, center:right] = np.linspace(1, 0, right - center,
                                              endpoint=False)
    _MEL_FILTER_CACHE[key] = fb
    return fb


def _compute_mfcc(mono: np.ndarray, sr: int, fft_size: int = 2048,
                  hop: int = 512, n_mfcc: int = 13,
                  n_mels: int = 40) -> list[float]:
    """Compute mean MFCCs via mel filterbank + DCT."""
    n = len(mono)
    if n < fft_size:
        return [0.0] * n_mfcc

    window = np.hanning(fft_size)
    mel_fb = _mel_filterbank(sr, fft_size, n_mels)
    n_frames = max(1, (n - fft_size) // hop)
    n_frames = min(n_frames, 500)  # cap for speed

    mel_sum = np.zeros(n_mels)
    for i in range(n_frames):
        start = i * hop
        frame = mono[start:start + fft_size]
        if len(frame) < fft_size:
            break
        spectrum = np.abs(rfft(frame * window)) ** 2
        mel_energies = mel_fb @ spectrum
        mel_energies = np.maximum(mel_energies, 1e-10)
        mel_sum += np.log(mel_energies)

    mel_avg = mel_sum / max(n_frames, 1)

    # Type-II DCT (manual, no scipy dependency)
    mfcc = np.zeros(n_mfcc)
    for k in range(n_mfcc):
        for j in range(n_mels):
            mfcc[k] += mel_avg[j] * math.cos(
                math.pi * k * (j + 0.5) / n_mels
            )
    return [float(c) for c in mfcc]


def _analyze_spectral(mono: np.ndarray, sr: int,
                      fft_size: int = 4096) -> SpectralDNA:
    """Full spectral DNA extraction."""
    n = len(mono)
    if n < fft_size:
        return SpectralDNA()

    window = np.hanning(fft_size)
    hop = fft_size // 2
    n_frames = min(64, max(1, (n - fft_size) // hop))
    freqs = rfftfreq(fft_size, 1.0 / sr)

    bands = {"sub": 0.0, "bass": 0.0, "low_mid": 0.0,
             "mid": 0.0, "high_mid": 0.0, "high": 0.0}
    centroid_sum = 0.0
    total_mag_sum = 0.0
    prev_spec = np.zeros(len(freqs))
    flux_vals: list[float] = []
    flatness_sum = 0.0
    # ── expanded accumulators ──
    bandwidth_sum = 0.0
    spread_sum = 0.0
    skew_sum = 0.0
    kurt_sum = 0.0
    hfc_sum = 0.0
    complexity_sum = 0
    # 6 contrast bands: sub/bass/low_mid/mid/high_mid/high
    contrast_bands = [(20, 60), (60, 250), (250, 500),
                      (500, 2000), (2000, 6000), (6000, 20000)]
    contrast_peak_sum = [0.0] * 6
    contrast_valley_sum = [0.0] * 6
    spectral_movement_sum = 0.0

    for i in range(n_frames):
        start = i * hop
        frame = mono[start:start + fft_size]
        if len(frame) < fft_size:
            break
        spectrum = np.abs(rfft(frame * window))
        power = spectrum ** 2

        bands["sub"] += float(np.sum(power[(freqs >= 20) & (freqs < 60)]))
        bands["bass"] += float(np.sum(power[(freqs >= 60) & (freqs < 250)]))
        bands["low_mid"] += float(
            np.sum(power[(freqs >= 250) & (freqs < 500)]))
        bands["mid"] += float(
            np.sum(power[(freqs >= 500) & (freqs < 2000)]))
        bands["high_mid"] += float(
            np.sum(power[(freqs >= 2000) & (freqs < 6000)]))
        bands["high"] += float(
            np.sum(power[(freqs >= 6000) & (freqs <= 20000)]))

        s_total = float(np.sum(spectrum))
        if s_total > 1e-10:
            c = float(np.sum(freqs * spectrum)) / s_total
            centroid_sum += c
            total_mag_sum += 1.0

            # Spectral bandwidth (std dev around centroid)
            bw = float(np.sqrt(
                np.sum(spectrum * (freqs - c) ** 2) / s_total))
            bandwidth_sum += bw

            # Higher moments: spread, skewness, kurtosis
            var = float(np.sum(spectrum * (freqs - c) ** 2) / s_total)
            spread_sum += var
            std = math.sqrt(var) if var > 1e-10 else 1e-10
            m3 = float(np.sum(spectrum * (freqs - c) ** 3) / s_total)
            skew_sum += m3 / (std ** 3)
            m4 = float(np.sum(spectrum * (freqs - c) ** 4) / s_total)
            kurt_sum += m4 / (std ** 4)

            # HFC: energy-weighted high frequency content
            hfc_sum += float(np.sum(freqs * spectrum)) / s_total

        flux = float(np.sum(np.maximum(0, spectrum - prev_spec)))
        flux_vals.append(flux)

        # Spectral movement: correlation with previous frame
        if i > 0 and float(np.std(spectrum)) > 1e-10:
            corr = float(np.corrcoef(spectrum, prev_spec)[0, 1])
            spectral_movement_sum += 1.0 - max(0.0, corr)

        prev_spec = spectrum.copy()

        geo_mean = float(np.exp(np.mean(np.log(spectrum + 1e-10))))
        arith_mean = float(np.mean(spectrum))
        if arith_mean > 1e-10:
            flatness_sum += geo_mean / arith_mean

        # Spectral complexity: count peaks in spectrum
        for j in range(1, len(spectrum) - 1):
            if (spectrum[j] > spectrum[j - 1]
                    and spectrum[j] > spectrum[j + 1]
                    and spectrum[j] > arith_mean * 2):
                complexity_sum += 1

        # Spectral contrast per band: peak vs valley
        for bi, (lo, hi) in enumerate(contrast_bands):
            mask = (freqs >= lo) & (freqs < hi)
            band_spec = spectrum[mask]
            if len(band_spec) > 2:
                sorted_b = np.sort(band_spec)
                top_n = max(1, len(sorted_b) // 10)
                contrast_peak_sum[bi] += float(np.mean(sorted_b[-top_n:]))
                contrast_valley_sum[bi] += float(np.mean(sorted_b[:top_n]))

    # Normalize bands
    total_band = sum(bands.values())
    if total_band > 0:
        for k in bands:
            bands[k] /= total_band

    # Spectral rolloff (from last frame)
    cumul = np.cumsum(prev_spec ** 2)
    total_p = cumul[-1] if len(cumul) > 0 else 0.0
    rolloff = 0.0
    if total_p > 1e-10:
        idx = int(np.searchsorted(cumul, 0.95 * total_p))
        rolloff = float(freqs[min(idx, len(freqs) - 1)])

    # Spectral tilt (dB/octave via linear regression on log-freq)
    tilt = 0.0
    if len(prev_spec) > 10:
        pos = freqs > 20
        log_f = np.log2(freqs[pos] + 1e-10)
        log_p = 10.0 * np.log10(prev_spec[pos] ** 2 + 1e-10)
        if len(log_f) > 2:
            coeffs = np.polyfit(log_f, log_p, 1)
            tilt = float(coeffs[0])

    # Zero crossing rate (time domain)
    zcr = 0.0
    if len(mono) > 1:
        signs = np.sign(mono)
        zcr = float(np.sum(np.abs(np.diff(signs)) > 0)) / len(mono)

    # Spectral contrast: dB difference between peaks and valleys
    nf = max(n_frames, 1)
    contrast_db: list[float] = []
    for bi in range(6):
        pk = contrast_peak_sum[bi] / nf
        vl = contrast_valley_sum[bi] / nf
        if vl > 1e-10:
            contrast_db.append(round(_db(pk) - _db(vl), 2))
        else:
            contrast_db.append(0.0)

    dna = SpectralDNA(
        sub=bands["sub"], bass=bands["bass"],
        low_mid=bands["low_mid"], mid=bands["mid"],
        high_mid=bands["high_mid"], high=bands["high"],
        centroid_hz=(centroid_sum / total_mag_sum
                     if total_mag_sum > 0 else 0.0),
        rolloff_hz=rolloff,
        flatness=flatness_sum / max(n_frames, 1),
        flux_mean=(float(np.mean(flux_vals)) if flux_vals else 0.0),
        flux_std=(float(np.std(flux_vals)) if flux_vals else 0.0),
        tilt_db_per_oct=tilt,
        mfcc=_compute_mfcc(mono, sr),
        bandwidth_hz=bandwidth_sum / max(total_mag_sum, 1),
        contrast=contrast_db,
        zero_crossing_rate=zcr,
        spectral_complexity=complexity_sum // max(n_frames, 1),
        high_freq_content=hfc_sum / max(total_mag_sum, 1),
        spectral_spread=spread_sum / max(total_mag_sum, 1),
        spectral_skewness=skew_sum / max(total_mag_sum, 1),
        spectral_kurtosis=kurt_sum / max(total_mag_sum, 1),
    )
    return dna


# ═══════════════════════════════════════════════════════════════════════════
# RHYTHM ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_rhythm(mono: np.ndarray, sr: int) -> RhythmDNA:
    """BPM, stability, swing, onset regularity."""
    # Use center 60s max
    max_s = int(sr * 60)
    if len(mono) > max_s:
        start = (len(mono) - max_s) // 2
        mono = mono[start:start + max_s]

    ds_factor = max(1, sr // 4000)
    ds = mono[::ds_factor]
    ds_sr = sr / ds_factor

    frame_size = int(ds_sr * 0.02)
    hop = frame_size // 2
    n_frames = (len(ds) - frame_size) // hop
    if n_frames < 10:
        return RhythmDNA()

    window = np.hanning(frame_size)
    prev_spec = np.zeros(frame_size // 2 + 1)
    onsets: list[float] = []

    for i in range(n_frames):
        s = i * hop
        frame = ds[s:s + frame_size]
        if len(frame) < frame_size:
            break
        spec = np.abs(rfft(frame * window))
        flux = float(np.sum(np.maximum(0, spec - prev_spec)))
        onsets.append(flux)
        prev_spec = spec

    onset_arr = np.array(onsets)
    onset_arr -= np.mean(onset_arr)

    # FFT-based autocorrelation
    nn = len(onset_arr)
    fft_sz = 1
    while fft_sz < 2 * nn:
        fft_sz *= 2
    onset_fft = rfft(onset_arr, fft_sz)
    corr = np.fft.irfft(onset_fft * np.conj(onset_fft), fft_sz)[:nn]

    # Wide search 60-200 BPM, then apply halftime/doubletime correction
    min_lag = max(1, int(60.0 / 200.0 * ds_sr / hop))
    max_lag = min(int(60.0 / 60.0 * ds_sr / hop), len(corr) - 1)
    if min_lag >= max_lag:
        return RhythmDNA()

    search = corr[min_lag:max_lag + 1]
    best_idx = int(np.argmax(search))
    best_lag = min_lag + best_idx
    if best_lag < 1:
        return RhythmDNA()

    bpm = 60.0 / (best_lag * hop / ds_sr)
    confidence = float(search[best_idx] / (corr[0] + 1e-10))

    # Halftime/doubletime correction for EDM (prefer 120-160 range)
    candidates = [(bpm, confidence)]
    for mult in (0.5, 2.0):
        alt_bpm = bpm * mult
        alt_lag = int(60.0 / alt_bpm * ds_sr / hop)
        if 1 <= alt_lag < len(corr):
            alt_conf = float(corr[alt_lag] / (corr[0] + 1e-10))
            candidates.append((alt_bpm, alt_conf))
    # Prefer candidates in 120-160 range with reasonable confidence
    edm_cands = [(b, c) for b, c in candidates if 120 <= b <= 160]
    if edm_cands:
        bpm, confidence = max(edm_cands, key=lambda x: x[1])
    else:
        # Fall back to candidate closest to 140 with decent confidence
        scored = [(b, c, c * max(0, 1.0 - abs(b - 140) / 80))
                  for b, c in candidates if 60 <= b <= 200]
        if scored:
            best = max(scored, key=lambda x: x[2])
            bpm, confidence = best[0], best[1]

    # Onset regularity: standard deviation of intervals between peaks
    threshold = float(np.mean(onset_arr) + np.std(onset_arr))
    peak_locs = [i for i in range(1, nn - 1)
                 if onset_arr[i] > threshold
                 and onset_arr[i] > onset_arr[i - 1]
                 and onset_arr[i] > onset_arr[i + 1]]
    intervals = np.diff(peak_locs).astype(float) if len(peak_locs) > 2 else []
    stability = 0.0
    regularity = 0.0
    swing = 0.5
    if len(intervals) > 2:
        mean_int = float(np.mean(intervals))
        if mean_int > 0:
            stability = 1.0 - min(1.0, float(np.std(intervals)) / mean_int)
            regularity = stability

        # Swing detection: ratio of even/odd intervals
        even_ints = intervals[::2]
        odd_ints = intervals[1::2]
        if len(even_ints) > 0 and len(odd_ints) > 0:
            total_io = float(np.mean(even_ints) + np.mean(odd_ints))
            if total_io > 0:
                swing = float(np.mean(even_ints)) / total_io

    onset_rate = len(peak_locs) / (nn * hop / ds_sr) if nn > 0 else 0.0

    return RhythmDNA(
        bpm=round(bpm, 1),
        bpm_confidence=round(confidence, 3),
        beat_stability=round(stability, 3),
        onset_rate=round(onset_rate, 2),
        onset_regularity=round(regularity, 3),
        swing_ratio=round(swing, 3),
        groove_strength=round(confidence, 3),
    )


# ═══════════════════════════════════════════════════════════════════════════
# HARMONIC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

_KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                    2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                    2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
               "F#", "G", "G#", "A", "A#", "B"]


def _analyze_harmonic(mono: np.ndarray, sr: int,
                      fft_size: int = 8192) -> HarmonicDNA:
    """Key detection, chroma, dissonance."""
    n = len(mono)
    if n < fft_size:
        return HarmonicDNA()

    window = np.hanning(fft_size)
    hop = fft_size // 2
    n_frames = min(32, max(1, (n - fft_size) // hop))
    freqs = rfftfreq(fft_size, 1.0 / sr)

    chroma = np.zeros(12)
    bass_hist = np.zeros(12)

    for i in range(n_frames):
        s = i * hop
        frame = mono[s:s + fft_size]
        if len(frame) < fft_size:
            break
        spectrum = np.abs(rfft(frame * window))

        # Build chroma from spectrum
        for j, f in enumerate(freqs):
            if f < 30 or f > 5000:
                continue
            midi = 12.0 * math.log2(f / 440.0) + 69.0
            pitch_class = int(round(midi)) % 12
            chroma[pitch_class] += float(spectrum[j]) ** 2

            # Bass histogram (< 250 Hz)
            if f < 250:
                bass_hist[pitch_class] += float(spectrum[j]) ** 2

    # Normalize
    c_total = np.sum(chroma)
    if c_total > 0:
        chroma /= c_total
    b_total = np.sum(bass_hist)
    if b_total > 0:
        bass_hist /= b_total

    # Key detection via Krumhansl-Kessler correlation
    best_corr = -2.0
    best_key = ""
    for shift in range(12):
        rolled = np.roll(chroma, -shift)
        for mode, profile, name in [
            ("major", _KRUMHANSL_MAJOR, "major"),
            ("minor", _KRUMHANSL_MINOR, "minor"),
        ]:
            prof = np.array(profile)
            r = float(np.corrcoef(rolled, prof)[0, 1])
            if r > best_corr:
                best_corr = r
                best_key = f"{_NOTE_NAMES[shift]} {name}"

    # Chroma entropy
    chroma_safe = chroma + 1e-10
    entropy = -float(np.sum(chroma_safe * np.log2(chroma_safe)))

    # Dissonance estimate (ratio of energy in tritone / minor 2nd intervals)
    dissonance = 0.0
    for i in range(12):
        # tritone = 6 semitones, minor 2nd = 1 semitone
        dissonance += chroma[i] * (chroma[(i + 1) % 12]
                                   + chroma[(i + 6) % 12])

    return HarmonicDNA(
        key=best_key,
        key_confidence=round(max(best_corr, 0.0), 3),
        chroma_entropy=round(entropy, 3),
        dissonance=round(min(dissonance, 1.0), 3),
        bass_note_histogram=[round(float(b), 4) for b in bass_hist],
        chroma_mean=[round(float(c), 4) for c in chroma],
    )


# ═══════════════════════════════════════════════════════════════════════════
# LOUDNESS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_loudness(mono: np.ndarray, left: np.ndarray,
                      right: np.ndarray, sr: int) -> LoudnessDNA:
    """Loudness, dynamics, limiting artifacts."""
    all_samples = np.concatenate([left, right])
    peak = float(np.max(np.abs(all_samples)))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    peak_db = _db(peak)
    rms_db = _db(rms)
    lufs = rms_db - 0.7  # K-weight approximation

    # Dynamic range (p5-p95 of 100ms blocks)
    block_size = int(sr * 0.1)
    n_blocks = len(mono) // block_size
    block_rms: list[float] = []
    for i in range(max(n_blocks, 1)):
        block = mono[i * block_size:(i + 1) * block_size]
        if len(block) > 0:
            br = float(np.sqrt(np.mean(block ** 2)))
            if br > 1e-10:
                block_rms.append(_db(br))

    dynamic_range = 0.0
    lra = 0.0
    if len(block_rms) >= 2:
        block_rms.sort()
        p5 = block_rms[max(0, len(block_rms) // 20)]
        p95 = block_rms[min(len(block_rms) - 1,
                            len(block_rms) * 19 // 20)]
        dynamic_range = p95 - p5

        # LRA: short-term loudness range (interquartile)
        p25 = block_rms[len(block_rms) // 4]
        p75 = block_rms[3 * len(block_rms) // 4]
        lra = p75 - p25

    # Limiting artifacts: consecutive near-ceiling samples
    ceiling = 0.99
    clipped = np.abs(all_samples) >= ceiling
    total_samples = len(all_samples)
    clip_pct = float(np.sum(clipped)) / total_samples if total_samples else 0

    # A-weighted RMS
    a_rms = _a_weighted_rms(mono, sr)

    return LoudnessDNA(
        peak_db=round(peak_db, 2),
        rms_db=round(rms_db, 2),
        lufs_estimate=round(lufs, 2),
        crest_factor_db=round(peak_db - rms_db, 2),
        dynamic_range_db=round(dynamic_range, 2),
        loudness_range_db=round(lra, 2),
        limiting_artifacts=round(clip_pct, 4),
        a_weighted_rms_db=round(a_rms, 2),
    )


def _a_weighted_rms(mono: np.ndarray, sr: int,
                    fft_size: int = 8192) -> float:
    """Compute A-weighted RMS in dB."""
    n = min(len(mono), fft_size * 16)
    if n < fft_size:
        return _db(float(np.sqrt(np.mean(mono ** 2))))

    hop = fft_size // 2
    window = np.hanning(fft_size)
    total_energy = 0.0
    count = 0
    for start in range(0, n - fft_size, hop):
        chunk = mono[start:start + fft_size]
        spectrum = np.abs(rfft(chunk * window))
        freqs = rfftfreq(fft_size, 1.0 / sr)
        for idx, f in enumerate(freqs):
            if f > 0:
                a_db = _a_weight(f)
                a_lin = 10.0 ** (a_db / 20.0)
                total_energy += (spectrum[idx] * a_lin) ** 2
                count += 1
    if count < 1:
        return -96.0
    return _db(math.sqrt(total_energy / count))


# ═══════════════════════════════════════════════════════════════════════════
# ARRANGEMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_arrangement(mono: np.ndarray, sr: int) -> ArrangementDNA:
    """Section detection via energy change points."""
    n = len(mono)
    duration = n / sr
    n_segments = 20
    seg_size = n // n_segments
    if seg_size < 1:
        return ArrangementDNA(duration_s=duration)

    # Energy curve (20 segments) -- use short-window RMS in dB
    curve: list[float] = []
    for i in range(n_segments):
        seg = mono[i * seg_size:(i + 1) * seg_size]
        rms = float(np.sqrt(np.mean(seg ** 2)))
        curve.append(_db(rms))

    # Smoothed energy for section detection
    smooth: list[float] = []
    for i in range(n_segments):
        lo = max(0, i - 1)
        hi = min(n_segments, i + 2)
        smooth.append(float(np.mean(curve[lo:hi])))

    # Detect boundaries via energy changes (adjacent or 2-segment look-back)
    boundaries = [0.0]
    for i in range(1, n_segments):
        d1 = abs(smooth[i] - smooth[i - 1])
        d2 = abs(smooth[i] - smooth[max(0, i - 2)]) if i >= 2 else d1
        if d1 > 2.0 or d2 > 3.5:
            boundaries.append(i / n_segments)
    boundaries.append(1.0)

    # Compute average energy per section
    sec_energies: list[float] = []
    for i in range(len(boundaries) - 1):
        start_idx = int(boundaries[i] * n_segments)
        end_idx = int(boundaries[i + 1] * n_segments)
        end_idx = min(end_idx, n_segments)
        if start_idx >= end_idx:
            sec_energies.append(-96.0)
        else:
            sec_energies.append(float(np.mean(curve[start_idx:end_idx])))

    # Label using relative energy + transitions
    p25 = float(np.percentile(curve, 25))
    p50 = float(np.percentile(curve, 50))
    p75 = float(np.percentile(curve, 75))
    e_range = max(curve) - min(curve)
    labels: list[str] = []
    for i, seg_e in enumerate(sec_energies):
        prev_e = sec_energies[i - 1] if i > 0 else seg_e - 10
        rising = seg_e - prev_e
        # Drop: high-energy section following a significant rise
        if seg_e >= p75 - 1.0 and rising > max(1.5, e_range * 0.10):
            labels.append("drop")
        elif seg_e >= p75 and i > 0 and prev_e < p50:
            labels.append("drop")
        elif seg_e <= p25 - 3:
            labels.append("intro/outro")
        elif seg_e <= p25:
            labels.append("breakdown")
        elif rising > 1.0 and seg_e > p50:
            labels.append("build")
        elif seg_e >= p75:
            labels.append("body")
        else:
            labels.append("body")

    drop_count = sum(1 for lb in labels if lb == "drop")

    # Intro/drop contrast
    intro_e = float(np.mean(curve[:3])) if len(curve) >= 3 else curve[0]
    loudest = max(curve) if curve else -96.0
    contrast = loudest - intro_e

    loudest_idx = int(np.argmax(curve))
    quietest_idx = int(np.argmin(curve))

    # ── expanded arrangement metrics (session 168) ──

    # Tension curve: spectral flux summed per segment (proxy for tension)
    tension_curve: list[float] = []
    t_fft = min(2048, n // 20)
    if t_fft >= 256:
        t_window = np.hanning(t_fft)
        for si in range(n_segments):
            seg = mono[si * seg_size:(si + 1) * seg_size]
            prev_s = np.zeros(t_fft // 2 + 1)
            flux_total = 0.0
            t_hop = t_fft // 2
            nf = max(1, (len(seg) - t_fft) // t_hop)
            for fi in range(min(nf, 8)):
                fr = seg[fi * t_hop:fi * t_hop + t_fft]
                if len(fr) < t_fft:
                    break
                sp = np.abs(rfft(fr * t_window))
                flux_total += float(np.sum(np.maximum(0, sp - prev_s)))
                prev_s = sp
            tension_curve.append(round(flux_total / max(nf, 1), 2))
    if not tension_curve:
        tension_curve = [0.0] * n_segments

    # Transition sharpness: avg absolute dB change at boundaries
    trans_sharp = 0.0
    if len(boundaries) > 2:
        diffs = []
        for bi in range(1, len(boundaries) - 1):
            idx = min(int(boundaries[bi] * n_segments), n_segments - 1)
            if idx > 0:
                diffs.append(abs(smooth[idx] - smooth[idx - 1]))
        trans_sharp = float(np.mean(diffs)) if diffs else 0.0

    # Energy arc type: classify the overall energy shape
    if len(curve) >= 4:
        first_q = float(np.mean(curve[:5]))
        mid_q = float(np.mean(curve[8:13]))
        last_q = float(np.mean(curve[15:]))
        if drop_count >= 1 and mid_q > first_q + 3:
            arc_type = "build-drop"
        elif abs(mid_q - first_q) < 2 and abs(mid_q - last_q) < 2:
            arc_type = "plateau"
        elif first_q < mid_q < last_q or first_q > mid_q > last_q:
            arc_type = "gradual"
        else:
            arc_type = "chaotic"
    else:
        arc_type = "unknown"

    # Buildup effectiveness: contrast between build sections and drops
    build_e = [sec_energies[i] for i, lb in enumerate(labels)
               if lb == "build"]
    drop_e = [sec_energies[i] for i, lb in enumerate(labels)
              if lb == "drop"]
    buildup_eff = 0.0
    if build_e and drop_e:
        buildup_eff = float(np.mean(drop_e)) - float(np.mean(build_e))

    # Section diversity: entropy of label distribution
    sec_div = 0.0
    if labels:
        from collections import Counter
        counts = Counter(labels)
        total = len(labels)
        for c in counts.values():
            p = c / total
            if p > 0:
                sec_div -= p * math.log2(p)

    # Breakdown depth: avg energy dip in breakdown sections
    bd_depth = 0.0
    bd_energies = [sec_energies[i] for i, lb in enumerate(labels)
                   if lb == "breakdown"]
    if bd_energies:
        bd_depth = float(np.mean(bd_energies)) - loudest

    return ArrangementDNA(
        duration_s=round(duration, 2),
        n_sections=len(labels),
        section_labels=labels,
        section_boundaries_pct=[round(b, 3) for b in boundaries],
        energy_curve=[round(e, 2) for e in curve],
        drop_count=drop_count,
        intro_drop_contrast_db=round(contrast, 2),
        loudest_section_idx=loudest_idx,
        quietest_section_idx=quietest_idx,
        tension_curve=tension_curve,
        transition_sharpness=round(trans_sharp, 2),
        energy_arc_type=arc_type,
        buildup_effectiveness=round(buildup_eff, 2),
        section_diversity=round(sec_div, 3),
        breakdown_depth_db=round(bd_depth, 2),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STEREO ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_stereo(left: np.ndarray, right: np.ndarray,
                    sr: int) -> StereoDNA:
    """Stereo width (overall + frequency-dependent)."""
    n = min(len(left), len(right))
    L = left[:n]
    R = right[:n]

    mid = (L + R) * 0.5
    side = (L - R) * 0.5

    mid_e = float(np.mean(mid ** 2))
    side_e = float(np.mean(side ** 2))
    total_e = mid_e + side_e
    width = side_e / total_e if total_e > 1e-10 else 0.0

    # Pearson correlation
    l_std = float(np.std(L))
    r_std = float(np.std(R))
    if l_std < 1e-10 or r_std < 1e-10:
        correlation = 1.0
    else:
        correlation = float(
            np.mean((L - np.mean(L)) * (R - np.mean(R))) / (l_std * r_std)
        )

    mono_compat = mid_e / total_e if total_e > 1e-10 else 1.0

    # Frequency-dependent width via FFT
    fft_size = min(8192, n)
    if fft_size < 256:
        return StereoDNA(width=width, correlation=correlation,
                         mono_compat=mono_compat)

    window = np.hanning(fft_size)
    center = n // 2
    half = fft_size // 2
    l_chunk = L[center - half:center + half]
    r_chunk = R[center - half:center + half]

    if len(l_chunk) < fft_size:
        return StereoDNA(width=width, correlation=correlation,
                         mono_compat=mono_compat)

    L_spec = np.abs(rfft(l_chunk * window))
    R_spec = np.abs(rfft(r_chunk * window))
    freqs = rfftfreq(fft_size, 1.0 / sr)

    mid_spec = (L_spec + R_spec) * 0.5
    side_spec = np.abs(L_spec - R_spec) * 0.5

    def _band_width(lo: float, hi: float) -> float:
        mask = (freqs >= lo) & (freqs < hi)
        m = float(np.sum(mid_spec[mask] ** 2))
        s = float(np.sum(side_spec[mask] ** 2))
        t = m + s
        return s / t if t > 1e-10 else 0.0

    return StereoDNA(
        width=round(width, 4),
        correlation=round(correlation, 4),
        mono_compat=round(mono_compat, 4),
        width_low=round(_band_width(20, 250), 4),
        width_mid=round(_band_width(250, 4000), 4),
        width_high=round(_band_width(4000, sr / 2), 4),
    )


# ═══════════════════════════════════════════════════════════════════════════
# BASS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_bass(mono: np.ndarray, sr: int,
                  fft_size: int = 8192) -> BassDNA:
    """Sub weight, fundamental, harmonics, wobble/modulation."""
    n = len(mono)
    if n < fft_size:
        return BassDNA()

    window = np.hanning(fft_size)
    freqs = rfftfreq(fft_size, 1.0 / sr)

    # Use drop section (30-60%) for bass analysis
    drop_start = int(n * 0.30)
    drop_end = int(n * 0.60)
    drop = mono[drop_start:drop_end]
    if len(drop) < fft_size:
        drop = mono

    center = len(drop) // 2
    half = fft_size // 2
    chunk = drop[max(0, center - half):center + half]
    if len(chunk) < fft_size:
        chunk = np.pad(chunk, (0, fft_size - len(chunk)))

    spectrum = np.abs(rfft(chunk * window))
    power = spectrum ** 2

    total_p = float(np.sum(power[(freqs >= 20) & (freqs <= 20000)]))
    if total_p < 1e-10:
        return BassDNA()

    sub_p = float(np.sum(power[(freqs >= 20) & (freqs < 60)]))
    bass_p = float(np.sum(power[(freqs >= 60) & (freqs < 250)]))

    # Dominant sub frequency
    sub_mask = (freqs >= 20) & (freqs < 120)
    sub_freqs = freqs[sub_mask]
    sub_power = power[sub_mask]
    fundamental = 0.0
    if len(sub_power) > 0 and float(np.max(sub_power)) > 1e-10:
        fundamental = float(sub_freqs[np.argmax(sub_power)])

    # Harmonic ratio: energy at 2f, 3f vs fundamental
    harmonic_e = 0.0
    if fundamental > 20:
        for mult in [2, 3, 4]:
            h_freq = fundamental * mult
            h_mask = (freqs >= h_freq * 0.9) & (freqs <= h_freq * 1.1)
            harmonic_e += float(np.sum(power[h_mask]))
    fund_e = float(np.sum(power[(freqs >= fundamental * 0.9)
                                & (freqs <= fundamental * 1.1)]
                          )) if fundamental > 20 else 1e-10
    harmonic_ratio = harmonic_e / (fund_e + 1e-10)

    # Wobble / modulation detection via bass envelope autocorrelation
    # Bandpass 30-250 Hz, compute envelope, autocorrelate
    bass_mask = (freqs >= 30) & (freqs < 250)
    bass_spec = np.zeros_like(spectrum)
    bass_spec[bass_mask] = spectrum[bass_mask]
    # Quick envelope from short blocks of the drop
    env_block = int(sr * 0.01)  # 10ms blocks
    n_blocks = min(len(drop) // env_block, 500)
    envelope: list[float] = []
    for i in range(n_blocks):
        blk = drop[i * env_block:(i + 1) * env_block]
        # Rough bass energy via lowpass (just use abs mean as proxy)
        envelope.append(float(np.sqrt(np.mean(blk ** 2))))

    wobble_rate = 0.0
    wobble_depth = 0.0
    if len(envelope) > 20:
        env_arr = np.array(envelope)
        env_arr -= np.mean(env_arr)
        env_std = float(np.std(env_arr))
        if env_std > 1e-10:
            env_arr /= env_std
            # Autocorrelation of envelope
            nn = len(env_arr)
            fsz = 1
            while fsz < 2 * nn:
                fsz *= 2
            e_fft = rfft(env_arr, fsz)
            e_corr = np.fft.irfft(e_fft * np.conj(e_fft), fsz)[:nn]
            e_corr /= (e_corr[0] + 1e-10)

            # Search 1-20 Hz modulation (dubstep wobble range)
            env_sr = sr / env_block
            min_lag = max(1, int(env_sr / 20))
            max_lag = min(int(env_sr / 1), nn - 1)
            if min_lag < max_lag:
                search = e_corr[min_lag:max_lag + 1]
                best = int(np.argmax(search))
                if search[best] > 0.2:
                    wobble_rate = env_sr / (min_lag + best)
                    wobble_depth = float(search[best])

    # Sidechain pump count
    pump_count = _sidechain_pumps(drop, sr)

    return BassDNA(
        sub_weight=round(sub_p / total_p, 4),
        bass_weight=round(bass_p / total_p, 4),
        fundamental_hz=round(fundamental, 1),
        harmonic_ratio=round(min(harmonic_ratio, 10.0), 3),
        wobble_rate_hz=round(wobble_rate, 2),
        wobble_depth=round(min(wobble_depth, 1.0), 3),
        sidechain_pump_count=pump_count,
    )


def _sidechain_pumps(segment: np.ndarray, sr: int) -> int:
    """Count sidechain pump events (>6 dB dip + recovery in 200ms)."""
    block_size = int(sr * 0.010)
    n_blocks = len(segment) // block_size
    if n_blocks < 4:
        return 0

    envelope: list[float] = []
    for i in range(n_blocks):
        blk = segment[i * block_size:(i + 1) * block_size]
        envelope.append(float(np.sqrt(np.mean(blk ** 2))))

    env = np.array(envelope)
    env_max = float(np.max(env))
    if env_max < 1e-10:
        return 0
    env /= env_max

    pumps = 0
    i = 0
    while i < len(env) - 2:
        if env[i] > 0.3 and env[i + 1] < env[i] * 0.5:
            for j in range(i + 2, min(i + 20, len(env))):
                if env[j] > env[i] * 0.7:
                    pumps += 1
                    i = j
                    break
        i += 1
    return pumps


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTION QUALITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_production(mono: np.ndarray, sr: int) -> ProductionDNA:
    """Transient sharpness, reverb, sidechain, compression, distortion."""
    n = len(mono)
    if n < 1024:
        return ProductionDNA()

    # Transient sharpness: avg attack rise time of onset peaks
    block_ms = 5
    block_size = int(sr * block_ms / 1000)
    n_blocks = len(mono) // block_size
    envelope: list[float] = []
    for i in range(min(n_blocks, 2000)):
        blk = mono[i * block_size:(i + 1) * block_size]
        envelope.append(float(np.max(np.abs(blk))))

    transient_sharpness = 0.0
    rise_count = 0
    for i in range(1, len(envelope) - 1):
        if envelope[i] > envelope[i - 1] * 1.5 and envelope[i] > 0.05:
            rise = (envelope[i] - envelope[i - 1]) / (envelope[i] + 1e-10)
            transient_sharpness += rise
            rise_count += 1
    if rise_count > 0:
        transient_sharpness /= rise_count

    # Reverb estimation: ratio of decaying tail energy to direct energy
    # Compare early (0-20ms) vs late (50-200ms) energy after onsets
    reverb_amount = 0.0
    rev_checks = 0
    onset_block = int(sr * 0.005)
    tail_block = int(sr * 0.100)
    for i in range(1, min(len(envelope), 1000)):
        if (envelope[i] > envelope[i - 1] * 2.0
                and envelope[i] > 0.1):
            # Found onset
            direct_idx = i * block_size
            tail_start = direct_idx + int(sr * 0.05)
            tail_end = tail_start + tail_block
            if tail_end < n:
                direct_e = float(np.mean(
                    mono[direct_idx:direct_idx + onset_block] ** 2))
                tail_e = float(np.mean(
                    mono[tail_start:tail_end] ** 2))
                if direct_e > 1e-10:
                    reverb_amount += tail_e / direct_e
                    rev_checks += 1
    if rev_checks > 0:
        reverb_amount /= rev_checks

    # Sidechain depth: avg dip magnitude from pump detection
    pump_depths: list[float] = []
    env = np.array(envelope)
    i = 0
    while i < len(env) - 2:
        if env[i] > 0.2 and env[i + 1] < env[i] * 0.5:
            depth_db = _db(env[i + 1] + 1e-10) - _db(env[i] + 1e-10)
            pump_depths.append(abs(depth_db))
            i += 3
        else:
            i += 1
    avg_sc_depth = float(np.mean(pump_depths)) if pump_depths else 0.0

    # Compression estimate: ratio of peak to RMS of envelope
    env_arr = np.array(envelope)
    env_rms = float(np.sqrt(np.mean(env_arr ** 2)))
    env_peak = float(np.max(env_arr))
    comp_ratio = env_peak / (env_rms + 1e-10)

    # Distortion: THD-like estimate from odd harmonic content
    fft_size = min(8192, n)
    center = n // 2
    half = fft_size // 2
    chunk = mono[max(0, center - half):center + half]
    if len(chunk) < fft_size:
        chunk = np.pad(chunk, (0, fft_size - len(chunk)))
    window = np.hanning(fft_size)
    spec = np.abs(rfft(chunk * window))
    freqs = rfftfreq(fft_size, 1.0 / sr)

    # Estimate distortion from ratio of odd harmonics above 5kHz
    high_e = float(np.sum(spec[(freqs > 5000)] ** 2))
    total_e = float(np.sum(spec ** 2))
    distortion = high_e / (total_e + 1e-10)

    # Noise floor
    noise_floor = -96.0
    if block_rms := [_db(envelope[j]) for j in range(len(envelope))
                     if envelope[j] > 1e-10]:
        noise_floor = min(block_rms)

    # Presence peak (biggest energy in 2-6 kHz)
    presence_mask = (freqs >= 2000) & (freqs <= 6000)
    presence_hz = 0.0
    p_spec = spec[presence_mask]
    p_freqs = freqs[presence_mask]
    if len(p_spec) > 0:
        presence_hz = float(p_freqs[np.argmax(p_spec)])

    return ProductionDNA(
        transient_sharpness=round(min(transient_sharpness, 1.0), 3),
        reverb_amount=round(min(reverb_amount, 1.0), 3),
        sidechain_depth_db=round(avg_sc_depth, 2),
        compression_ratio=round(min(comp_ratio, 20.0), 2),
        distortion_amount=round(min(distortion, 1.0), 4),
        noise_floor_db=round(noise_floor, 2),
        presence_peak_hz=round(presence_hz, 1),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STYLE ANALYSIS (Session 168)
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_style(analysis: ReferenceAnalysis) -> StyleDNA:
    """Derive musical style traits from existing DNA sub-analyses."""
    sp = analysis.spectral
    rh = analysis.rhythm
    ha = analysis.harmonic
    lo = analysis.loudness
    pr = analysis.production
    bs = analysis.bass

    # Aggression: distortion + transient sharpness + high energy
    aggression = min(1.0, (
        pr.distortion_amount * 3.0
        + pr.transient_sharpness
        + min(1.0, max(0, lo.rms_db + 10) / 10)
    ) / 3.0)

    # Darkness: negative tilt + minor key + low centroid
    is_minor = 1.0 if "minor" in ha.key.lower() else 0.0
    centroid_dark = max(0.0, 1.0 - sp.centroid_hz / 5000)
    tilt_dark = min(1.0, max(0.0, -sp.tilt_db_per_oct / 10))
    darkness = (is_minor * 0.3 + centroid_dark * 0.4 + tilt_dark * 0.3)

    # Energy level: RMS + onset rate + transients
    rms_energy = min(1.0, max(0, lo.rms_db + 20) / 20)
    onset_energy = min(1.0, rh.onset_rate / 15.0)
    energy_level = (rms_energy * 0.4 + onset_energy * 0.3
                    + pr.transient_sharpness * 0.3)

    # Danceability: steady beat + in-range BPM + beat stability
    bpm_score = max(0.0, 1.0 - abs(rh.bpm - 140) / 60) if rh.bpm > 0 else 0
    danceability = (bpm_score * 0.3 + rh.beat_stability * 0.35
                    + rh.onset_regularity * 0.35)

    # Density: spectral flatness + onset density
    density = (sp.flatness * 0.5
               + min(1.0, rh.onset_rate / 20.0) * 0.5)

    # Brightness: centroid + high band energy
    brightness = min(1.0, (
        sp.centroid_hz / 6000 * 0.6
        + (sp.high_mid + sp.high) * 0.4
    ))

    # Bass dominance
    bass_dominance = min(1.0, sp.sub + sp.bass + bs.sub_weight * 0.5)

    # Rhythm complexity: swing deviation + onset irregularity
    swing_dev = abs(rh.swing_ratio - 0.5) * 2
    rhythm_complexity = min(1.0, (
        swing_dev * 0.4
        + (1.0 - rh.onset_regularity) * 0.6
    ))

    # Genre tags
    tags: list[str] = []
    if rh.bpm >= 130 and rh.bpm <= 155:
        tags.append("dubstep-tempo")
    if rh.bpm >= 170:
        tags.append("dnb-tempo")
    if rh.bpm >= 125 and rh.bpm <= 135:
        tags.append("house-tempo")
    if bass_dominance > 0.6:
        tags.append("bass-heavy")
    if aggression > 0.6:
        tags.append("aggressive")
    if darkness > 0.6:
        tags.append("dark")
    if brightness > 0.6:
        tags.append("bright")
    if bs.wobble_rate_hz > 1:
        tags.append("wobble")
    if sp.flatness > 0.3:
        tags.append("noisy")
    if danceability > 0.7:
        tags.append("danceable")

    return StyleDNA(
        aggression=round(aggression, 3),
        darkness=round(darkness, 3),
        energy_level=round(energy_level, 3),
        danceability=round(danceability, 3),
        density=round(density, 3),
        brightness=round(brightness, 3),
        bass_dominance=round(bass_dominance, 3),
        rhythm_complexity=round(rhythm_complexity, 3),
        genre_tags=tags,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SOUND DESIGN ANALYSIS (Session 168)
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_sound_design(mono: np.ndarray, sr: int,
                          fft_size: int = 8192) -> SoundDesignDNA:
    """Sound design characteristics: attack, harmonics, modulation."""
    n = len(mono)
    if n < fft_size:
        return SoundDesignDNA()

    # ── Attack sharpness via log-attack-time on onset peaks ──
    block_ms = 2
    block_size = max(1, int(sr * block_ms / 1000))
    n_blocks = min(len(mono) // block_size, 5000)
    envelope: list[float] = []
    for i in range(n_blocks):
        blk = mono[i * block_size:(i + 1) * block_size]
        envelope.append(float(np.max(np.abs(blk))))

    attack_times: list[float] = []
    decay_ratios: list[float] = []
    for i in range(2, len(envelope) - 20):
        if (envelope[i] > envelope[i - 1] * 1.5
                and envelope[i] > 0.05):
            # Measure attack: how many blocks to reach peak
            peak_val = envelope[i]
            for j in range(i + 1, min(i + 20, len(envelope))):
                if envelope[j] > peak_val:
                    peak_val = envelope[j]
                else:
                    break
            attack_blocks = max(1, j - i + 1)
            attack_ms = attack_blocks * block_ms
            attack_times.append(attack_ms)

            # Decay: ratio of energy 50ms after peak to peak
            decay_idx = min(j + int(50 / block_ms), len(envelope) - 1)
            if peak_val > 1e-10:
                decay_ratios.append(envelope[decay_idx] / peak_val)

    attack_sharpness = 0.0
    if attack_times:
        avg_attack = float(np.mean(attack_times))
        attack_sharpness = max(0.0, min(1.0, 1.0 - avg_attack / 50))

    decay_char = float(np.mean(decay_ratios)) if decay_ratios else 0.5

    # ── Harmonic content analysis ──
    # Use center section for tonal analysis
    center = n // 2
    half = fft_size // 2
    chunk = mono[max(0, center - half):center + half]
    if len(chunk) < fft_size:
        chunk = np.pad(chunk, (0, fft_size - len(chunk)))

    window = np.hanning(fft_size)
    spectrum = np.abs(rfft(chunk * window))
    freqs = rfftfreq(fft_size, 1.0 / sr)
    power = spectrum ** 2

    # Find fundamental (strongest peak 30-500 Hz)
    fund_mask = (freqs >= 30) & (freqs < 500)
    fund_spec = spectrum[fund_mask]
    fund_freqs = freqs[fund_mask]
    fundamental = 0.0
    if len(fund_spec) > 0 and float(np.max(fund_spec)) > 1e-10:
        fundamental = float(fund_freqs[np.argmax(fund_spec)])

    # Inharmonicity: deviation of partials from exact harmonic series
    inharmonicity = 0.0
    odd_energy = 0.0
    even_energy = 0.0
    if fundamental > 30:
        for h in range(2, 16):
            expected = fundamental * h
            if expected > sr / 2:
                break
            # Find actual peak near expected harmonic
            h_mask = (freqs >= expected * 0.95) & (freqs <= expected * 1.05)
            h_spec = spectrum[h_mask]
            h_freqs = freqs[h_mask]
            if len(h_spec) > 0:
                actual_peak = float(h_freqs[np.argmax(h_spec)])
                deviation = abs(actual_peak - expected) / expected
                inharmonicity += deviation
                energy = float(np.max(h_spec)) ** 2
                if h % 2 == 1:
                    odd_energy += energy
                else:
                    even_energy += energy
        inharmonicity /= 14  # normalize by number of harmonics checked

    odd_even = 0.5
    total_he = odd_energy + even_energy
    if total_he > 1e-10:
        odd_even = odd_energy / total_he

    # ── Modulation detection (bass envelope autocorrelation, 1-30 Hz) ──
    env_block = int(sr * 0.005)  # 5ms blocks
    n_env = min(len(mono) // env_block, 2000)
    env_arr = np.array([
        float(np.sqrt(np.mean(mono[i * env_block:(i + 1) * env_block] ** 2)))
        for i in range(n_env)
    ]) if n_env > 20 else np.zeros(1)

    mod_depth = 0.0
    mod_rate = 0.0
    if len(env_arr) > 40:
        env_ac = env_arr - np.mean(env_arr)
        env_std = float(np.std(env_ac))
        if env_std > 1e-10:
            env_ac /= env_std
            nn = len(env_ac)
            fsz = 1
            while fsz < 2 * nn:
                fsz *= 2
            e_fft = rfft(env_ac, fsz)
            e_corr = np.fft.irfft(e_fft * np.conj(e_fft), fsz)[:nn]
            e_corr /= (e_corr[0] + 1e-10)

            env_sr = sr / env_block
            min_lag = max(1, int(env_sr / 30))
            max_lag = min(int(env_sr / 1), nn - 1)
            if min_lag < max_lag:
                search = e_corr[min_lag:max_lag + 1]
                best = int(np.argmax(search))
                if search[best] > 0.15:
                    mod_rate = env_sr / (min_lag + best)
                    mod_depth = float(search[best])

    # ── Texture density: number of simultaneous spectral peaks ──
    threshold = float(np.mean(spectrum)) * 2
    n_peaks = sum(1 for j in range(1, len(spectrum) - 1)
                  if spectrum[j] > spectrum[j - 1]
                  and spectrum[j] > spectrum[j + 1]
                  and spectrum[j] > threshold)
    texture_density = min(1.0, n_peaks / 200.0)

    # ── Formant presence: energy in vocal formant regions ──
    formant_bands = [(300, 900), (900, 2500), (2500, 3500)]
    formant_energy = 0.0
    total_e = float(np.sum(power[(freqs >= 100) & (freqs < 8000)]))
    for lo, hi in formant_bands:
        formant_energy += float(np.sum(power[(freqs >= lo) & (freqs < hi)]))
    formant_presence = formant_energy / (total_e + 1e-10)

    # ── Noise content: spectral flatness as noise indicator ──
    geo_mean = float(np.exp(np.mean(np.log(spectrum + 1e-10))))
    arith_mean = float(np.mean(spectrum))
    noise_content = geo_mean / (arith_mean + 1e-10)

    # ── Spectral movement: avg frame-to-frame spectral change ──
    hop = fft_size // 2
    nf = min(32, max(1, (n - fft_size) // hop))
    prev_s = np.zeros(len(freqs))
    movement_sum = 0.0
    for i in range(nf):
        s = i * hop
        frame = mono[s:s + fft_size]
        if len(frame) < fft_size:
            break
        sp = np.abs(rfft(frame * window))
        if i > 0 and float(np.sum(sp)) > 1e-10:
            # Cosine distance
            dot = float(np.dot(sp, prev_s))
            n1 = float(np.linalg.norm(sp))
            n2 = float(np.linalg.norm(prev_s))
            if n1 > 1e-10 and n2 > 1e-10:
                movement_sum += 1.0 - dot / (n1 * n2)
        prev_s = sp
    spectral_movement = movement_sum / max(nf - 1, 1)

    return SoundDesignDNA(
        attack_sharpness=round(min(attack_sharpness, 1.0), 3),
        decay_character=round(min(decay_char, 1.0), 3),
        inharmonicity=round(min(inharmonicity, 1.0), 4),
        odd_even_ratio=round(odd_even, 3),
        modulation_depth=round(min(mod_depth, 1.0), 3),
        modulation_rate_hz=round(mod_rate, 2),
        texture_density=round(texture_density, 3),
        formant_presence=round(min(formant_presence, 1.0), 3),
        noise_content=round(min(noise_content, 1.0), 3),
        spectral_movement=round(min(spectral_movement, 1.0), 4),
    )


# ═══════════════════════════════════════════════════════════════════════════
# MIXING ANALYSIS (Session 168)
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_mixing(mono: np.ndarray, left: np.ndarray,
                    right: np.ndarray, sr: int,
                    fft_size: int = 8192) -> MixingDNA:
    """Mix engineering quality: EQ balance, phase, DR per band, mud."""
    n = min(len(left), len(right), len(mono))
    if n < fft_size:
        return MixingDNA()

    L = left[:n]
    R = right[:n]

    # ── Peak headroom ──
    peak = float(np.max(np.abs(np.concatenate([L, R]))))
    headroom = -_db(peak) if peak > 1e-10 else 96.0

    # ── 10-band EQ curve (ISO octave bands) ──
    center_freqs = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    window = np.hanning(fft_size)
    freqs = rfftfreq(fft_size, 1.0 / sr)

    # Average spectrum over multiple frames
    hop = fft_size // 2
    nf = min(32, max(1, (n - fft_size) // hop))
    avg_power = np.zeros(len(freqs))
    for i in range(nf):
        s = i * hop
        frame = mono[s:s + fft_size]
        if len(frame) < fft_size:
            break
        spec = np.abs(rfft(frame * window))
        avg_power += spec ** 2
    avg_power /= max(nf, 1)

    eq_curve: list[float] = []
    for cf in center_freqs:
        lo = cf / 1.414
        hi = cf * 1.414
        mask = (freqs >= lo) & (freqs < hi)
        band_power = float(np.sum(avg_power[mask]))
        eq_curve.append(round(_db(math.sqrt(band_power + 1e-20)), 2))

    # Frequency balance: how flat the EQ curve is (ideal = 0 std dev)
    if eq_curve:
        eq_std = float(np.std(eq_curve))
        freq_balance = max(0.0, 1.0 - eq_std / 20.0)
    else:
        freq_balance = 0.0

    # ── Mud ratio: 200-500 Hz energy relative to neighbors ──
    mud_mask = (freqs >= 200) & (freqs < 500)
    neighbors = ((freqs >= 100) & (freqs < 200)) | (
        (freqs >= 500) & (freqs < 1000))
    mud_e = float(np.sum(avg_power[mud_mask]))
    neighbor_e = float(np.sum(avg_power[neighbors]))
    mud_ratio = mud_e / (neighbor_e + 1e-10) if neighbor_e > 1e-10 else 0.0

    # ── Harshness ratio: 2-5 kHz energy relative to neighbors ──
    harsh_mask = (freqs >= 2000) & (freqs < 5000)
    harsh_nbr = ((freqs >= 1000) & (freqs < 2000)) | (
        (freqs >= 5000) & (freqs < 8000))
    harsh_e = float(np.sum(avg_power[harsh_mask]))
    harsh_nbr_e = float(np.sum(avg_power[harsh_nbr]))
    harshness = harsh_e / (harsh_nbr_e + 1e-10)

    # ── Air ratio: 8-16 kHz presence ──
    air_mask = (freqs >= 8000) & (freqs < 16000)
    total_e = float(np.sum(avg_power[(freqs >= 20) & (freqs <= 20000)]))
    air_ratio = float(np.sum(avg_power[air_mask])) / (total_e + 1e-10)

    # ── Phase coherence per frequency band ──
    center = n // 2
    half = fft_size // 2
    l_chunk = L[max(0, center - half):center + half]
    r_chunk = R[max(0, center - half):center + half]

    phase_overall = 0.0
    phase_low = 0.0
    phase_mid = 0.0
    phase_high = 0.0

    if len(l_chunk) >= fft_size and len(r_chunk) >= fft_size:
        L_spec = rfft(l_chunk[:fft_size] * window)
        R_spec = rfft(r_chunk[:fft_size] * window)

        # Phase difference per bin
        L_phase = np.angle(L_spec)
        R_phase = np.angle(R_spec)
        phase_diff = np.cos(L_phase - R_phase)

        def _band_phase(lo_f: float, hi_f: float) -> float:
            mask = (freqs >= lo_f) & (freqs < hi_f)
            if not np.any(mask):
                return 1.0
            return float(np.mean(phase_diff[mask]))

        phase_overall = float(np.mean(phase_diff))
        phase_low = _band_phase(20, 250)
        phase_mid = _band_phase(250, 4000)
        phase_high = _band_phase(4000, sr / 2)

    # ── Dynamic range per frequency band ──
    def _band_dr(lo_f: float, hi_f: float) -> float:
        """Dynamic range in a frequency band (p95-p5 of per-block energy)."""
        block_size = int(sr * 0.1)
        nb = n // block_size
        if nb < 4:
            return 0.0
        block_energies: list[float] = []
        for bi in range(nb):
            blk = mono[bi * block_size:(bi + 1) * block_size]
            if len(blk) < fft_size:
                continue
            bp = np.abs(rfft(blk[:fft_size] * window)) ** 2
            band_e = float(np.sum(bp[(freqs >= lo_f) & (freqs < hi_f)]))
            if band_e > 1e-20:
                block_energies.append(_db(math.sqrt(band_e)))
        if len(block_energies) < 4:
            return 0.0
        block_energies.sort()
        p5 = block_energies[max(0, len(block_energies) // 20)]
        p95 = block_energies[min(len(block_energies) - 1,
                                  len(block_energies) * 19 // 20)]
        return p95 - p5

    dr_low = _band_dr(20, 250)
    dr_mid = _band_dr(250, 4000)
    dr_high = _band_dr(4000, sr / 2)

    # ── Separation score: inverse of spectral flatness ──
    # Well-separated mix = distinct peaks, not flat
    separation = max(0.0, 1.0 - (
        float(np.exp(np.mean(np.log(avg_power + 1e-20))))
        / (float(np.mean(avg_power)) + 1e-10)
    ))

    return MixingDNA(
        headroom_db=round(headroom, 2),
        frequency_balance_score=round(freq_balance, 3),
        mud_ratio=round(min(mud_ratio, 5.0), 3),
        harshness_ratio=round(min(harshness, 5.0), 3),
        air_ratio=round(air_ratio, 4),
        phase_coherence=round(phase_overall, 3),
        phase_low=round(phase_low, 3),
        phase_mid=round(phase_mid, 3),
        phase_high=round(phase_high, 3),
        dynamic_range_low=round(dr_low, 2),
        dynamic_range_mid=round(dr_mid, 2),
        dynamic_range_high=round(dr_high, 2),
        separation_score=round(separation, 3),
        eq_curve=eq_curve,
    )


# ═══════════════════════════════════════════════════════════════════════════
# MASTERING ANALYSIS (Session 168)
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_mastering(mono: np.ndarray, left: np.ndarray,
                       right: np.ndarray, sr: int) -> MasteringDNA:
    """Mastering quality: true peak, ISP, clipping, loudness, stereo."""
    n = min(len(left), len(right))
    if n < 1024:
        return MasteringDNA()

    L = left[:n]
    R = right[:n]
    all_samples = np.concatenate([L, R])

    # ── True peak via 4x linear interpolation oversampling ──
    # Sinc interpolation approximation using linear interp of short blocks
    true_peak = 0.0
    for ch in (L, R):
        # Process in chunks for memory efficiency
        chunk_sz = min(len(ch), sr * 2)  # 2 seconds
        for start in range(0, len(ch), chunk_sz):
            chunk = ch[start:start + chunk_sz]
            # 4x upsample via linear interpolation
            x_orig = np.arange(len(chunk))
            x_up = np.linspace(0, len(chunk) - 1, len(chunk) * 4)
            upsampled = np.interp(x_up, x_orig, chunk)
            cp = float(np.max(np.abs(upsampled)))
            if cp > true_peak:
                true_peak = cp

    true_peak_db = _db(true_peak)

    # ── Inter-sample peak (ISP): peaks between samples ──
    # Use parabolic interpolation between adjacent samples
    isp = 0.0
    for ch in (L, R):
        for i in range(1, len(ch) - 1):
            a = abs(ch[i - 1])
            b = abs(ch[i])
            c = abs(ch[i + 1])
            if b >= a and b >= c and b > 0.9:
                # Parabolic interpolation to find true peak
                denom = a - 2 * b + c
                if abs(denom) > 1e-10:
                    peak_est = b - (a - c) ** 2 / (8 * denom)
                    if peak_est > isp:
                        isp = peak_est
            if i > sr * 5:  # cap search to 5 seconds for speed
                break
    isp_db = _db(isp) if isp > 1e-10 else true_peak_db

    # ── Clipping: samples at digital ceiling ──
    clip_threshold = 0.9999
    clipping = int(np.sum(np.abs(all_samples) >= clip_threshold))

    # ── Saturation: odd harmonics above 5 kHz vs total ──
    fft_size = min(8192, n)
    window = np.hanning(fft_size)
    freqs = rfftfreq(fft_size, 1.0 / sr)
    center = n // 2
    half = fft_size // 2
    chunk = mono[max(0, center - half):center + half]
    if len(chunk) < fft_size:
        chunk = np.pad(chunk, (0, fft_size - len(chunk)))
    spec = np.abs(rfft(chunk * window))

    high_odd = 0.0
    total_spec_e = float(np.sum(spec ** 2))
    for j, f in enumerate(freqs):
        if f > 5000:
            high_odd += spec[j] ** 2
    saturation = high_odd / (total_spec_e + 1e-10)

    # ── Loudness consistency: short-term LUFS variance ──
    block_size = int(sr * 0.4)  # 400ms blocks (EBU R128 short-term)
    n_blocks = n // block_size
    block_lufs: list[float] = []
    for i in range(max(n_blocks, 1)):
        blk = mono[i * block_size:(i + 1) * block_size]
        if len(blk) > 0:
            rms = float(np.sqrt(np.mean(blk ** 2)))
            if rms > 1e-10:
                block_lufs.append(_db(rms) - 0.7)
    loudness_consistency = 0.0
    if len(block_lufs) >= 4:
        loudness_consistency = float(np.std(block_lufs))

    # ── Limiting transparency ──
    # Low crest factor + many consecutive near-ceiling samples = crushed
    peak_db = _db(float(np.max(np.abs(all_samples))))
    rms_db = _db(float(np.sqrt(np.mean(mono ** 2))))
    crest = peak_db - rms_db
    # Transparency: 0=crushed (crest<3dB), 1=dynamic (crest>12dB)
    limiting_transparency = min(1.0, max(0.0, (crest - 3.0) / 9.0))

    # ── Stereo fold-down loss ──
    mono_sum = (L + R) * 0.5
    stereo_energy = float(np.mean(L ** 2) + np.mean(R ** 2))
    mono_energy = float(np.mean(mono_sum ** 2)) * 2  # compensate for sum
    if stereo_energy > 1e-10:
        fold_loss = max(0.0, _db(stereo_energy) - _db(mono_energy))
    else:
        fold_loss = 0.0

    # ── False stereo detection ──
    # Haas effect: L/R highly correlated but time-shifted
    # Check if one channel is a delayed version
    l_std = float(np.std(L))
    r_std = float(np.std(R))
    false_stereo = False
    if l_std > 1e-10 and r_std > 1e-10:
        cross_corr_max = 0.0
        # Check a few delay values
        for delay in [0, int(sr * 0.005), int(sr * 0.010),
                      int(sr * 0.020), int(sr * 0.030)]:
            if delay > 0 and delay < n:
                c = float(np.corrcoef(L[delay:delay + min(sr, n - delay)],
                                      R[:min(sr, n - delay)])[0, 1])
                cross_corr_max = max(cross_corr_max, abs(c))
        # At-zero correlation
        c0 = float(np.corrcoef(L[:min(sr, n)], R[:min(sr, n)])[0, 1])
        # False stereo if delayed version has much higher correlation
        if cross_corr_max > 0.95 and cross_corr_max > abs(c0) + 0.03:
            false_stereo = True

    # ── Dynamic complexity: number of significant loudness changes ──
    complexity = 0.0
    if len(block_lufs) >= 4:
        diffs = np.abs(np.diff(block_lufs))
        complexity = float(np.sum(diffs > 1.5)) / len(diffs)

    # ── Streaming loudness penalty ──
    lufs_est = rms_db - 0.7
    streaming_target = -14.0
    penalty = max(0.0, lufs_est - streaming_target)

    # ── DC offset ──
    dc = abs(float(np.mean(mono)))

    # ── Noise floor: quietest 100ms block ──
    nf_block = int(sr * 0.1)
    nf_blocks = n // nf_block
    noise_floor = -96.0
    if nf_blocks > 0:
        block_rms = []
        for i in range(nf_blocks):
            blk = mono[i * nf_block:(i + 1) * nf_block]
            rms_val = float(np.sqrt(np.mean(blk ** 2)))
            if rms_val > 1e-10:
                block_rms.append(_db(rms_val))
        if block_rms:
            noise_floor = min(block_rms)

    return MasteringDNA(
        true_peak_db=round(true_peak_db, 2),
        inter_sample_peak_db=round(isp_db, 2),
        clipping_samples=clipping,
        saturation_amount=round(min(saturation, 1.0), 4),
        loudness_consistency=round(loudness_consistency, 2),
        limiting_transparency=round(limiting_transparency, 3),
        stereo_fold_down_loss_db=round(fold_loss, 2),
        false_stereo=false_stereo,
        dynamic_complexity=round(complexity, 3),
        streaming_loudness_penalty=round(penalty, 2),
        dc_offset=round(dc, 6),
        noise_floor_db=round(noise_floor, 2),
    )


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY SCORING
# ═══════════════════════════════════════════════════════════════════════════

def _score_quality(analysis: ReferenceAnalysis,
                   genre: str = "dubstep") -> QualityScore:
    """Score a track against genre benchmarks."""
    bench = GENRE_BENCHMARKS.get(genre, DUBSTEP_BENCHMARK)
    notes: list[str] = []

    def _in_range(val: float, rng: tuple[float, float]) -> float:
        lo, hi = rng
        if lo <= val <= hi:
            return 1.0
        if val < lo:
            return max(0.0, 1.0 - (lo - val) / (abs(lo) + 1))
        return max(0.0, 1.0 - (val - hi) / (abs(hi) + 1))

    # Spectral balance score
    sp = analysis.spectral
    sp_scores: list[float] = []
    sp_bench = bench["spectral_balance"]
    for band, val in [("sub", sp.sub), ("bass", sp.bass),
                      ("low_mid", sp.low_mid), ("mid", sp.mid),
                      ("high_mid", sp.high_mid), ("high", sp.high)]:
        s = _in_range(val, sp_bench[band])
        sp_scores.append(s)
        if s < 0.5:
            lo, hi = sp_bench[band]
            if val < lo:
                notes.append(f"{band} too low ({val:.1%} vs {lo:.1%}-{hi:.1%})")
            else:
                notes.append(f"{band} too high ({val:.1%} vs {lo:.1%}-{hi:.1%})")
    spectral_score = float(np.mean(sp_scores))

    # Bass score
    bass_s = (_in_range(sp.sub + sp.bass, (0.30, 0.75))
              + min(analysis.bass.harmonic_ratio, 3.0) / 3.0
              + (1.0 if analysis.bass.wobble_rate_hz > 0 else 0.5)) / 3.0
    if analysis.bass.sub_weight < 0.05:
        notes.append("Very little sub bass energy")

    # Loudness score
    loud = analysis.loudness
    l_scores = [
        _in_range(loud.lufs_estimate, bench["lufs_range"]),
        1.0 if loud.peak_db <= bench["peak_db_max"] else 0.5,
        _in_range(loud.crest_factor_db, bench["crest_factor_db"]),
    ]
    loudness_score = float(np.mean(l_scores))
    if loud.lufs_estimate < bench["lufs_range"][0] - 3:
        notes.append(f"Too quiet ({loud.lufs_estimate:.1f} LUFS)")
    if loud.limiting_artifacts > 0.01:
        notes.append(f"Clipping detected ({loud.limiting_artifacts:.1%})")

    # Arrangement score
    arr = analysis.arrangement
    arr_s = (
        _in_range(arr.intro_drop_contrast_db,
                  bench["intro_drop_contrast_db"])
        + (1.0 if arr.drop_count >= 1 else 0.3)
        + min(arr.n_sections / 5.0, 1.0)
    ) / 3.0
    if arr.drop_count == 0:
        notes.append("No drop detected")

    # Dynamics score
    dynamics_score = _in_range(loud.dynamic_range_db,
                               bench["dynamic_range_db"])
    if loud.dynamic_range_db < 3.0:
        notes.append("Over-compressed (no dynamic range)")

    # Stereo score
    st = analysis.stereo
    stereo_score = (
        _in_range(st.width, bench["stereo_width"])
        + (1.0 if st.mono_compat > 0.5 else 0.5)
        + (1.0 if st.width_low < 0.15 else 0.5)  # bass should be mono
    ) / 3.0
    if st.width_low > 0.2:
        notes.append("Too much stereo width in bass (<250Hz)")

    # Production score
    prod = analysis.production
    prod_s = (
        min(prod.transient_sharpness * 2, 1.0)
        + (1.0 if prod.sidechain_depth_db > 2 else 0.5)
        + (1.0 - min(prod.distortion_amount * 5, 1.0))
    ) / 3.0

    # Style score (session 168)
    sty = analysis.style
    style_s = (
        sty.danceability * 0.3
        + sty.energy_level * 0.3
        + (1.0 if sty.bass_dominance > 0.3 else 0.5) * 0.2
        + min(sty.aggression + 0.3, 1.0) * 0.2
    )

    # Sound design score (session 168)
    sd = analysis.sound_design
    sd_s = (
        sd.attack_sharpness * 0.2
        + sd.texture_density * 0.2
        + min(sd.modulation_depth * 2, 1.0) * 0.2
        + (1.0 - sd.inharmonicity) * 0.2  # controlled inharmonicity
        + sd.spectral_movement * 0.2
    )

    # Mixing score (session 168)
    mx = analysis.mixing
    mx_s = (
        mx.frequency_balance_score * 0.25
        + (1.0 if mx.headroom_db >= 0.3 else 0.5) * 0.15
        + max(0.0, 1.0 - mx.mud_ratio / 3.0) * 0.15
        + max(0.0, 1.0 - mx.harshness_ratio / 3.0) * 0.15
        + min(mx.phase_low, 1.0) * 0.15  # bass phase coherence critical
        + mx.separation_score * 0.15
    )
    if mx.mud_ratio > 2.0:
        notes.append(f"Mud buildup (200-500Hz ratio: {mx.mud_ratio:.1f})")
    if mx.harshness_ratio > 2.5:
        notes.append(f"Harshness (2-5kHz ratio: {mx.harshness_ratio:.1f})")
    if mx.phase_low < 0.5:
        notes.append("Poor bass phase coherence")

    # Mastering score (session 168)
    ms = analysis.mastering
    ms_s = (
        ms.limiting_transparency * 0.25
        + (1.0 if ms.clipping_samples == 0 else 0.3) * 0.15
        + (1.0 if ms.true_peak_db <= -0.3 else 0.5) * 0.15
        + max(0.0, 1.0 - ms.streaming_loudness_penalty / 6.0) * 0.15
        + (1.0 if not ms.false_stereo else 0.3) * 0.10
        + max(0.0, 1.0 - ms.stereo_fold_down_loss_db / 3.0) * 0.10
        + ms.dynamic_complexity * 0.10
    )
    if ms.true_peak_db > -0.1:
        notes.append(f"True peak too hot ({ms.true_peak_db:.1f} dBTP)")
    if ms.clipping_samples > 0:
        notes.append(f"{ms.clipping_samples} clipped samples")
    if ms.streaming_loudness_penalty > 3.0:
        notes.append(
            f"Streaming penalty: -{ms.streaming_loudness_penalty:.1f} dB")
    if ms.false_stereo:
        notes.append("False stereo detected (Haas/delay)")

    # Weighted overall (rebalanced for 11 categories)
    overall = (
        spectral_score * 0.12
        + bass_s * 0.12
        + loudness_score * 0.10
        + arr_s * 0.10
        + dynamics_score * 0.08
        + stereo_score * 0.08
        + prod_s * 0.08
        + style_s * 0.08
        + sd_s * 0.08
        + mx_s * 0.08
        + ms_s * 0.08
    ) * 100

    return QualityScore(
        overall=round(overall, 1),
        spectral_score=round(spectral_score, 3),
        bass_score=round(bass_s, 3),
        loudness_score=round(loudness_score, 3),
        arrangement_score=round(arr_s, 3),
        dynamics_score=round(dynamics_score, 3),
        stereo_score=round(stereo_score, 3),
        production_score=round(prod_s, 3),
        style_score=round(style_s, 3),
        sound_design_score=round(sd_s, 3),
        mixing_score=round(mx_s, 3),
        mastering_score=round(ms_s, 3),
        notes=notes,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def analyze_reference(path: str,
                      genre: str = "dubstep",
                      max_duration_s: float = 600.0) -> ReferenceAnalysis:
    """
    Run complete DNA analysis on a WAV file.

    Returns a ReferenceAnalysis with all DNA sub-structures populated
    and quality scored against the specified genre benchmark.
    """
    import os

    left, right, sr, bit_depth = _load_wav(path)

    # Cap length (center-crop long files)
    max_samples = int(sr * max_duration_s)
    if len(left) > max_samples:
        start = (len(left) - max_samples) // 2
        left = left[start:start + max_samples]
        right = right[start:start + max_samples]

    mono = (left + right) * 0.5

    result = ReferenceAnalysis()
    result.filename = os.path.basename(path)
    result.path = str(path)
    result.sample_rate = sr
    result.channels = 2 if not np.array_equal(left, right) else 1
    result.bit_depth = bit_depth

    result.spectral = _analyze_spectral(mono, sr)
    result.rhythm = _analyze_rhythm(mono, sr)
    result.harmonic = _analyze_harmonic(mono, sr)
    result.loudness = _analyze_loudness(mono, left, right, sr)
    result.arrangement = _analyze_arrangement(mono, sr)
    result.stereo = _analyze_stereo(left, right, sr)
    result.bass = _analyze_bass(mono, sr)
    result.production = _analyze_production(mono, sr)
    # Session 168 additions (style depends on earlier DNA being populated)
    result.sound_design = _analyze_sound_design(mono, sr)
    result.mixing = _analyze_mixing(mono, left, right, sr)
    result.mastering = _analyze_mastering(mono, left, right, sr)
    result.style = _analyze_style(result)
    result.quality = _score_quality(result, genre)

    return result


def compare_to_benchmark(analysis: ReferenceAnalysis,
                         genre: str = "dubstep") -> dict[str, Any]:
    """
    Compare an analysis to genre benchmarks.
    Returns delta dict + cosine similarity of spectral vectors.
    """
    bench = GENRE_BENCHMARKS.get(genre, DUBSTEP_BENCHMARK)
    sp = analysis.spectral

    your_vec = np.array([sp.sub, sp.bass, sp.low_mid,
                         sp.mid, sp.high_mid, sp.high])
    bench_sp = bench["spectral_balance"]
    ref_vec = np.array([
        (bench_sp[b][0] + bench_sp[b][1]) / 2
        for b in ["sub", "bass", "low_mid", "mid", "high_mid", "high"]
    ])

    dot = float(np.dot(your_vec, ref_vec))
    n1 = float(np.linalg.norm(your_vec))
    n2 = float(np.linalg.norm(ref_vec))
    cosine_sim = dot / (n1 * n2) if (n1 > 1e-10 and n2 > 1e-10) else 0.0

    return {
        "genre": genre,
        "quality_score": analysis.quality.overall,
        "cosine_similarity": round(cosine_sim, 4),
        "bpm_in_range": (bench["bpm_range"][0]
                         <= analysis.rhythm.bpm
                         <= bench["bpm_range"][1]),
        "lufs_in_range": (bench["lufs_range"][0]
                          <= analysis.loudness.lufs_estimate
                          <= bench["lufs_range"][1]),
        "notes": analysis.quality.notes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBLE API (Session 166)
# ═══════════════════════════════════════════════════════════════════════════


def list_references() -> list[str]:
    """List available reference profiles."""
    return sorted(REFERENCE_PROFILES.keys())


def profile_from_signal(signal: list[float],
                        name: str = "Your Mix") -> TrackProfile:
    """Create a profile from a raw signal."""
    if not signal:
        return TrackProfile(name=name)

    n = len(signal)
    rms = math.sqrt(sum(s * s for s in signal) / n)
    peak = max(abs(s) for s in signal)
    rms_db = 20 * math.log10(max(rms, 1e-10))
    peak_db = 20 * math.log10(max(peak, 1e-10))
    crest = peak_db - rms_db

    zc = sum(1 for i in range(1, n) if signal[i] * signal[i - 1] < 0)
    zcr = zc / n
    avg_freq = zcr * SAMPLE_RATE / 2

    sub = max(0.0, 1.0 - avg_freq / 60) if avg_freq < 120 else 0.0
    bass_e = max(0.0, min(1.0, 1.0 - abs(avg_freq - 150) / 200))
    mid = max(0.0, min(1.0, 1.0 - abs(avg_freq - 1000) / 2000))
    high = max(0.0, (avg_freq - 3000) / 5000) if avg_freq > 3000 else 0.0

    chunk_size = max(1, n // 20)
    chunk_rms: list[float] = []
    for i in range(0, n - chunk_size, chunk_size):
        chunk = signal[i:i + chunk_size]
        cr = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        if cr > 1e-10:
            chunk_rms.append(20 * math.log10(cr))
    dr = max(chunk_rms) - min(chunk_rms) if chunk_rms else 0.0

    return TrackProfile(
        name=name, rms_db=rms_db, peak_db=peak_db,
        crest_factor_db=crest, sub_energy=sub,
        bass_energy=bass_e, mid_energy=mid,
        high_energy=high, dynamic_range_db=dr,
    )


def compare_to_reference(your_profile: TrackProfile,
                         ref_name: str = "subtronics"
                         ) -> ReferenceComparison:
    """Compare your profile to a reference."""
    ref = REFERENCE_PROFILES.get(ref_name)
    if not ref:
        ref = REFERENCE_PROFILES["subtronics"]
        ref_name = "subtronics"

    points: list[ComparisonPoint] = []
    total_score = 0.0
    n_metrics = 0

    metrics = [
        ("RMS Level", your_profile.rms_db, ref.rms_db, 3.0, "dB",
         "Adjust overall level"),
        ("Peak Level", your_profile.peak_db, ref.peak_db, 1.0, "dB",
         "Adjust limiter threshold"),
        ("Crest Factor", your_profile.crest_factor_db,
         ref.crest_factor_db, 3.0, "dB",
         "Adjust compression ratio"),
        ("Sub Energy", your_profile.sub_energy, ref.sub_energy, 0.2,
         "", "Adjust sub bass level"),
        ("Bass Energy", your_profile.bass_energy, ref.bass_energy, 0.2,
         "", "Adjust bass EQ 60-250Hz"),
        ("Mid Energy", your_profile.mid_energy, ref.mid_energy, 0.2,
         "", "Adjust mid EQ 250-4kHz"),
        ("High Energy", your_profile.high_energy, ref.high_energy, 0.2,
         "", "Adjust high EQ 4k+"),
        ("Dynamic Range", your_profile.dynamic_range_db,
         ref.dynamic_range_db, 4.0, "dB",
         "Adjust compressor settings"),
    ]

    for name, yours, theirs, tolerance, unit, suggestion in metrics:
        diff = yours - theirs
        abs_diff = abs(diff)

        if abs_diff <= tolerance * 0.5:
            severity = "ok"
            score = 1.0
        elif abs_diff <= tolerance:
            severity = "caution"
            score = 0.5
        else:
            severity = "problem"
            score = max(0.0, 1.0 - abs_diff / (tolerance * 2))

        direction = "higher" if diff > 0 else "lower"
        sug = f"{suggestion} ({abs_diff:.1f}{unit} {direction} than ref)"

        points.append(ComparisonPoint(
            metric=name, your_value=yours, ref_value=theirs,
            diff=round(diff, 2), severity=severity,
            suggestion=sug if severity != "ok" else "On target",
        ))
        total_score += score
        n_metrics += 1

    overall = (total_score / n_metrics * 100) if n_metrics > 0 else 0

    return ReferenceComparison(
        reference_name=ref_name,
        your_profile=your_profile,
        ref_profile=ref,
        points=points,
        overall_match=overall,
    )


def comparison_text(comp: ReferenceComparison) -> str:
    """Format comparison as readable text."""
    lines = [
        f"**Reference Comparison: {comp.reference_name.upper()}**",
        f"Overall Match: {comp.overall_match:.0f}%",
        "",
    ]
    for p in comp.points:
        icon = {"ok": "+", "caution": "~", "problem": "!"}[p.severity]
        lines.append(
            f"  [{icon}] {p.metric}: {p.your_value:.2f} "
            f"(ref: {p.ref_value:.2f}) — {p.suggestion}"
        )
    return "\n".join(lines)
