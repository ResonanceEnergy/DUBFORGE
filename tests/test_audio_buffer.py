"""Tests for engine.audio_buffer — Session 208."""
import pytest
from engine.audio_buffer import AudioBufferPool, AudioBuffer


class TestAudioBuffer:
    def test_create(self):
        pool = AudioBufferPool()
        assert isinstance(pool, AudioBufferPool)

    def test_allocate(self):
        pool = AudioBufferPool()
        buf = pool.allocate(1024)
        assert isinstance(buf, AudioBuffer)
        assert len(buf.samples) == 1024

    def test_release(self):
        pool = AudioBufferPool()
        buf = pool.allocate(1024)
        result = pool.release(buf.buffer_id)
        assert result is True
