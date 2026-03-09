"""Tests for engine.auto_master — Session 188."""
import math
import pytest
from engine.auto_master import auto_master, MasterResult, MasterSettings

SR = 44100


class TestAutoMaster:
    def test_auto_master_default(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = auto_master(signal)
        assert isinstance(result, MasterResult)
        assert len(result.signal) > 0

    def test_auto_master_to_dict(self):
        signal = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        result = auto_master(signal)
        d = result.to_dict()
        assert "stages" in d
