"""
DUBFORGE Engine — Mid-Bass Growl Resampler

Resample + mangle pipeline for mid-bass growls.
Takes a single-cycle source, applies fractal-driven modulation,
distortion, and formant shifting to create evolving growl textures.

Outputs Serum-ready wavetable.

Based on MIDBASS_GROWL_RESAMPLER_ENGINE specs from Serum 2 Module Pack v1.

Dojo Integration (ill.Gates):
  - Mudpie technique: chaos → chop → extract → resample (mudpie_chaos_pipeline)
  - Audio Rate Filter FM: modulate filter cutoff at audio rates (dojo_audio_rate_fm)
  - Resampling Chains: iterative render → process → render (3 passes max)
"""

import math
from pathlib import Path

import numpy as np

# Import shared constants and wavetable writer
from engine.config_loader import PHI, get_config_value
from engine.phi_core import WAVETABLE_SIZE, write_wav
from engine.accel import fft, ifft
from engine.turboquant import (
    CompressedWavetable,
    TurboQuantConfig,
    compress_wavetable,
)

# --- Processing Steps -----------------------------------------------------

def pitch_shift(frame: np.ndarray, semitones: float,
                formant_preserve: bool = True,
                formant_shift: int = 3) -> np.ndarray:
    """
    Pitch shift a single-cycle frame.
    Simple spectral approach: shift FFT bins.
    """
    spectrum = fft(frame)
    n = len(spectrum)
    shift_bins = int(semitones * n / 48)  # rough semitone-to-bin

    shifted = np.zeros_like(spectrum)
    for i in range(n):
        new_idx = i + shift_bins
        if 0 <= new_idx < n:
            shifted[new_idx] = spectrum[i]

    if formant_preserve and formant_shift != 0:
        # Apply formant shift by shifting spectral envelope
        envelope = np.abs(spectrum)
        formant_bins = int(formant_shift * n / 48)
        shifted_env = np.zeros_like(envelope)
        for i in range(n):
            new_idx = i + formant_bins
            if 0 <= new_idx < n:
                shifted_env[new_idx] = envelope[i]

        # Blend formant envelope
        mag = np.abs(shifted)
        phase = np.angle(shifted)
        blend = 0.5
        new_mag = mag * (1 - blend) + shifted_env * blend
        shifted = new_mag * np.exp(1j * phase)

    result = ifft(shifted, n=len(frame))  # type: ignore[arg-type]
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak
    return result


def waveshape_distortion(frame: np.ndarray, drive: float = 0.618,
                          mix: float = 0.8) -> np.ndarray:
    """Tanh waveshaping distortion with phi-ratio drive."""
    drive_amount = 1.0 + drive * 8.0
    distorted = np.tanh(frame * drive_amount)
    return frame * (1 - mix) + distorted * mix


def frequency_shift(frame: np.ndarray, hz: float = 34.0,
                     mix: float = 0.4) -> np.ndarray:
    """
    Frequency shift by adding a fixed Hz offset in spectral domain.
    Creates inharmonic, metallic character.
    """
    spectrum = fft(frame)
    n = len(spectrum)
    # Shift bins by hz amount (relative to single-cycle)
    shift = int(hz * n / 22050)
    shifted = np.zeros_like(spectrum)
    for i in range(n):
        new_idx = i + shift
        if 0 <= new_idx < n:
            shifted[new_idx] = spectrum[i]

    result = ifft(shifted, n=len(frame))
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak
    return frame * (1 - mix) + result * mix


def comb_filter(frame: np.ndarray, delay_ms: float = 2.618,
                feedback: float = 0.55, mix: float = 0.5) -> np.ndarray:
    """
    Comb filter with phi-squared delay time.
    Creates metallic resonance.
    """
    delay_samples = int(delay_ms * 44.1)  # at 44100 Hz
    delay_samples = max(1, min(delay_samples, len(frame) // 2))

    output = np.copy(frame)
    for i in range(delay_samples, len(output)):
        output[i] += feedback * output[i - delay_samples]

    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak

    return frame * (1 - mix) + output * mix


def bit_reduce(frame: np.ndarray, bits: int = 8,
               sample_rate_reduce: float = 0.382,
               mix: float = 0.3) -> np.ndarray:
    """
    Bit reduction + sample rate reduction for lo-fi grit.
    """
    # Bit reduction
    levels = 2 ** bits
    reduced = np.round(frame * levels) / levels

    # Sample rate reduction
    step = max(1, int(1.0 / sample_rate_reduce))
    sr_reduced = np.copy(reduced)
    for i in range(0, len(sr_reduced), step):
        end = min(i + step, len(sr_reduced))
        sr_reduced[i:end] = sr_reduced[i]

    return frame * (1 - mix) + sr_reduced * mix


def formant_filter(frame: np.ndarray, vowel: str = "A",
                    depth: float = 0.618, mix: float = 0.6) -> np.ndarray:
    """
    Apply formant filter based on vowel shape.
    Simplified: boosts specific frequency bands.
    """
    # Formant center frequencies (Hz, approximate for bass range)
    formants = {
        "A": [730, 1090, 2440],
        "E": [660, 1720, 2410],
        "I": [390, 1990, 2550],
        "O": [570, 840, 2410],
        "U": [440, 1020, 2240],
    }

    centers = formants.get(vowel, formants["A"])
    spectrum = fft(frame)
    n = len(spectrum)
    freqs = np.fft.rfftfreq(len(frame), d=1.0 / 44100)

    formant_response = np.ones(n)
    for center in centers:
        bandwidth = center * 0.15  # Q factor
        boost = np.exp(-0.5 * ((freqs - center) / bandwidth) ** 2)
        formant_response += boost * depth * 3

    spectrum *= formant_response
    result = ifft(spectrum, n=len(frame))
    peak = np.max(np.abs(result))
    if peak > 0:
        result /= peak

    return frame * (1 - mix) + result * mix


# --- Full Pipeline --------------------------------------------------------

def growl_resample_pipeline(source_frame: np.ndarray,
                             n_output_frames: int = 256) -> list[np.ndarray]:
    """
    Full growl resampler pipeline.
    Generates multiple frames by varying pipeline parameters
    across the wavetable for evolving texture.
    """
    output_frames = []
    vowels = ["A", "E", "I", "O", "U"]

    for i in range(n_output_frames):
        progress = i / max(n_output_frames - 1, 1)

        # Current frame starts from source
        frame = np.copy(source_frame)

        # 1. Pitch shift (subtle variation)
        shift = math.sin(progress * 2 * math.pi) * 2  # +/- 2 semitones
        frame = pitch_shift(frame, semitones=shift,
                           formant_preserve=True, formant_shift=3)

        # 2. Distortion (increases with progress)
        drive = 0.3 + progress * 0.5
        frame = waveshape_distortion(frame, drive=drive, mix=0.7)

        # 3. Frequency shift (varies with phi)
        freq_hz = 34 * (1 + math.sin(progress * PHI * math.pi) * 0.5)
        frame = frequency_shift(frame, hz=freq_hz, mix=0.3)

        # 4. Comb filter
        delay = 2.618 * (1 + progress * 0.5)
        frame = comb_filter(frame, delay_ms=delay, feedback=0.5, mix=0.4)

        # 5. Bit reduction (subtle, increases slightly)
        frame = bit_reduce(frame, bits=8 + int(progress * 4),
                          sample_rate_reduce=0.382, mix=0.2 + progress * 0.1)

        # 6. Formant filter (cycles through vowels)
        vowel_idx = int(progress * len(vowels) * 2) % len(vowels)
        frame = formant_filter(frame, vowel=vowels[vowel_idx],
                              depth=0.618, mix=0.5)

        # Final normalize
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak

        output_frames.append(frame)

    return output_frames


# ═══════════════════════════════════════════════════════════════════════════
# DOJO INTEGRATION — ill.Gates Mudpies & Audio Rate Filter FM
# ═══════════════════════════════════════════════════════════════════════════

def mudpie_chaos_pipeline(source: np.ndarray, n_passes: int = 5,
                          seed: int | None = None) -> list[np.ndarray]:
    """ill.Gates Mudpie technique — randomized processing chain.

    Takes a source waveform and runs it through randomized combinations
    of pitch shift, distortion, frequency shift, comb filter, bit reduction,
    and formant filtering. Returns all variations — the user picks the gems.

    Args:
        source: Input waveform (single-cycle frame)
        n_passes: Number of random variations to generate (default: 5)
        seed: Random seed for reproducibility (None = true chaos)

    Returns:
        List of processed variations (Mudpie outputs)
    """
    rng = np.random.default_rng(seed)
    variations = []

    for pass_num in range(n_passes):
        frame = np.copy(source)

        # Randomize processing order
        processors = [
            ("pitch", lambda f: pitch_shift(f, semitones=rng.uniform(-12, 12),
                                            formant_preserve=rng.random() > 0.5)),
            ("distort", lambda f: waveshape_distortion(f, drive=rng.uniform(0.1, 0.9),
                                                        mix=rng.uniform(0.3, 1.0))),
            ("freq_shift", lambda f: frequency_shift(f, hz=rng.uniform(10, 200),
                                                      mix=rng.uniform(0.2, 0.7))),
            ("comb", lambda f: comb_filter(f, delay_ms=rng.uniform(0.5, 10.0),
                                            feedback=rng.uniform(0.2, 0.8),
                                            mix=rng.uniform(0.2, 0.6))),
            ("bitcrush", lambda f: bit_reduce(f, bits=int(rng.integers(3, 12)),
                                               sample_rate_reduce=rng.uniform(0.1, 0.8),
                                               mix=rng.uniform(0.1, 0.5))),
            ("formant", lambda f: formant_filter(f, vowel=rng.choice(["A", "E", "I", "O", "U"]),
                                                  depth=rng.uniform(0.3, 1.0),
                                                  mix=rng.uniform(0.3, 0.8))),
        ]

        # Randomly select 3-5 processors and randomize order
        n_procs = rng.integers(3, min(6, len(processors)) + 1)
        selected = rng.choice(len(processors), size=n_procs, replace=False)
        rng.shuffle(selected)

        for idx in selected:
            _name, proc_fn = processors[idx]
            try:
                frame = proc_fn(frame)
            except Exception:
                pass  # Skip failed processors — chaos is forgiving

        # Normalize output
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak

        variations.append(frame)

    return variations


def dojo_audio_rate_fm(frame: np.ndarray, mod_freq: float = 55.0,
                       depth: float = 0.5,
                       sample_rate: int = 48000) -> np.ndarray:
    """ill.Gates Audio Rate Filter FM — modulate filter cutoff at audio frequencies.

    Creates FM-like timbres by modulating a virtual filter cutoff at audio rate.
    This produces complex sidebands and metallic/bell-like textures from
    simple source material — a key ill.Gates sound design technique.

    Args:
        frame: Single-cycle waveform to process
        mod_freq: Modulation frequency in Hz (try phi-related: 55, 89, 144)
        depth: Modulation depth 0.0-1.0
        sample_rate: Sample rate for frequency calculation

    Returns:
        Processed waveform with audio-rate filter modulation
    """
    n = len(frame)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)

    # Generate modulator at audio rate
    mod_phase = mod_freq / sample_rate * n
    modulator = np.sin(t * mod_phase) * depth

    # Apply as multiplicative AM + phase modulation hybrid
    # This creates both sum/difference frequencies (FM sidebands)
    spectrum = fft(frame)
    mod_spectrum = fft(modulator)

    # Convolve in frequency domain (= multiply in time domain creates FM)
    n_spec = min(len(spectrum), len(mod_spectrum))
    result_spectrum = np.zeros_like(spectrum)
    for i in range(n_spec):
        result_spectrum[i] = spectrum[i] * (1.0 + mod_spectrum[i] * depth)

    result = ifft(result_spectrum, n=n)

    # Blend with original
    mix = depth * 0.7
    output = frame * (1 - mix) + result * mix

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak

    return output


def tq_compress_growl(
    frames: list[np.ndarray],
    name: str,
    config: TurboQuantConfig | None = None,
) -> CompressedWavetable:
    """TQ-compress growl resampler output frames."""
    float_frames = [f.tolist() for f in frames]
    return compress_wavetable(float_frames, config or TurboQuantConfig(), name=name)


# --- Source Generators (if no input provided) -----------------------------

def generate_saw_source(size: int = WAVETABLE_SIZE) -> np.ndarray:
    """Generate a basic saw wave as resampler source."""
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)
    return 2.0 * ((t / (2 * np.pi)) % 1.0) - 1.0


def generate_fm_source(size: int = WAVETABLE_SIZE,
                        fm_ratio: float = PHI,
                        fm_depth: float = 3.0) -> np.ndarray:
    """Generate FM synthesis source with phi ratio."""
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)
    modulator = np.sin(fm_ratio * t)
    carrier = np.sin(t + fm_depth * modulator)
    return carrier


# --- Main -----------------------------------------------------------------

def main() -> None:
    out_dir = Path('output/wavetables')
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load pipeline config from YAML (fallback to defaults)
    n_frames = 256
    fm_ratio = PHI
    try:
        cfg = get_config_value(
            "serum2_module_pack_v1", "MIDBASS_GROWL_RESAMPLER_ENGINE", default={})
        if isinstance(cfg, dict):
            pipeline = cfg.get("pipeline", [])
            for step in (pipeline if isinstance(pipeline, list) else []):
                if isinstance(step, dict) and step.get("step") == "resample_to_wavetable":
                    n_frames = int(step.get("frames", 256))
        fm_cfg = get_config_value(
            "serum2_module_pack_v1", "FM_BASS_ENGINE", "serum_osc_b", default={})
        if isinstance(fm_cfg, dict):
            fm_ratio = float(fm_cfg.get("pitch_fine", PHI))
    except FileNotFoundError:
        pass

    # Generate from saw source
    print("Generating growl wavetable from saw source...")
    saw_source = generate_saw_source()
    saw_frames = growl_resample_pipeline(saw_source, n_output_frames=n_frames)
    saw_path = str(out_dir / 'DUBFORGE_GROWL_SAW.wav')
    write_wav(saw_path, saw_frames)
    tq_compress_growl(saw_frames, "GROWL_SAW").compressed_bytes  # type: ignore[attr-defined]  # warm cache
    print(f"  -> {saw_path}")

    # Generate from FM source
    print("Generating growl wavetable from FM source...")
    fm_source = generate_fm_source(fm_ratio=fm_ratio)
    fm_frames = growl_resample_pipeline(fm_source, n_output_frames=n_frames)
    fm_path = str(out_dir / 'DUBFORGE_GROWL_FM.wav')
    write_wav(fm_path, fm_frames)
    tq_compress_growl(fm_frames, "GROWL_FM").compressed_bytes  # type: ignore[attr-defined]  # warm cache
    print(f"  -> {fm_path}")

    print("Growl Resampler complete.")


if __name__ == '__main__':
    main()
