"""
DUBFORGE Engine — Riser Synth

Riser/sweep generator for build-ups and transitions. Five riser types:
noise_sweep, pitch_rise, filter_sweep, harmonic_build, reverse_swell —
all governed by phi/Fibonacci doctrine.

Outputs:
    output/wavetables/riser_*.wav
    output/analysis/riser_synth_manifest.json
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

logger = get_logger(__name__)


@dataclass
class RiserPreset:
    """Configuration for a riser synthesis patch."""
    name: str
    riser_type: str  # noise_sweep | pitch_rise | filter_sweep | harmonic_build | reverse_swell
    duration_s: float = 4.0
    start_freq: float = 100.0
    end_freq: float = 4000.0
    brightness: float = 0.7
    intensity: float = 0.8
    distortion: float = 0.0
    reverb_amount: float = 0.3


@dataclass
class RiserBank:
    """A named collection of riser presets."""
    name: str
    presets: list[RiserPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _normalize(signal: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(signal))
    if peak > 0:
        return signal / peak * 0.95
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_noise_sweep(preset: RiserPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Noise sweep riser — filtered noise rising in frequency."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(n)

    # Sweeping low-pass filter using simple IIR
    cutoff_curve = np.linspace(preset.start_freq, preset.end_freq, n)
    signal = np.zeros(n)
    y = 0.0
    for i in range(n):
        alpha = min(0.99, cutoff_curve[i] / sample_rate * 2 * math.pi)
        y = y * (1 - alpha) + noise[i] * alpha
        signal[i] = y

    # Rising amplitude envelope
    env = np.linspace(0.1, 1.0, n) ** preset.intensity
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))
    return _normalize(signal)


def synthesize_pitch_rise(preset: RiserPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Pitch rise — oscillator sweeping upward in frequency."""
    n = int(preset.duration_s * sample_rate)

    # Exponential frequency sweep
    freq_curve = preset.start_freq * (preset.end_freq / max(1, preset.start_freq)) ** (
        np.arange(n) / max(1, n - 1))
    phase = np.cumsum(2 * math.pi * freq_curve / sample_rate)
    signal = np.sin(phase)

    # Add harmonics for brightness
    if preset.brightness > 0.3:
        signal += preset.brightness * 0.4 * np.sin(phase * 2)
        signal += preset.brightness * 0.15 * np.sin(phase * 3)

    # Rising envelope
    env = np.linspace(0.2, 1.0, n) ** preset.intensity
    attack_n = max(1, int(0.01 * sample_rate))
    env[:attack_n] *= np.linspace(0, 1, attack_n)
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


def synthesize_filter_sweep(preset: RiserPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Filter sweep — static tone with rising filter cutoff."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Rich harmonically complex source
    freq = preset.start_freq
    signal = np.sin(2 * math.pi * freq * t)
    for h in range(2, 12):
        amp = 0.7 / h
        signal += amp * np.sin(2 * math.pi * freq * h * t)

    # Sweeping filter
    cutoff_curve = np.linspace(200, preset.end_freq, n)
    filtered = np.zeros(n)
    y1 = 0.0
    y2 = 0.0
    for i in range(n):
        alpha = min(0.99, cutoff_curve[i] / sample_rate * 2 * math.pi)
        y1 = y1 * (1 - alpha) + signal[i] * alpha
        y2 = y2 * (1 - alpha * 0.5) + y1 * alpha * 0.5
        filtered[i] = y2

    env = np.linspace(0.3, 1.0, n) ** 0.7
    filtered *= env

    if preset.distortion > 0:
        filtered = np.tanh(filtered * (1 + preset.distortion * 4))
    return _normalize(filtered)


def synthesize_harmonic_build(preset: RiserPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Harmonic build — harmonics added progressively over time."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    signal = np.zeros(n)

    freq = preset.start_freq
    max_harmonics = int(8 + preset.brightness * 8)

    for h in range(1, max_harmonics + 1):
        h_freq = freq * h
        if h_freq > sample_rate / 2:
            break
        # Each harmonic fades in progressively later
        fade_start = int(n * (h - 1) / max_harmonics)
        fade_len = max(1, int(n * 0.3))
        harmonic = np.sin(2 * math.pi * h_freq * t) / h
        h_env = np.zeros(n)
        end = min(n, fade_start + fade_len)
        h_env[fade_start:end] = np.linspace(0, 1, end - fade_start)
        if end < n:
            h_env[end:] = 1.0
        signal += harmonic * h_env

    # Overall rising envelope
    env = np.linspace(0.15, 1.0, n) ** preset.intensity
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))
    return _normalize(signal)


def synthesize_reverse_swell(preset: RiserPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Reverse swell — reversed cymbal/noise texture building upward."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(66)

    # Base: bright noise
    noise = rng.standard_normal(n)

    # Metallic resonance via comb filter
    delay = max(1, int(sample_rate / max(preset.start_freq, 20)))
    signal = np.zeros(n)
    for i in range(n):
        fb = signal[i - delay] if i >= delay else 0.0
        signal[i] = noise[i] * 0.3 + 0.6 * fb

    # Brightness filter
    alpha = preset.brightness * 0.5 + 0.01
    y = 0.0
    for i in range(n):
        y = y * (1 - alpha) + signal[i] * alpha
        signal[i] = y

    # Reverse swell envelope: exponential rise
    env = np.exp(np.linspace(-4 * preset.intensity, 0, n))
    signal *= env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# v2.4 SYNTHESIZERS — fm_riser, granular_riser, doppler
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_fm_riser(preset: RiserPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """FM riser — FM modulation index rises over time."""
    n = int(preset.duration_s * sample_rate)
    # Carrier frequency sweeps up
    freq_curve = np.linspace(preset.start_freq, preset.end_freq, n)
    # Modulation index rises with intensity
    mod_index = np.linspace(0.0, preset.intensity * 8, n)
    mod_freq = freq_curve * 2  # modulator at 2x carrier
    mod_signal = mod_index * np.sin(2 * math.pi * np.cumsum(mod_freq / sample_rate))
    phase = np.cumsum(2 * math.pi * (freq_curve + mod_signal) / sample_rate)
    signal = np.sin(phase)
    # Add brightness harmonics
    if preset.brightness > 0.3:
        signal += preset.brightness * 0.3 * np.sin(phase * 2)
    # Rising envelope
    env = np.linspace(0.1, 1.0, n) ** preset.intensity
    signal *= env
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


def synthesize_granular_riser(preset: RiserPreset,
                              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Granular riser — grain density builds up over time."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(88)
    signal = np.zeros(n)
    grain_ms = 30
    grain_n = max(1, int(grain_ms * sample_rate / 1000))
    env_grain = np.hanning(grain_n)
    total_grains = int(preset.intensity * n / grain_n * 2)
    for g in range(total_grains):
        # Grains cluster toward the end for build-up effect
        progress = (g / max(1, total_grains - 1)) ** 0.5
        center = int(progress * (n - grain_n))
        pos = max(0, min(n - grain_n, center + rng.integers(-grain_n, grain_n)))
        freq = preset.start_freq + (preset.end_freq - preset.start_freq) * progress
        freq *= 2 ** (rng.uniform(-0.5, 0.5) / 12)
        t_grain = np.arange(grain_n) / sample_rate
        grain = np.sin(2 * math.pi * freq * t_grain) * env_grain
        if preset.brightness > 0.4:
            grain += preset.brightness * 0.3 * np.sin(4 * math.pi * freq * t_grain) * env_grain
        end = min(pos + grain_n, n)
        signal[pos:end] += grain[:end - pos]
    # Rising master envelope
    env = np.linspace(0.05, 1.0, n) ** 0.7
    signal *= env
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


def synthesize_doppler(preset: RiserPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Doppler riser — frequency Doppler effect rise."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    # Doppler curve: accelerating frequency shift
    progress = (t / preset.duration_s) ** 2
    freq_curve = preset.start_freq + (preset.end_freq - preset.start_freq) * progress
    phase = np.cumsum(2 * math.pi * freq_curve / sample_rate)
    signal = np.sin(phase)
    # Add harmonics that also Doppler-shift
    if preset.brightness > 0.3:
        signal += preset.brightness * 0.4 * np.sin(phase * 1.5)
        signal += preset.brightness * 0.2 * np.sin(phase * 3)
    # Amplitude rises with approach
    amp_curve = np.linspace(0.1, 1.0, n) ** preset.intensity
    signal *= amp_curve
    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))
    return _normalize(signal)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════


def synthesize_riser(preset: RiserPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct riser synthesizer."""
    synthesizers = {
        "noise_sweep": synthesize_noise_sweep,
        "pitch_rise": synthesize_pitch_rise,
        "filter_sweep": synthesize_filter_sweep,
        "harmonic_build": synthesize_harmonic_build,
        "reverse_swell": synthesize_reverse_swell,
        "fm_riser": synthesize_fm_riser,
        "granular_riser": synthesize_granular_riser,
        "doppler": synthesize_doppler,
    }
    fn = synthesizers.get(preset.riser_type)
    if fn is None:
        raise ValueError(f"Unknown riser_type: {preset.riser_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 presets = 20
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_BPM = 150
bar_s = 4 * 60 / DEFAULT_BPM


def noise_sweep_bank() -> RiserBank:
    """Noise sweep risers — filtered noise building upward."""
    return RiserBank(
        name="NOISE_SWEEPS",
        presets=[
            RiserPreset("nsweep_4bar", "noise_sweep", duration_s=4 * bar_s,
                        start_freq=200, end_freq=8000, brightness=0.7),
            RiserPreset("nsweep_8bar", "noise_sweep", duration_s=8 * bar_s,
                        start_freq=100, end_freq=12000, brightness=0.8),
            RiserPreset("nsweep_2bar_bright", "noise_sweep", duration_s=2 * bar_s,
                        start_freq=500, end_freq=16000, brightness=0.9, intensity=0.9),
            RiserPreset("nsweep_16bar_slow", "noise_sweep", duration_s=16 * bar_s,
                        start_freq=80, end_freq=6000, brightness=0.5, intensity=0.6),
        ],
    )


def pitch_rise_bank() -> RiserBank:
    """Pitch rise — oscillator sweeping upward."""
    return RiserBank(
        name="PITCH_RISES",
        presets=[
            RiserPreset("prise_4bar", "pitch_rise", duration_s=4 * bar_s,
                        start_freq=100, end_freq=2000, brightness=0.6),
            RiserPreset("prise_8bar_wide", "pitch_rise", duration_s=8 * bar_s,
                        start_freq=50, end_freq=4000, brightness=0.7, intensity=0.9),
            RiserPreset("prise_2bar_tight", "pitch_rise", duration_s=2 * bar_s,
                        start_freq=200, end_freq=1000, brightness=0.5),
            RiserPreset("prise_16bar_epic", "pitch_rise", duration_s=16 * bar_s,
                        start_freq=40, end_freq=6000, brightness=0.8, intensity=0.7),
        ],
    )


def filter_sweep_bank() -> RiserBank:
    """Filter sweep — static tone with rising filter."""
    return RiserBank(
        name="FILTER_SWEEPS",
        presets=[
            RiserPreset("fsweep_C3_4bar", "filter_sweep", duration_s=4 * bar_s,
                        start_freq=130.81, end_freq=8000, brightness=0.7),
            RiserPreset("fsweep_E2_8bar", "filter_sweep", duration_s=8 * bar_s,
                        start_freq=82.41, end_freq=12000, brightness=0.6),
            RiserPreset("fsweep_A2_2bar", "filter_sweep", duration_s=2 * bar_s,
                        start_freq=110.0, end_freq=6000, brightness=0.8, distortion=0.2),
            RiserPreset("fsweep_G2_16bar", "filter_sweep", duration_s=16 * bar_s,
                        start_freq=98.0, end_freq=10000, brightness=0.5),
        ],
    )


def harmonic_build_bank() -> RiserBank:
    """Harmonic build — harmonics added progressively."""
    return RiserBank(
        name="HARMONIC_BUILDS",
        presets=[
            RiserPreset("hbuild_C3_4bar", "harmonic_build", duration_s=4 * bar_s,
                        start_freq=130.81, brightness=0.7, intensity=0.8),
            RiserPreset("hbuild_E2_8bar", "harmonic_build", duration_s=8 * bar_s,
                        start_freq=82.41, brightness=0.8, intensity=0.6),
            RiserPreset("hbuild_A2_2bar", "harmonic_build", duration_s=2 * bar_s,
                        start_freq=110.0, brightness=0.9, intensity=0.9),
            RiserPreset("hbuild_D3_16bar", "harmonic_build", duration_s=16 * bar_s,
                        start_freq=146.83, brightness=0.6, intensity=0.5),
        ],
    )


def reverse_swell_bank() -> RiserBank:
    """Reverse swell — reversed cymbal/noise textures."""
    return RiserBank(
        name="REVERSE_SWELLS",
        presets=[
            RiserPreset("rswell_4bar", "reverse_swell", duration_s=4 * bar_s,
                        start_freq=400, brightness=0.7, intensity=1.0),
            RiserPreset("rswell_8bar", "reverse_swell", duration_s=8 * bar_s,
                        start_freq=300, brightness=0.6, intensity=0.8),
            RiserPreset("rswell_2bar_bright", "reverse_swell", duration_s=2 * bar_s,
                        start_freq=600, brightness=0.9, intensity=1.2),
            RiserPreset("rswell_1bar_short", "reverse_swell", duration_s=bar_s,
                        start_freq=500, brightness=0.8, intensity=1.5),
        ],
    )


def fm_riser_bank() -> RiserBank:
    """FM riser — FM modulation building upward."""
    return RiserBank(
        name="FM_RISERS",
        presets=[
            RiserPreset("fm_riser_4bar", "fm_riser", duration_s=6.4,
                        start_freq=200, end_freq=8000, brightness=0.7, intensity=0.8),
            RiserPreset("fm_riser_8bar", "fm_riser", duration_s=12.8,
                        start_freq=100, end_freq=12000, brightness=0.8, intensity=0.6),
            RiserPreset("fm_riser_2bar", "fm_riser", duration_s=3.2,
                        start_freq=300, end_freq=10000, brightness=0.9, intensity=0.9),
            RiserPreset("fm_riser_16bar", "fm_riser", duration_s=25.6,
                        start_freq=80, end_freq=6000, brightness=0.5, intensity=0.5),
        ],
    )


def granular_riser_bank() -> RiserBank:
    """Granular riser — grain density build-ups."""
    return RiserBank(
        name="GRANULAR_RISERS",
        presets=[
            RiserPreset("gran_riser_4bar", "granular_riser", duration_s=6.4,
                        start_freq=150, end_freq=6000, brightness=0.7, intensity=0.8),
            RiserPreset("gran_riser_8bar", "granular_riser", duration_s=12.8,
                        start_freq=100, end_freq=10000, brightness=0.6, intensity=0.7),
            RiserPreset("gran_riser_2bar", "granular_riser", duration_s=3.2,
                        start_freq=200, end_freq=8000, brightness=0.8, intensity=0.9),
            RiserPreset("gran_riser_1bar", "granular_riser", duration_s=1.6,
                        start_freq=300, end_freq=12000, brightness=0.9, intensity=1.0),
        ],
    )


def doppler_riser_bank() -> RiserBank:
    """Doppler riser — accelerating frequency approach."""
    return RiserBank(
        name="DOPPLER_RISERS",
        presets=[
            RiserPreset("doppler_4bar", "doppler", duration_s=6.4,
                        start_freq=200, end_freq=4000, brightness=0.7, intensity=0.8),
            RiserPreset("doppler_8bar", "doppler", duration_s=12.8,
                        start_freq=100, end_freq=8000, brightness=0.6, intensity=0.7),
            RiserPreset("doppler_2bar", "doppler", duration_s=3.2,
                        start_freq=400, end_freq=6000, brightness=0.8, intensity=0.9),
            RiserPreset("doppler_16bar", "doppler", duration_s=25.6,
                        start_freq=80, end_freq=3000, brightness=0.5, intensity=0.5),
        ],
    )


ALL_RISER_BANKS: dict[str, callable] = {
    "noise_sweeps":    noise_sweep_bank,
    "pitch_rises":     pitch_rise_bank,
    "filter_sweeps":   filter_sweep_bank,
    "harmonic_builds": harmonic_build_bank,
    "reverse_swells":  reverse_swell_bank,
    # v2.4
    "fm_risers":       fm_riser_bank,
    "granular_risers":  granular_riser_bank,
    "doppler_risers":   doppler_riser_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════


def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def write_riser_manifest(output_dir: str = "output") -> dict:
    """Generate all riser presets, write WAVs, and save manifest."""
    base = Path(output_dir)
    manifest: dict = {"module": "riser_synth", "banks": {}}

    for bank_key, bank_fn in ALL_RISER_BANKS.items():
        bank = bank_fn()
        bank_info: list[dict] = []
        for preset in bank.presets:
            audio = synthesize_riser(preset)
            wav_path = base / "wavetables" / f"riser_{preset.name}.wav"
            _write_wav(wav_path, audio)
            bank_info.append({
                "name": preset.name,
                "riser_type": preset.riser_type,
                "duration_s": preset.duration_s,
                "wav": str(wav_path),
            })
        manifest["banks"][bank_key] = {
            "name": bank.name,
            "presets": bank_info,
        }

    manifest_path = base / "analysis" / "riser_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Riser manifest → %s", manifest_path)
    return manifest


def main() -> None:
    """Entry point for riser_synth module."""
    logger.info("=== DUBFORGE Riser Synth ===")
    manifest = write_riser_manifest()
    total = sum(len(b["presets"]) for b in manifest["banks"].values())
    logger.info("Generated %d riser presets across %d banks",
                total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
