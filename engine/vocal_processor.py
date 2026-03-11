"""
DUBFORGE — Vocal Processor

Pitch correction, vocoder, formant shifting, and vocal effects.
5 types × 4 presets = 20 presets.

Types:
  pitch_correct  — auto-tune style pitch snapping to scale
  vocoder        — carrier/modulator vocoder synthesis
  formant_shift  — shift formants independently of pitch
  harmonizer     — add harmonised copies at phi-ratio intervals
  telephone      — band-pass + saturation lo-fi vocal effect
"""

from dataclasses import dataclass, field

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI, A4_432, A4_440
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VocalPreset:
    """Preset for vocal processing."""
    name: str
    vocal_type: str  # pitch_correct | vocoder | formant_shift | harmonizer | telephone
    # Pitch correction
    scale_root: int = 0            # 0=C, 1=C#, ...11=B
    correction_speed: float = 0.8  # 0=slow/natural .. 1=hard-snap
    # Vocoder
    num_bands: int = 16
    band_q: float = 5.0
    carrier_freq: float = 110.0    # base carrier for vocoder
    # Formant shift
    shift_semitones: float = 0.0   # formant shift amount
    # Harmonizer
    harmony_intervals: list = field(default_factory=lambda: [3, 5])
    harmony_mix: float = 0.4
    # Telephone
    lo_cut_hz: float = 300.0
    hi_cut_hz: float = 3400.0
    saturation: float = 0.5
    # Common
    mix: float = 1.0


@dataclass
class VocalBank:
    """Bank of vocal processor presets."""
    name: str
    presets: list[VocalPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _simple_biquad_bp(signal: np.ndarray, center_hz: float,
                      q: float, sr: int) -> np.ndarray:
    """2nd-order band-pass biquad filter."""
    w0 = 2.0 * np.pi * center_hz / sr
    alpha = np.sin(w0) / (2.0 * q)
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * np.cos(w0)
    a2 = 1.0 - alpha
    # Normalize
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0, a1 / a0, a2 / a0])
    out = np.zeros_like(signal)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(signal)):
        x0 = signal[i]
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


def _simple_biquad_lp(signal: np.ndarray, cutoff_hz: float,
                      q: float, sr: int) -> np.ndarray:
    """2nd-order low-pass biquad filter."""
    w0 = 2.0 * np.pi * cutoff_hz / sr
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b0 = (1.0 - cos_w0) / 2.0
    b1 = 1.0 - cos_w0
    b2 = (1.0 - cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0, a1 / a0, a2 / a0])
    out = np.zeros_like(signal)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(signal)):
        x0 = signal[i]
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


def _simple_biquad_hp(signal: np.ndarray, cutoff_hz: float,
                      q: float, sr: int) -> np.ndarray:
    """2nd-order high-pass biquad filter."""
    w0 = 2.0 * np.pi * cutoff_hz / sr
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0, a1 / a0, a2 / a0])
    out = np.zeros_like(signal)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(signal)):
        x0 = signal[i]
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


def _soft_clip(signal: np.ndarray, drive: float = 1.0) -> np.ndarray:
    """Soft-clip saturation via tanh."""
    return np.tanh(signal * drive)


# ═══════════════════════════════════════════════════════════════════════════
# PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

def apply_pitch_correct(signal: np.ndarray, preset: VocalPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Simplified pitch correction via spectral domain quantisation.
    Snaps frequencies toward chromatic scale tones using windowed FFT.
    """
    n = len(signal)
    if n == 0:
        return signal.copy()

    # Use overlapping windows for smoother result
    win_size = 2048
    hop = win_size // 4
    window = np.hanning(win_size)
    out = np.zeros(n)
    normalizer = np.zeros(n)

    # Chromatic frequencies in the root's scale (A4=432 DUBFORGE standard)
    root_freq = A4_432 * (2.0 ** ((preset.scale_root - 9) / 12.0))
    chromatic = [root_freq * (2.0 ** (s / 12.0))
                 for s in range(-36, 49)]  # wide range

    speed = preset.correction_speed

    for start in range(0, n - win_size, hop):
        chunk = signal[start:start + win_size] * window
        spectrum = np.fft.rfft(chunk)
        freqs = np.fft.rfftfreq(win_size, 1.0 / sample_rate)
        magnitudes = np.abs(spectrum)
        phases = np.angle(spectrum)

        # Find dominant frequency
        peak_idx = np.argmax(magnitudes[1:]) + 1
        peak_freq = freqs[peak_idx]

        if peak_freq > 20.0:
            # Find nearest chromatic note
            nearest = min(chromatic, key=lambda f: abs(f - peak_freq))
            ratio = nearest / peak_freq
            # Blend toward corrected pitch based on speed
            shift_ratio = 1.0 + (ratio - 1.0) * speed
            # Phase-vocoder-style frequency shift
            new_spectrum = np.zeros_like(spectrum)
            for i, (mag, phase) in enumerate(zip(magnitudes, phases)):
                target_bin = int(i * shift_ratio)
                if 0 <= target_bin < len(new_spectrum):
                    new_spectrum[target_bin] += mag * np.exp(1j * phase)
            chunk_out = np.fft.irfft(new_spectrum, n=win_size)
        else:
            chunk_out = chunk

        out[start:start + win_size] += chunk_out * window
        normalizer[start:start + win_size] += window ** 2

    # Normalize overlap-add
    mask = normalizer > 1e-8
    out[mask] /= normalizer[mask]
    return out


def apply_vocoder(signal: np.ndarray, preset: VocalPreset,
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Channel vocoder: analyse modulator (input signal) envelope per band,
    apply to a carrier signal (sawtooth at carrier_freq).
    """
    n = len(signal)
    if n == 0:
        return signal.copy()

    # Generate carrier — sawtooth wave
    t = np.arange(n) / sample_rate
    carrier = 2.0 * (t * preset.carrier_freq % 1.0) - 1.0

    # Split into frequency bands
    num_bands = max(4, preset.num_bands)
    min_freq = 80.0
    max_freq = min(sample_rate / 2.0 - 100, 12000.0)
    # Phi-spaced band centers
    band_centers = []
    freq = min_freq
    for _ in range(num_bands):
        if freq >= max_freq:
            break
        band_centers.append(freq)
        freq *= PHI ** 0.5  # sqrt(phi) spacing for tighter bands

    out = np.zeros(n)
    for center in band_centers:
        # Analyse: extract envelope from modulator band
        mod_band = _simple_biquad_bp(signal, center, preset.band_q, sample_rate)
        envelope = np.abs(mod_band)
        # Smooth envelope
        smooth_samples = max(1, int(0.005 * sample_rate))
        kernel = np.ones(smooth_samples) / smooth_samples
        envelope = np.convolve(envelope, kernel, mode='same')
        # Synthesize: filter carrier at same band, scale by envelope
        car_band = _simple_biquad_bp(carrier, center, preset.band_q, sample_rate)
        out += car_band * envelope

    # Normalize
    peak = np.max(np.abs(out))
    if peak > 1e-8:
        out = out / peak * np.max(np.abs(signal))
    return out


def apply_formant_shift(signal: np.ndarray, preset: VocalPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Shift formant frequencies without changing pitch.
    Uses spectral envelope shifting.
    """
    n = len(signal)
    if n == 0:
        return signal.copy()

    win_size = 2048
    hop = win_size // 4
    window = np.hanning(win_size)
    out = np.zeros(n)
    normalizer = np.zeros(n)

    shift_factor = 2.0 ** (preset.shift_semitones / 12.0)

    for start in range(0, n - win_size, hop):
        chunk = signal[start:start + win_size] * window
        spectrum = np.fft.rfft(chunk)
        magnitudes = np.abs(spectrum)
        phases = np.angle(spectrum)

        # Shift spectral envelope
        new_mags = np.zeros_like(magnitudes)
        for i in range(len(magnitudes)):
            src_idx = int(i / shift_factor)
            if 0 <= src_idx < len(magnitudes):
                new_mags[i] = magnitudes[src_idx]

        new_spectrum = new_mags * np.exp(1j * phases)
        chunk_out = np.fft.irfft(new_spectrum, n=win_size)
        out[start:start + win_size] += chunk_out * window
        normalizer[start:start + win_size] += window ** 2

    mask = normalizer > 1e-8
    out[mask] /= normalizer[mask]
    return out


def apply_harmonizer(signal: np.ndarray, preset: VocalPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Add pitch-shifted harmonies using simple resampling.
    Intervals in semitones from the harmony_intervals list.
    """
    n = len(signal)
    if n == 0:
        return signal.copy()

    out = signal.copy()
    for interval in preset.harmony_intervals:
        ratio = 2.0 ** (interval / 12.0)
        # Resample to shift pitch
        indices = np.arange(n) * ratio
        int_indices = np.clip(indices.astype(int), 0, n - 1)
        frac = indices - int_indices
        # Linear interpolation
        next_indices = np.clip(int_indices + 1, 0, n - 1)
        harmony = signal[int_indices] * (1.0 - frac) + signal[next_indices] * frac
        out += harmony * preset.harmony_mix

    # Normalize to original peak
    peak = np.max(np.abs(out))
    orig_peak = np.max(np.abs(signal))
    if peak > 1e-8 and orig_peak > 1e-8:
        out = out / peak * orig_peak
    return out


def apply_telephone(signal: np.ndarray, preset: VocalPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Lo-fi telephone effect: band-pass + saturation.
    """
    n = len(signal)
    if n == 0:
        return signal.copy()

    # High-pass at lo_cut
    out = _simple_biquad_hp(signal, preset.lo_cut_hz, 0.707, sample_rate)
    # Low-pass at hi_cut
    out = _simple_biquad_lp(out, preset.hi_cut_hz, 0.707, sample_rate)
    # Saturation
    out = _soft_clip(out, 1.0 + preset.saturation * 4.0)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def apply_vocal_processing(signal: np.ndarray, preset: VocalPreset,
                           sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct vocal processor based on preset type."""
    processors = {
        "pitch_correct": apply_pitch_correct,
        "vocoder": apply_vocoder,
        "formant_shift": apply_formant_shift,
        "harmonizer": apply_harmonizer,
        "telephone": apply_telephone,
    }
    proc = processors.get(preset.vocal_type)
    if proc is None:
        raise ValueError(f"Unknown vocal processing type: {preset.vocal_type}")
    processed = proc(signal, preset, sample_rate)
    # Wet/dry mix
    if preset.mix < 1.0:
        n = min(len(signal), len(processed))
        processed[:n] = signal[:n] * (1.0 - preset.mix) + processed[:n] * preset.mix
    return processed


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def pitch_correct_bank() -> VocalBank:
    return VocalBank("pitch_correct", [
        VocalPreset("pc_hard_snap", "pitch_correct", correction_speed=1.0),
        VocalPreset("pc_natural", "pitch_correct", correction_speed=0.4),
        VocalPreset("pc_phi_blend", "pitch_correct", correction_speed=1.0 / PHI),
        VocalPreset("pc_minor_key", "pitch_correct", scale_root=9,
                    correction_speed=0.7),
    ])


def vocoder_bank() -> VocalBank:
    return VocalBank("vocoder", [
        VocalPreset("voc_classic", "vocoder", num_bands=16, carrier_freq=110.0),
        VocalPreset("voc_lo_fi", "vocoder", num_bands=8, carrier_freq=55.0,
                    band_q=3.0),
        VocalPreset("voc_dense", "vocoder", num_bands=32, carrier_freq=220.0,
                    band_q=8.0),
        VocalPreset("voc_phi_carrier", "vocoder", num_bands=16,
                    carrier_freq=110.0 * PHI, band_q=5.0),
    ])


def formant_shift_bank() -> VocalBank:
    return VocalBank("formant_shift", [
        VocalPreset("fs_chipmunk", "formant_shift", shift_semitones=7.0),
        VocalPreset("fs_demon", "formant_shift", shift_semitones=-7.0),
        VocalPreset("fs_subtle_up", "formant_shift", shift_semitones=3.0),
        VocalPreset("fs_phi_shift", "formant_shift",
                    shift_semitones=12.0 / PHI),
    ])


def harmonizer_bank() -> VocalBank:
    return VocalBank("harmonizer", [
        VocalPreset("harm_thirds", "harmonizer",
                    harmony_intervals=[4, 7], harmony_mix=0.35),
        VocalPreset("harm_fifths", "harmonizer",
                    harmony_intervals=[7], harmony_mix=0.5),
        VocalPreset("harm_octave", "harmonizer",
                    harmony_intervals=[12, -12], harmony_mix=0.3),
        VocalPreset("harm_phi_stack", "harmonizer",
                    harmony_intervals=[int(12 / PHI), int(12 * PHI % 12)],
                    harmony_mix=1.0 / PHI),
    ])


def telephone_bank() -> VocalBank:
    return VocalBank("telephone", [
        VocalPreset("tel_classic", "telephone", lo_cut_hz=300.0,
                    hi_cut_hz=3400.0, saturation=0.5),
        VocalPreset("tel_am_radio", "telephone", lo_cut_hz=500.0,
                    hi_cut_hz=5000.0, saturation=0.3),
        VocalPreset("tel_megaphone", "telephone", lo_cut_hz=800.0,
                    hi_cut_hz=4000.0, saturation=0.9),
        VocalPreset("tel_walkie", "telephone", lo_cut_hz=400.0,
                    hi_cut_hz=2500.0, saturation=0.7),
    ])


ALL_VOCAL_BANKS: dict[str, callable] = {
    "pitch_correct": pitch_correct_bank,
    "vocoder": vocoder_bank,
    "formant_shift": formant_shift_bank,
    "harmonizer": harmonizer_bank,
    "telephone": telephone_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_vocal_processor_manifest(output_dir: str = "output") -> dict:
    """Write JSON manifest of all vocal processor presets."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_VOCAL_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "vocal_processor_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_vocal_processor_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    print(f"Vocal Processor: {len(manifest['banks'])} banks, {total} presets")


if __name__ == "__main__":
    main()
