"""Tests for engine.style_transfer — Session 187."""
import math
import pytest
from engine.style_transfer import transfer_style, TransferResult

SR = 44100


class TestStyleTransfer:
    def test_transfer(self):
        source = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        target = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = transfer_style(source, target)
        assert isinstance(result, TransferResult)
        assert len(result.signal) > 0

    def test_transfer_to_dict(self):
        source = [0.5 * math.sin(2 * math.pi * 440 * i / SR) for i in range(SR)]
        target = [0.5 * math.sin(2 * math.pi * 880 * i / SR) for i in range(SR)]
        result = transfer_style(source, target)
        d = result.to_dict()
        assert "transfer_amount" in d
