"""
DUBFORGE — Web Preview  (Session 137)

Lightweight HTTP endpoint for previewing renders:
upload .wav → get phi-analysis JSON + spectrogram PNG.
All pure Python — no Flask/FastAPI required.
"""

import io
import json
import wave
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class PreviewResult:
    """Result from analyzing a preview wav."""
    filename: str
    sample_rate: int
    duration_s: float
    peak_amplitude: float
    rms: float
    spectral_centroid: float
    phi_ratio: float
    crest_factor: float


def analyze_wav_bytes(wav_bytes: bytes, filename: str = "upload.wav") -> PreviewResult:
    """Analyze raw WAV bytes and return a PreviewResult."""
    bio = io.BytesIO(wav_bytes)
    with wave.open(bio, "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        raw = wf.readframes(n_frames)

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    if n_channels > 1:
        samples = samples[::n_channels]  # take first channel

    duration = len(samples) / sr
    peak = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
    rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

    # Spectral centroid via FFT
    if len(samples) > 256:
        spectrum = np.abs(np.fft.rfft(samples[:min(len(samples), 8192)]))
        freqs = np.fft.rfftfreq(min(len(samples), 8192), 1.0 / sr)
        total = np.sum(spectrum) + 1e-12
        centroid = float(np.sum(freqs * spectrum) / total)
    else:
        centroid = 0.0

    # Phi ratio — ratio of spectral centroid to fundamental-ish
    fund_est = centroid / PHI if centroid > 0 else 0.0
    phi_ratio = centroid / fund_est if fund_est > 0 else 0.0

    crest = peak / rms if rms > 0 else 0.0

    return PreviewResult(
        filename=filename,
        sample_rate=sr,
        duration_s=round(duration, 4),
        peak_amplitude=round(peak, 6),
        rms=round(rms, 6),
        spectral_centroid=round(centroid, 2),
        phi_ratio=round(phi_ratio, 6),
        crest_factor=round(crest, 4),
    )


def generate_spectrogram_data(wav_bytes: bytes,
                              n_fft: int = 1024) -> dict:
    """Generate basic spectrogram data as JSON-serializable dict."""
    bio = io.BytesIO(wav_bytes)
    with wave.open(bio, "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    hop = n_fft // 2
    n_segments = max(1, (len(samples) - n_fft) // hop)
    n_segments = min(n_segments, 128)  # cap for JSON size

    magnitudes = []
    for i in range(n_segments):
        start = i * hop
        seg = samples[start:start + n_fft]
        if len(seg) < n_fft:
            seg = np.pad(seg, (0, n_fft - len(seg)))
        spectrum = np.abs(np.fft.rfft(seg))
        # Downsample freq bins to 64
        if len(spectrum) > 64:
            indices = np.linspace(0, len(spectrum) - 1, 64, dtype=int)
            spectrum = spectrum[indices]
        magnitudes.append([round(float(v), 4) for v in spectrum])

    return {
        "sample_rate": sr,
        "n_fft": n_fft,
        "hop_size": hop,
        "n_segments": n_segments,
        "n_freq_bins": len(magnitudes[0]) if magnitudes else 0,
        "magnitudes": magnitudes,
    }


def render_preview_json(wav_bytes: bytes, filename: str = "upload.wav") -> str:
    """Full preview: analysis + spectrogram as JSON string."""
    analysis = analyze_wav_bytes(wav_bytes, filename)
    spectro = generate_spectrogram_data(wav_bytes)
    return json.dumps({
        "analysis": asdict(analysis),
        "spectrogram": spectro,
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# SIMPLE HTTP HANDLER
# ═══════════════════════════════════════════════════════════════════════════

class PreviewHandler(BaseHTTPRequestHandler):
    """HTTP handler for preview endpoints."""

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "engine": "DUBFORGE"})
        elif self.path == "/info":
            self._respond(200, {
                "endpoints": ["/health", "/info", "/analyze"],
                "methods": {"analyze": "POST .wav bytes"},
            })
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/analyze":
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                self._respond(400, {"error": "no data"})
                return
            body = self.rfile.read(length)
            try:
                result = render_preview_json(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(result.encode())
            except Exception as e:
                self._respond(500, {"error": str(e)})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, data: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # silence logs


def start_server(port: int = 8432) -> HTTPServer:
    """Create and return (but don't run) the preview server."""
    server = HTTPServer(("127.0.0.1", port), PreviewHandler)
    return server


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # Generate a test signal to demonstrate analysis
    dur = 1.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * 432 * t)
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    wav_bytes = buf.getvalue()

    result = analyze_wav_bytes(wav_bytes, "test_432hz.wav")
    print("Web Preview: analysis demo")
    print(f"  Duration: {result.duration_s}s  Peak: {result.peak_amplitude}")
    print(f"  RMS: {result.rms}  Centroid: {result.spectral_centroid} Hz")
    print(f"  Phi ratio: {result.phi_ratio}  Crest: {result.crest_factor}")
    print("  Server ready on port 8432 (call start_server())")


if __name__ == "__main__":
    main()
