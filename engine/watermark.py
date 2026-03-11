"""
DUBFORGE — Audio Watermark Engine  (Session 184)

Embeds invisible watermarks in audio using spread-spectrum
encoding with PHI-modulated carriers.
"""

import math
import os
import struct
import wave

from engine.config_loader import PHI
SAMPLE_RATE = 48000


def _text_to_bits(text: str) -> list[int]:
    """Convert text to bit sequence."""
    bits: list[int] = []
    for char in text.encode("utf-8"):
        for i in range(7, -1, -1):
            bits.append((char >> i) & 1)
    return bits


def _bits_to_text(bits: list[int]) -> str:
    """Convert bit sequence back to text."""
    chars: list[int] = []
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        chars.append(byte)
    try:
        return bytes(chars).decode("utf-8", errors="replace")
    except Exception:
        return ""


def embed_watermark(signal: list[float], message: str,
                     strength: float = 0.005,
                     sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Embed a text watermark into an audio signal."""
    bits = _text_to_bits(message)
    if not bits or not signal:
        return list(signal)

    # Samples per bit
    spb = len(signal) // len(bits)
    if spb < 100:
        # Signal too short for message
        spb = 100

    result = list(signal)
    carrier_freq = 18500  # Near ultrasonic

    for i, bit in enumerate(bits):
        start = i * spb
        if start >= len(result):
            break
        end = min(start + spb, len(result))

        val = 1.0 if bit == 1 else -1.0
        for j in range(start, end):
            t = j / sample_rate
            # Spread spectrum carrier
            carrier = math.sin(2 * math.pi * carrier_freq * t)
            # PHI modulation
            phi_mod = math.sin(2 * math.pi * carrier_freq / PHI * t) * 0.3
            result[j] += strength * val * (carrier + phi_mod)

    return result


def extract_watermark(signal: list[float], msg_length: int,
                       sample_rate: int = SAMPLE_RATE) -> str:
    """Extract a watermark from a watermarked signal."""
    n_bits = msg_length * 8
    spb = len(signal) // n_bits
    if spb < 100:
        spb = 100

    carrier_freq = 18500
    bits: list[int] = []

    for i in range(n_bits):
        start = i * spb
        if start >= len(signal):
            break
        end = min(start + spb, len(signal))

        correlation = 0.0
        for j in range(start, end):
            t = j / sample_rate
            carrier = math.sin(2 * math.pi * carrier_freq * t)
            phi_mod = math.sin(2 * math.pi * carrier_freq / PHI * t) * 0.3
            correlation += signal[j] * (carrier + phi_mod)

        bits.append(1 if correlation > 0 else 0)

    return _bits_to_text(bits)


def embed_id(signal: list[float], project_id: str,
              sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Embed a short project ID watermark."""
    tag = f"DUBFORGE:{project_id}"
    return embed_watermark(signal, tag, 0.003, sample_rate)


def detect_dubforge(signal: list[float],
                     sample_rate: int = SAMPLE_RATE) -> str | None:
    """Detect DUBFORGE watermark in signal."""
    # Try common ID lengths
    for length in [16, 24, 32, 48]:
        text = extract_watermark(signal, length, sample_rate)
        if text.startswith("DUBFORGE:"):
            return text[9:]
    return None


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


def main() -> None:
    print("Audio Watermark Engine")

    # Generate test signal
    duration = 3.0
    n = int(SAMPLE_RATE * duration)
    signal = [
        math.sin(2 * math.pi * 80 * i / SAMPLE_RATE) * 0.5 +
        math.sin(2 * math.pi * 200 * i / SAMPLE_RATE) * 0.2
        for i in range(n)
    ]

    # Embed watermark
    message = "DUBFORGE:PHI42"
    watermarked = embed_watermark(signal, message, 0.01)
    print(f"  Embedded: '{message}' ({len(message)} chars)")

    # Measure distortion
    diff = sum((a - b) ** 2 for a, b in zip(signal, watermarked))
    snr = 10 * math.log10(
        sum(x * x for x in signal) / max(diff, 1e-10)
    )
    print(f"  SNR: {snr:.1f} dB")

    # Extract
    extracted = extract_watermark(watermarked, len(message))
    print(f"  Extracted: '{extracted}'")
    print(f"  Match: {extracted == message}")

    # ID embed
    id_signal = embed_id(signal, "SESSION42")
    detected = detect_dubforge(id_signal)
    print(f"  ID detected: {detected}")

    print("Done.")


if __name__ == "__main__":
    main()
