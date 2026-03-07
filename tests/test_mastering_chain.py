"""Tests for engine.mastering_chain — Mastering DSP chain."""

import unittest

import numpy as np

from engine.mastering_chain import (
    MasterReport,
    MasterSettings,
    apply_eq,
    compress,
    db_to_linear,
    dubstep_master_settings,
    high_shelf,
    limit,
    linear_to_db,
    loudness_normalize,
    low_shelf,
    master,
    peak_db,
    peaking_eq,
    rms_db,
    stereo_widen,
    streaming_master_settings,
)


class TestDBConversions(unittest.TestCase):
    """Test dB ↔ linear conversions."""

    def test_unity(self):
        self.assertAlmostEqual(db_to_linear(0.0), 1.0)

    def test_minus_6(self):
        self.assertAlmostEqual(db_to_linear(-6.0), 0.5011872, places=4)

    def test_roundtrip(self):
        for db in [-20, -6, 0, 6, 12]:
            self.assertAlmostEqual(linear_to_db(db_to_linear(db)), db, places=4)

    def test_zero_linear(self):
        self.assertEqual(linear_to_db(0), -120.0)


class TestPeakDB(unittest.TestCase):
    """Test peak measurement."""

    def test_unity_signal(self):
        audio = np.array([0.0, 0.5, 1.0, -0.5])
        self.assertAlmostEqual(peak_db(audio), 0.0)

    def test_half_amplitude(self):
        audio = np.array([0.0, 0.5, -0.5])
        self.assertAlmostEqual(peak_db(audio), -6.0206, places=2)


class TestRmsDB(unittest.TestCase):
    """Test RMS measurement."""

    def test_dc_signal(self):
        audio = np.ones(1000) * 0.5
        self.assertAlmostEqual(rms_db(audio), -6.0206, places=2)

    def test_sine(self):
        t = np.linspace(0, 1, 44100)
        audio = np.sin(2 * np.pi * 440 * t)
        # RMS of sine = 1/sqrt(2) ≈ -3.01 dB
        self.assertAlmostEqual(rms_db(audio), -3.01, places=1)


class TestLowShelf(unittest.TestCase):
    """Test low-shelf filter."""

    def test_zero_gain_passthrough(self):
        audio = np.random.randn(4410)
        result = low_shelf(audio, 100.0, 0.0)
        np.testing.assert_array_equal(result, audio)

    def test_positive_gain_boosts(self):
        """Low-shelf boost should increase energy of low-freq content."""
        t = np.linspace(0, 1, 44100)
        audio = np.sin(2 * np.pi * 50 * t)  # 50 Hz
        boosted = low_shelf(audio, 200.0, 6.0)
        self.assertGreater(np.max(np.abs(boosted)), np.max(np.abs(audio)) * 0.9)

    def test_mono_shape(self):
        audio = np.random.randn(1000)
        result = low_shelf(audio, 100.0, 3.0)
        self.assertEqual(result.shape, audio.shape)


class TestHighShelf(unittest.TestCase):
    """Test high-shelf filter."""

    def test_zero_gain_passthrough(self):
        audio = np.random.randn(4410)
        result = high_shelf(audio, 8000.0, 0.0)
        np.testing.assert_array_equal(result, audio)

    def test_mono_shape(self):
        audio = np.random.randn(1000)
        result = high_shelf(audio, 8000.0, 3.0)
        self.assertEqual(result.shape, audio.shape)


class TestPeakingEQ(unittest.TestCase):
    """Test parametric EQ."""

    def test_zero_gain_passthrough(self):
        audio = np.random.randn(4410)
        result = peaking_eq(audio, 1000.0, 0.0)
        np.testing.assert_array_equal(result, audio)

    def test_shape_preserved(self):
        audio = np.random.randn(1000)
        result = peaking_eq(audio, 2500.0, 3.0, q=1.0)
        self.assertEqual(result.shape, audio.shape)


class TestApplyEQ(unittest.TestCase):
    """Test full EQ chain."""

    def test_flat_settings_approx_passthrough(self):
        settings = MasterSettings()  # All EQ gains are 0
        audio = np.random.randn(4410)
        result = apply_eq(audio, settings)
        np.testing.assert_array_almost_equal(result, audio, decimal=10)


class TestCompress(unittest.TestCase):
    """Test compressor."""

    def test_reduces_dynamic_range(self):
        audio = np.random.randn(44100) * 0.5
        # Add loud peaks
        audio[10000:10010] = 1.0
        audio[30000:30010] = -1.0

        settings = MasterSettings(compression_threshold_db=-6.0, compression_ratio=4.0)
        compressed = compress(audio, settings)
        # Peak should be reduced
        self.assertLessEqual(np.max(np.abs(compressed)), np.max(np.abs(audio)))

    def test_shape_mono(self):
        audio = np.random.randn(1000)
        settings = MasterSettings()
        result = compress(audio, settings)
        self.assertEqual(result.shape, audio.shape)

    def test_shape_stereo(self):
        audio = np.random.randn(1000, 2)
        settings = MasterSettings()
        result = compress(audio, settings)
        self.assertEqual(result.shape, audio.shape)


class TestLimit(unittest.TestCase):
    """Test brickwall limiter."""

    def test_ceiling_respected(self):
        audio = np.random.randn(44100)
        limited = limit(audio, ceiling_db=-1.0)
        ceiling_lin = db_to_linear(-1.0)
        self.assertLessEqual(np.max(np.abs(limited)), ceiling_lin + 0.01)

    def test_quiet_signal_unchanged(self):
        audio = np.ones(1000) * 0.01
        limited = limit(audio, ceiling_db=-1.0)
        np.testing.assert_array_almost_equal(limited, audio, decimal=3)


class TestStereoWiden(unittest.TestCase):
    """Test stereo width adjustment."""

    def test_mono_passthrough(self):
        audio = np.random.randn(1000)
        result = stereo_widen(audio, width=1.5)
        np.testing.assert_array_equal(result, audio)

    def test_unity_width_passthrough(self):
        audio = np.random.randn(1000, 2)
        result = stereo_widen(audio, width=1.0)
        np.testing.assert_array_equal(result, audio)

    def test_wider_increases_sides(self):
        left = np.sin(np.linspace(0, 2 * np.pi, 1000))
        right = np.cos(np.linspace(0, 2 * np.pi, 1000))
        audio = np.column_stack([left, right])
        wider = stereo_widen(audio, width=2.0)
        # Side content should be amplified
        orig_side = np.sum(np.abs(audio[:, 0] - audio[:, 1]))
        wide_side = np.sum(np.abs(wider[:, 0] - wider[:, 1]))
        self.assertGreater(wide_side, orig_side)


class TestLoudnessNormalize(unittest.TestCase):
    """Test loudness normalization."""

    def test_gain_applied(self):
        audio = np.ones(44100) * 0.01
        normalized, gain = loudness_normalize(audio, target_lufs=-14.0)
        self.assertNotEqual(gain, 0.0)

    def test_silent_signal(self):
        audio = np.zeros(44100)
        normalized, gain = loudness_normalize(audio, target_lufs=-14.0)
        self.assertEqual(gain, 0.0)


class TestMaster(unittest.TestCase):
    """Test full mastering chain."""

    def test_returns_audio_and_report(self):
        audio = np.random.randn(44100) * 0.3
        mastered, report = master(audio)
        self.assertEqual(mastered.shape, audio.shape)
        self.assertIsInstance(report, MasterReport)

    def test_report_has_measurements(self):
        audio = np.random.randn(44100) * 0.3
        mastered, report = master(audio)
        self.assertNotEqual(report.input_peak_db, 0.0)
        self.assertNotEqual(report.output_peak_db, 0.0)

    def test_custom_settings(self):
        audio = np.random.randn(44100) * 0.3
        settings = dubstep_master_settings()
        mastered, report = master(audio, settings=settings)
        self.assertEqual(report.settings.target_lufs, -10.0)


class TestMasterSettings(unittest.TestCase):
    """Test master settings dataclass."""

    def test_defaults(self):
        s = MasterSettings()
        self.assertEqual(s.target_lufs, -14.0)
        self.assertTrue(s.limiter_enabled)

    def test_dubstep_preset(self):
        s = dubstep_master_settings()
        self.assertEqual(s.target_lufs, -10.0)
        self.assertGreater(s.eq_low_shelf_db, 0)

    def test_streaming_preset(self):
        s = streaming_master_settings()
        self.assertEqual(s.target_lufs, -14.0)


if __name__ == "__main__":
    unittest.main()
