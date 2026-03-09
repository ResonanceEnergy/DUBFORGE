"""Tests for engine.clip_launcher — Session 167."""
import math
import pytest
from engine.clip_launcher import (
    ClipLauncher, Clip, Track, Scene, ClipState, create_default_launcher,
)

SR = 44100


class TestClipLauncher:
    def test_create(self):
        cl = ClipLauncher()
        assert isinstance(cl, ClipLauncher)

    def test_add_track(self):
        cl = ClipLauncher()
        t = cl.add_track("drums")
        assert isinstance(t, Track)

    def test_add_clip(self):
        cl = ClipLauncher()
        cl.add_track("drums")
        signal = [0.5 * math.sin(2 * math.pi * 100 * i / SR) for i in range(SR)]
        clip = Clip(name="kick", signal=signal)
        assert cl.add_clip("drums", clip) is True

    def test_launch_clip(self):
        cl = ClipLauncher()
        cl.add_track("drums")
        signal = [0.5] * SR
        cl.add_clip("drums", Clip(name="test", signal=signal))
        assert cl.launch_clip("drums", 0) is True

    def test_stop_all(self):
        cl = ClipLauncher()
        cl.stop_all()

    def test_status(self):
        cl = ClipLauncher()
        s = cl.status()
        assert isinstance(s, dict)

    def test_default_launcher(self):
        cl = create_default_launcher()
        assert isinstance(cl, ClipLauncher)
