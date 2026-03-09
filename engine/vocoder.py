"""
DUBFORGE — Vocoder Engine  (Session 163)

Channel vocoder synthesis — analyses a modulator signal's
spectral envelope and applies it to a carrier, creating
classic robotic vocal effects.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 44100


@dataclass
class VocoderPatch:
    """Vocoder configuration."""
    name: str = "Vocoder"
    n_bands: int = 16
    freq_lo: float = 80.0
    freq_hi: float = 8000.0
    attack_ms: float = 5.0
    release_ms: float = 20.0
    carrier_type: str = "saw"  # saw, square, noise, pulse
    carrier_harmonics: int = 32
    formant_shift: float = 1.0  # 0.5=down, 2.0=up
    mix: float = 1.0
    master_gain: float = 0.8


def _bandpass_filter(signal: list[float], center_freq: float,
                      bandwidth: float,
                      sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Simple IIR bandpass filter (2nd order)."""
    n = len(signal)
    if n == 0:
        return []

    w0 = 2.0 * math.pi * center_freq / sample_rate
    _bw = 2.0 * math.pi * bandwidth / sample_rate
    q = center_freq / max(bandwidth, 1.0)

    # Biquad coefficients
    alpha = math.sin(w0) / (2.0 * q) if q > 0 else 0.5
    cos_w0 = math.cos(w0)

    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    # Normalize
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0

    output = [0.0] * n
    x1 = x2 = y1 = y2 = 0.0

    for i in range(n):
        x0 = signal[i]
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        output[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0

    return output


def _envelope_follower(signal: list[float], attack_ms: float,
                        release_ms: float,
                        sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Extract amplitude envelope."""
    n = len(signal)
    if n == 0:
        return []

    attack_coeff = math.exp(-1.0 / (attack_ms * sample_rate / 1000))
    release_coeff = math.exp(-1.0 / (release_ms * sample_rate / 1000))

    envelope = [0.0] * n
    env = 0.0

    for i in range(n):
        rect = abs(signal[i])
        if rect > env:
            env = attack_coeff * env + (1 - attack_coeff) * rect
        else:
            env = release_coeff * env + (1 - release_coeff) * rect
        envelope[i] = env

    return envelope


def _generate_carrier(freq: float, n_samples: int,
                       carrier_type: str = "saw",
                       harmonics: int = 32,
                       sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate carrier oscillator."""
    dt = 1.0 / sample_rate
    signal = [0.0] * n_samples
    nyquist = sample_rate / 2

    for i in range(n_samples):
        t = i * dt
        phase = 2 * math.pi * freq * t

        if carrier_type == "saw":
            val = 0.0
            for k in range(1, harmonics + 1):
                if k * freq >= nyquist:
                    break
                val += ((-1) ** (k + 1)) * math.sin(k * phase) / k
            signal[i] = val * 2.0 / math.pi

        elif carrier_type == "square":
            val = 0.0
            for k in range(1, harmonics * 2, 2):
                if k * freq >= nyquist:
                    break
                val += math.sin(k * phase) / k
            signal[i] = val * 4.0 / math.pi

        elif carrier_type == "noise":
            x = int(t * sample_rate * 17 + 12345) & 0xFFFF
            x ^= x << 7
            x ^= x >> 9
            x ^= x << 8
            signal[i] = (x & 0xFFFF) / 32768.0 - 1.0

        elif carrier_type == "pulse":
            p = (phase % (2 * math.pi)) / (2 * math.pi)
            signal[i] = 1.0 if p < 0.25 else -1.0

    return signal


def vocode(modulator: list[float], carrier: list[float],
           patch: VocoderPatch,
           sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Apply vocoder processing."""
    n = min(len(modulator), len(carrier))
    if n == 0:
        return []

    # Calculate band center frequencies (logarithmic spacing)
    log_lo = math.log(patch.freq_lo)
    log_hi = math.log(patch.freq_hi)
    centers = [
        math.exp(log_lo + (log_hi - log_lo) * i / (patch.n_bands - 1))
        for i in range(patch.n_bands)
    ]

    # Bandwidth: distance between adjacent centers
    bandwidths = []
    for i in range(patch.n_bands):
        if i == 0:
            bw = centers[1] - centers[0] if patch.n_bands > 1 else \
                centers[0]
        elif i == patch.n_bands - 1:
            bw = centers[-1] - centers[-2]
        else:
            bw = (centers[i + 1] - centers[i - 1]) / 2
        bandwidths.append(bw)

    output = [0.0] * n

    for band_i in range(patch.n_bands):
        center = centers[band_i]
        bw = bandwidths[band_i]

        # Apply formant shift
        carrier_center = center * patch.formant_shift

        # Bandpass filter modulator
        mod_filtered = _bandpass_filter(
            modulator[:n], center, bw, sample_rate,
        )

        # Extract envelope from modulator band
        env = _envelope_follower(
            mod_filtered, patch.attack_ms, patch.release_ms, sample_rate,
        )

        # Bandpass filter carrier
        car_filtered = _bandpass_filter(
            carrier[:n], carrier_center, bw, sample_rate,
        )

        # Apply envelope to carrier band
        for i in range(n):
            output[i] += car_filtered[i] * env[i]

    # Normalize
    peak = max(abs(s) for s in output) if output else 1.0
    if peak > 0:
        scale = patch.master_gain / peak
        output = [s * scale for s in output]

    # Mix
    if patch.mix < 1.0:
        for i in range(n):
            output[i] = output[i] * patch.mix + \
                modulator[i] * (1 - patch.mix)

    return output


def render_vocoder(freq: float = 110.0, duration: float = 2.0,
                    patch: VocoderPatch | None = None,
                    sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate vocoder output from synthetic modulator+carrier."""
    if patch is None:
        patch = VocoderPatch()

    n = int(duration * sample_rate)
    dt = 1.0 / sample_rate

    # Modulator: formant-like signal (vocal simulation)
    modulator = [0.0] * n
    formant_freqs = [270, 730, 2300, 3000]  # Approx 'A' vowel
    for f in formant_freqs:
        for i in range(n):
            t = i * dt
            env = math.exp(-t * 2) * 0.7 + 0.3  # Decaying
            modulator[i] += env * math.sin(2 * math.pi * f * t) * 0.25

    # Carrier
    carrier = _generate_carrier(
        freq, n, patch.carrier_type, patch.carrier_harmonics, sample_rate,
    )

    return vocode(modulator, carrier, patch, sample_rate)


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


VOCODER_PRESETS: dict[str, VocoderPatch] = {
    "classic": VocoderPatch("Classic", 16, 80, 8000),
    "robot": VocoderPatch("Robot", 8, 100, 4000, carrier_type="square"),
    "whisper": VocoderPatch("Whisper", 24, 60, 12000, carrier_type="noise"),
    "deep": VocoderPatch("Deep", 12, 40, 4000, formant_shift=0.7),
    "alien": VocoderPatch("Alien", 16, 80, 8000, formant_shift=1.5),
    "phi_vocoder": VocoderPatch("PHI Vocoder", int(PHI * 10), 80,
                                 int(8000 * PHI), formant_shift=PHI / 2),
}


def render_preset(name: str, freq: float = 110.0,
                   duration: float = 2.0,
                   output_dir: str = "output/wavetables") -> str:
    patch = VOCODER_PRESETS.get(name, VOCODER_PRESETS["classic"])
    signal = render_vocoder(freq, duration, patch)
    path = os.path.join(output_dir, f"vocoder_{name}.wav")
    return _write_wav(path, signal)


def main() -> None:
    print("Vocoder Engine")
    for name, patch in VOCODER_PRESETS.items():
        sig = render_vocoder(110, 0.5, patch)
        peak = max(abs(s) for s in sig) if sig else 0
        print(f"  {name}: {patch.n_bands} bands, "
              f"carrier={patch.carrier_type}, "
              f"shift={patch.formant_shift:.1f}, peak={peak:.4f}")
    print("Done.")


if __name__ == "__main__":
    main()
