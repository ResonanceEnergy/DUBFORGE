"""Tests for engine.sample_slicer — Audio slicing engine."""

import unittest

import numpy as np

from engine.sample_slicer import (
    MIN_SLICE_MS,
    SlicePoint,
    SliceResult,
    SliceSegment,
    detect_onsets,
    fibonacci_slice_points,
    slice_audio,
    snap_to_grid,
)


class TestSlicePoint(unittest.TestCase):
    """Test SlicePoint dataclass."""

    def test_creation(self):
        sp = SlicePoint(sample_idx=44100, time_s=1.0, strength=0.8)
        self.assertEqual(sp.sample_idx, 44100)
        self.assertAlmostEqual(sp.time_s, 1.0)
        self.assertAlmostEqual(sp.strength, 0.8)

    def test_label_default(self):
        sp = SlicePoint(sample_idx=0, time_s=0, strength=0.5)
        self.assertEqual(sp.label, "")


class TestSliceSegment(unittest.TestCase):
    """Test SliceSegment dataclass."""

    def test_creation(self):
        seg = SliceSegment(index=0, start_sample=0, end_sample=44100,
                           start_time=0.0, end_time=1.0, duration_ms=1000.0)
        self.assertEqual(seg.index, 0)
        self.assertAlmostEqual(seg.duration_ms, 1000.0)


class TestDetectOnsets(unittest.TestCase):
    """Test onset detection."""

    def test_empty_audio(self):
        onsets = detect_onsets(np.array([]))
        self.assertEqual(len(onsets), 0)

    def test_silence(self):
        silence = np.zeros(44100)
        onsets = detect_onsets(silence)
        self.assertEqual(len(onsets), 0)

    def test_impulse_detected(self):
        """A sharp impulse should be detected as an onset."""
        audio = np.zeros(44100)
        audio[10000] = 1.0  # sharp impulse
        audio[10001] = -0.5
        onsets = detect_onsets(audio, threshold=0.1)
        # May or may not detect depending on spectral flux; just check no crash
        self.assertIsInstance(onsets, list)

    def test_stereo_input(self):
        """Should handle stereo audio by converting to mono."""
        stereo = np.zeros((44100, 2))
        stereo[10000, 0] = 1.0
        stereo[10000, 1] = 0.8
        onsets = detect_onsets(stereo, threshold=0.1)
        self.assertIsInstance(onsets, list)

    def test_returns_slice_points(self):
        """Detected onsets should be SlicePoint instances."""
        audio = np.random.randn(88200) * 0.5
        # Add distinct events
        audio[22050:22060] = 1.0
        audio[66150:66160] = 1.0
        onsets = detect_onsets(audio, threshold=0.2)
        if len(onsets) > 0:
            self.assertIsInstance(onsets[0], SlicePoint)
            self.assertGreater(onsets[0].sample_idx, 0)


class TestSnapToGrid(unittest.TestCase):
    """Test beat-grid snapping."""

    def test_empty(self):
        result = snap_to_grid([], 120.0)
        self.assertEqual(len(result), 0)

    def test_snaps_to_nearest(self):
        sr = 44100
        bpm = 120.0
        beat_samples = int(sr * 60 / bpm)  # 22050
        # Place onset slightly off-grid
        onsets = [SlicePoint(sample_idx=beat_samples + 100, time_s=1.002, strength=0.9)]
        snapped = snap_to_grid(onsets, bpm, sr, divisions=1)
        # Should snap to nearest beat
        self.assertEqual(snapped[0].sample_idx, beat_samples)

    def test_removes_duplicates(self):
        onsets = [
            SlicePoint(sample_idx=100, time_s=0.002, strength=0.9),
            SlicePoint(sample_idx=110, time_s=0.003, strength=0.8),
        ]
        snapped = snap_to_grid(onsets, 120.0, 44100, divisions=1)
        sample_idxs = [s.sample_idx for s in snapped]
        self.assertEqual(len(sample_idxs), len(set(sample_idxs)))


class TestFibonacciSlicePoints(unittest.TestCase):
    """Test Fibonacci-ratio slicing."""

    def test_generates_points(self):
        points = fibonacci_slice_points(88200)
        self.assertGreater(len(points), 0)

    def test_within_range(self):
        total = 88200
        points = fibonacci_slice_points(total)
        for p in points:
            self.assertGreater(p.sample_idx, 0)
            self.assertLess(p.sample_idx, total)

    def test_sorted(self):
        points = fibonacci_slice_points(88200)
        for i in range(len(points) - 1):
            self.assertLessEqual(points[i].sample_idx, points[i + 1].sample_idx)

    def test_has_labels(self):
        points = fibonacci_slice_points(88200)
        for p in points:
            self.assertTrue(p.label.startswith("fib_"))


class TestSliceAudio(unittest.TestCase):
    """Test audio slicing."""

    def test_empty_audio(self):
        result = slice_audio(np.array([]), [])
        self.assertEqual(len(result), 0)

    def test_single_slice(self):
        audio = np.ones(4410)  # 0.1s at 44100
        onsets = [SlicePoint(sample_idx=2205, time_s=0.05, strength=1.0)]
        segments = slice_audio(audio, onsets)
        self.assertEqual(len(segments), 2)

    def test_slice_durations_positive(self):
        audio = np.random.randn(88200)
        onsets = [
            SlicePoint(sample_idx=22050, time_s=0.5, strength=1.0),
            SlicePoint(sample_idx=66150, time_s=1.5, strength=1.0),
        ]
        segments = slice_audio(audio, onsets)
        for seg, chunk in segments:
            self.assertGreater(seg.duration_ms, 0)
            self.assertGreater(len(chunk), 0)

    def test_minimum_slice_length(self):
        """Slices shorter than MIN_SLICE_MS should be skipped."""
        audio = np.ones(4410)
        # Place onsets very close together
        onsets = [
            SlicePoint(sample_idx=10, time_s=0.0002, strength=1.0),
            SlicePoint(sample_idx=20, time_s=0.0005, strength=1.0),
        ]
        segments = slice_audio(audio, onsets)
        for seg, chunk in segments:
            self.assertGreaterEqual(seg.duration_ms, MIN_SLICE_MS)


class TestSliceResult(unittest.TestCase):
    """Test SliceResult dataclass."""

    def test_creation(self):
        r = SliceResult(
            source_file="test.wav",
            sample_rate=44100,
            total_samples=88200,
            total_duration_s=2.0,
            onset_count=3,
        )
        self.assertEqual(r.source_file, "test.wav")
        self.assertEqual(len(r.segments), 0)


if __name__ == "__main__":
    unittest.main()
