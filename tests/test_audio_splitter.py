"""Tests for engine.audio_splitter — Session 210."""
import math
import pytest
from engine.audio_splitter import AudioSplitter, AudioSegment

SR = 44100


class TestAudioSplitter:
    def test_create(self):
        s = AudioSplitter()
        assert isinstance(s, AudioSplitter)

    def test_split_by_duration(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR * 2)]
        s = AudioSplitter()
        chunks = s.split_by_duration(signal, duration_ms=1000.0)
        assert len(chunks) >= 2
        assert isinstance(chunks[0], AudioSegment)
