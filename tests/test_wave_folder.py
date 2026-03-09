"""Tests for engine.wave_folder — Session 159."""
import math
import pytest
from engine.wave_folder import (
    fold, fold_tanh, fold_sinusoidal, fold_phi,
    process_signal, generate_folded_wave, WaveFolderPatch,
)

SR = 44100


class TestWaveFolder:
    def test_fold_basic(self):
        assert isinstance(fold(0.5, 3.0), float)

    def test_fold_tanh(self):
        assert isinstance(fold_tanh(0.5, 3.0), float)

    def test_fold_phi(self):
        assert isinstance(fold_phi(0.5, 3.0), float)

    def test_generate_wave(self):
        patch = WaveFolderPatch(name="test", fold_amount=3.0)
        samples = generate_folded_wave(440.0, 0.2, patch)
        assert len(samples) > 0

    def test_process_signal(self):
        signal = [0.8 * math.sin(2 * math.pi * 440 * i / SR) for i in range(1000)]
        patch = WaveFolderPatch(name="test", fold_amount=2.0)
        result = process_signal(signal, patch)
        assert len(result) == len(signal)
