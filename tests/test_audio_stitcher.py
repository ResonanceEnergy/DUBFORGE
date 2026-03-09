"""Tests for engine.audio_stitcher — Session 217."""
import pytest
from engine.audio_stitcher import AudioStitcher, StitchSegment


class TestAudioStitcher:
    def test_create(self):
        s = AudioStitcher()
        assert isinstance(s, AudioStitcher)

    def test_stitch_sequential(self):
        s = AudioStitcher()
        segments = [
            StitchSegment(samples=[0.5] * 1000),
            StitchSegment(samples=[0.3] * 1000),
        ]
        result = s.stitch_sequential(segments)
        assert len(result) == 2000
