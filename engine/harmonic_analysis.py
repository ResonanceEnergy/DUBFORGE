"""
DUBFORGE — Harmonic Analysis Engine

FFT-based spectral analysis, harmonic tracking, overtone analysis,
and phi-ratio harmonic detection.
5 types × 4 presets = 20 presets.

Types:
  spectral_peaks  — detect dominant frequencies via FFT peak picking
  harmonic_series — identify fundamental + overtone structure
  phi_detection   — detect phi-ratio relationships between partials
  spectral_flux   — track spectral change over time (onset detection)
  roughness       — sensory dissonance / roughness analysis
"""

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import fft, ifft
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisPreset:
    """Preset for harmonic analysis."""
    name: str
    analysis_type: str  # spectral_peaks | harmonic_series | phi_detection
                        # | spectral_flux | roughness
    # FFT
    fft_size: int = 4096
    hop_size: int = 512
    window_type: str = "hann"       # hann | hamming | blackman
    # Peak detection
    min_freq: float = 20.0
    max_freq: float = 20000.0
    peak_threshold_db: float = -40.0   # below max peak
    max_peaks: int = 20
    # Harmonic series
    fundamental_range: tuple = (30.0, 4000.0)
    max_harmonics: int = 16
    harmonic_tolerance: float = 0.03   # frequency tolerance ratio
    # Phi detection
    phi_tolerance: float = 0.02        # ±2% of phi ratio
    # Spectral flux
    flux_threshold: float = 0.1
    # Roughness
    roughness_bandwidth: float = 1.0   # critical bandwidth multiplier


@dataclass
class AnalysisBank:
    """Bank of analysis presets."""
    name: str
    presets: list[AnalysisPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS RESULTS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SpectralPeak:
    """A detected spectral peak."""
    frequency: float
    magnitude_db: float
    phase: float = 0.0
    bin_index: int = 0


@dataclass
class HarmonicSeries:
    """Detected harmonic series."""
    fundamental: float
    harmonics: list[SpectralPeak] = field(default_factory=list)
    inharmonicity: float = 0.0    # deviation from perfect harmonic ratios


@dataclass
class PhiRelation:
    """A pair of frequencies in phi ratio."""
    freq_low: float
    freq_high: float
    ratio: float
    deviation_from_phi: float


@dataclass
class SpectralFluxPoint:
    """Spectral flux at a time point."""
    time_sec: float
    flux_value: float
    is_onset: bool = False


@dataclass
class RoughnessResult:
    """Roughness analysis result."""
    total_roughness: float
    partial_pairs: list[tuple] = field(default_factory=list)
    # Each pair: (freq1, freq2, roughness_contribution)


# ═══════════════════════════════════════════════════════════════════════════
# WINDOW FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _get_window(window_type: str, size: int) -> np.ndarray:
    """Get analysis window."""
    if window_type == "hamming":
        return np.hamming(size)
    if window_type == "blackman":
        return np.blackman(size)
    return np.hanning(size)  # default: hann


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZERS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_spectral_peaks(signal: np.ndarray, preset: AnalysisPreset,
                           sample_rate: int = SAMPLE_RATE) -> list[SpectralPeak]:
    """
    Detect dominant frequencies via FFT peak picking.
    Returns sorted list of spectral peaks above threshold.
    """
    n = len(signal)
    if n == 0:
        return []

    # Window and FFT
    fft_size = min(preset.fft_size, n)
    window = _get_window(preset.window_type, fft_size)
    chunk = signal[:fft_size] * window
    spectrum = fft(chunk)
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sample_rate)
    magnitudes = np.abs(spectrum)
    phases = np.angle(spectrum)

    # Convert to dB
    mag_db = np.full_like(magnitudes, -120.0)
    mask = magnitudes > 1e-10
    mag_db[mask] = 20.0 * np.log10(magnitudes[mask])

    max_db = np.max(mag_db)
    threshold = max_db + preset.peak_threshold_db

    # Frequency range mask
    freq_mask = (freqs >= preset.min_freq) & (freqs <= preset.max_freq)

    # Peak picking — local maxima above threshold
    peaks = []
    for i in range(1, len(magnitudes) - 1):
        if not freq_mask[i]:
            continue
        if mag_db[i] < threshold:
            continue
        if mag_db[i] > mag_db[i - 1] and mag_db[i] > mag_db[i + 1]:
            peaks.append(SpectralPeak(
                frequency=freqs[i],
                magnitude_db=mag_db[i],
                phase=phases[i],
                bin_index=i,
            ))

    # Sort by magnitude and trim
    peaks.sort(key=lambda p: p.magnitude_db, reverse=True)
    return peaks[:preset.max_peaks]


def analyze_harmonic_series(signal: np.ndarray, preset: AnalysisPreset,
                            sample_rate: int = SAMPLE_RATE) -> list[HarmonicSeries]:
    """
    Identify fundamental frequencies and their overtone structures.
    Uses harmonic product spectrum for robust f0 detection.
    """
    n = len(signal)
    if n == 0:
        return []

    fft_size = min(preset.fft_size, n)
    window = _get_window(preset.window_type, fft_size)
    chunk = signal[:fft_size] * window
    spectrum = fft(chunk)
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sample_rate)
    magnitudes = np.abs(spectrum)

    # Harmonic Product Spectrum (HPS) for fundamental detection
    hps = magnitudes.copy()
    for h in range(2, min(6, len(magnitudes) // 2)):
        downsampled = magnitudes[::h][:len(hps)]
        hps[:len(downsampled)] *= downsampled

    # Find fundamental candidates
    fund_min_bin = max(1, int(preset.fundamental_range[0] * fft_size / sample_rate))
    fund_max_bin = min(len(hps) - 1,
                       int(preset.fundamental_range[1] * fft_size / sample_rate))

    # Get top candidates
    candidates_idx = np.argsort(hps[fund_min_bin:fund_max_bin + 1])[::-1]
    candidates_idx += fund_min_bin

    results = []
    used_funds = set()

    for fund_idx in candidates_idx[:5]:
        fund_freq = freqs[fund_idx]
        # Skip if too close to already-detected fundamental
        if any(abs(fund_freq - uf) < fund_freq * 0.05 for uf in used_funds):
            continue

        # Check for harmonic partials
        harmonics = []
        total_deviation = 0.0
        for h in range(1, preset.max_harmonics + 1):
            expected = fund_freq * h
            if expected > sample_rate / 2.0:
                break
            # Find nearest peak
            expected_bin = int(expected * fft_size / sample_rate)
            search_range = max(1, int(expected * preset.harmonic_tolerance
                                      * fft_size / sample_rate))
            lo = max(0, expected_bin - search_range)
            hi = min(len(magnitudes) - 1, expected_bin + search_range)
            if lo >= hi:
                continue
            local_peak = lo + np.argmax(magnitudes[lo:hi + 1])
            actual_freq = freqs[local_peak]
            deviation = abs(actual_freq - expected) / expected

            if deviation <= preset.harmonic_tolerance:
                mag_db = 20.0 * np.log10(max(1e-10, magnitudes[local_peak]))
                harmonics.append(SpectralPeak(
                    frequency=actual_freq,
                    magnitude_db=mag_db,
                    bin_index=int(local_peak),
                ))
                total_deviation += deviation

        if len(harmonics) >= 2:
            inharmonicity = total_deviation / len(harmonics)
            results.append(HarmonicSeries(
                fundamental=float(fund_freq),
                harmonics=harmonics,
                inharmonicity=inharmonicity,
            ))
            used_funds.add(fund_freq)

    return results


def analyze_phi_relations(signal: np.ndarray, preset: AnalysisPreset,
                          sample_rate: int = SAMPLE_RATE) -> list[PhiRelation]:
    """
    Detect phi-ratio (1.618...) relationships between spectral peaks.
    Sacred geometry in the frequency domain.
    """
    peaks = analyze_spectral_peaks(signal, preset, sample_rate)
    if len(peaks) < 2:
        return []

    relations = []
    for i, p1 in enumerate(peaks):
        for p2 in peaks[i + 1:]:
            lo = min(p1.frequency, p2.frequency)
            hi = max(p1.frequency, p2.frequency)
            if lo < 1.0:
                continue
            ratio = hi / lo
            # Check against phi and its powers
            for power in [0.5, 1.0, 2.0]:
                target = PHI ** power
                deviation = abs(ratio - target) / target
                if deviation <= preset.phi_tolerance:
                    relations.append(PhiRelation(
                        freq_low=lo,
                        freq_high=hi,
                        ratio=ratio,
                        deviation_from_phi=deviation,
                    ))

    relations.sort(key=lambda r: r.deviation_from_phi)
    return relations


def analyze_spectral_flux(signal: np.ndarray, preset: AnalysisPreset,
                          sample_rate: int = SAMPLE_RATE
                          ) -> list[SpectralFluxPoint]:
    """
    Track spectral change over time for onset detection.
    Measures frame-to-frame spectral difference.
    """
    n = len(signal)
    if n < preset.fft_size:
        return []

    window = _get_window(preset.window_type, preset.fft_size)
    flux_points = []
    prev_spectrum = None

    for start in range(0, n - preset.fft_size, preset.hop_size):
        chunk = signal[start:start + preset.fft_size] * window
        spectrum = np.abs(fft(chunk))

        if prev_spectrum is not None:
            # Half-wave rectified spectral difference
            diff = spectrum - prev_spectrum
            diff[diff < 0] = 0
            flux = np.sum(diff) / len(diff)

            time_sec = start / sample_rate
            is_onset = flux > preset.flux_threshold
            flux_points.append(SpectralFluxPoint(
                time_sec=time_sec,
                flux_value=flux,
                is_onset=is_onset,
            ))

        prev_spectrum = spectrum

    return flux_points


def analyze_roughness(signal: np.ndarray, preset: AnalysisPreset,
                      sample_rate: int = SAMPLE_RATE) -> RoughnessResult:
    """
    Calculate sensory dissonance / roughness using Plomp-Levelt model.
    Measures beating between close frequency partials.
    """
    peaks = analyze_spectral_peaks(signal, preset, sample_rate)
    if len(peaks) < 2:
        return RoughnessResult(total_roughness=0.0)

    total = 0.0
    pairs = []

    for i, p1 in enumerate(peaks):
        for p2 in peaks[i + 1:]:
            f1 = min(p1.frequency, p2.frequency)
            f2 = max(p1.frequency, p2.frequency)
            if f1 < 20.0:
                continue

            # Critical bandwidth (Bark scale approximation)
            f_mean = (f1 + f2) / 2.0
            cb = 25 + 75 * (1 + 1.4 * (f_mean / 1000.0) ** 2) ** 0.69
            cb *= preset.roughness_bandwidth

            # Normalised frequency difference
            s = (f2 - f1) / cb
            if s > 1.2:
                continue  # beyond critical band — no roughness

            # Plomp-Levelt roughness curve (simplified)
            a1 = 10.0 ** (p1.magnitude_db / 20.0)
            a2 = 10.0 ** (p2.magnitude_db / 20.0)
            amp_product = a1 * a2

            # Bell-shaped roughness function peaking at ~s=0.25
            r = amp_product * (
                np.exp(-3.5 * s * 0.24) - np.exp(-3.5 * s * 5.75)
            )
            r = max(0.0, r)
            total += r
            if r > 0:
                pairs.append((f1, f2, r))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return RoughnessResult(
        total_roughness=total,
        partial_pairs=pairs[:20],
    )


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def run_analysis(signal: np.ndarray, preset: AnalysisPreset,
                 sample_rate: int = SAMPLE_RATE) -> dict:
    """Route to the correct analysis based on preset type."""
    if preset.analysis_type == "spectral_peaks":
        peaks = analyze_spectral_peaks(signal, preset, sample_rate)
        return {
            "type": "spectral_peaks",
            "peak_count": len(peaks),
            "peaks": [{"freq": p.frequency, "mag_db": p.magnitude_db}
                      for p in peaks],
        }
    elif preset.analysis_type == "harmonic_series":
        series_list = analyze_harmonic_series(signal, preset, sample_rate)
        return {
            "type": "harmonic_series",
            "fundamentals_found": len(series_list),
            "series": [{
                "fundamental": s.fundamental,
                "num_harmonics": len(s.harmonics),
                "inharmonicity": s.inharmonicity,
            } for s in series_list],
        }
    elif preset.analysis_type == "phi_detection":
        relations = analyze_phi_relations(signal, preset, sample_rate)
        return {
            "type": "phi_detection",
            "phi_relations_found": len(relations),
            "relations": [{
                "freq_low": r.freq_low,
                "freq_high": r.freq_high,
                "ratio": r.ratio,
                "deviation": r.deviation_from_phi,
            } for r in relations],
        }
    elif preset.analysis_type == "spectral_flux":
        flux = analyze_spectral_flux(signal, preset, sample_rate)
        onsets = [f for f in flux if f.is_onset]
        return {
            "type": "spectral_flux",
            "total_frames": len(flux),
            "onset_count": len(onsets),
            "onset_times": [o.time_sec for o in onsets],
        }
    elif preset.analysis_type == "roughness":
        result = analyze_roughness(signal, preset, sample_rate)
        return {
            "type": "roughness",
            "total_roughness": result.total_roughness,
            "num_rough_pairs": len(result.partial_pairs),
        }
    else:
        raise ValueError(f"Unknown analysis type: {preset.analysis_type}")


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def spectral_peaks_bank() -> AnalysisBank:
    return AnalysisBank("spectral_peaks", [
        AnalysisPreset("peaks_default", "spectral_peaks"),
        AnalysisPreset("peaks_hires", "spectral_peaks", fft_size=8192,
                       max_peaks=40),
        AnalysisPreset("peaks_bass", "spectral_peaks", min_freq=20.0,
                       max_freq=200.0, peak_threshold_db=-30.0),
        AnalysisPreset("peaks_presence", "spectral_peaks", min_freq=1000.0,
                       max_freq=8000.0, peak_threshold_db=-35.0),
    ])


def harmonic_series_bank() -> AnalysisBank:
    return AnalysisBank("harmonic_series", [
        AnalysisPreset("hs_default", "harmonic_series"),
        AnalysisPreset("hs_bass_focus", "harmonic_series",
                       fundamental_range=(30.0, 200.0), max_harmonics=8),
        AnalysisPreset("hs_wide", "harmonic_series",
                       fundamental_range=(50.0, 8000.0), max_harmonics=24),
        AnalysisPreset("hs_phi_tuned", "harmonic_series",
                       harmonic_tolerance=1.0 / (PHI * 20),
                       max_harmonics=int(PHI * 10)),
    ])


def phi_detection_bank() -> AnalysisBank:
    return AnalysisBank("phi_detection", [
        AnalysisPreset("phi_strict", "phi_detection", phi_tolerance=0.01),
        AnalysisPreset("phi_relaxed", "phi_detection", phi_tolerance=0.05),
        AnalysisPreset("phi_bass", "phi_detection", phi_tolerance=0.02,
                       min_freq=30.0, max_freq=500.0),
        AnalysisPreset("phi_full_range", "phi_detection", phi_tolerance=0.02,
                       min_freq=20.0, max_freq=16000.0, max_peaks=40),
    ])


def spectral_flux_bank() -> AnalysisBank:
    return AnalysisBank("spectral_flux", [
        AnalysisPreset("flux_default", "spectral_flux"),
        AnalysisPreset("flux_sensitive", "spectral_flux",
                       flux_threshold=0.05, hop_size=256),
        AnalysisPreset("flux_coarse", "spectral_flux",
                       flux_threshold=0.2, hop_size=1024),
        AnalysisPreset("flux_phi_hop", "spectral_flux",
                       hop_size=int(512 / PHI), flux_threshold=0.1),
    ])


def roughness_bank() -> AnalysisBank:
    return AnalysisBank("roughness", [
        AnalysisPreset("rough_default", "roughness"),
        AnalysisPreset("rough_narrow", "roughness", roughness_bandwidth=0.5),
        AnalysisPreset("rough_wide", "roughness", roughness_bandwidth=2.0),
        AnalysisPreset("rough_phi_bw", "roughness",
                       roughness_bandwidth=1.0 / PHI),
    ])


ALL_ANALYSIS_BANKS: dict[str, Callable[..., Any]] = {
    "spectral_peaks": spectral_peaks_bank,
    "harmonic_series": harmonic_series_bank,
    "phi_detection": phi_detection_bank,
    "spectral_flux": spectral_flux_bank,
    "roughness": roughness_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_harmonic_analysis_manifest(output_dir: str = "output") -> dict:
    """Write JSON manifest of all harmonic analysis presets."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_ANALYSIS_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "harmonic_analysis_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# WAV ANALYSIS  (Session 121)
# ═══════════════════════════════════════════════════════════════════════════

def analyze_wav_file(wav_path: str, analysis_type: str = "spectral_peaks",
                     preset: AnalysisPreset | None = None) -> dict:
    """Analyse a .wav file and return results as a dict.

    Parameters
    ----------
    wav_path : str
        Path to a .wav file (mono or stereo, 16-bit or float).
    analysis_type : str
        One of the five analysis types.
    preset : AnalysisPreset, optional
        Override preset.  Defaults to the first preset in the matching bank.

    Returns
    -------
    dict  with keys: ``file``, ``analysis_type``, ``sample_rate``, ``duration_s``,
    ``results`` (analysis-specific).
    """
    import wave
    from pathlib import Path as _Path

    p = _Path(wav_path)
    if not p.exists():
        raise FileNotFoundError(wav_path)

    with wave.open(str(p), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0

    # Mix to mono if needed
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    if preset is None:
        bank_fn = ALL_ANALYSIS_BANKS.get(analysis_type)
        if bank_fn is None:
            raise ValueError(f"Unknown analysis_type: {analysis_type}")
        bank = bank_fn()
        preset = bank.presets[0]

    result_obj = run_analysis(samples, preset)  # type: ignore[arg-type]

    # Convert result to serialisable dict
    def _to_dict(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _to_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
        if isinstance(obj, (list, tuple)):
            return [_to_dict(v) for v in obj]
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        return obj

    return {
        "file": str(p),
        "analysis_type": analysis_type,
        "sample_rate": sr,
        "duration_s": round(n_frames / sr, 4),
        "preset": preset.name,
        "results": _to_dict(result_obj),
    }


def export_analysis_reports(output_dir: str = "output") -> list[str]:
    """Generate analysis JSON reports for any .wav files in output/wavetables."""
    import json
    from pathlib import Path as _Path

    wav_dir = _Path(output_dir) / "wavetables"
    out = _Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    # Gather up to 20 .wav files to analyse
    wav_files = sorted(wav_dir.rglob("*.wav"))[:20] if wav_dir.exists() else []

    for wf in wav_files:
        for atype in ["spectral_peaks", "phi_detection"]:
            try:
                report = analyze_wav_file(str(wf), atype)
                fname = f"{wf.stem}_{atype}.json"
                rpath = out / fname
                with open(rpath, "w") as fp:
                    json.dump(report, fp, indent=2)
                paths.append(str(rpath))
            except Exception:
                pass  # skip unreadable or tiny files

    return paths


def main() -> None:
    manifest = write_harmonic_analysis_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())

    reports = export_analysis_reports()
    print(f"Harmonic Analysis: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(reports)} analysis reports")


if __name__ == "__main__":
    main()
