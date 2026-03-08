"""Tests for engine/cli.py — DUBFORGE CLI tool."""

import subprocess
import sys
from pathlib import Path

import pytest

CLI_MODULE = "engine.cli"


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", CLI_MODULE, *args],
        capture_output=True, text=True, check=check,
        cwd=str(Path(__file__).resolve().parent.parent),
    )


class TestCLIInfo:
    def test_info_runs(self):
        r = _run_cli("info")
        assert r.returncode == 0
        assert "DUBFORGE" in r.stdout

    def test_info_lists_modules(self):
        r = _run_cli("info")
        assert "phi_core" in r.stdout


class TestCLIRender:
    def test_render_pipeline(self, tmp_path):
        from engine.render_pipeline import export_pipeline_stems
        paths = export_pipeline_stems(str(tmp_path))
        assert len(paths) > 0

    def test_render_batch(self, tmp_path):
        from engine.batch_renderer import export_batch_renders
        paths = export_batch_renders(str(tmp_path))
        assert len(paths) > 0


class TestCLIExport:
    def test_export_samples(self, tmp_path):
        from engine.sample_pack_builder import export_all_packs
        paths = export_all_packs(str(tmp_path))
        assert len(paths) > 0

    def test_export_presets(self, tmp_path):
        from engine.preset_pack_builder import export_all_preset_packs
        paths = export_all_preset_packs(str(tmp_path))
        assert len(paths) > 0

    def test_export_wavetables(self, tmp_path):
        from engine.wavetable_morph import export_morph_wavetables
        paths = export_morph_wavetables(str(tmp_path))
        assert len(paths) > 0

    def test_export_resynth(self, tmp_path):
        from engine.spectral_resynthesis import export_resynth_wavetables
        paths = export_resynth_wavetables(str(tmp_path))
        assert len(paths) > 0

    def test_export_als(self, tmp_path):
        from engine.als_generator import export_all_als
        paths = export_all_als(str(tmp_path))
        assert len(paths) > 0

    def test_export_mix(self, tmp_path):
        from engine.stem_mixer import export_mix_demos
        paths = export_mix_demos(str(tmp_path))
        assert len(paths) > 0


class TestCLIAnalyze:
    def test_analyze_wav(self, tmp_path):
        import wave

        import numpy as np

        from engine.harmonic_analysis import analyze_wav_file

        # Create a test wav
        wav_path = tmp_path / "test.wav"
        sr = 44100
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        samples = np.sin(2 * np.pi * 440 * t)
        data = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())

        result = analyze_wav_file(str(wav_path), "spectral_peaks")
        assert result["analysis_type"] == "spectral_peaks"
        assert result["sample_rate"] == sr
        assert result["duration_s"] > 0

    def test_analyze_phi_detection(self, tmp_path):
        import wave

        import numpy as np

        from engine.harmonic_analysis import analyze_wav_file

        wav_path = tmp_path / "phi_test.wav"
        sr = 44100
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        samples = np.sin(2 * np.pi * 432 * t) + 0.5 * np.sin(2 * np.pi * 432 * 1.618 * t)
        data = np.clip(samples * 16000, -32768, 32767).astype(np.int16)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())

        result = analyze_wav_file(str(wav_path), "phi_detection")
        assert result["analysis_type"] == "phi_detection"

    def test_analyze_missing_file(self):
        from engine.harmonic_analysis import analyze_wav_file
        with pytest.raises(FileNotFoundError):
            analyze_wav_file("/nonexistent/path.wav")


class TestCLIHelp:
    def test_no_args_shows_help(self):
        r = _run_cli(check=False)
        assert r.returncode == 0

    def test_render_help(self):
        r = _run_cli("render", "--help")
        assert "batch" in r.stdout.lower()

    def test_export_help(self):
        r = _run_cli("export", "--help")
        assert "samples" in r.stdout.lower()

    def test_analyze_help(self):
        r = _run_cli("analyze", "--help")
        assert "path" in r.stdout.lower()
