"""Tests for engine.web_preview — WAV analysis, spectrogram, JSON preview."""

import io
import json
import wave
from http.server import HTTPServer

import numpy as np

from engine.web_preview import (
    PreviewResult,
    analyze_wav_bytes,
    generate_spectrogram_data,
    main,
    render_preview_json,
    start_server,
)

SAMPLE_RATE = 44100


def _make_wav_bytes(freq: float = 432.0, dur: float = 0.5) -> bytes:
    """Generate 16-bit mono PCM WAV bytes for testing."""
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ── PreviewResult ────────────────────────────────────────────────────────

class TestPreviewResult:
    def test_creation(self):
        r = PreviewResult("f.wav", 44100, 1.0, 0.5, 0.35, 432.0, 1.618, 1.43)
        assert r.filename == "f.wav"
        assert r.sample_rate == 44100

    def test_fields_count(self):
        import dataclasses
        fields = dataclasses.fields(PreviewResult)
        assert len(fields) == 8


# ── analyze_wav_bytes ────────────────────────────────────────────────────

class TestAnalyzeWavBytes:
    def test_returns_preview_result(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert isinstance(result, PreviewResult)

    def test_filename_default(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.filename == "upload.wav"

    def test_filename_custom(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav, "test.wav")
        assert result.filename == "test.wav"

    def test_sample_rate(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.sample_rate == SAMPLE_RATE

    def test_duration_half_second(self):
        wav = _make_wav_bytes(dur=0.5)
        result = analyze_wav_bytes(wav)
        assert abs(result.duration_s - 0.5) < 0.01

    def test_peak_amplitude_positive(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.peak_amplitude > 0

    def test_rms_positive(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.rms > 0

    def test_spectral_centroid_positive(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.spectral_centroid > 0

    def test_crest_factor_positive(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert result.crest_factor > 0

    def test_phi_ratio_field(self):
        wav = _make_wav_bytes()
        result = analyze_wav_bytes(wav)
        assert isinstance(result.phi_ratio, float)


# ── generate_spectrogram_data ────────────────────────────────────────────

class TestGenerateSpectrogramData:
    def test_returns_dict(self):
        wav = _make_wav_bytes()
        data = generate_spectrogram_data(wav)
        assert isinstance(data, dict)

    def test_has_expected_keys(self):
        wav = _make_wav_bytes()
        data = generate_spectrogram_data(wav)
        for key in ["sample_rate", "n_fft", "hop_size", "n_segments",
                     "n_freq_bins", "magnitudes"]:
            assert key in data, f"Missing key: {key}"

    def test_magnitudes_is_list(self):
        wav = _make_wav_bytes()
        data = generate_spectrogram_data(wav)
        assert isinstance(data["magnitudes"], list)
        assert len(data["magnitudes"]) > 0

    def test_custom_n_fft(self):
        wav = _make_wav_bytes()
        data = generate_spectrogram_data(wav, n_fft=512)
        assert data["n_fft"] == 512


# ── render_preview_json ──────────────────────────────────────────────────

class TestRenderPreviewJson:
    def test_returns_string(self):
        wav = _make_wav_bytes()
        result = render_preview_json(wav)
        assert isinstance(result, str)

    def test_valid_json(self):
        wav = _make_wav_bytes()
        result = render_preview_json(wav)
        data = json.loads(result)
        assert "analysis" in data
        assert "spectrogram" in data

    def test_analysis_has_filename(self):
        wav = _make_wav_bytes()
        data = json.loads(render_preview_json(wav, "demo.wav"))
        assert data["analysis"]["filename"] == "demo.wav"


# ── start_server ─────────────────────────────────────────────────────────

class TestStartServer:
    def test_creates_http_server(self):
        server = start_server(port=0)  # port 0 = OS picks
        assert isinstance(server, HTTPServer)
        server.server_close()


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Web Preview" in captured.out
