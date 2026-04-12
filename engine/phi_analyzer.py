"""
DUBFORGE — Phi Analyzer  (Session 123 · v3.6.0)

Measure phi-ratio presence in any .wav or numpy signal.
Score 0.0–1.0 "fractal coherence."

Analyses:
  harmonic_phi    — ratio of spectral peaks at phi-related intervals
  temporal_phi    — phi-ratio presence in envelope timing
  spectral_decay  — how energy decays by 1/phi across octaves
  phase_coherence — phase alignment at phi-ratio frequencies
  composite       — weighted blend of all four scores
"""

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
from engine.accel import fft, ifft
PHI_INV = 1.0 / PHI


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PhiScore:
    """Result of a phi coherence measurement."""
    harmonic_phi: float = 0.0       # 0-1
    temporal_phi: float = 0.0       # 0-1
    spectral_decay: float = 0.0     # 0-1
    phase_coherence: float = 0.0    # 0-1
    composite: float = 0.0          # weighted blend

    def as_dict(self) -> dict:
        return {
            "harmonic_phi": round(self.harmonic_phi, 4),
            "temporal_phi": round(self.temporal_phi, 4),
            "spectral_decay": round(self.spectral_decay, 4),
            "phase_coherence": round(self.phase_coherence, 4),
            "composite": round(self.composite, 4),
        }


@dataclass
class PhiAnalyzerPreset:
    name: str
    fft_size: int = 4096
    hop_size: int = 512
    min_freq: float = 20.0
    max_freq: float = 20000.0
    phi_tolerance: float = 0.02
    decay_octaves: int = 6
    weights: tuple = (0.35, 0.20, 0.25, 0.20)  # harm, temp, decay, phase


@dataclass
class PhiAnalyzerBank:
    name: str
    presets: list[PhiAnalyzerPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _get_spectrum(signal: np.ndarray, fft_size: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequencies, magnitudes) from FFT."""
    n = min(len(signal), fft_size)
    windowed = signal[:n] * np.hanning(n)
    spectrum = np.abs(fft(windowed, n=fft_size))
    freqs = np.fft.rfftfreq(fft_size, 1.0 / SAMPLE_RATE)
    return freqs, spectrum


def _find_peaks(mag: np.ndarray, threshold: float = 0.01) -> list[int]:
    """Simple peak detection."""
    peaks = []
    for i in range(1, len(mag) - 1):
        if mag[i] > mag[i - 1] and mag[i] > mag[i + 1] and mag[i] > threshold:
            peaks.append(i)
    return peaks


def measure_harmonic_phi(signal: np.ndarray, preset: PhiAnalyzerPreset) -> float:
    """Score how many spectral peak ratios approximate phi."""
    freqs, mag = _get_spectrum(signal, preset.fft_size)
    mag_norm = mag / (mag.max() + 1e-12)
    peak_indices = _find_peaks(mag_norm, 0.05)

    if len(peak_indices) < 2:
        return 0.0

    peak_freqs = freqs[peak_indices]
    peak_freqs = peak_freqs[(peak_freqs >= preset.min_freq) & (peak_freqs <= preset.max_freq)]

    if len(peak_freqs) < 2:
        return 0.0

    phi_count = 0
    total_pairs = 0
    for i in range(len(peak_freqs)):
        for j in range(i + 1, len(peak_freqs)):
            ratio = peak_freqs[j] / peak_freqs[i]
            # Check if ratio is close to phi or any power/root of phi
            for power in [1, 2, 3, 0.5]:
                target = PHI ** power
                if abs(ratio - target) / target < preset.phi_tolerance:
                    phi_count += 1
                    break
            total_pairs += 1

    return min(phi_count / max(total_pairs, 1) * 3.0, 1.0)  # scale up, cap at 1


def measure_temporal_phi(signal: np.ndarray, preset: PhiAnalyzerPreset) -> float:
    """Score phi-ratio presence in envelope timing (attack/decay/sustain)."""
    # Compute envelope via Hilbert-like approach (analytic signal approximation)
    n = len(signal)
    if n < preset.hop_size * 4:
        return 0.0

    hop = preset.hop_size
    envelope = np.array([np.sqrt(np.mean(signal[i:i + hop] ** 2))
                         for i in range(0, n - hop, hop)])

    if len(envelope) < 4:
        return 0.0

    # Find peak of envelope
    peak_idx = np.argmax(envelope)
    if peak_idx == 0 or peak_idx >= len(envelope) - 1:
        return 0.3  # flat signal gets partial credit

    # Attack = time to peak, decay = time from peak to 1/e of peak
    attack_len = peak_idx
    decay_env = envelope[peak_idx:]
    threshold = envelope[peak_idx] * PHI_INV
    decay_indices = np.where(decay_env < threshold)[0]
    decay_len = decay_indices[0] if len(decay_indices) > 0 else len(decay_env)

    if attack_len == 0 or decay_len == 0:
        return 0.2

    ratio = max(attack_len, decay_len) / min(attack_len, decay_len)
    # Score based on how close ratio is to phi
    deviation = abs(ratio - PHI) / PHI
    return max(0.0, 1.0 - deviation * 2)


def measure_spectral_decay(signal: np.ndarray, preset: PhiAnalyzerPreset) -> float:
    """Score how energy decays by 1/phi across octaves."""
    freqs, mag = _get_spectrum(signal, preset.fft_size)
    base_freq = preset.min_freq

    octave_energies = []
    for i in range(preset.decay_octaves):
        lo = base_freq * (2 ** i)
        hi = base_freq * (2 ** (i + 1))
        mask = (freqs >= lo) & (freqs < hi)
        energy = np.sum(mag[mask] ** 2) if np.any(mask) else 0.0
        octave_energies.append(energy)

    if len(octave_energies) < 2 or octave_energies[0] < 1e-12:
        return 0.0

    # Ideal: each octave is 1/phi of the previous
    score = 0.0
    count = 0
    for i in range(1, len(octave_energies)):
        if octave_energies[i - 1] < 1e-12:
            continue
        actual_ratio = octave_energies[i] / octave_energies[i - 1]
        ideal_ratio = PHI_INV
        deviation = abs(actual_ratio - ideal_ratio) / (ideal_ratio + 1e-12)
        score += max(0.0, 1.0 - deviation)
        count += 1

    return score / max(count, 1)


def measure_phase_coherence(signal: np.ndarray, preset: PhiAnalyzerPreset) -> float:
    """Score phase alignment at phi-ratio frequencies."""
    n = min(len(signal), preset.fft_size)
    windowed = signal[:n] * np.hanning(n)
    fft_result = fft(windowed, n=preset.fft_size)
    freqs = np.fft.rfftfreq(preset.fft_size, 1.0 / SAMPLE_RATE)
    phases = np.angle(fft_result)
    mag = np.abs(fft_result)

    # Find dominant frequency
    dominant_idx = np.argmax(mag[1:]) + 1
    if mag[dominant_idx] < 1e-12:
        return 0.0

    dominant_freq = freqs[dominant_idx]
    dominant_phase = phases[dominant_idx]

    # Check phases at phi-related frequencies
    phi_freqs = [dominant_freq * PHI, dominant_freq * PHI_INV,
                 dominant_freq * PHI ** 2, dominant_freq * PHI_INV ** 2]

    coherence_scores = []
    for pf in phi_freqs:
        idx = int(round(pf * preset.fft_size / SAMPLE_RATE))
        if 0 < idx < len(phases):
            phase_diff = abs(phases[idx] - dominant_phase) % (2 * np.pi)
            # Normalize to [0, pi]
            phase_diff = min(phase_diff, 2 * np.pi - phase_diff)
            # Score: 1.0 when in phase, 0.0 when out of phase
            coherence_scores.append(1.0 - phase_diff / np.pi)

    return float(np.mean(coherence_scores)) if coherence_scores else 0.0


def analyze_phi_coherence(signal: np.ndarray,
                          preset: PhiAnalyzerPreset | None = None) -> PhiScore:
    """Full phi coherence analysis of a signal."""
    if preset is None:
        preset = PhiAnalyzerPreset(name="default")

    h = measure_harmonic_phi(signal, preset)
    t = measure_temporal_phi(signal, preset)
    d = measure_spectral_decay(signal, preset)
    p = measure_phase_coherence(signal, preset)

    w = preset.weights
    composite = w[0] * h + w[1] * t + w[2] * d + w[3] * p

    return PhiScore(
        harmonic_phi=h,
        temporal_phi=t,
        spectral_decay=d,
        phase_coherence=p,
        composite=min(composite, 1.0),
    )


def analyze_wav_phi(wav_path: str,
                    preset: PhiAnalyzerPreset | None = None) -> PhiScore:
    """Analyse a .wav file for phi coherence."""
    p = Path(wav_path)
    if not p.exists():
        raise FileNotFoundError(wav_path)

    with wave.open(str(p), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    else:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return analyze_phi_coherence(samples, preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS  (5 × 4 = 20 presets)
# ═══════════════════════════════════════════════════════════════════════════

def standard_bank() -> PhiAnalyzerBank:
    return PhiAnalyzerBank("standard", [
        PhiAnalyzerPreset("std_4k", fft_size=4096),
        PhiAnalyzerPreset("std_8k", fft_size=8192),
        PhiAnalyzerPreset("std_tight", phi_tolerance=0.01),
        PhiAnalyzerPreset("std_loose", phi_tolerance=0.05),
    ])


def bass_focused_bank() -> PhiAnalyzerBank:
    return PhiAnalyzerBank("bass_focused", [
        PhiAnalyzerPreset("bass_sub", min_freq=20, max_freq=200),
        PhiAnalyzerPreset("bass_mid", min_freq=100, max_freq=1000),
        PhiAnalyzerPreset("bass_wide", min_freq=20, max_freq=2000),
        PhiAnalyzerPreset("bass_decay", decay_octaves=4, min_freq=20, max_freq=500),
    ])


def high_resolution_bank() -> PhiAnalyzerBank:
    return PhiAnalyzerBank("high_resolution", [
        PhiAnalyzerPreset("hires_16k", fft_size=16384),
        PhiAnalyzerPreset("hires_tight", fft_size=16384, phi_tolerance=0.005),
        PhiAnalyzerPreset("hires_256hop", fft_size=8192, hop_size=256),
        PhiAnalyzerPreset("hires_bass", fft_size=16384, min_freq=20, max_freq=500),
    ])


def harmonic_weighted_bank() -> PhiAnalyzerBank:
    return PhiAnalyzerBank("harmonic_weighted", [
        PhiAnalyzerPreset("harm_heavy", weights=(0.6, 0.1, 0.2, 0.1)),
        PhiAnalyzerPreset("temporal_heavy", weights=(0.1, 0.6, 0.1, 0.2)),
        PhiAnalyzerPreset("decay_heavy", weights=(0.1, 0.1, 0.6, 0.2)),
        PhiAnalyzerPreset("phase_heavy", weights=(0.1, 0.2, 0.2, 0.5)),
    ])


def production_bank() -> PhiAnalyzerBank:
    return PhiAnalyzerBank("production", [
        PhiAnalyzerPreset("prod_quick", fft_size=2048, hop_size=1024),
        PhiAnalyzerPreset("prod_master", fft_size=8192, phi_tolerance=0.015),
        PhiAnalyzerPreset("prod_full", fft_size=8192, decay_octaves=8),
        PhiAnalyzerPreset("prod_balanced", weights=(0.25, 0.25, 0.25, 0.25)),
    ])


ALL_PHI_ANALYZER_BANKS: dict[str, Callable[..., Any]] = {
    "standard": standard_bank,
    "bass_focused": bass_focused_bank,
    "high_resolution": high_resolution_bank,
    "harmonic_weighted": harmonic_weighted_bank,
    "production": production_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_phi_analyzer_manifest(output_dir: str = "output") -> dict:
    import json

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "phi_analyzer", "banks": {}}
    for name, gen_fn in ALL_PHI_ANALYZER_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "phi_analyzer_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def export_phi_scores(output_dir: str = "output") -> list[str]:
    """Score any .wav files in output/wavetables for phi coherence."""
    import json

    wav_dir = Path(output_dir) / "wavetables"
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    wav_files = sorted(wav_dir.rglob("*.wav"))[:20] if wav_dir.exists() else []

    for wf in wav_files:
        try:
            score = analyze_wav_phi(str(wf))
            result = {"file": str(wf), **score.as_dict()}
            rpath = out / f"{wf.stem}_phi_score.json"
            with open(rpath, "w") as fp:
                json.dump(result, fp, indent=2)
            paths.append(str(rpath))
        except Exception:
            pass

    return paths


def main() -> None:
    manifest = write_phi_analyzer_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    scores = export_phi_scores()
    print(f"Phi Analyzer: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(scores)} scores exported")


if __name__ == "__main__":
    main()
