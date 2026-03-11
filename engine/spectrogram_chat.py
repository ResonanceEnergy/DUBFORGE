"""
DUBFORGE — Spectrogram Chat Engine  (Session 146)

Generates spectrograms as base64 PNG images for inline display
in the SUBPHONICS browser chat interface.

Uses pure numpy FFT — no matplotlib dependency.
Outputs a simple PNG heatmap via raw PNG encoding.
"""

import base64
import struct
import time
import zlib
from dataclasses import dataclass, field

import numpy as np

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class SpectrogramResult:
    """Result of a spectrogram generation."""
    module_name: str
    png_base64: str
    width: int
    height: int
    freq_range_hz: tuple[float, float]
    time_range_s: tuple[float, float]
    peak_freq_hz: float
    elapsed_ms: float
    metadata: dict = field(default_factory=dict)


def _compute_spectrogram(signal: np.ndarray,
                         sr: int = SAMPLE_RATE,
                         n_fft: int = 1024,
                         hop: int = 256,
                         max_freq: float = 8000.0
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute STFT spectrogram. Returns (S_db, freqs, times)."""
    # Pad signal to fill final frame
    pad_len = n_fft - (len(signal) % hop)
    signal = np.concatenate([signal, np.zeros(pad_len)])

    window = np.hanning(n_fft)
    n_frames = (len(signal) - n_fft) // hop + 1
    n_bins = n_fft // 2 + 1

    S = np.zeros((n_bins, n_frames))
    for i in range(n_frames):
        start = i * hop
        frame = signal[start:start + n_fft] * window
        fft = np.fft.rfft(frame)
        S[:, i] = np.abs(fft)

    # Convert to dB
    S_db = 20 * np.log10(S + 1e-10)
    S_db = np.clip(S_db, -80, 0)

    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    times = np.arange(n_frames) * hop / sr

    # Trim to max_freq
    freq_mask = freqs <= max_freq
    S_db = S_db[freq_mask, :]
    freqs = freqs[freq_mask]

    return S_db, freqs, times


def _spectrogram_to_rgba(S_db: np.ndarray,
                         width: int = 400,
                         height: int = 200) -> np.ndarray:
    """Convert spectrogram matrix to RGBA pixel array with purple/blue colormap."""
    # Normalize to 0-1
    S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-10)

    # Resize to target dimensions
    from_h, from_w = S_norm.shape
    # Flip vertically (low freqs at bottom)
    S_norm = S_norm[::-1, :]

    # Simple nearest-neighbor resize
    rows = np.linspace(0, from_h - 1, height).astype(int)
    cols = np.linspace(0, from_w - 1, width).astype(int)
    S_resized = S_norm[np.ix_(rows, cols)]

    # DUBFORGE colormap: dark → purple → blue → cyan → white
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            v = S_resized[y, x]
            if v < 0.25:
                # Dark → deep purple
                t = v / 0.25
                r = int(10 + 50 * t)
                g = int(10 * t)
                b = int(15 + 60 * t)
            elif v < 0.5:
                # Purple → blue
                t = (v - 0.25) / 0.25
                r = int(60 + 120 * t)
                g = int(10 + 30 * t)
                b = int(75 + 180 * t)
            elif v < 0.75:
                # Blue → cyan
                t = (v - 0.5) / 0.25
                r = int(180 - 140 * t)
                g = int(40 + 172 * t)
                b = int(255)
            else:
                # Cyan → white
                t = (v - 0.75) / 0.25
                r = int(40 + 215 * t)
                g = int(212 + 43 * t)
                b = int(255)
            rgba[y, x] = [r, g, b, 255]

    return rgba


def _encode_png(rgba: np.ndarray) -> bytes:
    """Encode RGBA array as PNG bytes (minimal pure-Python encoder)."""
    height, width, _ = rgba.shape

    def write_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = write_chunk(b"IHDR", ihdr_data)

    # IDAT — raw pixel data with filter byte (0 = none) per row
    raw = b""
    for y in range(height):
        raw += b'\x00'  # filter: none
        raw += rgba[y].tobytes()
    compressed = zlib.compress(raw)
    idat = write_chunk(b"IDAT", compressed)

    # IEND
    iend = write_chunk(b"IEND", b"")

    return sig + ihdr + idat + iend


def generate_spectrogram(signal: np.ndarray,
                         sr: int = SAMPLE_RATE,
                         width: int = 400,
                         height: int = 200,
                         max_freq: float = 8000.0
                         ) -> tuple[bytes, dict]:
    """Generate spectrogram PNG from signal. Returns (png_bytes, metadata)."""
    S_db, freqs, times = _compute_spectrogram(signal, sr, max_freq=max_freq)

    # Find peak frequency
    mean_spectrum = np.mean(S_db, axis=1)
    peak_idx = np.argmax(mean_spectrum)
    peak_freq = float(freqs[peak_idx]) if peak_idx < len(freqs) else 0.0

    rgba = _spectrogram_to_rgba(S_db, width, height)
    png_bytes = _encode_png(rgba)

    meta = {
        "freq_range": (float(freqs[0]), float(freqs[-1])),
        "time_range": (float(times[0]), float(times[-1])),
        "peak_freq_hz": peak_freq,
        "n_fft_bins": len(freqs),
        "n_frames": len(times),
    }
    return png_bytes, meta


def spectrogram_from_module(module_name: str,
                            duration: float = 1.0,
                            freq: float = 55.0,
                            width: int = 400,
                            height: int = 200) -> SpectrogramResult:
    """Generate spectrogram for a module's preview signal."""
    from engine.audio_preview import generate_preview_signal

    t0 = time.time()
    signal = generate_preview_signal(module_name, duration, freq)
    png_bytes, meta = generate_spectrogram(signal, width=width, height=height)
    png_b64 = base64.b64encode(png_bytes).decode("ascii")
    elapsed = round((time.time() - t0) * 1000, 1)

    return SpectrogramResult(
        module_name=module_name,
        png_base64=png_b64,
        width=width,
        height=height,
        freq_range_hz=meta["freq_range"],
        time_range_s=meta["time_range"],
        peak_freq_hz=meta["peak_freq_hz"],
        elapsed_ms=elapsed,
    )


def spectrogram_to_html(result: SpectrogramResult) -> str:
    """Generate HTML image tag for inline display."""
    return (
        f'<img src="data:image/png;base64,{result.png_base64}" '
        f'width="{result.width}" height="{result.height}" '
        f'style="border-radius:8px;border:1px solid #2a2a3a">'
        f'<br><small>{result.module_name} | peak: {result.peak_freq_hz:.0f} Hz | '
        f'{result.elapsed_ms}ms</small>'
    )


def spectrogram_to_dict(result: SpectrogramResult) -> dict:
    """Convert to JSON-serializable dict."""
    return {
        "module": result.module_name,
        "png_base64": result.png_base64,
        "width": result.width,
        "height": result.height,
        "freq_range_hz": list(result.freq_range_hz),
        "time_range_s": list(result.time_range_s),
        "peak_freq_hz": result.peak_freq_hz,
        "elapsed_ms": result.elapsed_ms,
    }


def main() -> None:
    modules = ["sub_bass", "wobble_bass", "lead_synth", "drum_generator",
               "pad_synth", "arp_synth"]
    print(f"Spectrogram Chat Engine — generating {len(modules)} spectrograms")
    for mod in modules:
        result = spectrogram_from_module(mod)
        print(f"  {mod}: {result.width}×{result.height}, "
              f"peak {result.peak_freq_hz:.0f} Hz, "
              f"{len(result.png_base64)} base64 chars, "
              f"{result.elapsed_ms}ms")
    print("Done.")


if __name__ == "__main__":
    main()
