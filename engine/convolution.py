"""
DUBFORGE — Convolution Engine

Impulse response generation, convolution processing, and room simulation.
5 types × 4 presets = 20 presets.

Types:
  room_ir       — synthetic room impulse responses with phi reflections
  cabinet_ir    — guitar/bass cabinet simulation
  plate_ir      — plate reverb impulse response synthesis
  inverse_ir    — deconvolution / spectral inversion
  custom_ir     — user-defined impulse response convolution
"""

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from engine.config_loader import PHI
from engine.accel import fft, ifft, convolve, write_wav

SAMPLE_RATE = 44100
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConvolutionPreset:
    """Preset for convolution processing."""
    name: str
    conv_type: str  # room_ir | cabinet_ir | plate_ir | inverse_ir | custom_ir
    # Room IR
    room_length_m: float = 10.0     # room dimension metres
    room_width_m: float = 8.0
    room_height_m: float = 3.5
    wall_absorption: float = 0.3    # 0=reflective .. 1=absorbent
    # Cabinet
    cabinet_size: str = "4x12"      # 1x12 | 2x12 | 4x12
    speaker_type: str = "vintage"   # vintage | modern | bright
    mic_position: float = 0.5       # 0=edge .. 1=center
    # Plate
    plate_size: float = 1.0         # 0.5=small .. 2.0=large
    plate_damping: float = 0.5
    plate_brightness: float = 0.7
    # Inverse
    regularisation: float = 0.01    # Wiener filter regularisation
    # Custom
    ir_length_ms: float = 500.0     # custom IR length
    ir_decay: float = 0.95          # exponential decay rate
    # Common
    mix: float = 0.5
    ir_trim_db: float = -60.0       # trim IR below this level


@dataclass
class ConvolutionBank:
    """Bank of convolution presets."""
    name: str
    presets: list[ConvolutionPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# IR GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def generate_room_ir(preset: ConvolutionPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Generate a synthetic room impulse response using image-source method.
    Reflections are spaced using phi-ratio geometry for natural decay.
    """
    speed_of_sound = 343.0  # m/s
    max_time = 1.5  # seconds of IR

    ir_len = int(max_time * sample_rate)
    ir = np.zeros(ir_len)

    # Direct sound
    ir[0] = 1.0

    # Image source reflections from walls, floor, ceiling
    dimensions = [preset.room_length_m, preset.room_width_m, preset.room_height_m]
    reflection_coeff = 1.0 - preset.wall_absorption

    # Generate reflection points using phi-scaled distances
    for order in range(1, 8):
        for dim in dimensions:
            # Forward and back reflections
            for sign in [1.0, -1.0]:
                distance = dim * order * PHI ** 0.3
                delay_sec = distance / speed_of_sound
                delay_samp = int(delay_sec * sample_rate)
                if delay_samp < ir_len:
                    amplitude = (reflection_coeff ** order) * (
                        1.0 / (1.0 + distance * 0.1)
                    ) * sign * ((-1) ** order)
                    ir[delay_samp] += amplitude

    # Apply exponential decay envelope
    t = np.arange(ir_len) / sample_rate
    decay_env = np.exp(-t / (max_time * 0.5))
    ir *= decay_env

    # Diffusion filter — convolve with a short noise burst
    diff_len = int(0.003 * sample_rate)
    rng = np.random.default_rng(42)
    diff_kernel = rng.normal(0, 1, diff_len)
    diff_kernel /= np.sqrt(np.sum(diff_kernel ** 2))
    ir = convolve(ir, diff_kernel, mode='same')

    # Normalize
    peak = np.max(np.abs(ir))
    if peak > 1e-8:
        ir /= peak
    return ir


def generate_cabinet_ir(preset: ConvolutionPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Generate a synthetic cabinet impulse response.
    Models speaker cone + cabinet resonance + mic position.
    """
    ir_len = int(0.05 * sample_rate)  # 50ms is enough for a cab
    ir = np.zeros(ir_len)

    # Cabinet resonance frequencies based on size
    cab_resonances = {
        "1x12": [100.0, 800.0, 2500.0],
        "2x12": [80.0, 600.0, 2200.0],
        "4x12": [60.0, 500.0, 1800.0],
    }
    resonances = cab_resonances.get(preset.cabinet_size, cab_resonances["4x12"])

    # Speaker type brightness scaling
    brightness = {
        "vintage": 0.6,
        "modern": 1.0,
        "bright": 1.4,
    }
    bright = brightness.get(preset.speaker_type, 1.0)

    # Build IR as sum of damped sinusoids at resonance frequencies
    t = np.arange(ir_len) / sample_rate
    for freq in resonances:
        freq_scaled = freq * bright
        decay = np.exp(-t * freq_scaled * 0.02)
        ir += np.sin(2.0 * np.pi * freq_scaled * t) * decay

    # Mic position affects high-freq content
    # Center = more high-freq, edge = more low-freq
    if preset.mic_position < 0.5:
        # Low-pass roll-off for edge — decay simulation
        ir *= np.exp(-t * (1.0 - preset.mic_position) * 500)
    else:
        # Slight presence boost for center
        ir *= 1.0 + 0.3 * np.sin(2.0 * np.pi * 3500.0 * t) * np.exp(-t * 200)

    # Normalize
    peak = np.max(np.abs(ir))
    if peak > 1e-8:
        ir /= peak
    return ir


def generate_plate_ir(preset: ConvolutionPreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Generate a synthetic plate reverb impulse response.
    High modal density with phi-ratio spacing.
    """
    ir_len = int(preset.plate_size * sample_rate)
    ir = np.zeros(ir_len)

    # Plate modes at phi-ratio frequencies
    base_freq = 80.0 / preset.plate_size
    t = np.arange(ir_len) / sample_rate
    num_modes = 20

    for i in range(num_modes):
        freq = base_freq * (PHI ** (i * 0.7))
        if freq > sample_rate / 2.0 - 100:
            break
        # Higher modes decay faster
        mode_decay = preset.plate_damping * (1.0 + i * 0.5)
        amplitude = (1.0 / (1.0 + i * 0.3)) * preset.plate_brightness
        decay = np.exp(-t * mode_decay)
        ir += np.sin(2.0 * np.pi * freq * t) * decay * amplitude

    # Add diffusion via dense noise tail
    rng = np.random.default_rng(137)
    noise_tail = rng.normal(0, 1, ir_len)
    tail_env = np.exp(-t / (preset.plate_size * 0.4))
    ir += noise_tail * tail_env * 0.1

    peak = np.max(np.abs(ir))
    if peak > 1e-8:
        ir /= peak
    return ir


def generate_inverse_ir(original_ir: np.ndarray,
                        preset: ConvolutionPreset,
                        sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Generate inverse filter via spectral inversion (Wiener deconvolution).
    Used for removing room coloration or creating complementary EQ.
    """
    n = len(original_ir)
    if n == 0:
        return original_ir.copy()

    # Zero-pad for better frequency resolution
    fft_size = max(n * 2, 4096)
    spectrum = fft(original_ir, n=fft_size)

    # Wiener deconvolution
    power = np.abs(spectrum) ** 2
    reg = preset.regularisation * np.max(power)
    inverse_spectrum = np.conj(spectrum) / (power + reg)

    inverse_ir = ifft(inverse_spectrum, n=fft_size)[:n]

    # Normalize
    peak = np.max(np.abs(inverse_ir))
    if peak > 1e-8:
        inverse_ir /= peak
    return inverse_ir


def generate_custom_ir(preset: ConvolutionPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Generate a custom-shaped impulse response with configurable decay.
    Fibonacci-timed reflections with exponential envelope.
    """
    ir_len = int(preset.ir_length_ms * sample_rate / 1000.0)
    ir = np.zeros(ir_len)

    # Fibonacci-timed impulses
    fib = [1, 1]
    while fib[-1] < ir_len:
        fib.append(fib[-1] + fib[-2])

    for i, f in enumerate(fib):
        if f >= ir_len:
            break
        ir[f] = preset.ir_decay ** i

    # Smooth with noise convolution
    rng = np.random.default_rng(256)
    smooth_len = max(1, int(0.002 * sample_rate))
    kernel = rng.normal(0, 1, smooth_len)
    kernel /= np.sqrt(np.sum(kernel ** 2))
    ir = convolve(ir, kernel, mode='same')

    # Apply decay envelope
    t = np.arange(ir_len) / sample_rate
    decay_time = preset.ir_length_ms / 1000.0 * 0.5
    ir *= np.exp(-t / max(0.01, decay_time))

    peak = np.max(np.abs(ir))
    if peak > 1e-8:
        ir /= peak
    return ir


# ═══════════════════════════════════════════════════════════════════════════
# CONVOLUTION PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════

def convolve_signal(signal: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """
    Fast convolution via FFT overlap-add.
    Returns convolved signal trimmed to input length.
    """
    n_sig = len(signal)
    n_ir = len(ir)
    if n_sig == 0 or n_ir == 0:
        return signal.copy()

    # FFT convolution
    fft_size = 1
    while fft_size < n_sig + n_ir - 1:
        fft_size <<= 1

    sig_fft = fft(signal, n=fft_size)
    ir_fft = fft(ir, n=fft_size)
    result = ifft(sig_fft * ir_fft, n=fft_size)[:n_sig]

    return result


def apply_convolution(signal: np.ndarray, preset: ConvolutionPreset,
                      sample_rate: int = SAMPLE_RATE,
                      custom_ir: np.ndarray | None = None) -> np.ndarray:
    """
    Route to the correct IR generator and apply convolution.
    """
    if preset.conv_type == "room_ir":
        ir = generate_room_ir(preset, sample_rate)
    elif preset.conv_type == "cabinet_ir":
        ir = generate_cabinet_ir(preset, sample_rate)
    elif preset.conv_type == "plate_ir":
        ir = generate_plate_ir(preset, sample_rate)
    elif preset.conv_type == "inverse_ir":
        base_ir = custom_ir if custom_ir is not None else generate_room_ir(
            preset, sample_rate)
        ir = generate_inverse_ir(base_ir, preset, sample_rate)
    elif preset.conv_type == "custom_ir":
        ir = generate_custom_ir(preset, sample_rate)
    else:
        raise ValueError(f"Unknown convolution type: {preset.conv_type}")

    # Trim IR below threshold
    trim_linear = 10.0 ** (preset.ir_trim_db / 20.0)
    abs_ir = np.abs(ir)
    trim_idx = len(ir)
    for i in range(len(ir) - 1, 0, -1):
        if abs_ir[i] > trim_linear:
            trim_idx = i + 1
            break
    ir = ir[:trim_idx]

    # Convolve
    wet = convolve_signal(signal, ir)

    # Normalize wet to match dry level
    dry_peak = np.max(np.abs(signal))
    wet_peak = np.max(np.abs(wet))
    if wet_peak > 1e-8 and dry_peak > 1e-8:
        wet = wet / wet_peak * dry_peak

    # Wet/dry mix
    n = min(len(signal), len(wet))
    out = signal.copy()
    out[:n] = signal[:n] * (1.0 - preset.mix) + wet[:n] * preset.mix
    return out


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def room_ir_bank() -> ConvolutionBank:
    return ConvolutionBank("room_ir", [
        ConvolutionPreset("ir_small_room", "room_ir", room_length_m=5.0,
                          room_width_m=4.0, room_height_m=2.5,
                          wall_absorption=0.5, mix=0.3),
        ConvolutionPreset("ir_concert_hall", "room_ir", room_length_m=30.0,
                          room_width_m=20.0, room_height_m=12.0,
                          wall_absorption=0.2, mix=0.4),
        ConvolutionPreset("ir_bathroom", "room_ir", room_length_m=3.0,
                          room_width_m=2.5, room_height_m=2.5,
                          wall_absorption=0.1, mix=0.5),
        ConvolutionPreset("ir_phi_room", "room_ir",
                          room_length_m=PHI * 5,
                          room_width_m=PHI * 3,
                          room_height_m=PHI * 2,
                          wall_absorption=1.0 / PHI, mix=0.35),
    ])


def cabinet_ir_bank() -> ConvolutionBank:
    return ConvolutionBank("cabinet_ir", [
        ConvolutionPreset("ir_cab_4x12_vintage", "cabinet_ir",
                          cabinet_size="4x12", speaker_type="vintage",
                          mic_position=0.5, mix=1.0),
        ConvolutionPreset("ir_cab_2x12_modern", "cabinet_ir",
                          cabinet_size="2x12", speaker_type="modern",
                          mic_position=0.7, mix=1.0),
        ConvolutionPreset("ir_cab_1x12_bright", "cabinet_ir",
                          cabinet_size="1x12", speaker_type="bright",
                          mic_position=0.9, mix=1.0),
        ConvolutionPreset("ir_cab_4x12_dark", "cabinet_ir",
                          cabinet_size="4x12", speaker_type="vintage",
                          mic_position=0.1, mix=1.0),
    ])


def plate_ir_bank() -> ConvolutionBank:
    return ConvolutionBank("plate_ir", [
        ConvolutionPreset("ir_plate_small", "plate_ir", plate_size=0.5,
                          plate_damping=0.7, plate_brightness=0.8, mix=0.35),
        ConvolutionPreset("ir_plate_large", "plate_ir", plate_size=2.0,
                          plate_damping=0.3, plate_brightness=0.6, mix=0.4),
        ConvolutionPreset("ir_plate_bright", "plate_ir", plate_size=1.0,
                          plate_damping=0.4, plate_brightness=1.0, mix=0.3),
        ConvolutionPreset("ir_plate_phi", "plate_ir", plate_size=PHI,
                          plate_damping=1.0 / PHI,
                          plate_brightness=1.0 / PHI, mix=0.35),
    ])


def inverse_ir_bank() -> ConvolutionBank:
    return ConvolutionBank("inverse_ir", [
        ConvolutionPreset("ir_inverse_tight", "inverse_ir",
                          regularisation=0.1, mix=0.5),
        ConvolutionPreset("ir_inverse_smooth", "inverse_ir",
                          regularisation=0.001, mix=0.4),
        ConvolutionPreset("ir_inverse_mid", "inverse_ir",
                          regularisation=0.01, mix=0.5),
        ConvolutionPreset("ir_inverse_phi", "inverse_ir",
                          regularisation=1.0 / (PHI * 100), mix=0.5),
    ])


def custom_ir_bank() -> ConvolutionBank:
    return ConvolutionBank("custom_ir", [
        ConvolutionPreset("ir_fib_short", "custom_ir", ir_length_ms=200.0,
                          ir_decay=0.85, mix=0.3),
        ConvolutionPreset("ir_fib_long", "custom_ir", ir_length_ms=1000.0,
                          ir_decay=0.95, mix=0.4),
        ConvolutionPreset("ir_fib_dense", "custom_ir", ir_length_ms=500.0,
                          ir_decay=0.99, mix=0.35),
        ConvolutionPreset("ir_fib_phi", "custom_ir",
                          ir_length_ms=PHI * 300,
                          ir_decay=1.0 / PHI + 0.3, mix=0.35),
    ])


ALL_CONVOLUTION_BANKS: dict[str, Callable[[], ConvolutionBank]] = {
    "room_ir": room_ir_bank,
    "cabinet_ir": cabinet_ir_bank,
    "plate_ir": plate_ir_bank,
    "inverse_ir": inverse_ir_bank,
    "custom_ir": custom_ir_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    write_wav(str(path), samples, sample_rate=sample_rate)


def _export_path(path: Path) -> str:
    """Return stable POSIX-style paths for cross-platform callers/tests."""
    return path.as_posix()


def _test_signal(duration_s: float = 1.0, freq: float = 200.0,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a test sine for processing demos."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return 0.8 * np.sin(2.0 * np.pi * freq * t)


def export_convolution_demos(output_dir: str = "output") -> list[str]:
    """Render IRs + convolved demos for every preset and write .wav."""
    sig = _test_signal()
    out = Path(output_dir) / "wavetables" / "convolution"
    ir_dir = out / "irs"
    out.mkdir(parents=True, exist_ok=True)
    ir_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    ir_generators = {
        "room_ir": generate_room_ir,
        "cabinet_ir": generate_cabinet_ir,
        "plate_ir": generate_plate_ir,
        "custom_ir": generate_custom_ir,
    }

    for bank_name, bank_fn in ALL_CONVOLUTION_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            # Export processed audio
            processed = apply_convolution(sig, preset, SAMPLE_RATE)
            fname = f"conv_{preset.name}.wav"
            _write_wav(out / fname, processed)
            paths.append(_export_path(out / fname))

            # Also export the IR itself if generator exists
            gen = ir_generators.get(bank_name)
            if gen is not None:
                ir = gen(preset, SAMPLE_RATE)
                ir_fname = f"ir_{preset.name}.wav"
                _write_wav(ir_dir / ir_fname, ir)
                paths.append(_export_path(ir_dir / ir_fname))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_convolution_manifest(output_dir: str = "output") -> dict:
    """Write JSON manifest of all convolution presets."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_CONVOLUTION_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "convolution_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_convolution_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_convolution_demos()
    print(f"Convolution: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
