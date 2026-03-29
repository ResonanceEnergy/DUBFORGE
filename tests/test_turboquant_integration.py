"""
Tests for TurboQuant integration across DUBFORGE modules.

Verifies wiring into:
  - AudioBufferPool (compress-on-evict, archive, restore)
  - phi_core (compressed wavetable export)
  - FrequencyAnalyzer (feature vectors, spectral index)
  - WavPool (timbre search)
  - AudioStitcher (compressed export)
  - BatchRenderer (compressed results)
  - AudioPreview (compressed previews)
"""

import math
import os
import pickle
import tempfile

import numpy as np
import pytest


# ── AudioBufferPool integration ──────────────────────────────────────


class TestAudioBufferPoolTQ:
    """Test TurboQuant archive in AudioBufferPool."""

    def test_eviction_compresses_to_archive(self):
        from engine.audio_buffer import AudioBufferPool
        pool = AudioBufferPool(max_buffers=2)

        b1 = pool.allocate(256, label="first")
        b2 = pool.allocate(256, label="second")
        pool.release(b1.buffer_id)

        # Request larger size so free b1 (256) can't be reused → forces eviction
        b3 = pool.allocate(512, label="third")

        assert b1.buffer_id not in pool.buffers
        assert b1.buffer_id in pool._archive
        assert pool._archive[b1.buffer_id].label == "first"

    def test_get_restores_from_archive(self):
        from engine.audio_buffer import AudioBufferPool
        pool = AudioBufferPool(max_buffers=3)

        # Fill with a sine wave
        b1 = pool.allocate(256, label="sine")
        for i in range(256):
            b1.samples[i] = 0.8 * math.sin(2 * math.pi * 440 * i / 48000)
        original = list(b1.samples)

        b2 = pool.allocate(256, label="other")
        pool.release(b1.buffer_id)

        # Compress b1 to archive via compress_idle
        pool.compress_idle()
        assert b1.buffer_id in pool._archive

        # Restore from archive
        restored = pool.get(b1.buffer_id)
        assert restored is not None
        assert restored.label == "sine"
        assert b1.buffer_id not in pool._archive  # removed from archive
        assert b1.buffer_id in pool.buffers  # back in pool

        # Check reconstruction quality (TQ is lossy but should be close)
        mse = sum((a - b) ** 2 for a, b in zip(original, restored.samples)) / 256
        assert mse < 0.1  # reasonable for 3-bit quantization

    def test_compress_idle(self):
        from engine.audio_buffer import AudioBufferPool
        pool = AudioBufferPool(max_buffers=10)

        b1 = pool.allocate(128, label="active")
        b2 = pool.allocate(128, label="idle1")
        b3 = pool.allocate(128, label="idle2")

        pool.release(b2.buffer_id)
        pool.release(b3.buffer_id)

        count = pool.compress_idle()
        assert count == 2
        assert len(pool.buffers) == 1
        assert len(pool._archive) == 2

    def test_stats_include_archive(self):
        from engine.audio_buffer import AudioBufferPool
        pool = AudioBufferPool(max_buffers=2)

        b1 = pool.allocate(256, label="a")
        pool.release(b1.buffer_id)
        pool.compress_idle()

        stats = pool.get_stats()
        assert stats["archived"] == 1
        assert stats["archive_bytes"] > 0


# ── phi_core integration ─────────────────────────────────────────────


class TestPhiCoreTQ:
    """Test TurboQuant wavetable compression in phi_core."""

    def test_write_compressed_wavetable(self):
        from engine.phi_core import write_compressed_wavetable, WAVETABLE_SIZE
        frames = [np.sin(np.linspace(0, 2 * np.pi * (k + 1), WAVETABLE_SIZE))
                  for k in range(8)]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_wt.wav")
            cw = write_compressed_wavetable(path, frames, name="test")
            tq_path = path + ".tq"

            assert os.path.exists(tq_path)
            assert cw.name == "test"
            assert len(cw.frames) == 8
            assert cw.compression_ratio > 1.0

    def test_load_compressed_wavetable(self):
        from engine.phi_core import (
            write_compressed_wavetable, load_compressed_wavetable,
            WAVETABLE_SIZE,
        )
        frames = [np.sin(np.linspace(0, 2 * np.pi * (k + 1), WAVETABLE_SIZE))
                  for k in range(4)]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "roundtrip.wav")
            write_compressed_wavetable(path, frames, name="rt")
            restored = load_compressed_wavetable(path + ".tq")

            assert len(restored) == 4
            for orig, rest in zip(frames, restored):
                mse = np.mean((orig - rest) ** 2) / (np.mean(orig ** 2) + 1e-15)
                assert mse < 0.2  # lossy but close


# ── FrequencyAnalyzer integration ────────────────────────────────────


class TestFrequencyAnalyzerTQ:
    """Test TurboQuant spectral index in FrequencyAnalyzer."""

    def _sine(self, freq: float, dur: float = 0.1, sr: int = 48000) -> list[float]:
        n = int(dur * sr)
        return [math.sin(2 * math.pi * freq * i / sr) for i in range(n)]

    def test_feature_vector_length(self):
        from engine.frequency_analyzer import FrequencyAnalyzer
        analyzer = FrequencyAnalyzer()
        features = analyzer.analyze(self._sine(440))
        vec = features.to_feature_vector()
        assert len(vec) == 10  # 4 spectral + 6 bands

    def test_feature_vector_values_normalized(self):
        from engine.frequency_analyzer import FrequencyAnalyzer
        analyzer = FrequencyAnalyzer()
        features = analyzer.analyze(self._sine(1000))
        vec = features.to_feature_vector()
        # All values should be in reasonable range [0, ~2]
        assert all(-0.1 <= v <= 2.0 for v in vec)

    def test_build_spectral_index(self):
        from engine.frequency_analyzer import FrequencyAnalyzer
        analyzer = FrequencyAnalyzer()

        named = {
            "bass_100": self._sine(100),
            "mid_1000": self._sine(1000),
            "high_5000": self._sine(5000),
        }
        idx = analyzer.build_spectral_index(named)
        assert idx.size() == 3

    def test_find_similar(self):
        from engine.frequency_analyzer import FrequencyAnalyzer
        analyzer = FrequencyAnalyzer()

        named = {
            "bass_100": self._sine(100),
            "mid_1000": self._sine(1000),
            "high_5000": self._sine(5000),
        }
        idx = analyzer.build_spectral_index(named)

        # Query with a bass-like signal should match bass
        results = analyzer.find_similar(self._sine(120), idx, top_k=1)
        assert len(results) >= 1
        # Best match should be bass_100 (closest in frequency)
        assert results[0][0] == "bass_100"


# ── WavPool integration ─────────────────────────────────────────────


class TestWavPoolTQ:
    """Test TurboQuant timbre search in WavPool."""

    def test_spectral_features_field(self):
        from engine.wav_pool import WavFile
        wf = WavFile(path="/tmp/test.wav")
        assert wf.spectral_features is None

    def test_build_timbre_index_empty(self):
        from engine.wav_pool import WavPool
        pool = WavPool()
        idx = pool.build_timbre_index()
        assert idx.size() == 0

    def test_build_timbre_index_with_features(self):
        from engine.wav_pool import WavFile, WavPool
        from engine.frequency_analyzer import SpectralFeatures
        pool = WavPool()

        wf = WavFile(path="/tmp/test.wav", name="test_bass")
        wf.spectral_features = SpectralFeatures(
            centroid=200, bandwidth=100, rolloff=500, flatness=0.1,
            peak_freq=100, band_energy={
                "sub": 0.3, "bass": 0.5, "low_mid": 0.1,
                "mid": 0.05, "high_mid": 0.03, "high": 0.02,
            }, dominant_band="bass",
        )
        pool.add(wf)

        idx = pool.build_timbre_index()
        assert idx.size() == 1


# ── AudioStitcher integration ───────────────────────────────────────


class TestAudioStitcherTQ:
    """Test TurboQuant compression in AudioStitcher."""

    def test_export_compressed(self):
        from engine.audio_stitcher import AudioStitcher, StitchSegment
        stitcher = AudioStitcher()

        seg = StitchSegment(
            samples=[math.sin(2 * math.pi * 440 * i / 48000) for i in range(4800)],
            label="test_tone",
        )
        result = stitcher.stitch_sequential([seg])
        cab = stitcher.export_compressed(result, label="test_stitch")

        assert cab.buffer_id == "test_stitch"
        assert cab.original_length == len(result)
        assert cab.compression_ratio > 1.0

    def test_decompress_arrangement(self):
        from engine.audio_stitcher import AudioStitcher, StitchSegment
        stitcher = AudioStitcher()

        samples = [0.5 * math.sin(2 * math.pi * 220 * i / 48000)
                    for i in range(2400)]
        seg = StitchSegment(samples=samples)
        result = stitcher.stitch_sequential([seg])

        cab = stitcher.export_compressed(result, label="rt")
        restored = AudioStitcher.decompress_arrangement(cab)

        assert len(restored) == len(result)
        mse = sum((a - b) ** 2 for a, b in zip(result, restored)) / len(result)
        assert mse < 0.1


# ── BatchRenderer integration ───────────────────────────────────────


class TestBatchRendererTQ:
    """Test TurboQuant compression in BatchRenderer."""

    def test_render_batch_with_compression(self):
        from engine.batch_renderer import BatchPreset, render_batch
        with tempfile.TemporaryDirectory() as tmpdir:
            preset = BatchPreset("test_tq", "quick", duration_s=0.1)
            results = render_batch(preset, output_dir=tmpdir, compress=True)

            assert len(results) == 4  # 4 frequency variants
            for r in results:
                assert r.compressed is not None
                assert r.compressed.compression_ratio > 1.0

    def test_render_batch_without_compression(self):
        from engine.batch_renderer import BatchPreset, render_batch
        with tempfile.TemporaryDirectory() as tmpdir:
            preset = BatchPreset("test_no_tq", "quick", duration_s=0.1)
            results = render_batch(preset, output_dir=tmpdir, compress=False)

            for r in results:
                assert r.compressed is None


# ── AudioPreview integration ────────────────────────────────────────


class TestAudioPreviewTQ:
    """Test TurboQuant compression in AudioPreview."""

    def test_render_preview_compressed(self):
        from engine.audio_preview import render_preview_compressed
        preview = render_preview_compressed("sub_bass", duration=0.2)

        assert preview.compressed is not None
        assert preview.compressed.compression_ratio > 1.0
        assert "compression_ratio" in preview.metadata
        assert preview.wav_base64  # Still has playable WAV

    def test_render_preview_compressed_different_modules(self):
        from engine.audio_preview import render_preview_compressed
        for mod in ["sub_bass", "lead_synth", "drum_generator"]:
            preview = render_preview_compressed(mod, duration=0.1)
            assert preview.compressed is not None
            assert preview.module_name == mod
