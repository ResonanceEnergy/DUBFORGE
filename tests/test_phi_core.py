"""Tests for engine.phi_core — wavetable generation, midi/freq utilities."""

import numpy as np

from engine.phi_core import (
    fibonacci_harmonic_series,
    freq_to_midi,
    generate_phi_core_v1,
    generate_phi_core_v2_wook,
    midi_to_freq,
    phi_amplitude_curve,
    phi_harmonic_series,
)

# ── midi_to_freq / freq_to_midi ──────────────────────────────────────────

class TestMidiFreq:
    def test_a4_440(self):
        assert abs(midi_to_freq(69) - 440.0) < 0.01

    def test_a4_432(self):
        assert abs(midi_to_freq(69, a4=432.0) - 432.0) < 0.01

    def test_middle_c(self):
        # MIDI 60 = C4 ≈ 261.63 Hz
        assert abs(midi_to_freq(60) - 261.63) < 0.1

    def test_roundtrip(self):
        for note in [36, 48, 60, 69, 72, 84]:
            freq = midi_to_freq(note)
            back = freq_to_midi(freq)
            assert back == note

    def test_freq_to_midi_snap(self):
        # 443 Hz should snap to MIDI 69 (A4)
        assert freq_to_midi(443.0) == 69


# ── Harmonic Series ──────────────────────────────────────────────────────

class TestHarmonicSeries:
    def test_phi_harmonic_length(self):
        result = phi_harmonic_series(100.0, 5)
        assert len(result) == 5

    def test_phi_harmonic_first_is_fundamental(self):
        result = phi_harmonic_series(100.0, 3)
        assert abs(result[0] - 100.0) < 0.01

    def test_fibonacci_harmonic_contains_fibonacci_ratios(self):
        result = fibonacci_harmonic_series(100.0)
        # First element is 1*100 = 100
        assert abs(result[0] - 100.0) < 0.01


class TestAmplitudeCurve:
    def test_length(self):
        curve = phi_amplitude_curve(8)
        assert len(curve) == 8

    def test_first_element_is_one(self):
        curve = phi_amplitude_curve(8)
        assert abs(curve[0] - 1.0) < 0.001

    def test_monotonic_decay(self):
        curve = phi_amplitude_curve(8)
        for i in range(1, len(curve)):
            assert curve[i] <= curve[i - 1]


# ── Wavetable Generation ────────────────────────────────────────────────

class TestWavetableGeneration:
    def test_v1_returns_frames(self):
        frames = generate_phi_core_v1(n_frames=4)
        assert len(frames) == 4

    def test_v1_frame_shape(self):
        frames = generate_phi_core_v1(n_frames=2)
        assert frames[0].shape == (2048,)

    def test_v1_frames_normalized(self):
        frames = generate_phi_core_v1(n_frames=4)
        for f in frames:
            assert np.max(np.abs(f)) <= 1.0 + 1e-6

    def test_v2_wook_returns_frames(self):
        frames = generate_phi_core_v2_wook(n_frames=4)
        assert len(frames) == 4

    def test_v2_frame_shape(self):
        frames = generate_phi_core_v2_wook(n_frames=2)
        assert frames[0].shape == (2048,)
