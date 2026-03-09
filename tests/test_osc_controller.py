"""Tests for engine.osc_controller — Session 169."""
import pytest
from engine.osc_controller import OSCController, OSCMessage, OSCAddresses


class TestOSCController:
    def test_create(self):
        c = OSCController()
        assert isinstance(c, OSCController)

    def test_send(self):
        c = OSCController()
        msg = c.send("/test", 1.0)
        assert isinstance(msg, OSCMessage)
        assert msg.address == "/test"

    def test_play(self):
        c = OSCController()
        msg = c.play()
        assert msg.address == OSCAddresses.PLAY

    def test_set_bpm(self):
        c = OSCController()
        msg = c.set_bpm(140)
        assert 140 in msg.args or 140.0 in msg.args

    def test_message_log(self):
        c = OSCController()
        c.send("/test", 1)
        log = c.message_log(5)
        assert len(log) >= 1

    def test_status(self):
        c = OSCController()
        s = c.status()
        assert isinstance(s, dict)
