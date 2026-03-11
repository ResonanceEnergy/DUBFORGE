"""
DUBFORGE — Format Converter  (Session 193)

Audio format conversion utilities: WAV bit-depth,
sample rate conversion, normalization, mono/stereo.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class AudioInfo:
    """Audio file information."""
    path: str
    channels: int
    sample_width: int  # bytes
    sample_rate: int
    num_frames: int
    duration: float
    bit_depth: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "duration": round(self.duration, 3),
            "frames": self.num_frames,
        }


class FormatConverter:
    """Audio format conversion engine."""

    def __init__(self, output_dir: str = "output/converted"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_info(self, path: str) -> AudioInfo | None:
        """Get audio file information."""
        if not os.path.exists(path):
            return None
        try:
            with wave.open(path, "r") as wf:
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                sr = wf.getframerate()
                nf = wf.getnframes()
                return AudioInfo(
                    path=path, channels=ch, sample_width=sw,
                    sample_rate=sr, num_frames=nf,
                    duration=nf / sr if sr > 0 else 0.0,
                    bit_depth=sw * 8,
                )
        except Exception:
            return None

    def read_wav(self, path: str) -> tuple[list[float], int, int]:
        """Read WAV file as normalized float samples."""
        with wave.open(path, "r") as wf:
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            raw = wf.readframes(wf.getnframes())

        if sw == 1:
            fmt = f"<{len(raw)}B"
            samples_int = struct.unpack(fmt, raw)
            samples = [(s - 128) / 128.0 for s in samples_int]
        elif sw == 2:
            fmt = f"<{len(raw) // 2}h"
            samples_int = struct.unpack(fmt, raw)
            samples = [s / 32768.0 for s in samples_int]
        elif sw == 3:
            samples = []
            for i in range(0, len(raw), 3):
                val = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
                if val >= 0x800000:
                    val -= 0x1000000
                samples.append(val / 8388608.0)
        else:
            fmt = f"<{len(raw) // 4}i"
            samples_int = struct.unpack(fmt, raw)
            samples = [s / 2147483648.0 for s in samples_int]

        return samples, sr, ch

    def write_wav(self, path: str, samples: list[float],
                  sample_rate: int = SAMPLE_RATE, channels: int = 1,
                  bit_depth: int = 16) -> str:
        """Write samples to WAV file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        sw = bit_depth // 8

        with wave.open(path, "w") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sw)
            wf.setframerate(sample_rate)

            if bit_depth == 16:
                data = struct.pack(
                    f"<{len(samples)}h",
                    *[max(-32768, min(32767, int(s * 32767)))
                      for s in samples]
                )
            elif bit_depth == 24:
                buf = bytearray()
                for s in samples:
                    val = max(-8388608, min(8388607, int(s * 8388607)))
                    if val < 0:
                        val += 0x1000000
                    buf.append(val & 0xFF)
                    buf.append((val >> 8) & 0xFF)
                    buf.append((val >> 16) & 0xFF)
                data = bytes(buf)
            elif bit_depth == 32:
                data = struct.pack(
                    f"<{len(samples)}i",
                    *[max(-2147483648, min(2147483647,
                      int(s * 2147483647))) for s in samples]
                )
            else:
                data = struct.pack(
                    f"<{len(samples)}h",
                    *[max(-32768, min(32767, int(s * 32767)))
                      for s in samples]
                )

            wf.writeframes(data)
        return path

    def convert_bit_depth(self, path: str, target_bits: int = 24,
                          output: str = "") -> str:
        """Convert WAV to different bit depth."""
        samples, sr, ch = self.read_wav(path)
        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir,
                                   f"{base}_{target_bits}bit.wav")
        return self.write_wav(output, samples, sr, ch, target_bits)

    def convert_sample_rate(self, path: str, target_rate: int = 48000,
                            output: str = "") -> str:
        """Resample audio (linear interpolation)."""
        samples, sr, ch = self.read_wav(path)

        if sr == target_rate:
            return path

        ratio = target_rate / sr
        new_len = int(len(samples) * ratio)
        resampled: list[float] = []

        for i in range(new_len):
            src_pos = i / ratio
            idx = int(src_pos)
            frac = src_pos - idx
            if idx + 1 < len(samples):
                val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
            elif idx < len(samples):
                val = samples[idx]
            else:
                val = 0.0
            resampled.append(val)

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir,
                                   f"{base}_{target_rate}hz.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, resampled, target_rate, ch, bits)

    def mono_to_stereo(self, path: str, output: str = "") -> str:
        """Convert mono to stereo (duplicate channels)."""
        samples, sr, ch = self.read_wav(path)
        if ch == 2:
            return path

        stereo: list[float] = []
        for s in samples:
            stereo.append(s)  # L
            stereo.append(s)  # R

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir, f"{base}_stereo.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, stereo, sr, 2, bits)

    def stereo_to_mono(self, path: str, output: str = "") -> str:
        """Convert stereo to mono (average channels)."""
        samples, sr, ch = self.read_wav(path)
        if ch == 1:
            return path

        mono: list[float] = []
        for i in range(0, len(samples), ch):
            avg = sum(samples[i:i + ch]) / ch
            mono.append(avg)

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir, f"{base}_mono.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, mono, sr, 1, bits)

    def normalize(self, path: str, target_db: float = -1.0,
                  output: str = "") -> str:
        """Normalize audio to target peak level."""
        samples, sr, ch = self.read_wav(path)

        peak = max(abs(s) for s in samples) if samples else 1.0
        if peak == 0:
            return path

        target_linear = 10.0 ** (target_db / 20.0)
        gain = target_linear / peak

        normalized = [s * gain for s in samples]

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir, f"{base}_normalized.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, normalized, sr, ch, bits)

    def trim_silence(self, path: str, threshold_db: float = -60.0,
                     output: str = "") -> str:
        """Trim silence from start and end."""
        samples, sr, ch = self.read_wav(path)
        threshold = 10.0 ** (threshold_db / 20.0)

        start = 0
        for i, s in enumerate(samples):
            if abs(s) > threshold:
                start = i
                break

        end = len(samples) - 1
        for i in range(len(samples) - 1, -1, -1):
            if abs(samples[i]) > threshold:
                end = i
                break

        trimmed = samples[start:end + 1]

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir, f"{base}_trimmed.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, trimmed, sr, ch, bits)

    def fade(self, path: str, fade_in_ms: float = 10.0,
             fade_out_ms: float = 50.0, output: str = "") -> str:
        """Apply fade in/out to audio."""
        samples, sr, ch = self.read_wav(path)

        fade_in_samples = int(sr * fade_in_ms / 1000)
        fade_out_samples = int(sr * fade_out_ms / 1000)

        result = list(samples)

        for i in range(min(fade_in_samples, len(result))):
            envelope = i / fade_in_samples
            result[i] *= envelope

        for i in range(min(fade_out_samples, len(result))):
            idx = len(result) - 1 - i
            envelope = i / fade_out_samples
            result[idx] *= envelope

        if not output:
            base = os.path.splitext(os.path.basename(path))[0]
            output = os.path.join(self.output_dir, f"{base}_faded.wav")

        info = self.get_info(path)
        bits = info.bit_depth if info else 16
        return self.write_wav(output, result, sr, ch, bits)

    def phi_resample(self, path: str, output: str = "") -> str:
        """Resample at PHI ratio of original rate."""
        info = self.get_info(path)
        if not info:
            return path
        target = int(info.sample_rate * PHI)
        return self.convert_sample_rate(path, target, output)

    def batch_convert(self, paths: list[str], target_bits: int = 24,
                      target_rate: int = 0) -> list[str]:
        """Batch convert multiple files."""
        results: list[str] = []
        for p in paths:
            if not os.path.exists(p):
                continue
            out = self.convert_bit_depth(p, target_bits)
            if target_rate > 0:
                out = self.convert_sample_rate(out, target_rate)
            results.append(out)
        return results


def main() -> None:
    print("Format Converter")

    converter = FormatConverter()

    # Generate test WAV
    sr = 44100
    dur = 0.5
    n = int(sr * dur)
    samples = [0.8 * math.sin(2 * math.pi * 432 * i / sr) for i in range(n)]
    test_path = converter.write_wav(
        os.path.join(converter.output_dir, "test_source.wav"),
        samples, sr, 1, 16
    )

    info = converter.get_info(test_path)
    if info:
        print(f"  Source: {info.to_dict()}")

    # Convert to 24-bit
    out_24 = converter.convert_bit_depth(test_path, 24)
    info24 = converter.get_info(out_24)
    if info24:
        print(f"  24-bit: {info24.to_dict()}")

    # Normalize
    out_norm = converter.normalize(test_path, -3.0)
    print(f"  Normalized: {out_norm}")

    # Mono to stereo
    out_stereo = converter.mono_to_stereo(test_path)
    info_s = converter.get_info(out_stereo)
    if info_s:
        print(f"  Stereo: channels={info_s.channels}")

    print("Done.")


if __name__ == "__main__":
    main()
