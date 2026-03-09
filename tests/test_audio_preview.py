"""Tests for engine.audio_preview — Session 145."""

import pytest

from engine.audio_preview import AudioPreview


class TestAudioPreview:
    def test_dataclass(self):
        ap = AudioPreview(
            module_name="sub_bass",
            duration_s=1.0,
            sample_rate=44100,
            samples=44100,
            wav_base64="dGVzdA==",
            peak_db=-3.0,
            rms_db=-12.0,
            elapsed_ms=5.0,
        )
        assert ap.module_name == "sub_bass"
        assert ap.sample_rate == 44100

    def test_fields(self):
        ap = AudioPreview(
            module_name="lead_synth",
            duration_s=0.5,
            sample_rate=44100,
            samples=22050,
            wav_base64="YWJj",
            peak_db=-1.0,
            rms_db=-10.0,
            elapsed_ms=3.0,
        )
        assert ap.duration_s == 0.5
        assert ap.peak_db == -1.0
